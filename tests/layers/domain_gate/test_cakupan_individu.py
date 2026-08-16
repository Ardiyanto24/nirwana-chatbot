"""Test suite Deteksi Constraint Cakupan-Individu (Milestone 2.3).

File ini dibangun bertahap lintas checkpoint (preseden pola M2.2 CP4->CP5):
- Checkpoint 2 (Task 3): unit test validator ConstraintCakupanIndividu -
  murni pydantic, TANPA DATABASE_URL/OPENROUTER_API_KEY.
- Checkpoint 6 (Task 11): unit test pre-filter role/domain (LLM TIDAK
  dipanggil) - ditambahkan nanti.
- Checkpoint 7 (Task 12): test KK1-3 real LLM - ditambahkan nanti.
"""

import uuid

import pytest
from pydantic import ValidationError

import src.layers.domain_gate.cakupan_individu as cakupan_individu_module
from src.layers.domain_gate.cakupan_individu import deteksi_constraint_atomic_intent
from src.schemas.authorization import AtomicIntentAuthorization, DomainAuthorization
from src.schemas.cakupan_individu import ConstraintCakupanIndividu
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import LabelBentukJawaban


def _buat_atomic_intent_authorization(
    teks: str, domain_decisions: list[DomainAuthorization]
) -> AtomicIntentAuthorization:
    return AtomicIntentAuthorization(
        atomic_intent=AtomicIntent(
            atomic_intent_id=str(uuid.uuid4()),
            teks_kebutuhan=teks,
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
            bergantung_pada=None,
        ),
        domain_decisions=domain_decisions,
    )


def test_terdeteksi_true_wajib_alasan():
    with pytest.raises(ValidationError):
        ConstraintCakupanIndividu(terdeteksi=True, alasan=None)


def test_terdeteksi_false_tidak_boleh_alasan():
    with pytest.raises(ValidationError):
        ConstraintCakupanIndividu(terdeteksi=False, alasan="tidak seharusnya ada")


def test_terdeteksi_true_dengan_alasan_valid():
    hasil = ConstraintCakupanIndividu(
        terdeteksi=True, alasan="menyentuh v_hr_employee_performance_semester"
    )
    assert hasil.terdeteksi is True
    assert hasil.alasan is not None


def test_terdeteksi_false_tanpa_alasan_valid():
    hasil = ConstraintCakupanIndividu(terdeteksi=False, alasan=None)
    assert hasil.terdeteksi is False
    assert hasil.alasan is None


# --- Checkpoint 6: pre-filter role/domain (LLM TIDAK dipanggil) -------------


def test_pre_filter_role_bukan_staff_tier_tanpa_panggilan_llm(monkeypatch):
    panggilan = {"deteksi": 0, "verifikasi": 0}

    def _deteksi_gagal_jika_dipanggil(atomic_intent):
        panggilan["deteksi"] += 1
        raise AssertionError("deteksi_cakupan_individu TIDAK BOLEH dipanggil untuk role non-Staff")

    def _verifikasi_gagal_jika_dipanggil(atomic_intent, terdeteksi_awal):
        panggilan["verifikasi"] += 1
        raise AssertionError(
            "verifikasi_cakupan_individu TIDAK BOLEH dipanggil untuk role non-Staff"
        )

    monkeypatch.setattr(
        cakupan_individu_module, "deteksi_cakupan_individu", _deteksi_gagal_jika_dipanggil
    )
    monkeypatch.setattr(
        cakupan_individu_module, "verifikasi_cakupan_individu", _verifikasi_gagal_jika_dipanggil
    )

    aia = _buat_atomic_intent_authorization(
        "Siapa staf tercepat bulan ini?",
        [DomainAuthorization(domain=Domain.FACILITY, diizinkan=True)],
    )
    hasil = deteksi_constraint_atomic_intent(aia, "General Manager")

    assert hasil.constraint.terdeteksi is False
    assert panggilan == {"deteksi": 0, "verifikasi": 0}


def test_pre_filter_domain_tidak_relevan_tanpa_panggilan_llm(monkeypatch):
    panggilan = {"deteksi": 0, "verifikasi": 0}

    def _deteksi_gagal_jika_dipanggil(atomic_intent):
        panggilan["deteksi"] += 1
        raise AssertionError(
            "deteksi_cakupan_individu TIDAK BOLEH dipanggil untuk domain tidak relevan"
        )

    def _verifikasi_gagal_jika_dipanggil(atomic_intent, terdeteksi_awal):
        panggilan["verifikasi"] += 1
        raise AssertionError(
            "verifikasi_cakupan_individu TIDAK BOLEH dipanggil untuk domain tidak relevan"
        )

    monkeypatch.setattr(
        cakupan_individu_module, "deteksi_cakupan_individu", _deteksi_gagal_jika_dipanggil
    )
    monkeypatch.setattr(
        cakupan_individu_module, "verifikasi_cakupan_individu", _verifikasi_gagal_jika_dipanggil
    )

    aia = _buat_atomic_intent_authorization(
        "Berapa okupansi kamar bulan ini?",
        [DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
    )
    hasil = deteksi_constraint_atomic_intent(aia, "Housekeeping Staff")

    assert hasil.constraint.terdeteksi is False
    assert panggilan == {"deteksi": 0, "verifikasi": 0}


def test_pre_filter_domain_ditolak_tidak_dianggap_relevan(monkeypatch):
    """Domain facility ADA di domain_decisions tapi diizinkan=False -
    tetap harus dianggap tidak relevan (pre-filter cek diizinkan=True)."""
    monkeypatch.setattr(
        cakupan_individu_module,
        "deteksi_cakupan_individu",
        lambda atomic_intent: (_ for _ in ()).throw(
            AssertionError("tidak boleh dipanggil - domain facility ditolak")
        ),
    )

    aia = _buat_atomic_intent_authorization(
        "Siapa staf tercepat bulan ini?",
        [
            DomainAuthorization(
                domain=Domain.FACILITY, diizinkan=False, alasan="role tidak punya akses"
            )
        ],
    )
    hasil = deteksi_constraint_atomic_intent(aia, "HR Staff")

    assert hasil.constraint.terdeteksi is False
