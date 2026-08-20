"""Test suite Input Layer (Milestone 1.2, skema direvisi Milestone 1.3) — lewat
endpoint HTTP sungguhan (`TestClient`), membuktikan Kriteria Keberhasilan sumber:
- Field wajib hilang selalu ditolak dengan pesan menyebut field spesifik.
- `turn_index=1` (tanpa histori) dan `turn_index>1` (dengan histori) sama-sama
  diterima tanpa memperlakukan salah satunya sebagai kondisi khusus terlewat.

Sejak Milestone 7.17, `POST /v1/turns` menjalankan pipeline penuh (bukan
echo payload M1.2) - test PENERIMAAN (200) di bawah meng-monkeypatch
`proses_turn()` supaya tetap deterministik/tanpa LLM nyata, verifikasi
KK Input Layer tetap valid: payload lolos validasi (tidak 422) untuk
ketiga kedalaman histori. Test PENOLAKAN (422) TIDAK berubah - validasi
terjadi di langkah pertama `proses_turn()`, sebelum pipeline lain jalan.
"""

import pytest
from fastapi.testclient import TestClient

import src.main as main_module
from src.main import app
from src.schemas.decomposition import DecompositionResult, KlasifikasiKebutuhan
from src.schemas.interpretation import HasilNarasi, HasilVerifikasiNarasi
from src.schemas.orchestration import KeadaanTurn
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import StatusEksekusi
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload

client = TestClient(app)

_INTERPRETATION_DUMMY = (
    HasilNarasi(narasi="narasi dummy"),
    HasilVerifikasiNarasi(narasi="narasi dummy", status=StatusEksekusi.BERHASIL, lolos=True, alasan=None),
    None,
)


def _keadaan_turn_dummy(raw: dict) -> KeadaanTurn:
    payload = TurnPayload(**raw)
    return KeadaanTurn(
        payload=payload,
        ketergantungan=TurnDependencyResult(is_dependent=False, referenced_turn_index=None),
        rewrite=RewriteResult(rewritten_question=payload.question),
        session_memory=None,
        decomposition=DecompositionResult(
            klasifikasi=KlasifikasiKebutuhan.TUNGGAL,
            atomic_intents=[],
            verifikasi_valid=True,
            verifikasi_alasan=None,
            retry_count=0,
        ),
        matches=[],
        domain_gate=[],
        otorisasi=[],
        cakupan_individu=[],
        retriever=[],
        query_engine=[],
        verification_gate=[],
        execution=[],
        paket_narasi=[],
        interpretation=_INTERPRETATION_DUMMY,
    )

VALID_PAYLOAD_TURN1 = {
    "session_id": "sess-test",
    "turn_index": 1,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Berapa occupancy bulan ini?",
}

VALID_PAYLOAD_TURN2 = {
    "session_id": "sess-test",
    "turn_index": 2,
    "role_title": "Revenue Manager",
    "employee_id": "emp-2",
    "question": "Bandingkan dengan bulan lalu",
    "history": [
        {"turn_index": 1, "question": "Berapa occupancy April?", "answer": "78%"}
    ],
}

VALID_PAYLOAD_TURN3 = {
    "session_id": "sess-test",
    "turn_index": 3,
    "role_title": "General Manager",
    "employee_id": "emp-3",
    "question": "Bagaimana dengan spa?",
    "history": [
        {"turn_index": 1, "question": "Berapa occupancy April?", "answer": "78%"},
        {"turn_index": 2, "question": "Bandingkan dengan bulan lalu", "answer": "Naik 5%"},
    ],
}

REQUIRED_FIELDS = ["session_id", "turn_index", "role_title", "employee_id", "question"]


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_missing_required_field_rejected_with_specific_message(missing_field):
    payload = {k: v for k, v in VALID_PAYLOAD_TURN1.items() if k != missing_field}
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(missing_field in err["loc"] for err in errors), (
        f"pesan error tidak menyebut field '{missing_field}' secara spesifik: {errors}"
    )


def test_turn_index_1_without_history_accepted(monkeypatch):
    monkeypatch.setattr(
        main_module, "proses_turn", lambda raw: _keadaan_turn_dummy(VALID_PAYLOAD_TURN1)
    )
    response = client.post("/v1/turns", json=VALID_PAYLOAD_TURN1)
    assert response.status_code == 200
    assert response.json()["session_id"] == VALID_PAYLOAD_TURN1["session_id"]


def test_turn_index_2_with_history_accepted(monkeypatch):
    monkeypatch.setattr(
        main_module, "proses_turn", lambda raw: _keadaan_turn_dummy(VALID_PAYLOAD_TURN2)
    )
    response = client.post("/v1/turns", json=VALID_PAYLOAD_TURN2)
    assert response.status_code == 200
    assert response.json()["turn_index"] == 2


def test_turn_index_3_with_full_multi_turn_history_accepted(monkeypatch):
    monkeypatch.setattr(
        main_module, "proses_turn", lambda raw: _keadaan_turn_dummy(VALID_PAYLOAD_TURN3)
    )
    response = client.post("/v1/turns", json=VALID_PAYLOAD_TURN3)
    assert response.status_code == 200
    assert response.json()["turn_index"] == 3


def test_unknown_role_title_rejected():
    payload = {**VALID_PAYLOAD_TURN1, "role_title": "Bukan Role Asli"}
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("role_title" in err["loc"] for err in errors)


def test_turn_index_2_without_history_rejected():
    payload = {**VALID_PAYLOAD_TURN1, "turn_index": 2}
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("history" in err["msg"] for err in errors), (
        f"pesan error tidak menyebut 'history': {errors}"
    )


def test_turn_index_3_with_gap_in_history_rejected():
    # history cuma punya turn_index 1, padahal turn_index=3 butuh 1 DAN 2
    payload = {
        **VALID_PAYLOAD_TURN3,
        "history": [
            {"turn_index": 1, "question": "Berapa occupancy April?", "answer": "78%"}
        ],
    }
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("history" in err["msg"] for err in errors)


def test_turn_index_3_with_duplicate_history_turn_index_rejected():
    payload = {
        **VALID_PAYLOAD_TURN3,
        "history": [
            {"turn_index": 1, "question": "Berapa occupancy April?", "answer": "78%"},
            {"turn_index": 1, "question": "Berapa occupancy April? (lagi)", "answer": "78%"},
        ],
    }
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("history" in err["msg"] for err in errors)
