"""Skrip verifikasi KK1 M6.2 (fault injection) - mirror
infra/observability/smoke_test/send_dummy_span.py, session_id unik
supaya mudah dibedakan dari data smoke test/turn nyata lain.

Mengirim invoke_agent (anchor) + 1 span anak ke Collector lokal
(localhost:4317, DSN exporter sudah diarahkan sementara ke Postgres
lokal disposable Checkpoint 5). force_flush() dipanggil supaya SDK
export SEGERA (tidak menunggu batch periodik 5s), membuat timing
simulasi outage lebih presisi/terkontrol.

Jalankan dari root repo:
uv run python milestones/6.2-.../send_test_span_kk1.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from opentelemetry import trace  # noqa: E402
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: E402
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: E402

OTLP_ENDPOINT = "localhost:4317"
SERVICE_NAME = "m6.2-fault-injection-kk1"
SESSION_ID = "m6.2-fault-injection-kk1"


def main() -> None:
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(SERVICE_NAME)

    with tracer.start_as_current_span("invoke_agent") as turn_span:
        turn_span.set_attribute("session.id", SESSION_ID)
        turn_span.set_attribute("turn.index", 1)
        turn_span.set_attribute("role_title", "General Manager")

        with tracer.start_as_current_span("chat"):
            pass

        trace_id_hex = format(turn_span.get_span_context().trace_id, "032x")

    provider.force_flush()
    provider.shutdown()

    print(f"trace_id={trace_id_hex}")
    print(f"session_id={SESSION_ID}")


if __name__ == "__main__":
    main()
