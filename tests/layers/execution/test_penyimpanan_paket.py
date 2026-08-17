"""Test suite Penyusunan dan Penyimpanan Paket Session Memory (Milestone
4.3) - src/layers/execution/penyimpanan_paket.py. `store_session_memory`
di-monkeypatch (isolasi dari DB nyata) - round-trip Supabase sungguhan
ada di test_penyimpanan_paket_integrasi.py (Checkpoint 5)."""

import uuid

import pytest

from src.layers.execution import penyimpanan_paket as modul
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi

_VIEW_TERDAFTAR = "v_lookup_maintenance_tickets"  # punya catatan utk room_id


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="tiket maintenance bulan ini",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _patch_store(monkeypatch):
    dipanggil: dict = {}

    def _fake_store(package):
        dipanggil["package"] = package

    monkeypatch.setattr(modul, "store_session_memory", _fake_store)
    return dipanggil


# --- _bungkus_nilai_hasil ----------------------------------------------


def test_bungkus_list_jadi_rows():
    assert modul._bungkus_nilai_hasil([{"a": 1}, {"a": 2}]) == {"rows": [{"a": 1}, {"a": 2}]}


def test_bungkus_none_jadi_rows_kosong():
    assert modul._bungkus_nilai_hasil(None) == {"rows": []}


def test_bungkus_list_kosong_jadi_rows_kosong():
    assert modul._bungkus_nilai_hasil([]) == {"rows": []}


# --- _catatan_interpretasi_untuk_hasil ----------------------------------


def test_catatan_kolom_null_terdaftar_katalog_menghasilkan_catatan():
    nilai_hasil = [{"ticket_id": "T1", "room_id": None, "property_id": "P01"}]
    catatan = modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, nilai_hasil)
    assert len(catatan) == 1
    assert "fasilitas umum" in catatan[0]


def test_catatan_kolom_null_tidak_terdaftar_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"ticket_id": "T1", "kolom_tidak_dikenal": None}]
    catatan = modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, nilai_hasil)
    assert catatan == []


def test_catatan_kolom_terdaftar_tapi_tidak_null_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"ticket_id": "T1", "room_id": "R101"}]
    catatan = modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, nilai_hasil)
    assert catatan == []


def test_catatan_view_name_none_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"room_id": None}]
    assert modul._catatan_interpretasi_untuk_hasil(None, nilai_hasil) == []


def test_catatan_view_tidak_terdaftar_katalog_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"kolom_apapun": None}]
    assert modul._catatan_interpretasi_untuk_hasil("v_view_lain_yang_tidak_ada_di_katalog", nilai_hasil) == []


def test_catatan_nilai_hasil_kosong_tidak_menghasilkan_apa_apa():
    assert modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, []) == []
    assert modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, None) == []


# --- susun_dan_simpan_paket (orkestrator) -------------------------------


def test_orkestrator_berhasil_lengkap(monkeypatch):
    dipanggil = _patch_store(monkeypatch)
    ai = _buat_atomic_intent()
    nilai_hasil = [{"ticket_id": "T1", "room_id": None, "property_id": "P01"}]

    hasil = modul.susun_dan_simpan_paket(
        ai, "sess-1", 3, StatusEksekusi.BERHASIL, view_name=_VIEW_TERDAFTAR, nilai_hasil=nilai_hasil
    )

    assert hasil.atomic_intent_id == ai.atomic_intent_id
    assert hasil.session_id == "sess-1"
    assert hasil.turn_index == 3
    assert hasil.teks_kebutuhan == ai.teks_kebutuhan
    assert hasil.label_bentuk_jawaban == ai.label_bentuk_jawaban
    assert hasil.nilai_hasil == {"rows": nilai_hasil}
    assert len(hasil.catatan_interpretasi) == 1
    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.sumber == "eksekusi_baru"
    assert dipanggil["package"] == hasil


def test_orkestrator_gagal_teknis_tanpa_nilai_hasil(monkeypatch):
    dipanggil = _patch_store(monkeypatch)
    ai = _buat_atomic_intent()

    hasil = modul.susun_dan_simpan_paket(ai, "sess-1", 1, StatusEksekusi.GAGAL_TEKNIS)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.nilai_hasil == {"rows": []}
    assert hasil.catatan_interpretasi == []
    assert dipanggil["package"] == hasil


def test_orkestrator_sumber_selalu_eksekusi_baru(monkeypatch):
    _patch_store(monkeypatch)
    hasil = modul.susun_dan_simpan_paket(
        _buat_atomic_intent(), "sess-1", 1, StatusEksekusi.BERHASIL, nilai_hasil=[]
    )
    assert hasil.sumber == "eksekusi_baru"


def test_orkestrator_exception_store_diteruskan_apa_adanya(monkeypatch):
    def _fake_store_gagal(package):
        raise RuntimeError("simulasi DB gagal")

    monkeypatch.setattr(modul, "store_session_memory", _fake_store_gagal)

    with pytest.raises(RuntimeError, match="simulasi DB gagal"):
        modul.susun_dan_simpan_paket(_buat_atomic_intent(), "sess-1", 1, StatusEksekusi.BERHASIL)
