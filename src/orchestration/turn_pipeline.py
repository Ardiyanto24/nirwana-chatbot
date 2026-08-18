"""Orkestrator Turn PIC 7 Level 2 (Milestone 7.6, Sambungan 1): Input Layer
(M1.2) -> Pemetaan Ketergantungan Turn (M1.3).

Fungsi ini membuka span `invoke_agent` PERTAMA KALI di `src/` produksi -
pembungkus "operasi orkestrasi keseluruhan" per turn sesuai kontrak
Bagian 2 rancangan-observability-ai-chatbot.md. Tumbuh bertahap tiap
milestone Sambungan berikutnya (M7.7-7.16) hingga mencakup seluruh
sembilan layer. `src/main.py` SENGAJA belum memanggil fungsi ini -
penyambungan endpoint ditunda ke Milestone 7.17.

Short-circuit murni alami: `validate_turn_payload()` melempar
`pydantic.ValidationError` yang menjalar keluar tanpa `detect_turn_
dependency()` pernah terpanggil - tidak ada `try`/`if` eksplisit yang
menyembunyikan kegagalan. `openai.APIError` dari `detect_turn_
dependency()` juga dibiarkan menjalar apa adanya (celah M1.3, tidak
dirombak ulang di sini - lihat docs/keterbatasan-diterima.md).

Lihat milestones/7.6-sambungan-input-layer-pemetaan-ketergantungan/decisions.md.
"""

from src.layers.context_resolution.turn_dependency import detect_turn_dependency
from src.layers.input_layer import validate_turn_payload
from src.observability.tracing import get_tracer
from src.schemas.orchestration import KeadaanTurn

_TRACER_NAME = "orchestration"


def proses_turn(raw: dict) -> KeadaanTurn:
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("invoke_agent") as span:
        if "session_id" in raw:
            span.set_attribute("session.id", str(raw["session_id"]))
        if "turn_index" in raw:
            try:
                span.set_attribute("turn.index", int(raw["turn_index"]))
            except (TypeError, ValueError):
                pass

        payload = validate_turn_payload(raw)
        ketergantungan = detect_turn_dependency(payload)
        return KeadaanTurn(payload=payload, ketergantungan=ketergantungan)
