"""Test suite skema Kecukupan Struktural (Milestone 3.3) -
src/schemas/retriever.py (HasilKecukupanStruktural/KecukupanKandidat/
SumberKeputusanKecukupan). Nama file dipisah dari
test_kecukupan_struktural.py (Checkpoint 8+, test orkestrator
src/layers/retriever/kecukupan_struktural.py) - mirror preseden
test_kecocokan_makna_schema.py vs test_kecocokan_makna.py (M3.2)."""

import pytest
from pydantic import ValidationError

from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import (
    HasilKecukupanStruktural,
    KandidatView,
    KecukupanKandidat,
    LabelKecocokanMakna,
    SumberKeputusanKecukupan,
    SumberPencarian,
)
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id="ai-001",
        teks_kebutuhan="tren okupansi Bali 3 bulan terakhir",
        label_bentuk_jawaban=LabelBentukJawaban.TREN,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_kandidat(view_name: str = "v_reservation_room_type_daily") -> KandidatView:
    return KandidatView(
        view_name=view_name,
        domain=Domain.RESERVATION,
        skor=5.2,
        sumber=SumberPencarian.BM25,
    )


def _buat_kecukupan(
    view_name: str = "v_reservation_room_type_daily",
    cukup: bool = True,
    sumber_keputusan: SumberKeputusanKecukupan = SumberKeputusanKecukupan.DETERMINISTIK,
) -> KecukupanKandidat:
    return KecukupanKandidat(
        kandidat=_buat_kandidat(view_name),
        kecocokan_label=LabelKecocokanMakna.DITEMUKAN,
        cukup=cukup,
        alasan="grain punya dimensi waktu berulang, cukup untuk tren",
        sumber_keputusan=sumber_keputusan,
    )


def test_status_bukan_berhasil_ditolak():
    with pytest.raises(ValidationError):
        HasilKecukupanStruktural(
            atomic_intent=_buat_atomic_intent(),
            kecukupan=[_buat_kecukupan()],
            view_name_final="v_reservation_room_type_daily",
            status=StatusEksekusi.SEBAGIAN,
        )


def test_status_gagal_teknis_ditolak():
    with pytest.raises(ValidationError):
        HasilKecukupanStruktural(
            atomic_intent=_buat_atomic_intent(),
            kecukupan=[],
            view_name_final=None,
            status=StatusEksekusi.GAGAL_TEKNIS,
        )


def test_view_name_final_tidak_match_kandidat_cukup_ditolak():
    """Kandidat cukup=False, tapi view_name_final menyebut view itu juga
    - defensif, cek kelengkapan penegakan mirror verifikasi_gate() M2.4."""
    with pytest.raises(ValidationError):
        HasilKecukupanStruktural(
            atomic_intent=_buat_atomic_intent(),
            kecukupan=[_buat_kecukupan(cukup=False)],
            view_name_final="v_reservation_room_type_daily",
            status=StatusEksekusi.BERHASIL,
        )


def test_view_name_final_tidak_ada_di_kecukupan_sama_sekali_ditolak():
    with pytest.raises(ValidationError):
        HasilKecukupanStruktural(
            atomic_intent=_buat_atomic_intent(),
            kecukupan=[_buat_kecukupan()],
            view_name_final="v_view_lain_yang_tidak_pernah_dievaluasi",
            status=StatusEksekusi.BERHASIL,
        )


def test_view_name_final_none_dengan_kecukupan_kosong_valid():
    """Kasus tidak ada kandidat cukup sama sekali - view_name_final=None
    adalah hasil valid, bukan error."""
    hasil = HasilKecukupanStruktural(
        atomic_intent=_buat_atomic_intent(),
        kecukupan=[],
        view_name_final=None,
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.view_name_final is None


def test_view_name_final_none_dengan_seluruh_kandidat_tidak_cukup_valid():
    hasil = HasilKecukupanStruktural(
        atomic_intent=_buat_atomic_intent(),
        kecukupan=[_buat_kecukupan(cukup=False)],
        view_name_final=None,
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.view_name_final is None
    assert hasil.kecukupan[0].cukup is False


def test_view_name_final_match_kandidat_cukup_valid():
    hasil = HasilKecukupanStruktural(
        atomic_intent=_buat_atomic_intent(),
        kecukupan=[_buat_kecukupan(cukup=True)],
        view_name_final="v_reservation_room_type_daily",
        status=StatusEksekusi.BERHASIL,
    )
    assert hasil.view_name_final == "v_reservation_room_type_daily"


def test_kecukupan_kandidat_membawa_sumber_keputusan():
    kecukupan = _buat_kecukupan(sumber_keputusan=SumberKeputusanKecukupan.LLM)
    assert kecukupan.sumber_keputusan == SumberKeputusanKecukupan.LLM
    assert kecukupan.kandidat.domain == Domain.RESERVATION
