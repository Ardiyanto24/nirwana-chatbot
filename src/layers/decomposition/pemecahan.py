"""Pemecahan Atomik (Milestone 1.6, Langkah 5 Decomposition).

Memecah kalimat mandiri jadi daftar atomic intent (relasi + label bentuk
jawaban). LLM mereferensikan kebutuhan lain lewat index LOKAL (posisi dalam
responsnya sendiri) - kode yang generate atomic_intent_id (UUID4) SETELAH
respons diterima, lalu menerjemahkan index lokal jadi atomic_intent_id
sungguhan, dengan bounds-check deterministik (index dangling -> di-drop,
ditandai anomali). LLM TIDAK PERNAH diminta bikin ID sendiri - lihat
decisions.md Keputusan 7.

Parameter `feedback` opsional dipakai saat retry (dipanggil ulang dari
decompose.py kalau Langkah 6/Verifikasi menilai hasil sebelumnya invalid).
"""

import json
import uuid

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_DECOMPOSITION, get_openrouter_client
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
from src.schemas.decomposition import (
    AtomicIntent,
    KlasifikasiKebutuhan,
    PemecahanResult,
    RelasiKebutuhan,
)
from src.schemas.session_memory import LabelBentukJawaban

_TRACER_NAME = "decomposition.pemecahan"
_PROMPT_ID = "decomposition.pemecahan"

_FALLBACK_LABEL = LabelBentukJawaban.NILAI_TUNGGAL


class _RawAtomicIntent(BaseModel):
    index: int
    teks_kebutuhan: str
    label_bentuk_jawaban: str
    relasi: str
    bergantung_pada_index: list[int] | None = None


def _build_user_prompt(
    question: str, klasifikasi: KlasifikasiKebutuhan, feedback: str | None
) -> str:
    lines = [f"Klasifikasi kebutuhan (dari langkah sebelumnya): {klasifikasi.value}"]
    if feedback:
        lines.append(
            f"\nPERHATIAN: percobaan pemecahan sebelumnya dinilai KELIRU oleh "
            f"proses verifikasi independen, dengan alasan: {feedback}\n"
            f"Perbaiki pemecahan berikut berdasarkan alasan ini."
        )
    lines.append(f"\nPertanyaan: {question}")
    return "\n".join(lines)


def _call_llm(
    question: str, klasifikasi: KlasifikasiKebutuhan, feedback: str | None = None
):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    system_prompt = load_prompt(_PROMPT_ID).render()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DECOMPOSITION,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": _build_user_prompt(question, klasifikasi, feedback),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _fallback_result(question: str) -> PemecahanResult:
    return PemecahanResult(
        atomic_intents=[
            AtomicIntent(
                atomic_intent_id=str(uuid.uuid4()),
                teks_kebutuhan=question,
                label_bentuk_jawaban=_FALLBACK_LABEL,
                relasi=RelasiKebutuhan.INDEPENDEN,
            )
        ]
    )


def _parse_and_transform(
    raw_content: str, question: str
) -> tuple[PemecahanResult, list[str]]:
    """Parse JSON, generate atomic_intent_id (UUID) per item, terjemahkan
    bergantung_pada_index (lokal) jadi bergantung_pada (UUID) dengan
    bounds-check deterministik. Mengembalikan (result, daftar_anomali)."""
    anomalies: list[str] = []
    try:
        data = json.loads(raw_content)
        raw_items = [
            _RawAtomicIntent.model_validate(item) for item in data["kebutuhan"]
        ]
    except (json.JSONDecodeError, KeyError, ValidationError, TypeError) as exc:
        return _fallback_result(question), [f"parse_error: {exc}"]

    index_to_uuid = {item.index: str(uuid.uuid4()) for item in raw_items}
    valid_indices = set(index_to_uuid)

    atomic_intents: list[AtomicIntent] = []
    for item in raw_items:
        try:
            label = LabelBentukJawaban(item.label_bentuk_jawaban)
            relasi = RelasiKebutuhan(item.relasi)
        except ValueError as exc:
            anomalies.append(f"index_{item.index}_invalid_enum: {exc}")
            continue

        bergantung_pada: list[str] | None = None
        if relasi == RelasiKebutuhan.BERGANTUNG:
            requested = item.bergantung_pada_index or []
            resolved = [index_to_uuid[i] for i in requested if i in valid_indices]
            dropped = [i for i in requested if i not in valid_indices]
            if dropped:
                anomalies.append(
                    f"index_{item.index}_dangling_bergantung_pada: {dropped}"
                )
            if not resolved:
                # Tidak ada rujukan valid tersisa - turunkan jadi independen
                # (closed-space safe default, mirror bounds-check M1.3).
                anomalies.append(
                    f"index_{item.index}_no_valid_dependency_fallback_independen"
                )
                relasi = RelasiKebutuhan.INDEPENDEN
            else:
                bergantung_pada = resolved

        try:
            atomic_intents.append(
                AtomicIntent(
                    atomic_intent_id=index_to_uuid[item.index],
                    teks_kebutuhan=item.teks_kebutuhan,
                    label_bentuk_jawaban=label,
                    relasi=relasi,
                    bergantung_pada=bergantung_pada,
                )
            )
        except ValidationError as exc:
            anomalies.append(f"index_{item.index}_construction_failed: {exc}")

    if not atomic_intents:
        return _fallback_result(question), anomalies + [
            "all_items_failed_fallback_applied"
        ]

    return PemecahanResult(atomic_intents=atomic_intents), anomalies


def pecah_atomik(
    question: str,
    klasifikasi: KlasifikasiKebutuhan,
    feedback: str | None = None,
) -> PemecahanResult:
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DECOMPOSITION)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm(question, klasifikasi, feedback)
        except APIError as exc:
            span.set_attribute(
                "decomposition.forced_fallback_reason", f"api_error: {exc}"
            )
            result = _fallback_result(question)
            span.set_attribute("intent.count", len(result.atomic_intents))
            span.set_attribute("intent.relation_type", "independen")
            return result

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        raw_content = response.choices[0].message.content or ""
        result, anomalies = _parse_and_transform(raw_content, question)

        if anomalies:
            span.set_attribute("decomposition.pemecahan_anomalies", anomalies)

        span.set_attribute("intent.count", len(result.atomic_intents))
        relation_types = sorted({ai.relasi.value for ai in result.atomic_intents})
        span.set_attribute("intent.relation_type", relation_types)

        return result
