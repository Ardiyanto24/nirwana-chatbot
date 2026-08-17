# Rancangan Pengujian — Pemeriksaan Kecocokan Makna (Milestone 3.2)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/2.3-deteksi-cakupan-individu/rancangan.md`. **Jumlah skenario TIDAK dipatok** — 8 skenario di sini disesuaikan cakupan ruang kegagalan mekanisme (dua arah kesalahan: grain-mismatch dilonggarkan/false-positive, dan cocok-penuh-diragukan/false-negative), bukan konvensi wajib.

## Yang Diuji

`nilai_kecocokan_makna_atomic_intent()` (`src/layers/retriever/kecocokan_makna.py`) — Milestone 3.2 sudah lolos 73 unit test (mocked LLM, `_parse_generate`/`_parse_verifikasi`/orkestrator) di `tests/layers/retriever/test_kecocokan_makna.py`, membuktikan MEKANISME (jaminan struktural, fallback gagal-teknis, koreksi dua arah) bekerja benar terhadap respons LLM yang disimulasikan. Eval ini menguji sisi yang TIDAK bisa dibuktikan unit test: apakah model NYATA (Qwen3-32B Langkah 1 + DeepSeek V4 Pro Langkah 2) benar-benar menilai *makna* dengan tepat terhadap definisi katalog sungguhan — kedua Kriteria Keberhasilan sumber persis, plus jenis jebakan spesifik yang disebut dokumen sumber (kolom turunan/hasil join, `berpotensi tidak selalu terisi`) dan skala kandidat padat (preseden stress-test `evals/3.1-.../rancangan.md` Bagian B).

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Parsing/fallback/jaminan struktural (LLM disimulasikan) | Ya | — |
| KK1 sumber persis (grain-mismatch, breakdown per tipe kamar vs ringkasan per properti) | Tidak (LLM nyata) | S01 |
| KK2 sumber persis (cocok penuh, nama+grain+sumber semua sesuai) | Tidak (LLM nyata) | S02 |
| Kolom turunan (hasil hitung, BUKAN otomatis ditolak kalau nilainya tetap benar) | Tidak | S03 |
| Snapshot vs kebutuhan tren historis (jebakan folded ke Fungsi, bukan section Catatan terpisah) | Tidak | S04 |
| Snapshot cocok untuk kebutuhan point-in-time (counter-case, anti over-triggering S04) | Tidak | S05 |
| Domain padat kandidat (10 kandidat sekaligus dalam satu batch) | Tidak | S06 |
| Kolom hasil join lintas-tabel, berpotensi nullable (Catatan Lintas-Domain butir 5) | Tidak | S07 |
| Dua view mirip tapi beda filter bawaan (`v_financial_departmental_margin` vs `v_lookup_financial_summary`) | Tidak | S08 |

## Cara Baca Skenario

Tiap skenario: teks kebutuhan (atomic intent tunggal) + label bentuk jawaban, daftar kandidat `view_name` (disimulasikan sebagai hasil M3.1 — domain semuanya diizinkan), ekspektasi label per kandidat yang relevan, status toleransi. Dijalankan lewat `nilai_kecocokan_makna_atomic_intent()` end-to-end (Langkah 1 + Langkah 2 nyata), bukan fungsi internal — mencerminkan hasil FINAL (pasca-koreksi), sesuai kontrak keluaran mekanisme.

---

### S01 — KK1 Sumber Persis: Grain-Mismatch Ringkasan Properti vs Per Tipe Kamar

**Kebutuhan:** "Tampilkan breakdown okupansi per tipe kamar untuk properti Bali bulan ini" (bentuk jawaban: `komposisi`)
**Kandidat:** `v_reservation_room_type_daily` (grain benar: properti × tipe kamar × tanggal), `v_reservation_property_daily` (grain salah: properti × tanggal saja, TIDAK ada breakdown tipe kamar)

**Ekspektasi:** `v_reservation_room_type_daily` = `ditemukan`; `v_reservation_property_daily` = `sebagian` ATAU `tidak_ditemukan` (BUKAN `ditemukan`).

**Toleransi:** Tidak ada — ini KK1 sumber persis (`rancangan-retrieval-query.md`), skenario contoh yang eksplisit disebut dokumen milestone.

---

### S02 — KK2 Sumber Persis: Cocok Penuh Tanpa Ragu

**Kebutuhan:** "Berapa okupansi Suite di Bali bulan ini?" (bentuk jawaban: `nilai_tunggal`)
**Kandidat:** `v_reservation_room_type_daily` (nama, grain, dan sumber data semuanya sesuai — kolom `room_type_name` filter `Suite`, `property_id` filter Bali, `occupancy_rate` langsung tersedia)

**Ekspektasi:** `ditemukan`.

**Toleransi:** Tidak ada — KK2 sumber persis.

---

### S03 — Kolom Turunan Tetap Valid (Anti False-Negative)

**Kebutuhan:** "Berapa batas SLA (dalam jam) untuk tiket prioritas critical?" (bentuk jawaban: `nilai_tunggal`)
**Kandidat:** `v_maintenance_ticket_daily` (`sla_threshold_hours` ditandai **Kolom turunan** — hasil hitung dari `priority_name`, bukan kolom mentah tersimpan langsung, tapi NILAINYA tetap akurat menjawab kebutuhan)

**Ekspektasi:** `ditemukan` — kolom turunan bukan cacat kalau nilainya tetap benar; ini uji BAHWA model tidak menolak kandidat hanya karena marker "Kolom turunan" tanpa alasan substantif.

**Toleransi:** Ya, terbatas — kalau hasil `sebagian` dengan alasan eksplisit merujuk sifat "turunan"-nya (bukan isu grain/sumber lain), dicatat sebagai temuan nyata (bukan fail keras otomatis) karena ini nuansa interpretasi yang genuinely bisa diperdebatkan — beda dari S01/S02 yang persis dari dokumen sumber.

---

### S04 — Snapshot vs Kebutuhan Tren Historis

**Kebutuhan:** "Bagaimana TREN turnover karyawan departemen HR selama setahun terakhir?" (bentuk jawaban: `tren`)
**Kandidat:** `v_hr_turnover_snapshot` (Fungsi eksplisit: "snapshot, TIDAK ADA tren historis, data sumber tidak punya tanggal resign")

**Ekspektasi:** `sebagian` ATAU `tidak_ditemukan` — jebakan folded ke teks Fungsi, bukan section Catatan terpisah, menguji apakah model membaca definisi utuh (bukan cuma nama view yang terdengar relevan untuk "turnover").

**Toleransi:** Tidak ada — grain snapshot vs kebutuhan tren adalah bentuk lain dari jebakan KK1 (grain/cakupan tidak memenuhi bentuk jawaban yang diminta), sama prinsipnya dengan S01.

---

### S05 — Snapshot Cocok untuk Kebutuhan Point-in-Time (Counter-Case S04)

**Kebutuhan:** "Berapa tingkat turnover departemen HR bulan ini?" (bentuk jawaban: `nilai_tunggal`)
**Kandidat:** `v_hr_turnover_snapshot`

**Ekspektasi:** `ditemukan` — kebutuhan HANYA minta snapshot titik waktu (bukan tren), jadi keterbatasan "tidak ada tren historis" TIDAK relevan di sini; menguji anti over-triggering (jangan menolak view yang genuinely cocok hanya karena melihat kata "snapshot"/keterbatasan yang disebutkan di definisinya, padahal keterbatasan itu tidak relevan untuk kebutuhan spesifik ini).

**Toleransi:** Tidak ada — pasangan langsung S04, membuktikan model membedakan konteks, bukan pattern-matching kata "snapshot" secara membabi buta.

---

### S06 — Domain Padat Kandidat (10 Kandidat Sekaligus)

**Kebutuhan:** "Karyawan mana saja yang pola absensinya menyimpang jauh dari kebiasaan pribadinya bulan ini?" (bentuk jawaban: `peringkat`)
**Kandidat:** SELURUH 10 view domain `hr` — `v_hr_attendance_daily`, `v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_headcount_status_daily`, `v_hr_performance_by_status_semester`, `v_hr_performance_department_semester`, `v_hr_turnover_snapshot`, `v_hr_watchlist_monthly`, `v_lookup_employee_performance`, `v_lookup_staff_shifts` (mirror skenario stress-test B5 `evals/3.1-.../rancangan.md`, domain `hr` pernah mengembalikan seluruh 10 view sebagai kandidat BM25 di eval M3.1)

**Ekspektasi:** `v_hr_watchlist_monthly` = `ditemukan` (definisi eksplisit: deviasi dari baseline pribadi masing-masing karyawan); minimal 7 dari 9 kandidat lain = `sebagian` ATAU `tidak_ditemukan` (bukan `ditemukan` — mayoritas kandidat lain genuinely tidak menjawab kebutuhan spesifik ini).

**Toleransi:** Ya, sebagian — `v_hr_watchlist_monthly=ditemukan` WAJIB tanpa toleransi (kandidat paling tepat, kalau gagal ini temuan nyata). Untuk kandidat lain, toleransi hingga 2 dari 9 boleh mendapat `ditemukan` keliru (borderline case seperti `v_lookup_staff_shifts` yang menyentuh kehadiran individu tapi bukan soal deviasi-dari-baseline) — dicatat sebagai temuan bukan fail keras, karena tujuan utama S06 adalah membuktikan skala 10 kandidat tidak membuat model kehilangan kandidat yang JELAS benar, bukan presisi sempurna di seluruh 10.

---

### S07 — Kolom Hasil Join Lintas-Tabel (Berpotensi Nullable)

**Kebutuhan:** "Bandingkan durasi pembersihan tiap staf housekeeping per properti bulan ini" (bentuk jawaban: `perbandingan`)
**Kandidat:** `v_housekeeping_staff_daily` (`property_id` ditandai "di-join dari `dim_employee`" di Catatan Lintas-Domain butir 5 — berpotensi tidak selalu terisi kalau data karyawan tidak lengkap)

**Ekspektasi:** `ditemukan` ATAU `sebagian` dengan alasan eksplisit menyebut sifat join/nullable `property_id` (BUKAN alasan lain yang tidak relevan) — kandidat ini genuinely tepat secara grain (per staf per properti), jebakan di sini murni soal keandalan `property_id`, bukan soal apakah view-nya benar.

**Toleransi:** Ya, penuh — S07 murni observasional (apakah model MENYADARI nuansa join-derived saat relevan), bukan uji pass/fail biner. Dicatat di `audit.md` sebagai temuan kualitatif: apakah `alasan` yang dihasilkan menyinggung nuansa ini atau tidak sama sekali.

---

### S08 — Dua View Mirip, Beda Filter Bawaan (Baked-in vs Manual)

**Kebutuhan:** "Berapa margin per departemen (Room, F&B, Spa&Event) bulan ini, tanpa data ringkasan level properti?" (bentuk jawaban: `perbandingan`)
**Kandidat:** `v_financial_departmental_margin` (filter `Overall`/`Corporate Overhead` **ditanam permanen** di definisi view, otomatis sesuai kebutuhan), `v_lookup_financial_summary` (TIDAK ada filter bawaan — pemanggil wajib filter sendiri `department IN ('Room','F&B','Spa&Event')`)

**Ekspektasi:** `v_financial_departmental_margin` = `ditemukan` (langsung sesuai tanpa filter tambahan); `v_lookup_financial_summary` = `sebagian` (kandidat relevan tapi TIDAK secara otomatis mengecualikan `Overall`/`Corporate Overhead` seperti diminta kebutuhan — perlu langkah filter tambahan di luar kemampuan view itu sendiri).

**Toleransi:** Tidak ada — menguji pembacaan detail Catatan dua view yang topiknya sangat mirip (margin per departemen), perbedaannya HANYA pada baked-in filter vs tidak; kalau model tidak membedakan keduanya, ini temuan nyata soal kedalaman pembacaan definisi.

---

## Ringkasan Ekspektasi

| ID | Kandidat Fokus | Ekspektasi | Toleransi |
|---|---|---|---|
| S01 | `v_reservation_room_type_daily` / `v_reservation_property_daily` | `ditemukan` / bukan `ditemukan` | Tidak — KK1 sumber |
| S02 | `v_reservation_room_type_daily` | `ditemukan` | Tidak — KK2 sumber |
| S03 | `v_maintenance_ticket_daily` | `ditemukan` | Ya — nuansa interpretatif |
| S04 | `v_hr_turnover_snapshot` | bukan `ditemukan` | Tidak |
| S05 | `v_hr_turnover_snapshot` | `ditemukan` | Tidak |
| S06 | `v_hr_watchlist_monthly` (+9 lain) | `ditemukan` (fokus); campuran (lain) | Sebagian — hanya kandidat fokus wajib |
| S07 | `v_housekeeping_staff_daily` | `ditemukan`/`sebagian` + alasan relevan | Ya — observasional |
| S08 | `v_financial_departmental_margin` / `v_lookup_financial_summary` | `ditemukan` / `sebagian` | Tidak |
