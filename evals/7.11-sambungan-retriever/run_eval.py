"""Jalankan 4 kejadian E01-E04 di rancangan.md, simpan payload lengkap
(request+response mentah + bukti span) ke payloads/.

Mirror struktur run_eval.py evals/7.6-.../ s.d. evals/7.10-.../. Beda dari
M7.10: verifikasi SUBSTANTIF "tidak ada kandidat dari domain ditolak"
dilakukan lewat INSPEKSI LANGSUNG return value proses_turn() (`hasil.
otorisasi`, `hasil.cakupan_individu`, `hasil.retriever[i].kecukupan[*].
kandidat.domain`) - BUKAN parsing tag Jaeger, karena span `retriever.
cari_kandidat_view` hanya merekam `retrieval.candidates_count` (jumlah),
TIDAK merekam domain per-kandidat individual (dikonfirmasi baca
`src/layers/retriever/retriever.py::_atribut_span_dari_hasil()` sebelum
skrip ini ditulis). Jaeger tetap dipakai untuk membuktikan span+atribut
ringkasan (`intent.count`, `retrieval.selected_view`, dst) benar-benar
ter-emit sesuai kontrak observability - bukan untuk daftar kandidat.

Seluruh 4 kejadian turn 1 tanpa histori - TIDAK butuh seeding
store_session_memory() (beda dari E01/E03 M7.10 yang butuh simulasi
turn sebelumnya).

Butuh `docker compose up -d` di infra/observability/ sebelum dijalankan
(Jaeger API di localhost:16686).

Jalankan dari root repo: uv run python evals/7.11-sambungan-retriever/run_eval.py
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
from src.schemas.domain_gate import Domain

OUTPUT_DIR = Path(__file__).resolve().parent / "payloads"
JAEGER_API = "http://localhost:16686/api/traces"
SERVICE_NAME = "nirwana-chatbot-eval-7-11"


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
    """Ambil atribut ringkasan dari span-span kunci M7.11 - intent.count
    tiap wrapping span (_semua), retrieval.candidates_count/selected_view
    per span retriever.cari_kandidat_view."""
    if not trace_data or not trace_data.get("data"):
        return {}
    spans = trace_data["data"][0]["spans"]

    hasil = {
        "domain_gate_periksa_otorisasi_semua.intent_count": None,
        "domain_gate_deteksi_constraint_semua.intent_count": None,
        "domain_gate_deteksi_constraint_semua.terdeteksi_count": None,
        "retriever_proses_semua.intent_count": None,
        "authorization_check_count": 0,
        "retriever_cari_kandidat_view": [],
    }

    for s in spans:
        nama = s["operationName"]
        if nama == "domain_gate.periksa_otorisasi_semua":
            hasil["domain_gate_periksa_otorisasi_semua.intent_count"] = _tag_value(s, "intent.count")
        elif nama == "domain_gate.deteksi_constraint_semua":
            hasil["domain_gate_deteksi_constraint_semua.intent_count"] = _tag_value(s, "intent.count")
            hasil["domain_gate_deteksi_constraint_semua.terdeteksi_count"] = _tag_value(
                s, "constraint.terdeteksi_count"
            )
        elif nama == "retriever.proses_semua":
            hasil["retriever_proses_semua.intent_count"] = _tag_value(s, "intent.count")
        elif nama == "authorization.check":
            hasil["authorization_check_count"] += 1
        elif nama == "retriever.cari_kandidat_view":
            hasil["retriever_cari_kandidat_view"].append(
                {
                    "retrieval.candidates_count": _tag_value(s, "retrieval.candidates_count"),
                    "retrieval.selected_view": _tag_value(s, "retrieval.selected_view"),
                }
            )

    return hasil


def _domain_ditolak_ke_kandidat(hasil) -> dict:
    """Verifikasi SUBSTANTIF (bukan Jaeger): untuk tiap atomic intent,
    domain mana yang DITOLAK otorisasi, dan apakah domain itu genuinely
    TIDAK muncul sebagai domain kandidat mana pun di hasil.retriever -
    inspeksi langsung `KecukupanKandidat.kandidat.domain` (return value
    Python asli, sumber kebenaran paling langsung)."""
    laporan = []
    for aic in hasil.cakupan_individu:
        domain_ditolak = {
            d.domain for d in aic.domain_decisions if not d.diizinkan
        }
        retriever_match = next(
            (
                r
                for r in hasil.retriever
                if r.atomic_intent.atomic_intent_id == aic.atomic_intent.atomic_intent_id
            ),
            None,
        )
        domain_kandidat_muncul = (
            {kk.kandidat.domain for kk in retriever_match.kecukupan}
            if retriever_match
            else set()
        )
        domain_bocor = domain_ditolak & domain_kandidat_muncul
        laporan.append(
            {
                "atomic_intent_id": aic.atomic_intent.atomic_intent_id,
                "teks_kebutuhan": aic.atomic_intent.teks_kebutuhan,
                "domain_diidentifikasi": [
                    d.domain.value for d in aic.domain_decisions
                ],
                "domain_diizinkan": [
                    d.domain.value for d in aic.domain_decisions if d.diizinkan
                ],
                "domain_ditolak": [d.value for d in domain_ditolak],
                "domain_kandidat_muncul_di_retriever": [
                    d.value for d in domain_kandidat_muncul
                ],
                "domain_bocor": [d.value for d in domain_bocor],
                "zero_leakage": len(domain_bocor) == 0,
                "view_name_final": retriever_match.view_name_final if retriever_match else None,
                "cakupan_individu_terdeteksi": aic.constraint.terdeteksi,
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
    }


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)
    laporan_zero_leakage = _domain_ditolak_ke_kandidat(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id,
            span_wajib_ada={
                "invoke_agent",
                "input.validate",
                "chat",
                "domain_gate.periksa_otorisasi_semua",
                "retriever.proses_semua",
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
        "laporan_zero_leakage": laporan_zero_leakage,
        "trace_id": trace_id,
        "span_info": span_info,
        "error": None,
    }
    return record


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.11-e01",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }
    return _jalankan_kejadian(
        "E01",
        "Multi-domain sebagian ditolak otorisasi - bukti KK literal utama (reuse gop_margin M2.1/M7.3)",
        raw,
    )


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.11-e02",
        "turn_index": 1,
        "role_title": "CEO",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan ini?",
    }
    return _jalankan_kejadian("E02", "Baseline - seluruh domain diizinkan", raw)


def run_e03() -> dict:
    raw = {
        "session_id": "eval-7.11-e03",
        "turn_index": 1,
        "role_title": "F&B Staff",
        "employee_id": "emp-eval",
        "question": "Berapa GOP (gross operating profit) properti bulan ini?",
    }
    return _jalankan_kejadian(
        "E03", "Edge case - seluruh domain satu atomic intent ditolak (domain_diizinkan kosong)", raw
    )


def run_e04() -> dict:
    raw = {
        "session_id": "eval-7.11-e04",
        "turn_index": 1,
        "role_title": "HR Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana hasil review kinerja Budi semester ini?",
    }
    return _jalankan_kejadian(
        "E04", "Bukti sambungan M2.3 - reuse skenario evals/2.3-.../S01", raw
    )


def _simpan(record: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{record['kejadian_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    _setup_tracing_dengan_capture()

    for label, runner in [("E01", run_e01), ("E02", run_e02), ("E03", run_e03), ("E04", run_e04)]:
        print(f"Menjalankan {label}...")
        record = runner()
        _simpan(record)
        print(f"  trace_id={record['trace_id']}")
        for laporan in record["laporan_zero_leakage"]:
            print(
                f"  intent={laporan['atomic_intent_id'][:8]} "
                f"domain_diidentifikasi={laporan['domain_diidentifikasi']} "
                f"domain_diizinkan={laporan['domain_diizinkan']} "
                f"domain_ditolak={laporan['domain_ditolak']} "
                f"domain_bocor={laporan['domain_bocor']} "
                f"zero_leakage={laporan['zero_leakage']} "
                f"view_name_final={laporan['view_name_final']} "
                f"cakupan_individu={laporan['cakupan_individu_terdeteksi']}"
            )
        print(f"  span_info={json.dumps(record['span_info'], ensure_ascii=False)}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
