"""Orkestrator Interpretation (Milestone 7.5): Penyusunan Narasi (M4.4) ->
Verifikasi Kesetiaan Data + Visualisasi (M4.5) untuk satu turn, berurutan
nyata.

Return type tuple `(HasilNarasi, HasilVerifikasiNarasi, list[DataVisualisasi]
| None)` - TIDAK ada skema baru, konsisten dengan keputusan M7.4 (lihat
decisions.md Keputusan 3). `APIError` dari `susun_narasi()` (M4.4 sengaja
tanpa fallback) dibiarkan menjalar apa adanya, TIDAK ditangkap di sini
(decisions.md Keputusan 4). Tidak membuka span sendiri - kontrak
observability §2 Interpretation (2 span `chat`) sudah terpenuhi penuh oleh
M4.4/M4.5 masing-masing (decisions.md Keputusan 5).

Lihat milestones/7.5-menyambungkan-interpretation/decisions.md.
"""

from src.layers.interpretation.narasi import susun_narasi
from src.layers.interpretation.verifikasi_kesetiaan import verifikasi_dan_susun_visualisasi
from src.schemas.decomposition import AtomicIntent
from src.schemas.interpretation import DataVisualisasi, HasilNarasi, HasilVerifikasiNarasi
from src.schemas.session_memory import SessionMemoryPackage


def susun_dan_verifikasi_narasi(
    atomic_intents: list[AtomicIntent],
    packages: list[SessionMemoryPackage],
    session_id: str,
    turn_index: int,
) -> tuple[HasilNarasi, HasilVerifikasiNarasi, list[DataVisualisasi] | None]:
    """Gabungkan Langkah 1 (susun narasi) + Langkah 2 (verifikasi
    kesetiaan + visualisasi) untuk satu turn. `APIError` dari
    `susun_narasi()` TIDAK ditangkap - menjalar apa adanya ke pemanggil
    (M4.4 sengaja tanpa fallback aman)."""
    hasil_narasi = susun_narasi(atomic_intents, packages, session_id, turn_index)

    hasil_verifikasi, visualisasi = verifikasi_dan_susun_visualisasi(
        hasil_narasi.narasi, atomic_intents, packages, session_id, turn_index
    )
    return hasil_narasi, hasil_verifikasi, visualisasi
