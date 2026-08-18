"""Test orkestrator Query Engine (Milestone 7.4) -
src/layers/query_engine/query_engine.py. Checkpoint 2: unit test dasar
(mocked, tanpa LLM sungguhan) untuk wiring/short-circuit.
"""

import uuid

import src.layers.query_engine.query_engine as query_engine_module
from src.layers.query_engine.query_engine import susun_dan_verifikasi_request_atomic_intent
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest

_VIEW = "v_reservation_room_type_daily"
_VIEW_LAIN = "v_reservation_channel_daily"


def _buat_atomic_intent(
    teks: str = "okupansi Bali bulan lalu",
    label: LabelBentukJawaban = LabelBentukJawaban.NILAI_TUNGGAL,
) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=label,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_request(view_name: str = _VIEW) -> QueryEngineRequest:
    return QueryEngineRequest(domain=Domain.RESERVATION, view_name=view_name, params={"property_id": "P01"})


# --- Checkpoint 2: unit test dasar (mocked, tanpa LLM sungguhan) --------


def test_short_circuit_susun_gagal_verifikasi_tidak_dipanggil(monkeypatch):
    """Susun gagal (GAGAL_TEKNIS, request=None) -> return (hasil_susun,
    None), verifikasi_bentuk_request_atomic_intent TIDAK dipanggil sama
    sekali (decisions.md Keputusan 5)."""
    atomic_intent = _buat_atomic_intent()
    hasil_gagal = HasilPenyusunanRequest(
        atomic_intent=atomic_intent, request=None, status=StatusEksekusi.GAGAL_TEKNIS
    )

    monkeypatch.setattr(
        query_engine_module, "susun_request_atomic_intent", lambda *a, **kw: hasil_gagal
    )

    def _gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "verifikasi_bentuk_request_atomic_intent TIDAK BOLEH terpanggil saat susun gagal"
        )

    monkeypatch.setattr(
        query_engine_module, "verifikasi_bentuk_request_atomic_intent", _gagal_kalau_terpanggil
    )

    hasil_susun, hasil_verifikasi = susun_dan_verifikasi_request_atomic_intent(
        atomic_intent, _VIEW
    )

    assert hasil_susun is hasil_gagal
    assert hasil_verifikasi is None


def test_happy_path_request_diteruskan_identik_ke_verifikasi(monkeypatch):
    """Susun berhasil -> verifikasi dipanggil dengan objek `request` PERSIS
    (identity) dari return Susun, bukan rekonstruksi."""
    atomic_intent = _buat_atomic_intent()
    request = _buat_request(_VIEW)
    hasil_susun_sukses = HasilPenyusunanRequest(
        atomic_intent=atomic_intent, request=request, status=StatusEksekusi.BERHASIL
    )
    hasil_verifikasi_sukses = HasilVerifikasiBentukRequest(
        atomic_intent=atomic_intent,
        request=request,
        status=StatusEksekusi.BERHASIL,
        lolos=True,
        alasan=None,
    )

    monkeypatch.setattr(
        query_engine_module, "susun_request_atomic_intent", lambda *a, **kw: hasil_susun_sukses
    )

    diterima = {}

    def _rekam_verifikasi(ai, view_name_tervalidasi_retriever, req):
        diterima["request"] = req
        diterima["view_name_tervalidasi_retriever"] = view_name_tervalidasi_retriever
        return hasil_verifikasi_sukses

    monkeypatch.setattr(
        query_engine_module, "verifikasi_bentuk_request_atomic_intent", _rekam_verifikasi
    )

    hasil_susun, hasil_verifikasi = susun_dan_verifikasi_request_atomic_intent(
        atomic_intent, _VIEW
    )

    assert diterima["request"] is request  # identity, bukan rekonstruksi
    assert hasil_susun is hasil_susun_sukses
    assert hasil_verifikasi is hasil_verifikasi_sukses


def test_view_name_tervalidasi_retriever_default_ke_view_name(monkeypatch):
    """Kalau view_name_tervalidasi_retriever tidak diisi, default ke
    view_name (decisions.md Keputusan 3) - perilaku ini mempertahankan
    satu-satunya caller nyata yang ada (_revisi_request, M4.2)."""
    atomic_intent = _buat_atomic_intent()
    request = _buat_request(_VIEW)
    hasil_susun_sukses = HasilPenyusunanRequest(
        atomic_intent=atomic_intent, request=request, status=StatusEksekusi.BERHASIL
    )

    monkeypatch.setattr(
        query_engine_module, "susun_request_atomic_intent", lambda *a, **kw: hasil_susun_sukses
    )

    diterima = {}

    def _rekam_verifikasi(ai, view_name_tervalidasi_retriever, req):
        diterima["view_name_tervalidasi_retriever"] = view_name_tervalidasi_retriever
        return None

    monkeypatch.setattr(
        query_engine_module, "verifikasi_bentuk_request_atomic_intent", _rekam_verifikasi
    )

    susun_dan_verifikasi_request_atomic_intent(atomic_intent, _VIEW)

    assert diterima["view_name_tervalidasi_retriever"] == _VIEW


def test_view_name_tervalidasi_retriever_eksplisit_berbeda_diteruskan(monkeypatch):
    """Kalau view_name_tervalidasi_retriever diisi eksplisit berbeda dari
    view_name, nilai itu (bukan view_name) yang diteruskan ke verifikasi -
    prasyarat skenario mismatch KK M7.4 (Checkpoint 3)."""
    atomic_intent = _buat_atomic_intent()
    request = _buat_request(_VIEW)
    hasil_susun_sukses = HasilPenyusunanRequest(
        atomic_intent=atomic_intent, request=request, status=StatusEksekusi.BERHASIL
    )

    monkeypatch.setattr(
        query_engine_module, "susun_request_atomic_intent", lambda *a, **kw: hasil_susun_sukses
    )

    diterima = {}

    def _rekam_verifikasi(ai, view_name_tervalidasi_retriever, req):
        diterima["view_name_tervalidasi_retriever"] = view_name_tervalidasi_retriever
        return None

    monkeypatch.setattr(
        query_engine_module, "verifikasi_bentuk_request_atomic_intent", _rekam_verifikasi
    )

    susun_dan_verifikasi_request_atomic_intent(
        atomic_intent, _VIEW, view_name_tervalidasi_retriever=_VIEW_LAIN
    )

    assert diterima["view_name_tervalidasi_retriever"] == _VIEW_LAIN
