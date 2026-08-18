"""Test orkestrator lintas-layer Milestone 7.6 -
src/orchestration/turn_pipeline.py. Cakupan SEMPIT (decisions.md
Keputusan 8): hanya kejadian yang TIDAK butuh LLM/Jaeger nyata (short-
circuit deterministik + wiring identity mocked). Kejadian yang butuh
eksekusi nyata (LLM sungguhan, bukti span) ada di
evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/ - lihat
rancangan.md/audit.md di folder itu.
"""

import pydantic
import pytest

import src.orchestration.turn_pipeline as turn_pipeline_module
from src.orchestration.turn_pipeline import proses_turn
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload

_RAW_VALID_TURN1 = {
    "session_id": "sess-test",
    "turn_index": 1,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Berapa occupancy bulan ini?",
}

# Kejadian E03: history tidak cocok turn_index (turn_index=2 tapi history
# kosong) -> pydantic.ValidationError, forced by model_validator
# TurnPayload.history_matches_turn_index().
_RAW_GAGAL_VALIDASI = {
    "session_id": "sess-test",
    "turn_index": 2,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Bandingkan dengan bulan lalu",
    "history": [],
}


def test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil(
    monkeypatch,
):
    """Kejadian E03: payload gagal validasi Input Layer -> ValidationError
    menjalar, detect_turn_dependency() TIDAK PERNAH terpanggil."""

    def _gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "detect_turn_dependency TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", _gagal_kalau_terpanggil
    )

    with pytest.raises(pydantic.ValidationError):
        proses_turn(_RAW_GAGAL_VALIDASI)


def test_orkestrator_wiring_keadaan_turn_berisi_objek_identik(monkeypatch):
    """Payload valid -> KeadaanTurn berisi objek PERSIS (identity) dari
    kedua langkah, bukan rekonstruksi."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert hasil.payload is payload_asli
    assert hasil.ketergantungan is ketergantungan_asli
