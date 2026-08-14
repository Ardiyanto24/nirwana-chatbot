"""Aplikasi FastAPI - titik masuk HTTP untuk AI Chatbot RBAC.

Milestone 1.2: hanya Input Layer (`POST /v1/turns`) yang benar-benar
berjalan. Layer 2-9 belum ada, jadi endpoint ini mengembalikan payload
tervalidasi sebagai echo (belum diteruskan ke layer manapun).

Jalankan: uv run uvicorn src.main:app --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.layers.input_layer import validate_turn_payload
from src.observability.tracing import setup_tracing

SERVICE_NAME = "nirwana-chatbot-input-layer"


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


@app.post("/v1/turns")
async def submit_turn(payload: dict) -> dict:
    validated = validate_turn_payload(payload)
    return validated.model_dump()
