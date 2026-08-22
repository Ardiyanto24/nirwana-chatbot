"""Skema Pemeriksaan Otorisasi (Milestone 2.2): keputusan izin/tolak per
domain, murni deterministik (lookup role_permissions, TANPA LLM).

File terpisah dari schemas/domain_gate.py (M2.1) meski satu subpackage
layer domain_gate/ - satu mekanisme/milestone = satu file skema, mirror
preseden schemas/matching.py (M1.7) yang terpisah dari
decomposition.py/session_memory.py. Lihat decisions.md Keputusan 7.

Output granular PER DOMAIN (list[DomainAuthorization]), bukan satu
keputusan tunggal per atomic intent - forced Kriteria Keberhasilan 2
sumber, lihat decisions.md Keputusan 3.
"""

from typing import Self

from pydantic import BaseModel, model_validator

from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain


class DomainAuthorization(BaseModel):
    domain: Domain
    diizinkan: bool
    alasan: str | None = None

    @model_validator(mode="after")
    def alasan_konsisten_dengan_diizinkan(self) -> Self:
        if not self.diizinkan and self.alasan is None:
            raise ValueError("diizinkan=False wajib punya alasan")
        if self.diizinkan and self.alasan is not None:
            raise ValueError("diizinkan=True tidak boleh punya alasan")
        return self


class AtomicIntentAuthorization(BaseModel):
    atomic_intent: AtomicIntent
    domain_decisions: list[DomainAuthorization]
