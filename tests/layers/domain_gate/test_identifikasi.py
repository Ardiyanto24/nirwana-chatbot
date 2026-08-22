"""Test suite Identifikasi Domain Awal (Milestone 2.1, Langkah 1).

Dua kelompok test:
- Pure-function (bounds_check_domains, _parse_and_decide): deterministik,
  TIDAK butuh LLM/API key, selalu jalan - konsisten pemisahan parsing dari
  panggilan API (matching.py M1.7).
- Panggilan LLM NYATA (identifikasi_domain end-to-end): konsisten prinsip
  verifikasi proyek (test_matching.py/test_decompose.py, tidak di-mock),
  di-skip otomatis kalau OPENROUTER_API_KEY tidak tersedia.
"""

import os
import uuid

import pytest

from src.layers.domain_gate.identifikasi import (
    _parse_and_decide,
    bounds_check_domains,
    identifikasi_domain,
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


# --- Pure-function: bounds_check_domains -----------------------------------


def test_bounds_check_seluruh_domain_valid():
    valid, invalid = bounds_check_domains(["reservation", "financial"])
    assert valid == [Domain.RESERVATION, Domain.FINANCIAL]
    assert invalid == []


def test_bounds_check_domain_hallucinated_di_drop():
    valid, invalid = bounds_check_domains(["reservation", "guests"])
    assert valid == [Domain.RESERVATION]
    assert invalid == ["guests"]


def test_bounds_check_seluruh_domain_hallucinated():
    valid, invalid = bounds_check_domains(["corporate_master", "payroll"])
    assert valid == []
    assert invalid == ["corporate_master", "payroll"]


# --- Pure-function: _parse_and_decide ---------------------------------------


def test_parse_and_decide_respons_valid_dua_domain():
    result, alasan = _parse_and_decide('{"domains": ["reservation", "financial"]}')
    assert result.gagal is False
    assert set(result.domains) == {Domain.RESERVATION, Domain.FINANCIAL}
    assert alasan is None


def test_parse_and_decide_json_rusak():
    result, alasan = _parse_and_decide("bukan json valid")
    assert result.gagal is True
    assert result.domains == []
    assert alasan is not None and "parse_error" in alasan


def test_parse_and_decide_seluruh_domain_hallucinated_dipaksa_gagal():
    result, alasan = _parse_and_decide('{"domains": ["guests"]}')
    assert result.gagal is True
    assert result.domains == []
    assert alasan is not None and "tidak_ada_domain_valid" in alasan


def test_parse_and_decide_sebagian_hallucinated_tetap_lolos_dengan_anomali():
    result, alasan = _parse_and_decide('{"domains": ["reservation", "guests"]}')
    assert result.gagal is False
    assert result.domains == [Domain.RESERVATION]
    assert alasan is not None and "dropped_invalid_domains" in alasan


# --- Panggilan LLM nyata -----------------------------------------------------

pytestmark_llm = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


@pytestmark_llm
def test_kelompok_a_leakage_gop_margin_kenali_dua_domain():
    atomic_intent = _buat_atomic_intent(
        "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"
    )
    result = identifikasi_domain(atomic_intent)
    assert result.gagal is False
    assert Domain.RESERVATION in result.domains
    assert Domain.FINANCIAL in result.domains


@pytestmark_llm
def test_kelompok_b_guests_pii_kontak_tamu():
    atomic_intent = _buat_atomic_intent("Beri saya data kontak Bapak Herman.")
    result = identifikasi_domain(atomic_intent)
    assert result.gagal is False
    assert Domain.GUESTS_PII in result.domains
    assert Domain.GUESTS_PROFILE not in result.domains


@pytestmark_llm
def test_kelompok_c_guests_profile_nationality_mix():
    atomic_intent = _buat_atomic_intent("Berapa nationality mix tamu bulan ini?")
    result = identifikasi_domain(atomic_intent)
    assert result.gagal is False
    assert Domain.GUESTS_PROFILE in result.domains
    assert Domain.GUESTS_PII not in result.domains


@pytestmark_llm
def test_kelompok_d_baseline_domain_tunggal_tanpa_ambiguitas():
    atomic_intent = _buat_atomic_intent("Berapa okupansi kamar bulan ini?")
    result = identifikasi_domain(atomic_intent)
    assert result.gagal is False
    assert result.domains == [Domain.RESERVATION]


def test_sengaja_gagal_percobaan_gate_m8_2_domain_gate():
    """Percobaan Checkpoint 10 Milestone 8.2 - membuktikan test-python-llm
    genuinely path-filtered ke grup domain_gate. Dihapus setelah bukti
    didapat, TIDAK PERNAH masuk main."""
    assert 1 == 2, "sengaja gagal untuk percobaan Checkpoint 10 M8.2"
