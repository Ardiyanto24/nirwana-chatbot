"""Penulisan Ulang Pertanyaan Jadi Mandiri (Milestone 1.4, Langkah 3a Context
Resolution).

Menulis ulang teks turn terakhir menjadi kalimat yang bisa dipahami sepenuhnya
berdiri sendiri - elipsis/koreferensi ("dibanding itu", "yang tadi") diubah
jadi penyebutan eksplisit berdasar payload.history. Murni tugas linguistik,
TIDAK peduli apakah nilai yang disebutkan sudah tersedia di memory atau belum
(itu tanggung jawab Milestone 1.5/1.7) - dan TIDAK mengonsumsi output
TurnDependencyResult (M1.3), berjalan independen (lihat decisions.md
Keputusan 4).

Satu pemanggilan LLM tunggal (bukan generate+verify berpasangan) - forced by
Output Milestone 1.4 sendiri. Verifikasi yang dilakukan murni deterministik
(scan frasa penanda rujukan sisa), closed error space, tidak butuh LLM kedua -
lihat decisions.md Keputusan 2.
"""

from openai import APIError

from src.config.llm import OPENROUTER_MODEL_REWRITE, get_openrouter_client
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
from src.schemas.rewrite import RewriteResult
from src.schemas.turn_payload import TurnPayload

_TRACER_NAME = "context_resolution.rewrite"
_PROMPT_ID = "context_resolution.rewrite"

_RESIDUAL_REFERENCE_PHRASES = [
    "dibanding itu",
    "dibandingkan itu",
    "dibanding tadi",
    "dibandingkan dengan itu",
    "dibandingkan dengan tadi",
    "seperti tadi",
    "seperti itu tadi",
    "sama seperti sebelumnya",
    "sama seperti tadi",
    "hal itu",
    "hal tersebut",
    "yang disebutkan sebelumnya",
    "yang disebutkan tadi",
    "seperti yang disebutkan",
]


def _build_user_prompt(payload: TurnPayload) -> str:
    lines: list[str] = []
    if payload.history:
        lines.append("Histori percakapan dalam sesi ini:")
        for h in sorted(payload.history, key=lambda x: x.turn_index):
            lines.append(f"- Turn {h.turn_index}: Q: {h.question} | A: {h.answer}")
    else:
        lines.append("Tidak ada histori - ini turn pertama dalam sesi.")
    lines.append(
        f"\nPertanyaan turn terakhir (turn {payload.turn_index}): {payload.question}"
    )
    return "\n".join(lines)


def _call_llm(payload: TurnPayload):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah dari
    `rewrite_to_standalone()` supaya bisa dipakai ulang oleh skrip eval
    (`evals/`) untuk inspeksi payload lengkap tanpa memanggil API dua kali
    atau menduplikasi logic pembentukan request."""
    client = get_openrouter_client()
    system_prompt = load_prompt(_PROMPT_ID).render()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_REWRITE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": _build_user_prompt(payload)},
        ],
        temperature=0,
    )


def _detect_residual_reference(text: str) -> list[str]:
    """Scan ruang-tertutup: daftar frasa tetap penanda rujukan sisa (bukan
    kata tunggal ambigu seperti "itu"/"nya" saja - suffix "-nya" dan kata
    ganti tunggal terlalu umum dipakai legit dalam Bahasa Indonesia, mis.
    "harganya"). Murni flag observability, tidak memaksa fallback - lihat
    decisions.md Keputusan 2."""
    lowered = text.lower()
    return [phrase for phrase in _RESIDUAL_REFERENCE_PHRASES if phrase in lowered]


def rewrite_to_standalone(payload: TurnPayload) -> RewriteResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_REWRITE)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(payload)
        except APIError as exc:
            span.set_attribute("rewrite.forced_fallback_reason", f"api_error: {exc}")
            return RewriteResult(rewritten_question=payload.question)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        if not response.choices:
            span.set_attribute(
                "rewrite.forced_fallback_reason", "no_choices_in_response"
            )
            return RewriteResult(rewritten_question=payload.question)

        raw_content = (response.choices[0].message.content or "").strip()
        if not raw_content:
            span.set_attribute("rewrite.forced_fallback_reason", "empty_response")
            return RewriteResult(rewritten_question=payload.question)

        if payload.history:
            residual_phrases = _detect_residual_reference(raw_content)
            if residual_phrases:
                span.set_attribute("rewrite.residual_reference_detected", True)
                span.set_attribute(
                    "rewrite.residual_reference_phrases", residual_phrases
                )

        return RewriteResult(rewritten_question=raw_content)
