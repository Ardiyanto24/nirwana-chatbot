"""Korpus 67 deskripsi Fungsi bisnis per view (Milestone 3.1) - bahan
pencarian BM25/embedding, bukan katalog nama view (itu
src/config/katalog_view.py).

Ditranskripsi PERSIS (termasuk markup Markdown `**bold**` dan tanda kutip
lurus) dari teks setelah `**Fungsi**: ` di
docs/03-domain-source/katalog-data-chatbot.md, satu baris per view (67
header `####`). Transkripsi dipertahankan apa adanya (bukan dinormalisasi
menghapus markup) supaya tests/layers/retriever/test_korpus_view.py bisa
memparse ulang dokumen sumber via regex dan membandingkan string persis
sama - deteksi drift transkripsi, bukan perbandingan yang sudah
dinormalisasi di kedua sisi.

Key `view_name` harus persis sama dengan DAFTAR_VIEW_PER_DOMAIN
(src/config/katalog_view.py) - diverifikasi bijektif di test.
"""

KORPUS_FUNGSI_VIEW: dict[str, str] = {
    # --- reservation (10) ---
    "v_reservation_room_type_daily": (
        'okupansi/ADR/RevPAR per tipe kamar per hari — "berapa okupansi '
        'Suite di Bali bulan ini", tipe kamar mana penyumbang revenue '
        "terbesar."
    ),
    "v_reservation_channel_daily": (
        "performa tiap kanal booking, rasio pembatalan/no-show per kanal, "
        "tren pergeseran Direct vs OTA."
    ),
    "v_reservation_los_daily": (
        "pola lama menginap (**LOS = Length of Stay**) per tipe "
        'kamar/kanal — mis. "tamu Villa dari OTA menginap berapa malam '
        'rata-rata".'
    ),
    "v_reservation_property_daily": (
        "ringkasan performa harian 1 properti — lead time booking, "
        "pertumbuhan MoM/YoY, ranking dibanding 4 properti lain, tingkat "
        "tamu berulang."
    ),
    "v_reservation_gop_impact_monthly": (
        "menghubungkan strategi harga (deviasi dari tarif dasar) terhadap "
        'dampaknya ke margin profitabilitas (GOP) — "apakah diskon '
        'agresif bulan ini menekan margin".'
    ),
    "v_reservation_pricing_deviation": (
        "seberapa sering & seberapa besar tarif menyimpang dari tarif "
        "dasar, per alasan penyesuaian."
    ),
    "v_reservation_loyalty_daily": (
        "kontribusi tiap tier keanggotaan terhadap booking & revenue."
    ),
    "v_reservation_nationality_daily": (
        "kontribusi tamu domestik vs mancanegara terhadap booking & revenue."
    ),
    "v_lookup_bookings": (
        "status booking hari ini, detail 1 booking spesifik, riwayat "
        "booking 1 tamu (`guest_id`) — kebutuhan Front Office Staff."
    ),
    "v_lookup_daily_occupancy": (
        'ketersediaan kamar real-time per tipe kamar — "tipe kamar apa '
        'yang masih kosong hari ini di properti X".'
    ),
    # --- fnb (11) ---
    "v_fnb_outlet_daily": (
        "performa harian 1 outlet F&B — revenue, rata-rata nota, "
        "pertumbuhan, seberapa besar porsi tamu inhouse yang mampir "
        "(capture rate)."
    ),
    "v_fnb_category_daily": "kontribusi revenue per kategori menu di 1 outlet.",
    "v_fnb_hourly": (
        "pola intraday — jam sibuk sarapan/lunch/dinner/late-night per outlet."
    ),
    "v_fnb_customer_type_daily": (
        "perbandingan perilaku belanja tamu inhouse vs walk-in per outlet."
    ),
    "v_fnb_menu_item_daily": (
        "menu terlaris, dan apakah food cost tiap menu masih sesuai "
        'target — "menu apa yang food cost-nya melebihi target minggu '
        'ini".'
    ),
    "v_fnb_waste_daily": (
        "nilai kerugian dari bahan terbuang, per alasan — mengarahkan "
        "tindakan perbaikan yang tepat."
    ),
    "v_fnb_inventory_status": (
        "jumlah item yang stoknya di bawah ambang aman, per outlet per "
        "hari — sinyal risiko kehabisan bahan."
    ),
    "v_fnb_ingredient_price_daily": (
        "tren harga bahan baku harian — mendeteksi lonjakan harga (mis. "
        "cabai, minyak goreng) sebelum berdampak ke margin."
    ),
    "v_lookup_fnb_inventory": (
        'stok bahan real-time per outlet — "bahan apa yang hampir habis '
        'di outlet X sekarang".'
    ),
    "v_lookup_fnb_transactions": (
        "menu terlaris/total penjualan hari berjalan — granularitas "
        'harian di `mart_aggregated` bisa telat untuk pertanyaan "hari '
        'ini".'
    ),
    "v_lookup_recipe_bom": (
        "komposisi bahan per menu — dipakai untuk info alergi ke tamu "
        "dan sebagai dasar perhitungan food cost."
    ),
    # --- facility (12) ---
    "v_facility_room_status_daily": (
        "status 1 kamar tertentu pada tanggal tertentu — termasuk apakah "
        "sedang out-of-order."
    ),
    "v_housekeeping_room_type_daily": (
        "durasi pembersihan aktual vs baseline per tipe kamar — Villa "
        "(paling luas) butuh waktu jauh lebih lama dari Standard."
    ),
    "v_housekeeping_property_daily": (
        "hubungan okupansi dengan keterlambatan housekeeping — saat "
        "hotel penuh, staf kewalahan sehingga rasio delayed naik."
    ),
    "v_housekeeping_staff_daily": (
        "performa individu 1 staf housekeeping dibanding rata-rata tim "
        "— **sensitivitas lebih tinggi dari label domain**; filter "
        '"hanya data diri sendiri" untuk role Staff ditegakkan di API.'
    ),
    "v_maintenance_ticket_daily": (
        "volume tiket baru, rata-rata durasi penyelesaian, dan apakah "
        "SLA terlampaui — sudah menyertakan threshold SLA & flag "
        "pelanggaran terhitung langsung di view."
    ),
    "v_maintenance_cost_daily": (
        "biaya maintenance harian, dipecah dengan/tanpa penggantian "
        "part, plus tren pertumbuhan."
    ),
    "v_maintenance_room_recurrence_yearly": (
        'kamar mana yang berulang kali bermasalah ("problem room") '
        "dibanding median seluruh kamar."
    ),
    "v_maintenance_property_benchmark_yearly": (
        "benchmarking beban maintenance antar 5 properti, dinormalisasi "
        "terhadap usia gedung (gedung lebih tua wajar lebih sering "
        "rusak)."
    ),
    "v_maintenance_technician_daily": (
        "beban kerja individu 1 teknisi — jumlah tiket ditangani dan jam kerja."
    ),
    "v_lookup_rooms": (
        'status kamar tertentu saat ini — "kamar 305 statusnya apa sekarang".'
    ),
    "v_lookup_housekeeping_log": (
        "durasi pembersihan dan status keterlambatan per sesi — riwayat "
        "pembersihan 1 kamar, atau pekerjaan 1 staf hari itu."
    ),
    "v_lookup_maintenance_tickets": (
        "detail 1 tiket spesifik, atau riwayat tiket per kamar "
        "(`room_id`) atau per teknisi (`assigned_staff_id`)."
    ),
    # --- spa_event (9) ---
    "v_spa_daily": (
        "performa harian spa 1 properti — revenue, jumlah booking, "
        "rasio walk-in, lead time, tingkat pembatalan."
    ),
    "v_spa_customer_type_daily": (
        "perbandingan belanja spa tamu inhouse (cenderung pilih paket "
        "panjang/premium) vs walk-in (pilih layanan pendek/terjangkau)."
    ),
    "v_spa_service_daily": (
        "layanan spa mana yang paling laku dan kontribusinya terhadap "
        "revenue — mis. Couple Package/Hot Stone Massage lebih disukai "
        "tamu menginap, Body Scrub/Reflexology lebih disukai walk-in."
    ),
    "v_event_venue_daily": (
        "tingkat utilisasi 1 venue — venue mana yang kurang "
        "termanfaatkan (kandidat promosi/penurunan harga)."
    ),
    "v_event_property_daily": "tingkat pembatalan event per properti.",
    "v_event_type_daily": (
        "jenis event mana yang paling sering/paling menguntungkan per properti."
    ),
    "v_lookup_spa_bookings": (
        "jadwal booking spa hari ini/mendatang — kebutuhan Spa & Event Staff."
    ),
    "v_lookup_event_bookings": "detail 1 booking event dan ketersediaan venue.",
    "v_lookup_venues": (
        "kapasitas maksimal tiap venue — untuk cek apakah venue muat "
        "untuk jumlah peserta yang diminta."
    ),
    # --- hr (10) ---
    "v_hr_attendance_daily": (
        "ringkasan kehadiran harian per departemen — jumlah "
        "hadir/telat/cuti/absen dan total jam lembur."
    ),
    "v_hr_employee_monthly": (
        "performa kehadiran 1 karyawan dibanding rata-rata "
        "departemennya — sinyal gejala pra-resign (lembur/telat "
        "berlebihan)."
    ),
    "v_hr_employee_performance_semester": (
        "skor & catatan penilaian kinerja 1 karyawan per semester."
    ),
    "v_hr_turnover_snapshot": (
        "tingkat turnover per departemen per properti — snapshot, tidak "
        "ada tren historis (data sumber tidak punya tanggal resign)."
    ),
    "v_hr_headcount_status_daily": (
        "jumlah karyawan per status kepegawaian, per departemen per properti."
    ),
    "v_hr_performance_department_semester": (
        "rata-rata skor kinerja per departemen — benchmark antar "
        "departemen dalam 1 properti."
    ),
    "v_hr_performance_by_status_semester": (
        "apakah karyawan yang resign/terminated punya pola skor kinerja "
        "berbeda dari yang masih aktif (skor cenderung menurun menjelang "
        "resign)."
    ),
    "v_hr_watchlist_monthly": (
        "daftar pantau karyawan dengan pola absensi/keterlambatan "
        "menyimpang jauh dari baseline pribadinya — sinyal dini risiko "
        "resign."
    ),
    "v_lookup_staff_shifts": (
        'status kehadiran karyawan hari ini — "siapa yang belum '
        'absen/terlambat hari ini".'
    ),
    "v_lookup_employee_performance": (
        "skor & catatan performa terakhir 1 karyawan tertentu."
    ),
    # --- financial (11) ---
    "v_financial_departmental_margin": (
        "margin per lini bisnis (Room/F&B/Spa&Event) — perbandingan "
        "profitabilitas antar departemen."
    ),
    "v_financial_gop_overhead": (
        "**GOP (Gross Operating Profit)** dan overhead 1 properti — "
        "metrik ringkasan level properti, bukan per departemen."
    ),
    "v_financial_revenue_runrate_daily": (
        "proyeksi revenue run-rate harian 1 properti."
    ),
    "v_payroll_department_monthly": (
        "total komponen payroll per departemen — untuk analisis biaya "
        "tenaga kerja per departemen."
    ),
    "v_financial_service_charge_monthly": (
        "hubungan pool service charge dengan okupansi — take-home pay "
        "karyawan turun signifikan saat low season."
    ),
    "v_financial_labor_cost_monthly": (
        "biaya tenaga kerja sebagai persentase revenue — indikator "
        "efisiensi operasional."
    ),
    "v_payroll_access_level_monthly": (
        "perbandingan komponen gaji antar level jabatan (staff/manager/corporate)."
    ),
    "v_financial_business_line_group_monthly": (
        "kontribusi tiap lini bisnis (Room/F&B/Spa&Event) terhadap "
        "revenue grup secara keseluruhan."
    ),
    "v_financial_property_benchmark_monthly": (
        "ranking margin GOP 1 properti dibanding 4 properti lain."
    ),
    "v_lookup_financial_summary": (
        "laporan keuangan bulanan standar USALI, per departemen atau "
        "baris ringkasan properti."
    ),
    "v_lookup_payroll": (
        "komponen payroll individual 1 karyawan — kebutuhan Finance Manager."
    ),
    # --- properties_ref (1) ---
    "v_properties_ref": (
        "resolusi nama properti dari kode, atau daftar semua properti "
        'grup — "properti apa saja yang dimiliki Nirwana", "P04 itu '
        'nama hotelnya apa".'
    ),
    # --- employees_directory (1) ---
    "v_employees_directory": (
        "cari nama karyawan dari ID (atau sebaliknya), lihat "
        "departemen/level akses/properti seorang karyawan — dipakai "
        "berbagai domain lain untuk resolusi nama (`staff_id`, "
        "`assigned_staff_id`, dsb yang diteruskan mentah di view lookup "
        "domain lain)."
    ),
    # --- guests_pii (1) ---
    "guests_contact_view": (
        "data kontak untuk menghubungi 1 tamu — **tidak** ada atribut "
        "analitis (loyalitas/kebangsaan) di sini."
    ),
    # --- guests_profile (1) ---
    "guests_profile_view": (
        "atribut analitis 1 tamu — tier loyalitas, asal, tanggal "
        "registrasi. **Tidak** ada kolom kontak di sini."
    ),
}
