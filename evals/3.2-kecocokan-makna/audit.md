# Audit — Pemeriksaan Kecocokan Makna (Milestone 3.2)

Hasil eksekusi nyata `run_eval.py` terhadap 8 skenario `rancangan.md`, panggilan OpenRouter sungguhan (Qwen3-32B Langkah 1 + DeepSeek V4 Pro `reasoning="high"` Langkah 2), dijalankan 2026-08-17. Payload lengkap: `payloads/{S01..S08}.json`.

## Ringkasan

**8/8 skenario LOLOS** — termasuk keempat skenario tanpa toleransi (S01, S02, S04, S08) dan tiga skenario dengan toleransi eksplisit (S03, S06, S07) yang semuanya lolos DI DALAM ambang toleransi (S06 bahkan melebihi ambang, lihat di bawah). Tidak ada REVIEW/fail pada percobaan pertama.

| ID | Status | Catatan |
|---|---|---|
| S01 (KK1 sumber) | LOLOS | Grain-mismatch terdeteksi tepat — `v_reservation_room_type_daily=ditemukan`, `v_reservation_property_daily=tidak_ditemukan` |
| S02 (KK2 sumber) | LOLOS | Cocok penuh, `ditemukan` tanpa ragu |
| S03 (kolom turunan) | LOLOS | `ditemukan` — kolom turunan TIDAK menyebabkan penolakan keliru |
| S04 (snapshot vs tren) | LOLOS | `tidak_ditemukan`, alasan eksplisit merujuk "data sumber tidak punya tanggal resign" (persis frasa katalog) |
| S05 (snapshot cocok, counter-case) | LOLOS | `ditemukan` untuk kebutuhan point-in-time — tidak over-triggering menolak berdasar kata "snapshot" semata |
| S06 (10 kandidat) | LOLOS, lebih baik dari toleransi | 0/9 false-positive (toleransi mengizinkan hingga 2) — lihat detail di bawah |
| S07 (kolom join, observasional) | LOLOS, temuan kualitatif | Lihat "Temuan" di bawah — bukti nyata koreksi dua arah, tapi nuansa join/nullable tidak tersebut eksplisit |
| S08 (baked-in vs manual filter) | LOLOS | Perbedaan filter bawaan dua view mirip dibedakan tepat |

## Temuan

### Temuan 1 (positif) — Koreksi dua arah terbukti nyata, bukan cuma desain teoretis

S07 adalah bukti konkret pertama mekanisme koreksi dua arah (`decisions.md` Keputusan 1) bekerja pada panggilan nyata: `alasan` final eksplisit menyatakan *"Penilaian awal terlalu ragu, koreksi ke 'ditemukan' karena semua data yang dibutuhkan tersedia"* — Langkah 1 (Qwen3-32B) sempat menilai `sebagian`, Langkah 2 (DeepSeek V4 Pro) menaikkan ke `ditemukan` dengan alasan eksplisit merujuk penilaian awal. Ini bukan anchoring/menyalin — model verifikasi benar-benar menilai ulang dan mengoreksi arah "naik" (persis pola KK2, anti-hedging), sama seperti didesain di prompt `kecocokan_makna_verifikasi.md`.

### Temuan 2 (netral, dicatat sesuai toleransi eksplisit S07) — Nuansa join/nullable tidak muncul di alasan

S07 dirancang observasional untuk mengecek apakah `alasan` menyinggung sifat `property_id` hasil join dari `dim_employee` (Catatan Lintas-Domain butir 5, "berpotensi tidak selalu terisi"). Hasil aktual: `alasan` HANYA membahas kecukupan grain/kolom (`avg_cleaning_duration_minutes`, `property_id`, `period_date`) untuk menjawab kebutuhan — tidak menyebut risiko nullability kolom join sama sekali, meski `CATATAN_LINTAS_DOMAIN` (termasuk butir 5) diinject penuh ke system prompt Langkah 1 maupun Langkah 2. Kandidat tetap `ditemukan` (tepat secara grain), jadi TIDAK mengubah hasil `match=True` sesuai kriteria S07 yang memang toleran pada dimensi ini — tapi ini sinyal bahwa prompt saat ini belum secara konsisten mendorong model mengangkat nuansa reliabilitas kolom join kalau tidak langsung relevan ke pertanyaan grain. **Tidak dianggap cukup signifikan untuk `docs/keterbatasan-diterima.md`** (baru satu titik data, dan hasil akhirnya tetap benar) — dicatat di sini sebagai observasi untuk dipantau kalau pola serupa muncul lagi di M3.3 atau produksi nyata.

### Temuan 3 (positif) — Presisi domain padat melebihi ambang toleransi

S06 (10 kandidat domain `hr` sekaligus dalam satu batch) mengizinkan toleransi hingga 2/9 kandidat non-fokus salah dilabel `ditemukan` — hasil aktual 0/9. Distribusi label: 1 `ditemukan` (tepat), 2 `sebagian` (kandidat yang genuinely berdekatan secara topik — `v_hr_employee_monthly` dan `v_lookup_staff_shifts`, keduanya py alasan spesifik kenapa tidak cukup), 7 `tidak_ditemukan`. Ini bukti kuat bahwa keputusan batching per-kebutuhan-atomik (`decisions.md` Keputusan 2) tidak mengorbankan presisi bahkan pada kepadatan kandidat maksimum yang pernah tercatat (mirror stress-test B5 M3.1).

### Temuan 4 (netral) — Kedua Kriteria Keberhasilan sumber terbukti tanpa keraguan

S01 dan S02 (KK1/KK2 sumber persis dari `rancangan-retrieval-query.md`) lolos tanpa toleransi pada percobaan pertama — tidak perlu retry atau penyesuaian skenario. `alasan` di kedua kasus merujuk fakta konkret grain/kolom (bukan pernyataan generik), sesuai instruksi prompt.

## Tidak Ada Entri Baru `docs/keterbatasan-diterima.md`

Tidak ada temuan di eval ini yang cukup signifikan/berulang untuk dicatat sebagai keterbatasan diterima formal — Temuan 2 di atas adalah observasi satu-titik-data, bukan pola gagal berulang seperti preseden M2.1 #6 (over-triggering) atau M3.1 #11 (BM25 blind spot terverifikasi lintas 5 skenario). Kalau pola serupa (nuansa reliabilitas kolom tidak terangkat di `alasan`) muncul lagi di eval milestone berikutnya atau produksi nyata, baru layak dinaikkan jadi entri formal.

## Prompt Reliability Testing (Promptfoo)

Belum dijalankan — dilakukan di Checkpoint 14 (native config sudah dibuat Checkpoint 7-8, akan diselaraskan dengan 8 skenario di atas sebelum dieksekusi).
