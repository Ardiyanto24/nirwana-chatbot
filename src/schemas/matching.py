"""Skema Pencocokan Atomic Intent x Data Session Memory (Milestone 1.7).

`MatchStatus` sengaja 2 nilai (bukan mewarisi kosakata `StatusEksekusi` 5
nilai) - forced by Output M1.7 sendiri: label routing "selesai"/"perlu
eksekusi", beda konsep dari `status` kualitas eksekusi di dalam
`SessionMemoryPackage`. Lihat decisions.md Keputusan 9.

`AtomicIntentMatch.paket` HANYA terisi kalau status=selesai - validator
konsistensi mirror pola `AtomicIntent.bergantung_pada_konsisten_dengan_relasi`
(src/schemas/decomposition.py, M1.6).
"""

from enum import Enum, StrEnum

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.decomposition import AtomicIntent
from src.schemas.session_memory import SessionMemoryPackage


class MatchStatus(StrEnum):
    SELESAI = "selesai"
    PERLU_EKSEKUSI = "perlu_eksekusi"


class AtomicIntentMatch(BaseModel):
    atomic_intent: AtomicIntent
    status: MatchStatus
    paket: SessionMemoryPackage | None = None

    @model_validator(mode="after")
    def paket_konsisten_dengan_status(self) -> Self:
        if self.status == MatchStatus.SELESAI and self.paket is None:
            raise ValueError("status=selesai wajib punya paket")
        if self.status == MatchStatus.PERLU_EKSEKUSI and self.paket is not None:
            raise ValueError("status=perlu_eksekusi tidak boleh punya paket")
        return self
