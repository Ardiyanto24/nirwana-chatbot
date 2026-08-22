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

from typing import Self

from pydantic import BaseModel, model_validator

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


class HasilVerifikasiBentukRequest(BaseModel):
    """Skema Verifikasi Bentuk Request (Milestone 3.5, Langkah 2 Query Engine):
    hasil penilaian ulang independen `QueryEngineRequest` (M3.4) terhadap
    kepatuhan sumber (`view_name`) dan kecukupan semantik `params` terhadap
    `label_bentuk_jawaban`.

    `request` SELALU utuh (bukan Optional) - M3.5 mendiagnosis, tidak pernah
    merevisi/membuang apa yang dinilainya (beda `HasilVerifikasiGate` M2.4
    yang me-null-kan `request_final` saat `lolos=False`). Lihat
    milestones/3.5-verifikasi-bentuk-request/decisions.md Keputusan 7.

    `status` (teknis, biner) + `lolos`/`alasan` (substantif) menggabungkan
    dua pola preseden berbeda - lihat decisions.md Keputusan 9.
    """

    atomic_intent: AtomicIntent
    request: QueryEngineRequest
    status: StatusEksekusi
    lolos: bool | None
    alasan: str | None

    @model_validator(mode="after")
    def status_lolos_alasan_konsisten(self) -> Self:
        if self.status not in (StatusEksekusi.BERHASIL, StatusEksekusi.GAGAL_TEKNIS):
            raise ValueError(
                "status HasilVerifikasiBentukRequest hanya boleh "
                "berhasil/gagal_teknis - satu pemanggilan LLM, tanpa "
                "keputusan otorisasi/ketergantungan/batch"
            )
        if self.status == StatusEksekusi.GAGAL_TEKNIS:
            if self.lolos is not None or self.alasan is not None:
                raise ValueError("status=gagal_teknis wajib lolos=None dan alasan=None")
            return self

        if self.lolos is None:
            raise ValueError("status=berhasil wajib punya lolos (True/False)")
        if self.lolos and self.alasan is not None:
            raise ValueError("lolos=True tidak boleh punya alasan")
        if not self.lolos and self.alasan is None:
            raise ValueError("lolos=False wajib punya alasan")
        return self
