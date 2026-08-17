"""Skema Execution (Milestone 4.1-4.2).

`HasilPemanggilanChatbotAPI` (M4.1): hasil pemanggilan `chatbot_api`
mentah, tanpa interpretasi apa pun (klasifikasi status jadi tanggung
jawab Milestone 4.2).

`kegagalan_transport` sengaja BUKAN diberi nama `error_type` - kosakata
`error.type` di kontrak observability merujuk klasifikasi status project
(`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/
`terblokir_ketergantungan`), yang jadi tanggung jawab Output Milestone 4.2,
bukan Milestone 4.1. Lihat decisions.md M4.1 Keputusan 6.

`HasilEksekusiAtomicIntent` (M4.2): hasil klasifikasi akhir SETELAH
retry infrastruktural + loop revisi 400 diselesaikan sepenuhnya oleh
`src/layers/execution/klasifikasi_respons.py` - reuse `StatusEksekusi`
(HANYA `BERHASIL`/`GAGAL_TEKNIS` relevan di sini, `SEBAGIAN` SENGAJA
tidak dipakai, lihat milestones/4.2-.../decisions.md Keputusan 1 dan 7).
`kegagalan_alasan` (BUKAN `error_type`, alasan sama persis dengan
`kegagalan_transport` di atas) menyimpan detail granular untuk atribut
span CUSTOM (`execution.kegagalan_alasan`) - TERPISAH dari atribut
`error.type` (yang HANYA diisi `"gagal_teknis"`, satu kosakata status
project, sesuai "Prinsip pengisian error.type" kontrak observability).
"""

from typing import Any

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.decomposition import AtomicIntent
from src.schemas.session_memory import StatusEksekusi


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


class HasilEksekusiAtomicIntent(BaseModel):
    atomic_intent: AtomicIntent
    status: StatusEksekusi
    nilai_hasil: Any = None
    bug_prioritas_tinggi: bool = False
    retry_count_infra: int = 0
    revisi_count: int = 0
    kegagalan_alasan: str | None = None

    @model_validator(mode="after")
    def konsisten_dengan_status(self) -> Self:
        if self.status not in (StatusEksekusi.BERHASIL, StatusEksekusi.GAGAL_TEKNIS):
            raise ValueError(
                "status HasilEksekusiAtomicIntent hanya boleh berhasil/gagal_teknis "
                "- SEBAGIAN sengaja tidak dipakai di M4.2, lihat decisions.md Keputusan 1"
            )
        if self.status == StatusEksekusi.GAGAL_TEKNIS:
            if self.nilai_hasil is not None:
                raise ValueError("status=gagal_teknis wajib nilai_hasil=None")
            if self.kegagalan_alasan is None:
                raise ValueError("status=gagal_teknis wajib kegagalan_alasan terisi")
        if self.status == StatusEksekusi.BERHASIL:
            if self.kegagalan_alasan is not None:
                raise ValueError("status=berhasil tidak boleh punya kegagalan_alasan")
            if self.bug_prioritas_tinggi:
                raise ValueError("status=berhasil tidak boleh bug_prioritas_tinggi=True")
        return self
