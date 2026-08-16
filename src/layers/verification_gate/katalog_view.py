"""Katalog 67 view_name valid per domain (Milestone 2.4, Cek 1: bentuk
request statis).

Ditranskripsi dari docs/03-domain-source/katalog-data-chatbot.md (67
header `####` - 65 diawali `v_`, DUA PENGECUALIAN `guests_contact_view`/
`guests_profile_view` tidak mengikuti konvensi awalan `v_`, ditranskripsi
persis sesuai penamaan dokumen sumber, bukan disalahkan menjadi `v_guests_
*`). Dipakai verifikasi_bentuk_request_statis() untuk memastikan
`view_name` request benar-benar ada di domain yang dinyatakan - ruang
kesalahan tertutup (67 nilai final, diaudit tim database engineering).
"""

from src.schemas.domain_gate import Domain

DAFTAR_VIEW_PER_DOMAIN: dict[Domain, frozenset[str]] = {
    Domain.RESERVATION: frozenset(
        {
            "v_reservation_room_type_daily",
            "v_reservation_channel_daily",
            "v_reservation_los_daily",
            "v_reservation_property_daily",
            "v_reservation_gop_impact_monthly",
            "v_reservation_pricing_deviation",
            "v_reservation_loyalty_daily",
            "v_reservation_nationality_daily",
            "v_lookup_bookings",
            "v_lookup_daily_occupancy",
        }
    ),
    Domain.FNB: frozenset(
        {
            "v_fnb_outlet_daily",
            "v_fnb_category_daily",
            "v_fnb_hourly",
            "v_fnb_customer_type_daily",
            "v_fnb_menu_item_daily",
            "v_fnb_waste_daily",
            "v_fnb_inventory_status",
            "v_fnb_ingredient_price_daily",
            "v_lookup_fnb_inventory",
            "v_lookup_fnb_transactions",
            "v_lookup_recipe_bom",
        }
    ),
    Domain.FACILITY: frozenset(
        {
            "v_facility_room_status_daily",
            "v_housekeeping_room_type_daily",
            "v_housekeeping_property_daily",
            "v_housekeeping_staff_daily",
            "v_maintenance_ticket_daily",
            "v_maintenance_cost_daily",
            "v_maintenance_room_recurrence_yearly",
            "v_maintenance_property_benchmark_yearly",
            "v_maintenance_technician_daily",
            "v_lookup_rooms",
            "v_lookup_housekeeping_log",
            "v_lookup_maintenance_tickets",
        }
    ),
    Domain.SPA_EVENT: frozenset(
        {
            "v_spa_daily",
            "v_spa_customer_type_daily",
            "v_spa_service_daily",
            "v_event_venue_daily",
            "v_event_property_daily",
            "v_event_type_daily",
            "v_lookup_spa_bookings",
            "v_lookup_event_bookings",
            "v_lookup_venues",
        }
    ),
    Domain.HR: frozenset(
        {
            "v_hr_attendance_daily",
            "v_hr_employee_monthly",
            "v_hr_employee_performance_semester",
            "v_hr_turnover_snapshot",
            "v_hr_headcount_status_daily",
            "v_hr_performance_department_semester",
            "v_hr_performance_by_status_semester",
            "v_hr_watchlist_monthly",
            "v_lookup_staff_shifts",
            "v_lookup_employee_performance",
        }
    ),
    Domain.FINANCIAL: frozenset(
        {
            "v_financial_departmental_margin",
            "v_financial_gop_overhead",
            "v_financial_revenue_runrate_daily",
            "v_payroll_department_monthly",
            "v_financial_service_charge_monthly",
            "v_financial_labor_cost_monthly",
            "v_payroll_access_level_monthly",
            "v_financial_business_line_group_monthly",
            "v_financial_property_benchmark_monthly",
            "v_lookup_financial_summary",
            "v_lookup_payroll",
        }
    ),
    Domain.PROPERTIES_REF: frozenset({"v_properties_ref"}),
    Domain.EMPLOYEES_DIRECTORY: frozenset({"v_employees_directory"}),
    Domain.GUESTS_PII: frozenset({"guests_contact_view"}),
    Domain.GUESTS_PROFILE: frozenset({"guests_profile_view"}),
}
