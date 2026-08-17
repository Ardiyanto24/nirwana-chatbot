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

Direfactor Milestone 4.2 (Checkpoint 2, lihat milestones/4.2-.../
decisions.md Keputusan 5): logic murni diekstrak ke
`_panggil_chatbot_api_raw()` (TANPA span sendiri) - mirror pola refactor
M3.1/M3.3 (Keputusan 4 M3.3, `_kumpulkan_kandidat()`) - supaya M4.2 bisa
membungkus SATU span `execute_tool` untuk seluruh retry+revisi loop,
bukan span baru tiap percobaan. `panggil_chatbot_api()` publik (fungsi
di bawah) TIDAK berubah perilaku/signature/span sama sekali untuk
pemanggil standalone - tetap membuka span sendiri via wrapper tipis,
regresi test_pemanggilan_chatbot_api.py dijalankan penuh tanpa perubahan
assertion untuk membuktikannya.
"""

import httpx

from src.config.chatbot_api import CHATBOT_API_TIMEOUT_DETIK, get_chatbot_api_base_url
from src.config.slug_view_chatbot_api import VIEW_NAME_KE_SLUG_CHATBOT_API
from src.observability.tracing import get_tracer
from src.schemas.execution import HasilMetaChatbotAPI, HasilPemanggilanChatbotAPI
from src.schemas.verification_gate import QueryEngineRequest

_TRACER_NAME = "execution.pemanggilan_chatbot_api"


def _panggil_chatbot_api_raw(
    request: QueryEngineRequest, role_title: str, employee_id: str
) -> HasilPemanggilanChatbotAPI:
    """Logic murni M4.1 (HTTP GET + parsing), TANPA membuka span
    `execute_tool` sendiri - dipakai ulang M4.2 (`klasifikasi_respons.py`)
    untuk membungkus banyak percobaan (retry infra + revisi 400) dalam
    SATU span pembungkus, lihat decisions.md M4.2 Keputusan 5."""
    slug = VIEW_NAME_KE_SLUG_CHATBOT_API[request.view_name]
    url = f"{get_chatbot_api_base_url()}/chatbot/{request.domain.value}/{slug}"

    query_params = {k: v for k, v in request.params.items() if v is not None}
    query_params["role_title"] = role_title
    query_params["employee_id"] = employee_id

    try:
        with httpx.Client(timeout=CHATBOT_API_TIMEOUT_DETIK) as client:
            response = client.get(url, params=query_params)
    except httpx.TimeoutException:
        return HasilPemanggilanChatbotAPI(status_code=None, kegagalan_transport="timeout")
    except httpx.TransportError:
        return HasilPemanggilanChatbotAPI(status_code=None, kegagalan_transport="connection_error")

    try:
        body = response.json()
    except ValueError:
        body = response.text

    return HasilPemanggilanChatbotAPI(status_code=response.status_code, body=body)


def panggil_chatbot_api(
    request: QueryEngineRequest, role_title: str, employee_id: str
) -> HasilPemanggilanChatbotAPI:
    """Entry point standalone M4.1 - wrapper tipis di atas
    `_panggil_chatbot_api_raw()`, membuka+menutup span `execute_tool`
    sendiri (perilaku/signature/atribut span IDENTIK dengan sebelum
    refactor Checkpoint 2 M4.2). Dipakai kalau satu panggilan HTTP
    DIBUTUHKAN BERDIRI SENDIRI (mis. test M4.1) - jalur produksi penuh
    lewat orkestrator M4.2 (`klasifikasi_respons.eksekusi_atomic_intent()`)
    yang membungkus banyak percobaan dalam satu span.

    role_title/employee_id adalah identitas caller (dari TurnPayload,
    mengalir sejak M1.2) - parameter EKSPLISIT terpisah dari
    request.params (yang berisi filter data hasil ekstraksi Query Engine
    M3.4), lihat decisions.md M4.1 Keputusan 4."""
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("execute_tool") as span:
        hasil = _panggil_chatbot_api_raw(request, role_title, employee_id)
        if hasil.status_code is not None:
            span.set_attribute("http.response.status_code", hasil.status_code)
        return hasil


def panggil_meta_chatbot_api(
    request: QueryEngineRequest, role_title: str, employee_id: str
) -> HasilMetaChatbotAPI:
    """Endpoint `_meta` (tim database engineering, Milestone 4.7 sisi
    mereka - lihat milestones/4.2-.../decisions.md Keputusan 11) - sinyal
    freshness/kualitas data, Opsi B (endpoint terpisah, TIDAK mengubah
    bentuk endpoint data yang sudah ada). SATU percobaan saja, TANPA
    retry - kegagalan sinyal sekunder ini TIDAK BOLEH menahan/
    menggagalkan atomic intent yang datanya sendiri sudah berhasil
    diambil lewat `panggil_chatbot_api()`/`_panggil_chatbot_api_raw()`.

    TIDAK membuka span sendiri - dipanggil dari `eksekusi_atomic_intent()`
    (M4.2, `klasifikasi_respons.py`) yang sudah membungkus span
    `execute_tool`, mirror pola `_panggil_chatbot_api_raw()`.

    Non-200/kegagalan transport apa pun diperlakukan seragam sebagai
    "tidak diketahui" (field lain `None`) - TIDAK PERNAH crash, karena
    ini sinyal best-effort yang bukan bagian ruang kesalahan tertutup
    KK sumber M4.1/M4.2."""
    slug = VIEW_NAME_KE_SLUG_CHATBOT_API[request.view_name]
    url = f"{get_chatbot_api_base_url()}/chatbot/{request.domain.value}/{slug}/_meta"
    query_params = {"role_title": role_title, "employee_id": employee_id}

    try:
        with httpx.Client(timeout=CHATBOT_API_TIMEOUT_DETIK) as client:
            response = client.get(url, params=query_params)
    except httpx.TimeoutException:
        return HasilMetaChatbotAPI(status_code=None, kegagalan_transport="timeout")
    except httpx.TransportError:
        return HasilMetaChatbotAPI(status_code=None, kegagalan_transport="connection_error")

    if response.status_code != 200:
        return HasilMetaChatbotAPI(status_code=response.status_code)

    try:
        body = response.json()
    except ValueError:
        return HasilMetaChatbotAPI(status_code=response.status_code)

    if not isinstance(body, dict):
        return HasilMetaChatbotAPI(status_code=response.status_code)

    return HasilMetaChatbotAPI(
        status_code=response.status_code,
        data_quality_status=body.get("data_quality_status"),
        last_refreshed_at=body.get("last_refreshed_at"),
    )
