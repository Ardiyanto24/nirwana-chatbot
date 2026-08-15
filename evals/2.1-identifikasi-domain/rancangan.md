# Rancangan Pengujian — Identifikasi Domain dan Verifikasi Titik Buta (Milestone 2.1)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/1.6-.../1.7-.../rancangan.md`. **Jumlah skenario TIDAK dipatok** — 10 skenario di sini murni hasil analisis dimensi yang belum tercakup `tests/`, bukan konvensi wajib (lihat `decisions.md` M1.6 Keputusan 13, dipakai ulang di sini).

## Yang Diuji

`identifikasi_domain_atomic_intent()` (`src/layers/domain_gate/domain_gate.py`) — Milestone 2.1 sudah lolos ketiga Kriteria Keberhasilan sumber lewat panggilan LLM nyata di `tests/layers/domain_gate/` (Checkpoint 5-7) dan span nyata di Jaeger (Checkpoint 8): skenario `gop_margin` (KK1), verifikasi titik buta terisolasi dengan `domain_awal` sengaja tidak lengkap (KK2), dan `guests_pii`/`guests_profile` (KK3). Pengujian ini fokus pada dimensi yang **belum** tercakup: generalisasi pola cross-domain di luar satu contoh terdokumentasi, guard anti-false-positive di domain lain, cakupan domain minor yang belum pernah disentuh test, dan retest satu temuan Checkpoint 8 (potensi over-triggering verifikasi titik buta).

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Leakage `gop_margin` persis (KK1) | Ya | — |
| Blind-spot terisolasi dengan `domain_awal` sengaja tidak lengkap (KK2) | Ya | — |
| `guests_pii`/`guests_profile` murni (KK3) | Ya | — |
| Generalisasi pola cross-domain ke kasus BARU (bukan `gop_margin`) | Tidak | S01 |
| Fokus terlalu sempit, pola umum berbeda dari `gop_margin` | Tidak | S02 |
| `guests_pii` DAN `guests_profile` genuinely dibutuhkan sekaligus | Tidak | S03 |
| Retest temuan Checkpoint 8 (over-triggering `reservation` di skenario `nationality mix`) | Sebagian (1 run, belum retest) | S04 |
| Baseline domain tunggal `financial` murni | Tidak (baseline yang teruji `tests/` cuma `reservation`) | S05 |
| Guard anti-false-positive domain `hr` murni | Tidak | S06 |
| Domain minor `properties_ref` (belum pernah disentuh) | Tidak | S07 |
| Multi-domain EKSPLISIT (bukan leakage — keduanya disebut jelas) | Tidak | S08 |
| `employees_directory` + `hr` gabungan (resolusi nama karyawan) | Tidak | S09 |
| Jebakan payroll: `financial` MURNI, bukan `hr` | Tidak | S10 |

## Cara Baca Skenario

Tiap skenario: teks kebutuhan (atomic intent tunggal), ekspektasi domain (daftar `Domain` yang WAJIB ada, dan daftar yang WAJIB TIDAK ada kalau relevan), status toleransi.

---

### S01 — Generalisasi Pola Cross-Domain (Kasus Baru, Bukan `gop_margin`)

**Kebutuhan:** "Bagaimana margin keuntungan F&B dibandingkan dengan revenue F&B bulan ini?"

**Ekspektasi:** WAJIB ada `fnb` DAN `financial` (metrik "margin keuntungan" adalah metrik profitabilitas — domain `financial` — meski konteksnya F&B).

**Toleransi:** Tidak ada — ini pengujian INTI apakah prompt (`CATATAN_POLA_JEBAKAN`, sengaja ditulis sebagai prinsip umum + satu ilustrasi, lihat `decisions.md` Keputusan 11) benar-benar mengajarkan generalisasi, bukan cuma menghapal contoh `gop_margin`/`v_reservation_gop_impact_monthly` secara harfiah. Kalau gagal di sini, itu temuan signifikan terhadap desain grounding context.

---

### S02 — Fokus Terlalu Sempit (Pola Umum, Bukan Leakage Kolom)

**Kebutuhan:** "Siapa staff yang menangani housekeeping hari ini, dan berapa okupansi hotel saat itu?"

**Ekspektasi:** WAJIB ada `facility` (housekeeping) DAN `reservation` (okupansi) — dua domain eksplisit disebut tapi lewat kalimat majemuk yang mudah dibaca sekilas sebagai satu domain saja.

**Toleransi:** Tidak ada — pola jebakan kedua dari Lingkup sumber (fokus terlalu sempit pada kata eksplisit), beda dari leakage kolom turunan (S01).

---

### S03 — `guests_pii` DAN `guests_profile` Genuinely Dibutuhkan Sekaligus

**Kebutuhan:** "Siapkan laporan tamu VIP: nama, email, dan tingkat loyalitas mereka."

**Ekspektasi:** WAJIB ada `guests_pii` (nama, email — kontak) DAN `guests_profile` (tingkat loyalitas — atribut analitis).

**Toleransi:** Tidak ada — KK3 sumber eksplisit menyebut kemungkinan kebutuhan menyentuh keduanya sekaligus, belum ada skenario `tests/` yang menguji kasus gabungan ini (hanya kasus salah-satu-saja).

---

### S04 — Retest Temuan Checkpoint 8 (Potensi Over-Triggering)

**Kebutuhan:** "Berapa nationality mix tamu bulan ini?" (IDENTIK dengan skenario span nyata Checkpoint 8)

**Ekspektasi:** WAJIB ada `guests_profile`. `reservation` TIDAK diharapkan (pertanyaan murni demografis tamu, tidak menyebut booking/reservasi).

**Toleransi eksplisit:** Kalau `reservation` tetap muncul (mereplikasi temuan Checkpoint 8), INI BUKAN otomatis dianggap fail keras — dicatat sebagai temuan pola over-triggering verifikasi titik buta di `audit.md`, kandidat entri baru `docs/keterbatasan-diterima.md` kalau konsisten (mirror pola toleransi S09 `evals/1.7-.../rancangan.md` untuk recency bias).

---

### S05 — Baseline Domain Tunggal: `financial` Murni

**Kebutuhan:** "Berapa total revenue seluruh properti bulan ini?"

**Ekspektasi:** WAJIB ada `financial`. Domain lain (`reservation`, `fnb`, dst.) TIDAK diharapkan — pertanyaan generik "total revenue" tanpa spesifikasi sumber revenue tertentu.

**Toleransi:** Tidak ada.

---

### S06 — Guard Anti-False-Positive: `hr` Murni

**Kebutuhan:** "Berapa tingkat turnover karyawan bulan ini?"

**Ekspektasi:** WAJIB ada `hr`. `employees_directory`/`financial` (payroll) TIDAK diharapkan — turnover rate adalah metrik `hr` murni, tidak butuh resolusi nama karyawan maupun data payroll.

**Toleransi:** Tidak ada — guard anti-false-positive verifikasi titik buta, domain berbeda dari S04.

---

### S07 — Domain Minor: `properties_ref`

**Kebutuhan:** "Sebutkan nama-nama hotel yang sudah beroperasi lebih dari 5 tahun."

**Ekspektasi:** WAJIB ada `properties_ref` (master data properti — nama, tanggal buka).

**Toleransi:** Tidak ada — domain 1-view yang belum pernah disentuh satu pun test sebelumnya (`tests/`, Checkpoint 8), perlu dibuktikan minimal sekali.

---

### S08 — Multi-Domain Eksplisit (Bukan Leakage — Keduanya Disebut Jelas)

**Kebutuhan:** "Bandingkan revenue F&B dengan tingkat okupansi kamar bulan ini."

**Ekspektasi:** WAJIB ada `fnb` DAN `reservation` — kasus KONTROL: dua domain yang sama-sama eksplisit disebutkan, seharusnya sudah tertangkap Langkah 1 (identifikasi awal) tanpa perlu bantuan Langkah 2 (verifikasi titik buta) sama sekali.

**Toleransi:** Tidak ada pada domain akhir. (Analisis tambahan non-fail: dicatat di `audit.md` apakah Langkah 1 sendirian sudah menangkap keduanya, atau perlu Langkah 2 — untuk mengecek Langkah 1 tidak under-perform pada kasus yang seharusnya mudah.)

---

### S09 — `employees_directory` + `hr` Gabungan

**Kebutuhan:** "Siapa saja karyawan departemen HR yang performanya menurun bulan ini?"

**Ekspektasi:** WAJIB ada `hr` (data performa). `employees_directory` DIHARAPKAN (resolusi nama karyawan dari ID) tapi TIDAK wajib keras — dicatat sebagai analisis, bukan fail otomatis kalau tidak muncul (lihat Toleransi).

**Toleransi eksplisit:** `hr` wajib. `employees_directory` opsional-diharapkan — kalau tidak muncul, dicatat sebagai observasi (apakah sistem konsisten menganggap resolusi nama sebagai bagian dari domain sumber, bukan domain terpisah), bukan dianggap gagal keras karena dokumen sumber tidak eksplisit mewajibkan `employees_directory` muncul di setiap pertanyaan yang menyebut nama karyawan.

---

### S10 — Jebakan Payroll: `financial` MURNI, Bukan `hr`

**Kebutuhan:** "Berapa total payroll yang dibayarkan bulan ini?"

**Ekspektasi:** WAJIB ada `financial`. `hr` TIDAK diharapkan — payroll eksklusif domain `financial` (`katalog-data-chatbot.md` baris 50: "hr... tanpa payroll"; `financial` baris eksplisit "payroll - eksklusif domain ini"), meski kata "payroll" sering diasosiasikan keliru dengan HR secara umum.

**Toleransi:** Tidak ada — ini pengujian LANGSUNG terhadap catatan eksplisit di `DESKRIPSI_DOMAIN` (Checkpoint 4) yang menegaskan pengecualian ini.

---

## Ringkasan Ekspektasi

| ID | Domain wajib ADA | Domain wajib TIDAK ADA | Toleransi |
|---|---|---|---|
| S01 | `fnb`, `financial` | — | Tidak — inti pengujian generalisasi |
| S02 | `facility`, `reservation` | — | Tidak |
| S03 | `guests_pii`, `guests_profile` | — | Tidak |
| S04 | `guests_profile` | `reservation` (lunak) | Ya — retest temuan Checkpoint 8, dicatat bukan fail keras |
| S05 | `financial` | `reservation`, `fnb` | Tidak |
| S06 | `hr` | `employees_directory`, `financial` | Tidak |
| S07 | `properties_ref` | — | Tidak |
| S08 | `fnb`, `reservation` | — | Tidak pada domain; analisis Langkah 1 vs 2 non-fail |
| S09 | `hr` | — | `employees_directory` diharapkan, tidak wajib |
| S10 | `financial` | `hr` | Tidak |
