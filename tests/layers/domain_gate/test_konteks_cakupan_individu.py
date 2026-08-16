"""Test data grounding cakupan-individu (Milestone 2.3) - murni cek
struktur data statis, tanpa LLM/DB."""

from src.layers.domain_gate.konteks_cakupan_individu import DAFTAR_VIEW_CAKUPAN_INDIVIDU
from src.schemas.domain_gate import Domain

_VIEW_AGREGAT_YANG_HARUS_TIDAK_ADA = {
    "v_hr_attendance_daily",
    "v_hr_turnover_snapshot",
    "v_hr_headcount_status_daily",
    "v_hr_performance_department_semester",
    "v_hr_performance_by_status_semester",
    "v_housekeeping_room_type_daily",
    "v_housekeeping_property_daily",
    "v_maintenance_ticket_daily",
    "v_maintenance_cost_daily",
    "v_maintenance_room_recurrence_yearly",
    "v_maintenance_property_benchmark_yearly",
    "v_facility_room_status_daily",
}


def test_jumlah_9_view():
    assert len(DAFTAR_VIEW_CAKUPAN_INDIVIDU) == 9


def test_hanya_domain_facility_dan_hr():
    domains = {v.domain for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU}
    assert domains == {Domain.FACILITY, Domain.HR}


def test_4_view_facility_5_view_hr():
    facility = [v for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU if v.domain == Domain.FACILITY]
    hr = [v for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU if v.domain == Domain.HR]
    assert len(facility) == 4
    assert len(hr) == 5


def test_nama_view_sesuai_daftar_terkonfirmasi():
    nama_view = {v.nama for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU}
    assert nama_view == {
        "v_housekeeping_staff_daily",
        "v_maintenance_technician_daily",
        "v_lookup_housekeeping_log",
        "v_lookup_maintenance_tickets",
        "v_hr_employee_monthly",
        "v_hr_employee_performance_semester",
        "v_hr_watchlist_monthly",
        "v_lookup_staff_shifts",
        "v_lookup_employee_performance",
    }


def test_tidak_ada_view_agregat_yang_lolos():
    nama_view = {v.nama for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU}
    assert nama_view.isdisjoint(_VIEW_AGREGAT_YANG_HARUS_TIDAK_ADA)


def test_setiap_view_punya_kolom_identitas_dan_deskripsi():
    for v in DAFTAR_VIEW_CAKUPAN_INDIVIDU:
        assert v.kolom_identitas
        assert v.deskripsi
