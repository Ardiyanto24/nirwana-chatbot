"""Skema hasil penulisan ulang pertanyaan jadi mandiri (Milestone 1.4).

Satu field string - LLM dipanggil tanpa response_format=json_object (beda dari
turn_dependency.py M1.3 yang punya 2 field), lihat decisions.md Keputusan 5.
"""

from pydantic import BaseModel


class RewriteResult(BaseModel):
    rewritten_question: str
