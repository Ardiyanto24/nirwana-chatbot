"""Skema Pengumpulan Kandidat View (Milestone 3.1): hasil pencarian
kandidat `view_name` dari satu kebutuhan atomik + domain yang diizinkan.

Reuse eksplisit `AtomicIntent` (schemas/decomposition.py) dan `Domain`
(schemas/domain_gate.py) - tidak didefinisikan ulang, preseden konsisten
seluruh layer domain_gate/. `status` reuse `StatusEksekusi`
(schemas/session_memory.py) - HANYA 2 dari 5 nilai relevan di titik
pipeline ini:
- BERHASIL: BM25 cukup (fallback_terpicu=False), ATAU fallback embedding
  terpicu dan berhasil menambah kandidat.
- SEBAGIAN: fallback embedding terpicu tapi gagal teknis (network/API
  error) - kandidat BM25 tetap dikembalikan, bukan diblok total. Pola
  sama M2.1 "verifikasi titik buta gagal teknis: domain langkah 1 tetap
  dipakai."
GAGAL_TEKNIS tidak relevan di sini - BM25 murni deterministik, tidak
pernah "gagal teknis" seperti pemanggilan LLM. DITOLAK_OTORISASI dan
TERBLOKIR_KETERGANTUNGAN juga tidak relevan (M3.1 murni pencocokan,
tanpa keputusan otorisasi atau ketergantungan turn).

Lihat milestones/3.1-pengumpulan-kandidat-view/decisions.md.
"""

from enum import Enum

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import StatusEksekusi


class SumberPencarian(str, Enum):
    BM25 = "bm25"
    EMBEDDING_FALLBACK = "embedding_fallback"


class KandidatView(BaseModel):
    view_name: str
    domain: Domain
    skor: float
    sumber: SumberPencarian


class HasilPencarianKandidat(BaseModel):
    atomic_intent: AtomicIntent
    domain_diizinkan: list[Domain]
    kandidat: list[KandidatView]
    fallback_terpicu: bool
    status: StatusEksekusi

    @model_validator(mode="after")
    def status_konsisten_dengan_fallback(self) -> Self:
        if self.status not in (StatusEksekusi.BERHASIL, StatusEksekusi.SEBAGIAN):
            raise ValueError(
                "status HasilPencarianKandidat hanya boleh berhasil/sebagian "
                "- BM25 murni deterministik (tidak pernah gagal_teknis), M3.1 "
                "tidak membuat keputusan otorisasi/ketergantungan"
            )
        if not self.fallback_terpicu and self.status != StatusEksekusi.BERHASIL:
            raise ValueError(
                "fallback_terpicu=False wajib status=berhasil - BM25 tidak "
                "punya mode gagal-sebagian, status=sebagian hanya muncul "
                "kalau fallback embedding terpicu dan gagal teknis"
            )
        return self
