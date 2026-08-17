"""Test orkestrator + mekanisme Milestone 3.3 (kecukupan_struktural.py).
Dibangun bertahap lintas checkpoint (preseden pola M2.2/M2.3/M3.2):
- Checkpoint 4 (Task 7): matriks lengkap rule table deterministik
  `_evaluasi_deterministik()` - 5 label x nilai tri-state relevan.
- Checkpoint 6 (Task 10): `_evaluasi_llm_fallback()` mocked LLM.
- Checkpoint 8 (Task 13): `evaluasi_kecukupan_struktural_atomic_intent()` -
  ditambahkan nanti.
"""

import json
import uuid

import pytest
from openai import APIError

import src.layers.retriever.kecukupan_struktural as kecukupan_struktural_module
from src.layers.retriever.grain_view import KarakteristikGrain
from src.layers.retriever.kecukupan_struktural import _evaluasi_deterministik, _evaluasi_llm_fallback
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import (
    KandidatView,
    KecocokanKandidat,
    LabelKecocokanMakna,
    SumberKeputusanKecukupan,
    SumberPencarian,
)
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


# --- _evaluasi_llm_fallback (mocked LLM, TANPA network call nyata) ----------


def _buat_atomic_intent(
    label: LabelBentukJawaban = LabelBentukJawaban.TREN,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="tren booking dari mart_cleaned.bookings 3 bulan terakhir",
        label_bentuk_jawaban=label,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )


def _buat_kandidat(view_name: str) -> KandidatView:
    return KandidatView(view_name=view_name, domain=Domain.RESERVATION, skor=3.0, sumber=SumberPencarian.BM25)


def _buat_kecocokan_kandidat(
    view_name: str, label: LabelKecocokanMakna = LabelKecocokanMakna.DITEMUKAN
) -> KecocokanKandidat:
    return KecocokanKandidat(kandidat=_buat_kandidat(view_name), label=label, alasan="lolos M3.2")


class _FakeUsage:
    def __init__(self, prompt_tokens: int = 80, completion_tokens: int = 40):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content: str, choices: list | None = None):
        self.usage = _FakeUsage()
        self.choices = [_FakeChoice(content)] if choices is None else choices


def test_fallback_kosong_nol_panggilan_llm(monkeypatch):
    """Tidak ada kandidat tidak_pasti -> jalur pintas, TIDAK memanggil
    LLM sama sekali (dibuktikan monkeypatch raise, mirror pola
    pembuktian pre-filter M2.3/jalur pintas M3.2)."""
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "_call_llm_fallback",
        lambda ai, kk: (_ for _ in ()).throw(
            AssertionError("_call_llm_fallback TIDAK BOLEH dipanggil untuk batch kosong")
        ),
    )
    hasil = _evaluasi_llm_fallback(_buat_atomic_intent(), [])
    assert hasil == []


def test_fallback_sukses_normal(monkeypatch):
    kk = _buat_kecocokan_kandidat("v_lookup_bookings")
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_lookup_bookings",
                    "cukup": False,
                    "alasan": "row-level tanpa agregasi periode, tidak cukup untuk tren",
                }
            ]
        }
    )
    monkeypatch.setattr(
        kecukupan_struktural_module, "_call_llm_fallback", lambda ai, kk_list: _FakeChatResponse(raw)
    )

    hasil = _evaluasi_llm_fallback(_buat_atomic_intent(), [kk])

    assert len(hasil) == 1
    assert hasil[0].cukup is False
    assert hasil[0].sumber_keputusan == SumberKeputusanKecukupan.LLM
    assert hasil[0].kecocokan_label == LabelKecocokanMakna.DITEMUKAN


def test_fallback_api_error_default_aman_semua_tidak_cukup(monkeypatch):
    kk1 = _buat_kecocokan_kandidat("v_lookup_bookings")
    kk2 = _buat_kecocokan_kandidat("v_lookup_fnb_transactions")

    def _raise_api_error(ai, kk_list):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(kecukupan_struktural_module, "_call_llm_fallback", _raise_api_error)

    hasil = _evaluasi_llm_fallback(_buat_atomic_intent(), [kk1, kk2])

    assert len(hasil) == 2
    assert all(k.cukup is False for k in hasil)
    assert all(k.sumber_keputusan == SumberKeputusanKecukupan.LLM for k in hasil)


def test_fallback_empty_choices_default_aman_tidak_cukup(monkeypatch):
    kk = _buat_kecocokan_kandidat("v_lookup_bookings")
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "_call_llm_fallback",
        lambda ai, kk_list: _FakeChatResponse("", choices=[]),
    )

    hasil = _evaluasi_llm_fallback(_buat_atomic_intent(), [kk])

    assert len(hasil) == 1
    assert hasil[0].cukup is False


def test_fallback_json_rusak_default_aman_semua_tidak_cukup(monkeypatch):
    kk1 = _buat_kecocokan_kandidat("v_lookup_bookings")
    kk2 = _buat_kecocokan_kandidat("v_lookup_fnb_transactions")
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "_call_llm_fallback",
        lambda ai, kk_list: _FakeChatResponse("bukan json valid {{{"),
    )

    hasil = _evaluasi_llm_fallback(_buat_atomic_intent(), [kk1, kk2])

    assert len(hasil) == 2
    assert all(k.cukup is False for k in hasil)


def test_fallback_kandidat_hilang_dari_respons_default_aman_bukan_drop():
    """Respons SEBAGIAN valid (satu kandidat hilang) - kandidat yang
    hilang tetap muncul di keluaran dengan default aman cukup=False,
    BUKAN diam-diam dijatuhkan (jaminan struktural, mirror M3.2)."""
    kk1 = _buat_kecocokan_kandidat("v_lookup_bookings")
    kk2 = _buat_kecocokan_kandidat("v_lookup_fnb_transactions")
    raw = json.dumps(
        {
            "penilaian": [
                {"view_name": "v_lookup_bookings", "cukup": True, "alasan": "grain punya tanggal booking"}
            ]
        }
    )

    hasil, gagal = kecukupan_struktural_module._parse_fallback(raw, [kk1, kk2])

    assert gagal is False
    assert len(hasil) == 2
    by_view = {h.kandidat.view_name: h for h in hasil}
    assert by_view["v_lookup_bookings"].cukup is True
    assert by_view["v_lookup_fnb_transactions"].cukup is False
    assert "tidak muncul di respons" in by_view["v_lookup_fnb_transactions"].alasan
