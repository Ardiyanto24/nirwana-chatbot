"""Test korpus 67 deskripsi Fungsi (Milestone 3.1) - cross-check terhadap
dokumen sumber via regex independen (parse ulang dari
docs/03-domain-source/katalog-data-chatbot.md), bukan len()/perbandingan
terhadap dirinya sendiri - supaya bukan pengujian sirkular, deteksi drift
transkripsi. Mirror pola tests/config/test_katalog_view.py (M2.4)."""

import re
from pathlib import Path

from src.config.katalog_view import DAFTAR_VIEW_PER_DOMAIN
from src.layers.retriever.korpus_view import KORPUS_FUNGSI_VIEW

_KATALOG_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "03-domain-source"
    / "katalog-data-chatbot.md"
)

_PATTERN = re.compile(
    r"^#### `([^`]+)`.*\n" r"\*Sumber:.*\n" r"\*\*Fungsi\*\*:\s*(.+)$",
    re.MULTILINE,
)


def _parse_fungsi_dari_dokumen() -> dict[str, str]:
    teks = _KATALOG_PATH.read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in _PATTERN.finditer(teks)}


def test_korpus_sama_persis_dengan_dokumen_sumber():
    dari_dokumen = _parse_fungsi_dari_dokumen()
    assert dari_dokumen == KORPUS_FUNGSI_VIEW


def test_regex_menemukan_67_entri_di_dokumen():
    """Prasyarat test di atas - kalau regex sendiri gagal menemukan 67
    entri, perbandingan == di atas bisa 'lolos' secara keliru karena
    dua-duanya sama-sama kosong/parsial."""
    assert len(_parse_fungsi_dari_dokumen()) == 67


def test_korpus_67_entri():
    assert len(KORPUS_FUNGSI_VIEW) == 67


def test_bijektif_dengan_daftar_view_per_domain():
    seluruh_view_katalog = {
        v for views in DAFTAR_VIEW_PER_DOMAIN.values() for v in views
    }
    assert set(KORPUS_FUNGSI_VIEW.keys()) == seluruh_view_katalog


def test_okupansi_ada_di_teks_v_reservation_room_type_daily():
    """Prasyarat KK1 sumber M3.1 (skenario 'okupansi Bali bulan ini')."""
    assert "okupansi" in KORPUS_FUNGSI_VIEW["v_reservation_room_type_daily"]
