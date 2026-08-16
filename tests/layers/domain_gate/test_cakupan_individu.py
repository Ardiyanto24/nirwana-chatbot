"""Test suite Deteksi Constraint Cakupan-Individu (Milestone 2.3).

File ini dibangun bertahap lintas checkpoint (preseden pola M2.2 CP4->CP5):
- Checkpoint 2 (Task 3): unit test validator ConstraintCakupanIndividu -
  murni pydantic, TANPA DATABASE_URL/OPENROUTER_API_KEY.
- Checkpoint 6 (Task 11): unit test pre-filter role/domain (LLM TIDAK
  dipanggil) - ditambahkan nanti.
- Checkpoint 7 (Task 12): test KK1-3 real LLM - ditambahkan nanti.
"""

import pytest
from pydantic import ValidationError

from src.schemas.cakupan_individu import ConstraintCakupanIndividu


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
