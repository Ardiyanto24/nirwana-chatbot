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

from pydantic import ValidationError

from src.config.llm import OPENROUTER_MODEL, get_openrouter_client
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
)
from src.observability.tracing import get_tracer
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload

_TRACER_NAME = "context_resolution.turn_dependency"

_SYSTEM_PROMPT = """Anda adalah komponen sistem yang mendeteksi apakah pertanyaan \
terakhir dalam sebuah sesi percakapan bergantung pada (merujuk balik ke) \
pertanyaan/jawaban di turn LAIN dalam sesi yang sama. Anda TIDAK menjawab \
pertanyaannya - tugas Anda murni mendeteksi ketergantungan linguistik.

Balas HANYA dengan JSON persis berbentuk:
{"is_dependent": true atau false, "referenced_turn_index": <nomor turn yang \
dirujuk, atau null kalau tidak bergantung>}

Aturan:
- is_dependent=true HANYA kalau pertanyaan terakhir jelas merujuk balik ke \
sesuatu yang dibahas di turn lain (mis. "bandingkan dengan itu", "seperti yang \
tadi", rujukan eksplisit ke topik/angka yang muncul di turn sebelumnya).
- Kalau pertanyaan terakhir bisa dipahami penuh berdiri sendiri tanpa histori, \
is_dependent=false dan referenced_turn_index=null.
- referenced_turn_index HARUS salah satu nomor turn yang benar-benar ada di \
histori yang diberikan - JANGAN mengarang nomor turn yang tidak ada di histori.
- Rujukan bisa ke turn manapun dalam histori, tidak harus turn tepat sebelumnya."""


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


def detect_turn_dependency(payload: TurnPayload) -> TurnDependencyResult:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL)

        client = get_openrouter_client()
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        raw_content = response.choices[0].message.content or ""
        valid_turn_indices = {h.turn_index for h in payload.history}

        try:
            data = json.loads(raw_content)
            result = TurnDependencyResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            span.set_attribute("dependency.forced_independent_reason", f"parse_error: {exc}")
            return TurnDependencyResult(is_dependent=False)

        if result.is_dependent and result.referenced_turn_index not in valid_turn_indices:
            span.set_attribute(
                "dependency.forced_independent_reason",
                f"referenced_turn_index {result.referenced_turn_index} di luar "
                f"histori valid {sorted(valid_turn_indices)}",
            )
            return TurnDependencyResult(is_dependent=False)

        if result.is_dependent:
            span.set_attribute("dependency.referenced_turn_index", result.referenced_turn_index)

        return result
