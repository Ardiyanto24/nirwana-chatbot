"""Deteksi Awal Constraint Cakupan-Individu (Milestone 2.3, Langkah 1
Domain Gate).

Langkah pertama dari dua mekanisme berurutan (generate-verify union
aditif, lihat decisions.md Keputusan 2) - menilai apakah teks_kebutuhan
menyentuh kategori data performa individu staf (9 view, domain
facility/hr). Diikuti verifikasi_cakupan_individu.py (langkah 2,
independen, BUKAN retry).

Struktur mirror PERSIS identifikasi.py (M2.1): _call_llm/_parse_and_decide
dipisah dari span/orkestrasi supaya reusable oleh skrip eval dan testable
tanpa panggilan API nyata.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import (
    OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI,
    get_openrouter_client,
)
from src.layers.domain_gate.konteks_cakupan_individu import (
    CATATAN_INDIVIDU_VS_AGREGAT,
    DAFTAR_VIEW_CAKUPAN_INDIVIDU,
)
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
from src.schemas.cakupan_individu import DeteksiCakupanIndividuResult
from src.schemas.decomposition import AtomicIntent

_TRACER_NAME = "domain_gate.deteksi_cakupan_individu"
_PROMPT_ID = "domain_gate.deteksi_cakupan_individu"

_DAFTAR_VIEW_RENDER = [
    {
        "nama": v.nama,
        "domain": v.domain.value,
        "kolom_identitas": v.kolom_identitas,
        "deskripsi": v.deskripsi,
    }
    for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU
]


def _render_context() -> dict:
    """Variabel render prompt ini - dipakai kode produksi DAN provider
    Promptfoo supaya reliability testing selalu memakai context identik
    dengan yang benar-benar dikirim saat runtime."""
    return {
        "daftar_view": _DAFTAR_VIEW_RENDER,
        "catatan_individu_vs_agregat": CATATAN_INDIVIDU_VS_AGREGAT,
    }


def _render_system_prompt() -> str:
    return load_prompt(_PROMPT_ID).render(**_render_context())


class _RawDeteksiResult(BaseModel):
    terdeteksi: bool


def _call_llm(atomic_intent: AtomicIntent):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI,
        messages=[
            {"role": "system", "content": _render_system_prompt()},
            {"role": "user", "content": atomic_intent.teks_kebutuhan},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _parse_and_decide(
    raw_content: str,
) -> tuple[DeteksiCakupanIndividuResult, str | None]:
    """Parse hasil LLM. Mengembalikan (result, alasan_anomali) - alasan
    diisi kalau parse gagal, None kalau bersih."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawDeteksiResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return DeteksiCakupanIndividuResult(
            terdeteksi=False, gagal=True
        ), f"parse_error: {exc}"

    return DeteksiCakupanIndividuResult(terdeteksi=raw_result.terdeteksi), None


def deteksi_cakupan_individu(
    atomic_intent: AtomicIntent,
) -> DeteksiCakupanIndividuResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(
            GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI
        )
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(atomic_intent)
        except APIError as exc:
            span.set_attribute(
                "domain_gate.deteksi_cakupan_individu.forced_fallback_reason",
                f"api_error: {exc}",
            )
            return DeteksiCakupanIndividuResult(terdeteksi=False, gagal=True)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        if not response.choices:
            span.set_attribute(
                "domain_gate.deteksi_cakupan_individu.forced_fallback_reason",
                "empty_choices",
            )
            return DeteksiCakupanIndividuResult(terdeteksi=False, gagal=True)

        raw_content = response.choices[0].message.content or ""
        result, anomaly_reason = _parse_and_decide(raw_content)

        if anomaly_reason:
            span.set_attribute(
                "domain_gate.deteksi_cakupan_individu.forced_fallback_reason",
                anomaly_reason,
            )
        span.set_attribute(
            "domain_gate.deteksi_cakupan_individu.terdeteksi", result.terdeteksi
        )

        return result
