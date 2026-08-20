"""Jalankan 2 kejadian E01-E02 di rancangan.md, simpan payload lengkap
ke payloads/.

PERTAMA KALI eval project memanggil endpoint HTTP SUNGGUHAN (`httpx`
ke server `uvicorn` nyata di port 8001), bukan memanggil `proses_turn()`
langsung dari skrip Python seperti seluruh eval M7.6-7.16. Server app
milik proyek ini dinyalakan sebagai subprocess terlacak, dimatikan
bersih di akhir skrip (decisions.md Keputusan 8 - port 8001, hindari
bentrok `chatbot_api` di 8000).

Standar verifikasi KK1 (decisions.md Keputusan 7): kesetaraan
STRUKTURAL antara panggilan langsung proses_turn() dan panggilan lewat
HTTP, BUKAN kesamaan teks literal (non-determinisme LLM).

Butuh `docker compose up -d` di infra/observability/ (Jaeger API
localhost:16686) DAN `chatbot_api` lokal (`scripts/chatbot_api/`,
port 8000) SAMA-SAMA up - dicek di awal main(). Pantau aktif via
Jaeger selama eksekusi (preseden M7.14-7.16).

Jalankan dari root repo: uv run python evals/7.17-membangun-endpoint-api/run_eval.py
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

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

from src.observability.tracing import setup_tracing
from src.orchestration.turn_pipeline import proses_turn

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
CHATBOT_API_HEALTH = "http://127.0.0.1:8000/health"
APP_BASE_URL = "http://127.0.0.1:8001"
APP_HEALTH_URL = f"{APP_BASE_URL}/docs"
SERVICE_NAME = "nirwana-chatbot-eval-7-17"


class _TraceIdCapture(SpanProcessor):
    def __init__(self):
        self.last_trace_id: str | None = None

    def on_start(self, span, parent_context=None):
        if span.name == "invoke_agent":
            self.last_trace_id = format(span.get_span_context().trace_id, "032x")

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


_CAPTURE = _TraceIdCapture()


def _setup_tracing_dengan_capture() -> None:
    provider = setup_tracing(SERVICE_NAME)
    provider.add_span_processor(_CAPTURE)


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
    # sys.executable (BUKAN "uv run uvicorn ...") supaya Popen melacak
    # proses uvicorn LANGSUNG, bukan proses "uv" yang jadi induk terpisah
    # dari uvicorn (grandchild) - .terminate() pada wrapper "uv" TIDAK
    # menembus ke uvicorn di Windows, meninggalkan server orphan yang
    # masih menempati port (ditemukan nyata saat eksekusi Checkpoint 6).
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
    # Pengaman tambahan (Windows): pastikan seluruh pohon proses benar-benar
    # mati, bukan cuma proses induk yang dilacak Popen.
    if sys.platform == "win32":
        with suppress(Exception):
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
            )


def _query_jaeger_trace(
    trace_id: str, span_wajib_ada: set[str], percobaan: int = 15, jeda_detik: float = 3.0
) -> dict | None:
    url = f"{JAEGER_API}/{trace_id}"
    data = None
    for _ in range(percobaan):
        time.sleep(jeda_detik)
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            continue
        if not data.get("data"):
            continue
        nama_span_ditemukan = {s["operationName"] for s in data["data"][0]["spans"]}
        if span_wajib_ada.issubset(nama_span_ditemukan):
            return data
    return data


def _jalankan_langsung(raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    narasi, verifikasi, visualisasi = hasil.interpretation
    return {
        "trace_id": _CAPTURE.last_trace_id,
        "terverifikasi": verifikasi.lolos is True,
        "narasi_non_kosong": bool(narasi.narasi.strip()),
        "execution_statuses": [e.status.value for e in hasil.execution],
        "matches_statuses": [m.status.value for m in hasil.matches],
    }


def _jalankan_via_http(raw: dict) -> dict:
    # Skenario gop_margin (E02) terbukti bisa >600s (preseden M7.12 ~24.7
    # menit terburuk) - 1800s (30 menit) dipilih sebagai batas wajar,
    # bukan tanpa batas sama sekali (mencegah hang tak terbatas kalau
    # genuinely macet, docs/keterbatasan-diterima.md #7).
    with httpx.Client(timeout=1800.0) as client:
        response = client.post(f"{APP_BASE_URL}/v1/turns", json=raw)
    body = None
    try:
        body = response.json()
    except ValueError:
        body = {"_raw_text": response.text}
    return {
        "status_code": response.status_code,
        "body": body,
    }


def run_e01() -> dict:
    raw_direct = {
        "session_id": "eval-7.17-e01-direct",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }
    raw_http = {**raw_direct, "session_id": "eval-7.17-e01-http"}

    print("E01: panggilan langsung proses_turn()...")
    langsung = _jalankan_langsung(raw_direct)
    print(f"  langsung: {langsung}")

    print("E01: panggilan via HTTP...")
    via_http = _jalankan_via_http(raw_http)
    print(f"  http status={via_http['status_code']}")

    return {
        "kejadian_id": "E01",
        "deskripsi": "Kebutuhan tunggal sederhana, KK1 - kesetaraan struktural langsung vs HTTP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload_direct": raw_direct,
        "raw_payload_http": raw_http,
        "hasil_langsung": langsung,
        "hasil_http": via_http,
        "error": None,
    }


def run_e02() -> dict:
    raw_http = {
        "session_id": "eval-7.17-e02-http",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }

    print("E02: panggilan via HTTP (skenario RBAC gop_margin)...")
    via_http = _jalankan_via_http(raw_http)
    print(f"  http status={via_http['status_code']}")

    return {
        "kejadian_id": "E02",
        "deskripsi": "Penolakan otorisasi Domain Gate, KK2 - reuse skenario gop_margin",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload_http": raw_http,
        "hasil_http": via_http,
        "error": None,
    }


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _cek_prasyarat()
    _setup_tracing_dengan_capture()

    app_proc = _start_app_server()
    try:
        for label, runner in [("E01", run_e01), ("E02", run_e02)]:
            print(f"Menjalankan {label}...")
            record = runner()
            _simpan(record)
        print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")
    finally:
        print("Mematikan app server...")
        _matikan_app_server(app_proc)
        print("  app server dimatikan.")


if __name__ == "__main__":
    main()
