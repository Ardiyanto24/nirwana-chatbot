"""Test suite Penyimpanan dan Pengambilan Session Memory (Milestone 1.5) -
panggilan database NYATA ke Supabase (tidak di-mock, konsisten prinsip
verifikasi proyek), membuktikan kedua Kriteria Keberhasilan sumber.

Test data pakai session_id berprefix "test-" + teardown eksplisit supaya
Supabase (dipakai jangka panjang juga untuk M5/M6) tidak kotor sisa data uji.

Di-skip otomatis kalau `DATABASE_URL` tidak tersedia di environment.

Skenario KEGAGALAN store (span memory.store error.type, Milestone 4.3
Checkpoint 2) murni mocked - TIDAK butuh DATABASE_URL, sengaja dipisah ke
test_session_memory_kegagalan.py supaya tidak ikut ter-skip modul ini.
"""

import os

import pytest
from sqlmodel import Session, text

from src.config.database import get_engine
from src.layers.context_resolution.session_memory import (
    retrieve_session_memory,
    store_session_memory,
)
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL tidak diset - skip test yang butuh koneksi database nyata",
)


def _cleanup(session_id: str) -> None:
    with Session(get_engine()) as session:
        session.exec(
            text("DELETE FROM session_memory_packages WHERE session_id = :sid").bindparams(
                sid=session_id
            )
        )
        session.commit()


def test_kelompok_a_simpan_lalu_ambil_kembali_identik():
    session_id = "test-kelompok-a"
    package = SessionMemoryPackage(
        atomic_intent_id="test-atomic-a",
        session_id=session_id,
        turn_index=1,
        teks_kebutuhan="Berapa revenue reservasi bulan Maret 2026?",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"value": 800_000_000, "unit": "IDR"},
        catatan_interpretasi=["data lengkap"],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )
    try:
        store_session_memory(package)
        results = retrieve_session_memory(session_id, 1)
        assert len(results) == 1
        assert results[0] == package
    finally:
        _cleanup(session_id)


def test_kelompok_b_turn_tidak_ada_mengembalikan_list_kosong():
    session_id = "test-kelompok-b"
    results = retrieve_session_memory(session_id, 1)
    assert results == []
