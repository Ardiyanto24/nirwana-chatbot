"""Jalankan 3 kejadian E01-E03 di rancangan.md, simpan payload lengkap
ke payloads/.

Diadaptasi dari evals/7.14-sambungan-execution/run_eval.py
(decisions.md Keputusan 6) - beda fokus verifikasi: bukan urutan wave
(sudah dibuktikan M7.14), melainkan CAKUPAN SPAN 9 LAYER per skenario
(_analisis_cakupan_span di bawah), plus _serialize_result() diperluas
mencakup seluruh 15 field KeadaanTurn (M7.14 berhenti di `execution`,
sebelum paket_narasi/interpretation ditambah M7.15).

Teknik atribusi span "chat" (dipakai TIGA layer berbeda dengan nama
IDENTIK dan parent LANGSUNG invoke_agent - Ketergantungan+Rewrite,
Decomposition, Interpretation - tidak seperti layer lain yang py span
pembungkus unik): dibedakan lewat WINDOW WAKTU dibatasi span unik yang
forced oleh urutan sekuensial turn_pipeline.py (Ketergantungan+Rewrite+
Decomposition SELALU sebelum domain_gate.identifikasi_semua dimulai;
Interpretation SELALU setelah orchestration.susun_paket_narasi selesai,
karena itu langkah TERAKHIR) - bukan tebakan, forced by struktur kode
yang genuinely sekuensial (mirror preseden M7.14 memakai timestamp span
untuk membuktikan urutan wave).

Butuh `docker compose up -d` di infra/observability/ (Jaeger API
localhost:16686) DAN `chatbot_api` lokal (`scripts/chatbot_api/`,
`python -m uvicorn main:app --reload`, port 8000) SAMA-SAMA up - dicek
di awal main().

PENTING (pelajaran M7.12): pantau progres AKTIF lewat query Jaeger
berkala saat eksekusi berjalan (bukan menunggu buta).

Jalankan dari root repo: uv run python evals/7.16-verifikasi-alur-penuh-end-to-end/run_eval.py
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
SERVICE_NAME = "nirwana-chatbot-eval-7-16"

# Span pembungkus dengan NAMA UNIK per layer (decisions.md Keputusan 5) -
# presensinya dicek langsung, tidak ambigu. `matching.evaluate` SENGAJA
# tidak dimasukkan di sini - match_atomic_intents() (M1.7 Keputusan 4)
# mengambil fast-path NOL panggilan LLM (span ini genuinely tidak
# terbuka) kalau tidak ada kandidat session_memory berstatus BERHASIL -
# kondisi yang SELALU benar untuk E01/E02 (sesi baru, tanpa histori) dan
# E03 (sesi baru + history hanya field payload, session_memory DB tetap
# kosong). Temuan ini ditemukan SAAT run E01 pertama (Checkpoint 3),
# bukan diasumsikan sejak awal - lihat audit.md. Pencocokan tetap
# terbukti jalan lewat cabang deterministiknya sendiri (evidence:
# `hasil.matches` terisi, dicek terpisah di audit.md).
UNIQUE_LAYER_SPANS: dict[str, list[str]] = {
    "input_layer": ["input.validate"],
    "domain_gate": [
        "domain_gate.identifikasi_semua",
        "domain_gate.periksa_otorisasi_semua",
        "domain_gate.deteksi_constraint_semua",
    ],
    "retriever": ["retriever.proses_semua"],
    "query_engine": ["query_engine.susun_dan_verifikasi_request_semua"],
    "verification_gate": ["verification_gate.verifikasi_gate_semua"],
    "execution": [
        "execution.eksekusi_atomic_intent_semua",
        "execution.susun_dan_simpan_paket_semua",
    ],
    "orchestration": ["orchestration.susun_paket_narasi"],
}


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


def _analisis_cakupan_span(trace_data: dict | None, hasil) -> dict:
    """Verifikasi SUBSTANTIF cakupan span 9 layer - lihat penjelasan
    teknik atribusi "chat" di docstring modul ini."""
    if not trace_data or not trace_data.get("data"):
        return {"span_names_ditemukan": [], "cakupan_unik": {}, "lengkap": False}

    spans = trace_data["data"][0]["spans"]
    nama_ditemukan = {s["operationName"] for s in spans}

    cakupan_unik = {
        layer: {nama: (nama in nama_ditemukan) for nama in span_names}
        for layer, span_names in UNIQUE_LAYER_SPANS.items()
    }

    domain_gate_span = next(
        (s for s in spans if s["operationName"] == "domain_gate.identifikasi_semua"), None
    )
    paket_narasi_span = next(
        (s for s in spans if s["operationName"] == "orchestration.susun_paket_narasi"), None
    )
    chat_spans = [s for s in spans if s["operationName"] == "chat"]

    chat_sebelum_domain_gate = (
        [s for s in chat_spans if s["startTime"] < domain_gate_span["startTime"]]
        if domain_gate_span
        else []
    )
    chat_setelah_paket_narasi = (
        [
            s
            for s in chat_spans
            if s["startTime"] >= paket_narasi_span["startTime"] + paket_narasi_span["duration"]
        ]
        if paket_narasi_span
        else []
    )

    wave_spans = [s for s in spans if s["operationName"] == "orchestration.wave"]
    memory_retrieve_ada = "memory.retrieve" in nama_ditemukan
    matching_evaluate_ada = "matching.evaluate" in nama_ditemukan  # informasional, lihat komentar UNIQUE_LAYER_SPANS

    narasi_non_kosong = bool(hasil.interpretation[0].narasi.strip())

    span_unik_lengkap = all(all(v.values()) for v in cakupan_unik.values())
    lengkap = (
        span_unik_lengkap
        and len(chat_sebelum_domain_gate) >= 2  # minimal ketergantungan + rewrite (+decomposition)
        and len(chat_setelah_paket_narasi) >= 1  # minimal narasi Interpretation
        and narasi_non_kosong
    )

    return {
        "span_names_ditemukan": sorted(nama_ditemukan),
        "cakupan_unik": cakupan_unik,
        "chat_count_sebelum_domain_gate": len(chat_sebelum_domain_gate),
        "chat_count_setelah_paket_narasi": len(chat_setelah_paket_narasi),
        "wave_count": len(wave_spans),
        "memory_retrieve_ada": memory_retrieve_ada,
        "matching_evaluate_ada": matching_evaluate_ada,
        "narasi_non_kosong": narasi_non_kosong,
        "lengkap": lengkap,
    }


def _serialize_result(hasil) -> dict:
    narasi, verifikasi_narasi, visualisasi = hasil.interpretation
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
        "paket_narasi": [p.model_dump() for p in hasil.paket_narasi],
        "interpretation": {
            "narasi": narasi.model_dump(),
            "verifikasi_narasi": verifikasi_narasi.model_dump(),
            "visualisasi": [v.model_dump() for v in visualisasi] if visualisasi else None,
        },
    }


def _jalankan_kejadian(kejadian_id: str, deskripsi: str, raw: dict) -> dict:
    _CAPTURE.last_trace_id = None
    hasil = proses_turn(raw)
    trace.get_tracer_provider().force_flush()
    hasil_dump = _serialize_result(hasil)

    trace_id = _CAPTURE.last_trace_id
    span_wajib_ada = {"invoke_agent", "input.validate", "orchestration.susun_paket_narasi"}
    trace_data = _query_jaeger_trace(trace_id, span_wajib_ada) if trace_id else None
    cakupan_span = _analisis_cakupan_span(trace_data, hasil)

    record = {
        "kejadian_id": kejadian_id,
        "deskripsi": deskripsi,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_payload": raw,
        "hasil": hasil_dump,
        "trace_id": trace_id,
        "cakupan_span": cakupan_span,
        "error": None,
    }
    return record


def run_e01() -> dict:
    raw = {
        "session_id": "eval-7.16-e01",
        "turn_index": 1,
        "role_title": "General Manager",
        "employee_id": "emp-eval",
        "question": "Berapa occupancy rate properti kita bulan Juni 2026?",
    }
    return _jalankan_kejadian(
        "E01", "Kebutuhan tunggal sederhana (reuse M7.9 E01)", raw
    )


def run_e02() -> dict:
    raw = {
        "session_id": "eval-7.16-e02",
        "turn_index": 1,
        "role_title": "Front Office Staff",
        "employee_id": "emp-eval",
        "question": "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?",
    }
    return _jalankan_kejadian(
        "E02", "Kebutuhan dengan wave (reuse M7.14 E01)", raw
    )


def run_e03() -> dict:
    raw = {
        "session_id": "eval-7.16-e03",
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
        "E03", "Rujukan lintas-turn, history fiktif (mirror M7.7 E01)", raw
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
        print(f"  lengkap={record['cakupan_span']['lengkap']}")
        print(f"  cakupan_unik={json.dumps(record['cakupan_span']['cakupan_unik'], ensure_ascii=False)}")
        print(
            f"  chat_sebelum_domain_gate={record['cakupan_span']['chat_count_sebelum_domain_gate']} "
            f"chat_setelah_paket_narasi={record['cakupan_span']['chat_count_setelah_paket_narasi']} "
            f"wave_count={record['cakupan_span']['wave_count']} "
            f"memory_retrieve_ada={record['cakupan_span']['memory_retrieve_ada']}"
        )

    print(f"\nPayload lengkap tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
