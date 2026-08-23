# Milestone 8.7 - kontainerisasi backend FastAPI. Multi-stage mirror gaya
# custom-exporter/Dockerfile (build stage terpisah dari runtime stage
# minimal, decisions.md Keputusan 1). Base python:3.13-slim, cocok
# requires-python di pyproject.toml (Keputusan 2) - image resmi multi-arch,
# termasuk linux/arm64 (target akhir: VPS Oracle Ampere A1, Milestone 8.8).

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Layer dependency terpisah dari layer source (Keputusan 3) - cache Docker
# tidak perlu install ulang seluruh dependency kalau cuma src/ yang berubah.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev

FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"

# CMD memanggil venv Python LANGSUNG, TANPA wrapper `uv run` (Keputusan 3) -
# proses ini jadi PID 1 di container, wajib forward SIGTERM `docker stop`
# dengan benar untuk graceful shutdown (preseden bug M7.17: `uv run` tidak
# forward sinyal proses dengan benar ke child-nya).
# --host 0.0.0.0 WAJIB (bukan default 127.0.0.1) supaya bisa diakses dari
# luar container.
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
