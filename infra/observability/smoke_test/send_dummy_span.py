"""Skrip verifikasi Milestone 1.1 (emitter pertama/"primer").

Mengirim satu span dummy (dibungkus span induk `invoke_agent`, sesuai kontrak
Bagian 2 rancangan-observability-ai-chatbot.md) dan satu metric dummy ke OTel
Collector lokal (localhost:4317) - membuktikan Collector benar-benar menerima
dan meneruskan data end-to-end ke Jaeger (trace) dan Prometheus (metrics).

Jalankan dari root repo: uv run python infra/observability/smoke_test/send_dummy_span.py
"""

import sys
import time
from pathlib import Path

# genai_semconv.py ada satu level di atas folder skrip ini (infra/observability/),
# bukan paket yang di-install - ditambahkan manual ke sys.path supaya bisa
# diimpor terlepas dari cwd saat skrip dijalankan.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import genai_semconv as semconv  # noqa: E402

from opentelemetry import metrics, trace  # noqa: E402
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # noqa: E402
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: E402
    OTLPSpanExporter,
)
from opentelemetry.sdk.metrics import MeterProvider  # noqa: E402
from opentelemetry.sdk.metrics.export import (  # noqa: E402
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: E402

OTLP_ENDPOINT = "localhost:4317"
SERVICE_NAME = "milestone-1.1-smoke-test-primary"


def setup_tracing() -> tuple[trace.Tracer, TracerProvider]:
    resource = Resource.create({"service.name": SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(SERVICE_NAME), provider


def setup_metrics() -> tuple[metrics.Meter, MeterProvider]:
    resource = Resource.create({"service.name": SERVICE_NAME})
    exporter = OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=2000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return metrics.get_meter(SERVICE_NAME), provider


def main() -> None:
    tracer, tracer_provider = setup_tracing()
    meter, meter_provider = setup_metrics()

    counter = meter.create_counter(
        "smoke_test.dummy_counter",
        description="Metric dummy verifikasi Milestone 1.1 (emitter primer)",
    )

    with tracer.start_as_current_span("invoke_agent") as turn_span:
        turn_span.set_attribute("session.id", "milestone-1.1-smoke-test")
        turn_span.set_attribute("turn.index", 1)

        with tracer.start_as_current_span("chat") as chat_span:
            chat_span.set_attribute(semconv.GEN_AI_OPERATION_NAME, "chat")
            chat_span.set_attribute(
                semconv.GEN_AI_REQUEST_MODEL, "dummy-model-smoke-test"
            )
            chat_span.set_attribute(
                semconv.GEN_AI_CONVERSATION_ID, "milestone-1.1-smoke-test"
            )
            chat_span.set_attribute(semconv.GEN_AI_USAGE_INPUT_TOKENS, 10)
            chat_span.set_attribute(semconv.GEN_AI_USAGE_OUTPUT_TOKENS, 5)
            chat_span.set_attribute("smoke_test.marker", "milestone-1.1-primary")

        counter.add(1, {"smoke_test.marker": "milestone-1.1-primary"})

        trace_id_hex = format(turn_span.get_span_context().trace_id, "032x")

    tracer_provider.force_flush()
    meter_provider.force_flush()
    time.sleep(3)  # beri waktu PeriodicExportingMetricReader mengirim batch terakhir
    tracer_provider.shutdown()
    meter_provider.shutdown()

    print(f"trace_id={trace_id_hex}")
    print("Selesai mengirim span dummy + metric dummy (emitter primer) ke Collector.")


if __name__ == "__main__":
    main()
