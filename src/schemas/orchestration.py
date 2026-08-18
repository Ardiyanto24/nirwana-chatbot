"""Skema akumulator state turn PIC 7 Level 2 (Milestone 7.6+).

`KeadaanTurn` tumbuh field-demi-field tiap milestone Sambungan (M7.7-7.16
menambah field sendiri sesuai kebutuhan cabangnya) - BUKAN tuple yang terus
membesar/bersarang across 11 langkah berurutan. Kedua field M7.6 non-Optional:
baik `ValidationError` (Input Layer) maupun `APIError` (Pemetaan Ketergantungan
Turn) adalah exception keras yang menjalar keluar `proses_turn()`, bukan nilai
terdegradasi yang disimpan di sini. Lihat
milestones/7.6-sambungan-input-layer-pemetaan-ketergantungan/decisions.md
Keputusan 2.
"""

from pydantic import BaseModel

from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload


class KeadaanTurn(BaseModel):
    payload: TurnPayload
    ketergantungan: TurnDependencyResult
