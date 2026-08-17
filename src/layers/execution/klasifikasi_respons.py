"""Klasifikasi Respons dan Penanganan Kegagalan (Milestone 4.2). Konsumen
langsung `HasilPemanggilanChatbotAPI` (M4.1, lewat `_panggil_chatbot_api_raw()`
- BUKAN `panggil_chatbot_api()` publik, lihat decisions.md Keputusan 5)
- membaca `status_code`/`kegagalan_transport`/`body` dan menentukan jalur
penanganan sesuai kontrak `rancangan-execution-interpretation.md`: `200` ->
berhasil (SEBAGIAN sengaja tidak dipakai, Keputusan 1), `403`/`404` ->
eskalasi langsung tanpa retry sama sekali (bug prioritas tinggi), `5xx`/
timeout -> retry infrastruktural sampai batas, `400` -> loop revisi ke
Query Engine (M3.4, Checkpoint 6).

Murni deterministik, TANPA LLM - satu span `execute_tool` (tracer
`execution.klasifikasi_respons`) membungkus SATU ATAU LEBIH percobaan
(retry infra + revisi 400) sekaligus, mirror pola refactor M3.1/M3.3.

Checkpoint 5 (saat ini): jalur 200/403/404/retry-infra-exhausted.
Jalur 400 SEMENTARA placeholder gagal_teknis, dilengkapi Checkpoint 6.
"""

import time

from src.config.chatbot_api import (
    EXECUTION_MAX_RETRY_INFRA,
    EXECUTION_RETRY_DELAY_DETIK,
)
from src.layers.execution.pemanggilan_chatbot_api import _panggil_chatbot_api_raw
from src.observability.tracing import get_tracer
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


def eksekusi_atomic_intent(
    atomic_intent: AtomicIntent,
    view_name: str,
    request: QueryEngineRequest,
    constraint,
    role_title: str,
    employee_id: str,
) -> HasilEksekusiAtomicIntent:
    """Orkestrator M4.2. `view_name` (tervalidasi Retriever M3.1-3.3) dan
    `constraint` (ConstraintCakupanIndividu, Domain Gate M2.3) BELUM
    dipakai di Checkpoint 5 ini - keduanya dibutuhkan `_revisi_request()`
    (Checkpoint 6) untuk memanggil ulang `verifikasi_gate()` (M2.4) saat
    jalur 400 diimplementasikan penuh. Signature disiapkan sekaligus
    supaya konsumen (belum ada - project belum wiring end-to-end) tidak
    perlu menyesuaikan pemanggilan dua kali."""
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("execute_tool") as span:
        hasil_http, retry_infra = _panggil_dengan_retry_infra(request, role_title, employee_id)

        if hasil_http.status_code is not None:
            span.set_attribute("http.response.status_code", hasil_http.status_code)
        span.set_attribute("execution.retry_count_infra", retry_infra)

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
                retry_count_infra=retry_infra,
            )

        status_code = hasil_http.status_code

        if status_code == 200:
            return HasilEksekusiAtomicIntent(
                atomic_intent=atomic_intent,
                status=StatusEksekusi.BERHASIL,
                nilai_hasil=hasil_http.body,
                retry_count_infra=retry_infra,
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
                retry_count_infra=retry_infra,
            )

        if status_code == 400:
            # Checkpoint 6 melengkapi jalur ini dengan loop revisi nyata
            # ke Query Engine (M3.4 feedback) + Verifikasi Bentuk Request
            # (M3.5) + Verification Gate (M2.4).
            alasan = "belum_diimplementasi"
            span.set_attribute("error.type", "gagal_teknis")
            span.set_attribute("execution.kegagalan_alasan", alasan)
            return HasilEksekusiAtomicIntent(
                atomic_intent=atomic_intent,
                status=StatusEksekusi.GAGAL_TEKNIS,
                kegagalan_alasan=alasan,
                retry_count_infra=retry_infra,
            )

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
            retry_count_infra=retry_infra,
        )
