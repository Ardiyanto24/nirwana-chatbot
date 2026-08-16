"""Skema Deteksi Constraint Cakupan-Individu (Milestone 2.3): catatan
constraint per atomic intent, hasil dua panggilan LLM independen (union
aditif) - mirror pola dua-langkah M2.1, TAPI boolean tunggal per atomic
intent (bukan list domain).

File terpisah dari schemas/authorization.py (M2.2) meski satu subpackage
layer domain_gate/ - satu mekanisme/milestone = satu file skema, lihat
decisions.md Keputusan 9.

`AtomicIntentConstraint` rata (flat) - membawa `atomic_intent` MENTAH +
`domain_decisions` (diteruskan dari M2.2, dibutuhkan Retriever/Query
Engine) + `constraint` sendiri, TIDAK nesting `AtomicIntentAuthorization`
sebagai sub-objek. Lihat decisions.md Keputusan 6.

Tidak ada field `status`/`StatusEksekusi` - kegagalan teknis LLM
ditangani fail-closed langsung di `constraint.terdeteksi=True` (lihat
decisions.md Keputusan 7), bukan lewat field skema tambahan yang tidak
dikonsumsi siapa pun.
"""

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.authorization import DomainAuthorization
from src.schemas.decomposition import AtomicIntent


class DeteksiCakupanIndividuResult(BaseModel):
    """Hasil ANTARA Langkah 1 (deteksi awal) - dikonsumsi orkestrator
    cakupan_individu.py, mirror IdentifikasiDomainResult (M2.1)."""

    terdeteksi: bool
    gagal: bool = False


class VerifikasiCakupanIndividuResult(BaseModel):
    """Hasil ANTARA Langkah 2 (verifikasi titik buta) - independen dari
    Langkah 1, mirror VerifikasiTitikButaResult (M2.1)."""

    terdeteksi_tambahan: bool
    gagal: bool = False


class ConstraintCakupanIndividu(BaseModel):
    terdeteksi: bool
    alasan: str | None = None

    @model_validator(mode="after")
    def alasan_konsisten_dengan_terdeteksi(self) -> Self:
        if self.terdeteksi and self.alasan is None:
            raise ValueError("terdeteksi=True wajib punya alasan")
        if not self.terdeteksi and self.alasan is not None:
            raise ValueError("terdeteksi=False tidak boleh punya alasan")
        return self


class AtomicIntentConstraint(BaseModel):
    atomic_intent: AtomicIntent
    domain_decisions: list[DomainAuthorization]
    constraint: ConstraintCakupanIndividu
