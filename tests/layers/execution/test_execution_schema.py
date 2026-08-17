"""Test suite skema Execution (Milestone 4.2) - src/schemas/execution.py
(HasilEksekusiAtomicIntent). Nama file dipisah dari
test_klasifikasi_respons.py (test orkestrator
src/layers/execution/klasifikasi_respons.py) - mirror preseden
test_query_engine_schema.py vs test_penyusunan_request.py (M3.4)."""

import uuid

import pytest
from pydantic import ValidationError

from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.execution import HasilEksekusiAtomicIntent
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
        atomic_intent=_buat_atomic_intent(), status=StatusEksekusi.BERHASIL, nilai_hasil=[]
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
        HasilEksekusiAtomicIntent(atomic_intent=_buat_atomic_intent(), status=StatusEksekusi.GAGAL_TEKNIS)


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
    [
        StatusEksekusi.SEBAGIAN,
        StatusEksekusi.DITOLAK_OTORISASI,
        StatusEksekusi.TERBLOKIR_KETERGANTUNGAN,
    ],
)
def test_status_di_luar_berhasil_gagal_teknis_ditolak(status_terlarang):
    with pytest.raises(ValidationError):
        HasilEksekusiAtomicIntent(
            atomic_intent=_buat_atomic_intent(),
            status=status_terlarang,
            kegagalan_alasan="x",
        )


# --- retry_count_infra/revisi_count default -----------------------------


def test_default_retry_dan_revisi_count_nol():
    hasil = HasilEksekusiAtomicIntent(
        atomic_intent=_buat_atomic_intent(), status=StatusEksekusi.BERHASIL, nilai_hasil=[]
    )
    assert hasil.retry_count_infra == 0
    assert hasil.revisi_count == 0
