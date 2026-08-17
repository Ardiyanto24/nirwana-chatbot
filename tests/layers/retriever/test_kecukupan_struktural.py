"""Test orkestrator + mekanisme Milestone 3.3 (kecukupan_struktural.py).
Checkpoint 4: matriks lengkap rule table deterministik `_evaluasi_deterministik()`
- 5 label x nilai tri-state relevan, bukan sampel, supaya seluruh cabang
rule table teruji eksplisit."""

import pytest

from src.layers.retriever.grain_view import KarakteristikGrain
from src.layers.retriever.kecukupan_struktural import _evaluasi_deterministik
from src.schemas.session_memory import LabelBentukJawaban


def _grain(time_series="tidak_pasti", pembanding="tidak_pasti") -> KarakteristikGrain:
    return KarakteristikGrain(
        punya_time_series=time_series,
        punya_dimensi_pembanding=pembanding,
        catatan="fixture test",
    )


# --- nilai_tunggal: selalu cukup, apa pun grain-nya --------------------------


@pytest.mark.parametrize("time_series", ["ya", "tidak", "tidak_pasti"])
@pytest.mark.parametrize("pembanding", ["ya", "tidak", "tidak_pasti"])
def test_nilai_tunggal_selalu_cukup(time_series, pembanding):
    hasil, _ = _evaluasi_deterministik(
        LabelBentukJawaban.NILAI_TUNGGAL, _grain(time_series, pembanding)
    )
    assert hasil == "cukup"


# --- tren: bergantung punya_time_series --------------------------------------


def test_tren_time_series_ya_cukup():
    hasil, alasan = _evaluasi_deterministik(LabelBentukJawaban.TREN, _grain(time_series="ya"))
    assert hasil == "cukup"
    assert alasan


def test_tren_time_series_tidak_tidak_cukup():
    hasil, alasan = _evaluasi_deterministik(LabelBentukJawaban.TREN, _grain(time_series="tidak"))
    assert hasil == "tidak_cukup"
    assert alasan


def test_tren_time_series_tidak_pasti_tidak_pasti():
    hasil, alasan = _evaluasi_deterministik(
        LabelBentukJawaban.TREN, _grain(time_series="tidak_pasti")
    )
    assert hasil == "tidak_pasti"
    assert alasan


# --- perbandingan/peringkat/komposisi: bergantung punya_dimensi_pembanding ---


@pytest.mark.parametrize(
    "label",
    [LabelBentukJawaban.PERBANDINGAN, LabelBentukJawaban.PERINGKAT, LabelBentukJawaban.KOMPOSISI],
)
def test_dimensi_pembanding_ya_cukup(label):
    hasil, alasan = _evaluasi_deterministik(label, _grain(pembanding="ya"))
    assert hasil == "cukup"
    assert alasan


@pytest.mark.parametrize(
    "label",
    [LabelBentukJawaban.PERBANDINGAN, LabelBentukJawaban.PERINGKAT, LabelBentukJawaban.KOMPOSISI],
)
def test_dimensi_pembanding_tidak_tidak_cukup(label):
    hasil, alasan = _evaluasi_deterministik(label, _grain(pembanding="tidak"))
    assert hasil == "tidak_cukup"
    assert alasan


@pytest.mark.parametrize(
    "label",
    [LabelBentukJawaban.PERBANDINGAN, LabelBentukJawaban.PERINGKAT, LabelBentukJawaban.KOMPOSISI],
)
def test_dimensi_pembanding_tidak_pasti_tidak_pasti(label):
    hasil, alasan = _evaluasi_deterministik(label, _grain(pembanding="tidak_pasti"))
    assert hasil == "tidak_pasti"
    assert alasan


# --- fail-safe: label_bentuk_jawaban tidak dikenal rule table ---------------


def test_label_tidak_dikenal_fail_safe_tidak_pasti():
    """Bukti forward-compatibility (rasional user memilih hybrid,
    decisions.md Keputusan 1+6): kalau taksonomi label_bentuk_jawaban
    bertambah di masa depan, rule table TIDAK exception/menebak - jatuh
    ke tidak_pasti (otomatis dilempar ke fallback LLM oleh orkestrator).
    Simulasi nilai belum dikenal lewat plain str (bukan anggota Enum
    LabelBentukJawaban 5-nilai saat ini) - perbandingan `==` terhadap
    seluruh anggota enum di rule table pasti False, jatuh ke cabang
    fail-safe terakhir."""
    label_masa_depan = "deskriptif_naratif"
    hasil, alasan = _evaluasi_deterministik(label_masa_depan, _grain(time_series="ya", pembanding="ya"))
    assert hasil == "tidak_pasti"
    assert "tidak dikenal rule table" in alasan
