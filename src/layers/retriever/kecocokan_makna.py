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
    OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI,
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
_PROMPT_ID_VERIFIKASI = "retriever.kecocokan_makna_verifikasi"


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


# --- Langkah 2 (verifikasi, koreksi dua arah) --------------------------------


def _render_context_verifikasi() -> dict:
    """Variabel render prompt Langkah 2 - konstanta terpisah dari Langkah 1
    meski isinya sama (CATATAN_LINTAS_DOMAIN) - mirror preseden
    identifikasi.py/verifikasi_titik_buta.py (M2.1) yang masing-masing py
    `_render_context()` sendiri walau keduanya reuse DESKRIPSI_DOMAIN yang sama."""
    return {"catatan_lintas_domain": CATATAN_LINTAS_DOMAIN}


def _render_system_prompt_verifikasi() -> str:
    return load_prompt(_PROMPT_ID_VERIFIKASI).render(**_render_context_verifikasi())


def _build_user_prompt_verifikasi(
    hasil_pencarian: HasilPencarianKandidat, hasil_awal: list[KecocokanKandidat]
) -> str:
    ai = hasil_pencarian.atomic_intent
    awal_by_view_name = {k.kandidat.view_name: k for k in hasil_awal}
    lines = [
        f"Kebutuhan: {ai.teks_kebutuhan} (bentuk jawaban: {ai.label_bentuk_jawaban.value})",
        "\nDaftar kandidat, definisi lengkapnya, dan penilaian awal (Langkah 1):",
    ]
    for kv in hasil_pencarian.kandidat:
        definisi = DEFINISI_LENGKAP_VIEW.get(kv.view_name, "(definisi tidak ditemukan)")
        awal = awal_by_view_name.get(kv.view_name)
        penilaian_awal_text = (
            f'label="{awal.label.value}", alasan="{awal.alasan}"'
            if awal is not None
            else "(tidak ada penilaian awal)"
        )
        lines.append(
            f"\n### {kv.view_name}\n{definisi}\n\nPenilaian awal (Langkah 1): {penilaian_awal_text}"
        )
    return "\n".join(lines)


def _call_llm_verifikasi(hasil_pencarian: HasilPencarianKandidat, hasil_awal: list[KecocokanKandidat]):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI,
        messages=[
            {"role": "system", "content": _render_system_prompt_verifikasi()},
            {"role": "user", "content": _build_user_prompt_verifikasi(hasil_pencarian, hasil_awal)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        extra_body={"reasoning": {"effort": "high"}},
    )


def _parse_verifikasi(
    raw_content: str,
    kandidat: list[KandidatView],
    hasil_awal: list[KecocokanKandidat],
) -> tuple[list[KecocokanKandidat], bool, str | None]:
    """Parse hasil Langkah 2 + jaminan struktural, SAMA seperti
    `_parse_generate` DENGAN SATU PERBEDAAN: kalau satu kandidat spesifik
    hilang/invalid dari respons Langkah 2 (tapi respons secara keseluruhan
    ter-parse), fallback ke label Langkah 1 kandidat itu SAJA (bukan
    default generik SEBAGIAN) - kita SUDAH py penilaian nyata untuk
    kandidat itu dari Langkah 1, lebih aman dipakai daripada menebak.
    gagal=True HANYA kalau seluruh respons tidak bisa diparse sama sekali
    (orkestrator lalu mempertahankan hasil_awal utuh - Keputusan 8)."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawPenilaianResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return [], True, f"parse_error: {exc}"

    awal_by_view_name = {k.kandidat.view_name: k for k in hasil_awal}
    by_view_name = {entry.view_name: entry for entry in raw_result.penilaian}
    hasil: list[KecocokanKandidat] = []
    anomali: list[str] = []

    for kv in kandidat:
        entry = by_view_name.get(kv.view_name)
        awal = awal_by_view_name.get(kv.view_name)

        if entry is None:
            hasil.append(
                awal
                if awal is not None
                else _entri_aman_default(
                    kv, "parse_anomaly: kandidat tidak muncul di respons Langkah 2 maupun Langkah 1"
                )
            )
            anomali.append(f"missing:{kv.view_name}")
            continue

        try:
            label = LabelKecocokanMakna(entry.label)
        except ValueError:
            hasil.append(
                awal
                if awal is not None
                else _entri_aman_default(kv, f"parse_anomaly: label tidak valid ({entry.label!r})")
            )
            anomali.append(f"invalid_label:{kv.view_name}={entry.label}")
            continue

        hasil.append(KecocokanKandidat(kandidat=kv, label=label, alasan=entry.alasan))

    reason = f"partial_anomaly: {anomali}" if anomali else None
    return hasil, False, reason


def _langkah_verifikasi(
    hasil_pencarian: HasilPencarianKandidat, hasil_awal: list[KecocokanKandidat]
) -> tuple[list[KecocokanKandidat], bool]:
    """Langkah 2 - panggil LLM verifikasi independen, kembalikan
    (kecocokan, gagal). Hasil yang dikembalikan MENGGANTIKAN hasil_awal
    sepenuhnya kalau gagal=False (koreksi dua arah, bukan union aditif -
    decisions.md Keputusan 1)."""
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID_VERIFIKASI)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm_verifikasi(hasil_pencarian, hasil_awal)
        except APIError as exc:
            span.set_attribute(
                "retriever.kecocokan_makna.verifikasi_forced_fallback_reason", f"api_error: {exc}"
            )
            return [], True

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "retriever.kecocokan_makna.verifikasi_forced_fallback_reason", "empty_choices"
            )
            return [], True

        raw_content = response.choices[0].message.content or ""
        hasil, gagal, anomaly_reason = _parse_verifikasi(
            raw_content, hasil_pencarian.kandidat, hasil_awal
        )

        if anomaly_reason:
            span.set_attribute(
                "retriever.kecocokan_makna.verifikasi_forced_fallback_reason", anomaly_reason
            )

        dikoreksi_count = sum(
            1
            for baru in hasil
            for lama in hasil_awal
            if baru.kandidat.view_name == lama.kandidat.view_name and baru.label != lama.label
        )
        span.set_attribute("retriever.kecocokan_makna.verifikasi_dikoreksi_count", dikoreksi_count)
        span.set_attribute(
            "retriever.kecocokan_makna.verifikasi_ditemukan_count",
            sum(1 for k in hasil if k.label == LabelKecocokanMakna.DITEMUKAN),
        )

        return hasil, gagal
