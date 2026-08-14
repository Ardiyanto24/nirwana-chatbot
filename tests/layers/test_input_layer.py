"""Test suite Input Layer (Milestone 1.2) — lewat endpoint HTTP sungguhan
(`TestClient`), membuktikan Kriteria Keberhasilan sumber:
- Field wajib hilang selalu ditolak dengan pesan menyebut field spesifik.
- `turn_index=1` (tanpa histori) dan `turn_index>1` (dengan histori) sama-sama
  diterima tanpa memperlakukan salah satunya sebagai kondisi khusus terlewat.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

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
    "previous_turn": {"question": "Berapa occupancy April?", "answer": "78%"},
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


def test_turn_index_1_without_history_accepted():
    response = client.post("/v1/turns", json=VALID_PAYLOAD_TURN1)
    assert response.status_code == 200
    assert response.json()["previous_turn"] is None


def test_turn_index_2_with_previous_turn_accepted():
    response = client.post("/v1/turns", json=VALID_PAYLOAD_TURN2)
    assert response.status_code == 200
    body = response.json()
    assert body["previous_turn"]["answer"] == "78%"


def test_unknown_role_title_rejected():
    payload = {**VALID_PAYLOAD_TURN1, "role_title": "Bukan Role Asli"}
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("role_title" in err["loc"] for err in errors)


def test_turn_index_2_without_previous_turn_rejected():
    payload = {**VALID_PAYLOAD_TURN1, "turn_index": 2}
    response = client.post("/v1/turns", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("previous_turn" in err["msg"] for err in errors), (
        f"pesan error tidak menyebut 'previous_turn': {errors}"
    )
