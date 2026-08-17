"""Pencarian BM25 (Milestone 3.1): jalur utama pencarian kandidat
view_name, murni deterministik, tanpa network call. Index dibangun sekali
per proses (`@lru_cache`) dari `KORPUS_FUNGSI_VIEW`.

Trigger fallback ke embedding (Checkpoint 6) - PROVISIONAL:
BM25_SKOR_MINIMUM = 0.0 (tidak ada satu pun kandidat berskor positif di
domain_diizinkan, artinya tidak ada overlap leksikal sama sekali). Nilai
ini eksplisit sementara, direvisi Checkpoint 9 berbasis bukti eval
Checkpoint 7 - lihat
milestones/3.1-pengumpulan-kandidat-view/decisions.md.

Filter domain diterapkan di titik MATERIALISASI kandidat (Keputusan 6
decisions.md) - kandidat untuk domain di luar domain_diizinkan TIDAK
PERNAH dikonstruksi sama sekali, bukan disaring belakangan.
"""

import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from src.config.katalog_view import view_ke_domain
from src.layers.retriever.korpus_view import KORPUS_FUNGSI_VIEW
from src.schemas.domain_gate import Domain
from src.schemas.retriever import KandidatView, SumberPencarian

BM25_SKOR_MINIMUM = 0.0

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenisasi(teks: str) -> list[str]:
    return _TOKEN_PATTERN.findall(teks.lower())


@lru_cache(maxsize=1)
def _view_names() -> tuple[str, ...]:
    return tuple(KORPUS_FUNGSI_VIEW.keys())


@lru_cache(maxsize=1)
def _bm25_index() -> BM25Okapi:
    korpus_tertokenisasi = [_tokenisasi(KORPUS_FUNGSI_VIEW[v]) for v in _view_names()]
    return BM25Okapi(korpus_tertokenisasi)


def cari_bm25(
    teks_kebutuhan: str, domain_diizinkan: list[Domain]
) -> tuple[list[KandidatView], bool]:
    """Cari kandidat view_name via BM25 atas KORPUS_FUNGSI_VIEW. HANYA
    memateralisasi kandidat untuk domain_diizinkan (filter struktural,
    bukan post-filter). Hanya kandidat berskor > 0 (overlap leksikal
    nyata) yang dikembalikan - kandidat skor 0 bukan "mungkin relevan",
    murni noise. Mengembalikan (kandidat terurut skor menurun,
    perlu_fallback)."""
    index = _bm25_index()
    view_names = _view_names()
    domain_map = view_ke_domain()

    skor_semua = index.get_scores(_tokenisasi(teks_kebutuhan))

    kandidat = [
        KandidatView(
            view_name=view_name,
            domain=domain_map[view_name],
            skor=float(skor),
            sumber=SumberPencarian.BM25,
        )
        for view_name, skor in zip(view_names, skor_semua)
        if domain_map[view_name] in domain_diizinkan and skor > BM25_SKOR_MINIMUM
    ]
    kandidat.sort(key=lambda k: k.skor, reverse=True)

    perlu_fallback = len(kandidat) == 0

    return kandidat, perlu_fallback
