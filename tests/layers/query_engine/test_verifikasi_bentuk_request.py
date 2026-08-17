"""Test orkestrator Verifikasi Bentuk Request (Milestone 3.5) -
src/layers/query_engine/verifikasi_bentuk_request.py. Nama file dipisah
dari test_query_engine_schema.py (Checkpoint 2, test skema) - mirror
preseden test_penyusunan_request.py vs *_schema.py (M3.4)."""

import json
import uuid

import src.layers.query_engine.verifikasi_bentuk_request as verifikasi_module
from openai import APIError
from src.layers.query_engine.verifikasi_bentuk_request import (
    _build_user_prompt,
    _parse_response,
    _view_name_sesuai_retriever,
    verifikasi_bentuk_request_atomic_intent,
    verifikasi_bentuk_request_semua,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest

_VIEW = "v_reservation_room_type_daily"
_VIEW_LAIN = "v_reservation_channel_daily"


def _buat_atomic_intent(
    teks: str = "okupansi Bali bulan lalu",
    label: LabelBentukJawaban = LabelBentukJawaban.NILAI_TUNGGAL,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_request(view_name: str = _VIEW, params: dict | None = None) -> QueryEngineRequest:
    return QueryEngineRequest(
        domain=Domain.RESERVATION,
        view_name=view_name,
        params=params if params is not None else {"property_id": "P01"},
    )


# --- _view_name_sesuai_retriever (pure function) ------------------------


def test_view_name_sesuai_retriever_cocok():
    assert _view_name_sesuai_retriever(_buat_request(_VIEW), _VIEW) is True


def test_view_name_sesuai_retriever_tidak_cocok():
    assert _view_name_sesuai_retriever(_buat_request(_VIEW), _VIEW_LAIN) is False


# --- _build_user_prompt (pure function) ---------------------------------


def test_build_user_prompt_memuat_params_dan_definisi():
    prompt = _build_user_prompt(
        _buat_atomic_intent(), _buat_request(_VIEW, {"property_id": "P01"})
    )
    assert _VIEW in prompt
    assert "property_id" in prompt
    assert "nilai_tunggal" in prompt


# --- _parse_response (pure function) ------------------------------------


def test_parse_response_lolos_true():
    raw = json.dumps({"lolos": True})
    lolos, alasan, gagal = _parse_response(raw)
    assert gagal is False
    assert lolos is True
    assert alasan is None


def test_parse_response_lolos_false_dengan_alasan():
    raw = json.dumps({"lolos": False, "alasan": "rentang tanggal hanya satu hari"})
    lolos, alasan, gagal = _parse_response(raw)
    assert gagal is False
    assert lolos is False
    assert alasan == "rentang tanggal hanya satu hari"


def test_parse_response_lolos_false_tanpa_alasan_pakai_fallback():
    raw = json.dumps({"lolos": False})
    lolos, alasan, gagal = _parse_response(raw)
    assert gagal is False
    assert lolos is False
    assert alasan is not None  # fallback generik, bukan None


def test_parse_response_json_rusak_gagal_true():
    lolos, alasan, gagal = _parse_response("bukan json valid {{{")
    assert gagal is True
    assert lolos is None
    assert alasan is None


def test_parse_response_skema_salah_gagal_true():
    lolos, alasan, gagal = _parse_response(json.dumps({"bukan_lolos_key": True}))
    assert gagal is True


# --- verifikasi_bentuk_request_atomic_intent (mocked LLM) ---------------


class _FakeUsage:
    def __init__(self, prompt_tokens: int = 200, completion_tokens: int = 30):
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


def test_pre_check_gagal_llm_tidak_pernah_dipanggil(monkeypatch):
    """Pre-check Kriteria 1 gagal -> lolos=False LANGSUNG, TANPA
    memanggil LLM sama sekali (decisions.md Keputusan 1 dan 3). Dibuktikan
    dengan monkeypatch _call_llm agar raise kalau terpanggil - mirror
    pola pembuktian pre-filter M2.3."""

    def _gagal_kalau_terpanggil(ai, request):
        raise AssertionError("_call_llm TIDAK BOLEH terpanggil saat pre-check gagal")

    monkeypatch.setattr(verifikasi_module, "_call_llm", _gagal_kalau_terpanggil)

    hasil = verifikasi_bentuk_request_atomic_intent(
        _buat_atomic_intent(), _VIEW, _buat_request(_VIEW_LAIN)
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.lolos is False
    assert hasil.alasan is not None
    assert _VIEW in hasil.alasan
    assert _VIEW_LAIN in hasil.alasan
    assert hasil.request.view_name == _VIEW_LAIN  # request tetap utuh, tidak diubah


def test_pre_check_lolos_llm_lolos_true(monkeypatch):
    raw = json.dumps({"lolos": True})
    monkeypatch.setattr(verifikasi_module, "_call_llm", lambda ai, req: _FakeChatResponse(raw))

    hasil = verifikasi_bentuk_request_atomic_intent(
        _buat_atomic_intent(), _VIEW, _buat_request(_VIEW)
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.lolos is True
    assert hasil.alasan is None
    assert hasil.request.view_name == _VIEW


def test_pre_check_lolos_llm_lolos_false_dengan_alasan(monkeypatch):
    raw = json.dumps({"lolos": False, "alasan": "rentang tanggal hanya satu hari, tidak cukup untuk tren"})
    monkeypatch.setattr(verifikasi_module, "_call_llm", lambda ai, req: _FakeChatResponse(raw))

    ai = _buat_atomic_intent(label=LabelBentukJawaban.TREN)
    hasil = verifikasi_bentuk_request_atomic_intent(ai, _VIEW, _buat_request(_VIEW))

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.lolos is False
    assert "tren" in hasil.alasan


def test_api_error_gagal_teknis(monkeypatch):
    def _raise(ai, req):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(verifikasi_module, "_call_llm", _raise)

    hasil = verifikasi_bentuk_request_atomic_intent(
        _buat_atomic_intent(), _VIEW, _buat_request(_VIEW)
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.lolos is None
    assert hasil.alasan is None
    assert hasil.request.view_name == _VIEW  # request tetap utuh meski gagal teknis


def test_empty_choices_gagal_teknis(monkeypatch):
    monkeypatch.setattr(
        verifikasi_module, "_call_llm", lambda ai, req: _FakeChatResponse("", choices=[])
    )

    hasil = verifikasi_bentuk_request_atomic_intent(
        _buat_atomic_intent(), _VIEW, _buat_request(_VIEW)
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS


def test_json_rusak_gagal_teknis(monkeypatch):
    monkeypatch.setattr(
        verifikasi_module,
        "_call_llm",
        lambda ai, req: _FakeChatResponse("bukan json valid {{{"),
    )

    hasil = verifikasi_bentuk_request_atomic_intent(
        _buat_atomic_intent(), _VIEW, _buat_request(_VIEW)
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS


# --- verifikasi_bentuk_request_semua (orkestrator batch) ----------------


def test_semua_statistik_agregat_campuran(monkeypatch):
    panggilan = {"n": 0}

    def _fake_call_llm(ai, req):
        panggilan["n"] += 1
        if panggilan["n"] == 1:
            return _FakeChatResponse(json.dumps({"lolos": True}))
        return _FakeChatResponse(json.dumps({"lolos": False, "alasan": "tidak cukup"}))

    monkeypatch.setattr(verifikasi_module, "_call_llm", _fake_call_llm)

    daftar = [
        (_buat_atomic_intent("kebutuhan 1"), _VIEW, _buat_request(_VIEW)),
        (_buat_atomic_intent("kebutuhan 2"), _VIEW, _buat_request(_VIEW)),
        (_buat_atomic_intent("kebutuhan 3"), _VIEW, _buat_request(_VIEW_LAIN)),  # pre-check gagal
    ]

    hasil = verifikasi_bentuk_request_semua(daftar)

    assert len(hasil) == 3
    assert hasil[0].lolos is True
    assert hasil[1].lolos is False
    assert hasil[2].lolos is False  # dari pre-check, bukan LLM
    assert panggilan["n"] == 2  # item ke-3 tidak pernah memanggil LLM
