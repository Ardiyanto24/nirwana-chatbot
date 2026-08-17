"""Skema Execution (Milestone 4.1): hasil pemanggilan `chatbot_api` mentah,
tanpa interpretasi apa pun (klasifikasi status jadi tanggung jawab
Milestone 4.2, di luar cakupan skema ini).

`kegagalan_transport` sengaja BUKAN diberi nama `error_type` - kosakata
`error.type` di kontrak observability merujuk klasifikasi status project
(`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/
`terblokir_ketergantungan`), yang jadi tanggung jawab Output Milestone 4.2,
bukan Milestone 4.1. Lihat decisions.md Keputusan 6.
"""

from typing import Any

from pydantic import BaseModel, model_validator
from typing_extensions import Self


class HasilPemanggilanChatbotAPI(BaseModel):
    status_code: int | None
    body: Any = None
    kegagalan_transport: str | None = None

    @model_validator(mode="after")
    def status_code_xor_kegagalan_transport(self) -> Self:
        if self.status_code is None and self.kegagalan_transport is None:
            raise ValueError(
                "status_code=None wajib disertai kegagalan_transport terisi "
                "(tidak ada respons HTTP nyata yang diterima)"
            )
        if self.status_code is not None and self.kegagalan_transport is not None:
            raise ValueError(
                "status_code terisi (respons HTTP nyata diterima) tidak boleh "
                "disertai kegagalan_transport"
            )
        return self
