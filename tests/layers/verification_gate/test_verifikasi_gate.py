"""Test suite mekanisme Verification Gate (Milestone 2.4).

File ini dibangun bertahap lintas checkpoint (preseden pola M2.2/M2.3):
- Checkpoint 5 (Task 7-8): cek 1 (bentuk request statis).
- Checkpoint 6 (Task 9-10): cek 2 (kepatuhan sumber, KK2).
- Checkpoint 7 (Task 11-12): cek 3-4 (penegakan constraint, KK1).
- Checkpoint 8 (Task 13-14): orkestrator + KK1-3 end-to-end.
"""

from src.layers.verification_gate.verifikasi_gate import (
    tegakkan_constraint_cakupan_individu,
    verifikasi_bentuk_request_statis,
    verifikasi_kelengkapan_penegakan,
    verifikasi_kepatuhan_sumber,
)
from src.schemas.cakupan_individu import ConstraintCakupanIndividu
from src.schemas.domain_gate import Domain
from src.schemas.verification_gate import QueryEngineRequest


def _buat_request(
    domain: Domain = Domain.FACILITY,
    view_name: str = "v_housekeeping_staff_daily",
    params: dict | None = None,
) -> QueryEngineRequest:
    return QueryEngineRequest(domain=domain, view_name=view_name, params=params or {})


# --- Cek 1: Bentuk Request Statis -------------------------------------------


def test_cek1_request_valid_lolos():
    lolos, alasan = verifikasi_bentuk_request_statis(_buat_request())
    assert lolos is True
    assert alasan is None


def test_cek1_view_name_tidak_ada_di_domain_manapun():
    request = _buat_request(view_name="v_view_karangan_tidak_ada")
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is False
    assert alasan is not None and "v_view_karangan_tidak_ada" in alasan


def test_cek1_view_name_ada_tapi_di_domain_lain():
    """v_hr_employee_monthly ada di domain hr, bukan facility."""
    request = _buat_request(domain=Domain.FACILITY, view_name="v_hr_employee_monthly")
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is False
    assert alasan is not None and "facility" in alasan


def test_cek1_limit_melebihi_1000():
    request = _buat_request(params={"limit": 1001})
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is False
    assert alasan is not None and "1001" in alasan


def test_cek1_limit_persis_1000_masih_lolos():
    request = _buat_request(params={"limit": 1000})
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is True


def test_cek1_tanpa_limit_lolos():
    request = _buat_request(params={"employee_id": "E0002"})
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is True


# --- Cek 2: Kepatuhan Sumber (KK2) -------------------------------------------


def test_cek2_kk2_view_name_sengaja_tidak_cocok_ditolak():
    """KK2: view_name request SENGAJA dibuat tidak cocok dengan yang
    divalidasi Retriever - harus ditolak, alasan menyebut ketidaksesuaian."""
    request = _buat_request(view_name="v_housekeeping_staff_daily")
    lolos, alasan = verifikasi_kepatuhan_sumber(
        request, view_name_tervalidasi_retriever="v_maintenance_technician_daily"
    )
    assert lolos is False
    assert alasan is not None
    assert "v_housekeeping_staff_daily" in alasan
    assert "v_maintenance_technician_daily" in alasan


def test_cek2_view_name_cocok_lolos():
    request = _buat_request(view_name="v_housekeeping_staff_daily")
    lolos, alasan = verifikasi_kepatuhan_sumber(
        request, view_name_tervalidasi_retriever="v_housekeeping_staff_daily"
    )
    assert lolos is True
    assert alasan is None


# --- Cek 3-4: Penegakan Constraint + Kelengkapan (KK1) ----------------------


def test_kk1_constraint_terdeteksi_params_belum_benar_dikoreksi_paksa():
    """KK1: constraint terdeteksi, params BELUM menyertakan employee_id
    caller yang benar - harus DIKOREKSI PAKSA, bukan ditolak."""
    request = _buat_request(params={})
    constraint = ConstraintCakupanIndividu(terdeteksi=True, alasan="performa individu")

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request, constraint, employee_id="E0002"
    )

    assert terkoreksi is True
    assert request_terkoreksi.params["employee_id"] == "E0002"

    lolos, alasan = verifikasi_kelengkapan_penegakan(
        request_terkoreksi, constraint, employee_id="E0002"
    )
    assert lolos is True
    assert alasan is None


def test_kk1_constraint_terdeteksi_params_sudah_benar_tidak_dikoreksi_ulang():
    request = _buat_request(params={"employee_id": "E0002"})
    constraint = ConstraintCakupanIndividu(terdeteksi=True, alasan="performa individu")

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request, constraint, employee_id="E0002"
    )

    assert terkoreksi is False
    assert request_terkoreksi.params["employee_id"] == "E0002"


def test_constraint_tidak_terdeteksi_params_tidak_diubah_sama_sekali():
    request = _buat_request(params={"limit": 50})
    constraint = ConstraintCakupanIndividu(terdeteksi=False)

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request, constraint, employee_id="E0002"
    )

    assert terkoreksi is False
    assert request_terkoreksi.params == {"limit": 50}
    assert "employee_id" not in request_terkoreksi.params

    lolos, alasan = verifikasi_kelengkapan_penegakan(
        request_terkoreksi, constraint, employee_id="E0002"
    )
    assert lolos is True
