"""Test suite skema Penyusunan Request (Milestone 3.4) -
src/schemas/query_engine.py (HasilPenyusunanRequest). Nama file dipisah
dari test_penyusunan_request.py (Checkpoint 5, test orkestrator
src/layers/query_engine/penyusunan_request.py) - mirror preseden
test_retriever_schema.py vs test_retriever.py (M3.1)."""

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.query_engine import HasilPenyusunanRequest
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="okupansi Bali bulan lalu",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_request() -> QueryEngineRequest:
    return QueryEngineRequest(
        domain=Domain.RESERVATION,
        view_name="v_reservation_room_type_daily",
        params={"property_id": "P01", "period_date_from": "2026-07-01", "period_date_to": "2026-07-31"},
    )


def test_berhasil_dengan_request_terisi_valid():
    hasil = HasilPenyusunanRequest(
        atomic_intent=_buat_atomic_intent(), request=_buat_request(), status=StatusEksekusi.BERHASIL
    )
    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.request is not None


def test_berhasil_dengan_request_none_ditolak():
    with pytest.raises(ValidationError):
        HasilPenyusunanRequest(
            atomic_intent=_buat_atomic_intent(), request=None, status=StatusEksekusi.BERHASIL
        )


def test_gagal_teknis_dengan_request_terisi_ditolak():
    with pytest.raises(ValidationError):
        HasilPenyusunanRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=StatusEksekusi.GAGAL_TEKNIS,
        )


def test_gagal_teknis_dengan_request_none_valid():
    hasil = HasilPenyusunanRequest(
        atomic_intent=_buat_atomic_intent(), request=None, status=StatusEksekusi.GAGAL_TEKNIS
    )
    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.request is None


@pytest.mark.parametrize(
    "status_lain",
    [
        StatusEksekusi.SEBAGIAN,
        StatusEksekusi.DITOLAK_OTORISASI,
        StatusEksekusi.TERBLOKIR_KETERGANTUNGAN,
    ],
)
def test_status_lain_selain_berhasil_gagal_teknis_ditolak(status_lain):
    with pytest.raises(ValidationError):
        HasilPenyusunanRequest(
            atomic_intent=_buat_atomic_intent(), request=None, status=status_lain
        )
