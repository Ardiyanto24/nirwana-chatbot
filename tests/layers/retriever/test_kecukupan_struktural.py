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
from src.layers.retriever.kecukupan_struktural import (
    _evaluasi_deterministik,
    _evaluasi_llm_fallback,
    evaluasi_kecukupan_struktural_atomic_intent,
    proses_retrieval_atomic_intent,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import (
    HasilKecocokanMakna,
    HasilKecukupanStruktural,
    HasilPencarianKandidat,
    KandidatView,
    KecocokanKandidat,
    KecukupanKandidat,
    LabelKecocokanMakna,
    SumberKeputusanKecukupan,
    SumberPencarian,
)
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


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


def _buat_kandidat(view_name: str, skor: float = 3.0) -> KandidatView:
    return KandidatView(view_name=view_name, domain=Domain.RESERVATION, skor=skor, sumber=SumberPencarian.BM25)


def _buat_kecocokan_kandidat(
    view_name: str, label: LabelKecocokanMakna = LabelKecocokanMakna.DITEMUKAN, skor: float = 3.0
) -> KecocokanKandidat:
    return KecocokanKandidat(kandidat=_buat_kandidat(view_name, skor), label=label, alasan="lolos M3.2")


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


# --- evaluasi_kecukupan_struktural_atomic_intent (orkestrator per-item) ----


def _buat_hasil_kecocokan(
    kecocokan: list[KecocokanKandidat], label_bentuk_jawaban: LabelBentukJawaban = LabelBentukJawaban.TREN
) -> HasilKecocokanMakna:
    return HasilKecocokanMakna(
        atomic_intent=_buat_atomic_intent(label_bentuk_jawaban),
        kecocokan=kecocokan,
        status=StatusEksekusi.BERHASIL,
    )


def test_orkestrator_seluruh_deterministik_nol_panggilan_llm(monkeypatch):
    """v_reservation_room_type_daily: punya_time_series=ya (GRAIN_STRUKTURAL_VIEW)
    -> tren cukup murni rule table, TIDAK PERNAH menyentuh fallback LLM -
    dibuktikan monkeypatch _call_llm_fallback raise (mirror pola pembuktian
    jalur pintas M2.3/M3.1/M3.2)."""
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "_call_llm_fallback",
        lambda ai, kk: (_ for _ in ()).throw(
            AssertionError("_call_llm_fallback TIDAK BOLEH dipanggil untuk kandidat deterministik murni")
        ),
    )
    hasil_kecocokan = _buat_hasil_kecocokan(
        [_buat_kecocokan_kandidat("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]
    )

    hasil = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.view_name_final == "v_reservation_room_type_daily"
    assert hasil.kecukupan[0].sumber_keputusan == SumberKeputusanKecukupan.DETERMINISTIK


def test_orkestrator_sebagian_butuh_fallback_llm(monkeypatch):
    """v_lookup_bookings: punya_time_series=tidak_pasti -> rule table jatuh
    tidak_pasti, WAJIB lewat fallback LLM. Kombinasikan dengan kandidat
    deterministik murni (v_reservation_channel_daily, time_series=ya) dalam
    satu batch - bukti kedua jalur bisa hidup berdampingan per kebutuhan
    atomik yang sama."""
    kk_deterministik = _buat_kecocokan_kandidat(
        "v_reservation_channel_daily", LabelKecocokanMakna.SEBAGIAN
    )
    kk_ambigu = _buat_kecocokan_kandidat("v_lookup_bookings", LabelKecocokanMakna.DITEMUKAN)

    raw = json.dumps(
        {"penilaian": [{"view_name": "v_lookup_bookings", "cukup": False, "alasan": "row-level, tidak cukup untuk tren"}]}
    )
    monkeypatch.setattr(
        kecukupan_struktural_module, "_call_llm_fallback", lambda ai, kk: _FakeChatResponse(raw)
    )

    hasil_kecocokan = _buat_hasil_kecocokan([kk_deterministik, kk_ambigu])
    hasil = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

    by_view = {k.kandidat.view_name: k for k in hasil.kecukupan}
    assert by_view["v_reservation_channel_daily"].sumber_keputusan == SumberKeputusanKecukupan.DETERMINISTIK
    assert by_view["v_reservation_channel_daily"].cukup is True
    assert by_view["v_lookup_bookings"].sumber_keputusan == SumberKeputusanKecukupan.LLM
    assert by_view["v_lookup_bookings"].cukup is False
    # Tie-break: hanya v_reservation_channel_daily yang cukup -> dia yang final.
    assert hasil.view_name_final == "v_reservation_channel_daily"


def test_orkestrator_tidak_ada_kandidat_cukup_view_name_final_none():
    """v_properties_ref: punya_time_series=tidak (deterministik pasti,
    TANPA fallback LLM) -> tidak_cukup untuk tren, tidak ada kandidat lain
    -> view_name_final=None, bukan error."""
    hasil_kecocokan = _buat_hasil_kecocokan(
        [_buat_kecocokan_kandidat("v_properties_ref", LabelKecocokanMakna.SEBAGIAN)]
    )

    hasil = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

    assert hasil.view_name_final is None
    assert hasil.kecukupan[0].cukup is False
    assert hasil.status == StatusEksekusi.BERHASIL


def test_orkestrator_label_tidak_ditemukan_dikecualikan_dari_evaluasi():
    """Keputusan 3: kandidat berlabel tidak_ditemukan (M3.2) TIDAK ikut
    dievaluasi strukturnya sama sekali."""
    hasil_kecocokan = _buat_hasil_kecocokan(
        [_buat_kecocokan_kandidat("v_reservation_room_type_daily", LabelKecocokanMakna.TIDAK_DITEMUKAN)]
    )

    hasil = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

    assert hasil.kecukupan == []
    assert hasil.view_name_final is None


def test_orkestrator_tie_break_label_ditemukan_menang_atas_sebagian():
    """Dua kandidat sama-sama cukup (tren, keduanya time_series=ya) tapi
    label M3.2 beda - DITEMUKAN wajib menang meski skor lebih rendah."""
    kk_ditemukan = _buat_kecocokan_kandidat(
        "v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN, skor=1.0
    )
    kk_sebagian = _buat_kecocokan_kandidat(
        "v_reservation_channel_daily", LabelKecocokanMakna.SEBAGIAN, skor=9.0
    )

    hasil_kecocokan = _buat_hasil_kecocokan([kk_ditemukan, kk_sebagian])
    hasil = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

    assert hasil.view_name_final == "v_reservation_room_type_daily"


def test_orkestrator_tie_break_skor_tertinggi_menang_saat_label_sama():
    """Dua kandidat sama-sama cukup DAN sama-sama label DITEMUKAN - skor
    KandidatView (M3.1) tertinggi yang menang."""
    kk_skor_rendah = _buat_kecocokan_kandidat(
        "v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN, skor=2.0
    )
    kk_skor_tinggi = _buat_kecocokan_kandidat(
        "v_reservation_channel_daily", LabelKecocokanMakna.DITEMUKAN, skor=8.0
    )

    hasil_kecocokan = _buat_hasil_kecocokan([kk_skor_rendah, kk_skor_tinggi])
    hasil = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

    assert hasil.view_name_final == "v_reservation_channel_daily"


# --- proses_retrieval_atomic_intent (orkestrator penutup pipeline M3.1-3.3) -


def _buat_hasil_pencarian(kandidat: list[KandidatView]) -> HasilPencarianKandidat:
    return HasilPencarianKandidat(
        atomic_intent=_buat_atomic_intent(),
        domain_diizinkan=[Domain.RESERVATION],
        kandidat=kandidat,
        fallback_terpicu=False,
        status=StatusEksekusi.BERHASIL,
    )


def test_pipeline_urutan_panggilan_dan_hasil_akhir_konsisten(monkeypatch):
    """Bukti proses_retrieval_atomic_intent() memanggil M3.1(pure) ->
    M3.2 -> M3.3 dalam urutan yang benar, dan hasil akhir persis hasil
    evaluasi_kecukupan_struktural_atomic_intent() (M3.3) - bukan hasil
    tahap lain yang tercampur."""
    urutan_panggilan: list[str] = []

    hasil_pencarian_fixture = _buat_hasil_pencarian(
        [_buat_kandidat("v_reservation_room_type_daily")]
    )
    hasil_kecocokan_fixture = _buat_hasil_kecocokan(
        [_buat_kecocokan_kandidat("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]
    )
    hasil_kecukupan_fixture = HasilKecukupanStruktural(
        atomic_intent=hasil_kecocokan_fixture.atomic_intent,
        kecukupan=[
            KecukupanKandidat(
                kandidat=_buat_kandidat("v_reservation_room_type_daily"),
                kecocokan_label=LabelKecocokanMakna.DITEMUKAN,
                cukup=True,
                alasan="grain time-series jelas",
                sumber_keputusan=SumberKeputusanKecukupan.DETERMINISTIK,
            )
        ],
        view_name_final="v_reservation_room_type_daily",
        status=StatusEksekusi.BERHASIL,
    )

    def _fake_kumpulkan_kandidat(atomic_intent, domain_diizinkan):
        urutan_panggilan.append("m3.1")
        return hasil_pencarian_fixture

    def _fake_nilai_kecocokan(hasil_pencarian):
        urutan_panggilan.append("m3.2")
        assert hasil_pencarian is hasil_pencarian_fixture
        return hasil_kecocokan_fixture

    def _fake_evaluasi_kecukupan(hasil_kecocokan):
        urutan_panggilan.append("m3.3")
        assert hasil_kecocokan is hasil_kecocokan_fixture
        return hasil_kecukupan_fixture

    monkeypatch.setattr(kecukupan_struktural_module, "_kumpulkan_kandidat", _fake_kumpulkan_kandidat)
    monkeypatch.setattr(
        kecukupan_struktural_module, "nilai_kecocokan_makna_atomic_intent", _fake_nilai_kecocokan
    )
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "evaluasi_kecukupan_struktural_atomic_intent",
        _fake_evaluasi_kecukupan,
    )

    hasil = proses_retrieval_atomic_intent(_buat_atomic_intent(), [Domain.RESERVATION])

    assert urutan_panggilan == ["m3.1", "m3.2", "m3.3"]
    assert hasil is hasil_kecukupan_fixture
    assert hasil.view_name_final == "v_reservation_room_type_daily"


def test_pipeline_view_name_final_none_tidak_error(monkeypatch):
    """Kasus tidak ada kandidat cukup sama sekali - pipeline tetap
    selesai normal, retrieval.selected_view diisi string kosong (bukan
    exception saat span.set_attribute dipanggil dengan None)."""
    hasil_pencarian_fixture = _buat_hasil_pencarian([_buat_kandidat("v_properties_ref")])
    hasil_kecocokan_fixture = _buat_hasil_kecocokan(
        [_buat_kecocokan_kandidat("v_properties_ref", LabelKecocokanMakna.SEBAGIAN)]
    )
    hasil_kecukupan_fixture = HasilKecukupanStruktural(
        atomic_intent=hasil_kecocokan_fixture.atomic_intent,
        kecukupan=[
            KecukupanKandidat(
                kandidat=_buat_kandidat("v_properties_ref"),
                kecocokan_label=LabelKecocokanMakna.SEBAGIAN,
                cukup=False,
                alasan="tabel referensi murni, tidak cukup untuk tren",
                sumber_keputusan=SumberKeputusanKecukupan.DETERMINISTIK,
            )
        ],
        view_name_final=None,
        status=StatusEksekusi.BERHASIL,
    )

    monkeypatch.setattr(
        kecukupan_struktural_module, "_kumpulkan_kandidat", lambda ai, dd: hasil_pencarian_fixture
    )
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "nilai_kecocokan_makna_atomic_intent",
        lambda hp: hasil_kecocokan_fixture,
    )
    monkeypatch.setattr(
        kecukupan_struktural_module,
        "evaluasi_kecukupan_struktural_atomic_intent",
        lambda hk: hasil_kecukupan_fixture,
    )

    hasil = proses_retrieval_atomic_intent(_buat_atomic_intent(), [Domain.RESERVATION])

    assert hasil.view_name_final is None
