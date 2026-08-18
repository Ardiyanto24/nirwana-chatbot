"""Jalankan kejadian E01/E02 di rancangan.md, simpan payload lengkap
(request+response mentah + bukti span) ke payloads/. E03/E04 TIDAK
dieksekusi di sini - sudah terbukti murni deterministik lewat
tests/orchestration/test_turn_pipeline.py (Checkpoint 4).

Mirror struktur run_eval.py evals/7.6-.../ persis (_TraceIdCapture,
_query_jaeger_trace, _ringkas_span_jaeger) - tapi verifikasi span E01
di sini LEBIH KETAT: bukan cuma cek span ADA, tapi cek `chat` (Rewrite)
DAN `memory.retrieve` (Tarik Memory) SAMA-SAMA py parentSpanID = span
`invoke_agent` yang SAMA - bukti literal KK M7.7 ("parent_span_id yang
sama"). Butuh `docker compose up -d` di infra/observability/ sebelum
dijalankan (Jaeger API di localhost:16686).

Jalankan dari root repo: uv run python evals/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/run_eval.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Skrip ini dijalankan langsung (bukan lewat `-c`), jadi sys.path[0] adalah
# folder skrip ini sendiri, bukan root repo - root repo ditambahkan manual
# supaya "src" bisa diimpor, sama seperti pola evals/7.6-.../run_eval.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

from src.observability.tracing import setup_tracing
from src.orchestration.turn_pipeline import proses_turn

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
SERVICE_NAME = "nirwana-chatbot-eval-7-7"


class _TraceIdCapture(SpanProcessor):
    """Merekam trace_id span `invoke_agent` root - satu-satunya cara
    mengambil trace_id dari luar (proses_turn() tidak mengembalikannya),
    tanpa mengubah kode produksi."""

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


def _query_jaeger_trace(
    trace_id: str, span_wajib_ada: set[str], percobaan: int = 8, jeda_detik: float = 2.0
) -> dict | None:
    """Query trace langsung lewat Jaeger API - bukan asumsi dari kode,
    mirror pola verifikasi milestones/2.1-identifikasi-domain/logs.md
    Checkpoint 8. BEDA dari evals/7.6-.../run_eval.py: di sini retry
    menunggu SEMUA `span_wajib_ada` benar-benar muncul, bukan berhenti
    begitu `data` pertama kali tidak kosong - ditemukan race nyata saat
    eksekusi M7.7 (Jaeger sempat mengembalikan trace dengan 3 dari 4
    span, `invoke_agent` sendiri belum terindeks, sebelum retry cukup
    lama)."""
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


def _ringkas_span_jaeger(trace_data: dict) -> list[dict]:
    """Ekstrak nama span + parent-child relationship dari respons Jaeger
    API mentah - bentuk ringkas untuk disimpan ke payload."""
    if not trace_data.get("data"):
        return []
    spans = trace_data["data"][0]["spans"]
    ringkas = []
    for s in spans:
        parent_ids = [
            ref["spanID"] for ref in s.get("references", []) if ref["refType"] == "CHILD_OF"
        ]
        ringkas.append(
            {
                "spanID": s["spanID"],
                "operationName": s["operationName"],
                "parentSpanID": parent_ids[0] if parent_ids else None,
            }
        )
    return ringkas


def _serialize_result(hasil) -> dict:
    return {
        "payload": hasil.payload.model_dump(),
        "ketergantungan": hasil.ketergantungan.model_dump(),
        "rewrite": hasil.rewrite.model_dump(),
        "session_memory": (
            [p.model_dump() for p in hasil.session_memory]
            if hasil.session_memory is not None
            else None
        ),
    }


def run_e01() -> dict:
    """Kejadian E01: turn dengan referensi terdeteksi - LLM+DB nyata,
    DIBUKTIKAN LEWAT SPAN (query Jaeger API nyata): chat (Rewrite) dan
    memory.retrieve (Tarik Memory) harus SAMA-SAMA parentSpanID =
    spanID invoke_agent - bukti paralel literal KK M7.7."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-7.7-e01",
        "turn_index": 2,
        "role_title": "Corporate Revenue Director",
        "employee_id": "emp-eval",
        "question": "Bandingkan dengan bulan sebelumnya.",
        "history": [
            {
                "turn_index": 1,
                "question": "Berapa revenue reservasi bulan Maret 2026?",
                "answer": "Revenue reservasi Maret 2026 sebesar Rp 800 juta.",
            }
        ],
    }
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id, span_wajib_ada={"invoke_agent", "input.validate", "chat", "memory.retrieve"}
        )
        if trace_id
        else None
    )
    span_structure = _ringkas_span_jaeger(trace_data) if trace_data else []

    span_by_name = {s["operationName"]: s for s in span_structure}
    invoke_agent_span = span_by_name.get("invoke_agent")
    chat_span = span_by_name.get("chat")
    memory_span = span_by_name.get("memory.retrieve")

    invoke_agent_id = invoke_agent_span["spanID"] if invoke_agent_span else None
    chat_parent_cocok = bool(chat_span) and chat_span["parentSpanID"] == invoke_agent_id
    memory_parent_cocok = bool(memory_span) and memory_span["parentSpanID"] == invoke_agent_id

    record = {
        "kejadian_id": "E01",
        "deskripsi": "Turn dengan referensi terdeteksi, kedua jalur paralel (KK literal)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": _serialize_result(hasil),
        "trace_id": trace_id,
        "span_structure_jaeger": span_structure,
        "invoke_agent_span_id": invoke_agent_id,
        "chat_parent_span_id": chat_span["parentSpanID"] if chat_span else None,
        "memory_retrieve_parent_span_id": memory_span["parentSpanID"] if memory_span else None,
        "chat_parent_cocok_invoke_agent": chat_parent_cocok,
        "memory_retrieve_parent_cocok_invoke_agent": memory_parent_cocok,
        "kedua_span_anak_dari_span_sama": chat_parent_cocok and memory_parent_cocok,
        "error": None,
    }
    return record


def run_e02() -> dict:
    """Kejadian E02: turn tanpa referensi - hanya jalur Rewrite, Tarik
    Memory sama sekali tidak terpanggil (dibuktikan span memory.retrieve
    TIDAK ADA dalam trace, bukan cuma field Python kosong)."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-7.7-e02",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(trace_id, span_wajib_ada={"invoke_agent", "input.validate", "chat"})
        if trace_id
        else None
    )
    span_structure = _ringkas_span_jaeger(trace_data) if trace_data else []
    nama_span = {s["operationName"] for s in span_structure}

    record = {
        "kejadian_id": "E02",
        "deskripsi": "Turn tanpa referensi, hanya jalur Rewrite",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": _serialize_result(hasil),
        "trace_id": trace_id,
        "span_structure_jaeger": span_structure,
        "span_chat_ditemukan": "chat" in nama_span,
        "span_memory_retrieve_ditemukan": "memory.retrieve" in nama_span,
        "error": None,
    }
    return record


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _setup_tracing_dengan_capture()

    print("Menjalankan E01 (referensi terdeteksi, kedua jalur paralel)...")
    e01 = run_e01()
    _simpan(e01)
    print(f"  trace_id={e01['trace_id']}")
    print(f"  is_dependent={e01['hasil']['ketergantungan']['is_dependent']}, "
          f"referenced_turn_index={e01['hasil']['ketergantungan']['referenced_turn_index']}")
    print(f"  chat parent cocok invoke_agent: {e01['chat_parent_cocok_invoke_agent']}")
    print(f"  memory.retrieve parent cocok invoke_agent: {e01['memory_retrieve_parent_cocok_invoke_agent']}")
    print(f"  KEDUA SPAN ANAK DARI SPAN YANG SAMA: {e01['kedua_span_anak_dari_span_sama']}")

    print("Menjalankan E02 (tanpa referensi, hanya Rewrite)...")
    e02 = run_e02()
    _simpan(e02)
    print(f"  trace_id={e02['trace_id']}")
    print(f"  session_memory={e02['hasil']['session_memory']}")
    print(f"  span chat ditemukan={e02['span_chat_ditemukan']}, "
          f"span memory.retrieve ditemukan={e02['span_memory_retrieve_ditemukan']}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
