"""Test suite orkestrator Klasifikasi Respons (Milestone 4.2) -
src/layers/execution/klasifikasi_respons.py. `_panggil_chatbot_api_raw`
di-monkeypatch langsung (bukan httpx.Client seperti test M4.1) - modul
ini TIDAK menyentuh HTTP sama sekali, murni orkestrasi klasifikasi.
`time.sleep` di-monkeypatch supaya test retry tidak benar-benar
menunggu. Real testing ke chatbot_api sungguhan DITUNDA (Checkpoint 7,
lihat decisions.md Keputusan 4) - seluruh skenario di sini disimulasikan,
konsisten kata Kriteria Keberhasilan sumber M4.2 sendiri.

Jalur 200/403/404/retry-infra diuji di sini. Jalur 400 (loop revisi
penuh ke Query Engine, Checkpoint 6) diuji terpisah di
test_klasifikasi_respons_revisi.py - constraint/view_name di sini semua
diisi placeholder (None/tidak relevan) karena 400 TIDAK PERNAH terpicu
oleh skenario file ini.
"""

import uuid

import pytest

from src.layers.execution import klasifikasi_respons as modul
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.execution import HasilPemanggilanChatbotAPI
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="okupansi Bali bulan lalu",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_request() -> QueryEngineRequest:
    return QueryEngineRequest(
        domain=Domain.RESERVATION, view_name="v_reservation_room_type_daily", params={}
    )


@pytest.fixture(autouse=True)
def _tanpa_delay_nyata(monkeypatch):
    """time.sleep di-monkeypatch supaya test retry tidak benar-benar
    menunggu EXECUTION_RETRY_DELAY_DETIK tiap percobaan."""
    monkeypatch.setattr(modul.time, "sleep", lambda detik: None)


class _SpanRekam:
    """Mirror pola _SpanRekam/_TracerRekam di
    test_pemanggilan_chatbot_api.py (M4.1) - verifikasi atribut span
    in-process, TIDAK butuh Jaeger/Docker hidup."""

    def __init__(self):
        self.atribut: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, key, value):
        self.atribut[key] = value


class _TracerRekam:
    def __init__(self):
        self.span = _SpanRekam()

    def start_as_current_span(self, nama):
        return self.span


def _patch_tracer(monkeypatch) -> _TracerRekam:
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)
    return tracer_rekam


def _patch_raw(monkeypatch, urutan_hasil: list[HasilPemanggilanChatbotAPI]):
    """urutan_hasil dikonsumsi berurutan tiap kali _panggil_chatbot_api_raw
    dipanggil - kalau habis, ulangi elemen terakhir (dipakai skenario
    'gagal terus sampai batas')."""
    dipanggil = {"count": 0}

    def _fake_raw(request, role_title, employee_id):
        idx = min(dipanggil["count"], len(urutan_hasil) - 1)
        dipanggil["count"] += 1
        return urutan_hasil[idx]

    monkeypatch.setattr(modul, "_panggil_chatbot_api_raw", _fake_raw)
    return dipanggil


# --- 200 -> berhasil ------------------------------------------------------


def test_200_langsung_berhasil(monkeypatch):
    body = [{"property_id": "P01", "occupancy_rate": 0.75}]
    dipanggil = _patch_raw(monkeypatch, [HasilPemanggilanChatbotAPI(status_code=200, body=body)])
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(), "v_reservation_room_type_daily", _buat_request(),
        constraint=None, role_title="X", employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.nilai_hasil == body
    assert hasil.retry_count_infra == 0
    assert dipanggil["count"] == 1
    assert tracer_rekam.span.atribut["http.response.status_code"] == 200
    assert "error.type" not in tracer_rekam.span.atribut


def test_200_body_kosong_tetap_berhasil(monkeypatch):
    """Lihat decisions.md Keputusan 1: 0 baris legitimate tetap berhasil,
    bukan sebagian."""
    _patch_raw(monkeypatch, [HasilPemanggilanChatbotAPI(status_code=200, body=[])])
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(), "v_reservation_room_type_daily", _buat_request(),
        constraint=None, role_title="X", employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.nilai_hasil == []


# --- 403/404 -> eskalasi tanpa retry ---------------------------------------


@pytest.mark.parametrize("status_code", [403, 404])
def test_403_404_eskalasi_tanpa_retry(monkeypatch, status_code):
    dipanggil = _patch_raw(
        monkeypatch, [HasilPemanggilanChatbotAPI(status_code=status_code, body={"detail": "ditolak"})]
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(), "v_reservation_room_type_daily", _buat_request(),
        constraint=None, role_title="X", employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.bug_prioritas_tinggi is True
    assert hasil.kegagalan_alasan == f"eskalasi_{status_code}"
    assert dipanggil["count"] == 1  # bukti TANPA retry sama sekali
    assert tracer_rekam.span.atribut["error.type"] == "gagal_teknis"
    assert tracer_rekam.span.atribut["execution.bug_prioritas_tinggi"] is True


# --- 5xx/timeout -> retry infra ---------------------------------------------


def test_500_berturut_habis_batas_gagal_teknis(monkeypatch):
    dipanggil = _patch_raw(
        monkeypatch, [HasilPemanggilanChatbotAPI(status_code=500, body="error")]
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(), "v_reservation_room_type_daily", _buat_request(),
        constraint=None, role_title="X", employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "infra_exhausted_5xx"
    assert hasil.retry_count_infra == modul.EXECUTION_MAX_RETRY_INFRA
    assert dipanggil["count"] == 3  # EXECUTION_MAX_RETRY_INFRA(2) + 1 percobaan awal
    assert tracer_rekam.span.atribut["execution.retry_count_infra"] == 2


def test_timeout_berturut_habis_batas_gagal_teknis(monkeypatch):
    dipanggil = _patch_raw(
        monkeypatch, [HasilPemanggilanChatbotAPI(status_code=None, kegagalan_transport="timeout")]
    )
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(), "v_reservation_room_type_daily", _buat_request(),
        constraint=None, role_title="X", employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "infra_exhausted_timeout"
    assert dipanggil["count"] == 3


def test_500_lalu_sukses_percobaan_kedua_berhasil(monkeypatch):
    dipanggil = _patch_raw(
        monkeypatch,
        [
            HasilPemanggilanChatbotAPI(status_code=500, body="error"),
            HasilPemanggilanChatbotAPI(status_code=200, body=[{"a": 1}]),
        ],
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(), "v_reservation_room_type_daily", _buat_request(),
        constraint=None, role_title="X", employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.retry_count_infra == 1
    assert dipanggil["count"] == 2
    assert tracer_rekam.span.atribut["execution.retry_count_infra"] == 1
    assert tracer_rekam.span.atribut["http.response.status_code"] == 200
