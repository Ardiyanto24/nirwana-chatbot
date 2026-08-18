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
"""

from datetime import date

from src.layers.query_engine.penyusunan_request import susun_request_atomic_intent
from src.layers.query_engine.verifikasi_bentuk_request import (
    verifikasi_bentuk_request_atomic_intent,
)
from src.schemas.decomposition import AtomicIntent
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.session_memory import StatusEksekusi


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
