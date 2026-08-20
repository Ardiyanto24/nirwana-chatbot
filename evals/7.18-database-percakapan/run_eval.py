"""Jalankan 1 kejadian E01 di rancangan.md, simpan payload lengkap ke
payloads/.

Adaptasi infrastruktur `evals/7.17-membangun-endpoint-api/run_eval.py`
(server app sendiri via `sys.executable -m uvicorn` langsung - VERSI
SUDAH DIPERBAIKI M7.17, BUKAN wrapper `uv run uvicorn` yang menyebabkan
proses orphan). Beda fokus: setelah panggilan HTTP selesai, query
LANGSUNG tabel `conversation_turns` (SQLModel, tidak ada fungsi
retrieve produksi - decisions.md Keputusan 6) untuk memverifikasi
baris riwayat tersimpan cocok dengan yang genuinely ditanyakan/dijawab.

Butuh `docker compose up -d` di infra/observability/ (Jaeger API
localhost:16686) DAN `chatbot_api` lokal (`scripts/chatbot_api/`, port
8000, dijalankan dengan Python GLOBAL yang py psycopg2 - BUKAN venv
nirwana-chatbot yang pakai psycopg biasa) SAMA-SAMA up - dicek di awal
main().

Jalankan dari root repo: uv run python evals/7.18-database-percakapan/run_eval.py
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sqlmodel import Session, select

from src.config.database import get_engine
from src.db.models import ConversationTurnRow

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
CHATBOT_API_HEALTH = "http://127.0.0.1:8000/health"
APP_BASE_URL = "http://127.0.0.1:8001"
APP_HEALTH_URL = f"{APP_BASE_URL}/docs"


def _cek_prasyarat() -> None:
    try:
        with urllib.request.urlopen(CHATBOT_API_HEALTH, timeout=5) as resp:
            if resp.status != 200:
                raise SystemExit(f"chatbot_api /health status {resp.status}, harus 200")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(
            f"chatbot_api TIDAK reachable di {CHATBOT_API_HEALTH} - jalankan "
            "'python -m uvicorn main:app --reload' dari nirwana-database/scripts/chatbot_api/"
        ) from exc

    try:
        with urllib.request.urlopen("http://localhost:16686/api/services", timeout=5) as resp:
            if resp.status != 200:
                raise SystemExit("Jaeger API tidak 200 - jalankan docker compose up -d")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(
            "Jaeger TIDAK reachable - jalankan 'docker compose up -d' di infra/observability/"
        ) from exc


def _start_app_server() -> subprocess.Popen:
    print("Menyalakan uvicorn src.main:app --port 8001 sebagai subprocess...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.main:app", "--port", "8001"],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(APP_HEALTH_URL, timeout=2) as resp:
                if resp.status == 200:
                    print("  app server siap.")
                    return proc
        except (urllib.error.URLError, TimeoutError):
            continue
    _matikan_app_server(proc)
    raise SystemExit(f"App server (port 8001) gagal start dalam waktu wajar ({APP_HEALTH_URL})")


def _matikan_app_server(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    if sys.platform == "win32":
        with suppress(Exception):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
            )


def _query_conversation_turns(session_id: str) -> list[dict]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(ConversationTurnRow).where(ConversationTurnRow.session_id == session_id)
        ).all()
    return [
        {
            "id": str(row.id),
            "session_id": row.session_id,
            "turn_index": row.turn_index,
            "pertanyaan": row.pertanyaan,
            "narasi": row.narasi,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.18-e01f",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }

    print("E01: panggilan via HTTP...")
    with httpx.Client(timeout=1800.0) as client:
        response = client.post(f"{APP_BASE_URL}/v1/turns", json=raw)
    body = response.json()
    print(f"  http status={response.status_code}")

    print("E01: query conversation_turns...")
    rows = _query_conversation_turns(raw["session_id"])
    print(f"  baris ditemukan: {len(rows)}")

    return {
        "kejadian_id": "E01",
        "deskripsi": "Kebutuhan tunggal sederhana, KK1 - riwayat tersimpan cocok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil_http": {"status_code": response.status_code, "body": body},
        "conversation_turns_rows": rows,
        "error": None,
    }


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _cek_prasyarat()

    app_proc = _start_app_server()
    try:
        print("Menjalankan E01...")
        record = run_e01()
        _simpan(record)
        print(f"\nPayload tersimpan di: {OUTPUT_DIR}")
    finally:
        print("Mematikan app server...")
        _matikan_app_server(app_proc)
        print("  app server dimatikan.")


if __name__ == "__main__":
    main()
