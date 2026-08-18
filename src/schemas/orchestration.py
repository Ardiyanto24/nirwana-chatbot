"""Skema akumulator state turn PIC 7 Level 2 (Milestone 7.6+).

`KeadaanTurn` tumbuh field-demi-field tiap milestone Sambungan (M7.8-7.16
menambah field sendiri sesuai kebutuhan cabangnya) - BUKAN tuple yang terus
membesar/bersarang across 11 langkah berurutan. Field M7.6 (`payload`,
`ketergantungan`) non-Optional: baik `ValidationError` (Input Layer) maupun
`APIError` (Pemetaan Ketergantungan Turn) adalah exception keras yang
menjalar keluar `proses_turn()`, bukan nilai terdegradasi yang disimpan di
sini. Lihat
milestones/7.6-sambungan-input-layer-pemetaan-ketergantungan/decisions.md
Keputusan 2.

Field M7.7 (`rewrite`, `session_memory`): `rewrite` selalu terisi
(`rewrite_to_standalone()` py fallback penuh, tidak pernah raise).
`session_memory` membedakan `None` (Tarik Memory tidak pernah dipanggil -
tidak ada referensi terdeteksi) dari `[]` (dipanggil, genuinely tidak
menemukan data) - forced KK M7.7 eksplisit. Lihat
milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/
decisions.md Keputusan 3.
"""

from pydantic import BaseModel

from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import SessionMemoryPackage
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload


class KeadaanTurn(BaseModel):
    payload: TurnPayload
    ketergantungan: TurnDependencyResult
    rewrite: RewriteResult
    session_memory: list[SessionMemoryPackage] | None
