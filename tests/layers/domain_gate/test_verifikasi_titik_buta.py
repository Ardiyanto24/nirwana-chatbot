"""Test suite Verifikasi Titik Buta (Milestone 2.1, Langkah 2).

Dua kelompok test - sama pola dengan test_identifikasi.py:
- Pure-function (_parse_and_decide): deterministik, TIDAK butuh LLM.
- Panggilan LLM NYATA (verifikasi_titik_buta end-to-end, termasuk KK2 -
  domain sengaja dihilangkan dari domain_awal): di-skip kalau
  OPENROUTER_API_KEY tidak tersedia.
"""

import os
import uuid

import pytest

from src.layers.domain_gate.verifikasi_titik_buta import (
    _parse_and_decide,
    verifikasi_titik_buta,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
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


def test_parse_and_decide_menemukan_domain_tambahan():
    result, alasan = _parse_and_decide('{"domain_tambahan": ["financial"]}')
    assert result.gagal is False
    assert result.domain_tambahan == [Domain.FINANCIAL]
    assert alasan is None


def test_parse_and_decide_tidak_menemukan_apa_pun_bukan_anomali():
    result, alasan = _parse_and_decide('{"domain_tambahan": []}')
    assert result.gagal is False
    assert result.domain_tambahan == []
    assert alasan is None


def test_parse_and_decide_json_rusak():
    result, alasan = _parse_and_decide("bukan json")
    assert result.gagal is True
    assert result.domain_tambahan == []
    assert alasan is not None and "parse_error" in alasan


def test_parse_and_decide_domain_hallucinated_di_drop():
    result, alasan = _parse_and_decide('{"domain_tambahan": ["guests", "hr"]}')
    assert result.gagal is False
    assert result.domain_tambahan == [Domain.HR]
    assert alasan is not None and "dropped_invalid_domains" in alasan


# --- Panggilan LLM nyata -----------------------------------------------------

pytestmark_llm = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


@pytestmark_llm
def test_kelompok_a_kk2_menangkap_domain_sengaja_dihilangkan():
    """KK2: domain_awal SENGAJA dibuat tidak lengkap (hanya reservation,
    padahal pertanyaan eksplisit menyebut gop_margin/financial) - verifikasi
    titik buta harus menangkap financial sebagai domain_tambahan."""
    atomic_intent = _buat_atomic_intent(
        "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"
    )
    result = verifikasi_titik_buta(atomic_intent, domain_awal=[Domain.RESERVATION])
    assert result.gagal is False
    assert Domain.FINANCIAL in result.domain_tambahan


@pytestmark_llm
def test_kelompok_b_guard_anti_false_positive_domain_awal_lengkap():
    """Guard anti-false-positive: kalau domain_awal SUDAH lengkap, verifikasi
    titik buta seharusnya TIDAK menambah domain palsu."""
    atomic_intent = _buat_atomic_intent("Berapa okupansi kamar bulan ini?")
    result = verifikasi_titik_buta(atomic_intent, domain_awal=[Domain.RESERVATION])
    assert result.gagal is False
    assert result.domain_tambahan == []
