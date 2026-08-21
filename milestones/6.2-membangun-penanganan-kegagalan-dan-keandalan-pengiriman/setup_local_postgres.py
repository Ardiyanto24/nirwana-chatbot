"""Skrip sekali-jalan: siapkan Postgres LOKAL disposable (docker run,
BUKAN Supabase asli) untuk fault-injection test KK1 M6.2 - decisions.md
Keputusan 2. Container ini didedikasikan murni untuk mensimulasikan
"Supabase tidak terjangkau" (docker stop/start) TANPA pernah menyentuh
Supabase produksi.

Skema `traces`/`spans` dibuat lewat `SQLModel.metadata.create_all()`
(reuse src/db/models.py TraceRow/SpanRow - Bagian 4 rancangan-observability-
ai-chatbot.md) via engine TERPISAH mengarah ke Postgres lokal ini, BUKAN
`get_engine()`/`DATABASE_URL` project (Keputusan 6: superuser default
image resmi, bukan role write-only nirwana_exporter_writer - kredensial
ini murni test-only, tidak pernah disimpan permanen).

Jalankan dari root repo: uv run python milestones/6.2-.../setup_local_postgres.py
Untuk membongkar container setelah selesai: docker rm -f nirwana-m62-fault-postgres
"""

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import SQLModel, create_engine

from src.db.models import SpanRow, TraceRow

CONTAINER_NAME = "nirwana-m62-fault-postgres"
HOST_PORT = 5433
POSTGRES_PASSWORD = "m62-fault-injection-local-only"
POSTGRES_DB = "faultinjection"


def _container_running() -> bool:
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
        capture_output=True, text=True, check=True,
    )
    return CONTAINER_NAME in result.stdout


def _start_container() -> None:
    if _container_running():
        print(f"Container {CONTAINER_NAME} sudah jalan, reuse.")
        return

    # Buang container lama (kalau ada, exited) - fresh start tiap kali
    # skrip ini dijalankan, supaya skema/state tidak basi antar sesi test.
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

    print(f"Menjalankan {CONTAINER_NAME} (postgres:16, port {HOST_PORT})...")
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-e", f"POSTGRES_PASSWORD={POSTGRES_PASSWORD}",
            "-e", f"POSTGRES_DB={POSTGRES_DB}",
            "-p", f"{HOST_PORT}:5432",
            "postgres:16",
        ],
        check=True,
    )


def _wait_ready(timeout_s: int = 30) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "pg_isready", "-U", "postgres"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("Postgres lokal siap.")
            return
        time.sleep(1)
    raise RuntimeError(f"Postgres lokal tidak siap dalam {timeout_s} detik.")


def main() -> None:
    _start_container()
    _wait_ready()

    dsn_sqlalchemy = (
        f"postgresql+psycopg://postgres:{POSTGRES_PASSWORD}@localhost:{HOST_PORT}/{POSTGRES_DB}"
    )
    dsn_plain = f"postgres://postgres:{POSTGRES_PASSWORD}@localhost:{HOST_PORT}/{POSTGRES_DB}"

    engine = create_engine(dsn_sqlalchemy)
    # HANYA traces/spans (bukan SQLModel.metadata.create_all() polos yang
    # akan membuat SELURUH tabel project - session_memory_packages, roles,
    # dst - tidak relevan untuk fault-injection test exporter Go ini).
    SQLModel.metadata.create_all(engine, tables=[TraceRow.__table__, SpanRow.__table__])
    print("Tabel traces/spans dibuat di Postgres lokal.")

    print()
    print("=== DSN siap pakai ===")
    print(f"Untuk SUPABASE_EXPORTER_DSN (exporter Go, format pgx):")
    print(f"  {dsn_plain}")
    print()
    print("Simulasi outage:  docker stop", CONTAINER_NAME)
    print("Simulasi pulih:   docker start", CONTAINER_NAME)
    print("Bongkar:          docker rm -f", CONTAINER_NAME)


if __name__ == "__main__":
    main()
