"""Verifikasi Titik Buta Constraint Cakupan-Individu (Milestone 2.3,
Langkah 2 Domain Gate).

Langkah kedua, INDEPENDEN dari Langkah 1 (deteksi_cakupan_individu.py) -
menilai ulang secara independen apakah teks_kebutuhan genuinely menyentuh
kategori performa individu, BUKAN menilai ulang alasan Langkah 1 (bukan
retry/re-scoring). Lihat decisions.md Keputusan 2. Hasil akhir (union
terdeteksi_awal OR terdeteksi_tambahan) dihitung orkestrator
(cakupan_individu.py, Checkpoint 6), BUKAN di sini.

Model DeepSeek V4 Pro, reasoning="high" dikonfigurasi eksplisit - beda
dari Langkah 1 (Qwen3-32B) untuk keragaman peran verifier independen,
lihat decisions.md Keputusan 8.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI, get_openrouter_client
from src.layers.domain_gate.deteksi_cakupan_individu import _DAFTAR_VIEW_RENDER
from src.layers.domain_gate.konteks_cakupan_individu import CATATAN_INDIVIDU_VS_AGREGAT
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
from src.schemas.cakupan_individu import VerifikasiCakupanIndividuResult
from src.schemas.decomposition import AtomicIntent

_TRACER_NAME = "domain_gate.verifikasi_cakupan_individu"
_PROMPT_ID = "domain_gate.verifikasi_cakupan_individu"


def _render_context() -> dict:
    """Variabel render prompt ini - dipakai kode produksi DAN provider
    Promptfoo supaya reliability testing selalu memakai context identik
    dengan yang benar-benar dikirim saat runtime. Reuse _DAFTAR_VIEW_RENDER
    dari deteksi_cakupan_individu.py supaya kedua prompt tidak drift."""
    return {
        "daftar_view": _DAFTAR_VIEW_RENDER,
        "catatan_individu_vs_agregat": CATATAN_INDIVIDU_VS_AGREGAT,
    }


def _render_system_prompt() -> str:
    return load_prompt(_PROMPT_ID).render(**_render_context())


class _RawVerifikasiResult(BaseModel):
    terdeteksi_tambahan: bool


def _build_user_prompt(atomic_intent: AtomicIntent, terdeteksi_awal: bool) -> str:
    kesimpulan = "terdeteksi" if terdeteksi_awal else "tidak terdeteksi"
    return f"Kebutuhan: {atomic_intent.teks_kebutuhan}\nKesimpulan Langkah 1: {kesimpulan}"


def _call_llm(atomic_intent: AtomicIntent, terdeteksi_awal: bool):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI,
        messages=[
            {"role": "system", "content": _render_system_prompt()},
            {"role": "user", "content": _build_user_prompt(atomic_intent, terdeteksi_awal)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        extra_body={"reasoning": {"effort": "high"}},
    )


def _parse_and_decide(raw_content: str) -> tuple[VerifikasiCakupanIndividuResult, str | None]:
    """Parse hasil LLM. Mengembalikan (result, alasan_anomali) - alasan
    diisi kalau parse gagal, None kalau bersih."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawVerifikasiResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return (
            VerifikasiCakupanIndividuResult(terdeteksi_tambahan=False, gagal=True),
            f"parse_error: {exc}",
        )

    return VerifikasiCakupanIndividuResult(terdeteksi_tambahan=raw_result.terdeteksi_tambahan), None


def verifikasi_cakupan_individu(
    atomic_intent: AtomicIntent, terdeteksi_awal: bool
) -> VerifikasiCakupanIndividuResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(atomic_intent, terdeteksi_awal)
        except APIError as exc:
            span.set_attribute(
                "domain_gate.verifikasi_cakupan_individu.forced_fallback_reason",
                f"api_error: {exc}",
            )
            return VerifikasiCakupanIndividuResult(terdeteksi_tambahan=False, gagal=True)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "domain_gate.verifikasi_cakupan_individu.forced_fallback_reason", "empty_choices"
            )
            return VerifikasiCakupanIndividuResult(terdeteksi_tambahan=False, gagal=True)

        raw_content = response.choices[0].message.content or ""
        result, anomaly_reason = _parse_and_decide(raw_content)

        if anomaly_reason:
            span.set_attribute(
                "domain_gate.verifikasi_cakupan_individu.forced_fallback_reason", anomaly_reason
            )
        span.set_attribute(
            "domain_gate.verifikasi_cakupan_individu.terdeteksi_tambahan",
            result.terdeteksi_tambahan,
        )

        return result
