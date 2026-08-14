"""Setup `TracerProvider` bersama untuk aplikasi (bukan skrip smoke-test).

Dipanggil sekali saat startup `src/main.py`. Layer lain (mis.
`src/layers/input_layer.py`) memanggil `get_tracer()` untuk emit span,
memakai `TracerProvider` yang sama yang sudah di-setup di sini - bukan
membuat provider terpisah masing-masing.

Pola diadaptasi dari `infra/observability/smoke_test/send_dummy_span_secondary.py`
(Milestone 1.1), diparameterisasi lewat `service_name` dan dipisah jadi
`setup_tracing()` (dipanggil sekali) + `get_tracer()` (dipanggil tiap layer).
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

OTLP_ENDPOINT = "localhost:4317"


def setup_tracing(service_name: str) -> TracerProvider:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
