"""Klasifikasi Kebutuhan (Milestone 1.6, Langkah 4 Decomposition).

Menentukan apakah kalimat mandiri hasil Milestone 1.4 berisi kebutuhan
tunggal, majemuk-independen, atau majemuk-bergantung. Input MURNI kalimat
(tidak ada histori/session memory - M1.6 tidak menyentuh itu sama sekali).

Satu pemanggilan LLM tunggal, dipanggil sekali di awal decompose_question()
(TIDAK ikut retry loop, lihat decisions.md Keputusan 9).
"""

from openai import APIError

from src.config.llm import OPENROUTER_MODEL_DECOMPOSITION, get_openrouter_client
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
)
from src.observability.tracing import get_tracer
from src.schemas.decomposition import KlasifikasiKebutuhan

_TRACER_NAME = "decomposition.klasifikasi"

_SYSTEM_PROMPT = """Anda adalah komponen sistem yang mengklasifikasikan sebuah \
pertanyaan menjadi salah satu dari tiga kategori kebutuhan:

- tunggal: pertanyaan berisi satu kebutuhan informasi saja.
- majemuk_independen: pertanyaan berisi lebih dari satu kebutuhan informasi, \
tapi masing-masing bisa dijawab sendiri-sendiri TANPA bergantung pada \
jawaban kebutuhan lain.
- majemuk_bergantung: pertanyaan berisi lebih dari satu kebutuhan informasi, \
di mana salah satu kebutuhan butuh jawaban dari kebutuhan lain lebih dulu \
sebelum bisa diselesaikan (mis. perbandingan - kedua nilai yang \
dibandingkan perlu diketahui dulu).

Balas HANYA dengan salah satu dari tiga kata ini, tanpa penjelasan \
tambahan, tanpa tanda kutip: tunggal / majemuk_independen / \
majemuk_bergantung"""

_FALLBACK = KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG


def _call_llm(question: str):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DECOMPOSITION,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )


def klasifikasi_kebutuhan(question: str) -> KlasifikasiKebutuhan:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DECOMPOSITION)

        try:
            response = _call_llm(question)
        except APIError as exc:
            span.set_attribute("decomposition.forced_fallback_reason", f"api_error: {exc}")
            span.set_attribute("decomposition.classification", _FALLBACK.value)
            return _FALLBACK

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        raw = (response.choices[0].message.content or "").strip().lower()
        try:
            result = KlasifikasiKebutuhan(raw)
        except ValueError:
            span.set_attribute(
                "decomposition.forced_fallback_reason", f"unparseable_response: {raw!r}"
            )
            result = _FALLBACK

        span.set_attribute("decomposition.classification", result.value)
        return result
