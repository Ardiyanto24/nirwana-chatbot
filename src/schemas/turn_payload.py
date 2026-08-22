"""Skema payload satu turn percakapan dari frontend (Input Layer, Milestone 1.2).

Bentuk field mengikuti kontrak arsitektur induk §4: `session_id`, `turn_index`,
`role_title`, `employee_id`, teks pertanyaan turn ini, + seluruh histori
turn-turn sebelumnya dalam sesi kalau `turn_index > 1`.

Direvisi di Milestone 1.3: desain awal (Milestone 1.2) hanya membawa satu turn
sebelumnya (N-1). Kriteria Keberhasilan Milestone 1.3 menuntut deteksi rujukan
ke turn yang jauh lebih lama, sementara Langkah 2 (Pemetaan Ketergantungan
Turn) belum boleh membaca session memory - histori penuh di payload jadi
satu-satunya sumber data yang memungkinkan itu. Lihat
milestones/1.3-pemetaan-ketergantungan-turn/decisions.md.
"""

from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.config.roles import load_valid_roles


class HistoryTurn(BaseModel):
    turn_index: int = Field(ge=1)
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class TurnPayload(BaseModel):
    session_id: str = Field(min_length=1)
    turn_index: int = Field(ge=1)
    role_title: str = Field(min_length=1)
    employee_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    history: list[HistoryTurn] = Field(default_factory=list)

    @field_validator("role_title")
    @classmethod
    def role_title_must_be_known(cls, v: str) -> str:
        if v not in load_valid_roles():
            raise ValueError(f"role_title tidak dikenal: {v!r}")
        return v

    @model_validator(mode="after")
    def history_matches_turn_index(self) -> Self:
        if self.turn_index > 1:
            expected = set(range(1, self.turn_index))
            actual = {h.turn_index for h in self.history}
            if actual != expected:
                raise ValueError(
                    f"history harus berisi tepat turn_index {sorted(expected)} "
                    f"(satu entri per turn sebelumnya, tanpa gap/duplikat), "
                    f"ditemukan {sorted(actual)}"
                )
        return self
