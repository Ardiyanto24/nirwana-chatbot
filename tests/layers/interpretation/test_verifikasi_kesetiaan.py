"""Test orkestrator Verifikasi Kesetiaan Data + Penyusunan Visualisasi
(Milestone 4.5) - src/layers/interpretation/verifikasi_kesetiaan.py.
`_call_llm` di-monkeypatch (mirror pola test_verifikasi_bentuk_request.py
M3.5, test_narasi.py M4.4) - modul ini TIDAK butuh network call nyata
untuk diuji, panggilan LLM sungguhan sudah dibuktikan manual Checkpoint 4
(lihat logs.md) dan dibuktikan lebih luas lewat evals/ (Checkpoint 8).
"""

import uuid

import pytest
from openai import APIError

import src.layers.interpretation.verifikasi_kesetiaan as modul
from src.layers.interpretation.verifikasi_kesetiaan import (
    verifikasi_dan_susun_visualisasi,
    verifikasi_kesetiaan_narasi,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.interpretation import HasilVerifikasiNarasi
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage, StatusEksekusi


def _buat_atomic_intent(teks: str = "kebutuhan") -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_paket(atomic_intent_id: str) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent_id,
        session_id="s1",
        turn_index=1,
        teks_kebutuhan="teks",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": [{"nilai": 1}]},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


# --- mocked LLM (mirror test_verifikasi_bentuk_request.py M3.5) ---------


class _FakeUsage:
    def __init__(self, prompt_tokens: int = 300, completion_tokens: int = 50):
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


class _SpanRekam:
    def __init__(self):
        self.atribut: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, key, value):
        self.atribut[key] = value


class _TracerRekam:
    def __init__(self):
        self.span = _SpanRekam()

    def start_as_current_span(self, nama):
        return self.span


def _patch_tracer(monkeypatch) -> _TracerRekam:
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)
    return tracer_rekam


# --- verifikasi_kesetiaan_narasi ------------------------------------------


def test_lolos_true(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse('{"lolos": true}')
    )

    hasil = verifikasi_kesetiaan_narasi("narasi jujur", [ai], [paket], session_id="s1", turn_index=1)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.lolos is True
    assert hasil.alasan is None
    assert hasil.narasi == "narasi jujur"


def test_lolos_false_dengan_alasan(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    raw = '{"lolos": false, "alasan": "ada klaim sebab-akibat tak berdasar"}'
    monkeypatch.setattr(modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse(raw))

    hasil = verifikasi_kesetiaan_narasi("narasi buruk", [ai], [paket], session_id="s1", turn_index=1)

    assert hasil.lolos is False
    assert hasil.alasan == "ada klaim sebab-akibat tak berdasar"


def test_lolos_false_tanpa_alasan_dari_llm_dapat_fallback_generik(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse('{"lolos": false}')
    )

    hasil = verifikasi_kesetiaan_narasi("x", [ai], [paket], session_id="s1", turn_index=1)

    assert hasil.lolos is False
    assert hasil.alasan is not None


def test_api_error_fallback_aman_gagal_teknis(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)

    def _raise(narasi, ais, pks):
        raise APIError("simulasi", request=None, body=None)

    monkeypatch.setattr(modul, "_call_llm", _raise)

    hasil = verifikasi_kesetiaan_narasi("x", [ai], [paket], session_id="s1", turn_index=1)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.lolos is None
    assert hasil.alasan is None


def test_json_rusak_gagal_teknis(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse("bukan json valid {{{")
    )

    hasil = verifikasi_kesetiaan_narasi("x", [ai], [paket], session_id="s1", turn_index=1)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS


def test_empty_choices_gagal_teknis(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse("", choices=[])
    )

    hasil = verifikasi_kesetiaan_narasi("x", [ai], [paket], session_id="s1", turn_index=1)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS


def test_atribut_span_terisi_sesuai_kontrak(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse('{"lolos": true}')
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    verifikasi_kesetiaan_narasi("x", [ai], [paket], session_id="s1", turn_index=7)

    atribut = tracer_rekam.span.atribut
    assert atribut["session.id"] == "s1"
    assert atribut["turn.index"] == 7
    assert atribut["gen_ai.operation.name"] == "chat"
    assert atribut["gen_ai.request.model"] == "deepseek/deepseek-v4-pro-0813"
    assert atribut["prompt.id"] == "interpretation.verifikasi_kesetiaan"
    assert atribut["prompt.version"] == 2
    assert atribut["gen_ai.usage.input_tokens"] == 300
    assert atribut["gen_ai.usage.output_tokens"] == 50
    assert atribut["interpretation.verifikasi_kesetiaan.lolos"] is True


# --- verifikasi_dan_susun_visualisasi (orkestrator) -----------------------


def test_orkestrator_lolos_true_visualisasi_terisi(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse('{"lolos": true}')
    )

    hasil_verifikasi, visualisasi = verifikasi_dan_susun_visualisasi(
        "x", [ai], [paket], session_id="s1", turn_index=1
    )

    assert isinstance(hasil_verifikasi, HasilVerifikasiNarasi)
    assert hasil_verifikasi.lolos is True
    assert visualisasi is not None
    assert len(visualisasi) == 1
    assert visualisasi[0].atomic_intent_id == ai.atomic_intent_id


def test_orkestrator_lolos_false_visualisasi_none_dan_tidak_dipanggil(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    raw = '{"lolos": false, "alasan": "data hilang dari narasi"}'
    monkeypatch.setattr(modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse(raw))

    dipanggil = {"count": 0}

    def _spy(packages):
        dipanggil["count"] += 1
        return []

    monkeypatch.setattr(modul, "susun_data_visualisasi_semua", _spy)

    hasil_verifikasi, visualisasi = verifikasi_dan_susun_visualisasi(
        "x", [ai], [paket], session_id="s1", turn_index=1
    )

    assert hasil_verifikasi.lolos is False
    assert visualisasi is None
    assert dipanggil["count"] == 0, "susun_data_visualisasi_semua() TIDAK boleh dipanggil saat lolos=False"


def test_orkestrator_gagal_teknis_visualisasi_none(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)

    def _raise(narasi, ais, pks):
        raise APIError("simulasi", request=None, body=None)

    monkeypatch.setattr(modul, "_call_llm", _raise)

    hasil_verifikasi, visualisasi = verifikasi_dan_susun_visualisasi(
        "x", [ai], [paket], session_id="s1", turn_index=1
    )

    assert hasil_verifikasi.status == StatusEksekusi.GAGAL_TEKNIS
    assert visualisasi is None


@pytest.mark.parametrize("lolos_value", [True, False])
def test_narasi_disalin_utuh_ke_hasil(monkeypatch, lolos_value):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    raw = (
        '{"lolos": true}'
        if lolos_value
        else '{"lolos": false, "alasan": "sesuatu tidak setia"}'
    )
    monkeypatch.setattr(modul, "_call_llm", lambda n, ais, pks: _FakeChatResponse(raw))

    hasil = verifikasi_kesetiaan_narasi(
        "narasi persis ini", [ai], [paket], session_id="s1", turn_index=1
    )

    assert hasil.narasi == "narasi persis ini"
