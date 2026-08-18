"""Jalankan kejadian E01/E02/E04 di rancangan.md, simpan payload lengkap
(request+response/exception mentah + bukti span) ke payloads/. E03 TIDAK
dieksekusi di sini - sudah terbukti murni deterministik lewat
tests/orchestration/test_turn_pipeline.py (Checkpoint 3).

Beda dari run_eval.py evals/1.3-.../ (yang cukup memanggil _call_llm()
langsung): skrip ini memanggil setup_tracing() supaya span invoke_agent
+ chat + input.validate genuinely terekspor ke Collector->Jaeger nyata -
diperlukan untuk membuktikan E02 (Kriteria Keberhasilan literal M7.6:
"dibuktikan lewat span"). Butuh `docker compose up -d` di
infra/observability/ sebelum dijalankan (Jaeger API di localhost:16686).

Jalankan dari root repo: uv run python evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/run_eval.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

# Skrip ini dijalankan langsung (bukan lewat `-c`), jadi sys.path[0] adalah
# folder skrip ini sendiri, bukan root repo - root repo ditambahkan manual
# supaya "src" bisa diimpor, sama seperti pola infra/observability/smoke_test/
# dan evals/1.3-pemetaan-ketergantungan-turn/run_eval.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor
from openai import APIError

from src.observability.tracing import setup_tracing
from src.orchestration.turn_pipeline import proses_turn

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
SERVICE_NAME = "nirwana-chatbot-eval-7-6"


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


def _query_jaeger_trace(trace_id: str, percobaan: int = 5, jeda_detik: float = 2.0) -> dict | None:
    """Query trace langsung lewat Jaeger API - bukan asumsi dari kode,
    mirror pola verifikasi milestones/2.1-identifikasi-domain/logs.md
    Checkpoint 8. BatchSpanProcessor async, jadi di-retry dengan jeda
    supaya span sempat terekspor Collector->Jaeger."""
    url = f"{JAEGER_API}/{trace_id}"
    for _ in range(percobaan):
        time.sleep(jeda_detik)
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            continue
        if data.get("data"):
            return data
    return None


def _ringkas_span_jaeger(trace_data: dict) -> list[dict]:
    """Ekstrak nama span + parent-child relationship dari respons Jaeger
    API mentah - bentuk ringkas untuk disimpan ke payload, bukan dump
    penuh yang tidak terbaca."""
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
    }


def run_e01() -> dict:
    """Kejadian E01: payload valid, turn pertama (tanpa histori) - LLM nyata."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-e01",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()

    record = {
        "kejadian_id": "E01",
        "deskripsi": "Payload valid, turn pertama (tanpa histori)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": _serialize_result(hasil),
        "trace_id": _CAPTURE.last_trace_id,
        "error": None,
    }
    return record


def run_e02() -> dict:
    """Kejadian E02: payload valid, turn kedua dengan histori - skenario
    KK literal M7.6, LLM nyata, DIBUKTIKAN LEWAT SPAN (query Jaeger API
    nyata, bukan asumsi kode)."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-e02",
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
    trace_data = _query_jaeger_trace(trace_id) if trace_id else None
    span_structure = _ringkas_span_jaeger(trace_data) if trace_data else []
    nama_span = {s["operationName"] for s in span_structure}

    record = {
        "kejadian_id": "E02",
        "deskripsi": "Payload valid, turn kedua dengan histori (skenario KK literal M7.6)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": _serialize_result(hasil),
        "trace_id": trace_id,
        "span_structure_jaeger": span_structure,
        "span_invoke_agent_ditemukan": "invoke_agent" in nama_span,
        "span_input_validate_ditemukan": "input.validate" in nama_span,
        "span_chat_ditemukan": "chat" in nama_span,
        "error": None,
    }
    return record


def run_e04() -> dict:
    """Kejadian E04: kegagalan teknis LLM (openai.APIError) saat
    Pemetaan Ketergantungan - _call_llm DIPAKSA raise, di-scope ketat
    lewat context manager patch (bukan monkeypatch permanen). Payload
    sama seperti E02 (lolos Input Layer, tinggal ketergantungan yang
    gagal teknis)."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-e04",
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

    exception_tertangkap = None
    with patch(
        "src.layers.context_resolution.turn_dependency._call_llm",
        side_effect=APIError("simulasi kegagalan API - kejadian E04", request=None, body=None),
    ):
        try:
            proses_turn(raw)
        except APIError as exc:
            exception_tertangkap = str(exc)

    trace.get_tracer_provider().force_flush()

    record = {
        "kejadian_id": "E04",
        "deskripsi": "Kegagalan teknis LLM (openai.APIError) saat Pemetaan Ketergantungan",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": None,
        "trace_id": _CAPTURE.last_trace_id,
        "error": exception_tertangkap,
        "menjalar_tanpa_ditangkap": exception_tertangkap is not None,
    }
    return record


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _setup_tracing_dengan_capture()

    print("Menjalankan E01 (turn pertama, tanpa histori)...")
    e01 = run_e01()
    _simpan(e01)
    print(f"  trace_id={e01['trace_id']}")

    print("Menjalankan E02 (turn kedua, histori - skenario KK literal M7.6)...")
    e02 = run_e02()
    _simpan(e02)
    print(f"  trace_id={e02['trace_id']}")
    print(f"  is_dependent={e02['hasil']['ketergantungan']['is_dependent']}, "
          f"referenced_turn_index={e02['hasil']['ketergantungan']['referenced_turn_index']}")
    print(f"  span invoke_agent ditemukan={e02['span_invoke_agent_ditemukan']}, "
          f"input.validate={e02['span_input_validate_ditemukan']}, "
          f"chat={e02['span_chat_ditemukan']}")

    print("Menjalankan E04 (kegagalan teknis LLM dipaksa)...")
    e04 = run_e04()
    _simpan(e04)
    print(f"  APIError menjalar tanpa ditangkap: {e04['menjalar_tanpa_ditangkap']}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
