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
    PROMPT_ID,
    PROMPT_VERSION,
)
from src.observability.tracing import get_tracer
from src.prompts.loader import load_prompt
from src.schemas.decomposition import KlasifikasiKebutuhan

_TRACER_NAME = "decomposition.klasifikasi"
_PROMPT_ID = "decomposition.klasifikasi"

_FALLBACK = KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG


def _call_llm(question: str):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    system_prompt = load_prompt(_PROMPT_ID).render()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DECOMPOSITION,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0,
    )


def klasifikasi_kebutuhan(question: str) -> KlasifikasiKebutuhan:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DECOMPOSITION)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

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
