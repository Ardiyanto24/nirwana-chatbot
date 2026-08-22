"""Skema Pengumpulan Kandidat View (Milestone 3.1) + Kecocokan Makna
(Milestone 3.2): hasil pencarian kandidat `view_name` dari satu kebutuhan
atomik + domain yang diizinkan (M3.1), lalu penilaian kecocokan tiap
kandidat terhadap definisi lengkap katalog (M3.2).

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

Skema M3.2 (`LabelKecocokanMakna`/`KecocokanKandidat`/`HasilKecocokanMakna`)
GAGAL_TEKNIS + BERHASIL + SEBAGIAN sama-sama relevan di sini (beda dari
M3.1) - GAGAL_TEKNIS dipakai untuk kegagalan teknis Langkah 1 total.
Validator `HasilKecocokanMakna` SATU ARAH (bukan dua arah seperti
`AtomicIntentDomains`) - status BERHASIL dengan `kecocokan=[]` tetap
valid (M3.1 memang bisa tidak menemukan kandidat sama sekali). Lihat
milestones/3.2-kecocokan-makna/decisions.md Keputusan 7-10.

Skema M3.3 (`SumberKeputusanKecukupan`/`KecukupanKandidat`/
`HasilKecukupanStruktural`) - HANYA `StatusEksekusi.BERHASIL` yang valid
(beda dari M3.1/M3.2 yang punya mode gagal teknis nyata): mekanisme
hybrid M3.3 tidak pernah gagal teknis di level kebutuhan-atomik, jalur
deterministik murni Python dan kegagalan LLM fallback diserap sebagai
default aman `cukup=False` per-kandidat (bukan dipropagasi jadi status
gagal). `view_name_final` divalidasi wajib salah satu kandidat berlabel
`cukup=True` di `kecukupan` (cek kelengkapan penegakan, mirror
verifikasi_gate() M2.4 cek 4), atau `None` kalau tidak ada kandidat
cukup. Lihat milestones/3.3-kecukupan-struktural/decisions.md
Keputusan 9.
"""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, model_validator

from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import StatusEksekusi


class SumberPencarian(StrEnum):
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


class LabelKecocokanMakna(StrEnum):
    DITEMUKAN = "ditemukan"
    SEBAGIAN = "sebagian"
    TIDAK_DITEMUKAN = "tidak_ditemukan"


class KecocokanKandidat(BaseModel):
    kandidat: KandidatView
    label: LabelKecocokanMakna
    alasan: str


class HasilKecocokanMakna(BaseModel):
    atomic_intent: AtomicIntent
    kecocokan: list[KecocokanKandidat]
    status: StatusEksekusi

    @model_validator(mode="after")
    def kecocokan_konsisten_dengan_status(self) -> Self:
        if self.status == StatusEksekusi.GAGAL_TEKNIS and self.kecocokan:
            raise ValueError("status=gagal_teknis wajib kecocokan kosong")
        if self.status not in (
            StatusEksekusi.BERHASIL,
            StatusEksekusi.SEBAGIAN,
            StatusEksekusi.GAGAL_TEKNIS,
        ):
            raise ValueError(
                "status HasilKecocokanMakna hanya boleh berhasil/sebagian/"
                "gagal_teknis - M3.2 tidak membuat keputusan otorisasi/"
                "ketergantungan"
            )
        return self


class SumberKeputusanKecukupan(StrEnum):
    DETERMINISTIK = "deterministik"
    LLM = "llm"


class KecukupanKandidat(BaseModel):
    kandidat: KandidatView
    kecocokan_label: LabelKecocokanMakna
    cukup: bool
    alasan: str
    sumber_keputusan: SumberKeputusanKecukupan


class HasilKecukupanStruktural(BaseModel):
    atomic_intent: AtomicIntent
    kecukupan: list[KecukupanKandidat]
    view_name_final: str | None
    status: StatusEksekusi

    @model_validator(mode="after")
    def status_dan_view_name_final_konsisten(self) -> Self:
        if self.status != StatusEksekusi.BERHASIL:
            raise ValueError(
                "status HasilKecukupanStruktural wajib berhasil - mekanisme "
                "M3.3 tidak pernah gagal teknis di level kebutuhan-atomik "
                "(jalur deterministik murni Python, kegagalan LLM fallback "
                "diserap sebagai default aman cukup=False per-kandidat)"
            )
        if self.view_name_final is not None:
            view_names_cukup = {k.kandidat.view_name for k in self.kecukupan if k.cukup}
            if self.view_name_final not in view_names_cukup:
                raise ValueError(
                    "view_name_final wajib salah satu kandidat berlabel "
                    "cukup=True di kecukupan - tidak boleh memilih view yang "
                    "tidak pernah dinyatakan cukup"
                )
        return self
