"""Skema Identifikasi Domain (Milestone 2.1): Domain Enum, hasil gabungan
identifikasi awal + verifikasi titik buta per atomic intent.

`Domain` 10 nilai tertutup - forced by `role_permissions` (20 role x 10
domain), lihat decisions.md Keputusan 4.

`AtomicIntentDomains.status` reuse `StatusEksekusi` dari
src/schemas/session_memory.py (M1.5) alih-alih field bool baru - forced by
prinsip "Kejujuran terhadap keterbatasan" CLAUDE.md, lihat decisions.md
Keputusan 6. HANYA 3 dari 5 nilai StatusEksekusi relevan di titik pipeline
ini:
- BERHASIL: identifikasi awal dan verifikasi titik buta sukses.
- SEBAGIAN: identifikasi awal sukses, verifikasi titik buta gagal teknis
  (domain langkah 1 tetap dipakai, belum diverifikasi independen).
- GAGAL_TEKNIS: identifikasi awal gagal total, domain tidak bisa
  ditentukan sama sekali (domains WAJIB kosong).
DITOLAK_OTORISASI (milik Milestone 2.2) dan TERBLOKIR_KETERGANTUNGAN
(tidak relevan konteks ini) TIDAK PERNAH dipakai di sini.
"""

from enum import Enum

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.decomposition import AtomicIntent
from src.schemas.session_memory import StatusEksekusi


class Domain(str, Enum):
    RESERVATION = "reservation"
    FNB = "fnb"
    FACILITY = "facility"
    SPA_EVENT = "spa_event"
    HR = "hr"
    FINANCIAL = "financial"
    PROPERTIES_REF = "properties_ref"
    EMPLOYEES_DIRECTORY = "employees_directory"
    GUESTS_PII = "guests_pii"
    GUESTS_PROFILE = "guests_profile"


class AtomicIntentDomains(BaseModel):
    atomic_intent: AtomicIntent
    domains: list[Domain]
    status: StatusEksekusi

    @model_validator(mode="after")
    def domains_konsisten_dengan_status(self) -> Self:
        if self.status == StatusEksekusi.GAGAL_TEKNIS and self.domains:
            raise ValueError("status=gagal_teknis wajib domains kosong")
        if self.status != StatusEksekusi.GAGAL_TEKNIS and not self.domains:
            raise ValueError(
                "status selain gagal_teknis wajib domains non-kosong"
            )
        return self
