"""Test suite Penulisan Ulang Pertanyaan Jadi Mandiri (Milestone 1.4) —
panggilan LLM NYATA (tidak di-mock, konsisten prinsip verifikasi proyek sejak
Milestone 1.1), membuktikan kedua Kriteria Keberhasilan sumber lewat 2
kelompok skenario.

Di-skip otomatis kalau `OPENROUTER_API_KEY` tidak tersedia di environment.
"""

import os

import pytest

from src.layers.context_resolution.rewrite import rewrite_to_standalone
from src.schemas.turn_payload import HistoryTurn, TurnPayload

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


def test_kelompok_a_elipsis_diresolusi_jadi_eksplisit():
    payload = TurnPayload(
        session_id="test-kelompok-a",
        turn_index=2,
        role_title="General Manager",
        employee_id="emp-a",
        question="Bandingkan dengan occupancy satu tahun sebelumnya.",
        history=[
            HistoryTurn(
                turn_index=1,
                question="Berapa occupancy rate bulan April 2026?",
                answer="Occupancy April 2026 mencapai 78%.",
            )
        ],
    )
    result = rewrite_to_standalone(payload)
    rewritten = result.rewritten_question.lower()
    assert "april" in rewritten
    assert "2025" in rewritten, (
        f"'satu tahun sebelumnya' dari April 2026 harus diresolusi jadi April "
        f"2025 secara eksplisit - didapat {result.rewritten_question!r}"
    )


def test_kelompok_b_sudah_mandiri_diteruskan_tanpa_distorsi():
    payload = TurnPayload(
        session_id="test-kelompok-b",
        turn_index=1,
        role_title="Corporate Revenue Director",
        employee_id="emp-b",
        question="Berapa revenue reservasi bulan Maret 2026?",
        history=[],
    )
    result = rewrite_to_standalone(payload)
    rewritten = result.rewritten_question.lower()
    assert "maret" in rewritten
    assert "2026" in rewritten
    assert "reservasi" in rewritten
