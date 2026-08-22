"""Pemetaan Ketergantungan Turn (Milestone 1.3, Langkah 2 Context Resolution).

Mendeteksi apakah turn terakhir bergantung ke turn LAIN dalam sesi yang sama
(tidak harus turn tepat sebelumnya). Output HANYA {session_id, turn_index}
referensi - TIDAK PERNAH atomic_intent_id (sistem di titik ini belum pernah
membaca session memory, memaksa ID spesifik membuka risiko halusinasi).

Satu pemanggilan LLM tunggal (bukan generate+verify berpasangan) - forced by
Output Milestone 1.3 sendiri. Verifikasi yang dilakukan murni struktural
(bounds-check referenced_turn_index terhadap histori yang tersedia), closed
error space, tidak butuh LLM kedua.
"""

import json

from openai import APIError
from pydantic import ValidationError

from src.config.llm import OPENROUTER_MODEL, get_openrouter_client
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
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload

_TRACER_NAME = "context_resolution.turn_dependency"
_PROMPT_ID = "context_resolution.turn_dependency"


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
    `detect_turn_dependency()` supaya bisa dipakai ulang oleh skrip eval
    (`evals/`) untuk inspeksi payload lengkap tanpa memanggil API dua kali
    atau menduplikasi logic pembentukan request."""
    client = get_openrouter_client()
    system_prompt = load_prompt(_PROMPT_ID).render()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": _build_user_prompt(payload)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _parse_and_validate(
    raw_content: str, valid_turn_indices: set[int]
) -> tuple[TurnDependencyResult, str | None]:
    """Parse + bounds-check hasil LLM. Mengembalikan (result, alasan) - alasan
    diisi kalau hasil dipaksa jadi independent (parse gagal atau referenced_
    turn_index di luar histori valid), None kalau tidak."""
    try:
        data = json.loads(raw_content)
        result = TurnDependencyResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return TurnDependencyResult(is_dependent=False), f"parse_error: {exc}"

    if result.is_dependent and result.referenced_turn_index not in valid_turn_indices:
        reason = (
            f"referenced_turn_index {result.referenced_turn_index} di luar "
            f"histori valid {sorted(valid_turn_indices)}"
        )
        return TurnDependencyResult(is_dependent=False), reason

    return result, None


def detect_turn_dependency(payload: TurnPayload) -> TurnDependencyResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(payload)
        except APIError as exc:
            span.set_attribute(
                "dependency.forced_independent_reason", f"api_error: {exc}"
            )
            return TurnDependencyResult(is_dependent=False)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        raw_content = response.choices[0].message.content or ""
        valid_turn_indices = {h.turn_index for h in payload.history}
        result, forced_reason = _parse_and_validate(raw_content, valid_turn_indices)

        if forced_reason:
            span.set_attribute("dependency.forced_independent_reason", forced_reason)
        if result.is_dependent:
            span.set_attribute(
                "dependency.referenced_turn_index", result.referenced_turn_index
            )

        return result
