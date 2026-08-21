"""Skrip verifikasi Milestone 6.1 (mirror pola
infra/observability/smoke_test/send_dummy_span.py) - membuktikan KEDUA
Kriteria Keberhasilan M6.1 terhadap stack PRODUKSI (docker-compose port
4317, exporter "supabase" native), bukan binary lokal ad-hoc.

KK1: "Span percobaan sederhana... muncul sebagai baris baru di Supabase,
dengan seluruh atribut wajib (nama layer, durasi, status) terisi sesuai
nilai aslinya."
KK2: "Span anak dengan parent_span_id yang mengarah ke span induk yang
sudah tertulis lebih dulu, tersimpan dengan relasi induk-anak yang benar
dan bisa ditelusuri kembali lewat query sederhana."

Jalankan dari root repo (docker compose observability HARUS sudah up):
  uv run python milestones/6.1-membangun-exporter-dasar/verify_kk1_kk2.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from opentelemetry import trace  # noqa: E402
from opentelemetry.context import attach, detach  # noqa: E402
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: E402
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.trace import (  # noqa: E402
    NonRecordingSpan,
    SpanContext,
    TraceFlags,
    set_span_in_context,
)
from sqlalchemy import text  # noqa: E402

from src.config.database import get_engine  # noqa: E402

OTLP_ENDPOINT = "localhost:4317"  # port PRODUKSI docker-compose, bukan test port lokal
SERVICE_NAME = "milestone-6.1-verify-kk"
SESSION_ID = "milestone-6.1-verify-kk-session"


def setup_tracing() -> tuple[trace.Tracer, TracerProvider]:
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("orchestration"), provider


def cleanup(trace_id: str) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM spans WHERE trace_id = :tid"), {"tid": trace_id})
        conn.execute(text("DELETE FROM traces WHERE trace_id = :tid"), {"tid": trace_id})


def main() -> None:
    tracer, provider = setup_tracing()

    # --- KK1: span sederhana (anchor invoke_agent) ---
    with tracer.start_as_current_span("invoke_agent") as parent_span:
        parent_span.set_attribute("session.id", SESSION_ID)
        parent_span.set_attribute("turn.index", 1)
        trace_id_hex = format(parent_span.get_span_context().trace_id, "032x")
        parent_span_id_hex = format(parent_span.get_span_context().span_id, "016x")

    provider.force_flush()
    # otel-collector-config.yaml (M1.1) mengonfigurasi processor `batch`
    # dengan timeout: 5s - span ditahan di buffer batch SEBELUM diteruskan
    # ke exporter manapun (bukan keterlambatan exporter/Supabase). Jeda
    # WAJIB lebih lama dari 5s supaya query di bawah tidak race kondisi
    # batch belum ter-flush (ditemukan lewat percobaan nyata pertama -
    # lihat milestones/6.1-.../logs.md Checkpoint 10).
    time.sleep(7)

    engine = get_engine()
    with engine.connect() as conn:
        trace_row = conn.execute(
            text("SELECT session_id, turn_index FROM traces WHERE trace_id = :tid"),
            {"tid": trace_id_hex},
        ).fetchone()
        span_row = conn.execute(
            text(
                "SELECT layer_name, operation_name, duration_ms FROM spans "
                "WHERE trace_id = :tid AND span_id = :sid"
            ),
            {"tid": trace_id_hex, "sid": parent_span_id_hex},
        ).fetchone()

    kk1_ok = (
        trace_row is not None
        and trace_row.session_id == SESSION_ID
        and trace_row.turn_index == 1
        and span_row is not None
        and span_row.layer_name == "orchestration"
        and span_row.operation_name == "invoke_agent"
        and span_row.duration_ms is not None
    )
    print(f"KK1 - traces row: {trace_row}")
    print(f"KK1 - spans row (layer/operation/duration): {span_row}")
    print(f"KK1 TERPENUHI: {kk1_ok}")

    # --- KK2: span anak, context direkonstruksi dari parent yang SUDAH tertulis ---
    span_context = SpanContext(
        trace_id=int(trace_id_hex, 16),
        span_id=int(parent_span_id_hex, 16),
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    ctx = set_span_in_context(NonRecordingSpan(span_context))
    token = attach(ctx)
    tracer_child = trace.get_tracer("domain_gate.otorisasi")
    with tracer_child.start_as_current_span("authorization.check") as child_span:
        child_span.set_attribute("error.type", "ditolak_otorisasi")
        child_span_id_hex = format(child_span.get_span_context().span_id, "016x")
    detach(token)

    provider.force_flush()
    time.sleep(7)  # sama alasan seperti di atas - jeda batch processor 5s

    with engine.connect() as conn:
        joined = conn.execute(
            text(
                "SELECT s.span_id, s.parent_span_id, s.layer_name, s.error_type, "
                "p.span_id AS resolved_parent "
                "FROM spans s LEFT JOIN spans p ON s.parent_span_id = p.span_id "
                "WHERE s.trace_id = :tid AND s.span_id = :sid"
            ),
            {"tid": trace_id_hex, "sid": child_span_id_hex},
        ).fetchone()

    kk2_ok = (
        joined is not None
        and joined.parent_span_id == parent_span_id_hex
        and joined.resolved_parent == parent_span_id_hex
        and joined.layer_name == "domain_gate"
        and joined.error_type == "ditolak_otorisasi"
    )
    print(f"KK2 - JOIN span anak+induk: {joined}")
    print(f"KK2 TERPENUHI: {kk2_ok}")

    provider.shutdown()
    cleanup(trace_id_hex)
    print(f"trace_id={trace_id_hex} (data test dibersihkan)")

    if not (kk1_ok and kk2_ok):
        raise SystemExit("VERIFIKASI GAGAL - lihat detail di atas.")
    print("KEDUA KRITERIA KEBERHASILAN M6.1 TERPENUHI.")


if __name__ == "__main__":
    main()
