"""Pencarian embedding (Milestone 3.1): jalur FALLBACK, dipanggil HANYA
kalau `cari_bm25()` (pencarian_bm25.py) tidak menemukan kandidat berskor
positif sama sekali (`perlu_fallback=True`).

Fungsi generik menerima `model` sebagai parameter - BUKAN hardcode satu
model - supaya bisa dipakai untuk membandingkan 3 kandidat model secara
empiris (Checkpoint 7, eval), sebelum dikunci ke satu model final
(Checkpoint 8). Lihat milestones/3.1-pengumpulan-kandidat-view/decisions.md
Keputusan 2.

Reuse get_openrouter_client() apa adanya (timeout 90s, max_retries=1,
lihat docs/keterbatasan-diterima.md #7) - kegagalan teknis (network/API
error) ditangkap di sini, dikembalikan sebagai `gagal=True`, TIDAK
dilempar sebagai exception ke pemanggil - pola sama M2.1 "verifikasi
titik buta gagal teknis: domain langkah 1 tetap dipakai".
"""

from functools import lru_cache

import numpy as np

from src.config.katalog_view import view_ke_domain
from src.config.llm import get_openrouter_client
from src.layers.retriever.korpus_view import KORPUS_FUNGSI_VIEW
from src.schemas.domain_gate import Domain
from src.schemas.retriever import KandidatView, SumberPencarian


@lru_cache(maxsize=None)
def embed_korpus(model: str) -> dict[str, list[float]]:
    """Embed seluruh 67 teks KORPUS_FUNGSI_VIEW sekali per model (satu
    batch call), di-cache per model - dipanggil ulang untuk tiap
    kandidat model yang dibandingkan Checkpoint 7."""
    client = get_openrouter_client()
    view_names = list(KORPUS_FUNGSI_VIEW.keys())
    teks = list(KORPUS_FUNGSI_VIEW.values())
    response = client.embeddings.create(model=model, input=teks)
    return {view_names[item.index]: item.embedding for item in response.data}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    denom = float(np.linalg.norm(a_arr) * np.linalg.norm(b_arr))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def cari_embedding(
    teks_kebutuhan: str, domain_diizinkan: list[Domain], model: str
) -> tuple[list[KandidatView], bool]:
    """Cari kandidat view_name via cosine similarity embedding, HANYA
    memateralisasi kandidat untuk domain_diizinkan (filter struktural,
    pola sama cari_bm25()). Mengembalikan (kandidat terurut skor menurun,
    gagal) - gagal=True kalau panggilan API error, kandidat kosong."""
    try:
        korpus_vektor = embed_korpus(model)
        client = get_openrouter_client()
        response = client.embeddings.create(model=model, input=[teks_kebutuhan])
        query_vektor = response.data[0].embedding
    except Exception:
        return [], True

    domain_map = view_ke_domain()

    kandidat = [
        KandidatView(
            view_name=view_name,
            domain=domain_map[view_name],
            skor=_cosine_similarity(query_vektor, vektor),
            sumber=SumberPencarian.EMBEDDING_FALLBACK,
        )
        for view_name, vektor in korpus_vektor.items()
        if domain_map[view_name] in domain_diizinkan
    ]
    kandidat.sort(key=lambda k: k.skor, reverse=True)

    return kandidat, False
