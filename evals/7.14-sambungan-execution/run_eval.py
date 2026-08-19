"""Jalankan 3 kejadian E01-E03 di rancangan.md, simpan payload lengkap
ke payloads/.

PERTAMA KALI proses_turn() genuinely memanggil chatbot_api sungguhan lewat
pipeline otomatis penuh (bukan panggilan manual per-fungsi seperti
Checkpoint 1). Verifikasi substantif dilakukan lewat INSPEKSI LANGSUNG
return value proses_turn() (`hasil.execution[i].status`/`nilai_hasil`) -
Jaeger dipakai membuktikan URUTAN WAVE: span `orchestration.wave` untuk
wave N+1 TIDAK BOLEH mulai sebelum span `orchestration.wave` wave N
SELESAI (startTime+duration) - forced by struktur kode sekuensial murni
(bukan ThreadPoolExecutor seperti M7.7), jadi non-overlap adalah bukti
langsung urutan wave yang benar.

Butuh `docker compose up -d` di infra/observability/ (Jaeger API
localhost:16686) DAN `chatbot_api` lokal (`scripts/chatbot_api/`,
`python -m uvicorn main:app --reload`, port 8000) SAMA-SAMA up - dicek di
awal main().

PENTING (pelajaran M7.12): pantau progres AKTIF lewat query Jaeger
berkala saat eksekusi berjalan (bukan menunggu buta).

Jalankan dari root repo: uv run python evals/7.14-sambungan-execution/run_eval.py
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
CHATBOT_API_HEALTH = "http://127.0.0.1:8000/health"
SERVICE_NAME = "nirwana-chatbot-eval-7-14"


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


def _tag_value(span: dict, key: str):
    for tag in span.get("tags", []):
        if tag["key"] == key:
            return tag["value"]
    return None


def _analisis_urutan_wave(trace_data: dict | None) -> dict:
    """Verifikasi SUBSTANTIF urutan wave via timestamp span nyata - span
    `orchestration.wave` wave N+1 TIDAK BOLEH mulai (startTime) sebelum
    span wave N selesai (startTime+duration) - forced by loop sekuensial
    murni turn_pipeline.py (bukan thread paralel), jadi non-overlap
    membuktikan urutan langsung, tanpa perlu menelusuri parent chain
    execute_tool individual."""
    if not trace_data or not trace_data.get("data"):
        return {"wave_spans": [], "urutan_benar": None}

    spans = trace_data["data"][0]["spans"]
    wave_spans = [
        {
            "wave_index": _tag_value(s, "wave.index"),
            "intent_count": _tag_value(s, "wave.intent_count"),
            "start_time": s["startTime"],
            "end_time": s["startTime"] + s["duration"],
        }
        for s in spans
        if s["operationName"] == "orchestration.wave"
    ]
    wave_spans.sort(key=lambda w: w["wave_index"])

    urutan_benar = True
    for i in range(1, len(wave_spans)):
        if wave_spans[i]["start_time"] < wave_spans[i - 1]["end_time"]:
            urutan_benar = False

    return {"wave_spans": wave_spans, "urutan_benar": urutan_benar if wave_spans else None}


def _serialize_result(hasil) -> dict:
    return {
        "payload": hasil.payload.model_dump(),
        "decomposition": hasil.decomposition.model_dump(),
        "matches": [m.model_dump() for m in hasil.matches],
        "domain_gate": [d.model_dump() for d in hasil.domain_gate],
        "otorisasi": [o.model_dump() for o in hasil.otorisasi],
        "cakupan_individu": [c.model_dump() for c in hasil.cakupan_individu],
        "retriever": [r.model_dump() for r in hasil.retriever],
        "query_engine": [
            [hasil_susun.model_dump(), hasil_verifikasi.model_dump() if hasil_verifikasi else None]
            for hasil_susun, hasil_verifikasi in hasil.query_engine
        ],
        "verification_gate": [
            [atomic_intent.model_dump(), hasil_gate.model_dump()]
            for atomic_intent, hasil_gate in hasil.verification_gate
        ],
        "execution": [e.model_dump() for e in hasil.execution],
    }


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)

    laporan_execution = [
        {
            "atomic_intent_id": e.atomic_intent.atomic_intent_id,
            "teks_kebutuhan": e.atomic_intent.teks_kebutuhan,
            "status": e.status.value,
            "bug_prioritas_tinggi": e.bug_prioritas_tinggi,
            "retry_count_infra": e.retry_count_infra,
            "revisi_count": e.revisi_count,
            "kegagalan_alasan": e.kegagalan_alasan,
            "data_quality_status": e.data_quality_status,
            "nilai_hasil_ringkas": str(e.nilai_hasil)[:200] if e.nilai_hasil else None,
        }
        for e in hasil.execution
    ]

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id,
            span_wajib_ada={"invoke_agent", "input.validate"},
        )
        if trace_id
        else None
    )
    analisis_wave = _analisis_urutan_wave(trace_data)

    record = {
        "kejadian_id": kejadian_id,
        "deskripsi": deskripsi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "laporan_execution": laporan_execution,
        "trace_id": trace_id,
        "analisis_wave": analisis_wave,
        "error": None,
    }
    return record


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.14-e01",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }
    return _jalankan_kejadian(
        "E01",
        "Kebutuhan majemuk-bergantung, uji wave berulang nyata - KK literal utama (reuse gop_margin M7.9-7.13)",
        raw,
    )


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.14-e02",
        "turn_index": 1,
        "role_title": "HR Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana hasil review kinerja Budi semester ini?",
    }
    return _jalankan_kejadian(
        "E02", "Baseline 1 wave, koreksi paksa employee_id sampai chatbot_api nyata (reuse M7.13 E01)", raw
    )


def run_e03() -> dict:
    raw = {
        "session_id": "eval-7.14-e03",
        "turn_index": 1,
        "role_title": "Maintenance Staff",
        "employee_id": "emp-eval",
        "question": "Berapa banyak tiket yang ditangani teknisi Andi bulan ini?",
    }
    return _jalankan_kejadian(
        "E03", "Bukti kedua independen, domain facility (reuse M7.13 E03)", raw
    )


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _cek_prasyarat()
    _setup_tracing_dengan_capture()

    for label, runner in [("E01", run_e01), ("E02", run_e02), ("E03", run_e03)]:
        print(f"Menjalankan {label}...")
        record = runner()
        _simpan(record)
        print(f"  trace_id={record['trace_id']}")
        for laporan in record["laporan_execution"]:
            print(
                f"  intent={laporan['atomic_intent_id'][:8]} "
                f"status={laporan['status']} "
                f"bug_prioritas_tinggi={laporan['bug_prioritas_tinggi']} "
                f"kegagalan_alasan={laporan['kegagalan_alasan']}"
            )
        print(f"  analisis_wave={json.dumps(record['analisis_wave'], ensure_ascii=False)}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
