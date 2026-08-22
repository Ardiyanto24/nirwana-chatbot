"""Test suite skenario kegagalan teknis `detect_turn_dependency()`
(Milestone 1.3, addendum ditemukan Milestone 7.6 2026-08-18) - span
`chat` harus mencatat `dependency.forced_independent_reason` saat
`_call_llm()` gagal teknis (`openai.APIError`), LALU fungsi tetap
mengembalikan `TurnDependencyResult(is_dependent=False)` (fallback
aman, mirror pola bounds-check/parse-error yang sudah ada), BUKAN
melempar exception yang tidak tertangani.

Murni mocked (`_call_llm` di-monkeypatch) - SENGAJA dipisah dari
test_turn_dependency.py (yang murni LLM sungguhan, di-skip otomatis
tanpa `OPENROUTER_API_KEY`) supaya test ini tetap jalan tanpa API key,
mirror pola test_session_memory_kegagalan.py.

Lihat milestones/1.3-pemetaan-ketergantungan-turn/decisions.md Addendum
dan docs/keterbatasan-diterima.md #14 (status: DIPERBAIKI).
"""

import uuid

from openai import APIError

import src.layers.context_resolution.turn_dependency as modul
from src.layers.context_resolution.turn_dependency import detect_turn_dependency
from src.schemas.turn_payload import HistoryTurn, TurnPayload


def _buat_payload() -> TurnPayload:
    return TurnPayload(
        session_id=f"test-{uuid.uuid4()}",
        turn_index=2,
        role_title="CEO",
        employee_id="emp-1",
        question="Bandingkan dengan bulan sebelumnya.",
        history=[
            HistoryTurn(
                turn_index=1,
                question="Berapa revenue reservasi bulan Maret 2026?",
                answer="Revenue reservasi Maret 2026 sebesar Rp 800 juta.",
            )
        ],
    )


class _SpanRekam:
    def __init__(self):
        self.atribut: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, key, value):
        self.atribut[key] = value


class _TracerRekam:
    def __init__(self):
        self.span = _SpanRekam()

    def start_as_current_span(self, nama):
        return self.span


def test_api_error_fallback_aman_tanpa_exception_menjalar(monkeypatch):
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)

    def _raise(payload):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(modul, "_call_llm", _raise)

    result = detect_turn_dependency(_buat_payload())

    assert result.is_dependent is False
    assert result.referenced_turn_index is None
    assert (
        "api_error" in tracer_rekam.span.atribut["dependency.forced_independent_reason"]
    )
