"""Penyusunan Narasi (Milestone 4.4, Interpretation Langkah 13).

Langkah "generate" pertama Fase 3 - menyusun jawaban akhir berbahasa
Indonesia dari CAMPURAN dua sumber paket (`sumber="eksekusi_baru"` M4.3,
`sumber="session_memory (turn N)"` M1.7), diperlakukan IDENTIK karena
berbagi skema sama persis. Dipisah dari verifikasinya (Milestone 4.5,
belum dibangun) - SATU pemanggilan LLM murni, TANPA retry/parameter
`feedback` internal (forced by preseden penyusunan_request.py M3.4,
lihat decisions.md Keputusan 4).

Output adalah teks bebas (`response.choices[0].message.content`), BUKAN
JSON terstruktur - beda dari seluruh layer LLM lain di project (Keputusan
3). Tidak ada fallback aman untuk sebuah narasi kalau panggilan API gagal;
`APIError` ditandai `error.type=gagal_teknis` pada span lalu diteruskan
apa adanya ke pemanggil, mirror pola store_session_memory() (Keputusan 5).

Kontrak input mengasumsikan SETIAP `atomic_intent` sudah punya TEPAT SATU
`SessionMemoryPackage` pasangan (1:1 by atomic_intent_id, forced diagram
arsitektur §5 - lihat decisions.md Keputusan 9 dan plan Temuan Penting #3).
`_build_user_prompt()` menegakkan ini secara eksplisit (ValueError, bukan
diam-diam melewati atomic_intent yang tidak py pasangan) - lihat plan
Risiko & Mitigasi.
"""

import json

from openai import APIError

from src.config.llm import OPENROUTER_MODEL_NARASI, get_openrouter_client
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    NARRATIVE_TURN_REFERENCE,
    PROMPT_ID,
    PROMPT_VERSION,
)
from src.observability.tracing import get_tracer
from src.prompts.loader import load_prompt
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.interpretation import HasilNarasi
from src.schemas.session_memory import SessionMemoryPackage

_TRACER_NAME = "interpretation.narasi"
_PROMPT_ID = "interpretation.narasi"
_SUMBER_ARSIP_PREFIX = "session_memory (turn "


def _turn_reference(packages: list[SessionMemoryPackage]) -> list[int]:
    """Daftar turn_index UNIK yang dirujuk paket bersumber
    "session_memory (turn N)" - kosong kalau seluruh paket "eksekusi_baru"
    (tidak ada rujukan lintas-turn sama sekali di turn ini)."""
    turns: set[int] = set()
    for paket in packages:
        if paket.sumber.startswith(_SUMBER_ARSIP_PREFIX) and paket.sumber.endswith(")"):
            turn_str = paket.sumber[len(_SUMBER_ARSIP_PREFIX) : -1]
            if turn_str.isdigit():
                turns.add(int(turn_str))
    return sorted(turns)


def _build_user_prompt(
    atomic_intents: list[AtomicIntent], packages: list[SessionMemoryPackage]
) -> str:
    """Rakit daftar kebutuhan + paket + relasi ketergantungan sebagai teks
    terstruktur untuk LLM. Menegakkan kontrak 1:1 atomic_intent<->package
    SECARA EKSPLISIT (ValueError) - forced by Risiko & Mitigasi plan:
    "gagal terlihat jelas, bukan diam-diam salah"."""
    packages_by_id = {p.atomic_intent_id: p for p in packages}
    intents_by_id = {ai.atomic_intent_id: ai for ai in atomic_intents}

    hilang = [
        ai.atomic_intent_id
        for ai in atomic_intents
        if ai.atomic_intent_id not in packages_by_id
    ]
    if hilang:
        raise ValueError(
            f"atomic_intent tanpa package pasangan (kontrak 1:1 dilanggar): {hilang}"
        )

    lines = ["Daftar kebutuhan turn ini:"]
    for i, atomic_intent in enumerate(atomic_intents, start=1):
        paket = packages_by_id[atomic_intent.atomic_intent_id]
        lines.append(f"\n{i}. Kebutuhan: {atomic_intent.teks_kebutuhan}")
        lines.append(f"   Bentuk jawaban: {atomic_intent.label_bentuk_jawaban.value}")
        lines.append(f"   Status: {paket.status.value}")
        lines.append(f"   Sumber: {paket.sumber}")
        lines.append(
            f"   Nilai hasil: {json.dumps(paket.nilai_hasil, ensure_ascii=False)}"
        )
        if paket.catatan_interpretasi:
            lines.append(
                f"   Catatan interpretasi: {'; '.join(paket.catatan_interpretasi)}"
            )
        if (
            atomic_intent.relasi == RelasiKebutuhan.BERGANTUNG
            and atomic_intent.bergantung_pada
        ):
            prasyarat = []
            for dep_id in atomic_intent.bergantung_pada:
                dep_intent = intents_by_id.get(dep_id)
                dep_paket = packages_by_id.get(dep_id)
                if dep_intent is not None and dep_paket is not None:
                    prasyarat.append(
                        f'"{dep_intent.teks_kebutuhan}" (status: {dep_paket.status.value})'
                    )
                else:
                    prasyarat.append(f"id={dep_id} (tidak ditemukan dalam daftar ini)")
            lines.append(f"   Bergantung pada: {'; '.join(prasyarat)}")

    return "\n".join(lines)


def _call_llm(atomic_intents: list[AtomicIntent], packages: list[SessionMemoryPackage]):
    """Panggilan mentah ke OpenRouter, tanpa span - dipisah supaya bisa
    dipakai ulang oleh skrip eval (`evals/`), mirror pola `_call_llm()`
    layer LLM lain. Tanpa `response_format` (Keputusan 3 - output teks
    bebas)."""
    client = get_openrouter_client()
    system_prompt = load_prompt(_PROMPT_ID).render()
    user_prompt = _build_user_prompt(atomic_intents, packages)
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_NARASI,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )


def susun_narasi(
    atomic_intents: list[AtomicIntent],
    packages: list[SessionMemoryPackage],
    session_id: str,
    turn_index: int,
) -> HasilNarasi:
    """Orkestrator M4.4. SATU pemanggilan LLM, TANPA retry/feedback
    internal (Keputusan 4). `APIError` ditandai error.type=gagal_teknis
    pada span lalu diteruskan apa adanya (Keputusan 5) - TIDAK ada
    fallback aman untuk sebuah narasi."""
    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("session.id", session_id)
        span.set_attribute("turn.index", turn_index)
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_NARASI)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)
        span.set_attribute(NARRATIVE_TURN_REFERENCE, _turn_reference(packages))

        try:
            response = _call_llm(atomic_intents, packages)
        except APIError:
            span.set_attribute("error.type", "gagal_teknis")
            raise

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        narasi_teks = response.choices[0].message.content or ""
        return HasilNarasi(narasi=narasi_teks)
