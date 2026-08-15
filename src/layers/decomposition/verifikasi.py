"""Verifikasi Pemecahan (Milestone 1.6, Langkah 6 Decomposition).

LLM INDEPENDEN kedua yang menilai ulang hasil Langkah 5 (pecah_atomik) -
TANPA melihat proses berpikir/reasoning langkah itu, murni menilai ulang
dari hasil struktural akhirnya. Model BEDA dari Langkah 4/5 (DeepSeek V4 Pro,
bukan Qwen3-32B) - keragaman model untuk peran verifier independen, lihat
decisions.md Keputusan 2.

Generate-lalu-verify PENUH pertama di proyek (M1.3/M1.4 verifikasinya
deterministik ruang-tertutup) - forced by Prinsip Arsitektur #3, lihat
decisions.md Keputusan 5.
"""

import json

from openai import APIError
from pydantic import ValidationError

from src.config.llm import (
    OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI,
    get_openrouter_client,
)
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
)
from src.observability.tracing import get_tracer
from src.schemas.decomposition import PemecahanResult, VerifikasiResult

_TRACER_NAME = "decomposition.verifikasi"

_SYSTEM_PROMPT = """Anda adalah verifikator independen yang menilai APAKAH \
sebuah pemecahan pertanyaan menjadi daftar kebutuhan atomik sudah BENAR - \
Anda TIDAK melihat proses berpikir yang menghasilkan pemecahan itu, murni \
menilai ulang dari hasil akhirnya secara independen.

Periksa dengan teliti:
1. Apakah SELURUH kebutuhan yang tersirat dalam pertanyaan asli benar-benar \
tercakup (tidak ada yang terlewat)?
2. Apakah setiap kebutuhan atomik benar-benar atomik (tidak masih majemuk, \
tidak bisa dipecah lebih lanjut)?
3. Apakah relasi (independen/bergantung) antar kebutuhan sudah benar - \
terutama, apakah kebutuhan yang SEHARUSNYA bergantung pada kebutuhan lain \
(mis. perbandingan yang butuh kedua nilai diketahui lebih dulu) sudah \
ditandai "bergantung", BUKAN keliru ditandai "independen"?
4. Apakah label_bentuk_jawaban tiap kebutuhan sudah sesuai dengan bentuk \
jawaban yang sebenarnya diharapkan pertanyaan itu?

Balas HANYA dengan JSON persis berbentuk:
{"valid": true atau false, "alasan": "penjelasan singkat kenapa \
valid/tidak valid, sebutkan kebutuhan mana yang bermasalah kalau tidak \
valid" atau null kalau valid}"""


def _build_user_prompt(question: str, hasil: PemecahanResult) -> str:
    lines = [f"Pertanyaan asli: {question}", "\nHasil pemecahan:"]
    for i, ai in enumerate(hasil.atomic_intents, start=1):
        dep = f", bergantung pada kebutuhan #{ai.bergantung_pada}" if ai.bergantung_pada else ""
        lines.append(
            f"{i}. {ai.teks_kebutuhan} "
            f"[label_bentuk_jawaban={ai.label_bentuk_jawaban.value}, "
            f"relasi={ai.relasi.value}{dep}]"
        )
    return "\n".join(lines)


def _call_llm(question: str, hasil: PemecahanResult):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`)."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question, hasil)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        extra_body={"reasoning": {"effort": "high"}},
    )


def verifikasi_pemecahan(question: str, hasil: PemecahanResult) -> VerifikasiResult:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI)

        try:
            response = _call_llm(question, hasil)
        except APIError as exc:
            result = VerifikasiResult(valid=False, alasan=f"api_error: {exc}")
            span.set_attribute("decomposition.verification_valid", result.valid)
            return result

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(
                GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens
            )

        raw_content = response.choices[0].message.content or ""
        try:
            data = json.loads(raw_content)
            result = VerifikasiResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            # Parse gagal -> anggap invalid (memaksa retry), BUKAN diam-diam
            # dianggap valid - lebih aman menahan daripada meloloskan tanpa
            # penilaian nyata.
            result = VerifikasiResult(valid=False, alasan=f"verifier_parse_error: {exc}")

        span.set_attribute("decomposition.verification_valid", result.valid)
        if result.alasan:
            span.set_attribute("decomposition.verification_alasan", result.alasan)

        return result
