"""Test `susun_data_visualisasi()`/`susun_data_visualisasi_semua()`
(Milestone 4.5) - src/layers/interpretation/visualisasi.py. Fungsi murni
deterministik, TANPA LLM - seluruh test langsung terhadap fungsi asli,
tidak ada mock."""

from src.layers.interpretation.visualisasi import (
    susun_data_visualisasi,
    susun_data_visualisasi_semua,
)
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage, StatusEksekusi


def _paket(
    label: LabelBentukJawaban, rows: list[dict], atomic_intent_id: str = "a1"
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent_id,
        session_id="s1",
        turn_index=1,
        teks_kebutuhan="teks",
        label_bentuk_jawaban=label,
        nilai_hasil={"rows": rows},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


def test_nilai_tunggal_satu_baris_satu_kolom_jadi_scalar():
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.NILAI_TUNGGAL, [{"occupancy_rate": 0.82}]))
    assert hasil.nilai_tunggal == 0.82
    assert hasil.deret is None


def test_nilai_tunggal_ambigu_multi_kolom_fallback_deret():
    rows = [{"occupancy_rate": 0.82, "property_id": "P01"}]
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.NILAI_TUNGGAL, rows))
    assert hasil.nilai_tunggal is None
    assert hasil.deret == rows


def test_nilai_tunggal_ambigu_multi_baris_fallback_deret():
    rows = [{"v": 1}, {"v": 2}]
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.NILAI_TUNGGAL, rows))
    assert hasil.nilai_tunggal is None
    assert hasil.deret == rows


def test_tren_multi_baris_jadi_deret():
    rows = [{"bulan": "Jan", "v": 0.7}, {"bulan": "Feb", "v": 0.75}, {"bulan": "Mar", "v": 0.8}]
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.TREN, rows))
    assert hasil.deret == rows
    assert hasil.nilai_tunggal is None


def test_perbandingan_jadi_deret():
    rows = [{"kategori": "A", "v": 1}, {"kategori": "B", "v": 2}]
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.PERBANDINGAN, rows))
    assert hasil.deret == rows


def test_peringkat_jadi_deret():
    rows = [{"nama": "Budi", "rating": 4.9}, {"nama": "Ani", "rating": 4.8}]
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.PERINGKAT, rows))
    assert hasil.deret == rows


def test_komposisi_jadi_deret():
    rows = [{"departemen": "F&B", "revenue": 100}, {"departemen": "Housekeeping", "revenue": 50}]
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.KOMPOSISI, rows))
    assert hasil.deret == rows


def test_rows_kosong_jadi_deret_kosong_bukan_error():
    hasil = susun_data_visualisasi(_paket(LabelBentukJawaban.KOMPOSISI, []))
    assert hasil.deret == []


def test_atomic_intent_id_diteruskan_apa_adanya():
    hasil = susun_data_visualisasi(
        _paket(LabelBentukJawaban.NILAI_TUNGGAL, [{"v": 1}], atomic_intent_id="xyz-123")
    )
    assert hasil.atomic_intent_id == "xyz-123"


def test_susun_data_visualisasi_semua_batch():
    paket1 = _paket(LabelBentukJawaban.NILAI_TUNGGAL, [{"v": 1}], "a1")
    paket2 = _paket(LabelBentukJawaban.TREN, [{"x": 1}, {"x": 2}], "a2")
    hasil = susun_data_visualisasi_semua([paket1, paket2])
    assert len(hasil) == 2
    assert hasil[0].atomic_intent_id == "a1"
    assert hasil[1].atomic_intent_id == "a2"
