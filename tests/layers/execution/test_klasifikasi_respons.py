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

Revisit (2026-08-17): `panggil_meta_chatbot_api` di-monkeypatch default
"tidak diketahui" (both None) di SELURUH test 200 di sini - skenario
SEBAGIAN dari sinyal _meta (flagged/stale) diuji terpisah di
test_klasifikasi_respons_kualitas_data.py, mirror pola pemisahan jalur
400 (test_klasifikasi_respons_revisi.py).
"""

import uuid

import pytest

from src.layers.execution import klasifikasi_respons as modul
from src.schemas.cakupan_individu import (
    AtomicIntentConstraint,
    ConstraintCakupanIndividu,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.execution import (
    HasilEksekusiAtomicIntent,
    HasilMetaChatbotAPI,
    HasilPemanggilanChatbotAPI,
)
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest


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


def _patch_meta_tidak_diketahui(monkeypatch):
    """Default untuk seluruh test di file ini - _meta "tidak diketahui"
    (both None), supaya status tetap BERHASIL murni dari jalur data
    utama, tidak tercampur skenario SEBAGIAN (diuji file terpisah)."""
    monkeypatch.setattr(
        modul,
        "panggil_meta_chatbot_api",
        lambda request, role_title, employee_id: HasilMetaChatbotAPI(status_code=200),
    )


# --- 200 -> berhasil ------------------------------------------------------


def test_200_langsung_berhasil(monkeypatch):
    body = [{"property_id": "P01", "occupancy_rate": 0.75}]
    dipanggil = _patch_raw(
        monkeypatch, [HasilPemanggilanChatbotAPI(status_code=200, body=body)]
    )
    _patch_meta_tidak_diketahui(monkeypatch)
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
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
    _patch_meta_tidak_diketahui(monkeypatch)
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.nilai_hasil == []


# --- 403/404 -> eskalasi tanpa retry ---------------------------------------


@pytest.mark.parametrize("status_code", [403, 404])
def test_403_404_eskalasi_tanpa_retry(monkeypatch, status_code):
    dipanggil = _patch_raw(
        monkeypatch,
        [
            HasilPemanggilanChatbotAPI(
                status_code=status_code, body={"detail": "ditolak"}
            )
        ],
    )
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
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
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kegagalan_alasan == "infra_exhausted_5xx"
    assert hasil.retry_count_infra == modul.EXECUTION_MAX_RETRY_INFRA
    assert dipanggil["count"] == 3  # EXECUTION_MAX_RETRY_INFRA(2) + 1 percobaan awal
    assert tracer_rekam.span.atribut["execution.retry_count_infra"] == 2


def test_timeout_berturut_habis_batas_gagal_teknis(monkeypatch):
    dipanggil = _patch_raw(
        monkeypatch,
        [HasilPemanggilanChatbotAPI(status_code=None, kegagalan_transport="timeout")],
    )
    _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
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
    _patch_meta_tidak_diketahui(monkeypatch)
    tracer_rekam = _patch_tracer(monkeypatch)

    hasil = modul.eksekusi_atomic_intent(
        _buat_atomic_intent(),
        "v_reservation_room_type_daily",
        _buat_request(),
        constraint=None,
        role_title="X",
        employee_id="E0001",
    )

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.retry_count_infra == 1
    assert dipanggil["count"] == 2
    assert tracer_rekam.span.atribut["execution.retry_count_infra"] == 1
    assert tracer_rekam.span.atribut["http.response.status_code"] == 200


# --- eksekusi_atomic_intent_semua() (Milestone 7.14) -----------------------


def _buat_hasil_vg(
    atomic_intent: AtomicIntent,
    lolos: bool = True,
    request: QueryEngineRequest | None = None,
) -> HasilVerifikasiGate:
    req = request or _buat_request()
    if not lolos:
        return HasilVerifikasiGate(
            request_final=None,
            lolos=False,
            terkoreksi=False,
            alasan_penolakan="fixture test",
        )
    return HasilVerifikasiGate(request_final=req, lolos=True, terkoreksi=False)


def _buat_constraint(
    atomic_intent: AtomicIntent, terdeteksi: bool = False
) -> AtomicIntentConstraint:
    return AtomicIntentConstraint(
        atomic_intent=atomic_intent,
        domain_decisions=[],
        constraint=ConstraintCakupanIndividu(
            terdeteksi=terdeteksi, alasan="fixture test" if terdeteksi else None
        ),
    )


def test_eksekusi_atomic_intent_semua_list_kosong_hasil_kosong():
    assert modul.eksekusi_atomic_intent_semua([], [], "X", "E0001") == []


def test_eksekusi_atomic_intent_semua_skip_lolos_false(monkeypatch):
    dipanggil = []
    monkeypatch.setattr(
        modul, "eksekusi_atomic_intent", lambda *a, **kw: dipanggil.append((a, kw))
    )

    a1 = _buat_atomic_intent()
    a2 = _buat_atomic_intent()
    wave = [
        (a1, _buat_hasil_vg(a1, lolos=False)),
        (a2, _buat_hasil_vg(a2, lolos=True)),
    ]
    cakupan = [_buat_constraint(a1), _buat_constraint(a2)]

    hasil = modul.eksekusi_atomic_intent_semua(
        wave, cakupan, "Front Office Staff", "E0001"
    )

    assert len(dipanggil) == 1
    assert dipanggil[0][0][0].atomic_intent_id == a2.atomic_intent_id
    assert len(hasil) == 1


def test_eksekusi_atomic_intent_semua_argumen_benar_per_item(monkeypatch):
    dipanggil = []

    def _spy(atomic_intent, view_name, request, constraint, role_title, employee_id):
        dipanggil.append(
            {
                "atomic_intent": atomic_intent,
                "view_name": view_name,
                "request": request,
                "constraint": constraint,
                "role_title": role_title,
                "employee_id": employee_id,
            }
        )
        return HasilEksekusiAtomicIntent(
            atomic_intent=atomic_intent,
            status=StatusEksekusi.BERHASIL,
            nilai_hasil=[{}],
        )

    monkeypatch.setattr(modul, "eksekusi_atomic_intent", _spy)

    a1 = _buat_atomic_intent()
    request1 = _buat_request()
    hasil_vg1 = _buat_hasil_vg(a1, lolos=True, request=request1)
    constraint1 = ConstraintCakupanIndividu(terdeteksi=True, alasan="fixture test")
    cakupan1 = AtomicIntentConstraint(
        atomic_intent=a1, domain_decisions=[], constraint=constraint1
    )

    hasil = modul.eksekusi_atomic_intent_semua(
        [(a1, hasil_vg1)], [cakupan1], "HR Staff", "E0071"
    )

    assert len(hasil) == 1
    assert dipanggil[0]["atomic_intent"].atomic_intent_id == a1.atomic_intent_id
    assert dipanggil[0]["view_name"] == request1.view_name
    assert dipanggil[0]["request"] is request1
    assert dipanggil[0]["constraint"] is constraint1
    assert dipanggil[0]["role_title"] == "HR Staff"
    assert dipanggil[0]["employee_id"] == "E0071"


def test_eksekusi_atomic_intent_semua_multi_item_constraint_tidak_tertukar(monkeypatch):
    """Dua atomic intent, urutan cakupan_individu_result SENGAJA dibalik
    dari urutan wave - memverifikasi pencocokan murni via atomic_intent_id,
    bukan kebetulan sejajar by index (mirror pola M7.13)."""
    dipanggil = []

    def _spy(atomic_intent, view_name, request, constraint, role_title, employee_id):
        dipanggil.append((atomic_intent.atomic_intent_id, constraint.terdeteksi))
        return HasilEksekusiAtomicIntent(
            atomic_intent=atomic_intent,
            status=StatusEksekusi.BERHASIL,
            nilai_hasil=[{}],
        )

    monkeypatch.setattr(modul, "eksekusi_atomic_intent", _spy)

    a1 = _buat_atomic_intent()
    a2 = _buat_atomic_intent()
    wave = [(a1, _buat_hasil_vg(a1)), (a2, _buat_hasil_vg(a2))]
    cakupan_dibalik = [
        _buat_constraint(a2, terdeteksi=True),
        _buat_constraint(a1, terdeteksi=False),
    ]

    modul.eksekusi_atomic_intent_semua(wave, cakupan_dibalik, "X", "E0001")

    hasil_by_id = dict(dipanggil)
    assert hasil_by_id[a1.atomic_intent_id] is False
    assert hasil_by_id[a2.atomic_intent_id] is True


def test_eksekusi_atomic_intent_semua_urutan_dan_panjang_dipertahankan(monkeypatch):
    monkeypatch.setattr(
        modul,
        "eksekusi_atomic_intent",
        lambda atomic_intent, *a, **kw: HasilEksekusiAtomicIntent(
            atomic_intent=atomic_intent,
            status=StatusEksekusi.BERHASIL,
            nilai_hasil=[{}],
        ),
    )

    a1, a2, a3 = _buat_atomic_intent(), _buat_atomic_intent(), _buat_atomic_intent()
    wave = [
        (a1, _buat_hasil_vg(a1, lolos=True)),
        (a2, _buat_hasil_vg(a2, lolos=False)),
        (a3, _buat_hasil_vg(a3, lolos=True)),
    ]
    cakupan = [_buat_constraint(a1), _buat_constraint(a2), _buat_constraint(a3)]

    hasil = modul.eksekusi_atomic_intent_semua(wave, cakupan, "X", "E0001")

    assert len(hasil) == 2
    assert [h.atomic_intent.atomic_intent_id for h in hasil] == [
        a1.atomic_intent_id,
        a3.atomic_intent_id,
    ]
