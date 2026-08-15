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
)
from src.observability.tracing import get_tracer
from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain, VerifikasiTitikButaResult

_TRACER_NAME = "domain_gate.verifikasi_titik_buta"

_DAFTAR_DOMAIN_TEXT = "\n".join(
    f"- {domain.value}: {deskripsi}" for domain, deskripsi in DESKRIPSI_DOMAIN.items()
)

_SYSTEM_PROMPT = f"""Anda adalah komponen sistem yang mencari TITIK BUTA - domain data \
yang MUNGKIN TERLEWAT oleh proses identifikasi sebelumnya untuk sebuah kebutuhan \
(atomic intent). Anda BUKAN menilai ulang apakah domain yang sudah ditemukan itu \
benar atau salah - tugas Anda murni mencari domain TAMBAHAN yang genuinely relevan \
tapi belum ada di daftar yang sudah ditemukan. Bertindaklah sebagai pemeriksa \
independen dengan sudut pandang baru, bukan melanjutkan penalaran proses \
sebelumnya.

Daftar 10 domain yang valid (HANYA boleh memilih dari daftar ini):
{_DAFTAR_DOMAIN_TEXT}

{CATATAN_POLA_JEBAKAN}

Balas HANYA dengan JSON persis berbentuk:
{{"domain_tambahan": ["<nama domain>", ...]}}

Aturan:
- HANYA sebutkan domain yang BELUM ada di "Domain yang sudah ditemukan" (lihat \
pesan pengguna) tapi genuinely relevan - JANGAN mengulang domain yang sudah ada.
- Setiap nilai HARUS persis salah satu dari 10 nama domain di atas (huruf kecil \
semua, sesuai persis) - JANGAN mengarang nama domain lain.
- Kalau setelah pemeriksaan cermat memang TIDAK ADA domain yang terlewat, balas \
{{"domain_tambahan": []}} - JANGAN memaksakan tambahan yang sebenarnya tidak \
relevan hanya supaya terlihat menemukan sesuatu."""


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
            {"role": "system", "content": _SYSTEM_PROMPT},
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
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA)

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
