"""Skema response HTTP endpoint (Milestone 7.17): bentuk yang dikirim
`POST /v1/turns` ke frontend - genuinely concern baru (API di luar
9 layer), bukan salah satu skema per-layer di `src/schemas/`.

`TurnResponse` DISUSUN dari `KeadaanTurn.interpretation` (3-tuple
HasilNarasi/HasilVerifikasiNarasi/DataVisualisasi, M7.5) oleh
`src/main.py::_build_turn_response()` - lihat
milestones/7.17-membangun-endpoint-api/decisions.md Keputusan 1+5.
`narasi` DIGANTI pesan generik aman kapan pun `terverifikasi=False`
(mencakup HasilVerifikasiNarasi.lolos=False DAN lolos=None/GAGAL_TEKNIS)
- keputusan konservatif fase-awal, dicatat provisional di
docs/keputusan-tertunda.md #5.
"""

from pydantic import BaseModel

from src.schemas.interpretation import DataVisualisasi


class TurnResponse(BaseModel):
    session_id: str
    turn_index: int
    narasi: str
    terverifikasi: bool
    catatan_verifikasi: str | None
    visualisasi: list[DataVisualisasi] | None
