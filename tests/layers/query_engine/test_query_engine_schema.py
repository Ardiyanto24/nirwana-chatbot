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
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
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


# --- HasilVerifikasiBentukRequest (Milestone 3.5) -----------------------------


def test_gagal_teknis_lolos_none_alasan_none_valid():
    hasil = HasilVerifikasiBentukRequest(
        atomic_intent=_buat_atomic_intent(),
        request=_buat_request(),
        status=StatusEksekusi.GAGAL_TEKNIS,
        lolos=None,
        alasan=None,
    )
    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.lolos is None
    assert hasil.alasan is None


def test_berhasil_lolos_true_alasan_none_valid():
    hasil = HasilVerifikasiBentukRequest(
        atomic_intent=_buat_atomic_intent(),
        request=_buat_request(),
        status=StatusEksekusi.BERHASIL,
        lolos=True,
        alasan=None,
    )
    assert hasil.lolos is True
    assert hasil.alasan is None


def test_berhasil_lolos_false_alasan_terisi_valid():
    hasil = HasilVerifikasiBentukRequest(
        atomic_intent=_buat_atomic_intent(),
        request=_buat_request(),
        status=StatusEksekusi.BERHASIL,
        lolos=False,
        alasan="rentang tanggal hanya satu hari, tidak cukup membentuk tren",
    )
    assert hasil.lolos is False
    assert hasil.alasan is not None


def test_gagal_teknis_dengan_lolos_terisi_ditolak():
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=StatusEksekusi.GAGAL_TEKNIS,
            lolos=True,
            alasan=None,
        )


def test_gagal_teknis_dengan_alasan_terisi_ditolak():
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=StatusEksekusi.GAGAL_TEKNIS,
            lolos=None,
            alasan="alasan tidak seharusnya ada di sini",
        )


def test_berhasil_dengan_lolos_none_ditolak():
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=StatusEksekusi.BERHASIL,
            lolos=None,
            alasan=None,
        )


def test_lolos_true_dengan_alasan_terisi_ditolak():
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=StatusEksekusi.BERHASIL,
            lolos=True,
            alasan="tidak boleh ada alasan saat lolos",
        )


def test_lolos_false_dengan_alasan_none_ditolak():
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=StatusEksekusi.BERHASIL,
            lolos=False,
            alasan=None,
        )


@pytest.mark.parametrize(
    "status_lain",
    [
        StatusEksekusi.SEBAGIAN,
        StatusEksekusi.DITOLAK_OTORISASI,
        StatusEksekusi.TERBLOKIR_KETERGANTUNGAN,
    ],
)
def test_verifikasi_bentuk_request_status_lain_ditolak(status_lain):
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=_buat_request(),
            status=status_lain,
            lolos=None,
            alasan=None,
        )


def test_verifikasi_bentuk_request_request_wajib_terisi():
    with pytest.raises(ValidationError):
        HasilVerifikasiBentukRequest(
            atomic_intent=_buat_atomic_intent(),
            request=None,
            status=StatusEksekusi.GAGAL_TEKNIS,
            lolos=None,
            alasan=None,
        )
