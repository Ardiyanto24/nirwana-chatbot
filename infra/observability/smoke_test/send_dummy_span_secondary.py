"""Skrip verifikasi Milestone 1.1 (emitter kedua/"sekunder").

Independen dari send_dummy_span.py (proses Python terpisah, `service.name`
berbeda) - mensimulasikan "PIC lain" yang mengarahkan instrumentasinya ke
Collector yang sama, karena belum ada milestone PIC 2/3/4 sungguhan yang bisa
dipakai sebagai bukti nyata (lihat Temuan Penting #4 di plan). Sengaja
memakai bentuk span non-LLM (`input.validate`, sesuai kontrak Bagian 2
rancangan-observability-ai-chatbot.md untuk Input Layer) - berbeda dari span
`chat` berisi atribut gen_ai.* di skrip primer, supaya jelas ini emitter
yang benar-benar independen, bukan sekadar salinan skrip pertama.

Jalankan dari root repo (proses terpisah dari send_dummy_span.py):
uv run python infra/observability/smoke_test/send_dummy_span_secondary.py
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

OTLP_ENDPOINT = "localhost:4317"
SERVICE_NAME = "milestone-1.1-smoke-test-secondary"


def setup_tracing() -> tuple[trace.Tracer, TracerProvider]:
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME), provider


def main() -> None:
    tracer, provider = setup_tracing()

    with tracer.start_as_current_span("input.validate") as span:
        span.set_attribute("session.id", "milestone-1.1-smoke-test-secondary")
        span.set_attribute("turn.index", 1)
        span.set_attribute("smoke_test.marker", "milestone-1.1-secondary")
        trace_id_hex = format(span.get_span_context().trace_id, "032x")

    provider.force_flush()
    provider.shutdown()

    print(f"trace_id={trace_id_hex}")
    print("Selesai mengirim span dummy (emitter sekunder) ke Collector.")


if __name__ == "__main__":
    main()
