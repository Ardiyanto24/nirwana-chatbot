"""Test suite Pencocokan Atomic Intent x Data Session Memory (Milestone 1.7)
- panggilan LLM+database NYATA (tidak di-mock, konsisten prinsip verifikasi
proyek), membuktikan ketiga Kriteria Keberhasilan sumber.

Data "seakan-akan sudah dieksekusi" disuntik manual lewat store_session_
memory() - session memory belum organik (Execution/M4.5 belum dibangun),
lihat decisions.md Keputusan 13. Test data pakai session_id berprefix
"test-" + teardown eksplisit, mirror pola test_session_memory.py (M1.5).

Di-skip otomatis kalau OPENROUTER_API_KEY atau DATABASE_URL tidak tersedia.
"""

import os
import uuid

import pytest
from sqlmodel import Session, text

from src.config.database import get_engine
from src.layers.context_resolution.matching import match_and_archive
from src.layers.context_resolution.session_memory import (
    retrieve_session_memory,
    store_session_memory,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.matching import MatchStatus
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY") or not os.environ.get("DATABASE_URL"),
    reason="OPENROUTER_API_KEY/DATABASE_URL tidak diset - skip test yang butuh "
    "panggilan LLM+database nyata",
)


def _cleanup(session_id: str) -> None:
    with Session(get_engine()) as session:
        session.exec(
            text(
                "DELETE FROM session_memory_packages WHERE session_id = :sid"
            ).bindparams(sid=session_id)
        )
        session.commit()


def _seed_paket(
    session_id: str, turn_index: int, teks_kebutuhan: str
) -> SessionMemoryPackage:
    paket = SessionMemoryPackage(
        atomic_intent_id=str(uuid.uuid4()),
        session_id=session_id,
        turn_index=turn_index,
        teks_kebutuhan=teks_kebutuhan,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"value": 82.5, "unit": "percent"},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )
    store_session_memory(paket)
    return paket


def test_kelompok_a_intent_sudah_tersimpan_dicocokkan_tidak_dieksekusi_ulang():
    # Skenario uji dokumen sumber: "occupancy April 2026" yang memang sudah
    # dihitung dan tersimpan, dirujuk ulang di turn berikutnya.
    session_id = "test-m17-kelompok-a"
    try:
        paket_asal = _seed_paket(
            session_id, turn_index=3, teks_kebutuhan="occupancy rate bulan April 2026"
        )

        atomic_intent_baru = AtomicIntent(
            atomic_intent_id=str(uuid.uuid4()),
            teks_kebutuhan="berapa occupancy April 2026",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
        )
        candidates = retrieve_session_memory(session_id, 3)
        matches = match_and_archive(
            [atomic_intent_baru], candidates, session_id, turn_index=5
        )

        assert matches[0].status == MatchStatus.SELESAI, (
            "harus cocok, TIDAK dieksekusi ulang"
        )
        assert matches[0].paket is not None
        assert matches[0].paket.nilai_hasil == paket_asal.nilai_hasil
        assert matches[0].paket.atomic_intent_id == paket_asal.atomic_intent_id
    finally:
        _cleanup(session_id)


def test_kelompok_b_intent_baru_tidak_pernah_cocok_keliru():
    # Kebutuhan atomik yang benar-benar baru (topik tidak berkaitan dengan
    # kandidat manapun) tidak pernah tercocokkan secara keliru.
    session_id = "test-m17-kelompok-b"
    try:
        _seed_paket(
            session_id, turn_index=3, teks_kebutuhan="occupancy rate bulan April 2026"
        )

        atomic_intent_baru = AtomicIntent(
            atomic_intent_id=str(uuid.uuid4()),
            teks_kebutuhan="berapa jumlah staff yang resign bulan Juni 2026",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
        )
        candidates = retrieve_session_memory(session_id, 3)
        matches = match_and_archive(
            [atomic_intent_baru], candidates, session_id, turn_index=5
        )

        assert matches[0].status == MatchStatus.PERLU_EKSEKUSI, (
            "topik tidak berkaitan, TIDAK boleh cocok"
        )
        assert matches[0].paket is None
    finally:
        _cleanup(session_id)


def test_kelompok_c_rantai_arsip_ulang_turn_tujuh_lima_tiga():
    # Skenario uji dokumen sumber: turn ketujuh merujuk hasil turn kelima, di
    # mana hasil itu sendiri sebenarnya berasal dari turn ketiga. Dibuktikan
    # lewat DUA pemanggilan match_and_archive() NYATA berantai (bukan dua
    # fixture independen) - lihat decisions.md Keputusan 13.
    session_id = "test-m17-kelompok-c"
    try:
        paket_asal = _seed_paket(
            session_id, turn_index=3, teks_kebutuhan="occupancy rate bulan April 2026"
        )

        # Hop 1: turn 5 merujuk turn 3
        ai_turn5 = AtomicIntent(
            atomic_intent_id=str(uuid.uuid4()),
            teks_kebutuhan="berapa occupancy April 2026",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
        )
        candidates_turn3 = retrieve_session_memory(session_id, 3)
        matches_turn5 = match_and_archive(
            [ai_turn5], candidates_turn3, session_id, turn_index=5
        )
        assert matches_turn5[0].status == MatchStatus.SELESAI

        # Hop 2: turn 7 merujuk turn 5, MEMAKAI baris arsip nyata hasil hop 1
        ai_turn7 = AtomicIntent(
            atomic_intent_id=str(uuid.uuid4()),
            teks_kebutuhan="berapa occupancy April 2026 kemarin",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
        )
        candidates_turn5 = retrieve_session_memory(session_id, 5)
        assert len(candidates_turn5) == 1, "harus menemukan baris arsip hasil hop 1"
        matches_turn7 = match_and_archive(
            [ai_turn7], candidates_turn5, session_id, turn_index=7
        )

        assert matches_turn7[0].status == MatchStatus.SELESAI

        rows_turn7 = retrieve_session_memory(session_id, 7)
        assert len(rows_turn7) == 1
        arsip_turn7 = rows_turn7[0]
        assert arsip_turn7.atomic_intent_id == paket_asal.atomic_intent_id
        assert arsip_turn7.sumber == "session_memory (turn 3)", (
            "rantai sumber harus tetap menunjuk turn PALING ASAL (turn 3), "
            "tidak putus di turn 5 (arsip perantara)"
        )
        assert arsip_turn7.nilai_hasil == paket_asal.nilai_hasil
    finally:
        _cleanup(session_id)
