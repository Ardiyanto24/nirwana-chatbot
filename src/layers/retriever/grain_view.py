"""Taksonomi Grain Terstruktur (Milestone 3.3) - bahan mekanisme
deterministik kecukupan struktural, beda sifat dari korpus_view.py
(M3.1)/definisi_view.py (M3.2) yang murni transkripsi verbatim: grain di
docs/03-domain-source/katalog-data-chatbot.md hanya tertulis sebagai
prosa ("grain: properti x tipe kamar x tanggal"), tidak ada tabel
terstruktur siap pakai - jadi tabel di bawah adalah hasil KLASIFIKASI/
JUDGMENT (dibaca+ditafsir dari baris "Sumber" tiap view), bukan sekadar
salin. Karena itu verifikasinya juga beda: review manual + spot-check
test terarah (tests/layers/retriever/test_grain_view.py), BUKAN
drift-detection regex penuh seperti korpus M3.1/M3.2.

Dua sinyal tri-state (`ya`/`tidak`/`tidak_pasti`) per view, dipakai
_evaluasi_deterministik() (kecukupan_struktural.py):
- `punya_time_series`: grain punya dimensi waktu BERULANG untuk entitas
  yang sama (mis. "properti x tanggal") -> relevan label `tren`. `tidak`
  kalau grain eksplisit ditandai "(snapshot)" di katalog, atau memang
  tidak py dimensi waktu sama sekali (tabel referensi/master murni).
  `tidak_pasti` untuk grain row-level ("1 baris = 1 X") yang TIDAK py
  label periode eksplisit (mis. "1 baris = 1 reservasi") - ambigu apakah
  genuinely bisa dipakai untuk tren atau cuma daftar event individual.
- `punya_dimensi_pembanding`: grain py dimensi breakdown/entity yang
  menghasilkan >1 baris comparable dalam satu query (mis. tipe kamar,
  kanal, outlet, departemen, karyawan) -> relevan `perbandingan`/
  `peringkat`/`komposisi`. `tidak` untuk tabel referensi murni tanpa
  metrik bisnis apa pun (mis. `v_properties_ref` cuma nama+region).
  `tidak_pasti` untuk kasus row-level yang ambigu apakah "banyak baris"
  di situ genuinely berarti dimensi pembanding yang bermakna bisnis.

Klasifikasi `tidak_pasti` SENGAJA dipertahankan untuk kasus ambigu
(bukan dipaksa ya/tidak) - inilah tepat alasan mekanisme M3.3 dirancang
hybrid (lihat milestones/3.3-kecukupan-struktural/decisions.md
Keputusan 1): kandidat dengan sinyal tidak_pasti dilempar ke fallback
LLM, bukan ditebak deterministik.
"""

from typing import Literal

from pydantic import BaseModel

NilaiGrain = Literal["ya", "tidak", "tidak_pasti"]


class KarakteristikGrain(BaseModel):
    punya_time_series: NilaiGrain
    punya_dimensi_pembanding: NilaiGrain
    catatan: str


GRAIN_STRUKTURAL_VIEW: dict[str, KarakteristikGrain] = {
    # --- reservation (10) ---
    "v_reservation_room_type_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tipe kamar x tanggal - tanggal berulang, tipe kamar jadi dimensi pembanding.",
    ),
    "v_reservation_channel_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x kanal x tanggal.",
    ),
    "v_reservation_los_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tipe kamar x kanal x tanggal.",
    ),
    "v_reservation_property_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tanggal - properti jadi dimensi pembanding antar 5 properti.",
    ),
    "v_reservation_gop_impact_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x bulan.",
    ),
    "v_reservation_pricing_deviation": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x alasan harga x tanggal.",
    ),
    "v_reservation_loyalty_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tier loyalitas x tanggal.",
    ),
    "v_reservation_nationality_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x kelompok kebangsaan x tanggal.",
    ),
    "v_lookup_bookings": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 reservasi', tanpa label periode eksplisit - ambigu apakah cukup untuk tren/perbandingan agregat, bukan snapshot maupun deret waktu yang jelas.",
    ),
    "v_lookup_daily_occupancy": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain eksplisit properti x tipe kamar x tanggal (walau sumber mart_cleaned/lookup, bentuk grain sama dengan view agregat).",
    ),
    # --- fnb (11) ---
    "v_fnb_outlet_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x tanggal.",
    ),
    "v_fnb_category_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x kategori x tanggal.",
    ),
    "v_fnb_hourly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x tanggal x jam - dua dimensi waktu berulang.",
    ),
    "v_fnb_customer_type_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x tipe pelanggan x tanggal.",
    ),
    "v_fnb_menu_item_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x item menu x tanggal - item menu jadi dimensi komposisi.",
    ),
    "v_fnb_waste_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x alasan waste x tanggal.",
    ),
    "v_fnb_inventory_status": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: outlet x tanggal - tidak ditandai snapshot di katalog, diperlakukan sebagai catatan harian berulang.",
    ),
    "v_fnb_ingredient_price_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: bahan x tanggal (tanpa property_id, harga global).",
    ),
    "v_lookup_fnb_inventory": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="ya",
        catatan="grain eksplisit 'snapshot per 30 Juni 2026, bukan time-series' - katalog sendiri menegaskan tidak berulang; outlet x bahan tetap jadi dimensi pembanding.",
    ),
    "v_lookup_fnb_transactions": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 item dalam 1 struk', log transaksi individual tanpa label periode - ambigu.",
    ),
    "v_lookup_recipe_bom": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="ya",
        catatan="grain: menu x bahan, tanpa dimensi tanggal sama sekali (komposisi resep global, statis); menu x bahan tetap dimensi komposisi yang jelas.",
    ),
    # --- facility (12) ---
    "v_facility_room_status_daily": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="ya",
        catatan="grain 'kamar x tanggal (snapshot)' - REVISI Checkpoint 7 (eval Promptfoo): beda dari v_hr_turnover_snapshot yang Fungsi-nya eksplisit menyatakan 'tidak ada tren historis', view ini TIDAK punya pernyataan serupa - period_date berulang tiap hari (nama _daily, sumber fact_..._daily) genuinely bisa dibaca sebagai state-per-hari yang membentuk tren (mis. tren jumlah kamar out-of-order per hari), bukan snapshot tunggal. Ambigu, sengaja dilempar ke fallback LLM alih-alih ditebak deterministik.",
    ),
    "v_housekeeping_room_type_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tipe kamar x tanggal.",
    ),
    "v_housekeeping_property_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tanggal.",
    ),
    "v_housekeeping_staff_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: staff x tanggal - staff jadi dimensi pembanding performa individu.",
    ),
    "v_maintenance_ticket_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x area x jenis isu x prioritas x tanggal.",
    ),
    "v_maintenance_cost_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x jenis isu x tanggal.",
    ),
    "v_maintenance_room_recurrence_yearly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: kamar x tahun - tahun tetap dimensi waktu berulang (granularitas tahunan).",
    ),
    "v_maintenance_property_benchmark_yearly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tahun.",
    ),
    "v_maintenance_technician_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: teknisi x tanggal - teknisi jadi dimensi pembanding performa individu.",
    ),
    "v_lookup_rooms": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 kamar fisik', tabel master atribut kamar tanpa dimensi tanggal; ambigu apakah membandingkan atribut statis kamar terhitung 'perbandingan' bermakna bisnis.",
    ),
    "v_lookup_housekeeping_log": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 sesi pembersihan', log event individual tanpa label periode - ambigu.",
    ),
    "v_lookup_maintenance_tickets": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 tiket', log event individual tanpa label periode - ambigu.",
    ),
    # --- spa_event (9) ---
    "v_spa_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tanggal.",
    ),
    "v_spa_customer_type_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tipe pelanggan x tanggal.",
    ),
    "v_spa_service_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x layanan x tanggal.",
    ),
    "v_event_venue_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: venue x tanggal - venue jadi dimensi pembanding.",
    ),
    "v_event_property_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tanggal.",
    ),
    "v_event_type_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x jenis event x tanggal.",
    ),
    "v_lookup_spa_bookings": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 booking spa', log event individual tanpa label periode - ambigu.",
    ),
    "v_lookup_event_bookings": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 event', log event individual tanpa label periode - ambigu.",
    ),
    "v_lookup_venues": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 venue', tabel master atribut venue tanpa dimensi tanggal - ambigu untuk perbandingan.",
    ),
    # --- hr (10) ---
    "v_hr_attendance_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x departemen x tanggal.",
    ),
    "v_hr_employee_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: karyawan x bulan - karyawan jadi dimensi pembanding individu.",
    ),
    "v_hr_employee_performance_semester": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: karyawan x periode review - 'periode review' (semester) tetap label periode berulang eksplisit.",
    ),
    "v_hr_turnover_snapshot": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="ya",
        catatan="grain '(snapshot)' DIPERKUAT pernyataan eksplisit di teks Fungsi katalog: 'snapshot, tidak ada tren historis (data sumber tidak punya tanggal resign)' - beda dari v_facility_room_status_daily/v_hr_headcount_status_daily (Checkpoint 7) yang cuma bertanda '(snapshot)' tanpa pernyataan serupa, sehingga TETAP diklasifikasi tidak (pasti), bukan tidak_pasti. properti x departemen tetap dimensi pembanding.",
    ),
    "v_hr_headcount_status_daily": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="ya",
        catatan="grain 'properti x departemen x status x tanggal (snapshot)' - REVISI Checkpoint 7 (eval Promptfoo, pola sama v_facility_room_status_daily): TANPA pernyataan eksplisit 'tidak ada tren historis' seperti v_hr_turnover_snapshot, period_date berulang tiap hari genuinely bisa membentuk tren (mis. tren jumlah karyawan resigned per hari). Ambigu, dilempar ke fallback LLM.",
    ),
    "v_hr_performance_department_semester": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x departemen x periode review.",
    ),
    "v_hr_performance_by_status_semester": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x status kepegawaian x periode review.",
    ),
    "v_hr_watchlist_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: karyawan x bulan.",
    ),
    "v_lookup_staff_shifts": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="row-level TAPI grain eksplisit '1 baris = 1 karyawan x 1 hari kerja' - label entitas x periode jelas (mirror hr_attendance_daily), beda dari log event tanpa label periode.",
    ),
    "v_lookup_employee_performance": KarakteristikGrain(
        punya_time_series="tidak_pasti",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="row-level '1 baris = 1 review', tanpa label periode eksplisit (beda dari hr_employee_performance_semester yang eksplisit 'periode review') - ambigu.",
    ),
    # --- financial (11) ---
    "v_financial_departmental_margin": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x lini bisnis x bulan.",
    ),
    "v_financial_gop_overhead": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x bulan.",
    ),
    "v_financial_revenue_runrate_daily": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x tanggal.",
    ),
    "v_payroll_department_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x departemen x bulan.",
    ),
    "v_financial_service_charge_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x bulan.",
    ),
    "v_financial_labor_cost_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x bulan.",
    ),
    "v_payroll_access_level_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x level akses x bulan.",
    ),
    "v_financial_business_line_group_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: lini bisnis x bulan (tanpa property_id, level grup).",
    ),
    "v_financial_property_benchmark_monthly": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain: properti x bulan.",
    ),
    "v_lookup_financial_summary": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="grain eksplisit properti x bulan x departemen (bukan row-level event, walau nama 'lookup').",
    ),
    "v_lookup_payroll": KarakteristikGrain(
        punya_time_series="ya",
        punya_dimensi_pembanding="ya",
        catatan="row-level TAPI grain eksplisit '1 baris = 1 karyawan x 1 bulan' - label entitas x periode jelas (mirror hr_employee_monthly).",
    ),
    # --- properties_ref (1) ---
    "v_properties_ref": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="tidak",
        catatan="tabel referensi murni (nama, region, tanggal buka) - 6 baris master properti, tanpa metrik bisnis apa pun untuk dibandingkan/dikomposisi.",
    ),
    # --- employees_directory (1) ---
    "v_employees_directory": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="tidak",
        catatan="tabel direktori murni (nama, properti, departemen, level akses) - tanpa metrik bisnis, dipakai resolusi nama bukan pelaporan.",
    ),
    # --- guests_pii (1) ---
    "guests_contact_view": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="tidak",
        catatan="tabel kontak murni (nama, email, telepon) - tanpa metrik bisnis apa pun.",
    ),
    # --- guests_profile (1) ---
    "guests_profile_view": KarakteristikGrain(
        punya_time_series="tidak",
        punya_dimensi_pembanding="tidak_pasti",
        catatan="1 baris = 1 pelanggan, py atribut kategorikal (loyalitas, kebangsaan) yang berpotensi jadi dimensi komposisi tapi row-level per-tamu tanpa agregasi eksplisit - ambigu.",
    ),
}
