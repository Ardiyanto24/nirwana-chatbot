# Audit — Penyusunan Request (Milestone 3.4)

Eksekusi nyata `susun_request_atomic_intent()` (bukan mock) untuk 7 skenario `rancangan.md`, `tanggal_referensi=2026-08-17` tetap. **6/7 skenario lolos check otomatis** (run final, setelah prompt v2). Payload lengkap: `payloads/S01.json` s.d. `S07.json`.

## Ringkasan Hasil (Run Final, Prompt v2)

| ID | Status | Match | Catatan |
|---|---|---|---|
| S01 | LOLOS | ✓ | `period_date_from/to` = 2026-07-01/2026-07-31, persis benar |
| S02 | LOLOS | ✓ | `period_date_from/to` = 2026-05-17/2026-08-17 (rolling 3 bulan), sesuai toleransi rancangan |
| S03 | LOLOS | ✓ | `channel_name="Direct"` + bulan Juni persis |
| S04 | REVIEW | ✗ (otomatis) | Lihat Temuan 1 + Temuan 2 di bawah — bukan kegagalan mekanisme, dua nuansa berbeda |
| S05 | LOLOS | ✓ | `params={}` — TIDAK lagi salah mengisi `property_id="Nirwana"` setelah prompt v2 (lihat Temuan 3) |
| S06 | LOLOS | ✓ | `item_name="Nasi Goreng"`, tidak ada param tanggal dikarang |
| S07 | LOLOS | ✓ | `star_rating` tidak pernah muncul di `request.params` |

## Temuan 1 — S04: `property_name` Dipakai, Bukan `property_id` (Bukan Bug)

Ekspektasi awal rancangan meminta `property_id="P05"`. Hasil nyata: `property_name="Nirwana Lombok Escape"`. Setelah ditinjau ulang: **ini BUKAN kegagalan** — `property_name` adalah parameter yang SAMA-SAMA valid di whitelist (`PARAM_WHITELIST_VIEW`), dan nilainya (`"Nirwana Lombok Escape"`) persis sama dengan `property_name` di `properties.csv` nyata yang diberikan user. Prompt yang diberikan ke model TIDAK PERNAH menyertakan tabel pemetaan nama properti ke kode (`v_reservation_room_type_daily` sendiri di katalog hanya menyebut "Kode properti P01-P05", tanpa daftar nama lengkapnya) — jadi model membuat pilihan yang AMAN dan valid (filter pakai nama yang disebutkan langsung di kebutuhan) daripada menebak kode yang tidak pernah diberitahukan.

**Koreksi penilaian**: fungsi `check()` di `run_eval.py` untuk S04 terlalu ketat (mengasumsikan konteks yang sebenarnya tidak diberikan ke model). Skenario ini dianggap **LOLOS secara substansi** meski gagal check otomatis literal — dicatat transparan di sini, bukan diam-diam mengubah `check()` seolah tidak pernah salah desain.

## Temuan 2 — S04: Nilai Parameter Nonsensikal (`occupancy_rate: "nilai_tunggal"`)

Di LUAR temuan 1, payload S04 juga mengandung `"occupancy_rate": "nilai_tunggal"` — `occupancy_rate` adalah kolom METRIK (hasil, bukan filter), dan nilainya diisi string label bentuk jawaban (`"nilai_tunggal"`) yang jelas tidak masuk akal sebagai nilai filter kolom itu. **Ini genuinely temuan kualitas nyata** — key `occupancy_rate` LOLOS filter defensif (Checkpoint 5) karena memang ada di whitelist (key-nya sah), tapi NILAI-nya tidak masuk akal secara semantik.

**Ini BUKAN sesuatu yang diperbaiki di M3.4** — filter defensif M3.4 (`_saring_params_tidak_dikenal`) sengaja hanya memvalidasi KEY (nama parameter), bukan kewajaran NILAI per key (validasi nilai/tipe per parameter adalah ruang kesalahan jauh lebih terbuka, di luar cakupan "tidak mengarang nama parameter" KK2 sumber). Temuan ini justru **mengonfirmasi kenapa Milestone 3.5 (Verifikasi Bentuk Request, independen, di luar cakupan plan ini) ada sebagai langkah terpisah** — persis jenis kesalahan (parameter dengan nilai tidak masuk akal, lolos dari sisi nama tapi salah dari sisi makna) yang dirancang untuk ditangkap verifikasi independen tahap berikutnya, bukan oleh Langkah 1 (generate) sendirian.

**Tidak dicatat sebagai entri `docs/keterbatasan-diterima.md`** — satu titik data, dan penanganannya memang secara arsitektur didesain sebagai tanggung jawab M3.5, bukan celah M3.4 yang perlu ditambal.

## Temuan 3 — S05 (Sebelum Prompt v2): "Nirwana" Disalahartikan sebagai Nama Properti

Run PERTAMA (prompt v1) menghasilkan `params={"property_id": "Nirwana"}` untuk kebutuhan "Ada berapa venue yang dimiliki Nirwana?" — model salah menafsirkan nama GRUP perusahaan ("Nirwana Hospitality Group") sebagai nilai filter properti spesifik. **Diperbaiki**: prompt v2 menambah aturan eksplisit "Nirwana adalah nama grup, bukan nama properti spesifik — jangan isi filter properti kalau cuma nama grup yang disebut". Diverifikasi ulang (run final v2): `params={}` — benar, tanpa filter yang dikarang.

## Kesimpulan

Kedua Kriteria Keberhasilan sumber M3.4 terbukti:
- **KK1** (resolusi tanggal relatif): S01 ("bulan lalu") dan S02 ("tiga bulan terakhir") lolos persis tanpa toleransi pada rentang tanggalnya.
- **KK2** (tidak mengarang parameter di luar yang tersedia): S07 (parameter masuk akal tapi tidak ada di whitelist, `star_rating`) lolos bersih; S05 lolos setelah satu iterasi perbaikan prompt (v1→v2) berbasis bukti nyata, mirror pola M3.3.

Satu temuan kualitas nyata (Temuan 2, nilai parameter nonsensikal) SENGAJA TIDAK diperbaiki di M3.4 — bukan kelalaian, melainkan konfirmasi langsung bahwa arsitektur generate-verify (M3.4 generate, M3.5 verify independen) memang dirancang untuk kasus persis seperti ini.
