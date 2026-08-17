"""Skema Penyusunan Request (Milestone 3.4, Langkah 1 Query Engine):
hasil satu pemanggilan LLM generate-only yang menyusun `QueryEngineRequest`
dari kebutuhan atomik + `view_name` yang sudah divalidasi Retriever.

`QueryEngineRequest` (`{domain, view_name, params}`) DI-REUSE dari
`src/schemas/verification_gate.py` (M2.4, kontrak terkunci) - TIDAK
didefinisikan ulang di sini. Lihat milestones/3.4-penyusunan-request/
decisions.md Keputusan 2.

`status` HANYA `BERHASIL`/`GAGAL_TEKNIS` (beda dari M3.1-3.3 yang py
lebih banyak nilai relevan) - M3.4 satu pemanggilan LLM generate-only,
tanpa semantik batch/parsial/otorisasi/ketergantungan. Validator DUA
ARAH (`status=BERHASIL` <=> `request` terisi) - mirror `HasilVerifikasiGate`
(M2.4), BUKAN pola satu-arah `HasilKecocokanMakna`/`HasilKecukupanStruktural`
(M3.2/M3.3) yang py kasus valid "berhasil tapi kosong" - kasus itu
TIDAK berlaku di M3.4 (BERHASIL selalu berarti ada request konkret).
Lihat decisions.md Keputusan 6.
"""

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.decomposition import AtomicIntent
from src.schemas.session_memory import StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest


class HasilPenyusunanRequest(BaseModel):
    atomic_intent: AtomicIntent
    request: QueryEngineRequest | None
    status: StatusEksekusi

    @model_validator(mode="after")
    def status_konsisten_dengan_request(self) -> Self:
        if self.status not in (StatusEksekusi.BERHASIL, StatusEksekusi.GAGAL_TEKNIS):
            raise ValueError(
                "status HasilPenyusunanRequest hanya boleh berhasil/gagal_teknis "
                "- M3.4 satu pemanggilan LLM generate-only, tanpa keputusan "
                "otorisasi/ketergantungan/batch"
            )
        if self.status == StatusEksekusi.BERHASIL and self.request is None:
            raise ValueError("status=berhasil wajib punya request")
        if self.status == StatusEksekusi.GAGAL_TEKNIS and self.request is not None:
            raise ValueError("status=gagal_teknis wajib request=None")
        return self
