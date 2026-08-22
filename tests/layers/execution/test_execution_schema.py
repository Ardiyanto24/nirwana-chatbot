"""Test suite skema Execution (Milestone 4.2) - src/schemas/execution.py
(HasilEksekusiAtomicIntent, HasilMetaChatbotAPI). Nama file dipisah dari
test_klasifikasi_respons.py (test orkestrator
src/layers/execution/klasifikasi_respons.py) - mirror preseden
test_query_engine_schema.py vs test_penyusunan_request.py (M3.4).

Revisit (2026-08-17): SEBAGIAN sekarang valid (sebelumnya ditolak sama
seperti DITOLAK_OTORISASI/TERBLOKIR_KETERGANTUNGAN) - lihat
milestones/4.2-.../decisions.md Keputusan 11."""

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.execution import HasilEksekusiAtomicIntent, HasilMetaChatbotAPI
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="okupansi Bali bulan lalu",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


# --- status=BERHASIL ---------------------------------------------------


def test_berhasil_dengan_nilai_hasil_terisi_valid():
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(),
        status=StatusEksekusi.BERHASIL,
        nilai_hasil=[{"property_id": "P01"}],
    )
    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.nilai_hasil == [{"property_id": "P01"}]
    assert hasil.kegagalan_alasan is None
    assert hasil.bug_prioritas_tinggi is False


def test_berhasil_dengan_nilai_hasil_list_kosong_valid():
    """Hasil kosong (0 baris) tetap sah BERHASIL - lihat decisions.md
    Keputusan 1 (0 legitimate berbeda dari 0 karena bug)."""
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(),
        status=StatusEksekusi.BERHASIL,
        nilai_hasil=[],
    )
    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.nilai_hasil == []


def test_berhasil_dengan_kegagalan_alasan_ditolak():
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=StatusEksekusi.BERHASIL,
            nilai_hasil=[],
            kegagalan_alasan="eskalasi_403",
        )


def test_berhasil_dengan_bug_prioritas_tinggi_true_ditolak():
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=StatusEksekusi.BERHASIL,
            nilai_hasil=[],
            bug_prioritas_tinggi=True,
        )


# --- status=GAGAL_TEKNIS -------------------------------------------------


def test_gagal_teknis_dengan_kegagalan_alasan_terisi_valid():
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(),
        status=StatusEksekusi.GAGAL_TEKNIS,
        kegagalan_alasan="eskalasi_403",
        bug_prioritas_tinggi=True,
    )
    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.nilai_hasil is None
    assert hasil.kegagalan_alasan == "eskalasi_403"


def test_gagal_teknis_tanpa_kegagalan_alasan_ditolak():
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(), status=StatusEksekusi.GAGAL_TEKNIS
        )


def test_gagal_teknis_dengan_nilai_hasil_terisi_ditolak():
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=StatusEksekusi.GAGAL_TEKNIS,
            kegagalan_alasan="infra_exhausted_5xx",
            nilai_hasil=[{"property_id": "P01"}],
        )


# --- status di luar BERHASIL/GAGAL_TEKNIS ditolak -----------------------


@pytest.mark.parametrize(
    "status_terlarang",
    [StatusEksekusi.DITOLAK_OTORISASI, StatusEksekusi.TERBLOKIR_KETERGANTUNGAN],
)
def test_status_di_luar_berhasil_sebagian_gagal_teknis_ditolak(status_terlarang):
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=status_terlarang,
            kegagalan_alasan="x",
        )


# --- status=SEBAGIAN (Revisit 2026-08-17) --------------------------------


def test_sebagian_dengan_nilai_hasil_terisi_valid():
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(),
        status=StatusEksekusi.SEBAGIAN,
        nilai_hasil=[{"property_id": "P01"}],
        data_quality_status="flagged",
    )
    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.data_quality_status == "flagged"
    assert hasil.kegagalan_alasan is None
    assert hasil.bug_prioritas_tinggi is False


def test_sebagian_dengan_kegagalan_alasan_ditolak():
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=StatusEksekusi.SEBAGIAN,
            nilai_hasil=[],
            kegagalan_alasan="x",
        )


def test_sebagian_dengan_bug_prioritas_tinggi_true_ditolak():
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=StatusEksekusi.SEBAGIAN,
            nilai_hasil=[],
            bug_prioritas_tinggi=True,
        )


def test_data_quality_status_dan_last_refreshed_at_default_none():
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(),
        status=StatusEksekusi.BERHASIL,
        nilai_hasil=[],
    )
    assert hasil.data_quality_status is None
    assert hasil.last_refreshed_at is None


# --- HasilMetaChatbotAPI --------------------------------------------------


def test_meta_status_code_dan_kegagalan_transport_xor():
    with pytest.raises(ValidationError):
        HasilMetaChatbotAPI(status_code=None, kegagalan_transport=None)
    with pytest.raises(ValidationError):
        HasilMetaChatbotAPI(status_code=200, kegagalan_transport="timeout")


def test_meta_200_dengan_field_null_valid():
    hasil = HasilMetaChatbotAPI(
        status_code=200, data_quality_status=None, last_refreshed_at=None
    )
    assert hasil.status_code == 200
    assert hasil.data_quality_status is None


# --- retry_count_infra/revisi_count default -----------------------------


def test_default_retry_dan_revisi_count_nol():
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(),
        status=StatusEksekusi.BERHASIL,
        nilai_hasil=[],
    )
    assert hasil.retry_count_infra == 0
    assert hasil.revisi_count == 0
