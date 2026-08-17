"""Pemeriksaan Kecukupan Struktural (Milestone 3.3, langkah PENUTUP tiga
langkah Retriever). Mencocokkan `label_bentuk_jawaban` (M1.6, dibawa
lewat `AtomicIntent`) terhadap grain kandidat `view_name` yang sudah
dinyatakan cocok maknanya di Milestone 3.2 (`HasilKecocokanMakna`, label
`ditemukan`/`sebagian`), lalu memfinalkan SATU `view_name`.

Mekanisme HYBRID (dikonfirmasi user lewat `AskUserQuestion`, lihat
decisions.md Keputusan 1) - mirror pola BM25->embedding fallback M3.1
sendiri: rule table deterministik tri-state (`_evaluasi_deterministik`,
di bawah) sebagai jalur utama; SATU panggilan LLM konservatif (bukan
generate-verify penuh, Keputusan 5) HANYA untuk kandidat yang rule
table-nya menghasilkan `tidak_pasti`, dibatch per kebutuhan atomik
(Keputusan 7). User memilih hybrid secara eksplisit menolak
deterministik-murni karena taksonomi 5 `label_bentuk_jawaban` sekarang
diperkirakan akan bertambah kompleks ke depan - rule table karena itu
WAJIB fail-safe ke `tidak_pasti` (bukan menebak) untuk label yang tidak
dikenali (Keputusan 6), supaya mekanisme genuinely forward-compatible.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL, get_openrouter_client
from src.layers.retriever.definisi_view import DEFINISI_LENGKAP_VIEW
from src.layers.retriever.grain_view import KarakteristikGrain
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
from src.schemas.retriever import KecocokanKandidat, KecukupanKandidat, SumberKeputusanKecukupan
from src.schemas.session_memory import LabelBentukJawaban

_TRACER_NAME = "retriever.kecukupan_struktural"
_PROMPT_ID_FALLBACK = "retriever.kecukupan_struktural_fallback"

_KecukupanRuleResult = tuple[str, str]
"""('cukup' | 'tidak_cukup' | 'tidak_pasti', alasan)."""


def _evaluasi_deterministik(
    label_bentuk_jawaban: LabelBentukJawaban, grain: KarakteristikGrain
) -> _KecukupanRuleResult:
    """Rule table murni Python, TANPA LLM. `nilai_tunggal` selalu cukup
    (bisa diambil dari grain apa pun). `tren` bergantung
    `punya_time_series`. `perbandingan`/`peringkat`/`komposisi`
    bergantung `punya_dimensi_pembanding` (pola sama untuk ketiganya -
    semua butuh grain yang menghasilkan >1 baris comparable dalam satu
    query, mirip cukup untuk membedakan tiga bentuk jawaban ini secara
    struktural). Label yang tidak dikenal rule table -> `tidak_pasti`
    (fail-safe eksplisit, bukan exception/tebakan - Keputusan 6)."""
    if label_bentuk_jawaban == LabelBentukJawaban.NILAI_TUNGGAL:
        return "cukup", "nilai_tunggal selalu bisa diambil dari grain apa pun"

    if label_bentuk_jawaban == LabelBentukJawaban.TREN:
        sinyal = grain.punya_time_series
        if sinyal == "ya":
            return "cukup", "grain punya dimensi waktu berulang, cukup untuk tren"
        if sinyal == "tidak":
            return (
                "tidak_cukup",
                "grain tidak punya dimensi waktu berulang (snapshot/statis), tidak cukup untuk tren",
            )
        return "tidak_pasti", "sinyal punya_time_series ambigu untuk grain ini"

    if label_bentuk_jawaban in (
        LabelBentukJawaban.PERBANDINGAN,
        LabelBentukJawaban.PERINGKAT,
        LabelBentukJawaban.KOMPOSISI,
    ):
        sinyal = grain.punya_dimensi_pembanding
        if sinyal == "ya":
            return (
                "cukup",
                f"grain punya dimensi pembanding, cukup untuk {label_bentuk_jawaban.value}",
            )
        if sinyal == "tidak":
            return (
                "tidak_cukup",
                f"grain tidak punya dimensi pembanding, tidak cukup untuk {label_bentuk_jawaban.value}",
            )
        return "tidak_pasti", "sinyal punya_dimensi_pembanding ambigu untuk grain ini"

    return (
        "tidak_pasti",
        f"label_bentuk_jawaban {label_bentuk_jawaban!r} tidak dikenal rule table - fail-safe ke LLM",
    )


# --- Fallback LLM (satu panggilan konservatif, batch per kebutuhan atomik) ---


def _render_system_prompt_fallback() -> str:
    return load_prompt(_PROMPT_ID_FALLBACK).render()


class _RawKecukupanEntry(BaseModel):
    view_name: str
    cukup: bool
    alasan: str


class _RawKecukupanResult(BaseModel):
    penilaian: list[_RawKecukupanEntry]


def _build_user_prompt_fallback(
    atomic_intent: AtomicIntent, kandidat_tidak_pasti: list[KecocokanKandidat]
) -> str:
    lines = [
        f"Kebutuhan: {atomic_intent.teks_kebutuhan} "
        f"(bentuk jawaban: {atomic_intent.label_bentuk_jawaban.value})",
        "\nDaftar kandidat yang grain-nya ambigu, beserta definisi lengkapnya:",
    ]
    for kk in kandidat_tidak_pasti:
        definisi = DEFINISI_LENGKAP_VIEW.get(kk.kandidat.view_name, "(definisi tidak ditemukan)")
        lines.append(f"\n### {kk.kandidat.view_name}\n{definisi}")
    return "\n".join(lines)


def _call_llm_fallback(atomic_intent: AtomicIntent, kandidat_tidak_pasti: list[KecocokanKandidat]):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`), mirror pola kecocokan_makna.py."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL,
        messages=[
            {"role": "system", "content": _render_system_prompt_fallback()},
            {"role": "user", "content": _build_user_prompt_fallback(atomic_intent, kandidat_tidak_pasti)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _default_aman_semua(
    kandidat_tidak_pasti: list[KecocokanKandidat], alasan: str
) -> list[KecukupanKandidat]:
    """Default aman kalau LLM fallback gagal teknis total (mirror pola
    aman M1.7) - SELURUH kandidat batch itu jadi cukup=False, BUKAN
    exception yang memblokir pemanggil. Salah bilang tidak_cukup aman
    (decisions.md Keputusan 5)."""
    return [
        KecukupanKandidat(
            kandidat=kk.kandidat,
            kecocokan_label=kk.label,
            cukup=False,
            alasan=alasan,
            sumber_keputusan=SumberKeputusanKecukupan.LLM,
        )
        for kk in kandidat_tidak_pasti
    ]


def _parse_fallback(
    raw_content: str, kandidat_tidak_pasti: list[KecocokanKandidat]
) -> tuple[list[KecukupanKandidat], bool]:
    """Parse hasil LLM fallback. gagal=True HANYA kalau seluruh respons
    tidak bisa diparse sama sekali (JSON rusak/skema salah total) -
    caller lalu menerapkan default aman ke SELURUH batch. Kandidat yang
    hilang dari respons yang SEBAGIAN valid diberi default aman
    cukup=False individual (bukan menggagalkan seluruh batch)."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawKecukupanResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return [], True

    by_view_name = {entry.view_name: entry for entry in raw_result.penilaian}
    hasil: list[KecukupanKandidat] = []

    for kk in kandidat_tidak_pasti:
        entry = by_view_name.get(kk.kandidat.view_name)
        if entry is None:
            hasil.append(
                KecukupanKandidat(
                    kandidat=kk.kandidat,
                    kecocokan_label=kk.label,
                    cukup=False,
                    alasan="fallback_anomaly: kandidat tidak muncul di respons LLM, default aman tidak_cukup",
                    sumber_keputusan=SumberKeputusanKecukupan.LLM,
                )
            )
            continue

        hasil.append(
            KecukupanKandidat(
                kandidat=kk.kandidat,
                kecocokan_label=kk.label,
                cukup=bool(entry.cukup),
                alasan=entry.alasan,
                sumber_keputusan=SumberKeputusanKecukupan.LLM,
            )
        )

    return hasil, False


def _evaluasi_llm_fallback(
    atomic_intent: AtomicIntent, kandidat_tidak_pasti: list[KecocokanKandidat]
) -> list[KecukupanKandidat]:
    """SATU panggilan batch (bukan generate-verify penuh, decisions.md
    Keputusan 5) untuk seluruh kandidat `tidak_pasti` satu kebutuhan
    atomik sekaligus (Keputusan 7). Span `"chat"` HANYA dibuka kalau ada
    kandidat untuk dievaluasi (Keputusan 8)."""
    if not kandidat_tidak_pasti:
        return []

    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID_FALLBACK)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm_fallback(atomic_intent, kandidat_tidak_pasti)
        except APIError as exc:
            span.set_attribute(
                "retriever.kecukupan_struktural.fallback_forced_default_reason", f"api_error: {exc}"
            )
            return _default_aman_semua(kandidat_tidak_pasti, f"fallback_teknis: api_error {exc}")

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "retriever.kecukupan_struktural.fallback_forced_default_reason", "empty_choices"
            )
            return _default_aman_semua(kandidat_tidak_pasti, "fallback_teknis: empty_choices")

        raw_content = response.choices[0].message.content or ""
        hasil, gagal = _parse_fallback(raw_content, kandidat_tidak_pasti)

        if gagal:
            span.set_attribute(
                "retriever.kecukupan_struktural.fallback_forced_default_reason", "parse_error_total"
            )
            return _default_aman_semua(kandidat_tidak_pasti, "fallback_teknis: parse_error_total")

        span.set_attribute(
            "retriever.kecukupan_struktural.fallback_cukup_count",
            sum(1 for k in hasil if k.cukup),
        )
        return hasil
