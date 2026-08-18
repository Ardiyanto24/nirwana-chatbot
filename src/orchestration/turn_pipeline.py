"""Orkestrator Turn PIC 7 Level 2: Input Layer (M1.2) -> Pemetaan
Ketergantungan Turn (M1.3) -> Percabangan Paralel (Rewrite M1.4 + Tarik
Session Memory M1.5) -> Decomposition (M1.6).

Fungsi ini membuka span `invoke_agent` PERTAMA KALI di `src/` produksi
(Milestone 7.6) - pembungkus "operasi orkestrasi keseluruhan" per turn
sesuai kontrak Bagian 2 rancangan-observability-ai-chatbot.md. Tumbuh
bertahap tiap milestone Sambungan berikutnya (M7.9-7.16) hingga mencakup
seluruh sembilan layer. `src/main.py` SENGAJA belum memanggil fungsi ini -
penyambungan endpoint ditunda ke Milestone 7.17.

Short-circuit murni alami: `validate_turn_payload()` melempar
`pydantic.ValidationError` yang menjalar keluar tanpa langkah berikutnya
pernah terpanggil - tidak ada `try`/`if` eksplisit yang menyembunyikan
kegagalan. `openai.APIError` dari `detect_turn_dependency()` juga
dibiarkan menjalar apa adanya (celah M1.3, sudah diperbaiki - lihat
docs/keterbatasan-diterima.md #14).

Milestone 7.7: Rewrite (selalu jalan) dan Tarik Session Memory (HANYA
jalan kalau ada referensi terdeteksi) dijalankan BENAR-BENAR paralel
lewat `ThreadPoolExecutor` - context span OTel dipropagasi manual ke
thread worker (`opentelemetry.context.attach()`/`detach()`), diverifikasi
nyata terhadap Jaeger live sebelum dikunci sebagai pendekatan. Kegagalan
ganda (kedua cabang gagal bersamaan) TIDAK ditangani secara khusus -
`.result()` dipanggil berurutan, exception pertama yang menjalar. Lihat
milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/
decisions.md.

Milestone 7.8: setelah blok `ThreadPoolExecutor` selesai (`rewrite_result`
final), `decompose_question()` dipanggil SEKUENSIAL di thread utama
dengan `rewrite_result.rewritten_question` (bukan `payload.question`
asli) - Decomposition murni bergantung data pada hasil Rewrite, bukan
Tarik Memory, sehingga tidak butuh paralelisme baru maupun propagasi
context manual (span `chat` dari ketiga sub-langkah Decomposition
otomatis jadi anak `invoke_agent` karena tetap di thread yang sama). Lihat
milestones/7.8-sambungan-rewrite-decomposition/decisions.md.
"""

from concurrent.futures import ThreadPoolExecutor

from opentelemetry import context as otel_context

from src.layers.context_resolution.rewrite import rewrite_to_standalone
from src.layers.context_resolution.session_memory import retrieve_session_memory
from src.layers.context_resolution.turn_dependency import detect_turn_dependency
from src.layers.decomposition.decompose import decompose_question
from src.layers.input_layer import validate_turn_payload
from src.observability.tracing import get_tracer
from src.schemas.orchestration import KeadaanTurn
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import SessionMemoryPackage
from src.schemas.turn_payload import TurnPayload

_TRACER_NAME = "orchestration"


def _jalankan_rewrite(ctx: otel_context.Context, payload: TurnPayload) -> RewriteResult:
    token = otel_context.attach(ctx)
    try:
        return rewrite_to_standalone(payload)
    finally:
        otel_context.detach(token)


def _jalankan_tarik_memory(
    ctx: otel_context.Context, session_id: str, turn_index: int
) -> list[SessionMemoryPackage]:
    token = otel_context.attach(ctx)
    try:
        return retrieve_session_memory(session_id, turn_index)
    finally:
        otel_context.detach(token)


def proses_turn(raw: dict) -> KeadaanTurn:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("invoke_agent") as span:
        if "session_id" in raw:
            span.set_attribute("session.id", str(raw["session_id"]))
        if "turn_index" in raw:
            try:
                span.set_attribute("turn.index", int(raw["turn_index"]))
            except (TypeError, ValueError):
                pass

        payload = validate_turn_payload(raw)
        ketergantungan = detect_turn_dependency(payload)

        harus_tarik_memory = (
            ketergantungan.is_dependent and ketergantungan.referenced_turn_index is not None
        )

        ctx = otel_context.get_current()
        with ThreadPoolExecutor(max_workers=2) as executor:
            rewrite_future = executor.submit(_jalankan_rewrite, ctx, payload)
            memory_future = (
                executor.submit(
                    _jalankan_tarik_memory,
                    ctx,
                    payload.session_id,
                    ketergantungan.referenced_turn_index,
                )
                if harus_tarik_memory
                else None
            )

            rewrite_result = rewrite_future.result()
            session_memory_result = memory_future.result() if memory_future else None

        decomposition_result = decompose_question(rewrite_result.rewritten_question)

        return KeadaanTurn(
            payload=payload,
            ketergantungan=ketergantungan,
            rewrite=rewrite_result,
            session_memory=session_memory_result,
            decomposition=decomposition_result,
        )
