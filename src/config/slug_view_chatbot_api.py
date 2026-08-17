"""Pemetaan `view_name` internal (nama SQL, `src/config/katalog_view.py`) ->
slug URL yang dipakai `chatbot_api` sebagai key `WHITELIST` di tiap
`whitelist_<domain>.py`.

Ditranskripsi manual, per 2026-08-17, dari 10 file `whitelist_<domain>.py`
di repo bertetangga `../nirwana-database/scripts/chatbot_api/` (dibaca
read-only, TIDAK dimodifikasi - `chatbot_api` sudah final dan di luar
cakupan revisi proyek ini, `CLAUDE.md` "Batas Implementasi Saat Ini").

Dibuat karena `view_name` (nama SQL, mis. `v_housekeeping_staff_daily`)
TIDAK SAMA dengan slug URL `chatbot_api` (mis. `housekeeping-staff-daily`)
- dan transformasinya TIDAK bisa diturunkan otomatis lewat regex, terbukti
tidak konsisten antar view (`v_lookup_housekeeping_log` -> `housekeeping-log`
strip "lookup_"; `v_hr_attendance_daily` -> `attendance-daily` strip "hr_";
`v_lookup_financial_summary` -> `financial-summary` strip "lookup_" TAPI
PERTAHANKAN "financial_"; `v_financial_departmental_margin` ->
`departmental-margin` strip "financial_"). Mirror preseden `katalog_view.py`:
transkripsi eksplisit dari sumber eksternal final, ruang kesalahan tertutup
(67 nilai, sama seperti DAFTAR_VIEW_PER_DOMAIN).

Status: sama seperti `docs/kontrak-parameter-chatbot-api-usulan.md`/
`docs/keputusan-tertunda.md` #3 - `api-chatbot.md` sendiri menandai bentuk
URL "berpotensi berubah" (bukan hasil negosiasi dengan tim chatbot
sungguhan). Lihat
milestones/4.1-membangun-pemanggilan-chatbot-api/decisions.md Keputusan 5.
"""

VIEW_NAME_KE_SLUG_CHATBOT_API: dict[str, str] = {
    # reservation (10) - whitelist_reservation.py
    "v_reservation_room_type_daily": "room-type-daily",
    "v_reservation_channel_daily": "channel-daily",
    "v_reservation_los_daily": "los-daily",
    "v_reservation_property_daily": "property-daily",
    "v_reservation_gop_impact_monthly": "gop-impact-monthly",
    "v_reservation_pricing_deviation": "pricing-deviation",
    "v_reservation_loyalty_daily": "loyalty-daily",
    "v_reservation_nationality_daily": "nationality-daily",
    "v_lookup_bookings": "bookings",
    "v_lookup_daily_occupancy": "daily-occupancy",
    # fnb (11) - whitelist_fnb.py
    "v_fnb_outlet_daily": "outlet-daily",
    "v_fnb_category_daily": "category-daily",
    "v_fnb_hourly": "hourly",
    "v_fnb_customer_type_daily": "customer-type-daily",
    "v_fnb_menu_item_daily": "menu-item-daily",
    "v_fnb_waste_daily": "waste-daily",
    "v_fnb_inventory_status": "inventory-status",
    "v_fnb_ingredient_price_daily": "ingredient-price-daily",
    "v_lookup_fnb_inventory": "fnb-inventory",
    "v_lookup_fnb_transactions": "fnb-transactions",
    "v_lookup_recipe_bom": "recipe-bom",
    # facility (12) - whitelist_facility.py
    "v_facility_room_status_daily": "room-status-daily",
    "v_housekeeping_room_type_daily": "housekeeping-room-type-daily",
    "v_housekeeping_property_daily": "housekeeping-property-daily",
    "v_housekeeping_staff_daily": "housekeeping-staff-daily",
    "v_maintenance_ticket_daily": "maintenance-ticket-daily",
    "v_maintenance_cost_daily": "maintenance-cost-daily",
    "v_maintenance_room_recurrence_yearly": "maintenance-room-recurrence-yearly",
    "v_maintenance_property_benchmark_yearly": "maintenance-property-benchmark-yearly",
    "v_maintenance_technician_daily": "maintenance-technician-daily",
    "v_lookup_rooms": "rooms",
    "v_lookup_housekeeping_log": "housekeeping-log",
    "v_lookup_maintenance_tickets": "maintenance-tickets",
    # spa_event (9) - whitelist_spa_event.py
    "v_spa_daily": "spa-daily",
    "v_spa_customer_type_daily": "spa-customer-type-daily",
    "v_spa_service_daily": "spa-service-daily",
    "v_event_venue_daily": "event-venue-daily",
    "v_event_property_daily": "event-property-daily",
    "v_event_type_daily": "event-type-daily",
    "v_lookup_spa_bookings": "spa-bookings",
    "v_lookup_event_bookings": "event-bookings",
    "v_lookup_venues": "venues",
    # hr (10) - whitelist_hr.py
    "v_hr_attendance_daily": "attendance-daily",
    "v_hr_employee_monthly": "employee-monthly",
    "v_hr_employee_performance_semester": "employee-performance-semester",
    "v_hr_turnover_snapshot": "turnover-snapshot",
    "v_hr_headcount_status_daily": "headcount-status-daily",
    "v_hr_performance_department_semester": "performance-department-semester",
    "v_hr_performance_by_status_semester": "performance-by-status-semester",
    "v_hr_watchlist_monthly": "watchlist-monthly",
    "v_lookup_staff_shifts": "staff-shifts",
    "v_lookup_employee_performance": "employee-performance",
    # financial (11) - whitelist_financial.py
    "v_financial_departmental_margin": "departmental-margin",
    "v_financial_gop_overhead": "gop-overhead",
    "v_financial_revenue_runrate_daily": "revenue-runrate-daily",
    "v_payroll_department_monthly": "payroll-department-monthly",
    "v_financial_service_charge_monthly": "service-charge-monthly",
    "v_financial_labor_cost_monthly": "labor-cost-monthly",
    "v_payroll_access_level_monthly": "payroll-access-level-monthly",
    "v_financial_business_line_group_monthly": "business-line-group-monthly",
    "v_financial_property_benchmark_monthly": "property-benchmark-monthly",
    "v_lookup_financial_summary": "financial-summary",
    "v_lookup_payroll": "payroll",
    # properties_ref (1) - whitelist_properties_ref.py
    "v_properties_ref": "properties",
    # employees_directory (1) - whitelist_employees_directory.py
    "v_employees_directory": "employees",
    # guests_pii (1) - whitelist_guests_pii.py
    "guests_contact_view": "guests-contact",
    # guests_profile (1) - whitelist_guests_profile.py
    "guests_profile_view": "guests-profile",
}
