"""Test suite skema Kecocokan Makna (Milestone 3.2) -
src/schemas/retriever.py (HasilKecocokanMakna/KecocokanKandidat/
LabelKecocokanMakna). Nama file dipisah dari test_kecocokan_makna.py
(Checkpoint 7-10, test orkestrator src/layers/retriever/kecocokan_makna.py)
- mirror preseden test_retriever_schema.py vs test_retriever.py (M3.1)."""

import pytest
from pydantic import ValidationError

from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import (
    HasilKecocokanMakna,
    KandidatView,
    KecocokanKandidat,
    LabelKecocokanMakna,
    SumberPencarian,
)
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


def _buat_kecocokan(
    label: LabelKecocokanMakna = LabelKecocokanMakna.DITEMUKAN,
) -> KecocokanKandidat:
    return KecocokanKandidat(
        kandidat=_buat_kandidat(), label=label, alasan="grain sesuai kebutuhan"
    )


def test_status_gagal_teknis_dengan_kecocokan_nonkosong_ditolak():
    with pytest.raises(ValidationError):
        HasilKecocokanMakna(
            atomic_intent=_buat_atomic_intent(),
            kecocokan=[_buat_kecocokan()],
            status=StatusEksekusi.GAGAL_TEKNIS,
        )


def test_status_ditolak_otorisasi_ditolak():
    with pytest.raises(ValidationError):
        HasilKecocokanMakna(
            atomic_intent=_buat_atomic_intent(),
            kecocokan=[_buat_kecocokan()],
            status=StatusEksekusi.DITOLAK_OTORISASI,
        )


def test_status_terblokir_ketergantungan_ditolak():
    with pytest.raises(ValidationError):
        HasilKecocokanMakna(
            atomic_intent=_buat_atomic_intent(),
            kecocokan=[],
            status=StatusEksekusi.TERBLOKIR_KETERGANTUNGAN,
        )


def test_status_gagal_teknis_dengan_kecocokan_kosong_valid():
    hasil = HasilKecocokanMakna(
        atomic_intent=_buat_atomic_intent(),
        kecocokan=[],
        status=StatusEksekusi.GAGAL_TEKNIS,
    )
    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kecocokan == []


def test_status_berhasil_dengan_kecocokan_kosong_valid():
    """Beda dari AtomicIntentDomains (M2.1, validator dua arah) - kasus
    valid M3.1 tidak menemukan kandidat sama sekali (kandidat=[]) harus
    tetap bisa direpresentasikan sebagai BERHASIL+kecocokan=[], bukan
    ditolak. Lihat decisions.md Keputusan 10."""
    hasil = HasilKecocokanMakna(
        atomic_intent=_buat_atomic_intent(),
        kecocokan=[],
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.kecocokan == []


def test_status_sebagian_dengan_kecocokan_nonkosong_valid():
    hasil = HasilKecocokanMakna(
        atomic_intent=_buat_atomic_intent(),
        kecocokan=[_buat_kecocokan(LabelKecocokanMakna.SEBAGIAN)],
        status=StatusEksekusi.SEBAGIAN,
    )
    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.kecocokan[0].label == LabelKecocokanMakna.SEBAGIAN


def test_status_berhasil_dengan_kecocokan_nonkosong_valid():
    hasil = HasilKecocokanMakna(
        atomic_intent=_buat_atomic_intent(),
        kecocokan=[_buat_kecocokan(LabelKecocokanMakna.TIDAK_DITEMUKAN)],
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.kecocokan[0].label == LabelKecocokanMakna.TIDAK_DITEMUKAN


def test_kecocokan_kandidat_membawa_objek_kandidatview_utuh():
    """Keputusan 12: KandidatView utuh (domain/skor/sumber), bukan
    view_name str polos - berguna untuk audit/observability M3.3 tanpa
    join balik ke HasilPencarianKandidat."""
    kecocokan = _buat_kecocokan()
    assert kecocokan.kandidat.domain == Domain.RESERVATION
    assert kecocokan.kandidat.sumber == SumberPencarian.BM25
