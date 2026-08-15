"""Identifikasi Domain Awal (Milestone 2.1, Langkah 1 Domain Gate).

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
)
from src.observability.tracing import get_tracer
from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain, IdentifikasiDomainResult

_TRACER_NAME = "domain_gate.identifikasi"

_DAFTAR_DOMAIN_TEXT = "\n".join(
    f"- {domain.value}: {deskripsi}" for domain, deskripsi in DESKRIPSI_DOMAIN.items()
)

_SYSTEM_PROMPT = f"""Anda adalah komponen sistem yang mengidentifikasi domain data \
apa saja yang tersentuh oleh sebuah kebutuhan (atomic intent) dari pertanyaan \
pengguna. Anda TIDAK menjawab kebutuhannya - tugas Anda murni menentukan domain \
data yang relevan.

Daftar 10 domain yang valid (HANYA boleh memilih dari daftar ini):
{_DAFTAR_DOMAIN_TEXT}

{CATATAN_POLA_JEBAKAN}

Balas HANYA dengan JSON persis berbentuk:
{{"domains": ["<nama domain 1>", "<nama domain 2>", ...]}}

Aturan:
- Setiap nilai di "domains" HARUS persis salah satu dari 10 nama domain di atas \
(huruf kecil semua, sesuai persis) - JANGAN mengarang nama domain lain.
- Sebutkan SEMUA domain yang genuinely tersentuh, termasuk lewat kolom turunan \
lintas-domain (pola 1) dan pemisahan guests_pii/guests_profile (pola 3) - jangan \
hanya domain yang disebut eksplisit di kata-kata pertanyaan.
- Minimal satu domain wajib teridentifikasi - setiap kebutuhan data pasti \
menyentuh domain data tertentu."""


class _RawIdentifikasiResult(BaseModel):
    domains: list[str]


def _call_llm(atomic_intent: AtomicIntent):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
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
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI)

        try:
            response = _call_llm(atomic_intent)
        except APIError as exc:
            span.set_attribute("domain_gate.identifikasi.forced_fallback_reason", f"api_error: {exc}")
            return IdentifikasiDomainResult(domains=[], gagal=True)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "domain_gate.identifikasi.forced_fallback_reason", "empty_choices"
            )
            return IdentifikasiDomainResult(domains=[], gagal=True)

        raw_content = response.choices[0].message.content or ""
        result, anomaly_reason = _parse_and_decide(raw_content)

        if anomaly_reason:
            span.set_attribute("domain_gate.identifikasi.forced_fallback_reason", anomaly_reason)
        span.set_attribute(
            "domain_gate.identifikasi.domains_found",
            ",".join(d.value for d in result.domains),
        )

        return result
