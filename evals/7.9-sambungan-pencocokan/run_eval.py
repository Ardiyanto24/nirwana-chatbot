"""Jalankan 6 kejadian E01-E06 di rancangan.md, simpan payload lengkap
(request+response mentah + bukti span + status match) ke payloads/.

Mirror struktur run_eval.py evals/7.6-.../, evals/7.7-.../, evals/7.8-.../
(_TraceIdCapture, _query_jaeger_trace dengan `span_wajib_ada`) - verdict
KELULUSAN di sini berbasis STATUS match aktual (`selesai`/`perlu_eksekusi`
per atomic_intent), bukan required/forbidden phrases (pola M7.8) atau
parent_span_id (pola M7.6/M7.7) - KK M7.9 soal closed-space status yang
benar. Span `matching.evaluate`+`chat` Pencocokan dihitung sebagai
konfirmasi sekunder, diidentifikasi lewat relasi parent (chat yang parent-
nya persis span matching.evaluate), bukan lewat nama tracer (Jaeger API
tidak selalu mengekspos nama tracer per span secara langsung).

E03-E06 butuh seeding data "turn sebelumnya" via store_session_memory()
manual (lihat decisions.md Keputusan 6) - mensimulasikan seolah Execution
sudah pernah menyimpan hasil turn 1, karena Execution belum disambungkan
ke proses_turn(). Data yang diuji SENDIRI (atomic_intents/candidates turn
INI) tetap 100% dari pipeline nyata.

Butuh `docker compose up -d` di infra/observability/ sebelum dijalankan
(Jaeger API di localhost:16686).

Jalankan dari root repo: uv run python evals/7.9-sambungan-pencocokan/run_eval.py
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

from src.layers.context_resolution.session_memory import (
    retrieve_session_memory,
    store_session_memory,
)
from src.observability.tracing import setup_tracing
from src.orchestration.turn_pipeline import proses_turn
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
SERVICE_NAME = "nirwana-chatbot-eval-7-9"


class _TraceIdCapture(SpanProcessor):
    """Merekam trace_id span `invoke_agent` root - mirror preseden
    evals/7.6-.../evals/7.7-.../evals/7.8-.../run_eval.py."""

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
    """Query trace langsung lewat Jaeger API. Retry menunggu SEMUA
    `span_wajib_ada` muncul (Temuan Pola M7.7), bukan berhenti begitu data
    pertama tidak kosong."""
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


def _hitung_span_matching(span_structure: list[dict]) -> dict:
    """Identifikasi span Pencocokan lewat relasi PARENT (chat yang
    parent-nya persis span matching.evaluate), bukan lewat nama tracer -
    Jaeger API tidak selalu mengekspos nama tracer per span langsung."""
    matching_evaluate = [s for s in span_structure if s["operationName"] == "matching.evaluate"]
    jumlah_matching_evaluate = len(matching_evaluate)
    if not matching_evaluate:
        return {"jumlah_matching_evaluate": 0, "jumlah_chat_matching": 0}
    matching_evaluate_id = matching_evaluate[0]["spanID"]
    chat_matching = [
        s
        for s in span_structure
        if s["operationName"] == "chat" and s["parentSpanID"] == matching_evaluate_id
    ]
    return {
        "jumlah_matching_evaluate": jumlah_matching_evaluate,
        "jumlah_chat_matching": len(chat_matching),
    }


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
    }


def _seed_turn_sebelumnya(
    session_id: str,
    turn_index: int,
    teks_kebutuhan: str,
    status: StatusEksekusi,
    nilai_hasil: dict,
) -> None:
    """Suntik satu SessionMemoryPackage manual, mensimulasikan seolah
    Execution sudah pernah menghitung dan menyimpannya (Execution belum
    disambungkan ke proses_turn(), lihat decisions.md Keputusan 6)."""
    store_session_memory(
        SessionMemoryPackage(
            atomic_intent_id=str(uuid.uuid4()),
            session_id=session_id,
            turn_index=turn_index,
            teks_kebutuhan=teks_kebutuhan,
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            nilai_hasil=nilai_hasil,
            catatan_interpretasi=[],
            status=status,
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
        _query_jaeger_trace(trace_id, span_wajib_ada={"invoke_agent", "input.validate", "chat"})
        if trace_id
        else None
    )
    span_structure = _ringkas_span_jaeger(trace_data) if trace_data else []
    span_matching = _hitung_span_matching(span_structure)

    record = {
        "kejadian_id": kejadian_id,
        "deskripsi": deskripsi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "status_per_intent": [m["status"] for m in hasil_dump["matches"]],
        "trace_id": trace_id,
        "span_structure_jaeger": span_structure,
        **span_matching,
        "error": None,
    }
    return record


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.9-e01",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }
    return _jalankan_kejadian("E01", "Tarik Memory tidak dipanggil (fast-path)", raw)


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.9-e02",
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
    return _jalankan_kejadian(
        "E02", "Tarik Memory dipanggil, genuinely kosong (fast-path)", raw
    )


def run_e03() -> dict:
    _seed_turn_sebelumnya(
        "eval-7.9-e03", 1, "Berapa occupancy rate bulan April 2026?",
        StatusEksekusi.BERHASIL, {"occupancy_rate": 78},
    )
    raw = {
        "session_id": "eval-7.9-e03",
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
    return _jalankan_kejadian("E03", "Match nyata - bukti KK literal utama", raw)


def run_e04() -> dict:
    _seed_turn_sebelumnya(
        "eval-7.9-e04", 1, "Berapa occupancy rate bulan April 2026?",
        StatusEksekusi.BERHASIL, {"occupancy_rate": 78},
    )
    raw = {
        "session_id": "eval-7.9-e04",
        "turn_index": 2,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Sekarang gimana dengan revenue F&B bulan yang sama?",
        "history": [
            {
                "turn_index": 1,
                "question": "Berapa occupancy rate bulan April 2026?",
                "answer": "Occupancy April 2026 mencapai 78%.",
            }
        ],
    }
    return _jalankan_kejadian(
        "E04", "Anti false-positive - kandidat ada, topik beda, TIDAK match", raw
    )


def run_e05() -> dict:
    _seed_turn_sebelumnya(
        "eval-7.9-e05", 1, "Berapa occupancy rate bulan April 2026?",
        StatusEksekusi.GAGAL_TEKNIS, {},
    )
    raw = {
        "session_id": "eval-7.9-e05",
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
        "E05", "Kandidat ada tapi status!=berhasil - terfilter internal", raw
    )


def run_e06() -> dict:
    _seed_turn_sebelumnya(
        "eval-7.9-e06", 1, "Berapa occupancy rate bulan April 2026?",
        StatusEksekusi.BERHASIL, {"occupancy_rate": 78},
    )
    raw = {
        "session_id": "eval-7.9-e06",
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
    record = _jalankan_kejadian(
        "E06", "Majemuk campuran - granularitas per-intent (reuse pola M7.8 E01)", raw
    )
    # Konfirmasi arsip ulang: query langsung baris tersimpan turn_index=2.
    arsip_turn2 = retrieve_session_memory("eval-7.9-e06", 2)
    record["arsip_turn2_jumlah_baris"] = len(arsip_turn2)
    record["arsip_turn2"] = [p.model_dump() for p in arsip_turn2]
    return record


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _setup_tracing_dengan_capture()

    for label, runner in [
        ("E01", run_e01), ("E02", run_e02), ("E03", run_e03),
        ("E04", run_e04), ("E05", run_e05), ("E06", run_e06),
    ]:
        print(f"Menjalankan {label}...")
        record = runner()
        _simpan(record)
        print(f"  trace_id={record['trace_id']}")
        print(f"  status_per_intent={record['status_per_intent']}")
        print(
            f"  span matching.evaluate={record['jumlah_matching_evaluate']}, "
            f"chat(matching)={record['jumlah_chat_matching']}"
        )
        if "arsip_turn2_jumlah_baris" in record:
            print(f"  arsip turn2 jumlah baris={record['arsip_turn2_jumlah_baris']}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
