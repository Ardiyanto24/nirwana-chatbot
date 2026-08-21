"""Test src/main.py - Milestone 7.17: sambungan `POST /v1/turns` ke
proses_turn() + exception handler HTTP. Cakupan SEMPIT (mirror
tests/orchestration/test_turn_pipeline.py): hanya kejadian yang TIDAK
butuh LLM/DB/HTTP nyata (`proses_turn()` di-monkeypatch penuh).
Kejadian real HTTP+LLM+chatbot_api ada di
evals/7.17-membangun-endpoint-api/rancangan.md + audit.md.
"""

from fastapi.testclient import TestClient
from openai import APIError
from sqlalchemy.exc import SQLAlchemyError

import src.main as main_module
from src.main import _build_turn_response, app
from src.schemas.decomposition import DecompositionResult, KlasifikasiKebutuhan
from src.schemas.interpretation import DataVisualisasi, HasilNarasi, HasilVerifikasiNarasi
from src.schemas.orchestration import KeadaanTurn
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload

client = TestClient(app)

_PAYLOAD_RAW = {
    "session_id": "sess-test",
    "turn_index": 1,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Berapa occupancy bulan ini?",
}

_PAYLOAD_DUMMY = TurnPayload(**_PAYLOAD_RAW)

_DECOMPOSITION_DUMMY = DecompositionResult(
    klasifikasi=KlasifikasiKebutuhan.TUNGGAL,
    atomic_intents=[],
    verifikasi_valid=True,
    verifikasi_alasan=None,
    retry_count=0,
)


def _keadaan_turn_dummy(interpretation) -> KeadaanTurn:
    return KeadaanTurn(
        payload=_PAYLOAD_DUMMY,
        ketergantungan=TurnDependencyResult(is_dependent=False, referenced_turn_index=None),
        rewrite=RewriteResult(rewritten_question=_PAYLOAD_DUMMY.question),
        session_memory=None,
        decomposition=_DECOMPOSITION_DUMMY,
        matches=[],
        domain_gate=[],
        otorisasi=[],
        cakupan_individu=[],
        retriever=[],
        query_engine=[],
        verification_gate=[],
        execution=[],
        paket_narasi=[],
        interpretation=interpretation,
        invoke_agent_trace_id="0123456789abcdef0123456789abcdef",
        invoke_agent_span_id="0123456789abcdef",
    )


_VISUALISASI_DUMMY = [
    DataVisualisasi(
        atomic_intent_id="ai-1",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_tunggal=78.5,
        deret=None,
    )
]

_INTERPRETATION_LOLOS = (
    HasilNarasi(narasi="Occupancy bulan ini 78.5%."),
    HasilVerifikasiNarasi(
        narasi="Occupancy bulan ini 78.5%.",
        status=StatusEksekusi.BERHASIL,
        lolos=True,
        alasan=None,
    ),
    _VISUALISASI_DUMMY,
)

_INTERPRETATION_TIDAK_LOLOS = (
    HasilNarasi(narasi="narasi mengandung klaim tidak berdasar data"),
    HasilVerifikasiNarasi(
        narasi="narasi mengandung klaim tidak berdasar data",
        status=StatusEksekusi.BERHASIL,
        lolos=False,
        alasan="klaim sebab-akibat tidak didukung data yang diambil",
    ),
    None,
)

_INTERPRETATION_GAGAL_TEKNIS = (
    HasilNarasi(narasi="narasi yang tidak sempat diverifikasi"),
    HasilVerifikasiNarasi(
        narasi="narasi yang tidak sempat diverifikasi",
        status=StatusEksekusi.GAGAL_TEKNIS,
        lolos=None,
        alasan=None,
    ),
    None,
)


# --- _build_turn_response() ---


def test_build_turn_response_lolos_true_narasi_asli_dan_visualisasi_ada():
    hasil = _build_turn_response(_keadaan_turn_dummy(_INTERPRETATION_LOLOS))
    assert hasil.narasi == "Occupancy bulan ini 78.5%."
    assert hasil.terverifikasi is True
    assert hasil.catatan_verifikasi is None
    assert hasil.visualisasi == _VISUALISASI_DUMMY
    assert hasil.session_id == "sess-test"
    assert hasil.turn_index == 1


def test_build_turn_response_lolos_false_narasi_diganti_generik():
    hasil = _build_turn_response(_keadaan_turn_dummy(_INTERPRETATION_TIDAK_LOLOS))
    assert hasil.narasi == main_module._PESAN_NARASI_BELUM_TERVERIFIKASI
    assert hasil.terverifikasi is False
    assert hasil.catatan_verifikasi == "klaim sebab-akibat tidak didukung data yang diambil"
    assert hasil.visualisasi is None
    # narasi asli (berpotensi mengandung klaim tidak berdasar) TIDAK boleh bocor
    assert "klaim tidak berdasar" not in hasil.narasi


def test_build_turn_response_gagal_teknis_diperlakukan_sama_seperti_lolos_false():
    hasil = _build_turn_response(_keadaan_turn_dummy(_INTERPRETATION_GAGAL_TEKNIS))
    assert hasil.narasi == main_module._PESAN_NARASI_BELUM_TERVERIFIKASI
    assert hasil.terverifikasi is False
    assert hasil.catatan_verifikasi == main_module._PESAN_VERIFIKASI_GAGAL_TEKNIS
    assert hasil.visualisasi is None


# --- endpoint sukses ---


def test_endpoint_sukses_mengembalikan_turn_response(monkeypatch):
    monkeypatch.setattr(
        main_module, "proses_turn", lambda payload: _keadaan_turn_dummy(_INTERPRETATION_LOLOS)
    )
    # simpan_riwayat_turn (M7.18) di-mock supaya test ini TIDAK menulis ke
    # DB nyata - file ini murni deterministik (lihat docstring modul).
    monkeypatch.setattr(main_module, "simpan_riwayat_turn", lambda **kwargs: None)
    response = client.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 200
    body = response.json()
    assert body["narasi"] == "Occupancy bulan ini 78.5%."
    assert body["terverifikasi"] is True
    assert body["visualisasi"][0]["nilai_tunggal"] == 78.5


# --- pemetaan exception handler (defense-in-depth: pesan asli tidak bocor) ---


def test_endpoint_openai_apierror_dipetakan_503(monkeypatch):
    def _raise(payload):
        raise APIError("pesan internal openai seharusnya tidak bocor", request=None, body=None)

    monkeypatch.setattr(main_module, "proses_turn", _raise)
    response = client.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 503
    assert "pesan internal openai" not in response.text
    assert response.json()["detail"] == main_module._PESAN_LLM_TIDAK_TERSEDIA


def test_endpoint_sqlalchemy_error_dipetakan_500(monkeypatch):
    def _raise(payload):
        raise SQLAlchemyError("detail koneksi database seharusnya tidak bocor")

    monkeypatch.setattr(main_module, "proses_turn", _raise)
    response = client.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 500
    assert "detail koneksi database" not in response.text
    assert response.json()["detail"] == main_module._PESAN_KESALAHAN_INTERNAL


def test_endpoint_runtime_error_dipetakan_500(monkeypatch):
    def _raise(payload):
        raise RuntimeError("DATABASE_URL belum di-set seharusnya tidak bocor")

    monkeypatch.setattr(main_module, "proses_turn", _raise)
    response = client.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 500
    assert "DATABASE_URL" not in response.text
    assert response.json()["detail"] == main_module._PESAN_KESALAHAN_INTERNAL


def test_endpoint_exception_generik_dipetakan_500_catch_all(monkeypatch):
    # Simulasi celah laten (IndexError/KeyError, docs/keterbatasan-diterima.md #17).
    # `Exception` bawaan ditangani ServerErrorMiddleware (bukan ExceptionMiddleware
    # seperti tipe spesifik lain) - Starlette SELALU re-raise exception setelah
    # membangun response (by design, supaya ASGI server produksi tetap bisa
    # mencatat error meski response sudah terkirim ke client) - TestClient default
    # (`raise_server_exceptions=True`) meneruskan re-raise itu sebagai kegagalan
    # test, jadi klien khusus `raise_server_exceptions=False` dipakai DI SINI SAJA
    # untuk membaca response yang genuinely terkirim, bukan exception Python-nya.
    def _raise(payload):
        raise IndexError("list index out of range seharusnya tidak bocor")

    monkeypatch.setattr(main_module, "proses_turn", _raise)
    client_tanpa_reraise = TestClient(app, raise_server_exceptions=False)
    response = client_tanpa_reraise.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 500
    assert "list index out of range" not in response.text
    assert response.json()["detail"] == main_module._PESAN_KESALAHAN_INTERNAL


def test_endpoint_payload_invalid_tetap_422_bukan_ditelan_catch_all():
    # ValidationError WAJIB tetap 422 (kontrak M1.2) - proses_turn() TIDAK
    # di-mock (validasi adalah langkah PERTAMA proses_turn(), terjadi sebelum
    # LLM/DB/HTTP apa pun disentuh), membuktikan handler lebih spesifik
    # menang atas catch-all Exception, bukan malah jadi 500.
    response = client.post("/v1/turns", json={"session_id": "sess-test"})
    assert response.status_code == 422


# --- riwayat percakapan (M7.18) ---


def test_endpoint_tetap_200_walau_simpan_riwayat_gagal(monkeypatch):
    # KK2 M7.18 literal, dibuktikan deterministik di titik paling kritis:
    # kegagalan menulis riwayat TIDAK BOLEH menggagalkan response ke user.
    monkeypatch.setattr(
        main_module, "proses_turn", lambda payload: _keadaan_turn_dummy(_INTERPRETATION_LOLOS)
    )

    def _simpan_gagal(**kwargs):
        raise RuntimeError("simulasi penyimpanan riwayat tidak terjangkau")

    monkeypatch.setattr(main_module, "simpan_riwayat_turn", _simpan_gagal)

    response = client.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 200
    body = response.json()
    assert body["narasi"] == "Occupancy bulan ini 78.5%."
    assert body["terverifikasi"] is True


def test_simpan_riwayat_dipanggil_dengan_argumen_benar(monkeypatch):
    monkeypatch.setattr(
        main_module, "proses_turn", lambda payload: _keadaan_turn_dummy(_INTERPRETATION_LOLOS)
    )
    panggilan = {}

    def _rekam(**kwargs):
        panggilan.update(kwargs)

    monkeypatch.setattr(main_module, "simpan_riwayat_turn", _rekam)

    response = client.post("/v1/turns", json=_PAYLOAD_RAW)
    assert response.status_code == 200
    assert panggilan["session_id"] == "sess-test"
    assert panggilan["turn_index"] == 1
    assert panggilan["pertanyaan"] == "Berapa occupancy bulan ini?"
    assert panggilan["narasi"] == "Occupancy bulan ini 78.5%."
    assert panggilan["status"] == "tidak_ada_kebutuhan"  # paket_narasi=[] pada dummy
