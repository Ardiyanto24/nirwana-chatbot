"""Identifikasi Domain Awal (Milestone 2.1, Langkah 1 Domain Gate).

Komentar sengaja - percobaan Checkpoint 10 Milestone 8.2, membuktikan
path-filter test-python-llm memicu grup domain_gate. Dihapus setelah
bukti didapat, TIDAK PERNAH masuk main.

Langkah pertama dari dua mekanisme berurutan Domain Gate - membaca teks
kebutuhan atomik dan mengenali domain data yang tersentuh, termasuk lewat
kolom turunan lintas-domain dan pemisahan guests_pii/guests_profile.
Diikuti verifikasi_titik_buta.py (langkah 2, independen, BUKAN retry -
lihat decisions.md Keputusan 2).

Panggilan LLM mentah dipisah dari parsing/bounds-check (pola
_call_llm/_parse_and_decide matching.py M1.7) supaya reusable oleh skrip
eval dan testable tanpa panggilan API nyata.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI, get_openrouter_client
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
from src.schemas.domain_gate import Domain, IdentifikasiDomainResult

_TRACER_NAME = "domain_gate.identifikasi"
_PROMPT_ID = "domain_gate.identifikasi"

_DAFTAR_DOMAIN = [
    (domain.value, deskripsi) for domain, deskripsi in DESKRIPSI_DOMAIN.items()
]


def _render_context() -> dict:
    """Variabel render prompt ini - dipakai kode produksi (`_render_system_
    prompt()`) DAN provider Promptfoo (`prompt_reliability/provider.py`,
    config `render_context`) supaya reliability testing selalu memakai
    context identik dengan yang benar-benar dikirim saat runtime."""
    return {
        "daftar_domain": _DAFTAR_DOMAIN,
        "catatan_pola_jebakan": CATATAN_POLA_JEBAKAN,
    }


def _render_system_prompt() -> str:
    return load_prompt(_PROMPT_ID).render(**_render_context())


class _RawIdentifikasiResult(BaseModel):
    domains: list[str]


def _call_llm(atomic_intent: AtomicIntent):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI,
        messages=[
            {"role": "system", "content": _render_system_prompt()},
            {"role": "user", "content": atomic_intent.teks_kebutuhan},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def bounds_check_domains(raw_domains: list[str]) -> tuple[list[Domain], list[str]]:
    """Pisahkan domain string valid (ada di closed-set 10 nilai Domain Enum)
    dari yang invalid (hallucinated LLM). Murni deterministik, TANPA LLM -
    lihat decisions.md Keputusan 5."""
    valid_values = {d.value for d in Domain}
    valid: list[Domain] = []
    invalid: list[str] = []
    for raw in raw_domains:
        if raw in valid_values:
            valid.append(Domain(raw))
        else:
            invalid.append(raw)
    return valid, invalid


def _parse_and_decide(raw_content: str) -> tuple[IdentifikasiDomainResult, str | None]:
    """Parse hasil LLM + bounds-check. Mengembalikan (result, alasan_anomali) -
    alasan diisi kalau ada domain hallucinated yang di-drop ATAU hasil akhir
    kosong (dipaksa gagal=True), None kalau bersih tanpa anomali."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawIdentifikasiResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return IdentifikasiDomainResult(domains=[], gagal=True), f"parse_error: {exc}"

    valid_domains, invalid_domains = bounds_check_domains(raw_result.domains)

    if not valid_domains:
        reason = f"tidak_ada_domain_valid: raw={raw_result.domains}"
        return IdentifikasiDomainResult(domains=[], gagal=True), reason

    reason = f"dropped_invalid_domains: {invalid_domains}" if invalid_domains else None
    return IdentifikasiDomainResult(domains=valid_domains), reason


def identifikasi_domain(atomic_intent: AtomicIntent) -> IdentifikasiDomainResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(atomic_intent)
        except APIError as exc:
            span.set_attribute(
                "domain_gate.identifikasi.forced_fallback_reason", f"api_error: {exc}"
            )
            return IdentifikasiDomainResult(domains=[], gagal=True)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        if not response.choices:
            span.set_attribute(
                "domain_gate.identifikasi.forced_fallback_reason", "empty_choices"
            )
            return IdentifikasiDomainResult(domains=[], gagal=True)

        raw_content = response.choices[0].message.content or ""
        result, anomaly_reason = _parse_and_decide(raw_content)

        if anomaly_reason:
            span.set_attribute(
                "domain_gate.identifikasi.forced_fallback_reason", anomaly_reason
            )
        span.set_attribute(
            "domain_gate.identifikasi.domains_found",
            ",".join(d.value for d in result.domains),
        )

        return result
