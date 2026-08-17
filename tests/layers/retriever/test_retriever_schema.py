"""Test suite skema Retriever (Milestone 3.1) - src/schemas/retriever.py.

Nama file sengaja dibedakan dari test_retriever.py (Checkpoint 10, test
orkestrator src/layers/retriever/retriever.py) - mirror preseden M2.4
(test_verification_gate.py untuk skema vs test_verifikasi_gate.py untuk
orkestrator), meski di sini nama modul schema dan orkestrator kebetulan
identik ("retriever"), bukan dibedakan lewat bahasa Inggris/Indonesia
seperti M2.4.
"""

import pytest
from pydantic import ValidationError

from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import HasilPencarianKandidat, KandidatView, SumberPencarian
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id="ai-001",
        teks_kebutuhan="okupansi Bali bulan ini",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_kandidat() -> KandidatView:
    return KandidatView(
        view_name="v_reservation_room_type_daily",
        domain=Domain.RESERVATION,
        skor=5.2,
        sumber=SumberPencarian.BM25,
    )


def test_status_gagal_teknis_ditolak():
    with pytest.raises(ValidationError):
        HasilPencarianKandidat(
            atomic_intent=_buat_atomic_intent(),
            domain_diizinkan=[Domain.RESERVATION],
            kandidat=[_buat_kandidat()],
            fallback_terpicu=False,
            status=StatusEksekusi.GAGAL_TEKNIS,
        )


def test_status_ditolak_otorisasi_ditolak():
    with pytest.raises(ValidationError):
        HasilPencarianKandidat(
            atomic_intent=_buat_atomic_intent(),
            domain_diizinkan=[Domain.RESERVATION],
            kandidat=[_buat_kandidat()],
            fallback_terpicu=False,
            status=StatusEksekusi.DITOLAK_OTORISASI,
        )


def test_fallback_tidak_terpicu_wajib_status_berhasil():
    with pytest.raises(ValidationError):
        HasilPencarianKandidat(
            atomic_intent=_buat_atomic_intent(),
            domain_diizinkan=[Domain.RESERVATION],
            kandidat=[_buat_kandidat()],
            fallback_terpicu=False,
            status=StatusEksekusi.SEBAGIAN,
        )


def test_fallback_terpicu_status_sebagian_valid():
    hasil = HasilPencarianKandidat(
        atomic_intent=_buat_atomic_intent(),
        domain_diizinkan=[Domain.RESERVATION],
        kandidat=[_buat_kandidat()],
        fallback_terpicu=True,
        status=StatusEksekusi.SEBAGIAN,
    )
    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.fallback_terpicu is True


def test_fallback_terpicu_status_berhasil_valid():
    hasil = HasilPencarianKandidat(
        atomic_intent=_buat_atomic_intent(),
        domain_diizinkan=[Domain.RESERVATION],
        kandidat=[_buat_kandidat()],
        fallback_terpicu=True,
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.status == StatusEksekusi.BERHASIL


def test_fallback_tidak_terpicu_status_berhasil_valid():
    hasil = HasilPencarianKandidat(
        atomic_intent=_buat_atomic_intent(),
        domain_diizinkan=[Domain.RESERVATION],
        kandidat=[_buat_kandidat()],
        fallback_terpicu=False,
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.fallback_terpicu is False
    assert hasil.status == StatusEksekusi.BERHASIL
