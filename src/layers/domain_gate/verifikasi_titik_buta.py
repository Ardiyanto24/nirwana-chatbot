"""Verifikasi Titik Buta (Milestone 2.1, Langkah 2 Domain Gate).

Langkah kedua, INDEPENDEN dari Langkah 1 (identifikasi.py) - mencari
domain yang mungkin TERLEWAT dari hasil Langkah 1, BUKAN menilai ulang
kebenaran hasil Langkah 1 (bukan retry/re-scoring). Lihat decisions.md
Keputusan 2. Hasil akhir (union domain_awal + domain_tambahan) dihitung
orkestrator (domain_gate.py, Checkpoint 7), BUKAN di sini.

Model DeepSeek V4 Pro, reasoning="high" dikonfigurasi eksplisit - beda
dari Langkah 1 (Qwen3-32B) untuk keragaman peran verifier independen,
lihat decisions.md Keputusan 9.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import (
    OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA,
    get_openrouter_client,
)
from src.layers.domain_gate.identifikasi import bounds_check_domains
from src.layers.domain_gate.konteks_domain import CATATAN_POLA_JEBAKAN, DESKRIPSI_DOMAIN
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
from src.schemas.domain_gate import Domain, VerifikasiTitikButaResult

_TRACER_NAME = "domain_gate.verifikasi_titik_buta"
_PROMPT_ID = "domain_gate.verifikasi_titik_buta"

_DAFTAR_DOMAIN = [(domain.value, deskripsi) for domain, deskripsi in DESKRIPSI_DOMAIN.items()]


def _render_context() -> dict:
    """Variabel render prompt ini - dipakai kode produksi DAN provider
    Promptfoo (`prompt_reliability/provider.py`, config `render_context`)
    supaya reliability testing selalu memakai context identik dengan yang
    benar-benar dikirim saat runtime."""
    return {"daftar_domain": _DAFTAR_DOMAIN, "catatan_pola_jebakan": CATATAN_POLA_JEBAKAN}


def _render_system_prompt() -> str:
    return load_prompt(_PROMPT_ID).render(**_render_context())


class _RawVerifikasiTitikButaResult(BaseModel):
    domain_tambahan: list[str]


def _build_user_prompt(atomic_intent: AtomicIntent, domain_awal: list[Domain]) -> str:
    domain_awal_text = ", ".join(d.value for d in domain_awal)
    return (
        f"Kebutuhan: {atomic_intent.teks_kebutuhan}\n"
        f"Domain yang sudah ditemukan: {domain_awal_text}"
    )


def _call_llm(atomic_intent: AtomicIntent, domain_awal: list[Domain]):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA,
        messages=[
            {"role": "system", "content": _render_system_prompt()},
            {"role": "user", "content": _build_user_prompt(atomic_intent, domain_awal)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        extra_body={"reasoning": {"effort": "high"}},
    )


def _parse_and_decide(raw_content: str) -> tuple[VerifikasiTitikButaResult, str | None]:
    """Parse hasil LLM + bounds-check. Mengembalikan (result, alasan_anomali) -
    alasan diisi kalau ada domain hallucinated yang di-drop, None kalau bersih
    (termasuk jalur normal domain_tambahan=[] genuinely tidak menemukan apa
    pun - BUKAN dianggap anomali)."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawVerifikasiTitikButaResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return VerifikasiTitikButaResult(domain_tambahan=[], gagal=True), f"parse_error: {exc}"

    valid_domains, invalid_domains = bounds_check_domains(raw_result.domain_tambahan)
    reason = f"dropped_invalid_domains: {invalid_domains}" if invalid_domains else None
    return VerifikasiTitikButaResult(domain_tambahan=valid_domains), reason


def verifikasi_titik_buta(
    atomic_intent: AtomicIntent, domain_awal: list[Domain]
) -> VerifikasiTitikButaResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(atomic_intent, domain_awal)
        except APIError as exc:
            span.set_attribute(
                "domain_gate.verifikasi_titik_buta.forced_fallback_reason", f"api_error: {exc}"
            )
            return VerifikasiTitikButaResult(domain_tambahan=[], gagal=True)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "domain_gate.verifikasi_titik_buta.forced_fallback_reason", "empty_choices"
            )
            return VerifikasiTitikButaResult(domain_tambahan=[], gagal=True)

        raw_content = response.choices[0].message.content or ""
        result, anomaly_reason = _parse_and_decide(raw_content)

        if anomaly_reason:
            span.set_attribute(
                "domain_gate.verifikasi_titik_buta.forced_fallback_reason", anomaly_reason
            )
        span.set_attribute(
            "domain_gate.verifikasi_titik_buta.domain_tambahan_count",
            len(result.domain_tambahan),
        )

        return result
