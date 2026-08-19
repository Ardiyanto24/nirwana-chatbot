"""Jalankan 3 kejadian E01-E03 di rancangan.md, simpan payload lengkap
ke payloads/.

Mirror struktur run_eval.py evals/7.11-.../ - verifikasi SUBSTANTIF
"view_name persis sama" dilakukan lewat INSPEKSI LANGSUNG return value
proses_turn() (`hasil.query_engine[i][*].request.view_name` dibandingkan
`hasil.retriever[i].view_name_final`, per atomic_intent_id) - pendekatan
yang sama seperti M7.11 (lebih andal daripada parsing tag Jaeger untuk
klaim per-item). Jaeger tetap dipakai membuktikan span `chat` (M3.4/M3.5,
tag `request.view_name`) dan span pembungkus `query_engine.susun_dan_
verifikasi_request_semua` (`intent.count`) benar-benar ter-emit.

Seluruh 3 kejadian turn 1 tanpa histori - tidak butuh seeding.

Butuh `docker compose up -d` di infra/observability/ sebelum dijalankan
(Jaeger API di localhost:16686) - kemungkinan sudah `up` dari sesi M7.11.

Jalankan dari root repo: uv run python evals/7.12-sambungan-query-engine/run_eval.py
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
SERVICE_NAME = "nirwana-chatbot-eval-7-12"


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
    trace_id: str, span_wajib_ada: set[str], percobaan: int = 10, jeda_detik: float = 2.0
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


def _ringkas_span(trace_data: dict | None) -> dict:
    """Ambil atribut ringkasan span kunci M7.12 - intent.count span
    pembungkus, dan seluruh span `chat` yang membawa tag `request.
    view_name` (M3.4 Penyusunan Request + M3.5 Verifikasi Bentuk Request,
    keduanya set tag ini - lihat penyusunan_request.py/
    verifikasi_bentuk_request.py)."""
    if not trace_data or not trace_data.get("data"):
        return {}
    spans = trace_data["data"][0]["spans"]

    hasil = {
        "query_engine_semua.intent_count": None,
        "chat_spans_dengan_request_view_name": [],
    }

    for s in spans:
        if s["operationName"] == "query_engine.susun_dan_verifikasi_request_semua":
            hasil["query_engine_semua.intent_count"] = _tag_value(s, "intent.count")
        elif s["operationName"] == "chat":
            view_name = _tag_value(s, "request.view_name")
            if view_name is not None:
                hasil["chat_spans_dengan_request_view_name"].append(
                    {
                        "request.domain": _tag_value(s, "request.domain"),
                        "request.view_name": view_name,
                    }
                )

    return hasil


def _verifikasi_view_name_konsisten(hasil) -> list[dict]:
    """Verifikasi SUBSTANTIF (bukan Jaeger): untuk tiap atomic intent hasil
    Retriever, cocokkan terhadap entri KeadaanTurn.query_engine (kalau
    ada) - view_name yang dikirim HARUS PERSIS view_name_final (lihat
    decisions.md Keputusan 5), item view_name_final=None WAJIB tidak
    py entri query_engine sama sekali (Keputusan 4)."""
    by_id_query_engine = {}
    for hasil_susun, hasil_verifikasi in hasil.query_engine:
        aid = hasil_susun.atomic_intent.atomic_intent_id
        request = (
            hasil_verifikasi.request if hasil_verifikasi is not None else hasil_susun.request
        )
        by_id_query_engine[aid] = {
            "hasil_susun_status": hasil_susun.status.value,
            "hasil_verifikasi_lolos": (
                hasil_verifikasi.lolos if hasil_verifikasi is not None else None
            ),
            "request_view_name": request.view_name if request is not None else None,
        }

    laporan = []
    for r in hasil.retriever:
        aid = r.atomic_intent.atomic_intent_id
        entri_query_engine = by_id_query_engine.get(aid)

        if r.view_name_final is None:
            laporan.append(
                {
                    "atomic_intent_id": aid,
                    "teks_kebutuhan": r.atomic_intent.teks_kebutuhan,
                    "view_name_final": None,
                    "diteruskan_ke_query_engine": entri_query_engine is not None,
                    "skip_benar": entri_query_engine is None,
                    "view_name_persis_sama": None,
                }
            )
            continue

        view_name_persis_sama = (
            entri_query_engine is not None
            and entri_query_engine["request_view_name"] == r.view_name_final
        )
        laporan.append(
            {
                "atomic_intent_id": aid,
                "teks_kebutuhan": r.atomic_intent.teks_kebutuhan,
                "view_name_final": r.view_name_final,
                "diteruskan_ke_query_engine": entri_query_engine is not None,
                "hasil_susun_status": (
                    entri_query_engine["hasil_susun_status"] if entri_query_engine else None
                ),
                "hasil_verifikasi_lolos": (
                    entri_query_engine["hasil_verifikasi_lolos"] if entri_query_engine else None
                ),
                "request_view_name": (
                    entri_query_engine["request_view_name"] if entri_query_engine else None
                ),
                "view_name_persis_sama": view_name_persis_sama,
            }
        )
    return laporan


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
    }


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)
    laporan_view_name = _verifikasi_view_name_konsisten(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id,
            span_wajib_ada={
                "invoke_agent",
                "input.validate",
                "chat",
                "query_engine.susun_dan_verifikasi_request_semua",
            },
        )
        if trace_id
        else None
    )
    span_info = _ringkas_span(trace_data)

    record = {
        "kejadian_id": kejadian_id,
        "deskripsi": deskripsi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "laporan_view_name": laporan_view_name,
        "trace_id": trace_id,
        "span_info": span_info,
        "error": None,
    }
    return record


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.12-e01",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }
    return _jalankan_kejadian(
        "E01",
        "view_name persis sama - bukti KK literal utama (reuse gop_margin M7.11 E01)",
        raw,
    )


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.12-e02",
        "turn_index": 1,
        "role_title": "F&B Staff",
        "employee_id": "emp-eval",
        "question": "Berapa GOP (gross operating profit) properti bulan ini?",
    }
    return _jalankan_kejadian(
        "E02", "Item view_name_final=None di-skip dari Query Engine (reuse M7.11 E03)", raw
    )


def run_e03() -> dict:
    raw = {
        "session_id": "eval-7.12-e03",
        "turn_index": 1,
        "role_title": "HR Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana hasil review kinerja Budi semester ini?",
    }
    return _jalankan_kejadian(
        "E03", "Bukti kedua independen + kepatuhan sumber (reuse M7.11 E04)", raw
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
        for laporan in record["laporan_view_name"]:
            print(
                f"  intent={laporan['atomic_intent_id'][:8]} "
                f"view_name_final={laporan['view_name_final']} "
                f"diteruskan_ke_query_engine={laporan['diteruskan_ke_query_engine']} "
                f"request_view_name={laporan.get('request_view_name')} "
                f"view_name_persis_sama={laporan['view_name_persis_sama']} "
                f"skip_benar={laporan.get('skip_benar')}"
            )
        print(f"  span_info={json.dumps(record['span_info'], ensure_ascii=False)}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
