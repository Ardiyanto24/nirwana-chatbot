"""Skema hasil deteksi ketergantungan turn (Milestone 1.3).

`session_id` sengaja TIDAK diminta dari LLM - rujukan selalu dalam sesi yang
sama (kontrak arsitektur induk SS4, Langkah 2), jadi kode yang menempelkannya
setelah hasil LLM diterima, bukan LLM yang menentukan. Mengurangi risiko
halusinasi session_id yang sebenarnya tidak relevan.
"""

from pydantic import BaseModel


class TurnDependencyResult(BaseModel):
    is_dependent: bool
    referenced_turn_index: int | None = None
