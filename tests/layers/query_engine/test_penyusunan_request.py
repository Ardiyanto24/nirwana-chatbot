"""Test orkestrator Penyusunan Request (Milestone 3.4) -
src/layers/query_engine/penyusunan_request.py. Nama file dipisah dari
test_query_engine_schema.py (Checkpoint 3, test skema) - mirror
preseden test_kecukupan_struktural.py vs *_schema.py (M3.3)."""

import json
import uuid
from datetime import date

from openai import APIError

import src.layers.query_engine.penyusunan_request as penyusunan_request_module
from src.layers.query_engine.penyusunan_request import (
    _build_user_prompt,
    _parse_response,
    _saring_params_tidak_dikenal,
    susun_request_atomic_intent,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi

_VIEW = "v_reservation_room_type_daily"
_TANGGAL_TETAP = date(2026, 7, 15)


def _buat_atomic_intent(teks: str = "okupansi Bali bulan lalu") -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


# --- _build_user_prompt (pure function) --------------------------------


def test_build_user_prompt_memuat_tanggal_referensi_dan_whitelist():
    prompt = _build_user_prompt(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)
    assert "2026-07-15" in prompt
    assert "period_date_from" in prompt
    assert "room_type_name" in prompt
    assert (
        "employee_id" not in prompt
    )  # tidak pernah masuk whitelist, tidak muncul di daftar


def test_build_user_prompt_tanpa_feedback_tidak_memuat_perhatian():
    prompt = _build_user_prompt(
        _buat_atomic_intent(), _VIEW, _TANGGAL_TETAP, feedback=None
    )
    assert "PERHATIAN" not in prompt


def test_build_user_prompt_dengan_feedback_menyisipkan_perhatian():
    prompt = _build_user_prompt(
        _buat_atomic_intent(),
        _VIEW,
        _TANGGAL_TETAP,
        feedback="parameter 'room_type_name' tidak dikenal server",
    )
    assert "PERHATIAN" in prompt
    assert "parameter 'room_type_name' tidak dikenal server" in prompt


# --- _parse_response (pure function) ------------------------------------


def test_parse_response_sukses():
    raw = json.dumps(
        {"params": {"property_id": "P01", "period_date_from": "2026-06-01"}}
    )
    params, gagal = _parse_response(raw)
    assert gagal is False
    assert params == {"property_id": "P01", "period_date_from": "2026-06-01"}


def test_parse_response_json_rusak_gagal_true():
    params, gagal = _parse_response("bukan json valid {{{")
    assert gagal is True
    assert params is None


def test_parse_response_skema_salah_gagal_true():
    params, gagal = _parse_response(json.dumps({"bukan_params_key": {}}))
    assert gagal is True


# --- _saring_params_tidak_dikenal (pure function) -----------------------


def test_saring_params_key_valid_lolos():
    hasil, dibuang = _saring_params_tidak_dikenal(
        _VIEW, {"property_id": "P01", "room_type_name": "Suite"}
    )
    assert hasil == {"property_id": "P01", "room_type_name": "Suite"}
    assert dibuang == []


def test_saring_params_key_tidak_dikenal_dibuang():
    hasil, dibuang = _saring_params_tidak_dikenal(
        _VIEW, {"property_id": "P01", "kolom_karangan_llm": "nilai"}
    )
    assert hasil == {"property_id": "P01"}
    assert dibuang == ["kolom_karangan_llm"]


def test_saring_params_employee_id_selalu_dibuang():
    """employee_id TIDAK PERNAH lolos ke request.params, meski kebetulan
    ada di daftar kolom view (defense in depth, decisions.md Keputusan 7)."""
    hasil, dibuang = _saring_params_tidak_dikenal(
        _VIEW, {"employee_id": "E0001", "property_id": "P01"}
    )
    assert "employee_id" not in hasil
    assert "employee_id" in dibuang
    assert hasil == {"property_id": "P01"}


def test_saring_params_role_title_domain_view_name_selalu_dibuang():
    hasil, dibuang = _saring_params_tidak_dikenal(
        _VIEW,
        {
            "role_title": "CEO",
            "domain": "reservation",
            "view_name": _VIEW,
            "property_id": "P01",
        },
    )
    assert hasil == {"property_id": "P01"}
    assert set(dibuang) == {"role_title", "domain", "view_name"}


# --- susun_request_atomic_intent (mocked LLM, TANPA network call nyata) -


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


def test_orkestrator_sukses_normal(monkeypatch):
    raw = json.dumps(
        {
            "params": {
                "property_id": "P01",
                "period_date_from": "2026-06-01",
                "period_date_to": "2026-06-30",
            }
        }
    )
    monkeypatch.setattr(
        penyusunan_request_module,
        "_call_llm",
        lambda ai, vn, tr, fb=None: _FakeChatResponse(raw),
    )

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.request is not None
    assert hasil.request.domain == Domain.RESERVATION
    assert hasil.request.view_name == _VIEW
    assert hasil.request.params == {
        "property_id": "P01",
        "period_date_from": "2026-06-01",
        "period_date_to": "2026-06-30",
    }


def test_orkestrator_domain_diturunkan_kode_tanpa_ditanyakan_llm(monkeypatch):
    """Mock LLM sama sekali TIDAK diberi tahu apa domain-nya - hasil
    domain tetap benar karena diturunkan view_ke_domain(), bukan
    ditanyakan ke LLM."""
    raw = json.dumps({"params": {}})
    dipanggil_dengan = {}

    def _fake_call_llm(ai, vn, tr, fb=None):
        dipanggil_dengan["view_name"] = vn
        return _FakeChatResponse(raw)

    monkeypatch.setattr(penyusunan_request_module, "_call_llm", _fake_call_llm)

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert hasil.request.domain == Domain.RESERVATION
    assert (
        "view_name" in dipanggil_dengan
    )  # _call_llm hanya terima view_name, bukan domain


def test_orkestrator_api_error_gagal_teknis(monkeypatch):
    def _raise(ai, vn, tr, fb=None):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(penyusunan_request_module, "_call_llm", _raise)

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.request is None


def test_orkestrator_empty_choices_gagal_teknis(monkeypatch):
    monkeypatch.setattr(
        penyusunan_request_module,
        "_call_llm",
        lambda ai, vn, tr, fb=None: _FakeChatResponse("", choices=[]),
    )

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS


def test_orkestrator_json_rusak_gagal_teknis(monkeypatch):
    monkeypatch.setattr(
        penyusunan_request_module,
        "_call_llm",
        lambda ai, vn, tr, fb=None: _FakeChatResponse("bukan json valid {{{"),
    )

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS


def test_orkestrator_key_tidak_dikenal_tersaring_dari_request_final(monkeypatch):
    raw = json.dumps({"params": {"property_id": "P01", "kolom_karangan": "nilai"}})
    monkeypatch.setattr(
        penyusunan_request_module,
        "_call_llm",
        lambda ai, vn, tr, fb=None: _FakeChatResponse(raw),
    )

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert "kolom_karangan" not in hasil.request.params
    assert hasil.request.params == {"property_id": "P01"}


def test_orkestrator_employee_id_dari_llm_tidak_pernah_lolos(monkeypatch):
    raw = json.dumps({"params": {"employee_id": "E0001", "property_id": "P01"}})
    monkeypatch.setattr(
        penyusunan_request_module,
        "_call_llm",
        lambda ai, vn, tr, fb=None: _FakeChatResponse(raw),
    )

    hasil = susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert "employee_id" not in hasil.request.params


def test_orkestrator_feedback_diteruskan_ke_call_llm(monkeypatch):
    """Milestone 4.2: feedback dari penolakan chatbot_api sebelumnya
    (400) wajib benar-benar sampai ke _call_llm(), bukan cuma diterima
    lalu dibuang."""
    raw = json.dumps({"params": {"property_id": "P01"}})
    diterima: dict = {}

    def _fake_call_llm(ai, vn, tr, fb=None):
        diterima["feedback"] = fb
        return _FakeChatResponse(raw)

    monkeypatch.setattr(penyusunan_request_module, "_call_llm", _fake_call_llm)

    susun_request_atomic_intent(
        _buat_atomic_intent(),
        _VIEW,
        _TANGGAL_TETAP,
        feedback="alasan penolakan chatbot_api",
    )

    assert diterima["feedback"] == "alasan penolakan chatbot_api"


def test_orkestrator_feedback_default_none(monkeypatch):
    raw = json.dumps({"params": {}})
    diterima: dict = {}

    def _fake_call_llm(ai, vn, tr, fb=None):
        diterima["feedback"] = fb
        return _FakeChatResponse(raw)

    monkeypatch.setattr(penyusunan_request_module, "_call_llm", _fake_call_llm)

    susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, _TANGGAL_TETAP)

    assert diterima["feedback"] is None


def test_orkestrator_tanggal_referensi_default_terpakai_kalau_tidak_diberikan(
    monkeypatch,
):
    """tanggal_referensi=None -> default dihitung server-side, bukan
    error/None diteruskan mentah ke _call_llm."""
    tanggal_dipakai = {}

    def _fake_call_llm(ai, vn, tr, fb=None):
        tanggal_dipakai["tr"] = tr
        return _FakeChatResponse(json.dumps({"params": {}}))

    monkeypatch.setattr(penyusunan_request_module, "_call_llm", _fake_call_llm)

    susun_request_atomic_intent(_buat_atomic_intent(), _VIEW, tanggal_referensi=None)

    assert isinstance(tanggal_dipakai["tr"], date)
