"""Test suite Deteksi Awal Constraint Cakupan-Individu (Milestone 2.3,
Langkah 1).

Dua kelompok test: pure-function (_parse_and_decide, deterministik, tidak
butuh API key) dan panggilan LLM NYATA (deteksi_cakupan_individu end-to-end,
tidak di-mock, di-skip otomatis kalau OPENROUTER_API_KEY tidak tersedia).
"""

import os
import uuid

import pytest

from src.layers.domain_gate.deteksi_cakupan_individu import (
    _parse_and_decide,
    deteksi_cakupan_individu,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban


def _buat_atomic_intent(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )


# --- Pure-function: _parse_and_decide ---------------------------------------


def test_parse_and_decide_terdeteksi_true():
    result, alasan = _parse_and_decide('{"terdeteksi": true}')
    assert result.gagal is False
    assert result.terdeteksi is True
    assert alasan is None


def test_parse_and_decide_terdeteksi_false():
    result, alasan = _parse_and_decide('{"terdeteksi": false}')
    assert result.gagal is False
    assert result.terdeteksi is False
    assert alasan is None


def test_parse_and_decide_json_rusak():
    result, alasan = _parse_and_decide("bukan json valid")
    assert result.gagal is True
    assert result.terdeteksi is False
    assert alasan is not None and "parse_error" in alasan


# --- Panggilan LLM nyata -----------------------------------------------------

pytestmark_llm = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


@pytestmark_llm
def test_kasus_jelas_individu_performa_staf_tertentu():
    atomic_intent = _buat_atomic_intent(
        "Bagaimana performa staf housekeeping Budi bulan ini?"
    )
    result = deteksi_cakupan_individu(atomic_intent)
    assert result.gagal is False
    assert result.terdeteksi is True


@pytestmark_llm
def test_kasus_jelas_individu_ranking_staf_tercepat():
    atomic_intent = _buat_atomic_intent("Siapa staf tercepat bulan ini?")
    result = deteksi_cakupan_individu(atomic_intent)
    assert result.gagal is False
    assert result.terdeteksi is True


@pytestmark_llm
def test_kasus_jelas_agregat_jumlah_staf_hadir():
    atomic_intent = _buat_atomic_intent("Berapa staf hadir hari ini?")
    result = deteksi_cakupan_individu(atomic_intent)
    assert result.gagal is False
    assert result.terdeteksi is False


@pytestmark_llm
def test_kasus_jelas_agregat_rata_rata_departemen():
    atomic_intent = _buat_atomic_intent(
        "Berapa rata-rata skor kinerja departemen housekeeping?"
    )
    result = deteksi_cakupan_individu(atomic_intent)
    assert result.gagal is False
    assert result.terdeteksi is False


@pytestmark_llm
def test_kasus_di_luar_domain_facility_hr():
    atomic_intent = _buat_atomic_intent("Berapa okupansi kamar bulan ini?")
    result = deteksi_cakupan_individu(atomic_intent)
    assert result.gagal is False
    assert result.terdeteksi is False
