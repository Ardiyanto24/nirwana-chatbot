"""Orkestrator Query Engine (Milestone 7.4): Penyusunan Request (M3.4) ->
Verifikasi Bentuk Request (M3.5) untuk SATU atomic intent, berurutan nyata.

`view_name_tervalidasi_retriever` sengaja terpisah dari `view_name` (default
ke `view_name` kalau tidak diisi) - satu-satunya caller nyata yang sudah ada
(`_revisi_request()`, M4.2) memakai nilai identik untuk keduanya, tapi
Kriteria Keberhasilan M7.4 butuh kemungkinan nilai berbeda untuk membuktikan
skenario mismatch tertangkap mengalir dari Susun ke Verifikasi (lihat
decisions.md Keputusan 3).

Return type tuple `(HasilPenyusunanRequest, HasilVerifikasiBentukRequest |
None)`, elemen kedua `None` kalau Susun gagal - TIDAK ada skema baru (lihat
decisions.md Keputusan 5). Tidak membuka span sendiri - kontrak observability
§2 Query Engine (2 span `chat`) sudah terpenuhi penuh oleh M3.4/M3.5 masing-
masing (lihat decisions.md Keputusan 7).

Lihat milestones/7.4-menyambungkan-query-engine/decisions.md.

Milestone 7.12 (Sambungan 7: Retriever -> Query Engine): fungsi batch baru
`susun_dan_verifikasi_request_semua()` - layer ini sebelumnya HANYA py
`susun_dan_verifikasi_request_atomic_intent()` per-item, tidak ada wrapper
level-list untuk gabungan Langkah 1+2 (beda dari `verifikasi_bentuk_request_
semua()` yang sudah ada tapi khusus Langkah 2 saja, dipakai jalur revisi
`_revisi_request()` M4.2). Item Retriever dengan `view_name_final=None`
WAJIB di-skip (forced by signature `view_name: str` non-Optional), bukan
pilihan gaya seperti filtering Retriever M7.11. Lihat
milestones/7.12-sambungan-query-engine/decisions.md Keputusan 2-4+8.
"""

from datetime import date

from src.layers.query_engine.penyusunan_request import susun_request_atomic_intent
from src.layers.query_engine.verifikasi_bentuk_request import (
    verifikasi_bentuk_request_atomic_intent,
)
from src.observability.tracing import get_tracer
from src.schemas.decomposition import AtomicIntent
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.retriever import HasilKecukupanStruktural
from src.schemas.session_memory import StatusEksekusi

_TRACER_NAME = "query_engine.query_engine"


def susun_dan_verifikasi_request_atomic_intent(
    atomic_intent: AtomicIntent,
    view_name: str,
    view_name_tervalidasi_retriever: str | None = None,
    tanggal_referensi: date | None = None,
    feedback: str | None = None,
) -> tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]:
    """Gabungkan Langkah 1 (susun) + Langkah 2 (verifikasi bentuk) untuk
    SATU atomic intent. Langkah 2 TIDAK dipanggil kalau Langkah 1 gagal
    total - tidak ada request untuk diverifikasi."""
    if view_name_tervalidasi_retriever is None:
        view_name_tervalidasi_retriever = view_name

    hasil_susun = susun_request_atomic_intent(
        atomic_intent, view_name, tanggal_referensi, feedback
    )

    if hasil_susun.status != StatusEksekusi.BERHASIL or hasil_susun.request is None:
        return hasil_susun, None

    hasil_verifikasi = verifikasi_bentuk_request_atomic_intent(
        atomic_intent, view_name_tervalidasi_retriever, hasil_susun.request
    )
    return hasil_susun, hasil_verifikasi


# --- Orkestrator batch (M7.12): daftar HasilKecukupanStruktural -> daftar tuple ---


def susun_dan_verifikasi_request_semua(
    daftar_retriever: list[HasilKecukupanStruktural],
) -> list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]:
    """Untuk seluruh `HasilKecukupanStruktural` (Retriever, M7.11) dalam
    satu turn, susun+verifikasi request-nya satu per satu lewat
    `susun_dan_verifikasi_request_atomic_intent()` - mirror struktur
    `domain_gate.identifikasi_domain_semua()`/`retriever.proses_retrieval_
    semua()`. Ditambah Milestone 7.12 (layer Query Engine sendiri belum py
    fungsi batch untuk gabungan Langkah 1+2 - lihat
    milestones/7.12-sambungan-query-engine/decisions.md Keputusan 2-3).

    Item dengan `view_name_final=None` (Retriever tidak menemukan view
    cukup) DI-SKIP, TIDAK diteruskan ke `susun_request_atomic_intent()` -
    forced oleh signature `view_name: str` non-Optional, bukan pilihan
    gaya (lihat decisions.md Keputusan 4). `view_name`/`view_name_
    tervalidasi_retriever` diisi dari `view_name_final` yang SAMA
    (decisions.md Keputusan 5)."""
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("query_engine.susun_dan_verifikasi_request_semua") as span:
        span.set_attribute("intent.count", len(daftar_retriever))

        hasil = [
            susun_dan_verifikasi_request_atomic_intent(item.atomic_intent, item.view_name_final)
            for item in daftar_retriever
            if item.view_name_final is not None
        ]

        return hasil
