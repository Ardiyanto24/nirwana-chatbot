"""Test suite jalur revisi 400 (Milestone 4.2, Checkpoint 6) -
src/layers/execution/klasifikasi_respons.py `_revisi_request()` +
integrasinya di `eksekusi_atomic_intent()`. `susun_request_atomic_intent`
(M3.4), `verifikasi_bentuk_request_atomic_intent` (M3.5), `verifikasi_gate`
(M2.4) SEMUA di-monkeypatch langsung - modul ini TIDAK menyentuh LLM/HTTP
sama sekali, murni orkestrasi. Real testing ke chatbot_api sungguhan
DITUNDA (Checkpoint 7, decisions.md Keputusan 4).

Dipisah dari test_klasifikasi_respons.py (jalur 200/403/404/retry-infra)
- mirror preseden pemisahan file test per-kelompok-skenario di project ini
(mis. test_kecukupan_struktural.py vs *_schema.py, M3.3).
"""

import uuid

import pytest

from src.layers.execution import klasifikasi_respons as modul
from src.schemas.cakupan_individu import ConstraintCakupanIndividu
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.execution import HasilPemanggilanChatbotAPI
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest

_VIEW = "v_reservation_room_type_daily"


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="okupansi Bali bulan lalu",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_request(params: dict | None = None) -> QueryEngineRequest:
    return QueryEngineRequest(domain=Domain.RESERVATION, view_name=_VIEW, params=params or {})


_CONSTRAINT_TIDAK_TERDETEKSI = ConstraintCakupanIndividu(terdeteksi=False)


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


def _patch_raw(monkeypatch, urutan_hasil: list[HasilPemanggilanChatbotAPI]):
    dipanggil = {"count": 0}

    def _fake_raw(request, role_title, employee_id):
        idx = min(dipanggil["count"], len(urutan_hasil) - 1)
        dipanggil["count"] += 1
        return urutan_hasil[idx]

    monkeypatch.setattr(modul, "_panggil_chatbot_api_raw", _fake_raw)
    return dipanggil


# --- revisi berhasil di percobaan ke-2 -------------------------------------


def test_400_lalu_200_di_revisi_kedua_berhasil(monkeypatch):
    ai = _buat_atomic_intent()
    request_baru = _buat_request({"property_id": "P01"})

    dipanggil_http = _patch_raw(
        monkeypatch,
        [
            HasilPemanggilanChatbotAPI(status_code=400, body={"detail": "property_id salah bentuk"}),
            HasilPemanggilanChatbotAPI(status_code=200, body=[{"a": 1}]),
        ],
    )
    dipanggil_susun = {"count": 0, "feedback": None}

    def _fake_susun(atomic_intent, view_name, feedback=None):
        dipanggil_susun["count"] += 1
        dipanggil_susun["feedback"] = feedback
        return HasilPenyusunanRequest(atomic_intent=ai, request=request_baru, status=StatusEksekusi.BERHASIL)

    monkeypatch.setattr(modul, "susun_request_atomic_intent", _fake_susun)
    monkeypatch.setattr(
        modul,
        "verifikasi_bentuk_request_atomic_intent",
        lambda atomic_intent, view_name, request: HasilVerifikasiBentukRequest(
            atomic_intent=ai, request=request, status=StatusEksekusi.BERHASIL, lolos=True, alasan=None
        ),
    )
    monkeypatch.setattr(
        modul,
        "verifikasi_gate",
        lambda request, constraint, employee_id, view_name_tervalidasi_retriever: HasilVerifikasiGate(
            request_final=request, lolos=True, terkoreksi=False
        ),
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        ai, _VIEW, _buat_request(), _CONSTRAINT_TIDAK_TERDETEKSI, role_title="X", employee_id="E0001"
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.revisi_count == 1
    assert dipanggil_http["count"] == 2
    assert dipanggil_susun["count"] == 1
    assert dipanggil_susun["feedback"] == "property_id salah bentuk"
    assert tracer_rekam.span.atribut["execution.revisi_count"] == 1


# --- revisi gagal di M3.4 (susun_request_atomic_intent) --------------------


def test_revisi_gagal_susun_gagal_teknis(monkeypatch):
    ai = _buat_atomic_intent()
    _patch_raw(monkeypatch, [HasilPemanggilanChatbotAPI(status_code=400, body={"detail": "x"})])

    monkeypatch.setattr(
        modul,
        "susun_request_atomic_intent",
        lambda atomic_intent, view_name, feedback=None: HasilPenyusunanRequest(
            atomic_intent=ai, request=None, status=StatusEksekusi.GAGAL_TEKNIS
        ),
    )
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        ai, _VIEW, _buat_request(), _CONSTRAINT_TIDAK_TERDETEKSI, role_title="X", employee_id="E0001"
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "revisi_gagal_susun"


# --- revisi gagal di M3.5 (verifikasi_bentuk_request_atomic_intent) --------


def test_revisi_gagal_verifikasi_bentuk_gagal_teknis(monkeypatch):
    ai = _buat_atomic_intent()
    request_baru = _buat_request()
    _patch_raw(monkeypatch, [HasilPemanggilanChatbotAPI(status_code=400, body={"detail": "x"})])

    monkeypatch.setattr(
        modul,
        "susun_request_atomic_intent",
        lambda atomic_intent, view_name, feedback=None: HasilPenyusunanRequest(
            atomic_intent=ai, request=request_baru, status=StatusEksekusi.BERHASIL
        ),
    )
    monkeypatch.setattr(
        modul,
        "verifikasi_bentuk_request_atomic_intent",
        lambda atomic_intent, view_name, request: HasilVerifikasiBentukRequest(
            atomic_intent=ai,
            request=request,
            status=StatusEksekusi.BERHASIL,
            lolos=False,
            alasan="view_name tidak sesuai retriever",
        ),
    )
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        ai, _VIEW, _buat_request(), _CONSTRAINT_TIDAK_TERDETEKSI, role_title="X", employee_id="E0001"
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "revisi_gagal_verifikasi_bentuk"


# --- revisi gagal di M2.4 (verifikasi_gate) ---------------------------------


def test_revisi_gagal_verification_gate_gagal_teknis(monkeypatch):
    ai = _buat_atomic_intent()
    request_baru = _buat_request()
    _patch_raw(monkeypatch, [HasilPemanggilanChatbotAPI(status_code=400, body={"detail": "x"})])

    monkeypatch.setattr(
        modul,
        "susun_request_atomic_intent",
        lambda atomic_intent, view_name, feedback=None: HasilPenyusunanRequest(
            atomic_intent=ai, request=request_baru, status=StatusEksekusi.BERHASIL
        ),
    )
    monkeypatch.setattr(
        modul,
        "verifikasi_bentuk_request_atomic_intent",
        lambda atomic_intent, view_name, request: HasilVerifikasiBentukRequest(
            atomic_intent=ai, request=request, status=StatusEksekusi.BERHASIL, lolos=True, alasan=None
        ),
    )
    monkeypatch.setattr(
        modul,
        "verifikasi_gate",
        lambda request, constraint, employee_id, view_name_tervalidasi_retriever: HasilVerifikasiGate(
            request_final=None, lolos=False, terkoreksi=False, alasan_penolakan="constraint gagal"
        ),
    )
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        ai, _VIEW, _buat_request(), _CONSTRAINT_TIDAK_TERDETEKSI, role_title="X", employee_id="E0001"
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "revisi_gagal_verification_gate"


# --- 400 berulang sampai batas revisi habis ---------------------------------


def test_400_berulang_sampai_batas_revisi_habis(monkeypatch):
    ai = _buat_atomic_intent()
    request_baru = _buat_request()
    dipanggil_http = _patch_raw(
        monkeypatch, [HasilPemanggilanChatbotAPI(status_code=400, body={"detail": "selalu salah"})]
    )
    dipanggil_susun = {"count": 0}

    def _fake_susun(atomic_intent, view_name, feedback=None):
        dipanggil_susun["count"] += 1
        return HasilPenyusunanRequest(atomic_intent=ai, request=request_baru, status=StatusEksekusi.BERHASIL)

    monkeypatch.setattr(modul, "susun_request_atomic_intent", _fake_susun)
    monkeypatch.setattr(
        modul,
        "verifikasi_bentuk_request_atomic_intent",
        lambda atomic_intent, view_name, request: HasilVerifikasiBentukRequest(
            atomic_intent=ai, request=request, status=StatusEksekusi.BERHASIL, lolos=True, alasan=None
        ),
    )
    monkeypatch.setattr(
        modul,
        "verifikasi_gate",
        lambda request, constraint, employee_id, view_name_tervalidasi_retriever: HasilVerifikasiGate(
            request_final=request, lolos=True, terkoreksi=False
        ),
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        ai, _VIEW, _buat_request(), _CONSTRAINT_TIDAK_TERDETEKSI, role_title="X", employee_id="E0001"
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "revisi_exhausted"
    # EXECUTION_MAX_REVISI percobaan chatbot_api total (1 awal + hingga N-1 revisi)
    assert dipanggil_http["count"] == modul.EXECUTION_MAX_REVISI
    # revisi (susun_request_atomic_intent) dipanggil EXECUTION_MAX_REVISI - 1 kali
    assert dipanggil_susun["count"] == modul.EXECUTION_MAX_REVISI - 1
    assert tracer_rekam.span.atribut["execution.revisi_count"] == modul.EXECUTION_MAX_REVISI - 1
