"""Test suite pemanggilan_chatbot_api (Milestone 4.1), Checkpoint 4.

`httpx.Client.get` di-monkeypatch (tanpa dependency mock tambahan) -
seluruh test murni terhadap logic panggil_chatbot_api(), TIDAK menyentuh
chatbot_api sungguhan (itu Checkpoint 5, DITUNDA - lihat decisions.md
Keputusan 2).
"""

import httpx
import pytest

from src.layers.execution import pemanggilan_chatbot_api as modul
from src.schemas.domain_gate import Domain
from src.schemas.verification_gate import QueryEngineRequest

_BASE_URL = "http://testserver"


@pytest.fixture(autouse=True)
def _base_url_tetap(monkeypatch):
    monkeypatch.setattr(modul, "get_chatbot_api_base_url", lambda: _BASE_URL)


def _buat_request(
    domain: Domain = Domain.FACILITY,
    view_name: str = "v_housekeeping_staff_daily",
    params: dict | None = None,
) -> QueryEngineRequest:
    return QueryEngineRequest(domain=domain, view_name=view_name, params=params or {})


def _patch_get(monkeypatch, respons_atau_exception):
    """respons_atau_exception: httpx.Response untuk sukses, atau Exception
    untuk disimulasikan sebagai raise. Mengembalikan dict yang diisi
    argumen panggilan get() terakhir untuk diperiksa test."""
    dipanggil_dengan: dict = {}

    def _fake_get(self, url, params=None, **kwargs):
        dipanggil_dengan["url"] = url
        dipanggil_dengan["params"] = params
        if isinstance(respons_atau_exception, Exception):
            raise respons_atau_exception
        return respons_atau_exception

    monkeypatch.setattr(httpx.Client, "get", _fake_get)
    return dipanggil_dengan


# --- (a) translasi view_name -> slug URL ------------------------------------


def test_view_name_diterjemahkan_ke_slug_url(monkeypatch):
    dipanggil = _patch_get(monkeypatch, httpx.Response(200, json=[]))

    panggil_chatbot_api = modul.panggil_chatbot_api
    panggil_chatbot_api(
        _buat_request(domain=Domain.FACILITY, view_name="v_housekeeping_staff_daily"),
        role_title="Housekeeping Staff",
        employee_id="E0001",
    )

    assert dipanggil["url"] == f"{_BASE_URL}/chatbot/facility/housekeeping-staff-daily"
    assert "v_housekeeping_staff_daily" not in dipanggil["url"]


def test_view_name_lain_domain_lain_diterjemahkan_benar(monkeypatch):
    dipanggil = _patch_get(monkeypatch, httpx.Response(200, json=[]))

    modul.panggil_chatbot_api(
        _buat_request(domain=Domain.HR, view_name="v_lookup_employee_performance"),
        role_title="HR Manager",
        employee_id="E0002",
    )

    assert dipanggil["url"] == f"{_BASE_URL}/chatbot/hr/employee-performance"


# --- (b) respons 200 diteruskan apa adanya ----------------------------------


def test_respons_200_diteruskan_apa_adanya(monkeypatch):
    body_asli = [{"property_id": "P01", "room_count": 42}]
    _patch_get(monkeypatch, httpx.Response(200, json=body_asli))

    hasil = modul.panggil_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code == 200
    assert hasil.body == body_asli
    assert hasil.kegagalan_transport is None


# --- (c) respons 403/404 diteruskan apa adanya, bukan di-raise -------------


@pytest.mark.parametrize("status_code", [403, 404])
def test_respons_403_404_diteruskan_apa_adanya(monkeypatch, status_code):
    body_asli = {"detail": "pesan penolakan asli"}
    _patch_get(monkeypatch, httpx.Response(status_code, json=body_asli))

    hasil = modul.panggil_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code == status_code
    assert hasil.body == body_asli
    assert hasil.kegagalan_transport is None


# --- (d) respons 500 non-JSON ditangani tanpa crash -------------------------


def test_respons_500_non_json_fallback_ke_text(monkeypatch):
    _patch_get(monkeypatch, httpx.Response(500, text="<html>Internal Server Error</html>"))

    hasil = modul.panggil_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code == 500
    assert hasil.body == "<html>Internal Server Error</html>"
    assert hasil.kegagalan_transport is None


# --- (e) kegagalan transport (timeout/connection error) --------------------


def test_timeout_menghasilkan_kegagalan_transport(monkeypatch):
    _patch_get(monkeypatch, httpx.TimeoutException("simulasi timeout"))

    hasil = modul.panggil_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code is None
    assert hasil.kegagalan_transport == "timeout"


def test_connection_error_menghasilkan_kegagalan_transport(monkeypatch):
    _patch_get(monkeypatch, httpx.ConnectError("simulasi connection refused"))

    hasil = modul.panggil_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code is None
    assert hasil.kegagalan_transport == "connection_error"


# --- (f) role_title/employee_id/params masuk benar ke query string ---------


def test_role_title_employee_id_params_masuk_ke_query_string(monkeypatch):
    dipanggil = _patch_get(monkeypatch, httpx.Response(200, json=[]))

    modul.panggil_chatbot_api(
        _buat_request(params={"property_id": "P01", "date_from": "2026-06-01"}),
        role_title="Housekeeping Staff",
        employee_id="E0001",
    )

    assert dipanggil["params"] == {
        "property_id": "P01",
        "date_from": "2026-06-01",
        "role_title": "Housekeeping Staff",
        "employee_id": "E0001",
    }


def test_nilai_none_di_params_tidak_ikut_terkirim(monkeypatch):
    dipanggil = _patch_get(monkeypatch, httpx.Response(200, json=[]))

    modul.panggil_chatbot_api(
        _buat_request(params={"property_id": "P01", "status": None}),
        role_title="X",
        employee_id="E0001",
    )

    assert "status" not in dipanggil["params"]
    assert dipanggil["params"]["property_id"] == "P01"


# --- span execute_tool -------------------------------------------------------


# --- panggil_meta_chatbot_api (Milestone 4.2 revisit) -----------------------


def test_meta_url_menyisipkan_meta_di_belakang_slug(monkeypatch):
    dipanggil = _patch_get(
        monkeypatch, httpx.Response(200, json={"data_quality_status": "ok", "last_refreshed_at": "x"})
    )

    modul.panggil_meta_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert dipanggil["url"] == (
        f"{_BASE_URL}/chatbot/facility/housekeeping-staff-daily/_meta"
    )


def test_meta_200_lengkap_ter_parse_benar(monkeypatch):
    _patch_get(
        monkeypatch,
        httpx.Response(
            200, json={"view": "x", "data_quality_status": "flagged", "last_refreshed_at": "2026-08-17T05:12:03.481Z"}
        ),
    )

    hasil = modul.panggil_meta_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code == 200
    assert hasil.data_quality_status == "flagged"
    assert hasil.last_refreshed_at == "2026-08-17T05:12:03.481Z"
    assert hasil.kegagalan_transport is None


def test_meta_200_field_null_diterima_apa_adanya(monkeypatch):
    _patch_get(monkeypatch, httpx.Response(200, json={"data_quality_status": None, "last_refreshed_at": None}))

    hasil = modul.panggil_meta_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code == 200
    assert hasil.data_quality_status is None
    assert hasil.last_refreshed_at is None


@pytest.mark.parametrize("status_code", [403, 404, 500])
def test_meta_non_200_field_kosong_tanpa_crash(monkeypatch, status_code):
    _patch_get(monkeypatch, httpx.Response(status_code, json={"detail": "x"}))

    hasil = modul.panggil_meta_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code == status_code
    assert hasil.data_quality_status is None
    assert hasil.last_refreshed_at is None


def test_meta_timeout_field_kosong_tanpa_crash(monkeypatch):
    _patch_get(monkeypatch, httpx.TimeoutException("simulasi timeout"))

    hasil = modul.panggil_meta_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert hasil.status_code is None
    assert hasil.kegagalan_transport == "timeout"
    assert hasil.data_quality_status is None


def test_meta_tidak_membuka_span_sendiri(monkeypatch):
    """Beda dari panggil_chatbot_api(), fungsi ini TIDAK boleh memanggil
    get_tracer() sama sekali - span execute_tool dibungkus pemanggil
    (M4.2 klasifikasi_respons.py)."""
    dipanggil_tracer = {"count": 0}

    def _fake_get_tracer(name):
        dipanggil_tracer["count"] += 1
        raise AssertionError("panggil_meta_chatbot_api tidak boleh memanggil get_tracer()")

    monkeypatch.setattr(modul, "get_tracer", _fake_get_tracer)
    _patch_get(monkeypatch, httpx.Response(200, json={}))

    modul.panggil_meta_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert dipanggil_tracer["count"] == 0


def test_span_execute_tool_mencatat_status_code(monkeypatch):
    _patch_get(monkeypatch, httpx.Response(200, json=[]))

    atribut_tercatat = {}
    kelas_span_asli = modul.get_tracer

    class _SpanRekam:
        def __init__(self, nama):
            self.nama = nama

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def set_attribute(self, key, value):
            atribut_tercatat[key] = value

    class _TracerRekam:
        def start_as_current_span(self, nama):
            return _SpanRekam(nama)

    monkeypatch.setattr(modul, "get_tracer", lambda name: _TracerRekam())

    modul.panggil_chatbot_api(_buat_request(), role_title="X", employee_id="E0001")

    assert atribut_tercatat.get("http.response.status_code") == 200
