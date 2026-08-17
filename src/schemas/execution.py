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
`src/layers/execution/klasifikasi_respons.py` - reuse `StatusEksekusi`.
`kegagalan_alasan` (BUKAN `error_type`, alasan sama persis dengan
`kegagalan_transport` di atas) menyimpan detail granular untuk atribut
span CUSTOM (`execution.kegagalan_alasan`) - TERPISAH dari atribut
`error.type` (yang diisi `"gagal_teknis"`/`"sebagian"`, satu kosakata
status project, sesuai "Prinsip pengisian error.type" kontrak
observability).

**Revisit (2026-08-17, lihat milestones/4.2-.../decisions.md Keputusan
11):** `SEBAGIAN` SEKARANG valid (sebelumnya sengaja tidak dipakai,
Keputusan 1 asli - endpoint `_meta` tim database baru tersedia sekarang,
memenuhi pemicu peninjauan ulang). `SEBAGIAN` structurally MIRIP
`BERHASIL` (data tetap berhasil diambil, `nilai_hasil` wajib terisi,
TIDAK boleh `kegagalan_alasan`/`bug_prioritas_tinggi` - beda dari
`GAGAL_TEKNIS` yang genuinely gagal). `data_quality_status`/
`last_refreshed_at` diteruskan APA ADANYA dari `HasilMetaChatbotAPI` -
teks manusiawi untuk `catatan_interpretasi` adalah domain M4.3
(`src/layers/execution/penyimpanan_paket.py`), bukan di sini.

`HasilMetaChatbotAPI` (M4.2, revisit): hasil panggilan endpoint
`GET /chatbot/{domain}/{view_name}/_meta` (tim database, Milestone 4.7
sisi mereka) - mirror `HasilPemanggilanChatbotAPI` (XOR status_code/
kegagalan_transport). `data_quality_status`/`last_refreshed_at` BISA
`None` sekalipun `status_code=200` (tim database eksplisit: null berarti
genuinely tidak diketahui, BUKAN default aman) - TIDAK ada invarian yang
memaksa keduanya terisi.
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
    data_quality_status: str | None = None
    last_refreshed_at: str | None = None

    @model_validator(mode="after")
    def konsisten_dengan_status(self) -> Self:
        if self.status not in (
            StatusEksekusi.BERHASIL,
            StatusEksekusi.SEBAGIAN,
            StatusEksekusi.GAGAL_TEKNIS,
        ):
            raise ValueError(
                "status HasilEksekusiAtomicIntent hanya boleh berhasil/sebagian/gagal_teknis "
                "- lihat decisions.md Keputusan 1 (revisi) dan 11"
            )
        if self.status == StatusEksekusi.GAGAL_TEKNIS:
            if self.nilai_hasil is not None:
                raise ValueError("status=gagal_teknis wajib nilai_hasil=None")
            if self.kegagalan_alasan is None:
                raise ValueError("status=gagal_teknis wajib kegagalan_alasan terisi")
        if self.status in (StatusEksekusi.BERHASIL, StatusEksekusi.SEBAGIAN):
            if self.kegagalan_alasan is not None:
                raise ValueError("status=berhasil/sebagian tidak boleh punya kegagalan_alasan")
            if self.bug_prioritas_tinggi:
                raise ValueError("status=berhasil/sebagian tidak boleh bug_prioritas_tinggi=True")
        return self


class HasilMetaChatbotAPI(BaseModel):
    status_code: int | None
    data_quality_status: str | None = None
    last_refreshed_at: str | None = None
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
