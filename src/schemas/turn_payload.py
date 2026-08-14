"""Skema payload satu turn percakapan dari frontend (Input Layer, Milestone 1.2).

Bentuk field mengikuti kontrak arsitektur induk §4: `session_id`, `turn_index`,
`role_title`, `employee_id`, teks pertanyaan turn ini, + teks & jawaban turn
sebelumnya kalau `turn_index > 1`.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Self

from src.config.roles import load_valid_roles


class PreviousTurn(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class TurnPayload(BaseModel):
    session_id: str = Field(min_length=1)
    turn_index: int = Field(ge=1)
    role_title: str = Field(min_length=1)
    employee_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    previous_turn: PreviousTurn | None = None

    @field_validator("role_title")
    @classmethod
    def role_title_must_be_known(cls, v: str) -> str:
        if v not in load_valid_roles():
            raise ValueError(f"role_title tidak dikenal: {v!r}")
        return v

    @model_validator(mode="after")
    def previous_turn_required_when_not_first_turn(self) -> Self:
        if self.turn_index > 1 and self.previous_turn is None:
            raise ValueError("previous_turn wajib diisi kalau turn_index > 1")
        return self
