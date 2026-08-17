"""Klasifikasi Respons dan Penanganan Kegagalan (Milestone 4.2). Konsumen
langsung `HasilPemanggilanChatbotAPI` (M4.1, lewat `_panggil_chatbot_api_raw()`
- BUKAN `panggil_chatbot_api()` publik, lihat decisions.md Keputusan 5)
- membaca `status_code`/`kegagalan_transport`/`body` dan menentukan jalur
penanganan sesuai kontrak `rancangan-execution-interpretation.md`: `200` ->
berhasil (SEBAGIAN sengaja tidak dipakai, Keputusan 1), `403`/`404` ->
eskalasi langsung tanpa retry sama sekali (bug prioritas tinggi), `5xx`/
timeout -> retry infrastruktural sampai batas, `400` -> loop revisi PENUH
ke Query Engine (Keputusan 3, Opsi B).

Murni deterministik, TANPA LLM di modul ini sendiri - satu span
`execute_tool` (tracer `execution.klasifikasi_respons`) membungkus SATU
ATAU LEBIH percobaan (retry infra + revisi 400) sekaligus, mirror pola
refactor M3.1/M3.3. Loop revisi 400 MEMANGGIL fungsi ber-LLM (M3.4/M3.5)
- span `chat` masing-masing otomatis jadi anak span `execute_tool` ini
lewat context propagation OTel (mirror pola `retriever.py`).

Batas retry infra: `EXECUTION_MAX_RETRY_INFRA`. Batas revisi 400:
`EXECUTION_MAX_REVISI` (1 percobaan awal + hingga N-1 revisi). Keduanya
independen - tiap percobaan revisi punya jatah retry infra sendiri.

Revisit (2026-08-17, Keputusan 11): SETELAH 200 sukses, `_meta` (endpoint
tim database) dipanggil SEKALI (tanpa retry, lihat
`panggil_meta_chatbot_api()`) untuk menentukan `berhasil` vs `sebagian`
- `flagged`/data stale (lewat `EXECUTION_DATA_STALENESS_THRESHOLD_JAM`)
-> `sebagian`; `null`/kegagalan `_meta` -> TETAP `berhasil` (TIDAK PERNAH
`sebagian` dari ketidaktahuan semata).
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config.chatbot_api import (
    EXECUTION_DATA_STALENESS_THRESHOLD_JAM,
    EXECUTION_MAX_RETRY_INFRA,
    EXECUTION_MAX_REVISI,
    EXECUTION_RETRY_DELAY_DETIK,
)
from src.layers.execution.pemanggilan_chatbot_api import (
    _panggil_chatbot_api_raw,
    panggil_meta_chatbot_api,
)
from src.layers.query_engine.penyusunan_request import susun_request_atomic_intent
from src.layers.query_engine.verifikasi_bentuk_request import (
    verifikasi_bentuk_request_atomic_intent,
)
from src.layers.verification_gate.verifikasi_gate import verifikasi_gate
from src.observability.tracing import get_tracer
from src.schemas.cakupan_individu import ConstraintCakupanIndividu
from src.schemas.decomposition import AtomicIntent
from src.schemas.execution import HasilEksekusiAtomicIntent, HasilPemanggilanChatbotAPI
from src.schemas.session_memory import StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest

_TRACER_NAME = "execution.klasifikasi_respons"

_STATUS_MIN_SERVER_ERROR = 500


def _kegagalan_infra(hasil: HasilPemanggilanChatbotAPI) -> bool:
    """True kalau hasil ini termasuk kategori retryable (5xx/timeout/
    connection_error) - BUKAN 403/404/400/200 yang masing-masing punya
    jalur penanganannya sendiri di luar retry infra."""
    if hasil.kegagalan_transport is not None:
        return True
    return hasil.status_code is not None and hasil.status_code >= _STATUS_MIN_SERVER_ERROR


def _panggil_dengan_retry_infra(
    request: QueryEngineRequest, role_title: str, employee_id: str
) -> tuple[HasilPemanggilanChatbotAPI, int]:
    """Retry HANYA untuk kegagalan infrastruktural, maks
    `EXECUTION_MAX_RETRY_INFRA` kali (1 percobaan awal + N retry).
    403/404/400/200 dikembalikan APA ADANYA di percobaan pertama kali
    muncul, TANPA retry - keduanya deterministik terhadap isi request
    (arsitektur sumber: retry sia-sia untuk kasus itu). Mengembalikan
    (hasil_terakhir, jumlah_retry_yang_dipakai)."""
    percobaan = 0
    while True:
        hasil = _panggil_chatbot_api_raw(request, role_title, employee_id)
        if not _kegagalan_infra(hasil) or percobaan >= EXECUTION_MAX_RETRY_INFRA:
            return hasil, percobaan
        percobaan += 1
        time.sleep(EXECUTION_RETRY_DELAY_DETIK)


def _data_basi(last_refreshed_at: str) -> bool:
    """True kalau last_refreshed_at melewati
    EXECUTION_DATA_STALENESS_THRESHOLD_JAM dari sekarang (UTC). Parse
    gagal (format tak terduga) -> False (TIDAK dianggap basi) - kegagalan
    parsing murni ketidaktahuan, bukan sinyal kualitas data, sudah
    ditangani jalur null/gagal terpisah (Keputusan 11)."""
    try:
        waktu = datetime.fromisoformat(last_refreshed_at)
    except ValueError:
        return False
    if waktu.tzinfo is None:
        waktu = waktu.replace(tzinfo=timezone.utc)
    usia = datetime.now(timezone.utc) - waktu
    return usia > timedelta(hours=EXECUTION_DATA_STALENESS_THRESHOLD_JAM)


def _tentukan_kualitas_data(
    data_quality_status: str | None, last_refreshed_at: str | None
) -> tuple[StatusEksekusi, str | None]:
    """Keputusan 11 (Revisit): `flagged` ATAU stale -> SEBAGIAN
    (closed-rule, keduanya independen, bisa trigger sendiri-sendiri
    tanpa dobel-hitung). `null`/tidak ada `last_refreshed_at` -> BERHASIL,
    TIDAK PERNAH SEBAGIAN dari ketidaktahuan semata - supaya sinyal
    SEBAGIAN tetap jarang+berarti (2 view guests-* dikonfirmasi tim
    database akan sering null bukan karena masalah)."""
    if data_quality_status == "flagged":
        return StatusEksekusi.SEBAGIAN, "data_quality_flagged"
    if last_refreshed_at is not None and _data_basi(last_refreshed_at):
        return StatusEksekusi.SEBAGIAN, "data_stale"
    return StatusEksekusi.BERHASIL, None


def _ekstrak_alasan_400(body: Any) -> str:
    """chatbot_api membalas 400 dengan body bebas bentuknya (biasanya
    {"detail": "..."} mirror pola 403, tapi tidak dijamin) - diambil
    representasi teks paling informatif yang tersedia untuk dijadikan
    feedback ke susun_request_atomic_intent()."""
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)


def _revisi_request(
    atomic_intent: AtomicIntent,
    view_name: str,
    feedback: str,
    constraint: ConstraintCakupanIndividu,
    employee_id: str,
) -> tuple[QueryEngineRequest | None, str | None]:
    """Orkestrasi loop revisi (Keputusan 3, Opsi B): panggil ulang
    susun_request_atomic_intent() (M3.4) DENGAN feedback, lalu
    verifikasi_bentuk_request_atomic_intent() (M3.5) dan verifikasi_gate()
    (M2.4) APA ADANYA tanpa modifikasi (keduanya stateless, Keputusan 8).
    Mengembalikan (request_final, None) kalau lolos ketiganya, atau
    (None, alasan_spesifik) di titik pertama yang gagal."""
    hasil_susun = susun_request_atomic_intent(atomic_intent, view_name, feedback=feedback)
    if hasil_susun.status != StatusEksekusi.BERHASIL or hasil_susun.request is None:
        return None, "revisi_gagal_susun"

    hasil_verif_bentuk = verifikasi_bentuk_request_atomic_intent(
        atomic_intent, view_name, hasil_susun.request
    )
    if not hasil_verif_bentuk.lolos:
        return None, "revisi_gagal_verifikasi_bentuk"

    hasil_gate = verifikasi_gate(hasil_verif_bentuk.request, constraint, employee_id, view_name)
    if not hasil_gate.lolos or hasil_gate.request_final is None:
        return None, "revisi_gagal_verification_gate"

    return hasil_gate.request_final, None


def eksekusi_atomic_intent(
    atomic_intent: AtomicIntent,
    view_name: str,
    request: QueryEngineRequest,
    constraint: ConstraintCakupanIndividu,
    role_title: str,
    employee_id: str,
) -> HasilEksekusiAtomicIntent:
    """Orkestrator penuh M4.2. `request` HARUS sudah lolos Verification
    Gate (M2.4) sebelum dipanggil (prasyarat M4.1 yang tetap berlaku di
    sini) - `constraint`/`view_name` diteruskan APA ADANYA ke
    `_revisi_request()` kalau jalur 400 terpicu, tidak dipakai di
    percobaan pertama."""
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("execute_tool") as span:
        current_request = request
        total_retry_infra = 0
        revisi_count = 0

        while True:
            hasil_http, retry_infra = _panggil_dengan_retry_infra(
                current_request, role_title, employee_id
            )
            total_retry_infra += retry_infra

            if hasil_http.status_code is not None:
                span.set_attribute("http.response.status_code", hasil_http.status_code)
            span.set_attribute("execution.retry_count_infra", total_retry_infra)
            span.set_attribute("execution.revisi_count", revisi_count)

            if _kegagalan_infra(hasil_http):
                alasan = (
                    f"infra_exhausted_{hasil_http.kegagalan_transport}"
                    if hasil_http.kegagalan_transport is not None
                    else "infra_exhausted_5xx"
                )
                span.set_attribute("error.type", "gagal_teknis")
                span.set_attribute("execution.kegagalan_alasan", alasan)
                return HasilEksekusiAtomicIntent(
                    atomic_intent=atomic_intent,
                    status=StatusEksekusi.GAGAL_TEKNIS,
                    kegagalan_alasan=alasan,
                    retry_count_infra=total_retry_infra,
                    revisi_count=revisi_count,
                )

            status_code = hasil_http.status_code

            if status_code == 200:
                hasil_meta = panggil_meta_chatbot_api(current_request, role_title, employee_id)
                status_akhir, alasan_kualitas = _tentukan_kualitas_data(
                    hasil_meta.data_quality_status, hasil_meta.last_refreshed_at
                )

                if hasil_meta.data_quality_status is not None:
                    span.set_attribute(
                        "execution.data_quality_status", hasil_meta.data_quality_status
                    )
                if hasil_meta.last_refreshed_at is not None:
                    span.set_attribute(
                        "execution.last_refreshed_at", hasil_meta.last_refreshed_at
                    )
                if status_akhir == StatusEksekusi.SEBAGIAN:
                    span.set_attribute("error.type", "sebagian")
                    # BUKAN execution.kegagalan_alasan (nama itu khusus
                    # GAGAL_TEKNIS di jalur lain) - SEBAGIAN bukan kegagalan.
                    span.set_attribute("execution.alasan_sebagian", alasan_kualitas)

                return HasilEksekusiAtomicIntent(
                    atomic_intent=atomic_intent,
                    status=status_akhir,
                    nilai_hasil=hasil_http.body,
                    retry_count_infra=total_retry_infra,
                    revisi_count=revisi_count,
                    data_quality_status=hasil_meta.data_quality_status,
                    last_refreshed_at=hasil_meta.last_refreshed_at,
                )

            if status_code in (403, 404):
                alasan = f"eskalasi_{status_code}"
                span.set_attribute("error.type", "gagal_teknis")
                span.set_attribute("execution.bug_prioritas_tinggi", True)
                span.set_attribute("execution.kegagalan_alasan", alasan)
                return HasilEksekusiAtomicIntent(
                    atomic_intent=atomic_intent,
                    status=StatusEksekusi.GAGAL_TEKNIS,
                    bug_prioritas_tinggi=True,
                    kegagalan_alasan=alasan,
                    retry_count_infra=total_retry_infra,
                    revisi_count=revisi_count,
                )

            if status_code == 400:
                if revisi_count >= EXECUTION_MAX_REVISI - 1:
                    alasan = "revisi_exhausted"
                    span.set_attribute("error.type", "gagal_teknis")
                    span.set_attribute("execution.kegagalan_alasan", alasan)
                    return HasilEksekusiAtomicIntent(
                        atomic_intent=atomic_intent,
                        status=StatusEksekusi.GAGAL_TEKNIS,
                        kegagalan_alasan=alasan,
                        retry_count_infra=total_retry_infra,
                        revisi_count=revisi_count,
                    )

                feedback = _ekstrak_alasan_400(hasil_http.body)
                request_baru, alasan_gagal = _revisi_request(
                    atomic_intent, view_name, feedback, constraint, employee_id
                )
                if request_baru is None:
                    span.set_attribute("error.type", "gagal_teknis")
                    span.set_attribute("execution.kegagalan_alasan", alasan_gagal)
                    return HasilEksekusiAtomicIntent(
                        atomic_intent=atomic_intent,
                        status=StatusEksekusi.GAGAL_TEKNIS,
                        kegagalan_alasan=alasan_gagal,
                        retry_count_infra=total_retry_infra,
                        revisi_count=revisi_count,
                    )

                current_request = request_baru
                revisi_count += 1
                continue

            # Status code lain yang tak terduga (mis. 401) - fallback aman,
            # bukan bagian ruang kesalahan tertutup KK sumber M4.2 tapi
            # tidak boleh crash/diam-diam disamarkan sebagai berhasil.
            alasan = f"status_tak_dikenal_{status_code}"
            span.set_attribute("error.type", "gagal_teknis")
            span.set_attribute("execution.kegagalan_alasan", alasan)
            return HasilEksekusiAtomicIntent(
                atomic_intent=atomic_intent,
                status=StatusEksekusi.GAGAL_TEKNIS,
                kegagalan_alasan=alasan,
                retry_count_infra=total_retry_infra,
                revisi_count=revisi_count,
            )
