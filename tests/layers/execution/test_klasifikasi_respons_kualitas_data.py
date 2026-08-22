"""Test suite jalur SEBAGIAN dari sinyal kualitas data (Milestone 4.2
Revisit, 2026-08-17, decisions.md Keputusan 11) -
src/layers/execution/klasifikasi_respons.py `_tentukan_kualitas_data()`
+ integrasinya di `eksekusi_atomic_intent()`. `panggil_meta_chatbot_api`
di-monkeypatch langsung - modul ini TIDAK menyentuh HTTP.

Dipisah dari test_klasifikasi_respons.py (jalur 200/403/404/retry-infra,
yang men-default-kan _meta ke "tidak diketahui") - mirror pola pemisahan
test_klasifikasi_respons_revisi.py untuk jalur 400.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.layers.execution import klasifikasi_respons as modul
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.execution import HasilMetaChatbotAPI, HasilPemanggilanChatbotAPI
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
    monkeypatch.setattr(modul.time, "sleep", lambda detik: None)


class _SpanRekam:
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


def _patch_raw_200(monkeypatch, body=None):
    monkeypatch.setattr(
        modul,
        "_panggil_chatbot_api_raw",
        lambda request, role_title, employee_id: HasilPemanggilanChatbotAPI(
            status_code=200, body=body if body is not None else [{"a": 1}]
        ),
    )


def _patch_meta(monkeypatch, hasil: HasilMetaChatbotAPI):
    dipanggil = {"count": 0}

    def _fake_meta(request, role_title, employee_id):
        dipanggil["count"] += 1
        return hasil

    monkeypatch.setattr(modul, "panggil_meta_chatbot_api", _fake_meta)
    return dipanggil


def _eksekusi(monkeypatch):
    return modul.eksekusi_atomic_intent(
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
    )


_WAKTU_STALE = "2020-01-01T00:00:00+00:00"


def _waktu_segar() -> str:
    return datetime.now(UTC).isoformat()


# --- data_quality_status="flagged" -----------------------------------------


def test_flagged_menghasilkan_sebagian(monkeypatch):
    _patch_raw_200(monkeypatch)
    _patch_meta(
        monkeypatch, HasilMetaChatbotAPI(status_code=200, data_quality_status="flagged")
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.data_quality_status == "flagged"
    assert hasil.nilai_hasil == [{"a": 1}]
    assert hasil.kegagalan_alasan is None
    assert hasil.bug_prioritas_tinggi is False
    assert tracer_rekam.span.atribut["error.type"] == "sebagian"
    assert (
        tracer_rekam.span.atribut["execution.alasan_sebagian"] == "data_quality_flagged"
    )
    assert tracer_rekam.span.atribut["execution.data_quality_status"] == "flagged"


# --- last_refreshed_at basi --------------------------------------------


def test_last_refreshed_at_basi_menghasilkan_sebagian(monkeypatch):
    _patch_raw_200(monkeypatch)
    _patch_meta(
        monkeypatch,
        HasilMetaChatbotAPI(
            status_code=200, data_quality_status="ok", last_refreshed_at=_WAKTU_STALE
        ),
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.last_refreshed_at == _WAKTU_STALE
    assert tracer_rekam.span.atribut["execution.alasan_sebagian"] == "data_stale"


def test_last_refreshed_at_segar_tetap_berhasil(monkeypatch):
    _patch_raw_200(monkeypatch)
    waktu_segar = _waktu_segar()
    _patch_meta(
        monkeypatch,
        HasilMetaChatbotAPI(
            status_code=200, data_quality_status="ok", last_refreshed_at=waktu_segar
        ),
    )
    _patch_tracer(monkeypatch)

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.last_refreshed_at == waktu_segar


def test_flagged_dan_stale_sekaligus_tetap_sebagian_tidak_dobel(monkeypatch):
    _patch_raw_200(monkeypatch)
    _patch_meta(
        monkeypatch,
        HasilMetaChatbotAPI(
            status_code=200,
            data_quality_status="flagged",
            last_refreshed_at=_WAKTU_STALE,
        ),
    )

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.SEBAGIAN


# --- null / kegagalan _meta -> TETAP berhasil -------------------------------


def test_data_quality_status_null_tetap_berhasil(monkeypatch):
    _patch_raw_200(monkeypatch)
    _patch_meta(monkeypatch, HasilMetaChatbotAPI(status_code=200))
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.data_quality_status is None
    assert "execution.alasan_sebagian" not in tracer_rekam.span.atribut


def test_panggilan_meta_gagal_tetap_berhasil_tanpa_retry(monkeypatch):
    _patch_raw_200(monkeypatch)
    dipanggil_meta = _patch_meta(
        monkeypatch,
        HasilMetaChatbotAPI(status_code=None, kegagalan_transport="timeout"),
    )

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.retry_count_infra == 0  # kegagalan _meta TIDAK ikut retry infra
    assert dipanggil_meta["count"] == 1  # SATU percobaan saja, tanpa retry


def test_last_refreshed_at_format_tak_terduga_tidak_dianggap_basi(monkeypatch):
    """_data_basi() gagal parse -> False, bukan exception - format tak
    terduga BUKAN sinyal kualitas data, murni ketidaktahuan."""
    _patch_raw_200(monkeypatch)
    _patch_meta(
        monkeypatch,
        HasilMetaChatbotAPI(
            status_code=200, last_refreshed_at="bukan-format-tanggal-valid"
        ),
    )

    hasil = _eksekusi(monkeypatch)

    assert hasil.status == StatusEksekusi.BERHASIL


# --- _data_basi() dan _tentukan_kualitas_data() (unit langsung) -------------


def test_data_basi_true_untuk_waktu_lampau():
    assert modul._data_basi(_WAKTU_STALE) is True


def test_data_basi_false_untuk_waktu_segar():
    assert modul._data_basi(_waktu_segar()) is False


def test_data_basi_tepat_di_ambang_belum_basi():
    waktu = (
        datetime.now(UTC)
        - timedelta(hours=modul.EXECUTION_DATA_STALENESS_THRESHOLD_JAM - 1)
    ).isoformat()
    assert modul._data_basi(waktu) is False


def test_tentukan_kualitas_data_keduanya_none_berhasil():
    status, alasan = modul._tentukan_kualitas_data(None, None)
    assert status == StatusEksekusi.BERHASIL
    assert alasan is None
