"""Verifikasi Bentuk Request (Milestone 3.5, Langkah 2 Query Engine).
Menilai ulang SECARA INDEPENDEN `QueryEngineRequest` hasil Milestone 3.4
(tanpa melihat proses generate-nya) terhadap dua kriteria: (1) kepatuhan
sumber - `view_name` sama dengan yang divalidasi Retriever; (2) kecukupan
semantik - `params` benar-benar menghasilkan bentuk jawaban sesuai
`label_bentuk_jawaban`.

Mekanisme HYBRID (decisions.md Keputusan 1): Kriteria 1 adalah pre-check
DETERMINISTIK (ruang kesalahan tertutup, satu perbandingan string) yang
dijalankan LEBIH DULU - kalau gagal, short-circuit TANPA membuka span
`chat` dan TANPA memanggil LLM sama sekali (Keputusan 3). Kriteria 2
BUTUH LLM (ruang kesalahan terbuka) - SATU pemanggilan, tanpa retry,
tanpa verifier independen kedua di dalam milestone ini (Keputusan 4).

`request` pada output SELALU utuh, tidak pernah di-null-kan/dimodifikasi
(Keputusan 7) - beda `verifikasi_gate()` (M2.4) yang menolak dengan
me-null-kan. M3.5 mendiagnosis, bukan merevisi/menolak.

Lihat milestones/3.5-verifikasi-bentuk-request/decisions.md.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import (
    OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST,
    get_openrouter_client,
)
from src.layers.retriever.definisi_view import DEFINISI_LENGKAP_VIEW
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    PROMPT_ID,
    PROMPT_VERSION,
    REQUEST_DOMAIN,
    REQUEST_VIEW_NAME,
)
from src.observability.tracing import get_tracer
from src.prompts.loader import load_prompt
from src.schemas.decomposition import AtomicIntent
from src.schemas.query_engine import HasilVerifikasiBentukRequest
from src.schemas.session_memory import StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest

_TRACER_NAME = "query_engine.verifikasi_bentuk_request"
_PROMPT_ID = "query_engine.verifikasi_bentuk_request"


def _view_name_sesuai_retriever(
    request: QueryEngineRequest, view_name_tervalidasi_retriever: str
) -> bool:
    """Kriteria 1 - pre-check deterministik, ruang kesalahan tertutup
    (decisions.md Keputusan 2). SENGAJA redundan dengan
    verifikasi_kepatuhan_sumber() (M2.4, verifikasi_gate.py) - keduanya
    perbandingan string sederhana atas dua nilai yang sama, tapi berperan
    di lapisan berbeda (lihat decisions.md Keputusan 2, Catatan
    Ketergantungan)."""
    return request.view_name == view_name_tervalidasi_retriever


def _render_system_prompt() -> str:
    return load_prompt(_PROMPT_ID).render()


def _build_user_prompt(atomic_intent: AtomicIntent, request: QueryEngineRequest) -> str:
    definisi = DEFINISI_LENGKAP_VIEW.get(
        request.view_name, "(definisi tidak ditemukan)"
    )
    return (
        f"Kebutuhan: {atomic_intent.teks_kebutuhan} "
        f"(bentuk jawaban: {atomic_intent.label_bentuk_jawaban.value})\n"
        f"\nView data yang dipakai: {request.view_name}\n"
        f"\nDefinisi lengkap view (grain, kolom, sumber):\n{definisi}\n"
        f"\nParams yang tersusun:\n{json.dumps(request.params, ensure_ascii=False)}"
    )


def _call_llm(atomic_intent: AtomicIntent, request: QueryEngineRequest):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`), mirror pola
    penyusunan_request.py/kecocokan_makna.py."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST,
        messages=[
            {"role": "system", "content": _render_system_prompt()},
            {"role": "user", "content": _build_user_prompt(atomic_intent, request)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        extra_body={"reasoning": {"effort": "high"}},
    )


class _RawVerifikasiBentukRequestResult(BaseModel):
    lolos: bool
    alasan: str | None = None


def _parse_response(raw_content: str) -> tuple[bool | None, str | None, bool]:
    """gagal=True HANYA kalau JSON rusak/skema salah total. Mengembalikan
    (lolos, alasan, gagal). Kalau lolos=False tapi LLM lupa mengisi
    alasan (melanggar instruksi prompt), isi fallback generik daripada
    membiarkan alasan=None (yang akan gagal validator skema)."""
    try:
        data = json.loads(raw_content)
        hasil = _RawVerifikasiBentukRequestResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None, None, True
    if hasil.lolos:
        return True, None, False
    alasan = hasil.alasan or "LLM menyatakan tidak lolos tanpa alasan spesifik"
    return False, alasan, False


def verifikasi_bentuk_request_atomic_intent(
    atomic_intent: AtomicIntent,
    view_name_tervalidasi_retriever: str,
    request: QueryEngineRequest,
) -> HasilVerifikasiBentukRequest:
    """Pre-check Kriteria 1 dulu (Keputusan 1 dan 3) - kalau gagal,
    langsung `lolos=False` tanpa span `chat`/panggilan LLM. Kalau lolos,
    SATU pemanggilan LLM untuk Kriteria 2, tanpa retry (Keputusan 4)."""
    if not _view_name_sesuai_retriever(request, view_name_tervalidasi_retriever):
        return HasilVerifikasiBentukRequest(
            atomic_intent=atomic_intent,
            request=request,
            status=StatusEksekusi.BERHASIL,
            lolos=False,
            alasan=(
                f"view_name request ('{request.view_name}') tidak sesuai dengan "
                f"view_name yang divalidasi Retriever ('{view_name_tervalidasi_retriever}')"
            ),
        )

    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)

    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(
            GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST
        )
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)
        span.set_attribute(REQUEST_DOMAIN, request.domain.value)
        span.set_attribute(REQUEST_VIEW_NAME, request.view_name)

        try:
            response = _call_llm(atomic_intent, request)
        except APIError as exc:
            span.set_attribute(
                "query_engine.verifikasi_bentuk_request.gagal_alasan",
                f"api_error: {exc}",
            )
            return HasilVerifikasiBentukRequest(
                atomic_intent=atomic_intent,
                request=request,
                status=StatusEksekusi.GAGAL_TEKNIS,
                lolos=None,
                alasan=None,
            )

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        if not response.choices:
            span.set_attribute(
                "query_engine.verifikasi_bentuk_request.gagal_alasan", "empty_choices"
            )
            return HasilVerifikasiBentukRequest(
                atomic_intent=atomic_intent,
                request=request,
                status=StatusEksekusi.GAGAL_TEKNIS,
                lolos=None,
                alasan=None,
            )

        raw_content = response.choices[0].message.content or ""
        lolos, alasan, gagal = _parse_response(raw_content)

        if gagal:
            span.set_attribute(
                "query_engine.verifikasi_bentuk_request.gagal_alasan", "parse_error"
            )
            return HasilVerifikasiBentukRequest(
                atomic_intent=atomic_intent,
                request=request,
                status=StatusEksekusi.GAGAL_TEKNIS,
                lolos=None,
                alasan=None,
            )

        span.set_attribute("query_engine.verifikasi_bentuk_request.lolos", lolos)
        return HasilVerifikasiBentukRequest(
            atomic_intent=atomic_intent,
            request=request,
            status=StatusEksekusi.BERHASIL,
            lolos=lolos,
            alasan=alasan,
        )


def verifikasi_bentuk_request_semua(
    daftar: list[tuple[AtomicIntent, str, QueryEngineRequest]],
) -> list[HasilVerifikasiBentukRequest]:
    """Orkestrator batch - satu per kebutuhan atomik dalam satu turn,
    dipanggil dengan `(atomic_intent, view_name_tervalidasi_retriever,
    request)` per item (pemanggil yang menyaring hanya item M3.4
    `status=BERHASIL` - Keputusan 8). Span pembungkus non-LLM dengan
    statistik agregat, mirror nilai_kecocokan_makna_semua()/
    identifikasi_domain_semua() (Keputusan 13)."""
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(
        "query_engine.verifikasi_bentuk_request_semua"
    ) as span:
        span.set_attribute("verifikasi_bentuk_request.intent_count", len(daftar))

        hasil = [
            verifikasi_bentuk_request_atomic_intent(ai, view_name, request)
            for ai, view_name, request in daftar
        ]

        lolos_count = sum(1 for h in hasil if h.lolos is True)
        perlu_revisi_count = sum(1 for h in hasil if h.lolos is False)
        gagal_teknis_count = sum(
            1 for h in hasil if h.status == StatusEksekusi.GAGAL_TEKNIS
        )
        span.set_attribute("verifikasi_bentuk_request.lolos_count", lolos_count)
        span.set_attribute(
            "verifikasi_bentuk_request.perlu_revisi_count", perlu_revisi_count
        )
        span.set_attribute(
            "verifikasi_bentuk_request.gagal_teknis_count", gagal_teknis_count
        )

        return hasil
