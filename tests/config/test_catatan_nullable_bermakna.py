"""Test katalog nullable-bermakna (Milestone 4.3) -
src/config/catatan_nullable_bermakna.py. Cross-check view_name terhadap
DAFTAR_VIEW_PER_DOMAIN (view nyata, bukan typo) DAN cross-check potongan
kalimat kunci tiap catatan benar-benar muncul di
docs/03-domain-source/katalog-data-chatbot.md pada bagian view yang
bersangkutan (bukti transkripsi tidak melenceng dari sumber), mirror
prinsip cross-check independen test_katalog_view.py (M2.4/M3.1)."""

from pathlib import Path

from src.config.catatan_nullable_bermakna import CATATAN_NULLABLE_BERMAKNA
from src.config.katalog_view import DAFTAR_VIEW_PER_DOMAIN

_KATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "03-domain-source"
    / "katalog-data-chatbot.md"
)

# Potongan kalimat kunci (bukan kalimat penuh) yang WAJIB muncul persis di
# katalog sumber pada bagian view terkait - dipilih independen dari isi
# dict di atas (ditulis ulang manual saat test ini dibuat, bukan copy-paste
# dari catatan_nullable_bermakna.py) supaya bukan pengujian sirkular.
_FRASA_KUNCI_SUMBER = {
    ("v_lookup_fnb_transactions", "guest_id"): "~70% kosong",
    ("v_lookup_maintenance_tickets", "room_id"): "kerusakan di fasilitas umum",
    ("v_maintenance_ticket_daily", "avg_exceeds_sla_threshold"): "NULL jika durasi belum ada",
}


def test_seluruh_view_name_terdaftar_valid():
    seluruh_view_valid = {v for views in DAFTAR_VIEW_PER_DOMAIN.values() for v in views}
    for view_name in CATATAN_NULLABLE_BERMAKNA:
        assert view_name in seluruh_view_valid, f"{view_name} bukan view yang terdaftar"


def test_katalog_tidak_kosong_dan_terbatas_subset():
    total_kolom = sum(len(kolom) for kolom in CATATAN_NULLABLE_BERMAKNA.values())
    assert total_kolom > 0
    # Subset representatif (Keputusan 2) - bukan cakupan penuh 67 view.
    assert len(CATATAN_NULLABLE_BERMAKNA) < 10


def test_frasa_kunci_muncul_di_katalog_sumber_pada_bagian_view_terkait():
    teks_sumber = _KATALOG_PATH.read_text(encoding="utf-8")

    for (view_name, kolom), frasa in _FRASA_KUNCI_SUMBER.items():
        heading = f"#### `{view_name}`"
        idx_heading = teks_sumber.find(heading)
        assert idx_heading != -1, f"heading {heading} tidak ditemukan di katalog sumber"

        # Frasa kunci wajib muncul dalam 3000 karakter setelah heading view
        # (mencakup tabel kolom view tersebut, sebelum heading view berikutnya).
        potongan = teks_sumber[idx_heading : idx_heading + 3000]
        assert frasa in potongan, (
            f"frasa kunci '{frasa}' untuk {view_name}.{kolom} tidak ditemukan "
            f"di bagian view tersebut - kemungkinan transkripsi melenceng"
        )


def test_seluruh_pasangan_view_kolom_di_katalog_py_punya_frasa_kunci_diuji():
    """Memastikan tabel _FRASA_KUNCI_SUMBER tidak diam-diam kurang lengkap
    dibanding isi CATATAN_NULLABLE_BERMAKNA yang sesungguhnya."""
    pasangan_di_katalog = {
        (view_name, kolom)
        for view_name, kolom_dict in CATATAN_NULLABLE_BERMAKNA.items()
        for kolom in kolom_dict
    }
    assert pasangan_di_katalog == set(_FRASA_KUNCI_SUMBER.keys())
