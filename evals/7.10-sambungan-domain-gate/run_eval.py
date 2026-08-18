"""Jalankan 3 kejadian E01-E03 di rancangan.md, simpan payload lengkap
(request+response mentah + bukti span `intent.count`) ke payloads/.

Mirror struktur run_eval.py evals/7.6-.../ s.d. evals/7.9-.../ - verdict
KELULUSAN di sini berbasis atribut span `intent.count` LANGSUNG (span
`domain_gate.identifikasi_semua`, tracer `domain_gate.domain_gate`) -
atribut ini sudah disediakan kode M2.1 sendiri, tidak perlu teknik hitung
child-span lewat relasi parent seperti evals/7.9-.../.

E01/E03 butuh seeding data "turn sebelumnya" via store_session_memory()
manual (lihat decisions.md Keputusan 6) - mensimulasikan seolah Execution
sudah pernah menyimpan hasil turn 1.

Butuh `docker compose up -d` di infra/observability/ sebelum dijalankan
(Jaeger API di localhost:16686).

Jalankan dari root repo: uv run python evals/7.10-sambungan-domain-gate/run_eval.py
"""

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

from src.layers.context_resolution.session_memory import store_session_memory
from src.observability.tracing import setup_tracing
from src.orchestration.turn_pipeline import proses_turn
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
SERVICE_NAME = "nirwana-chatbot-eval-7-10"


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


def _query_jaeger_trace(
    trace_id: str, span_wajib_ada: set[str], percobaan: int = 8, jeda_detik: float = 2.0
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


def _cari_intent_count(trace_data: dict) -> dict:
    """Cari span `domain_gate.identifikasi_semua`, ambil atribut `intent.count`
    LANGSUNG - lebih sederhana dari teknik hitung child-span M7.9 karena
    atributnya sudah disediakan kode M2.1 sendiri."""
    if not trace_data.get("data"):
        return {"span_ditemukan": False, "intent_count": None}
    spans = trace_data["data"][0]["spans"]
    for s in spans:
        if s["operationName"] != "domain_gate.identifikasi_semua":
            continue
        for tag in s.get("tags", []):
            if tag["key"] == "intent.count":
                return {"span_ditemukan": True, "intent_count": tag["value"]}
        return {"span_ditemukan": True, "intent_count": None}
    return {"span_ditemukan": False, "intent_count": None}


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
        "matches": [m.model_dump() for m in hasil.matches],
        "domain_gate": [d.model_dump() for d in hasil.domain_gate],
    }


def _seed_turn_sebelumnya(
    session_id: str, turn_index: int, teks_kebutuhan: str, nilai_hasil: dict
) -> None:
    store_session_memory(
        SessionMemoryPackage(
            atomic_intent_id=str(uuid.uuid4()),
            session_id=session_id,
            turn_index=turn_index,
            teks_kebutuhan=teks_kebutuhan,
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            nilai_hasil=nilai_hasil,
            catatan_interpretasi=[],
            status=StatusEksekusi.BERHASIL,
            sumber="eksekusi_baru",
        )
    )


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id, span_wajib_ada={"invoke_agent", "input.validate", "chat"}
        )
        if trace_id
        else None
    )
    intent_count_info = _cari_intent_count(trace_data) if trace_data else {
        "span_ditemukan": False, "intent_count": None
    }

    record = {
        "kejadian_id": kejadian_id,
        "deskripsi": deskripsi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "jumlah_matches": len(hasil_dump["matches"]),
        "jumlah_domain_gate": len(hasil_dump["domain_gate"]),
        "trace_id": trace_id,
        "domain_gate_span_ditemukan": intent_count_info["span_ditemukan"],
        "intent_count_dari_span": intent_count_info["intent_count"],
        "error": None,
    }
    return record


def run_e01() -> dict:
    _seed_turn_sebelumnya(
        "eval-7.10-e01", 1, "Berapa occupancy rate bulan April 2026?", {"occupancy_rate": 78}
    )
    raw = {
        "session_id": "eval-7.10-e01",
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
    return _jalankan_kejadian(
        "E01", "Campuran dua status - bukti KK literal utama (reuse M7.9 E06)", raw
    )


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.10-e02",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }
    return _jalankan_kejadian("E02", "Seluruh match perlu_eksekusi", raw)


def run_e03() -> dict:
    _seed_turn_sebelumnya(
        "eval-7.10-e03", 1, "Berapa occupancy rate bulan April 2026?", {"occupancy_rate": 78}
    )
    raw = {
        "session_id": "eval-7.10-e03",
        "turn_index": 2,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa lagi occupancy April 2026 itu?",
        "history": [
            {
                "turn_index": 1,
                "question": "Berapa occupancy rate bulan April 2026?",
                "answer": "Occupancy April 2026 mencapai 78%.",
            }
        ],
    }
    return _jalankan_kejadian(
        "E03", "Seluruh match selesai - semua ditahan, TIDAK diteruskan", raw
    )


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _setup_tracing_dengan_capture()

    for label, runner in [("E01", run_e01), ("E02", run_e02), ("E03", run_e03)]:
        print(f"Menjalankan {label}...")
        record = runner()
        _simpan(record)
        print(f"  trace_id={record['trace_id']}")
        print(
            f"  jumlah_matches={record['jumlah_matches']}, "
            f"jumlah_domain_gate={record['jumlah_domain_gate']}"
        )
        print(
            f"  span domain_gate.identifikasi_semua ditemukan="
            f"{record['domain_gate_span_ditemukan']}, "
            f"intent.count={record['intent_count_dari_span']}"
        )

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
