"""Jalankan 3 kejadian E01-E03 di rancangan.md, simpan payload lengkap
ke payloads/.

Mirror struktur run_eval.py evals/7.12-.../ - verifikasi SUBSTANTIF
"koreksi paksa employee_id benar" dilakukan lewat INSPEKSI LANGSUNG
return value proses_turn() (`hasil.verification_gate[i][1].terkoreksi`/
`.request_final.params["employee_id"]` dibandingkan `hasil.cakupan_
individu[i].constraint.terdeteksi`/`payload.employee_id`, per
atomic_intent_id) - pendekatan yang sama seperti M7.11/M7.12 (lebih
andal daripada parsing tag Jaeger untuk klaim per-item). Jaeger tetap
dipakai membuktikan span `verification_gate.check`
(verification.check_name="constraint_cakupan_individu",
verification.terkoreksi) dan span pembungkus `verification_gate.
verifikasi_gate_semua` (`intent.count`) benar-benar ter-emit.

Seluruh 3 kejadian turn 1 tanpa histori - tidak butuh seeding.

Butuh `docker compose up -d` di infra/observability/ sebelum dijalankan
(Jaeger API di localhost:16686) - kemungkinan sudah `up` dari sesi
sebelumnya.

PENTING (pelajaran M7.12): pantau progres AKTIF lewat query Jaeger
berkala saat eksekusi berjalan (bukan menunggu buta) - kalau gap
antar-span > ~5 menit tanpa progres, hentikan proses dan jalankan ulang
(tidak ada payload tersimpan sebelum satu runner() selesai, aman untuk
restart).

Jalankan dari root repo: uv run python evals/7.13-sambungan-verification-gate/run_eval.py
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
SERVICE_NAME = "nirwana-chatbot-eval-7-13"


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
    """Ambil atribut ringkasan span kunci M7.13 - intent.count span
    pembungkus, dan seluruh span `verification_gate.check` yang tag
    check_name="constraint_cakupan_individu" (Cek 3 M2.4 - satu-satunya
    cek yang mengekspos verification.terkoreksi, lihat
    verifikasi_gate.py baris 138-143)."""
    if not trace_data or not trace_data.get("data"):
        return {}
    spans = trace_data["data"][0]["spans"]

    hasil = {
        "verification_gate_semua.intent_count": None,
        "constraint_check_spans": [],
    }

    for s in spans:
        if s["operationName"] == "verification_gate.verifikasi_gate_semua":
            hasil["verification_gate_semua.intent_count"] = _tag_value(s, "intent.count")
        elif s["operationName"] == "verification_gate.check":
            check_name = _tag_value(s, "verification.check_name")
            if check_name == "constraint_cakupan_individu":
                hasil["constraint_check_spans"].append(
                    {"verification.terkoreksi": _tag_value(s, "verification.terkoreksi")}
                )

    return hasil


def _verifikasi_koreksi_konsisten(hasil) -> list[dict]:
    """Verifikasi SUBSTANTIF (bukan Jaeger): untuk tiap item yang
    mencapai Verification Gate, cocokkan constraint yang DIPAKAI
    terhadap KeadaanTurn.cakupan_individu (Domain Gate sungguhan run
    ini, bukan dicatat manual - syarat eksplisit KK M7.13), dan cek
    invarian koreksi paksa: terdeteksi=True -> request_final.params
    ["employee_id"] == payload.employee_id; terdeteksi=False ->
    terkoreksi=False dan params tidak berubah dari request Query
    Engine asli."""
    constraint_by_id = {c.atomic_intent.atomic_intent_id: c.constraint for c in hasil.cakupan_individu}
    request_asli_by_id = {}
    for hasil_susun, hasil_verifikasi in hasil.query_engine:
        if hasil_verifikasi is not None and hasil_verifikasi.lolos:
            request_asli_by_id[hasil_susun.atomic_intent.atomic_intent_id] = hasil_verifikasi.request

    laporan = []
    for atomic_intent, hasil_gate in hasil.verification_gate:
        aid = atomic_intent.atomic_intent_id
        constraint = constraint_by_id.get(aid)
        request_asli = request_asli_by_id.get(aid)
        params_final = (
            hasil_gate.request_final.params if hasil_gate.request_final is not None else None
        )

        if constraint is None:
            laporan.append(
                {
                    "atomic_intent_id": aid,
                    "teks_kebutuhan": atomic_intent.teks_kebutuhan,
                    "error": "constraint tidak ditemukan di cakupan_individu_result",
                }
            )
            continue

        if constraint.terdeteksi:
            koreksi_benar = (
                hasil_gate.lolos
                and params_final is not None
                and params_final.get("employee_id") == hasil.payload.employee_id
            )
        else:
            koreksi_benar = (
                hasil_gate.terkoreksi is False
                and (params_final is None or params_final == (request_asli.params if request_asli else None))
            )

        laporan.append(
            {
                "atomic_intent_id": aid,
                "teks_kebutuhan": atomic_intent.teks_kebutuhan,
                "constraint_terdeteksi": constraint.terdeteksi,
                "hasil_gate_lolos": hasil_gate.lolos,
                "terkoreksi": hasil_gate.terkoreksi,
                "params_asli": request_asli.params if request_asli else None,
                "params_final": params_final,
                "payload_employee_id": hasil.payload.employee_id,
                "koreksi_benar": koreksi_benar,
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
        "verification_gate": [
            [atomic_intent.model_dump(), hasil_gate.model_dump()]
            for atomic_intent, hasil_gate in hasil.verification_gate
        ],
    }


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)
    laporan_koreksi = _verifikasi_koreksi_konsisten(hasil)

    trace_id = _CAPTURE.last_trace_id
    trace_data = (
        _query_jaeger_trace(
            trace_id,
            span_wajib_ada={
                "invoke_agent",
                "input.validate",
                "verification_gate.verifikasi_gate_semua",
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
        "laporan_koreksi": laporan_koreksi,
        "trace_id": trace_id,
        "span_info": span_info,
        "error": None,
    }
    return record


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.13-e01",
        "turn_index": 1,
        "role_title": "HR Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana hasil review kinerja Budi semester ini?",
    }
    return _jalankan_kejadian(
        "E01",
        "Koreksi paksa employee_id - bukti KK literal utama (reuse S01/M7.11 E04/M7.12 E03)",
        raw,
    )


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.13-e02",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }
    return _jalankan_kejadian(
        "E02", "Baseline tanpa constraint (reuse gop_margin M7.11 E01/M7.12 E01)", raw
    )


def run_e03() -> dict:
    raw = {
        "session_id": "eval-7.13-e03",
        "turn_index": 1,
        "role_title": "Maintenance Staff",
        "employee_id": "emp-eval",
        "question": "Berapa banyak tiket yang ditangani teknisi Andi bulan ini?",
    }
    return _jalankan_kejadian(
        "E03", "Bukti kedua independen, domain facility (reuse evals/2.3-.../S02)", raw
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
        for laporan in record["laporan_koreksi"]:
            print(
                f"  intent={laporan['atomic_intent_id'][:8]} "
                f"constraint_terdeteksi={laporan.get('constraint_terdeteksi')} "
                f"terkoreksi={laporan.get('terkoreksi')} "
                f"params_final={laporan.get('params_final')} "
                f"koreksi_benar={laporan.get('koreksi_benar')}"
            )
        print(f"  span_info={json.dumps(record['span_info'], ensure_ascii=False)}")

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
