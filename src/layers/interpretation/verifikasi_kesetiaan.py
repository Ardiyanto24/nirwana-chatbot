"""Verifikasi Kesetiaan Data + Orkestrator Visualisasi (Milestone 4.5,
Interpretation Langkah 14).

Menilai ulang SECARA INDEPENDEN narasi hasil M4.4 (`susun_narasi()`)
terhadap data sumber yang sama - TIDAK melihat proses penyusunannya.
SATU pemanggilan LLM (DeepSeek V4 Pro `reasoning="high"`), TANPA retry
balik ke `susun_narasi()` - mirror preseden persis `verifikasi_bentuk_
request.py` (M3.5): jalur perbaikan di luar cakupan milestone ini, lihat
decisions.md Keputusan 2.

`_build_user_prompt()` REUSE dari `narasi.py` (Keputusan 5) - verifier
butuh konteks ground-truth yang PERSIS sama dipakai menyusun narasi.

`verifikasi_dan_susun_visualisasi()` adalah orkestrator gabungan
(Keputusan 10, BEDA dari Keputusan 2 - sekuens verify->visualisasi
eksplisit satu Lingkup yang sama, bukan lintas-milestone): visualisasi
HANYA dijalankan kalau `lolos=True`.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_VERIFIKASI_KESETIAAN, get_openrouter_client
from src.layers.interpretation.narasi import _build_user_prompt as _build_user_prompt_narasi
from src.layers.interpretation.visualisasi import susun_data_visualisasi_semua
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    PROMPT_ID,
    PROMPT_VERSION,
)
from src.observability.tracing import get_tracer
from src.prompts.loader import load_prompt
from src.schemas.decomposition import AtomicIntent
from src.schemas.interpretation import DataVisualisasi, HasilVerifikasiNarasi
from src.schemas.session_memory import SessionMemoryPackage, StatusEksekusi

_TRACER_NAME = "interpretation.verifikasi_kesetiaan"
_PROMPT_ID = "interpretation.verifikasi_kesetiaan"


def _build_user_prompt(
    narasi: str, atomic_intents: list[AtomicIntent], packages: list[SessionMemoryPackage]
) -> str:
    """Konteks ground-truth (reuse narasi._build_user_prompt(), Keputusan 5)
    + narasi yang dinilai."""
    konteks_sumber = _build_user_prompt_narasi(atomic_intents, packages)
    return f"{konteks_sumber}\n\nNarasi yang dinilai:\n{narasi}"


def _call_llm(narasi: str, atomic_intents: list[AtomicIntent], packages: list[SessionMemoryPackage]):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`), mirror pola seluruh
    layer LLM lain."""
    client = get_openrouter_client()
    system_prompt = load_prompt(_PROMPT_ID).render()
    user_prompt = _build_user_prompt(narasi, atomic_intents, packages)
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_VERIFIKASI_KESETIAAN,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        extra_body={"reasoning": {"effort": "high"}},
    )


class _RawVerifikasiKesetiaanResult(BaseModel):
    lolos: bool
    alasan: str | None = None


def _parse_response(raw_content: str) -> tuple[bool | None, str | None, bool]:
    """gagal=True HANYA kalau JSON rusak/skema salah total. Mengembalikan
    (lolos, alasan, gagal) - mirror persis `_parse_response()` M3.5."""
    try:
        data = json.loads(raw_content)
        hasil = _RawVerifikasiKesetiaanResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None, None, True
    if hasil.lolos:
        return True, None, False
    alasan = hasil.alasan or "LLM menyatakan tidak lolos tanpa alasan spesifik"
    return False, alasan, False


def verifikasi_kesetiaan_narasi(
    narasi: str,
    atomic_intents: list[AtomicIntent],
    packages: list[SessionMemoryPackage],
    session_id: str,
    turn_index: int,
) -> HasilVerifikasiNarasi:
    """Orkestrator verifikasi. SATU pemanggilan LLM, TANPA retry balik ke
    `susun_narasi()` (Keputusan 2). Kegagalan API/parse -> `GAGAL_TEKNIS`
    (fallback aman, mirror M3.5 - BEDA dari `susun_narasi()` M4.4 yang
    TIDAK punya fallback aman)."""
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)

    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("session.id", session_id)
        span.set_attribute("turn.index", turn_index)
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_VERIFIKASI_KESETIAAN)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(narasi, atomic_intents, packages)
        except APIError as exc:
            span.set_attribute(
                "interpretation.verifikasi_kesetiaan.gagal_alasan", f"api_error: {exc}"
            )
            return HasilVerifikasiNarasi(
                narasi=narasi, status=StatusEksekusi.GAGAL_TEKNIS, lolos=None, alasan=None
            )

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute("interpretation.verifikasi_kesetiaan.gagal_alasan", "empty_choices")
            return HasilVerifikasiNarasi(
                narasi=narasi, status=StatusEksekusi.GAGAL_TEKNIS, lolos=None, alasan=None
            )

        raw_content = response.choices[0].message.content or ""
        lolos, alasan, gagal = _parse_response(raw_content)

        if gagal:
            span.set_attribute("interpretation.verifikasi_kesetiaan.gagal_alasan", "parse_error")
            return HasilVerifikasiNarasi(
                narasi=narasi, status=StatusEksekusi.GAGAL_TEKNIS, lolos=None, alasan=None
            )

        span.set_attribute("interpretation.verifikasi_kesetiaan.lolos", lolos)
        return HasilVerifikasiNarasi(
            narasi=narasi, status=StatusEksekusi.BERHASIL, lolos=lolos, alasan=alasan
        )


def verifikasi_dan_susun_visualisasi(
    narasi: str,
    atomic_intents: list[AtomicIntent],
    packages: list[SessionMemoryPackage],
    session_id: str,
    turn_index: int,
) -> tuple[HasilVerifikasiNarasi, list[DataVisualisasi] | None]:
    """Orkestrator gabungan (Keputusan 10): verifikasi dulu, visualisasi
    HANYA dijalankan kalau `lolos=True` - forced Lingkup M4.5 sumber
    ("Untuk narasi yang lolos, dilanjutkan dengan...")."""
    hasil_verifikasi = verifikasi_kesetiaan_narasi(
        narasi, atomic_intents, packages, session_id, turn_index
    )
    if hasil_verifikasi.lolos is not True:
        return hasil_verifikasi, None
    return hasil_verifikasi, susun_data_visualisasi_semua(packages)
