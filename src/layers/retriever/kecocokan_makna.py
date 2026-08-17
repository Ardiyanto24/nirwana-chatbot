"""Pemeriksaan Kecocokan Makna (Milestone 3.2, tahap kedua Retriever).

Menilai TIAP kandidat `view_name` hasil Milestone 3.1 (`HasilPencarianKandidat`)
terhadap definisi lengkapnya di katalog (grain, sumber, kolom, catatan) -
bukan hanya namanya. Dua langkah berurutan, BATCH per kebutuhan atomik
(seluruh kandidat sekaligus, bukan satu panggilan per kandidat - lihat
decisions.md Keputusan 2):

- Langkah 1 (generate, Qwen3-32B): label awal + alasan per kandidat.
- Langkah 2 (verifikasi, DeepSeek V4 Pro reasoning="high"): independen
  menilai ulang dari definisi lengkap, hasilnya MENGGANTIKAN Langkah 1
  sepenuhnya (koreksi dua arah - beda dari union aditif M2.1/M2.3, lihat
  decisions.md Keputusan 1).

Satu file (bukan dipecah 3 file seperti domain_gate/) - mirror struktur
context_resolution/matching.py, karena granularitas kerja di sini adalah
"satu kebutuhan atomik beserta seluruh kandidatnya", bukan per-kandidat
terpisah yang butuh modul sendiri-sendiri.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import (
    OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE,
    get_openrouter_client,
)
from src.layers.retriever.definisi_view import CATATAN_LINTAS_DOMAIN, DEFINISI_LENGKAP_VIEW
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
from src.schemas.retriever import HasilPencarianKandidat, KandidatView, KecocokanKandidat, LabelKecocokanMakna

_TRACER_NAME = "retriever.kecocokan_makna"
_PROMPT_ID_GENERATE = "retriever.kecocokan_makna_generate"


def _render_context_generate() -> dict:
    """Variabel render prompt Langkah 1 - dipakai kode produksi DAN provider
    Promptfoo (`prompt_reliability/provider.py`, config `render_context`)
    supaya reliability testing selalu memakai context identik dengan yang
    benar-benar dikirim saat runtime."""
    return {"catatan_lintas_domain": CATATAN_LINTAS_DOMAIN}


def _render_system_prompt_generate() -> str:
    return load_prompt(_PROMPT_ID_GENERATE).render(**_render_context_generate())


class _RawPenilaianEntry(BaseModel):
    view_name: str
    label: str
    alasan: str


class _RawPenilaianResult(BaseModel):
    penilaian: list[_RawPenilaianEntry]


def _build_user_prompt_generate(hasil_pencarian: HasilPencarianKandidat) -> str:
    ai = hasil_pencarian.atomic_intent
    lines = [
        f"Kebutuhan: {ai.teks_kebutuhan} (bentuk jawaban: {ai.label_bentuk_jawaban.value})",
        "\nDaftar kandidat beserta definisi lengkapnya:",
    ]
    for kv in hasil_pencarian.kandidat:
        definisi = DEFINISI_LENGKAP_VIEW.get(kv.view_name, "(definisi tidak ditemukan)")
        lines.append(f"\n### {kv.view_name}\n{definisi}")
    return "\n".join(lines)


def _call_llm_generate(hasil_pencarian: HasilPencarianKandidat):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE,
        messages=[
            {"role": "system", "content": _render_system_prompt_generate()},
            {"role": "user", "content": _build_user_prompt_generate(hasil_pencarian)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _entri_aman_default(kandidat: KandidatView, alasan: str) -> KecocokanKandidat:
    """Kandidat yang hilang/anomali di respons LLM WAJIB tetap muncul di
    keluaran (bukan drop diam-diam) - jaminan struktural decisions.md
    Keputusan 9. Default label=SEBAGIAN (bukan DITEMUKAN) - aman kalau
    memang ternyata bukan kandidat yang tepat, bukan optimis keliru."""
    return KecocokanKandidat(kandidat=kandidat, label=LabelKecocokanMakna.SEBAGIAN, alasan=alasan)


def _parse_generate(
    raw_content: str, kandidat: list[KandidatView]
) -> tuple[list[KecocokanKandidat], bool, str | None]:
    """Parse hasil LLM + jaminan struktural (SETIAP kandidat input WAJIB
    muncul di keluaran). Mengembalikan (hasil, gagal, alasan_anomali) -
    gagal=True HANYA kalau seluruh respons tidak bisa diparse sama sekali
    (JSON rusak/skema salah total); anomali PARSIAL (satu-dua kandidat
    hilang/label invalid di respons yang sebagian besar valid) TIDAK
    dianggap gagal total - kandidat terdampak diberi default aman, bukan
    memaksa GAGAL_TEKNIS untuk seluruh batch karena satu entri bermasalah."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawPenilaianResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return [], True, f"parse_error: {exc}"

    by_view_name = {entry.view_name: entry for entry in raw_result.penilaian}
    hasil: list[KecocokanKandidat] = []
    anomali: list[str] = []

    for kv in kandidat:
        entry = by_view_name.get(kv.view_name)
        if entry is None:
            hasil.append(
                _entri_aman_default(kv, "parse_anomaly: kandidat tidak muncul di respons LLM")
            )
            anomali.append(f"missing:{kv.view_name}")
            continue

        try:
            label = LabelKecocokanMakna(entry.label)
        except ValueError:
            hasil.append(
                _entri_aman_default(
                    kv, f"parse_anomaly: label tidak valid ({entry.label!r})"
                )
            )
            anomali.append(f"invalid_label:{kv.view_name}={entry.label}")
            continue

        hasil.append(KecocokanKandidat(kandidat=kv, label=label, alasan=entry.alasan))

    reason = f"partial_anomaly: {anomali}" if anomali else None
    return hasil, False, reason


def _langkah_generate(hasil_pencarian: HasilPencarianKandidat) -> tuple[list[KecocokanKandidat], bool]:
    """Langkah 1 - panggil LLM generate, kembalikan (kecocokan, gagal).
    Diasumsikan `hasil_pencarian.kandidat` TIDAK kosong - jalur pintas
    kandidat kosong ditangani orkestrator (Checkpoint 9), bukan di sini."""
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID_GENERATE)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm_generate(hasil_pencarian)
        except APIError as exc:
            span.set_attribute(
                "retriever.kecocokan_makna.generate_forced_fallback_reason", f"api_error: {exc}"
            )
            return [], True

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "retriever.kecocokan_makna.generate_forced_fallback_reason", "empty_choices"
            )
            return [], True

        raw_content = response.choices[0].message.content or ""
        hasil, gagal, anomaly_reason = _parse_generate(raw_content, hasil_pencarian.kandidat)

        if anomaly_reason:
            span.set_attribute(
                "retriever.kecocokan_makna.generate_forced_fallback_reason", anomaly_reason
            )
        span.set_attribute(
            "retriever.kecocokan_makna.generate_ditemukan_count",
            sum(1 for k in hasil if k.label == LabelKecocokanMakna.DITEMUKAN),
        )

        return hasil, gagal
