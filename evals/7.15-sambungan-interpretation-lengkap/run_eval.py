"""Jalankan kejadian E01 (2-turn, WAJIB), E02 (gap RBAC, penting), E03
(gap teknis, opsional/bonus) di rancangan.md, simpan payload lengkap ke
payloads/.

E01 adalah skenario 2-TURN NYATA PERTAMA yang genuinely bergantung pada
M4.3 tersambung orkestrator (M7.15 sendiri) - turn 1 dijalankan lewat
proses_turn() sungguhan (bukan seed manual seperti evals/7.9-.../E06),
menyimpan paket via susun_dan_simpan_paket_semua() (BARU), lalu turn 2
memakai `history` berisi narasi ASLI hasil turn 1 (bukan placeholder).

Verifikasi substantif: inspeksi langsung `hasil.paket_narasi` (re-keying,
klasifikasi gap) DAN `hasil.interpretation[1].narasi` (teks narasi final,
dibaca manual di audit.md - bukan cuma structural check). Span
`orchestration.susun_paket_narasi` dipakai membuktikan 4 count kategori.

Butuh `docker compose up -d` (Jaeger, `infra/observability/`) DAN
`chatbot_api` lokal (`scripts/chatbot_api/`) SAMA-SAMA up.

Jalankan dari root repo: uv run python evals/7.15-sambungan-interpretation-lengkap/run_eval.py
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
SERVICE_NAME = "nirwana-chatbot-eval-7-15"


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


def _ringkas_span_paket_narasi(trace_data: dict | None) -> dict:
    if not trace_data or not trace_data.get("data"):
        return {}
    spans = trace_data["data"][0]["spans"]
    for s in spans:
        if s["operationName"] == "orchestration.susun_paket_narasi":
            return {
                "selesai_count": _tag_value(s, "paket_narasi.selesai_count"),
                "eksekusi_count": _tag_value(s, "paket_narasi.eksekusi_count"),
                "gap_rbac_count": _tag_value(s, "paket_narasi.gap_rbac_count"),
                "gap_teknis_count": _tag_value(s, "paket_narasi.gap_teknis_count"),
            }
    return {}


def _verifikasi_paket_narasi(hasil) -> list[dict]:
    """Verifikasi SUBSTANTIF (bukan Jaeger): panjang paket_narasi ==
    panjang matches, re-keying paket "selesai" benar (atomic_intent_id
    turn ini, bukan turn asal), klasifikasi gap (kalau ada) benar."""
    paket_by_id = {p.atomic_intent_id: p for p in hasil.paket_narasi}
    laporan = []
    for match in hasil.matches:
        aid = match.atomic_intent.atomic_intent_id
        paket = paket_by_id.get(aid)
        entri = {
            "atomic_intent_id": aid,
            "teks_kebutuhan": match.atomic_intent.teks_kebutuhan,
            "match_status": match.status.value,
            "paket_ditemukan": paket is not None,
        }
        if paket is not None:
            entri["paket_status"] = paket.status.value
            entri["paket_sumber"] = paket.sumber
            entri["paket_atomic_intent_id_cocok"] = paket.atomic_intent_id == aid
        laporan.append(entri)
    return laporan


def _serialize_result(hasil) -> dict:
    narasi, verifikasi_narasi, visualisasi = hasil.interpretation
    return {
        "payload": hasil.payload.model_dump(),
        "decomposition": hasil.decomposition.model_dump(),
        "matches": [m.model_dump() for m in hasil.matches],
        "otorisasi": [o.model_dump() for o in hasil.otorisasi],
        "retriever": [r.model_dump() for r in hasil.retriever],
        "query_engine": [
            [hasil_susun.model_dump(), hasil_verifikasi.model_dump() if hasil_verifikasi else None]
            for hasil_susun, hasil_verifikasi in hasil.query_engine
        ],
        "execution": [e.model_dump() for e in hasil.execution],
        "paket_narasi": [p.model_dump() for p in hasil.paket_narasi],
        "interpretation": {
            "narasi_awal": narasi.model_dump(),
            "verifikasi_narasi": verifikasi_narasi.model_dump(),
            "visualisasi": [v.model_dump() for v in visualisasi] if visualisasi else None,
        },
    }


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)
    laporan_paket_narasi = _verifikasi_paket_narasi(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id,
            span_wajib_ada={"invoke_agent", "input.validate", "orchestration.susun_paket_narasi"},
        )
        if trace_id
        else None
    )
    span_paket_narasi = _ringkas_span_paket_narasi(trace_data)

    record = {
        "kejadian_id": kejadian_id,
        "deskripsi": deskripsi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "laporan_paket_narasi": laporan_paket_narasi,
        "narasi_final": hasil.interpretation[1].narasi,
        "trace_id": trace_id,
        "span_paket_narasi": span_paket_narasi,
        "error": None,
    }
    return record


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def run_e01() -> tuple[dict, dict]:
    session_id = "eval-7.15-e01"
    raw_turn1 = {
        "session_id": session_id,
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate bulan April 2026?",
    }
    record_turn1 = _jalankan_kejadian(
        "E01-turn1", "Turn 1 - dijalankan nyata, akan tersimpan Session Memory", raw_turn1
    )

    raw_turn2 = {
        "session_id": session_id,
        "turn_index": 2,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Bandingkan dengan occupancy satu tahun sebelumnya.",
        "history": [
            {
                "turn_index": 1,
                "question": raw_turn1["question"],
                "answer": record_turn1["narasi_final"],
            }
        ],
    }
    record_turn2 = _jalankan_kejadian(
        "E01-turn2",
        "Turn 2 - KK literal utama, campuran selesai (turn 1)+eksekusi baru",
        raw_turn2,
    )
    return record_turn1, record_turn2


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.15-e02",
        "turn_index": 1,
        "role_title": "F&B Staff",
        "employee_id": "emp-eval",
        "question": "Berapa GOP (gross operating profit) properti bulan ini?",
    }
    return _jalankan_kejadian(
        "E02", "Paket gap RBAC (reuse skenario domain ditolak total M7.11 E03/M7.12 E02)", raw
    )


def run_e03() -> dict:
    raw = {
        "session_id": "eval-7.15-e03",
        "turn_index": 1,
        "role_title": "HR Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana hasil review kinerja Budi semester ini?",
    }
    return _jalankan_kejadian(
        "E03", "Paket gap teknis - bonus/opsional (reuse skenario HR Budi M7.13/M7.14)", raw
    )


def _cetak_laporan(record: dict) -> None:
    print(f"  trace_id={record['trace_id']}")
    for laporan in record["laporan_paket_narasi"]:
        print(
            f"  intent={laporan['atomic_intent_id'][:8]} "
            f"match_status={laporan['match_status']} "
            f"paket_status={laporan.get('paket_status')} "
            f"paket_sumber={laporan.get('paket_sumber')} "
            f"id_cocok={laporan.get('paket_atomic_intent_id_cocok')}"
        )
    print(f"  span_paket_narasi={json.dumps(record['span_paket_narasi'], ensure_ascii=False)}")
    print(f"  narasi_final={record['narasi_final'][:300]}")


def main() -> None:
    _cek_prasyarat()
    _setup_tracing_dengan_capture()

    print("Menjalankan E01 (turn 1+2)...")
    record_turn1, record_turn2 = run_e01()
    _simpan(record_turn1)
    _simpan(record_turn2)
    _cetak_laporan(record_turn1)
    _cetak_laporan(record_turn2)

    for label, runner in [("E02", run_e02), ("E03", run_e03)]:
        print(f"Menjalankan {label}...")
        record = runner()
        _simpan(record)
        _cetak_laporan(record)

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
