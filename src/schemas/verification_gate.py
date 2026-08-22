"""Skema Verification Gate (Milestone 2.4): request final Query Engine,
hasil pemeriksaan berlapis (bentuk statis, kepatuhan sumber, penegakan
constraint cakupan-individu, verifikasi kelengkapan).

`QueryEngineRequest.params` sengaja `dict[str, Any]` opaque - skema
parameter per-view_name belum terdokumentasi di mana pun (M3.x belum
dibangun). Lihat decisions.md Keputusan 4.

File terpisah dari schemas/cakupan_individu.py (M2.3) - subpackage layer
BEDA (verification_gate/ vs domain_gate/), lihat decisions.md Keputusan 3.
"""

from typing import Any, Self

from pydantic import BaseModel, model_validator

from src.schemas.domain_gate import Domain


class QueryEngineRequest(BaseModel):
    domain: Domain
    view_name: str
    params: dict[str, Any] = {}


class HasilVerifikasiGate(BaseModel):
    request_final: QueryEngineRequest | None
    lolos: bool
    terkoreksi: bool
    alasan_penolakan: str | None = None

    @model_validator(mode="after")
    def konsisten_dengan_lolos(self) -> Self:
        if self.lolos:
            if self.request_final is None:
                raise ValueError("lolos=True wajib punya request_final")
            if self.alasan_penolakan is not None:
                raise ValueError("lolos=True tidak boleh punya alasan_penolakan")
        else:
            if self.request_final is not None:
                raise ValueError("lolos=False wajib request_final=None")
            if self.alasan_penolakan is None:
                raise ValueError("lolos=False wajib punya alasan_penolakan")
        return self
