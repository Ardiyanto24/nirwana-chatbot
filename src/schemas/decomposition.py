"""Skema Decomposition (Milestone 1.6): Klasifikasi, Pemecahan, Verifikasi.

`LabelBentukJawaban` di-reuse dari src/schemas/session_memory.py (M1.5) -
kontrak bersama PIC 1/PIC 4, TIDAK didefinisikan ulang di sini. Lihat
decisions.md Keputusan 8.

`RelasiKebutuhan` cuma 2 nilai (independen/bergantung) - derived langsung
dari taksonomi Langkah 4 (tunggal/majemuk-independen/majemuk-bergantung),
bukan taksonomi baru yang tidak diminta dokumen sumber. Lihat decisions.md
Keputusan 6.

`atomic_intent_id` TIDAK PERNAH diminta dari LLM - kode yang generate (UUID4)
setelah respons LLM diterima, mirror preseden turun_dependency.py (M1.3).
Lihat decisions.md Keputusan 7.
"""

from enum import Enum

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.session_memory import LabelBentukJawaban


class KlasifikasiKebutuhan(str, Enum):
    TUNGGAL = "tunggal"
    MAJEMUK_INDEPENDEN = "majemuk_independen"
    MAJEMUK_BERGANTUNG = "majemuk_bergantung"


class RelasiKebutuhan(str, Enum):
    INDEPENDEN = "independen"
    BERGANTUNG = "bergantung"


class AtomicIntent(BaseModel):
    atomic_intent_id: str
    teks_kebutuhan: str
    label_bentuk_jawaban: LabelBentukJawaban
    relasi: RelasiKebutuhan
    bergantung_pada: list[str] | None = None

    @model_validator(mode="after")
    def bergantung_pada_konsisten_dengan_relasi(self) -> Self:
        if self.relasi == RelasiKebutuhan.BERGANTUNG and not self.bergantung_pada:
            raise ValueError(
                "relasi=bergantung wajib punya bergantung_pada non-kosong"
            )
        if self.relasi == RelasiKebutuhan.INDEPENDEN and self.bergantung_pada:
            raise ValueError("relasi=independen tidak boleh punya bergantung_pada")
        return self


class PemecahanResult(BaseModel):
    atomic_intents: list[AtomicIntent]


class VerifikasiResult(BaseModel):
    valid: bool
    alasan: str | None = None


class DecompositionResult(BaseModel):
    klasifikasi: KlasifikasiKebutuhan
    atomic_intents: list[AtomicIntent]
    verifikasi_valid: bool
    verifikasi_alasan: str | None = None
    retry_count: int = 0
