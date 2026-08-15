"""Pencocokan Atomic Intent x Data Session Memory (Milestone 1.7, Langkah 7
Context Resolution).

Titik temu jalur Decomposition (M1.6, atomic intent baru turn ini) dan jalur
Session Memory (M1.5, kandidat dari turn yang dirujuk M1.3). Menerima
`candidates` sebagai parameter polos - TIDAK memanggil `retrieve_session_
memory()` sendiri, mirror pola komposisi longgar proyek (lihat decisions.md
Keputusan 10).

Satu panggilan LLM per atomic intent (bukan batch), prompt konservatif
("hanya cocok kalau yakin"), fallback aman ke PERLU_EKSEKUSI pada kegagalan
apa pun - TANPA verifier independen kedua (beda dari pola generate-lalu-
verify M1.6, lihat decisions.md Keputusan 1-2). Kandidat difilter ke
status=berhasil SAJA sebelum ditawarkan sebagai kandidat cocok (Keputusan 4).
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_MATCHING, get_openrouter_client
from src.layers.context_resolution.session_memory import store_session_memory
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
)
from src.observability.tracing import get_tracer
from src.schemas.decomposition import AtomicIntent
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.session_memory import SessionMemoryPackage, StatusEksekusi

_TRACER_NAME = "context_resolution.matching"

_SYSTEM_PROMPT = """Anda adalah komponen sistem yang menilai apakah sebuah \
kebutuhan (atomic intent) pada pertanyaan turn ini SUDAH punya jawabannya di \
antara daftar kandidat yang sudah pernah dihitung dan tersimpan di turn \
sebelumnya. Anda TIDAK menjawab kebutuhannya - tugas Anda murni menilai \
kesesuaian MAKNA.

Balas HANYA dengan JSON persis berbentuk:
{"matched": true atau false, "candidate_index": <nomor index kandidat yang \
cocok, atau null kalau tidak ada>}

Aturan:
- matched=true HANYA kalau kebutuhan ini benar-benar merepresentasikan hal \
yang SAMA PERSIS dengan salah satu kandidat (entitas/waktu/metrik yang \
sama) - BUKAN sekadar topik yang mirip atau berkaitan.
- Kalau ragu, atau kandidat membahas entitas/waktu/metrik yang BERBEDA \
(meski topiknya mirip, mis. bulan berbeda atau metrik berbeda), \
matched=false. Lebih aman mengatakan tidak cocok daripada memaksakan \
kecocokan yang keliru.
- candidate_index HARUS salah satu index yang benar-benar ada di daftar \
kandidat yang diberikan - JANGAN mengarang index yang tidak ada di daftar."""


class _RawMatchResult(BaseModel):
    matched: bool
    candidate_index: int | None = None


def _build_user_prompt(
    atomic_intent: AtomicIntent, candidates: list[SessionMemoryPackage]
) -> str:
    lines = [
        f"Kebutuhan yang dinilai: {atomic_intent.teks_kebutuhan} "
        f"(bentuk jawaban: {atomic_intent.label_bentuk_jawaban.value})",
        "\nDaftar kandidat yang sudah tersimpan:",
    ]
    for i, candidate in enumerate(candidates, start=1):
        lines.append(
            f"- Index {i}: {candidate.teks_kebutuhan} "
            f"(bentuk jawaban: {candidate.label_bentuk_jawaban.value})"
        )
    return "\n".join(lines)


def _call_llm(atomic_intent: AtomicIntent, candidates: list[SessionMemoryPackage]):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_MATCHING,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(atomic_intent, candidates)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _parse_and_decide(
    raw_content: str,
    atomic_intent: AtomicIntent,
    candidates: list[SessionMemoryPackage],
) -> tuple[AtomicIntentMatch, str | None]:
    """Parse + bounds-check hasil LLM. Mengembalikan (result, alasan) - alasan
    diisi kalau hasil dipaksa jadi PERLU_EKSEKUSI karena kegagalan (parse
    gagal atau candidate_index di luar daftar), None kalau jalur normal
    (termasuk matched=false yang genuinely diputuskan LLM)."""
    try:
        data = json.loads(raw_content)
        result = _RawMatchResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        return (
            AtomicIntentMatch(atomic_intent=atomic_intent, status=MatchStatus.PERLU_EKSEKUSI),
            f"parse_error: {exc}",
        )

    if not result.matched or result.candidate_index is None:
        return (
            AtomicIntentMatch(atomic_intent=atomic_intent, status=MatchStatus.PERLU_EKSEKUSI),
            None,
        )

    if not (1 <= result.candidate_index <= len(candidates)):
        reason = (
            f"dangling_candidate_index: {result.candidate_index} di luar "
            f"rentang 1..{len(candidates)}"
        )
        return (
            AtomicIntentMatch(atomic_intent=atomic_intent, status=MatchStatus.PERLU_EKSEKUSI),
            reason,
        )

    paket = candidates[result.candidate_index - 1]
    return (
        AtomicIntentMatch(atomic_intent=atomic_intent, status=MatchStatus.SELESAI, paket=paket),
        None,
    )


def _match_single(
    atomic_intent: AtomicIntent, candidates: list[SessionMemoryPackage]
) -> AtomicIntentMatch:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_MATCHING)

        try:
            response = _call_llm(atomic_intent, candidates)
        except APIError as exc:
            span.set_attribute("matching.forced_fallback_reason", f"api_error: {exc}")
            return AtomicIntentMatch(atomic_intent=atomic_intent, status=MatchStatus.PERLU_EKSEKUSI)

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        raw_content = response.choices[0].message.content or ""
        result, forced_reason = _parse_and_decide(raw_content, atomic_intent, candidates)

        if forced_reason:
            span.set_attribute("matching.forced_fallback_reason", forced_reason)
        span.set_attribute("matching.result", result.status.value)

        return result


def match_atomic_intents(
    atomic_intents: list[AtomicIntent],
    candidates: list[SessionMemoryPackage],
) -> list[AtomicIntentMatch]:
    """Untuk tiap atomic intent, nilai apakah sudah punya jawabannya di
    antara `candidates` (kandidat dari SATU turn yang dirujuk M1.3, hasil
    `retrieve_session_memory()` M1.5 - caller yang menyediakan, lihat
    decisions.md Keputusan 10). Kandidat difilter ke status=berhasil SAJA
    (Keputusan 4). Kalau hasil filter kosong, jalur pintas deterministik:
    semua PERLU_EKSEKUSI, NOL panggilan LLM."""
    filtered = [c for c in candidates if c.status == StatusEksekusi.BERHASIL]

    if not filtered:
        return [
            AtomicIntentMatch(atomic_intent=ai, status=MatchStatus.PERLU_EKSEKUSI)
            for ai in atomic_intents
        ]

    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("matching.evaluate") as span:
        span.set_attribute("candidate.pool_size", len(filtered))

        results = [_match_single(ai, filtered) for ai in atomic_intents]

        matched_count = sum(1 for r in results if r.status == MatchStatus.SELESAI)
        span.set_attribute("intent.matched_count", matched_count)
        span.set_attribute("intent.unmatched_count", len(results) - matched_count)

        return results


def _sumber_arsip(paket_lama: SessionMemoryPackage) -> str:
    """Tentukan nilai `sumber` baris arsip. Kalau paket lama ITU SENDIRI hasil
    eksekusi asli ("eksekusi_baru"), sumber baris arsip dibangun jadi
    "session_memory (turn N)" dengan N = turn_index paket lama (turn asal
    fakta ini pertama kali dihitung). Kalau paket lama SUDAH berupa arsip
    sebelumnya ("session_memory (turn N)", hasil match/arsip turn lain
    sebelum ini - kasus rantai transitif), nilai itu dipertahankan UTUH TANPA
    PERUBAHAN - N tetap merujuk turn PALING ASAL, bukan turn_index paket lama
    (yang di kasus ini adalah turn arsip perantara, bukan turn asal
    sebenarnya). Lihat decisions.md Keputusan 7."""
    if paket_lama.sumber == "eksekusi_baru":
        return f"session_memory (turn {paket_lama.turn_index})"
    return paket_lama.sumber


def archive_matched_packages(
    matches: list[AtomicIntentMatch], session_id: str, turn_index: int
) -> None:
    """Untuk tiap match berstatus SELESAI, simpan ULANG paketnya sebagai
    baris arsip baru di bawah `turn_index` (turn SAAT INI, bukan turn asal).
    `atomic_intent_id`/`teks_kebutuhan`/`label_bentuk_jawaban`/`nilai_hasil`/
    `catatan_interpretasi`/`status` disalin UTUH dari paket lama; `sumber`
    dihitung lewat `_sumber_arsip()` supaya rantai "turn asal sebenarnya"
    tidak pernah putus lintas berapa pun kali paket ini diarsip ulang -
    forced by komentar desain src/db/models.py, lihat decisions.md
    Keputusan 7. Tanpa span baru (Keputusan 11 - mirror store_session_
    memory() sendiri yang juga tanpa span, preseden Keputusan 6 M1.5)."""
    for match in matches:
        if match.status != MatchStatus.SELESAI:
            continue

        paket_lama = match.paket
        assert paket_lama is not None  # dijamin validator AtomicIntentMatch

        arsip = SessionMemoryPackage(
            atomic_intent_id=paket_lama.atomic_intent_id,
            session_id=session_id,
            turn_index=turn_index,
            teks_kebutuhan=paket_lama.teks_kebutuhan,
            label_bentuk_jawaban=paket_lama.label_bentuk_jawaban,
            nilai_hasil=paket_lama.nilai_hasil,
            catatan_interpretasi=paket_lama.catatan_interpretasi,
            status=paket_lama.status,
            sumber=_sumber_arsip(paket_lama),
        )
        store_session_memory(arsip)


def match_and_archive(
    atomic_intents: list[AtomicIntent],
    candidates: list[SessionMemoryPackage],
    session_id: str,
    turn_index: int,
) -> list[AtomicIntentMatch]:
    """Orkestrator tipis: `match_atomic_intents()` lalu `archive_matched_
    packages()` untuk hasilnya. Titik masuk tunggal yang nanti dipanggil
    pipeline penuh (`src/main.py`, belum dirangkai)."""
    matches = match_atomic_intents(atomic_intents, candidates)
    archive_matched_packages(matches, session_id, turn_index)
    return matches
