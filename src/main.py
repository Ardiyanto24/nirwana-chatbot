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

Jalankan: uv run uvicorn src.main:app --port 8001
(port 8000 dipakai chatbot_api, yang WAJIB jalan bersamaan karena
dipanggil proses_turn() secara internal saat Execution)
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from openai import APIError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.observability.tracing import setup_tracing
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
    return _build_turn_response(keadaan)
