"""Pemanggilan chatbot_api (Milestone 4.1): satu-satunya titik dalam
seluruh sistem yang benar-benar melakukan panggilan HTTP ke chatbot_api -
murni teknis, TANPA LLM sama sekali (lihat decisions.md Keputusan 3).

Menerima QueryEngineRequest yang SUDAH lolos Verification Gate (M2.4,
`HasilVerifikasiGate.request_final` saat `lolos=True`) - fungsi ini
TIDAK memeriksa ulang kelolosan itu, murni prasyarat yang diasumsikan
sudah dipenuhi pemanggil.

Mengembalikan respons mentah (status_code + body) APA ADANYA, tanpa
klasifikasi/interpretasi - itu tanggung jawab Milestone 4.2 (di luar
cakupan modul ini).
"""

import httpx

from src.config.chatbot_api import CHATBOT_API_TIMEOUT_DETIK, get_chatbot_api_base_url
from src.config.slug_view_chatbot_api import VIEW_NAME_KE_SLUG_CHATBOT_API
from src.observability.tracing import get_tracer
from src.schemas.execution import HasilPemanggilanChatbotAPI
from src.schemas.verification_gate import QueryEngineRequest

_TRACER_NAME = "execution.pemanggilan_chatbot_api"


def panggil_chatbot_api(
    request: QueryEngineRequest, role_title: str, employee_id: str
) -> HasilPemanggilanChatbotAPI:
    """Satu panggilan GET ke chatbot_api. role_title/employee_id adalah
    identitas caller (dari TurnPayload, mengalir sejak M1.2) - parameter
    EKSPLISIT terpisah dari request.params (yang berisi filter data hasil
    ekstraksi Query Engine M3.4), lihat decisions.md Keputusan 4."""
    slug = VIEW_NAME_KE_SLUG_CHATBOT_API[request.view_name]
    url = f"{get_chatbot_api_base_url()}/chatbot/{request.domain.value}/{slug}"

    query_params = {k: v for k, v in request.params.items() if v is not None}
    query_params["role_title"] = role_title
    query_params["employee_id"] = employee_id

    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("execute_tool") as span:
        try:
            with httpx.Client(timeout=CHATBOT_API_TIMEOUT_DETIK) as client:
                response = client.get(url, params=query_params)
        except httpx.TimeoutException:
            return HasilPemanggilanChatbotAPI(status_code=None, kegagalan_transport="timeout")
        except httpx.TransportError:
            return HasilPemanggilanChatbotAPI(
                status_code=None, kegagalan_transport="connection_error"
            )

        span.set_attribute("http.response.status_code", response.status_code)

        try:
            body = response.json()
        except ValueError:
            body = response.text

        return HasilPemanggilanChatbotAPI(status_code=response.status_code, body=body)
