"""Test suite Verifikasi Titik Buta Constraint Cakupan-Individu (Milestone
2.3, Langkah 2).

Dua kelompok test - sama pola dengan test_verifikasi_titik_buta.py (M2.1):
pure-function (_parse_and_decide) dan panggilan LLM NYATA (termasuk
skenario titik-buta terkontrol - terdeteksi_awal sengaja diset False),
di-skip kalau OPENROUTER_API_KEY tidak tersedia.
"""

import os
import uuid

import pytest

from src.layers.domain_gate.verifikasi_cakupan_individu import (
    _parse_and_decide,
    verifikasi_cakupan_individu,
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


def test_parse_and_decide_terdeteksi_tambahan_true():
    result, alasan = _parse_and_decide('{"terdeteksi_tambahan": true}')
    assert result.gagal is False
    assert result.terdeteksi_tambahan is True
    assert alasan is None


def test_parse_and_decide_terdeteksi_tambahan_false():
    result, alasan = _parse_and_decide('{"terdeteksi_tambahan": false}')
    assert result.gagal is False
    assert result.terdeteksi_tambahan is False
    assert alasan is None


def test_parse_and_decide_json_rusak():
    result, alasan = _parse_and_decide("bukan json")
    assert result.gagal is True
    assert result.terdeteksi_tambahan is False
    assert alasan is not None and "parse_error" in alasan


# --- Panggilan LLM nyata -----------------------------------------------------

pytestmark_llm = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


@pytestmark_llm
def test_titik_buta_menangkap_terdeteksi_awal_sengaja_salah():
    """Skenario terkontrol: terdeteksi_awal SENGAJA diset False padahal
    pertanyaan eksplisit menyentuh performa individu - verifikasi titik
    buta harus menangkapnya sebagai terdeteksi_tambahan=True."""
    atomic_intent = _buat_atomic_intent("Siapa staf tercepat bulan ini?")
    result = verifikasi_cakupan_individu(atomic_intent, terdeteksi_awal=False)
    assert result.gagal is False
    assert result.terdeteksi_tambahan is True


@pytestmark_llm
def test_guard_anti_false_positive_kebutuhan_genuinely_agregat():
    """Guard anti-false-positive: kebutuhan genuinely agregat, terdeteksi_awal
    sudah benar False - verifikasi titik buta seharusnya TIDAK menambah
    positif palsu."""
    atomic_intent = _buat_atomic_intent("Berapa staf hadir hari ini?")
    result = verifikasi_cakupan_individu(atomic_intent, terdeteksi_awal=False)
    assert result.gagal is False
    assert result.terdeteksi_tambahan is False
