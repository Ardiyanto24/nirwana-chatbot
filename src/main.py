"""Aplikasi FastAPI - titik masuk HTTP untuk AI Chatbot RBAC.

Milestone 7.17: `POST /v1/turns` sekarang menjalankan pipeline penuh
9 layer (`proses_turn()`, src/orchestration/turn_pipeline.py) - BUKAN
lagi echo payload tervalidasi seperti Milestone 1.2. Exception yang
bisa lolos dari proses_turn() dipetakan ke status HTTP wajar (lihat
milestones/7.17-membangun-endpoint-api/decisions.md Keputusan 6):
pydantic.ValidationError -> 422 (existing sejak M1.2, TIDAK diubah),
openai.APIError -> 503 (dependency LLM tidak tersedia), SQLAlchemyError
/RuntimeError -> 500 (kegagalan internal/DB), catch-all Exception -> 500
(termasuk celah laten IndexError/KeyError yang ditemukan riset M7.17
tapi SENGAJA TIDAK diperbaiki di layer manapun, konsisten batasan
mengikat M7.17 - lihat docs/keterbatasan-diterima.md #17). Seluruh
body error `{"detail": "<pesan aman>"}`, tidak memuat tipe/pesan
exception asli.

Narasi yang gagal verifikasi kesetiaan (HasilVerifikasiNarasi.lolos
False ATAU None/GAGAL_TEKNIS) diganti pesan generik aman, BUKAN narasi
asli - keputusan konservatif fase awal (Keputusan 1), dicatat
provisional di docs/keputusan-tertunda.md #5.

Milestone 7.18: setelah TurnResponse dibangun, `_simpan_riwayat_
percakapan_aman()` menulis satu baris ke tabel `conversation_turns`
(riwayat untuk kebutuhan APLIKASI, terpisah dari Session Memory) lewat
`simpan_riwayat_turn()` (src/orchestration/riwayat_percakapan.py).
Panggilan ini SENGAJA dibungkus try/except yang menangkap Exception
dan TIDAK re-raise - SATU-SATUNYA titik "tangkap-dan-diam" di seluruh
project (forced literal KK2 M7.18: kegagalan menulis riwayat TIDAK
BOLEH menggagalkan response ke user). Kegagalan tetap tercatat sebagai
sinyal terpisah lewat span `riwayat.simpan` (error.type=gagal_teknis)
milik simpan_riwayat_turn() sendiri, terlihat di Jaeger meski tidak
sampai ke response HTTP - lihat
milestones/7.18-database-percakapan/decisions.md Keputusan 5.

Milestone 6.1 (addendum, gap ditemukan riset PIC 6): span `riwayat.simpan`
tadinya jadi trace akar terpisah dari `invoke_agent` (context sudah exit
saat `_simpan_riwayat_percakapan_aman()` dipanggil) - `traces.status`
akibatnya tidak akan pernah terisi untuk trace utama begitu data asli
mengalir ke Supabase (PIC 6). Diperbaiki dengan merekonstruksi
`SpanContext`/`NonRecordingSpan` dari `KeadaanTurn.invoke_agent_trace_id`/
`invoke_agent_span_id`, `context.attach()`/`detach()` membungkus
`simpan_riwayat_turn()`. Lihat
milestones/6.1-membangun-exporter-dasar/decisions.md Keputusan 2.

Jalankan: uv run uvicorn src.main:app --port 8001
(port 8000 dipakai chatbot_api, yang WAJIB jalan bersamaan karena
dipanggil proses_turn() secara internal saat Execution)
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from openai import APIError
from opentelemetry import context as otel_context
from opentelemetry import trace as otel_trace
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.observability.tracing import setup_tracing
from src.orchestration.riwayat_percakapan import (
    simpan_riwayat_turn,
    tentukan_status_keseluruhan_turn,
)
from src.orchestration.turn_pipeline import proses_turn
from src.schemas.api_response import TurnResponse
from src.schemas.orchestration import KeadaanTurn

SERVICE_NAME = "nirwana-chatbot-input-layer"

_PESAN_NARASI_BELUM_TERVERIFIKASI = (
    "Sistem belum dapat memastikan keakuratan jawaban ini sepenuhnya. Mohon "
    "ajukan pertanyaan ini kembali, atau hubungi tim terkait untuk verifikasi "
    "lebih lanjut."
)
_PESAN_VERIFIKASI_GAGAL_TEKNIS = (
    "Verifikasi kesetiaan jawaban tidak dapat dijalankan karena kendala teknis."
)
_PESAN_LLM_TIDAK_TERSEDIA = (
    "Layanan AI sedang tidak tersedia, silakan coba lagi beberapa saat lagi."
)
_PESAN_KESALAHAN_INTERNAL = (
    "Terjadi kesalahan internal, silakan coba lagi atau hubungi tim terkait."
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_tracing(SERVICE_NAME)
    yield


app = FastAPI(title="Nirwana Chatbot - Input Layer", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    # Milestone 8.7 - murni buktikan proses hidup (tanpa DB/LLM/chatbot_api),
    # dipakai verifikasi image container + nanti health-check reverse-proxy
    # (M8.9) dan deploy pipeline (M8.10, KK sumber eksplisit menyebut
    # "endpoint health/versi").
    return {"status": "ok"}


@app.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    # validate_turn_payload() memanggil Pydantic secara manual (bukan lewat
    # parameter endpoint bertipe model), jadi FastAPI tidak otomatis
    # menangani ValidationError seperti pada RequestValidationError bawaan -
    # exception handler ini yang menyamakan perilakunya jadi 422 dengan
    # detail per-field, sesuai kontrak Output Milestone 1.2.
    return JSONResponse(
        status_code=422, content={"detail": jsonable_encoder(exc.errors())}
    )


@app.exception_handler(APIError)
async def llm_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": _PESAN_LLM_TIDAK_TERSEDIA})


@app.exception_handler(SQLAlchemyError)
@app.exception_handler(RuntimeError)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": _PESAN_KESALAHAN_INTERNAL})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": _PESAN_KESALAHAN_INTERNAL})


def _build_turn_response(keadaan: KeadaanTurn) -> TurnResponse:
    hasil_narasi, hasil_verifikasi, visualisasi = keadaan.interpretation
    terverifikasi = hasil_verifikasi.lolos is True

    if terverifikasi:
        narasi = hasil_narasi.narasi
        catatan_verifikasi = None
    else:
        narasi = _PESAN_NARASI_BELUM_TERVERIFIKASI
        catatan_verifikasi = hasil_verifikasi.alasan or _PESAN_VERIFIKASI_GAGAL_TEKNIS

    return TurnResponse(
        session_id=keadaan.payload.session_id,
        turn_index=keadaan.payload.turn_index,
        narasi=narasi,
        terverifikasi=terverifikasi,
        catatan_verifikasi=catatan_verifikasi,
        visualisasi=visualisasi if terverifikasi else None,
    )


def _simpan_riwayat_percakapan_aman(
    keadaan: KeadaanTurn, turn_response: TurnResponse
) -> None:
    # SATU-SATUNYA try/except "tangkap-dan-diam" (tidak re-raise) di
    # seluruh project - forced literal KK2 M7.18 ("kegagalan penulisan
    # riwayat tidak boleh menggagalkan pengiriman response ke user").
    # Kegagalan TETAP tercatat sebagai sinyal terpisah lewat span
    # riwayat.simpan (error.type=gagal_teknis) milik simpan_riwayat_turn()
    # sendiri, bukan disembunyikan - hanya tidak sampai ke response HTTP.
    #
    # M6.1 addendum: context invoke_agent DIREKONSTRUKSI dari trace_id/
    # span_id di KeadaanTurn (with-block invoke_agent asli sudah exit saat
    # fungsi ini dipanggil, Context aslinya tidak lagi bisa dipakai ulang)
    # - span riwayat.simpan supaya genuinely jadi anak invoke_agent, bukan
    # trace akar terpisah. Lihat
    # milestones/6.1-membangun-exporter-dasar/decisions.md Keputusan 2.
    try:
        span_context = otel_trace.SpanContext(
            trace_id=int(keadaan.invoke_agent_trace_id, 16),
            span_id=int(keadaan.invoke_agent_span_id, 16),
            is_remote=True,
            trace_flags=otel_trace.TraceFlags(otel_trace.TraceFlags.SAMPLED),
        )
        ctx = otel_trace.set_span_in_context(otel_trace.NonRecordingSpan(span_context))
        token = otel_context.attach(ctx)
        try:
            status = tentukan_status_keseluruhan_turn(keadaan.paket_narasi)
            simpan_riwayat_turn(
                session_id=keadaan.payload.session_id,
                turn_index=keadaan.payload.turn_index,
                pertanyaan=keadaan.payload.question,
                narasi=turn_response.narasi,
                status=status,
            )
        finally:
            otel_context.detach(token)
    except Exception:
        pass


@app.post("/v1/turns", response_model=TurnResponse)
def submit_turn(payload: dict) -> TurnResponse:
    # def BIASA (bukan async def) SENGAJA - proses_turn() sepenuhnya
    # sinkron/blocking (LLM/DB/HTTP berurutan, bisa menit-menitan). FastAPI
    # otomatis menjalankan path operation function def biasa di threadpool
    # worker (starlette.concurrency.run_in_threadpool), sehingga event loop
    # tetap bisa melayani request lain (termasuk health check) selama satu
    # turn diproses - kalau ini async def, proses_turn() akan memblokir
    # event loop TUNGGAL uvicorn sepenuhnya (ditemukan nyata Checkpoint 6,
    # server berhenti merespons apa pun selama satu turn diproses).
    keadaan = proses_turn(payload)
    turn_response = _build_turn_response(keadaan)
    _simpan_riwayat_percakapan_aman(keadaan, turn_response)
    return turn_response
