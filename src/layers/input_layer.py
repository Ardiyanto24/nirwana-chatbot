"""Input Layer (Milestone 1.2): validasi payload turn percakapan.

Murni mekanis, TANPA pemanggilan model AI - kegagalan di titik ini selalu
karena alasan struktural yang jelas (lihat rancangan-context-decomposition.md
Milestone 1.2). Mengemisi span `input.validate` sesuai kontrak Bagian 2
rancangan-observability-ai-chatbot.md.
"""

from src.observability.tracing import get_tracer
from src.schemas.turn_payload import TurnPayload

_TRACER_NAME = "input_layer"


def validate_turn_payload(raw: dict) -> TurnPayload:
    """Validasi payload mentah, kembalikan `TurnPayload` atau lempar
    `pydantic.ValidationError` kalau ada field yang bermasalah."""
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("input.validate") as span:
        if "session_id" in raw:
            span.set_attribute("session.id", str(raw["session_id"]))
        if "turn_index" in raw:
            try:
                span.set_attribute("turn.index", int(raw["turn_index"]))
            except (TypeError, ValueError):
                pass
        return TurnPayload.model_validate(raw)
