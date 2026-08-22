"""Penyusunan Request (Milestone 3.4, Langkah 1 Query Engine). Dari
kebutuhan atomik + `view_name` yang sudah divalidasi Retriever (M3.1-3.3),
menyusun `QueryEngineRequest {domain, view_name, params}` lewat SATU
pemanggilan LLM (ekstraksi parameter terstruktur) - tanpa retry internal,
tanpa verifier independen (Milestone 3.5 terpisah).

`domain` diturunkan kode via `view_ke_domain()[view_name]` (M3.1),
TIDAK diminta dari LLM. `params` disaring deterministik pasca-LLM
terhadap `PARAM_WHITELIST_VIEW[view_name]` (Checkpoint 2) - exact key
match, bukan mempercayai kepatuhan prompt saja. `employee_id`/
`role_title`/`domain`/`view_name` TIDAK PERNAH masuk `params`, di-strip
paksa kapan pun muncul di respons LLM.

Lihat milestones/3.4-penyusunan-request/decisions.md.

Parameter `feedback` opsional (ditambahkan Milestone 4.2, lihat
milestones/4.2-klasifikasi-respons-dan-penanganan-kegagalan/decisions.md
Keputusan 3) dipakai saat REVISI - dipanggil ulang dari orkestrator
Execution (`src/layers/execution/klasifikasi_respons.py`) kalau
chatbot_api menolak request sebelumnya dengan status 400. Mirror pola
persis parameter `feedback` di `pecah_atomik()` (M1.6). Fungsi ini
SENDIRI tetap tanpa retry internal - loop revisi (kalau ada) sepenuhnya
tanggung jawab pemanggil (Execution), bukan modul ini.
"""

import json
from datetime import date, datetime, timedelta, timezone

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.katalog_view import view_ke_domain
from src.config.llm import OPENROUTER_MODEL_PENYUSUNAN_REQUEST, get_openrouter_client
from src.layers.query_engine.param_whitelist import (
    PARAM_TERLARANG,
    PARAM_WHITELIST_VIEW,
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
from src.schemas.query_engine import HasilPenyusunanRequest
from src.schemas.session_memory import StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest

_TRACER_NAME = "query_engine.penyusunan_request"
_PROMPT_ID = "query_engine.penyusunan_request"
_ZONA_WIB = timezone(timedelta(hours=7))


def _tanggal_referensi_default() -> date:
    return datetime.now(_ZONA_WIB).date()


def _render_system_prompt() -> str:
    return load_prompt(_PROMPT_ID).render()


def _build_user_prompt(
    atomic_intent: AtomicIntent,
    view_name: str,
    tanggal_referensi: date,
    feedback: str | None = None,
) -> str:
    whitelist = sorted(PARAM_WHITELIST_VIEW.get(view_name, frozenset()))
    definisi = DEFINISI_LENGKAP_VIEW.get(view_name, "(definisi tidak ditemukan)")
    lines = [
        f"Kebutuhan: {atomic_intent.teks_kebutuhan} "
        f"(bentuk jawaban: {atomic_intent.label_bentuk_jawaban.value})",
        f"Tanggal referensi hari ini: {tanggal_referensi.isoformat()}",
    ]
    if feedback:
        lines.append(
            f"\nPERHATIAN: percobaan penyusunan parameter sebelumnya DITOLAK "
            f"chatbot_api dengan alasan: {feedback}\n"
            f"Perbaiki parameter berikut berdasarkan alasan ini."
        )
    lines.append(f"\nView data yang dipakai: {view_name}")
    lines.append(
        f"\nDefinisi lengkap view (untuk memahami arti tiap kolom):\n{definisi}"
    )
    lines.append(
        f"\nDaftar parameter yang VALID untuk view ini "
        f"(HANYA boleh pakai key dari daftar ini):\n{', '.join(whitelist)}"
    )
    return "\n".join(lines)


def _call_llm(
    atomic_intent: AtomicIntent,
    view_name: str,
    tanggal_referensi: date,
    feedback: str | None = None,
):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`), mirror pola
    kecocokan_makna.py/kecukupan_struktural.py."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_PENYUSUNAN_REQUEST,
        messages=[
            {"role": "system", "content": _render_system_prompt()},
            {
                "role": "user",
                "content": _build_user_prompt(
                    atomic_intent, view_name, tanggal_referensi, feedback
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


class _RawPenyusunanRequestResult(BaseModel):
    params: dict[str, str | int | float | bool]


def _parse_response(raw_content: str) -> tuple[dict | None, bool]:
    """gagal=True HANYA kalau JSON rusak/skema salah total - tidak ada
    jaminan struktural per-key di sini (beda dari M3.2/M3.3) karena
    output-nya bukan daftar per-kandidat, cukup satu dict params yang
    lalu disaring `_saring_params_tidak_dikenal()`."""
    try:
        data = json.loads(raw_content)
        hasil = _RawPenyusunanRequestResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return None, True
    return hasil.params, False


def _saring_params_tidak_dikenal(
    view_name: str, params: dict
) -> tuple[dict, list[str]]:
    """Filter deterministik pasca-LLM: buang key mana pun yang TIDAK ada
    persis (exact match) di PARAM_WHITELIST_VIEW[view_name]; secara
    eksplisit strip PARAM_TERLARANG kapan pun muncul (defense in depth,
    meski seharusnya tidak pernah lolos dari instruksi prompt)."""
    whitelist = PARAM_WHITELIST_VIEW.get(view_name, frozenset())
    hasil: dict = {}
    dibuang: list[str] = []
    for key, value in params.items():
        if key in PARAM_TERLARANG:
            dibuang.append(key)
            continue
        if key not in whitelist:
            dibuang.append(key)
            continue
        hasil[key] = value
    return hasil, dibuang


def susun_request_atomic_intent(
    atomic_intent: AtomicIntent,
    view_name: str,
    tanggal_referensi: date | None = None,
    feedback: str | None = None,
) -> HasilPenyusunanRequest:
    """SATU pemanggilan LLM generate-only (tanpa retry internal, tanpa
    verifier independen - Milestone 3.5 terpisah). `domain` diturunkan
    kode via `view_ke_domain()`, TIDAK diminta LLM. `tanggal_referensi`
    default hari ini zona WIB kalau tidak diberikan (test/eval bisa pin
    nilai tetap lewat parameter ini). `feedback` opsional dipakai saat
    dipanggil ulang dari orkestrator Execution (M4.2) untuk merevisi
    parameter yang sebelumnya ditolak chatbot_api (status 400) - lihat
    docstring modul untuk detail."""
    if tanggal_referensi is None:
        tanggal_referensi = _tanggal_referensi_default()

    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    domain = view_ke_domain()[view_name]

    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_PENYUSUNAN_REQUEST)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)
        span.set_attribute(REQUEST_DOMAIN, domain.value)
        span.set_attribute(REQUEST_VIEW_NAME, view_name)

        try:
            response = _call_llm(atomic_intent, view_name, tanggal_referensi, feedback)
        except APIError as exc:
            span.set_attribute(
                "query_engine.penyusunan_request.gagal_alasan", f"api_error: {exc}"
            )
            return HasilPenyusunanRequest(
                atomic_intent=atomic_intent,
                request=None,
                status=StatusEksekusi.GAGAL_TEKNIS,
            )

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        if not response.choices:
            span.set_attribute(
                "query_engine.penyusunan_request.gagal_alasan", "empty_choices"
            )
            return HasilPenyusunanRequest(
                atomic_intent=atomic_intent,
                request=None,
                status=StatusEksekusi.GAGAL_TEKNIS,
            )

        raw_content = response.choices[0].message.content or ""
        params_mentah, gagal = _parse_response(raw_content)

        if gagal:
            span.set_attribute(
                "query_engine.penyusunan_request.gagal_alasan", "parse_error"
            )
            return HasilPenyusunanRequest(
                atomic_intent=atomic_intent,
                request=None,
                status=StatusEksekusi.GAGAL_TEKNIS,
            )

        params_bersih, dibuang = _saring_params_tidak_dikenal(view_name, params_mentah)
        if dibuang:
            span.set_attribute(
                "query_engine.penyusunan_request.params_dibuang",
                ", ".join(sorted(dibuang)),
            )

        request = QueryEngineRequest(
            domain=domain, view_name=view_name, params=params_bersih
        )
        return HasilPenyusunanRequest(
            atomic_intent=atomic_intent, request=request, status=StatusEksekusi.BERHASIL
        )
