"""Test suite Pemetaan Ketergantungan Turn (Milestone 1.3) — panggilan LLM
NYATA (tidak di-mock, konsisten prinsip verifikasi proyek sejak Milestone 1.1),
membuktikan ketiga Kriteria Keberhasilan sumber lewat 3 kelompok skenario.

Di-skip otomatis kalau `OPENROUTER_API_KEY` tidak tersedia di environment.
"""

import os

import pytest

from src.layers.context_resolution.turn_dependency import detect_turn_dependency
from src.schemas.turn_payload import HistoryTurn, TurnPayload

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


def test_kelompok_a_rujukan_eksplisit_ke_turn_sebelumnya():
    payload = TurnPayload(
        session_id="test-kelompok-a",
        turn_index=2,
        role_title="Corporate Revenue Director",
        employee_id="emp-a",
        question="Bandingkan dengan bulan sebelumnya.",
        history=[
            HistoryTurn(
                turn_index=1,
                question="Berapa revenue reservasi bulan Maret 2026?",
                answer="Revenue reservasi Maret 2026 sebesar Rp 800 juta.",
            )
        ],
    )
    result = detect_turn_dependency(payload)
    assert result.is_dependent is True
    assert result.referenced_turn_index == 1


def test_kelompok_b_berdiri_sendiri_tanpa_rujukan():
    payload = TurnPayload(
        session_id="test-kelompok-b",
        turn_index=2,
        role_title="HR Manager",
        employee_id="emp-b",
        question="Apa saja fasilitas yang tersedia di area spa?",
        history=[
            HistoryTurn(
                turn_index=1,
                question="Berapa jumlah staff aktif di departemen HR?",
                answer="Departemen HR memiliki 8 staff aktif.",
            )
        ],
    )
    result = detect_turn_dependency(payload)
    assert result.is_dependent is False
    assert result.referenced_turn_index is None


def test_kelompok_c_rujukan_ke_turn_jauh_bukan_terdekat():
    history = [
        HistoryTurn(
            turn_index=1,
            question="Berapa occupancy rate properti kita bulan April 2026?",
            answer="Occupancy April 2026 mencapai 78%.",
        ),
        HistoryTurn(
            turn_index=2,
            question="Bagaimana dengan revenue F&B bulan yang sama?",
            answer="Revenue F&B April 2026 sebesar Rp 450 juta.",
        ),
        HistoryTurn(
            turn_index=3,
            question="Berapa banyak komplain yang diterima housekeeping bulan ini?",
            answer="Housekeeping menerima 12 komplain di April 2026, mayoritas soal kebersihan kamar.",
        ),
        HistoryTurn(
            turn_index=4,
            question="Bagaimana kondisi maintenance AC di lantai 3?",
            answer="3 unit AC di lantai 3 sedang dalam perbaikan, estimasi selesai minggu depan.",
        ),
        HistoryTurn(
            turn_index=5,
            question="Berapa booking spa yang masuk minggu ini?",
            answer="Spa menerima 45 booking minggu ini, naik 10% dari minggu lalu.",
        ),
        HistoryTurn(
            turn_index=6,
            question="Siapa staff dengan performa terbaik bulan ini?",
            answer="Staff Front Office bernama Sari mencatat rating kepuasan tamu tertinggi bulan ini.",
        ),
    ]
    payload = TurnPayload(
        session_id="test-kelompok-c",
        turn_index=7,
        role_title="Housekeeping Manager",
        employee_id="emp-c",
        question="Balik lagi ke soal komplain housekeeping tadi, apa tindak lanjutnya?",
        history=history,
    )
    result = detect_turn_dependency(payload)
    assert result.is_dependent is True
    assert result.referenced_turn_index == 3, (
        f"seharusnya merujuk turn 3 (komplain housekeeping), bukan turn terdekat "
        f"(6) atau turn lain - didapat {result.referenced_turn_index}"
    )
