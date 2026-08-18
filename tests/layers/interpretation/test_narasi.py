"""Test orkestrator Penyusunan Narasi (Milestone 4.4) -
src/layers/interpretation/narasi.py. `_call_llm` di-monkeypatch (mirror
pola test_penyusunan_request.py, M3.4) - modul ini TIDAK butuh network
call nyata untuk diuji, panggilan LLM sungguhan sudah dibuktikan manual
Checkpoint 4 (lihat logs.md) dan dibuktikan lebih luas lewat evals/
(Checkpoint 6-7). Tracer di-monkeypatch (_TracerRekam, mirror pola
test_klasifikasi_respons.py M4.2) supaya atribut span bisa diverifikasi
in-process tanpa Jaeger/Docker hidup.
"""

import uuid

import pytest
from openai import APIError

import src.layers.interpretation.narasi as modul
from src.layers.interpretation.narasi import (
    _build_user_prompt,
    _turn_reference,
    susun_narasi,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.interpretation import HasilNarasi
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)


def _buat_atomic_intent(
    teks: str = "okupansi Bali bulan lalu",
    relasi: RelasiKebutuhan = RelasiKebutuhan.INDEPENDEN,
    bergantung_pada: list[str] | None = None,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=relasi,
        bergantung_pada=bergantung_pada,
    )


def _buat_paket(
    atomic_intent_id: str,
    status: StatusEksekusi = StatusEksekusi.BERHASIL,
    sumber: str = "eksekusi_baru",
    catatan_interpretasi: list[str] | None = None,
    turn_index: int = 5,
) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent_id,
        session_id="s1",
        turn_index=turn_index,
        teks_kebutuhan="teks",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": [{"nilai": 1}]},
        catatan_interpretasi=catatan_interpretasi or [],
        status=status,
        sumber=sumber,
    )


# --- _turn_reference (pure function) -------------------------------------


def test_turn_reference_kosong_kalau_seluruh_eksekusi_baru():
    p1 = _buat_paket("a1", sumber="eksekusi_baru")
    p2 = _buat_paket("a2", sumber="eksekusi_baru")
    assert _turn_reference([p1, p2]) == []


def test_turn_reference_unik_dan_terurut():
    p1 = _buat_paket("a1", sumber="session_memory (turn 5)")
    p2 = _buat_paket("a2", sumber="session_memory (turn 3)")
    p3 = _buat_paket("a3", sumber="session_memory (turn 5)")  # duplikat turn 5
    assert _turn_reference([p1, p2, p3]) == [3, 5]


# --- _build_user_prompt (pure function) -----------------------------------


def test_build_user_prompt_memuat_status_sumber_dan_catatan():
    ai = _buat_atomic_intent()
    paket = _buat_paket(
        ai.atomic_intent_id,
        status=StatusEksekusi.SEBAGIAN,
        sumber="session_memory (turn 2)",
        catatan_interpretasi=["data belum diperbarui baru-baru ini"],
    )
    prompt = _build_user_prompt([ai], [paket])

    assert ai.teks_kebutuhan in prompt
    assert "sebagian" in prompt
    assert "session_memory (turn 2)" in prompt
    assert "data belum diperbarui baru-baru ini" in prompt


def test_build_user_prompt_menyertakan_relasi_bergantung_pada():
    ai_prasyarat = _buat_atomic_intent(teks="occupancy rate April 2026")
    ai_bergantung = _buat_atomic_intent(
        teks="bandingkan dengan Maret 2026",
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=[ai_prasyarat.atomic_intent_id],
    )
    paket_prasyarat = _buat_paket(ai_prasyarat.atomic_intent_id, status=StatusEksekusi.GAGAL_TEKNIS)
    paket_bergantung = _buat_paket(
        ai_bergantung.atomic_intent_id, status=StatusEksekusi.TERBLOKIR_KETERGANTUNGAN
    )

    prompt = _build_user_prompt(
        [ai_prasyarat, ai_bergantung], [paket_prasyarat, paket_bergantung]
    )

    assert "Bergantung pada" in prompt
    assert ai_prasyarat.teks_kebutuhan in prompt
    assert "gagal_teknis" in prompt  # status prasyarat ikut disebut


def test_build_user_prompt_tanpa_package_pasangan_raise_value_error():
    ai = _buat_atomic_intent()
    with pytest.raises(ValueError, match="kontrak 1:1 dilanggar"):
        _build_user_prompt([ai], [])


# --- susun_narasi (mocked LLM, TANPA network call nyata) ------------------


class _FakeUsage:
    def __init__(self, prompt_tokens: int = 500, completion_tokens: int = 120):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content: str, usage: _FakeUsage | None = None):
        self.usage = _FakeUsage() if usage is None else usage
        self.choices = [_FakeChoice(content)]


class _SpanRekam:
    """Mirror pola _SpanRekam/_TracerRekam di test_klasifikasi_respons.py
    (M4.2) - verifikasi atribut span in-process, TIDAK butuh Jaeger/Docker
    hidup."""

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


def test_susun_narasi_sukses_normal(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)
    monkeypatch.setattr(
        modul, "_call_llm", lambda ais, pks: _FakeChatResponse("Narasi jawaban akhir.")
    )

    hasil = susun_narasi([ai], [paket], session_id="s1", turn_index=5)

    assert isinstance(hasil, HasilNarasi)
    assert hasil.narasi == "Narasi jawaban akhir."


def test_susun_narasi_atribut_span_terisi_sesuai_kontrak(monkeypatch):
    ai_baru = _buat_atomic_intent()
    ai_lama = _buat_atomic_intent(teks="kebutuhan lama")
    paket_baru = _buat_paket(ai_baru.atomic_intent_id, sumber="eksekusi_baru")
    paket_lama = _buat_paket(ai_lama.atomic_intent_id, sumber="session_memory (turn 3)")

    monkeypatch.setattr(
        modul, "_call_llm", lambda ais, pks: _FakeChatResponse("Narasi.", _FakeUsage(500, 120))
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    susun_narasi([ai_baru, ai_lama], [paket_baru, paket_lama], session_id="s1", turn_index=5)

    atribut = tracer_rekam.span.atribut
    assert atribut["session.id"] == "s1"
    assert atribut["turn.index"] == 5
    assert atribut["gen_ai.operation.name"] == "chat"
    assert atribut["gen_ai.request.model"] == "qwen/qwen3-32b"
    assert atribut["prompt.id"] == "interpretation.narasi"
    assert atribut["prompt.version"] == 1
    assert atribut["narrative.turn_reference"] == [3]
    assert atribut["gen_ai.usage.input_tokens"] == 500
    assert atribut["gen_ai.usage.output_tokens"] == 120
    assert "error.type" not in atribut


def test_susun_narasi_api_error_diteruskan_dan_error_type_tercatat(monkeypatch):
    ai = _buat_atomic_intent()
    paket = _buat_paket(ai.atomic_intent_id)

    def _raise(ais, pks):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(modul, "_call_llm", _raise)
    tracer_rekam = _patch_tracer(monkeypatch)

    with pytest.raises(APIError):
        susun_narasi([ai], [paket], session_id="s1", turn_index=5)

    assert tracer_rekam.span.atribut["error.type"] == "gagal_teknis"
