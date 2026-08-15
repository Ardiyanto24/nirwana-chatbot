"""Orkestrator Decomposition (Milestone 1.6): Klasifikasi -> Pemecahan ->
Verifikasi, dengan retry.

Klasifikasi dipanggil SEKALI (tidak ikut retry loop - lihat decisions.md
Keputusan 9). Pemecahan+Verifikasi diulang maksimal 3 kali TOTAL (1
percobaan awal + hingga 2 retry) kalau Verifikasi menilai hasil invalid,
dengan alasan invalid disisipkan sebagai feedback ke percobaan berikutnya
(lihat decisions.md Keputusan 3). Kalau percobaan ke-3 masih invalid, hasil
percobaan terakhir tetap dikembalikan apa adanya (verifikasi_valid=False
TIDAK disamarkan jadi True) - kejujuran terhadap keterbatasan.
"""

from src.layers.decomposition.klasifikasi import klasifikasi_kebutuhan
from src.layers.decomposition.pemecahan import pecah_atomik
from src.layers.decomposition.verifikasi import verifikasi_pemecahan
from src.schemas.decomposition import DecompositionResult

_MAX_ATTEMPTS = 3


def decompose_question(question: str) -> DecompositionResult:
    klasifikasi = klasifikasi_kebutuhan(question)

    feedback: str | None = None
    attempt = 1
    while True:
        hasil = pecah_atomik(question, klasifikasi, feedback)
        verifikasi = verifikasi_pemecahan(question, hasil)
        if verifikasi.valid or attempt >= _MAX_ATTEMPTS:
            break
        feedback = verifikasi.alasan
        attempt += 1

    return DecompositionResult(
        klasifikasi=klasifikasi,
        atomic_intents=hasil.atomic_intents,
        verifikasi_valid=verifikasi.valid,
        verifikasi_alasan=verifikasi.alasan,
        retry_count=attempt - 1,
    )
