"""Test suite `simpan_riwayat_turn()` (Milestone 7.18) - panggilan
database NYATA ke Supabase (tidak di-mock, konsisten prinsip verifikasi
proyek), membuktikan KK1 sumber ("bisa ditarik kembali dan cocok dengan
apa yang sesungguhnya ditanyakan dan dijawab").

Tidak ada fungsi retrieve produksi (decisions.md Keputusan 6) - baca
balik lewat query SQLModel langsung, mirror pola verifikasi eval.

Test data pakai session_id berprefix "test-" + teardown eksplisit.
Di-skip otomatis kalau `DATABASE_URL` tidak tersedia di environment.

Skenario KEGAGALAN dan test murni `tentukan_status_keseluruhan_turn()`
(tanpa DB) SENGAJA dipisah ke test_riwayat_percakapan_kegagalan.py
supaya tidak ikut ter-skip modul ini.
"""

import os

import pytest
from sqlmodel import Session, select, text

from src.config.database import get_engine
from src.db.models import ConversationTurnRow
from src.orchestration.riwayat_percakapan import simpan_riwayat_turn

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL tidak diset - skip test yang butuh koneksi database nyata",
)


def _cleanup(session_id: str) -> None:
    with Session(get_engine()) as session:
        session.exec(
            text("DELETE FROM conversation_turns WHERE session_id = :sid").bindparams(
                sid=session_id
            )
        )
        session.commit()


def test_simpan_lalu_baca_balik_cocok_dengan_yang_ditanyakan_dijawab():
    session_id = "test-riwayat-a"
    try:
        simpan_riwayat_turn(
            session_id=session_id,
            turn_index=1,
            pertanyaan="Berapa occupancy rate properti kita bulan Juni 2026?",
            narasi="Occupancy rate Juni 2026 tercatat 78%.",
            status="berhasil",
        )

        with Session(get_engine()) as session:
            rows = session.exec(
                select(ConversationTurnRow).where(
                    ConversationTurnRow.session_id == session_id
                )
            ).all()

        assert len(rows) == 1
        assert rows[0].turn_index == 1
        assert (
            rows[0].pertanyaan == "Berapa occupancy rate properti kita bulan Juni 2026?"
        )
        assert rows[0].narasi == "Occupancy rate Juni 2026 tercatat 78%."
        assert rows[0].status == "berhasil"
        assert rows[0].created_at is not None
    finally:
        _cleanup(session_id)


def test_simpan_dua_turn_beda_turn_index_tidak_tertukar():
    session_id = "test-riwayat-b"
    try:
        simpan_riwayat_turn(
            session_id=session_id,
            turn_index=1,
            pertanyaan="pertanyaan turn 1",
            narasi="narasi turn 1",
            status="berhasil",
        )
        simpan_riwayat_turn(
            session_id=session_id,
            turn_index=2,
            pertanyaan="pertanyaan turn 2",
            narasi="narasi turn 2",
            status="campuran",
        )

        with Session(get_engine()) as session:
            rows = session.exec(
                select(ConversationTurnRow)
                .where(ConversationTurnRow.session_id == session_id)
                .order_by(ConversationTurnRow.turn_index)
            ).all()

        assert len(rows) == 2
        assert rows[0].turn_index == 1 and rows[0].status == "berhasil"
        assert rows[1].turn_index == 2 and rows[1].status == "campuran"
    finally:
        _cleanup(session_id)
