"""Pencarian BM25 (Milestone 3.1): jalur utama pencarian kandidat
view_name, murni deterministik, tanpa network call. Index dibangun sekali
per proses (`@lru_cache`) dari `KORPUS_FUNGSI_VIEW`.

Trigger fallback ke embedding (Checkpoint 6) - REVISI Checkpoint 9
berbasis bukti `evals/3.1-pengumpulan-kandidat-view/audit.md`:

1. **Stopword filtering ditambahkan** (`_STOPWORDS_ID`). Temuan Checkpoint 9:
   tokenizer awal Checkpoint 5 (tanpa stopword) membuat query APA PUN nyaris
   selalu punya skor positif terhadap SETIAP view lewat kata fungsi umum
   ("yang", "dan", "di", dst, muncul di hampir seluruh 67 teks korpus) -
   trigger `perlu_fallback` jadi TIDAK PERNAH aktif bahkan untuk 5/5
   skenario stress-test Checkpoint 7 yang eksplisit dirancang menstress
   kegagalan BM25 (dikonfirmasi ulang: implementasi ASLI tanpa stopword
   filtering menghasilkan `perlu_fallback=False` di SEMUA 5 skenario,
   bukan cuma 4/5 seperti draf awal `rancangan.md`/`audit.md` sebelum
   koreksi ini - lihat logs.md Checkpoint 9 untuk detail kesalahan
   dokumentasi yang diperbaiki).
2. **BM25_SKOR_MINIMUM dipertahankan di 0.0** (bukan dinaikkan) - dengan
   stopword filtering, skor positif kini benar-benar berarti overlap kata
   BERMAKNA (bukan kata fungsi), jadi threshold "positif vs nol" kembali
   jadi sinyal yang wajar, bukan lagi trigger yang nyaris tidak pernah
   aktif.

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

# Kata fungsi umum Bahasa Indonesia (+ beberapa Inggris/istilah generik yang
# muncul di korpus, mis. "vs", "mis") - tanpa daftar ini, kata-kata ini
# muncul di hampir seluruh 67 teks Fungsi sehingga query APA PUN kebetulan
# selalu "cocok" sesuatu, membuat trigger fallback nyaris tidak pernah aktif
# (temuan Checkpoint 9, bukan daftar stemming lengkap - sengaja konservatif,
# hanya kata fungsi murni tanpa muatan topik/domain).
_STOPWORDS_ID = frozenset(
    {
        "yang", "dan", "atau", "di", "ke", "dari", "ini", "itu", "untuk",
        "dengan", "pada", "adalah", "atas", "akan", "bisa", "ada", "tidak",
        "tapi", "juga", "saja", "saat", "oleh", "sebagai", "secara", "per",
        "jadi", "kalau", "karena", "seperti", "lebih", "sudah", "belum",
        "masih", "harus", "dapat", "agar", "maupun", "serta", "bagi",
        "tentang", "tanpa", "hal", "satu", "dua", "para", "apa", "gimana",
        "sih", "ya", "nya", "mu", "ku", "the", "a", "an", "of", "in", "on",
        "for", "to", "vs", "mis",
    }
)


def _tokenisasi(teks: str) -> list[str]:
    return [
        t for t in _TOKEN_PATTERN.findall(teks.lower()) if t not in _STOPWORDS_ID
    ]


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
