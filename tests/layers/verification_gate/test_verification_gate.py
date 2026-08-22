"""Test suite skema Verification Gate (Milestone 2.4).

File ini dibangun bertahap lintas checkpoint (preseden pola M2.2 CP4->CP5,
M2.3 CP2->CP7):
- Checkpoint 2 (Task 3): unit test validator HasilVerifikasiGate - murni
  pydantic, TANPA DATABASE_URL.
"""

import pytest
from pydantic import ValidationError

from src.schemas.domain_gate import Domain
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest


def _buat_request() -> QueryEngineRequest:
    return QueryEngineRequest(
        domain=Domain.FACILITY, view_name="v_housekeeping_staff_daily", params={}
    )


def test_lolos_true_wajib_request_final():
    with pytest.raises(ValidationError):
        HasilVerifikasiGate(request_final=None, lolos=True, terkoreksi=False)


def test_lolos_true_tidak_boleh_alasan_penolakan():
    with pytest.raises(ValidationError):
        HasilVerifikasiGate(
            request_final=_buat_request(),
            lolos=True,
            terkoreksi=False,
            alasan_penolakan="tidak seharusnya ada",
        )


def test_lolos_false_wajib_request_final_none():
    with pytest.raises(ValidationError):
        HasilVerifikasiGate(
            request_final=_buat_request(),
            lolos=False,
            terkoreksi=False,
            alasan_penolakan="ditolak",
        )


def test_lolos_false_wajib_alasan_penolakan():
    with pytest.raises(ValidationError):
        HasilVerifikasiGate(request_final=None, lolos=False, terkoreksi=False)


def test_lolos_true_valid():
    hasil = HasilVerifikasiGate(
        request_final=_buat_request(), lolos=True, terkoreksi=True
    )
    assert hasil.lolos is True
    assert hasil.request_final is not None
    assert hasil.alasan_penolakan is None


def test_lolos_false_valid():
    hasil = HasilVerifikasiGate(
        request_final=None,
        lolos=False,
        terkoreksi=False,
        alasan_penolakan="view_name tidak cocok",
    )
    assert hasil.lolos is False
    assert hasil.request_final is None
    assert hasil.alasan_penolakan is not None
