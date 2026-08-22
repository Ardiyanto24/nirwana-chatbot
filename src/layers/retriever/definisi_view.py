"""Corpus definisi lengkap 67 view (Milestone 3.2) - bahan penilaian
kecocokan makna (grain, sumber, kolom, catatan), beda dari
korpus_view.py (M3.1, hanya teks Fungsi untuk BM25/embedding).

Ditranskripsi PERSIS (Sumber+Fungsi+tabel Kolom+Catatan inline kalau ada)
dari blok tiap view (header `#### `view_name`` s.d. batas berikutnya) di
docs/03-domain-source/katalog-data-chatbot.md - dibangkitkan otomatis dari
dokumen sumber (bukan diketik ulang manual) untuk menjamin byte-identik,
lalu diverifikasi ulang lewat tests/layers/retriever/test_definisi_view.py
(re-parse independen, mirror pola test_korpus_view.py M3.1).

Key `view_name` sama dengan KORPUS_FUNGSI_VIEW/DAFTAR_VIEW_PER_DOMAIN -
diverifikasi bijektif di test.

CATATAN_LINTAS_DOMAIN: 7 butir aturan lintas-domain (mis. `property_id`
selalu mentah, kolom `property_id` hasil join bukan native) yang menurut
dokumen sumber sendiri "dijelaskan sekali... tidak diulang di tiap view" -
diinject SEKALI ke system prompt (lihat decisions.md Keputusan 6), bukan
diduplikasi ke 67 entri di atas.
"""

DEFINISI_LENGKAP_VIEW: dict[str, str] = {
    # --- reservation (10) ---
    "v_reservation_room_type_daily": (
        """*Sumber: `fact_revenue_room_type_daily` + `dim_property` + `dim_room_type` — grain: properti × tipe kamar × tanggal.*
**Fungsi**: okupansi/ADR/RevPAR per tipe kamar per hari — "berapa okupansi Suite di Bali bulan ini", tipe kamar mana penyumbang revenue terbesar.

| Kolom | Deskripsi |
|---|---|
| `property_id` | Kode properti (P01–P05; P06 kantor pusat tidak punya kamar). |
| `property_name` | Nama hotel. |
| `region` | Wilayah properti. |
| `room_type_name` | `Standard`, `Deluxe`, `Suite`, atau `Villa`. **Villa hanya ada di P01/P04/P05** — Jakarta (P02) & Yogyakarta (P03) tidak punya. |
| `period_date` | Tanggal. |
| `rooms_sold` | Jumlah kamar tipe ini terjual pada tanggal itu. |
| `total_rooms_available` | Jumlah kamar tipe ini yang tersedia untuk dijual. |
| `occupancy_rate` | `rooms_sold ÷ total_rooms_available`, rentang 0–1. |
| `adr` | **Average Daily Rate** — rata-rata tarif kamar terjual (Rupiah). |
| `revpar` | **Revenue Per Available Room** = `adr × occupancy_rate` — metrik profitabilitas utama industri hotel. |
| `revenue` | Total pendapatan kamar tipe ini pada tanggal itu. |
| `room_type_revenue_share_pct` | Kontribusi tipe kamar ini terhadap total revenue kamar properti hari itu. |"""
    ),
    "v_reservation_channel_daily": (
        """*Sumber: `fact_revenue_channel_daily` + `dim_property` + `dim_channel` — grain: properti × kanal booking × tanggal.*
**Fungsi**: performa tiap kanal booking, rasio pembatalan/no-show per kanal, tren pergeseran Direct vs OTA.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `region` | Identitas properti. |
| `channel_name` | `Direct` (tanpa komisi, paling menguntungkan), `OTA-Booking.com`, `OTA-Agoda`, `Travel Agent`, `Corporate` (kontrak korporat, tarif khusus). |
| `period_date` | Tanggal. |
| `revenue` | Revenue dari kanal ini hari itu. |
| `bookings_count` | Jumlah booking. |
| `cancellations_count` | Jumlah pembatalan sebelum check-in. |
| `no_shows_count` | Jumlah tamu tidak datang tanpa pembatalan. |"""
    ),
    "v_reservation_los_daily": (
        """*Sumber: `fact_revenue_los_daily` + `dim_property` + `dim_room_type` + `dim_channel` — grain: properti × tipe kamar × kanal × tanggal.*
**Fungsi**: pola lama menginap (**LOS = Length of Stay**) per tipe kamar/kanal — mis. "tamu Villa dari OTA menginap berapa malam rata-rata".

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `room_type_name`, `channel_name` | Tipe kamar, kanal booking. |
| `period_date` | Tanggal. |
| `avg_los_nights` | Rata-rata jumlah malam menginap. |
| `median_los_nights` | Median jumlah malam menginap. |"""
    ),
    "v_reservation_property_daily": (
        """*Sumber: `fact_revenue_property_daily` + `dim_property` — grain: properti × tanggal.*
**Fungsi**: ringkasan performa harian 1 properti — lead time booking, pertumbuhan MoM/YoY, ranking dibanding 4 properti lain, tingkat tamu berulang.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `region` | Identitas properti. |
| `period_date` | Tanggal. |
| `avg_lead_time_days` / `median_lead_time_days` | Rata-rata/median jarak hari antara `booking_date` dan `check_in_date`. |
| `mom_occupancy_growth` / `yoy_occupancy_growth` | Pertumbuhan okupansi bulan-ke-bulan / tahun-ke-tahun. |
| `mom_adr_growth` / `yoy_adr_growth` | Pertumbuhan ADR MoM/YoY. |
| `mom_revpar_growth` / `yoy_revpar_growth` | Pertumbuhan RevPAR MoM/YoY. |
| `repeat_guest_rate` | Proporsi booking dari tamu yang sudah pernah menginap sebelumnya. |
| `revpar_rank_group` / `adr_rank_group` / `occupancy_rank_group` | Kelompok ranking properti ini dibanding 5 properti lain untuk metrik terkait. |"""
    ),
    "v_reservation_gop_impact_monthly": (
        """*Sumber: `fact_revenue_gop_impact_monthly` + `dim_property` — grain: properti × bulan. Cross-domain: `gop_margin` berasal dari `financial_summary` baris `Overall`.*
**Fungsi**: menghubungkan strategi harga (deviasi dari tarif dasar) terhadap dampaknya ke margin profitabilitas (GOP) — "apakah diskon agresif bulan ini menekan margin".

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Bulan. |
| `avg_pricing_deviation` | Rata-rata deviasi tarif diterapkan vs tarif dasar bulan itu. |
| `gop_margin` | **Gross Operating Profit margin** properti bulan itu (dari domain `financial`). |"""
    ),
    "v_reservation_pricing_deviation": (
        """*Sumber: `fact_revenue_pricing_deviation` + `dim_property` + `dim_pricing_reason` — grain: properti × alasan harga × tanggal.*
**Fungsi**: seberapa sering & seberapa besar tarif menyimpang dari tarif dasar, per alasan penyesuaian.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `reason_name` | `manual` (penyesuaian manual revenue manager), `promo` (diskon terencana low season), `dynamic-pricing-AI` (sistem otomatis — jarang, baru mulai dipakai). |
| `period_date` | Tanggal. |
| `avg_applied_rate` | Rata-rata tarif yang benar-benar diterapkan. |
| `avg_base_rate` | Rata-rata tarif dasar (rack rate). |
| `avg_deviation_pct` | Rata-rata persentase deviasi `applied_rate` dari `base_rate`. |
| `day_share_pct` | Persentase hari dalam periode yang memakai alasan harga ini. |"""
    ),
    "v_reservation_loyalty_daily": (
        """*Sumber: `fact_revenue_loyalty_daily` + `dim_property` + `dim_loyalty_tier` — grain: properti × tier loyalitas × tanggal.*
**Fungsi**: kontribusi tiap tier keanggotaan terhadap booking & revenue.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `loyalty_tier_name` | `none` (bukan member), `Silver`, `Gold`, `Platinum` (tertinggi). |
| `period_date` | Tanggal. |
| `bookings_count` | Jumlah booking tier ini. |
| `revenue` | Revenue dari tier ini. |"""
    ),
    "v_reservation_nationality_daily": (
        """*Sumber: `fact_revenue_nationality_daily` + `dim_property` + `dim_nationality_group` — grain: properti × kelompok kebangsaan × tanggal.*
**Fungsi**: kontribusi tamu domestik vs mancanegara terhadap booking & revenue.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `nationality_group_name` | `Domestik` atau `Mancanegara` (dikategorikan dari kolom `nationality` mentah). |
| `period_date` | Tanggal. |
| `bookings_count`, `revenue` | Jumlah booking dan revenue kelompok ini. |"""
    ),
    "v_lookup_bookings": (
        """*Sumber: `mart_cleaned.bookings` (row-level, tanpa join) — grain: 1 baris = 1 reservasi.*
**Fungsi**: status booking hari ini, detail 1 booking spesifik, riwayat booking 1 tamu (`guest_id`) — kebutuhan Front Office Staff.

| Kolom | Deskripsi |
|---|---|
| `booking_id` | ID reservasi. |
| `property_id` | Properti yang dipesan. |
| `guest_id` | Pemesan — **selalu G00001–G18000** (pelanggan lokal F&B/spa tidak pernah booking kamar). |
| `room_type` | `Standard`, `Deluxe`, `Suite`, `Villa`. |
| `booking_channel` | `Direct`, `OTA-Booking.com`, `OTA-Agoda`, `Travel Agent`, `Corporate`. |
| `check_in_date` / `check_out_date` | Tanggal masuk/keluar. |
| `booking_date` | Tanggal reservasi dibuat (selalu ≤ `check_in_date`). |
| `nights` | Jumlah malam. |
| `room_rate` | Tarif per malam. |
| `total_amount` | `room_rate × nights`. |
| `status` | `completed` (sudah checkout), `confirmed` (belum menginap), `cancelled`, `no-show`. **Hanya `completed`/`confirmed` dihitung sebagai revenue** — konvensi yang berlaku di seluruh database. |

> **Catatan**: tidak join ke `guests` — nama/kontak tamu pemesan hanya bisa didapat lewat `guests_contact_view` (domain terpisah `guests_pii`)."""
    ),
    "v_lookup_daily_occupancy": (
        """*Sumber: `mart_cleaned.daily_occupancy` — grain: properti × tipe kamar × tanggal.*
**Fungsi**: ketersediaan kamar real-time per tipe kamar — "tipe kamar apa yang masih kosong hari ini di properti X".

| Kolom | Deskripsi |
|---|---|
| `property_id`, `room_type`, `date` | Identitas baris. |
| `rooms_sold` | Kamar terjual malam itu. |
| `adr` | Average Daily Rate. |
| `total_rooms_available` | Kamar tersedia untuk tipe ini. |
| `occupancy_rate` | `rooms_sold ÷ total_rooms_available`. |
| `revpar` | Revenue Per Available Room. |"""
    ),
    # --- fnb (11) ---
    "v_fnb_outlet_daily": (
        """*Sumber: `fact_fnb_outlet_daily` + `dim_outlet` + `dim_property` + `dim_outlet_type` — grain: outlet × tanggal.*
**Fungsi**: performa harian 1 outlet F&B — revenue, rata-rata nota, pertumbuhan, seberapa besar porsi tamu inhouse yang mampir (capture rate).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Properti pemilik outlet. |
| `outlet_id`, `outlet_name` | Identitas outlet. |
| `outlet_type_name` | `Restaurant`, `Bar`, atau `Room Service` (Room Service tidak menerima walk-in). |
| `period_date` | Tanggal. |
| `revenue` | Revenue outlet hari itu. |
| `transaction_count` | Jumlah struk. |
| `avg_check` | Rata-rata nilai per struk. |
| `mom_revenue_growth` / `yoy_revenue_growth` | Pertumbuhan revenue MoM/YoY. |
| `capture_rate` | Porsi tamu inhouse (yang sedang menginap) yang memakai outlet ini. |
| `walk_in_ratio` | Porsi transaksi dari pelanggan luar (bukan tamu menginap). |
| `revenue_rank_vs_outlet_type_avg` | Ranking revenue outlet ini dibanding rata-rata outlet sejenis. |"""
    ),
    "v_fnb_category_daily": (
        """*Sumber: `fact_fnb_category_daily` + `dim_outlet` + `dim_property` + `dim_fnb_category` — grain: outlet × kategori × tanggal.*
**Fungsi**: kontribusi revenue per kategori menu di 1 outlet.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `outlet_id`, `outlet_name` | Identitas outlet. |
| `category_name` | `Food`, `Beverage`, atau `Dessert`. |
| `period_date` | Tanggal. |
| `revenue` | Revenue kategori ini hari itu. |"""
    ),
    "v_fnb_hourly": (
        """*Sumber: `fact_fnb_hourly` + `dim_outlet` + `dim_property` — grain: outlet × tanggal × jam.*
**Fungsi**: pola intraday — jam sibuk sarapan/lunch/dinner/late-night per outlet.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `outlet_id`, `outlet_name` | Identitas outlet. |
| `period_date` | Tanggal. |
| `hour_of_day` | Jam (0–23). |
| `transaction_count` | Jumlah struk pada jam itu. |"""
    ),
    "v_fnb_customer_type_daily": (
        """*Sumber: `fact_fnb_customer_type_daily` + `dim_outlet` + `dim_property` + `dim_customer_type` — grain: outlet × tipe pelanggan × tanggal.*
**Fungsi**: perbandingan perilaku belanja tamu inhouse vs walk-in per outlet.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `outlet_id`, `outlet_name` | Identitas outlet. |
| `customer_type_name` | `inhouse` (tamu yang sedang menginap) atau `walk-in` (pelanggan dari luar). |
| `period_date` | Tanggal. |
| `revenue`, `visit_count` | Revenue dan jumlah kunjungan kelompok ini. |
| `revenue_per_visit` | Rata-rata belanja per kunjungan. |"""
    ),
    "v_fnb_menu_item_daily": (
        """*Sumber: `fact_fnb_menu_item_daily` + `dim_outlet` + `dim_property` — grain: outlet × item menu × tanggal.*
**Fungsi**: menu terlaris, dan apakah food cost tiap menu masih sesuai target — "menu apa yang food cost-nya melebihi target minggu ini".

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `outlet_id`, `outlet_name` | Identitas outlet. |
| `item_name` | Nama menu. |
| `period_date` | Tanggal. |
| `revenue`, `quantity_sold` | Revenue dan porsi terjual. |
| `food_cost_ratio_actual` | Rasio biaya bahan aktual terhadap harga jual. |
| `food_cost_ratio_target` | Target rasio (standar: Food 34%, Beverage 24%, Dessert 28%). |
| `food_cost_deviation` | Selisih aktual vs target. |"""
    ),
    "v_fnb_waste_daily": (
        """*Sumber: `fact_fnb_waste_daily` + `dim_outlet` + `dim_property` + `dim_waste_reason` — grain: outlet × alasan waste × tanggal.*
**Fungsi**: nilai kerugian dari bahan terbuang, per alasan — mengarahkan tindakan perbaikan yang tepat.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `outlet_id`, `outlet_name` | Identitas outlet. |
| `reason_name` | `overproduction` (masak berlebihan — bisa dicegah lewat forecasting), `expired` (kadaluarsa — perbaiki rotasi stok/FIFO), `spillage` (tumpah/rusak saat penanganan — pelatihan staf). |
| `period_date` | Tanggal. |
| `waste_value` | Nilai kerugian (Rupiah). |
| `waste_quantity` | Jumlah bahan terbuang. |
| `waste_ratio` | Rasio waste terhadap total pemakaian bahan (baseline industri ~3.5%). |"""
    ),
    "v_fnb_inventory_status": (
        """*Sumber: `fact_fnb_inventory_status` + `dim_outlet` + `dim_property` — grain: outlet × tanggal.*
**Fungsi**: jumlah item yang stoknya di bawah ambang aman, per outlet per hari — sinyal risiko kehabisan bahan.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name`, `outlet_id`, `outlet_name` | Identitas outlet. |
| `period_date` | Tanggal. |
| `low_stock_item_count` | Jumlah item bahan dengan stok di bawah ambang minimum (`stock_current < stock_min_threshold`). |"""
    ),
    "v_fnb_ingredient_price_daily": (
        """*Sumber: `fact_fnb_ingredient_price_daily` — grain: bahan × tanggal. **Tanpa `property_id`** — harga bahan bersifat global, tidak terikat 1 outlet/properti.*
**Fungsi**: tren harga bahan baku harian — mendeteksi lonjakan harga (mis. cabai, minyak goreng) sebelum berdampak ke margin.

| Kolom | Deskripsi |
|---|---|
| `ingredient_id` | Kode bahan baku. |
| `period_date` | Tanggal. |
| `avg_unit_cost` | Rata-rata harga per satuan bahan (Rp/kg, Rp/liter, atau Rp/pcs) hari itu. |"""
    ),
    "v_lookup_fnb_inventory": (
        """*Sumber: `mart_cleaned.fnb_inventory` LEFT JOIN `fnb_outlets` — grain: outlet × bahan (snapshot per 30 Juni 2026, bukan time-series).*
**Fungsi**: stok bahan real-time per outlet — "bahan apa yang hampir habis di outlet X sekarang".

| Kolom | Deskripsi |
|---|---|
| `outlet_id` | Outlet. |
| `ingredient_id`, `ingredient_name` | Identitas bahan. |
| `unit` | `kg`, `liter`, atau `pcs`. |
| `stock_current` | Stok tersedia saat ini. |
| `stock_min_threshold` | Batas aman (setara kebutuhan 3 hari berdasar rata-rata pemakaian). |
| `unit_cost` | Harga terkini bahan ini. |
| `property_id` | **Di-join dari `fnb_outlets`** — `fnb_inventory` sendiri tidak punya kolom ini secara native. |"""
    ),
    "v_lookup_fnb_transactions": (
        """*Sumber: `mart_cleaned.fnb_transactions` LEFT JOIN `fnb_outlets` — grain: 1 baris = 1 item dalam 1 struk.*
**Fungsi**: menu terlaris/total penjualan hari berjalan — granularitas harian di `mart_aggregated` bisa telat untuk pertanyaan "hari ini".

| Kolom | Deskripsi |
|---|---|
| `transaction_id` | **ID struk, bukan primary key baris** — berulang untuk tiap item dalam struk yang sama. |
| `outlet_id` | Outlet. |
| `guest_id` | **Nullable.** Terisi selalu untuk `customer_type='inhouse'`; untuk `walk-in` hanya ~30% terisi (member/repeat), ~70% kosong — pelanggan bayar tanpa memberi identitas, bukan data kotor. |
| `customer_type` | `inhouse` (tamu sedang menginap) atau `walk-in` (pelanggan luar). |
| `transaction_datetime` | Tanggal + jam transaksi. |
| `item_name` | Nama menu. |
| `category` | `Food`, `Beverage`, `Dessert`. |
| `quantity` | Jumlah porsi item ini dalam struk. |
| `unit_price`, `total_price` | Harga satuan dan total (`unit_price × quantity`). |
| `property_id` | **Di-join dari `fnb_outlets`** — tidak native di tabel sumber. |"""
    ),
    "v_lookup_recipe_bom": (
        """*Sumber: `mart_cleaned.recipe_bom` — grain: menu × bahan. Tanpa `property_id` — komposisi resep bersifat global, sama di semua properti.*
**Fungsi**: komposisi bahan per menu — dipakai untuk info alergi ke tamu dan sebagai dasar perhitungan food cost.

| Kolom | Deskripsi |
|---|---|
| `item_name` | Nama menu. |
| `ingredient_id` | Bahan baku penyusun. |
| `qty_per_portion` | Takaran bahan per 1 porsi. |"""
    ),
    # --- facility (12) ---
    "v_facility_room_status_daily": (
        """*Sumber: `fact_facility_room_status_daily` + `dim_room` + `dim_property` + `dim_room_type` — grain: kamar × tanggal (snapshot).*
**Fungsi**: status 1 kamar tertentu pada tanggal tertentu — termasuk apakah sedang out-of-order.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Properti pemilik kamar. |
| `room_id` | Kode kamar. |
| `room_type_name` | Tipe kamar. |
| `period_date` | Tanggal snapshot. |
| `status` | Kondisi kamar (`occupied`, `available`, `cleaning`, `maintenance`, `out-of-order`). |
| `is_out_of_order` | Boolean — kamar rusak berat, tidak bisa dijual. |"""
    ),
    "v_housekeeping_room_type_daily": (
        """*Sumber: `fact_housekeeping_room_type_daily` + `dim_property` + `dim_room_type` — grain: properti × tipe kamar × tanggal.*
**Fungsi**: durasi pembersihan aktual vs baseline per tipe kamar — Villa (paling luas) butuh waktu jauh lebih lama dari Standard.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `room_type_name` | Tipe kamar. |
| `period_date` | Tanggal. |
| `avg_cleaning_duration_minutes` | Rata-rata durasi pembersihan aktual. |
| `baseline_duration_minutes` | Durasi baseline/acuan untuk tipe kamar ini. |"""
    ),
    "v_housekeeping_property_daily": (
        """*Sumber: `fact_housekeeping_property_daily` + `dim_property` — grain: properti × tanggal.*
**Fungsi**: hubungan okupansi dengan keterlambatan housekeeping — saat hotel penuh, staf kewalahan sehingga rasio delayed naik.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Tanggal. |
| `delayed_rate` | Rasio sesi pembersihan berstatus `delayed`. |
| `occupancy_rate` | Okupansi properti hari itu (untuk korelasi). |"""
    ),
    "v_housekeeping_staff_daily": (
        """*Sumber: `fact_housekeeping_staff_daily` + `dim_employee` — grain: staff × tanggal.*
**Fungsi**: performa individu 1 staf housekeeping dibanding rata-rata tim — **sensitivitas lebih tinggi dari label domain**; filter "hanya data diri sendiri" untuk role Staff ditegakkan di API.

| Kolom | Deskripsi |
|---|---|
| `staff_id` | ID karyawan housekeeping. |
| `staff_name` | Nama staf (dari `dim_employee.full_name`). |
| `period_date` | Tanggal. |
| `avg_cleaning_duration_minutes` | Rata-rata durasi pembersihan staf ini. |
| `team_avg_duration_minutes` | Rata-rata durasi tim/properti untuk perbandingan. |
| `property_id` | Properti staf ini bertugas (di-join dari `dim_employee`). |"""
    ),
    "v_maintenance_ticket_daily": (
        """*Sumber: `fact_maintenance_ticket_daily` + `dim_property` + `dim_facility_area` + `dim_issue_type` + `dim_priority` — grain: properti × area × jenis isu × prioritas × tanggal.*
**Fungsi**: volume tiket baru, rata-rata durasi penyelesaian, dan apakah SLA terlampaui — sudah menyertakan threshold SLA & flag pelanggaran terhitung langsung di view.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `facility_area_name` | Lokasi kerusakan (`Room`, `Pool`, `Lobby`, `Elevator`, `Restaurant`, `Gym`, `Parking`). |
| `issue_type_name` | Jenis kerusakan (`AC`, `Plumbing`, `Electrical`, `Furniture`, `TV/Elektronik`, `Kunci/Lock`, `Lainnya`). |
| `priority_name` | `critical`, `high`, `medium`, `low`. |
| `period_date` | Tanggal. |
| `new_ticket_count` | Jumlah tiket baru. |
| `avg_sla_duration_hours` | Rata-rata durasi penyelesaian (jam). |
| `pending_count` | Jumlah tiket masih `open`/`in-progress`. |
| `sla_threshold_hours` | **Kolom turunan** — batas SLA sesuai prioritas: `critical`=8 jam, `high`=24 jam, `medium`=48 jam, `low`=72 jam. |
| `avg_exceeds_sla_threshold` | **Kolom turunan** (boolean) — apakah `avg_sla_duration_hours` melebihi `sla_threshold_hours`. NULL jika durasi belum ada. |"""
    ),
    "v_maintenance_cost_daily": (
        """*Sumber: `fact_maintenance_cost_daily` + `dim_property` + `dim_issue_type` — grain: properti × jenis isu × tanggal.*
**Fungsi**: biaya maintenance harian, dipecah dengan/tanpa penggantian part, plus tren pertumbuhan.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `issue_type_name` | Jenis kerusakan. |
| `period_date` | Tanggal. |
| `total_cost` | Total biaya = `(labor_hours × tarif teknisi) + harga part`. |
| `cost_with_parts` / `cost_without_parts` | Pemecahan biaya berdasar ada/tidaknya penggantian part. |
| `mom_cost_growth` / `yoy_cost_growth` | Pertumbuhan biaya MoM/YoY. |"""
    ),
    "v_maintenance_room_recurrence_yearly": (
        """*Sumber: `fact_maintenance_room_recurrence_yearly` + `dim_room` + `dim_property` + `dim_room_type` — grain: kamar × tahun.*
**Fungsi**: kamar mana yang berulang kali bermasalah ("problem room") dibanding median seluruh kamar.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `room_id`, `room_type_name` | Kamar dan tipenya. |
| `year` | Tahun. |
| `ticket_count` | Jumlah tiket maintenance kamar ini tahun itu. |
| `vs_median_ratio` | Rasio jumlah tiket kamar ini terhadap median seluruh kamar. |"""
    ),
    "v_maintenance_property_benchmark_yearly": (
        """*Sumber: `fact_maintenance_property_benchmark_yearly` + `dim_property` — grain: properti × tahun.*
**Fungsi**: benchmarking beban maintenance antar 5 properti, dinormalisasi terhadap usia gedung (gedung lebih tua wajar lebih sering rusak).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `year` | Tahun. |
| `tickets_per_room` | Rata-rata tiket per kamar. |
| `building_age_years` | Usia gedung (Jakarta dibangun 2012 — paling tua; Lombok 2020 — paling baru). |
| `tickets_per_room_normalized` | `tickets_per_room` yang sudah dinormalisasi terhadap usia gedung, untuk perbandingan adil antar properti. |"""
    ),
    "v_maintenance_technician_daily": (
        """*Sumber: `fact_maintenance_technician_daily` + `dim_employee` — grain: teknisi × tanggal.*
**Fungsi**: beban kerja individu 1 teknisi — jumlah tiket ditangani dan jam kerja.

| Kolom | Deskripsi |
|---|---|
| `assigned_staff_id` | ID teknisi. |
| `technician_name` | Nama teknisi (dari `dim_employee.full_name`). |
| `period_date` | Tanggal. |
| `ticket_count` | Jumlah tiket ditangani teknisi ini. |
| `labor_hours` | Total jam kerja. |
| `property_id` | Properti teknisi ini bertugas (di-join dari `dim_employee`). |"""
    ),
    "v_lookup_rooms": (
        """*Sumber: `mart_cleaned.rooms` — grain: 1 baris = 1 kamar fisik.*
**Fungsi**: status kamar tertentu saat ini — "kamar 305 statusnya apa sekarang".

| Kolom | Deskripsi |
|---|---|
| `room_id` | Kode kamar. |
| `property_id` | Properti. |
| `room_number` | Nomor kamar (format `{lantai}{urutan}`; Villa: `V01`, `V02`, dst). |
| `room_type` | `Standard`, `Deluxe`, `Suite`, `Villa`. |
| `floor` | Lantai (Villa selalu 1, standalone). |
| `status` | `occupied`, `available`, `cleaning`, `maintenance`, `out-of-order`. |"""
    ),
    "v_lookup_housekeeping_log": (
        """*Sumber: `mart_cleaned.housekeeping_log` LEFT JOIN `rooms` — grain: 1 baris = 1 sesi pembersihan.*
**Fungsi**: durasi pembersihan dan status keterlambatan per sesi — riwayat pembersihan 1 kamar, atau pekerjaan 1 staf hari itu.

| Kolom | Deskripsi |
|---|---|
| `log_id` | ID sesi pembersihan. |
| `room_id` | Kamar yang dibersihkan. |
| `date` | Tanggal. |
| `cleaning_start_time` / `cleaning_end_time` | Waktu mulai/selesai (shift housekeeping 08:00–15:00). |
| `staff_id` | Staf yang membersihkan (departemen Housekeeping). |
| `status` | `completed` atau `delayed`. |
| `property_id` | **Di-join dari `rooms`** — `housekeeping_log` sendiri tidak punya kolom ini native. |"""
    ),
    "v_lookup_maintenance_tickets": (
        """*Sumber: `mart_cleaned.maintenance_tickets` (tanpa join) — grain: 1 baris = 1 tiket.*
**Fungsi**: detail 1 tiket spesifik, atau riwayat tiket per kamar (`room_id`) atau per teknisi (`assigned_staff_id`).

| Kolom | Deskripsi |
|---|---|
| `ticket_id` | ID tiket. |
| `property_id` | Properti. |
| `room_id` | **Nullable** — kosong jika kerusakan di fasilitas umum (Pool/Lobby/Elevator/Restaurant/Gym/Parking, bukan di dalam kamar). |
| `facility_area` | Lokasi kerusakan. |
| `issue_type` | Jenis kerusakan. |
| `reported_date` | Kapan dilaporkan. |
| `resolved_date` | **Nullable** — kosong jika status masih `open`/`in-progress`. |
| `status` | `open`, `in-progress`, `resolved`. |
| `priority` | `low`, `medium`, `high`, `critical` (menentukan SLA — lihat `v_maintenance_ticket_daily`). |
| `assigned_staff_id` | Teknisi yang ditugaskan. |
| `labor_hours` | Jam kerja teknisi untuk tiket ini. |
| `parts_replaced` | **Nullable** (~52% kosong) — nama part yang diganti, kosong jika tidak ada penggantian part. |
| `cost` | Total biaya tiket = `(labor_hours × tarif teknisi) + harga part`. |"""
    ),
    # --- spa_event (9) ---
    "v_spa_daily": (
        """*Sumber: `fact_spa_daily` + `dim_property` — grain: properti × tanggal.*
**Fungsi**: performa harian spa 1 properti — revenue, jumlah booking, rasio walk-in, lead time, tingkat pembatalan.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Tanggal. |
| `revenue`, `booking_count` | Revenue dan jumlah booking spa hari itu. |
| `walk_in_ratio` | Porsi booking dari pelanggan luar (bukan tamu menginap). |
| `avg_lead_time_days` / `median_lead_time_days` | Rata-rata/median jarak hari antara booking dibuat dan treatment dilakukan (spa sering dadakan, 1–2 hari). |
| `cancellation_rate` | Rasio pembatalan. |"""
    ),
    "v_spa_customer_type_daily": (
        """*Sumber: `fact_spa_customer_type_daily` + `dim_property` + `dim_customer_type` — grain: properti × tipe pelanggan × tanggal.*
**Fungsi**: perbandingan belanja spa tamu inhouse (cenderung pilih paket panjang/premium) vs walk-in (pilih layanan pendek/terjangkau).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `customer_type_name` | `inhouse` atau `walk-in`. |
| `period_date` | Tanggal. |
| `revenue`, `visit_count` | Revenue dan kunjungan kelompok ini. |
| `revenue_per_visit` | Rata-rata belanja per kunjungan. |"""
    ),
    "v_spa_service_daily": (
        """*Sumber: `fact_spa_service_daily` + `dim_property` + `dim_spa_service` — grain: properti × layanan × tanggal.*
**Fungsi**: layanan spa mana yang paling laku dan kontribusinya terhadap revenue — mis. Couple Package/Hot Stone Massage lebih disukai tamu menginap, Body Scrub/Reflexology lebih disukai walk-in.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `service_name` | Nama layanan (9 jenis: Couple Package, Hot Stone Massage, Aromatherapy Massage, Balinese Massage, Facial Treatment, Body Scrub, Reflexology, dst). |
| `period_date` | Tanggal. |
| `booking_count`, `revenue` | Jumlah booking dan revenue layanan ini. |
| `revenue_share_pct` | Kontribusi layanan ini terhadap total revenue spa hari itu. |"""
    ),
    "v_event_venue_daily": (
        """*Sumber: `fact_event_venue_daily` + `dim_venue` + `dim_property` + `dim_venue_type` — grain: venue × tanggal.*
**Fungsi**: tingkat utilisasi 1 venue — venue mana yang kurang termanfaatkan (kandidat promosi/penurunan harga).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Properti pemilik venue. |
| `venue_id`, `venue_name` | Identitas venue. |
| `venue_type_name` | `Ballroom`, `Meeting Room`, atau `Outdoor`. |
| `max_capacity` | Kapasitas maksimal venue. |
| `period_date` | Tanggal. |
| `bookings_pipeline_count` / `revenue_pipeline` | Booking dan revenue dalam pipeline untuk venue ini. |
| `utilization_rate` | `capacity_booked ÷ max_capacity`. |
| `mom_revenue_growth` / `yoy_revenue_growth` | Pertumbuhan revenue MoM/YoY. |
| `low_utilization_days_last_30` | Jumlah hari dengan utilisasi rendah (<45%) dalam 30 hari terakhir. |"""
    ),
    "v_event_property_daily": (
        """*Sumber: `fact_event_property_daily` + `dim_property` — grain: properti × tanggal.*
**Fungsi**: tingkat pembatalan event per properti.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Tanggal. |
| `cancellation_rate` | Rasio event yang dibatalkan. |"""
    ),
    "v_event_type_daily": (
        """*Sumber: `fact_event_type_daily` + `dim_property` + `dim_event_type` — grain: properti × jenis event × tanggal.*
**Fungsi**: jenis event mana yang paling sering/paling menguntungkan per properti.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `event_type_name` | `Corporate Meeting`, `Wedding`, `Conference`, `Gala Dinner`, `Product Launch`, `Training/Workshop`. |
| `period_date` | Tanggal. |
| `event_count`, `revenue` | Jumlah event dan revenue jenis ini. |"""
    ),
    "v_lookup_spa_bookings": (
        """*Sumber: `mart_cleaned.spa_bookings` — grain: 1 baris = 1 booking spa.*
**Fungsi**: jadwal booking spa hari ini/mendatang — kebutuhan Spa & Event Staff.

| Kolom | Deskripsi |
|---|---|
| `spa_booking_id` | ID booking. |
| `property_id` | Properti. |
| `guest_id` | **Nullable** (~21% kosong) — kosong untuk walk-in anonim. |
| `customer_type` | `inhouse` atau `walk-in`. |
| `service_name` | Jenis treatment. |
| `booking_date` | Kapan dipesan. |
| `service_date` | Kapan treatment dilakukan. |
| `duration_minutes` | Durasi treatment (45/60/90/120 menit). |
| `price` | Harga (sudah disesuaikan multiplier properti). |
| `status` | `completed`, `cancelled`, `confirmed`. |"""
    ),
    "v_lookup_event_bookings": (
        """*Sumber: `mart_cleaned.event_bookings` — grain: 1 baris = 1 event.*
**Fungsi**: detail 1 booking event dan ketersediaan venue.

| Kolom | Deskripsi |
|---|---|
| `event_id` | ID event. |
| `property_id` | Properti. |
| `venue_id`, `venue_name` | Venue yang dipakai. |
| `client_name` | Nama klien — **teks bebas**, bukan FK ke `guests`. Wedding: nama pasangan; korporat: nama perusahaan. **Tidak ada kolom `guest_id` sama sekali** di tabel ini — klien event tidak terhubung ke tamu terdaftar. |
| `event_type` | `Corporate Meeting`, `Wedding`, `Conference`, `Gala Dinner`, `Product Launch`, `Training/Workshop`. |
| `event_date` | Tanggal acara. |
| `capacity_booked` | Jumlah peserta (selalu ≤ `max_capacity` venue). |
| `total_revenue` | Total pendapatan event. |
| `status` | `completed`, `cancelled`, `confirmed`. |"""
    ),
    "v_lookup_venues": (
        """*Sumber: `mart_cleaned.venues` — grain: 1 baris = 1 venue.*
**Fungsi**: kapasitas maksimal tiap venue — untuk cek apakah venue muat untuk jumlah peserta yang diminta.

| Kolom | Deskripsi |
|---|---|
| `venue_id` | ID venue. |
| `property_id` | Properti. |
| `venue_name` | Nama venue. |
| `venue_type` | `Ballroom`, `Meeting Room`, `Outdoor`. |
| `max_capacity` | Kapasitas maksimal peserta. |"""
    ),
    # --- hr (10) ---
    "v_hr_attendance_daily": (
        """*Sumber: `fact_hr_attendance_daily` + `dim_property` + `dim_department` — grain: properti × departemen × tanggal.*
**Fungsi**: ringkasan kehadiran harian per departemen — jumlah hadir/telat/cuti/absen dan total jam lembur.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `department_name` | Salah satu dari 8 departemen: `Housekeeping`, `F&B`, `Revenue`, `Spa&Event`, `Facility`, `HR`, `Finance`, `Corporate`. |
| `period_date` | Tanggal. |
| `present_count` / `late_count` / `leave_count` / `absent_count` | Jumlah karyawan per status kehadiran hari itu. |
| `overtime_hours_total` | Total jam lembur departemen hari itu. |"""
    ),
    "v_hr_employee_monthly": (
        """*Sumber: `fact_hr_employee_monthly` + `dim_employee` + `dim_property` + `dim_department` — grain: karyawan × bulan.*
**Fungsi**: performa kehadiran 1 karyawan dibanding rata-rata departemennya — sinyal gejala pra-resign (lembur/telat berlebihan).

| Kolom | Deskripsi |
|---|---|
| `employee_id`, `full_name` | Identitas karyawan. |
| `department_name` | Departemen. |
| `property_id`, `property_name` | Properti tempat bertugas. |
| `period_date` | Bulan. |
| `overtime_hours` | Total jam lembur bulan itu. |
| `overtime_vs_dept_avg` | Perbandingan terhadap rata-rata departemen. |
| `late_rate` | Rasio keterlambatan bulan itu. |
| `late_vs_dept_avg` | Perbandingan terhadap rata-rata departemen. |"""
    ),
    "v_hr_employee_performance_semester": (
        """*Sumber: `fact_hr_employee_performance_semester` + `dim_employee` + `dim_property` + `dim_department` — grain: karyawan × periode review.*
**Fungsi**: skor & catatan penilaian kinerja 1 karyawan per semester.

| Kolom | Deskripsi |
|---|---|
| `employee_id`, `full_name` | Identitas karyawan. |
| `department_name` | Departemen. |
| `property_id`, `property_name` | Properti. |
| `review_period` | Format `YYYY-S1` (Jan–Jun) atau `YYYY-S2` (Jul–Des). |
| `score` | Skor 1.00–5.00: 4.3–5.0 sangat baik, 3.5–4.29 baik, 2.5–3.49 cukup, 1.0–2.49 di bawah standar. |
| `notes` | Catatan kualitatif, konsisten dengan rentang skor. |"""
    ),
    "v_hr_turnover_snapshot": (
        """*Sumber: `fact_hr_turnover_snapshot` + `dim_property` + `dim_department` — grain: properti × departemen × tanggal (snapshot).*
**Fungsi**: tingkat turnover per departemen per properti — snapshot, tidak ada tren historis (data sumber tidak punya tanggal resign).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `department_name` | Departemen. |
| `period_date` | Tanggal snapshot. |
| `turnover_rate` | Rasio karyawan keluar (resigned/terminated) di departemen ini. |"""
    ),
    "v_hr_headcount_status_daily": (
        """*Sumber: `fact_hr_headcount_status_daily` + `dim_property` + `dim_department` + `dim_employee_status` — grain: properti × departemen × status × tanggal (snapshot).*
**Fungsi**: jumlah karyawan per status kepegawaian, per departemen per properti.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `department_name` | Departemen. |
| `status_name` | `active`, `resigned`, atau `terminated`. |
| `period_date` | Tanggal snapshot. |
| `employee_count` | Jumlah karyawan dengan status ini. |"""
    ),
    "v_hr_performance_department_semester": (
        """*Sumber: `fact_hr_performance_department_semester` + `dim_property` + `dim_department` — grain: properti × departemen × periode review.*
**Fungsi**: rata-rata skor kinerja per departemen — benchmark antar departemen dalam 1 properti.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `department_name` | Departemen. |
| `review_period` | `YYYY-S1`/`YYYY-S2`. |
| `avg_performance_score` | Rata-rata skor kinerja departemen ini periode itu. |"""
    ),
    "v_hr_performance_by_status_semester": (
        """*Sumber: `fact_hr_performance_by_status_semester` + `dim_property` + `dim_employee_status` — grain: properti × status kepegawaian × periode review.*
**Fungsi**: apakah karyawan yang resign/terminated punya pola skor kinerja berbeda dari yang masih aktif (skor cenderung menurun menjelang resign).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `status_name` | `active`, `resigned`, `terminated`. |
| `review_period` | `YYYY-S1`/`YYYY-S2`. |
| `avg_performance_score` | Rata-rata skor kelompok status ini. |"""
    ),
    "v_hr_watchlist_monthly": (
        """*Sumber: `fact_hr_watchlist_monthly` + `dim_employee` + `dim_property` + `dim_department` — grain: karyawan × bulan.*
**Fungsi**: daftar pantau karyawan dengan pola absensi/keterlambatan menyimpang jauh dari baseline pribadinya — sinyal dini risiko resign.

| Kolom | Deskripsi |
|---|---|
| `employee_id`, `full_name` | Identitas karyawan. |
| `department_name` | Departemen. |
| `property_id`, `property_name` | Properti. |
| `period_date` | Bulan. |
| `current_absence_rate` / `baseline_absence_rate` | Tingkat absensi bulan berjalan vs baseline historis karyawan ini. |
| `current_late_rate` / `baseline_late_rate` | Tingkat keterlambatan bulan berjalan vs baseline. |
| `absence_deviation_ratio` / `late_deviation_ratio` | Rasio penyimpangan dari baseline. |
| `in_watchlist` | Boolean — masuk daftar pantau jika deviasi >5x baseline. |"""
    ),
    "v_lookup_staff_shifts": (
        """*Sumber: `mart_cleaned.staff_shifts` LEFT JOIN `employees` — grain: 1 baris = 1 karyawan × 1 hari kerja.*
**Fungsi**: status kehadiran karyawan hari ini — "siapa yang belum absen/terlambat hari ini".

| Kolom | Deskripsi |
|---|---|
| `shift_id` | ID shift. |
| `employee_id` | Karyawan. |
| `property_id` | **Di-join dari `employees`** — hanya kolom ini yang ditarik (bukan kolom lain) supaya tidak diam-diam bocor ke domain `employees_directory`. |
| `date` | Tanggal. |
| `shift_type` | `Morning` (07:00–15:00, semua departemen), `Afternoon`/`Night` (hanya departemen operasional). |
| `clock_in` / `clock_out` | **Nullable** — kosong jika `status` adalah `absent` atau `leave`. |
| `status` | `present` (87%), `late` (6%), `leave` (5%), `absent` (2%). |"""
    ),
    "v_lookup_employee_performance": (
        """*Sumber: `mart_cleaned.employee_performance` LEFT JOIN `employees` — grain: 1 baris = 1 review.*
**Fungsi**: skor & catatan performa terakhir 1 karyawan tertentu.

| Kolom | Deskripsi |
|---|---|
| `review_id` | ID review. |
| `employee_id` | Karyawan. |
| `property_id` | **Di-join dari `employees`**. |
| `review_period` | `YYYY-S1`/`YYYY-S2`. |
| `score`, `notes` | Skor 1.00–5.00 dan catatan kualitatif. |"""
    ),
    # --- financial (11) ---
    "v_financial_departmental_margin": (
        """*Sumber: `fact_financial_business_line_monthly` + `dim_property` + `dim_business_line` — grain: properti × lini bisnis × bulan.*
**Fungsi**: margin per lini bisnis (Room/F&B/Spa&Event) — perbandingan profitabilitas antar departemen.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `business_line_name` | `Room`, `F&B`, atau `Spa&Event` — **`Overall` dan `Corporate Overhead` sengaja dikecualikan** (lihat Catatan). |
| `period_date` | Bulan. |
| `revenue`, `expense`, `profit` | Pendapatan, biaya langsung, dan laba lini bisnis ini. |
| `margin_pct` | `profit ÷ revenue`. |

> **Catatan**: `WHERE line_name NOT IN ('Overall', 'Corporate Overhead')` **ditanam permanen** di definisi view ini, tidak bisa dilewati oleh pemanggil. Ini melindungi dari double counting — `Overall` adalah baris ringkasan properti, bukan lini bisnis tambahan; menjumlahkannya bersama `Room`/`F&B`/`Spa&Event` akan menghitung dua kali."""
    ),
    "v_financial_gop_overhead": (
        """*Sumber: `fact_financial_overall_monthly` + `dim_property` — grain: properti × bulan.*
**Fungsi**: **GOP (Gross Operating Profit)** dan overhead 1 properti — metrik ringkasan level properti, bukan per departemen.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Bulan. |
| `gop` | Gross Operating Profit properti bulan itu. |
| `gop_margin_pct` | Margin GOP. |
| `mom_gop_growth` / `yoy_gop_growth` | Pertumbuhan GOP MoM/YoY. |
| `undistributed_expense_total` | Total biaya overhead bersama (tidak dialokasikan ke 1 departemen tertentu). |
| `overhead_ratio` | Rasio overhead terhadap revenue/GOP. |"""
    ),
    "v_financial_revenue_runrate_daily": (
        """*Sumber: `fact_financial_revenue_runrate_daily` + `dim_property` — grain: properti × tanggal.*
**Fungsi**: proyeksi revenue run-rate harian 1 properti.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Tanggal. |
| `revenue_runrate` | Proyeksi revenue berjalan. |"""
    ),
    "v_payroll_department_monthly": (
        """*Sumber: `fact_payroll_department_monthly` + `dim_property` + `dim_department` — grain: properti × departemen × bulan.*
**Fungsi**: total komponen payroll per departemen — untuk analisis biaya tenaga kerja per departemen.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `department_name` | Departemen. |
| `period_date` | Bulan. |
| `base_salary_total` | Total gaji pokok. |
| `service_charge_total` | Total bagi hasil service charge — **bisa melebihi gaji pokok** di hotel ramai (berkorelasi kuat dengan okupansi). |
| `overtime_pay_total` | Total upah lembur. |
| `thr_total` | Total Tunjangan Hari Raya (hanya terisi bulan Maret). |
| `deduction_total` | Total potongan (BPJS + PPh21). |
| `net_salary_total` | Total gaji bersih. |
| `mom_growth` | Pertumbuhan bulan-ke-bulan. |"""
    ),
    "v_financial_service_charge_monthly": (
        """*Sumber: `fact_financial_service_charge_monthly` + `dim_property` — grain: properti × bulan.*
**Fungsi**: hubungan pool service charge dengan okupansi — take-home pay karyawan turun signifikan saat low season.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Bulan. |
| `service_charge_pool` | Total pool service charge properti (= `revenue × 10% × 85%`). |
| `occupancy_rate` | Okupansi bulan itu (korelasi r=0.83–0.95 dengan service charge). |"""
    ),
    "v_financial_labor_cost_monthly": (
        """*Sumber: `fact_financial_labor_cost_monthly` + `dim_property` — grain: properti × bulan.*
**Fungsi**: biaya tenaga kerja sebagai persentase revenue — indikator efisiensi operasional.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Bulan. |
| `labor_cost_pct_revenue` | Biaya tenaga kerja ÷ revenue. |"""
    ),
    "v_payroll_access_level_monthly": (
        """*Sumber: `fact_payroll_access_level_monthly` + `dim_property` + `dim_access_level` — grain: properti × level akses × bulan.*
**Fungsi**: perbandingan komponen gaji antar level jabatan (staff/manager/corporate).

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `access_level_name` | `staff` (poin service charge 1.0), `manager` (poin 2.2), `corporate` (poin 0 — bukan staf properti, tidak dapat service charge). |
| `period_date` | Bulan. |
| `service_charge_total`, `base_salary_total` | Total service charge dan gaji pokok level ini. |
| `service_charge_to_base_ratio` | Rasio service charge terhadap gaji pokok. |"""
    ),
    "v_financial_business_line_group_monthly": (
        """*Sumber: `fact_financial_business_line_group_monthly` + `dim_business_line` — grain: lini bisnis × bulan. **Tanpa `property_id`** — level grup, lintas 5 properti sekaligus.*
**Fungsi**: kontribusi tiap lini bisnis (Room/F&B/Spa&Event) terhadap revenue grup secara keseluruhan.

| Kolom | Deskripsi |
|---|---|
| `business_line_name` | Lini bisnis. |
| `period_date` | Bulan. |
| `group_revenue` | Total revenue lini bisnis ini lintas seluruh grup. |
| `revenue_share_pct` | Kontribusi terhadap total revenue grup. |

> **Catatan**: karena tidak ada `property_id`, view ini hanya cocok untuk konteks `all_properties` (level corporate/CEO) — bukan untuk role `own_property`."""
    ),
    "v_financial_property_benchmark_monthly": (
        """*Sumber: `fact_financial_property_benchmark_monthly` + `dim_property` — grain: properti × bulan.*
**Fungsi**: ranking margin GOP 1 properti dibanding 4 properti lain.

| Kolom | Deskripsi |
|---|---|
| `property_id`, `property_name` | Identitas properti. |
| `period_date` | Bulan. |
| `gop_margin_rank` | Ranking margin GOP properti ini dibanding properti lain bulan itu. |"""
    ),
    "v_lookup_financial_summary": (
        """*Sumber: `mart_cleaned.financial_summary` (tanpa join) — grain: properti × bulan × departemen.*
**Fungsi**: laporan keuangan bulanan standar USALI, per departemen atau baris ringkasan properti.

| Kolom | Deskripsi |
|---|---|
| `property_id` | Properti. |
| `period` | Format `YYYY-MM`. |
| `department` | `Room`, `F&B`, `Spa&Event` (departemen), `Overall` (**baris ringkasan properti** — bukan departemen tambahan), `Corporate Overhead` (kantor pusat, hanya biaya). |
| `departmental_revenue` / `departmental_expense` / `departmental_profit` | Pendapatan/biaya/laba departemen (atau properti untuk baris `Overall`). |
| `undistributed_expense` | **Hanya terisi di baris `Overall`** — biaya overhead bersama. |
| `gop` | **Hanya terisi di baris `Overall`** — Gross Operating Profit. |

> **Catatan penting — beda dari `v_financial_departmental_margin`**: view ini **tidak** punya filter `Overall`/`Corporate Overhead` bawaan. Pemanggil **wajib memfilter sendiri** sesuai kebutuhan: `department IN ('Room','F&B','Spa&Event')` untuk margin per departemen (hindari double counting), atau `department = 'Overall'` khusus untuk mengambil `gop`/`undistributed_expense`."""
    ),
    "v_lookup_payroll": (
        """*Sumber: `mart_cleaned.payroll` LEFT JOIN `employees` — grain: 1 baris = 1 karyawan × 1 bulan.*
**Fungsi**: komponen payroll individual 1 karyawan — kebutuhan Finance Manager.

| Kolom | Deskripsi |
|---|---|
| `payroll_id` | ID payroll. |
| `employee_id` | Karyawan. |
| `period` | Format `YYYY-MM`. |
| `base_salary` | Gaji pokok (naik 6,5%/tahun mengikuti UMK). |
| `service_charge` | Bagi hasil service charge — lihat `v_financial_service_charge_monthly` untuk mekanismenya. |
| `overtime_pay` | Upah lembur = `(base_salary ÷ 173) × jam lembur`. |
| `thr` | Tunjangan Hari Raya — hanya terisi 1x/tahun (Maret). |
| `deduction` | Potongan: BPJS Kesehatan 1% + BPJS Ketenagakerjaan 3% + PPh21 ~5%. |
| `net_salary` | `base + service_charge + overtime + thr − deduction`. |
| `property_id` | **Di-join dari `employees`** — `payroll` sendiri tidak punya kolom ini native. |"""
    ),
    # --- properties_ref (1) ---
    "v_properties_ref": (
        """*Sumber: `mart_aggregated.dim_property` (tanpa join) — grain: 1 baris = 1 properti (6 baris: P01–P06).*
**Fungsi**: resolusi nama properti dari kode, atau daftar semua properti grup — "properti apa saja yang dimiliki Nirwana", "P04 itu nama hotelnya apa".

| Kolom | Deskripsi |
|---|---|
| `property_id` | Kode properti (P01–P06). |
| `property_name` | Nama hotel. P06 = Kantor Pusat (bukan hotel — tidak punya kamar). |
| `region` | Wilayah. |
| `opening_date` | Tanggal properti mulai beroperasi (dipakai untuk menghitung usia gedung, lihat `v_maintenance_property_benchmark_yearly`). |"""
    ),
    # --- employees_directory (1) ---
    "v_employees_directory": (
        """*Sumber: `mart_aggregated.dim_employee` + `dim_property` + `dim_department` + `dim_access_level` — grain: 1 baris = 1 karyawan.*
**Fungsi**: cari nama karyawan dari ID (atau sebaliknya), lihat departemen/level akses/properti seorang karyawan — dipakai berbagai domain lain untuk resolusi nama (`staff_id`, `assigned_staff_id`, dsb yang diteruskan mentah di view lookup domain lain).

| Kolom | Deskripsi |
|---|---|
| `employee_id` | ID karyawan. |
| `full_name` | Nama karyawan. |
| `property_id`, `property_name` | Properti tempat bertugas (P06 = kantor pusat). |
| `department_name` | Salah satu dari 8 departemen (`Housekeeping`, `F&B`, `Revenue`, `Spa&Event`, `Facility`, `HR`, `Finance`, `Corporate`). |
| `access_level_name` | `staff`, `manager`, atau `corporate`. |

> **Catatan**: view ini **tidak** menyertakan `role_title` atau `status` (aktif/resigned/terminated) — untuk kebutuhan itu, lihat `mart_cleaned.employees` lewat domain lain yang relevan (mis. `v_lookup_staff_shifts` di domain `hr` untuk status kehadiran)."""
    ),
    # --- guests_pii (1) ---
    "guests_contact_view": (
        """*Sumber: `mart_cleaned.guests` + turunan `last_active_property_id` — grain: 1 baris = 1 pelanggan.*
**Fungsi**: data kontak untuk menghubungi 1 tamu — **tidak** ada atribut analitis (loyalitas/kebangsaan) di sini.

| Kolom | Deskripsi |
|---|---|
| `guest_id` | ID pelanggan (rentang menentukan populasi: G00001–G18000 = pernah booking kamar; G18001–G24500 = hanya F&B/spa; G24501+ = duplikat data). |
| `full_name` | Nama. ~2% mengandung typo (simulasi human input error). |
| `email` | ~4% kosong — walk-in yang tidak mengisi form lengkap, bukan data hilang. |
| `phone` | Format tidak konsisten (4 variasi format domestik); ~3% kosong. |
| `last_active_property_id` | Properti aktivitas terakhir tamu ini (dari booking kamar/spa terbaru) — dipakai API untuk penegakan filter `own_property`. |"""
    ),
    # --- guests_profile (1) ---
    "guests_profile_view": (
        """*Sumber: `mart_cleaned.guests` + turunan `last_active_property_id` yang sama — grain: 1 baris = 1 pelanggan.*
**Fungsi**: atribut analitis 1 tamu — tier loyalitas, asal, tanggal registrasi. **Tidak** ada kolom kontak di sini.

| Kolom | Deskripsi |
|---|---|
| `guest_id` | ID pelanggan. |
| `loyalty_tier` | `none` (bukan member, 56%), `Silver` (27%), `Gold` (12%), `Platinum` (5%, paling bernilai). |
| `nationality` | Negara asal (~3% kapitalisasi tidak konsisten di sumbernya, mis. `indonesia` vs `Indonesia`). |
| `registered_date` | Tanggal pertama terdaftar. |
| `last_active_property_id` | Sama seperti di `guests_contact_view`. |"""
    ),
}

CATATAN_LINTAS_DOMAIN: str = """## Catatan Lintas-Domain

Aturan berikut berlaku di banyak view sekaligus — dibaca sekali di sini, tidak diulang per view:

1. **`property_id` selalu mentah, tidak pernah difilter di level view.** Pembatasan "hanya properti sendiri" (`access_scope = own_property`) sepenuhnya tanggung jawab API chatbot (M4.4): API memvalidasi `role_title` pemanggil terhadap `role_permissions`, lalu menyuntikkan `WHERE property_id = :user_property_id` sendiri. View yang dipanggil langsung ke database (di luar API) **akan mengembalikan data lintas 5 properti tanpa filter** — bukan bug, tapi desain yang sengaja memindahkan tanggung jawab filter ke API.
2. **Tidak ada view domain operasional (`reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`) yang join ke `guests`.** Kolom `guest_id` diteruskan sebagai FK mentah di view-view tersebut (kadang nullable untuk walk-in). Nama/kontak/atribut tamu hanya bisa didapat lewat `guests_contact_view`/`guests_profile_view` — mencegah PII bocor lewat domain lain.
3. **`financial` adalah satu-satunya domain yang menyentuh payroll.** Domain `hr` sengaja tidak punya view payroll sama sekali, baik agregat maupun row-level — segregation of duties.
4. **Pengecualian `Overall`/`Corporate Overhead`**: hanya `v_financial_departmental_margin` yang otomatis mengecualikan dua baris ini (baked-in `WHERE`). `v_lookup_financial_summary` **tidak** — pemanggil wajib filter sendiri sesuai kebutuhan (lihat catatan di view tersebut).
5. **Beberapa kolom `property_id` adalah hasil join, bukan kolom native tabel sumber** (ditandai "di-join dari..." di tiap view terkait): `v_lookup_fnb_inventory`/`v_lookup_fnb_transactions` (dari `fnb_outlets`), `v_lookup_housekeeping_log` (dari `rooms`), `v_lookup_staff_shifts`/`v_lookup_employee_performance`/`v_lookup_payroll` (dari `employees`), `v_housekeeping_staff_daily`/`v_maintenance_technician_daily` (dari `dim_employee`).
6. **Data performa individu staff** (`v_housekeeping_staff_daily`, `v_maintenance_technician_daily`, kolom `staff_id`/`assigned_staff_id` di view lookup domain `facility`) — role Staff seharusnya hanya melihat datanya sendiri; view tidak membatasi ini, ditegakkan di API.
7. **Gap yang diketahui** (dari `milestones/4.2-view-akses-granular-per-domain/report.md`): belum ada index khusus untuk `chatbot_views` — view lookup atas tabel besar (`v_lookup_fnb_transactions` di atas 901rb baris, `v_lookup_housekeeping_log` di atas 425rb baris) belum diuji di beban query API nyata."""
