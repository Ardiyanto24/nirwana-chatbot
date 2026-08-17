# Kontrak Parameter `chatbot_api` — Usulan (Milestone 3.4)

**Status dokumen:** USULAN dari sisi `nirwana-chatbot` (Lapis 1 RBAC AI Chatbot) — **BUKAN kontrak resmi** `chatbot_api`. Dibangkitkan programatik dari `src/layers/query_engine/param_whitelist.py` pada 2026-08-17 (regenerasi diperlukan kalau whitelist di kode berubah).

## Latar Belakang

`docs/03-domain-source/api-chatbot.md` hanya mendokumentasikan 4 parameter GLOBAL yang berlaku di semua endpoint (`role_title`, `employee_id`, `property_id`, `limit`/`offset`). Whitelist parameter PER-VIEW yang dirujuk dokumen itu sendiri (`whitelist_<domain>.py`) belum final — tim pembangun `chatbot_api` masih menunggu proyek `nirwana-chatbot` ini selesai untuk menentukan parameter pastinya (dikonfirmasi langsung oleh pemilik proyek). Dokumen ini adalah **usulan konkret** dari sisi kebutuhan `nirwana-chatbot`, untuk **direkonsiliasi dengan tim pembangun `chatbot_api` di akhir proyek** — bukan daftar final yang sudah disepakati.

## Aturan Derivasi

Tiap parameter di bawah diturunkan langsung dari nama kolom yang benar-benar ada di definisi view terkait (`docs/03-domain-source/katalog-data-chatbot.md`), TANPA satu pun nama dikarang:

1. **Kolom bertema tanggal** (nama kolom mengandung kata "date", mis. `period_date`, `check_in_date`, `booking_date`) menghasilkan TIGA parameter: `<kolom>` (filter tanggal tunggal, exact match), `<kolom>_from`, `<kolom>_to` (filter rentang tanggal). Format tanggal yang diusulkan: **`YYYY-MM-DD`** (ISO 8601, tidak ada bukti kontrak lain sehingga dipilih sebagai default REST yang umum).
2. **Kolom lain** menghasilkan SATU parameter exact-match `<kolom>` (nilai harus persis sama, termasuk untuk kolom kategorikal seperti `channel_name`, `room_type_name`).
3. **`limit`/`offset`** (parameter global sesuai `api-chatbot.md`, default 100/0, maksimal `limit` 1000) berlaku di SETIAP view, tidak diulang per baris di bawah.
4. **`employee_id`/`role_title`** SENGAJA TIDAK diusulkan di sini sebagai parameter filter tambahan — keduanya sudah punya arti berbeda di `api-chatbot.md` (identity claim/resolusi `own_property`), bukan filter baris data biasa.

## Pemicu Peninjauan Ulang

- Rekonsiliasi langsung dengan tim pembangun `chatbot_api` di akhir proyek — dokumen ini WAJIB dicocokkan terhadap `whitelist_<domain>.py` yang sebenarnya begitu tersedia.
- Kegagalan `400` (bentuk parameter salah) berulang saat Milestone 4.x (Execution) mulai mengirim request nyata — pola kegagalan berulang mengindikasikan konvensi di dokumen ini perlu direvisi.

Lihat `docs/keputusan-tertunda.md` untuk status keputusan tertunda terkait.

## Daftar Parameter Usulan per View

### Domain `reservation` (10 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_lookup_bookings` | `booking_channel`, `booking_date`, `booking_date_from`, `booking_date_to`, `booking_id`, `check_in_date`, `check_in_date_from`, `check_in_date_to`, `check_out_date`, `check_out_date_from`, `check_out_date_to`, `guest_id`, `nights`, `property_id`, `room_rate`, `room_type`, `status`, `total_amount` |
| `v_lookup_daily_occupancy` | `adr`, `date`, `date_from`, `date_to`, `occupancy_rate`, `property_id`, `revpar`, `room_type`, `rooms_sold`, `total_rooms_available` |
| `v_reservation_channel_daily` | `bookings_count`, `cancellations_count`, `channel_name`, `no_shows_count`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `region`, `revenue` |
| `v_reservation_gop_impact_monthly` | `avg_pricing_deviation`, `gop_margin`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_reservation_los_daily` | `avg_los_nights`, `channel_name`, `median_los_nights`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `room_type_name` |
| `v_reservation_loyalty_daily` | `bookings_count`, `loyalty_tier_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue` |
| `v_reservation_nationality_daily` | `bookings_count`, `nationality_group_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue` |
| `v_reservation_pricing_deviation` | `avg_applied_rate`, `avg_base_rate`, `avg_deviation_pct`, `day_share_pct`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `reason_name` |
| `v_reservation_property_daily` | `adr_rank_group`, `avg_lead_time_days`, `median_lead_time_days`, `mom_adr_growth`, `mom_occupancy_growth`, `mom_revpar_growth`, `occupancy_rank_group`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `region`, `repeat_guest_rate`, `revpar_rank_group`, `yoy_adr_growth`, `yoy_occupancy_growth`, `yoy_revpar_growth` |
| `v_reservation_room_type_daily` | `adr`, `occupancy_rate`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `region`, `revenue`, `revpar`, `room_type_name`, `room_type_revenue_share_pct`, `rooms_sold`, `total_rooms_available` |

### Domain `fnb` (11 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_fnb_category_daily` | `category_name`, `outlet_id`, `outlet_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue` |
| `v_fnb_customer_type_daily` | `customer_type_name`, `outlet_id`, `outlet_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue`, `revenue_per_visit`, `visit_count` |
| `v_fnb_hourly` | `hour_of_day`, `outlet_id`, `outlet_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `transaction_count` |
| `v_fnb_ingredient_price_daily` | `avg_unit_cost`, `ingredient_id`, `period_date`, `period_date_from`, `period_date_to` |
| `v_fnb_inventory_status` | `low_stock_item_count`, `outlet_id`, `outlet_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_fnb_menu_item_daily` | `food_cost_deviation`, `food_cost_ratio_actual`, `food_cost_ratio_target`, `item_name`, `outlet_id`, `outlet_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `quantity_sold`, `revenue` |
| `v_fnb_outlet_daily` | `avg_check`, `capture_rate`, `mom_revenue_growth`, `outlet_id`, `outlet_name`, `outlet_type_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue`, `revenue_rank_vs_outlet_type_avg`, `transaction_count`, `walk_in_ratio`, `yoy_revenue_growth` |
| `v_fnb_waste_daily` | `outlet_id`, `outlet_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `reason_name`, `waste_quantity`, `waste_ratio`, `waste_value` |
| `v_lookup_fnb_inventory` | `ingredient_id`, `ingredient_name`, `outlet_id`, `property_id`, `stock_current`, `stock_min_threshold`, `unit`, `unit_cost` |
| `v_lookup_fnb_transactions` | `category`, `customer_type`, `guest_id`, `item_name`, `outlet_id`, `property_id`, `quantity`, `total_price`, `transaction_datetime`, `transaction_datetime_from`, `transaction_datetime_to`, `transaction_id`, `unit_price` |
| `v_lookup_recipe_bom` | `ingredient_id`, `item_name`, `qty_per_portion` |

### Domain `facility` (12 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_facility_room_status_daily` | `is_out_of_order`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `room_id`, `room_type_name`, `status` |
| `v_housekeeping_property_daily` | `delayed_rate`, `occupancy_rate`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_housekeeping_room_type_daily` | `avg_cleaning_duration_minutes`, `baseline_duration_minutes`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `room_type_name` |
| `v_housekeeping_staff_daily` | `avg_cleaning_duration_minutes`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `staff_id`, `staff_name`, `team_avg_duration_minutes` |
| `v_lookup_housekeeping_log` | `cleaning_end_time`, `cleaning_start_time`, `date`, `date_from`, `date_to`, `log_id`, `property_id`, `room_id`, `staff_id`, `status` |
| `v_lookup_maintenance_tickets` | `assigned_staff_id`, `cost`, `facility_area`, `issue_type`, `labor_hours`, `parts_replaced`, `priority`, `property_id`, `reported_date`, `reported_date_from`, `reported_date_to`, `resolved_date`, `resolved_date_from`, `resolved_date_to`, `room_id`, `status`, `ticket_id` |
| `v_lookup_rooms` | `floor`, `property_id`, `room_id`, `room_number`, `room_type`, `status` |
| `v_maintenance_cost_daily` | `cost_with_parts`, `cost_without_parts`, `issue_type_name`, `mom_cost_growth`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `total_cost`, `yoy_cost_growth` |
| `v_maintenance_property_benchmark_yearly` | `building_age_years`, `property_id`, `property_name`, `tickets_per_room`, `tickets_per_room_normalized`, `year` |
| `v_maintenance_room_recurrence_yearly` | `property_id`, `property_name`, `room_id`, `room_type_name`, `ticket_count`, `vs_median_ratio`, `year` |
| `v_maintenance_technician_daily` | `assigned_staff_id`, `labor_hours`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `technician_name`, `ticket_count` |
| `v_maintenance_ticket_daily` | `avg_exceeds_sla_threshold`, `avg_sla_duration_hours`, `facility_area_name`, `issue_type_name`, `new_ticket_count`, `pending_count`, `period_date`, `period_date_from`, `period_date_to`, `priority_name`, `property_id`, `property_name`, `sla_threshold_hours` |

### Domain `spa_event` (9 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_event_property_daily` | `cancellation_rate`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_event_type_daily` | `event_count`, `event_type_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue` |
| `v_event_venue_daily` | `bookings_pipeline_count`, `low_utilization_days_last_30`, `max_capacity`, `mom_revenue_growth`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue_pipeline`, `utilization_rate`, `venue_id`, `venue_name`, `venue_type_name`, `yoy_revenue_growth` |
| `v_lookup_event_bookings` | `capacity_booked`, `client_name`, `event_date`, `event_date_from`, `event_date_to`, `event_id`, `event_type`, `property_id`, `status`, `total_revenue`, `venue_id`, `venue_name` |
| `v_lookup_spa_bookings` | `booking_date`, `booking_date_from`, `booking_date_to`, `customer_type`, `duration_minutes`, `guest_id`, `price`, `property_id`, `service_date`, `service_date_from`, `service_date_to`, `service_name`, `spa_booking_id`, `status` |
| `v_lookup_venues` | `max_capacity`, `property_id`, `venue_id`, `venue_name`, `venue_type` |
| `v_spa_customer_type_daily` | `customer_type_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue`, `revenue_per_visit`, `visit_count` |
| `v_spa_daily` | `avg_lead_time_days`, `booking_count`, `cancellation_rate`, `median_lead_time_days`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue`, `walk_in_ratio` |
| `v_spa_service_daily` | `booking_count`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue`, `revenue_share_pct`, `service_name` |

### Domain `hr` (10 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_hr_attendance_daily` | `absent_count`, `department_name`, `late_count`, `leave_count`, `overtime_hours_total`, `period_date`, `period_date_from`, `period_date_to`, `present_count`, `property_id`, `property_name` |
| `v_hr_employee_monthly` | `department_name`, `full_name`, `late_rate`, `late_vs_dept_avg`, `overtime_hours`, `overtime_vs_dept_avg`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_hr_employee_performance_semester` | `department_name`, `full_name`, `notes`, `property_id`, `property_name`, `review_period`, `score` |
| `v_hr_headcount_status_daily` | `department_name`, `employee_count`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `status_name` |
| `v_hr_performance_by_status_semester` | `avg_performance_score`, `property_id`, `property_name`, `review_period`, `status_name` |
| `v_hr_performance_department_semester` | `avg_performance_score`, `department_name`, `property_id`, `property_name`, `review_period` |
| `v_hr_turnover_snapshot` | `department_name`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `turnover_rate` |
| `v_hr_watchlist_monthly` | `absence_deviation_ratio`, `baseline_absence_rate`, `baseline_late_rate`, `current_absence_rate`, `current_late_rate`, `department_name`, `full_name`, `in_watchlist`, `late_deviation_ratio`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_lookup_employee_performance` | `notes`, `property_id`, `review_id`, `review_period`, `score` |
| `v_lookup_staff_shifts` | `clock_in`, `clock_out`, `date`, `date_from`, `date_to`, `property_id`, `shift_id`, `shift_type`, `status` |

### Domain `financial` (11 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_financial_business_line_group_monthly` | `business_line_name`, `group_revenue`, `period_date`, `period_date_from`, `period_date_to`, `revenue_share_pct` |
| `v_financial_departmental_margin` | `business_line_name`, `expense`, `margin_pct`, `period_date`, `period_date_from`, `period_date_to`, `profit`, `property_id`, `property_name`, `revenue` |
| `v_financial_gop_overhead` | `gop`, `gop_margin_pct`, `mom_gop_growth`, `overhead_ratio`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `undistributed_expense_total`, `yoy_gop_growth` |
| `v_financial_labor_cost_monthly` | `labor_cost_pct_revenue`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_financial_property_benchmark_monthly` | `gop_margin_rank`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name` |
| `v_financial_revenue_runrate_daily` | `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `revenue_runrate` |
| `v_financial_service_charge_monthly` | `occupancy_rate`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `service_charge_pool` |
| `v_lookup_financial_summary` | `department`, `departmental_expense`, `departmental_profit`, `departmental_revenue`, `gop`, `period`, `property_id`, `undistributed_expense` |
| `v_lookup_payroll` | `base_salary`, `deduction`, `net_salary`, `overtime_pay`, `payroll_id`, `period`, `property_id`, `service_charge`, `thr` |
| `v_payroll_access_level_monthly` | `access_level_name`, `base_salary_total`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `service_charge_to_base_ratio`, `service_charge_total` |
| `v_payroll_department_monthly` | `base_salary_total`, `deduction_total`, `department_name`, `mom_growth`, `net_salary_total`, `overtime_pay_total`, `period_date`, `period_date_from`, `period_date_to`, `property_id`, `property_name`, `service_charge_total`, `thr_total` |

### Domain `properties_ref` (1 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_properties_ref` | `opening_date`, `opening_date_from`, `opening_date_to`, `property_id`, `property_name`, `region` |

### Domain `employees_directory` (1 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `v_employees_directory` | `access_level_name`, `department_name`, `full_name`, `property_id`, `property_name` |

### Domain `guests_pii` (1 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `guests_contact_view` | `email`, `full_name`, `guest_id`, `last_active_property_id`, `phone` |

### Domain `guests_profile` (1 view)

| `view_name` | Parameter usulan (selain `limit`/`offset`) |
|---|---|
| `guests_profile_view` | `guest_id`, `last_active_property_id`, `loyalty_tier`, `nationality`, `registered_date`, `registered_date_from`, `registered_date_to` |

