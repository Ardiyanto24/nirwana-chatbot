"""Jalankan kejadian E01/E02 di rancangan.md, simpan payload lengkap
(request+response mentah + bukti span) ke payloads/.

Mirror struktur run_eval.py evals/7.6-.../ dan evals/7.7-.../
(_TraceIdCapture, _query_jaeger_trace dengan `span_wajib_ada`,
_ringkas_span_jaeger) - tapi verdict KELULUSAN di sini BEDA dari M7.6/M7.7:
KK M7.8 murni soal KONTEN (bukan struktur span), jadi tiap kejadian
dinilai lewat required_phrases/forbidden_phrases pada gabungan
teks_kebutuhan hasil Decomposition (format evals/1.4-rewrite-mandiri/).
Bukti span tetap direkam sebagai konfirmasi sekunder (decisions.md
Keputusan 1), bukan syarat lolos.

Butuh `docker compose up -d` di infra/observability/ sebelum dijalankan
(Jaeger API di localhost:16686).

Jalankan dari root repo: uv run python evals/7.8-sambungan-rewrite-decomposition/run_eval.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

from src.observability.tracing import setup_tracing
from src.orchestration.turn_pipeline import proses_turn

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
SERVICE_NAME = "nirwana-chatbot-eval-7-8"


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
    """Query trace langsung lewat Jaeger API - bukan asumsi dari kode.
    Retry menunggu SEMUA `span_wajib_ada` muncul (Temuan Pola M7.7),
    bukan berhenti begitu data pertama tidak kosong."""
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
        "decomposition": hasil.decomposition.model_dump(),
    }


def _gabungan_teks_kebutuhan(decomposition_dump: dict) -> str:
    return " | ".join(
        item["teks_kebutuhan"] for item in decomposition_dump["atomic_intents"]
    ).lower()


def _cek_phrases(teks: str, required: list[str], forbidden: list[str]) -> dict:
    required_hasil = {p: (p.lower() in teks) for p in required}
    forbidden_hasil = {p: (p.lower() in teks) for p in forbidden}
    semua_required_ada = all(required_hasil.values())
    ada_forbidden = any(forbidden_hasil.values())
    return {
        "required_phrases_ditemukan": required_hasil,
        "forbidden_phrases_ditemukan": forbidden_hasil,
        "semua_required_ada": semua_required_ada,
        "ada_forbidden_muncul": ada_forbidden,
        "lolos_konten": semua_required_ada and not ada_forbidden,
    }


def run_e01() -> dict:
    """Kejadian E01: kasus elipsis/koreferensi (reuse skenario M1.4
    Kelompok A) - bukti KK literal M7.8 berbasis KONTEN, bukan span."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-7.8-e01",
        "turn_index": 2,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Bandingkan dengan occupancy satu tahun sebelumnya.",
        "history": [
            {
                "turn_index": 1,
                "question": "Berapa occupancy rate bulan April 2026?",
                "answer": "Occupancy April 2026 mencapai 78%.",
            }
        ],
    }
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(trace_id, span_wajib_ada={"invoke_agent", "input.validate", "chat"})
        if trace_id
        else None
    )
    span_structure = _ringkas_span_jaeger(trace_data) if trace_data else []
    span_by_name = {s["operationName"]: s for s in span_structure}
    invoke_agent_span = span_by_name.get("invoke_agent")
    invoke_agent_id = invoke_agent_span["spanID"] if invoke_agent_span else None
    chat_span_ids = [s["spanID"] for s in span_structure if s["operationName"] == "chat"]
    chat_parents = [s["parentSpanID"] for s in span_structure if s["operationName"] == "chat"]
    semua_chat_anak_invoke_agent = bool(chat_span_ids) and all(
        p == invoke_agent_id for p in chat_parents
    )

    teks = _gabungan_teks_kebutuhan(hasil_dump["decomposition"])
    cek_konten = _cek_phrases(teks, required=["april", "2025"], forbidden=["satu tahun sebelumnya", "2026"])

    record = {
        "kejadian_id": "E01",
        "deskripsi": "Kasus elipsis/koreferensi - bukti KK literal M7.8 (konten)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "teks_kebutuhan_gabungan": teks,
        "cek_konten": cek_konten,
        "trace_id": trace_id,
        "span_structure_jaeger": span_structure,
        "jumlah_span_chat_ditemukan": len(chat_span_ids),
        "semua_span_chat_anak_invoke_agent": semua_chat_anak_invoke_agent,
        "error": None,
    }
    return record


def run_e02() -> dict:
    """Kejadian E02: kasus sudah mandiri (reuse skenario M1.4 Kelompok B)
    - baseline kontras terhadap E01."""
    _CAPTURE.last_trace_id = None
    raw = {
        "session_id": "eval-7.8-e02",
        "turn_index": 1,
        "role_title": "Corporate Revenue Director",
        "employee_id": "emp-eval",
        "question": "Berapa revenue reservasi bulan Maret 2026?",
    }
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(trace_id, span_wajib_ada={"invoke_agent", "input.validate", "chat"})
        if trace_id
        else None
    )
    span_structure = _ringkas_span_jaeger(trace_data) if trace_data else []
    span_by_name = {s["operationName"]: s for s in span_structure}
    invoke_agent_span = span_by_name.get("invoke_agent")
    invoke_agent_id = invoke_agent_span["spanID"] if invoke_agent_span else None
    chat_span_ids = [s["spanID"] for s in span_structure if s["operationName"] == "chat"]
    chat_parents = [s["parentSpanID"] for s in span_structure if s["operationName"] == "chat"]
    semua_chat_anak_invoke_agent = bool(chat_span_ids) and all(
        p == invoke_agent_id for p in chat_parents
    )

    teks = _gabungan_teks_kebutuhan(hasil_dump["decomposition"])
    cek_konten = _cek_phrases(teks, required=["reservasi", "maret", "2026"], forbidden=[])

    record = {
        "kejadian_id": "E02",
        "deskripsi": "Kasus sudah mandiri - baseline kontras",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "teks_kebutuhan_gabungan": teks,
        "cek_konten": cek_konten,
        "trace_id": trace_id,
        "span_structure_jaeger": span_structure,
        "jumlah_span_chat_ditemukan": len(chat_span_ids),
        "semua_span_chat_anak_invoke_agent": semua_chat_anak_invoke_agent,
        "error": None,
    }
    return record


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _setup_tracing_dengan_capture()

    print("Menjalankan E01 (elipsis/koreferensi)...")
    e01 = run_e01()
    _simpan(e01)
    print(f"  trace_id={e01['trace_id']}")
    print(f"  rewritten_question={e01['hasil']['rewrite']['rewritten_question']!r}")
    print(f"  teks_kebutuhan_gabungan={e01['teks_kebutuhan_gabungan']!r}")
    print(f"  LOLOS KONTEN: {e01['cek_konten']['lolos_konten']}")
    print(f"  jumlah span chat: {e01['jumlah_span_chat_ditemukan']}, semua anak invoke_agent: {e01['semua_span_chat_anak_invoke_agent']}")

    print("Menjalankan E02 (sudah mandiri, baseline)...")
    e02 = run_e02()
    _simpan(e02)
    print(f"  trace_id={e02['trace_id']}")
    print(f"  rewritten_question={e02['hasil']['rewrite']['rewritten_question']!r}")
    print(f"  teks_kebutuhan_gabungan={e02['teks_kebutuhan_gabungan']!r}")
    print(f"  LOLOS KONTEN: {e02['cek_konten']['lolos_konten']}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
