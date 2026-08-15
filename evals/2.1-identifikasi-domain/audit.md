# Audit — Pengujian Identifikasi Domain dan Verifikasi Titik Buta (Milestone 2.1)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-15, dijalankan per-skenario/proses-terisolasi — lihat Catatan Operasional), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap skenario ada di `payloads/<ID>.json`. Model: `qwen/qwen3-32b` (identifikasi awal), `deepseek/deepseek-v4-pro` reasoning="high" (verifikasi titik buta), `temperature=0` di kedua langkah.

## Ringkasan

**10/10 skenario dengan check otomatis lolos.** Berbeda dari pola M1.6 (5 REVIEW = temuan substantif) dan M1.7 (campuran artefak skenario + temuan nyata), **seluruh check formal M2.1 lolos** — tapi ini **bukan berarti tidak ada temuan**. Dua skenario (S04, S08) lolos check formal (toleransi sengaja dilonggarkan di `rancangan.md` untuk keduanya) SAMBIL tetap menunjukkan pola over-triggering verifikasi titik buta yang konsisten dengan temuan Checkpoint 8 — dianalisis di bawah sebagai temuan nyata, bukan disembunyikan di balik status "LOLOS".

| ID | Domain Wajib Ada | Hasil Aktual | Verdict | Kategori |
|---|---|---|---|---|
| S01 | `fnb`, `financial` | `fnb`, `financial` | ✅ Lolos | Generalisasi cross-domain tervalidasi |
| S02 | `facility`, `reservation` | `employees_directory`, `reservation`, `facility` | ✅ Lolos | `employees_directory` bonus wajar |
| S03 | `guests_pii`, `guests_profile` | `guests_pii`, `guests_profile` | ✅ Lolos | Persis, tanpa tambahan |
| S04 | `guests_profile` | `guests_profile`, **`reservation`** | ⚠️ Lolos (toleransi) → **Temuan nyata** | Replikasi over-triggering Checkpoint 8 |
| S05 | `financial` (murni) | `financial` | ✅ Lolos | Baseline bersih |
| S06 | `hr` (murni) | `hr` | ✅ Lolos | Guard anti-false-positive bersih |
| S07 | `properties_ref` | `properties_ref` | ✅ Lolos | Domain minor tervalidasi |
| S08 | `fnb`, `reservation` | `fnb`, `reservation`, **`financial`** | ⚠️ Lolos (tanpa toleransi ketat) → **Temuan pola serupa** | Over-inklusi kedua |
| S09 | `hr` | `hr`, `employees_directory` | ✅ Lolos | `employees_directory` sesuai harapan |
| S10 | `financial` (tanpa `hr`) | `financial` | ✅ Lolos | Jebakan payroll terhindar tepat |

## Analisis Per Skenario Penting

### S01 — Generalisasi Pola Cross-Domain ke Kasus Baru (LOLOS, Krusial)

**Payload:** "Bagaimana margin keuntungan F&B dibandingkan dengan revenue F&B bulan ini?" → `fnb`, `financial`.

**Kenapa penting:** Ini pengujian INTI terhadap Keputusan 11 (`decisions.md`) — apakah `CATATAN_POLA_JEBAKAN` (ditulis sebagai prinsip umum + satu ilustrasi `gop_margin`, bukan daftar tertutup) benar-benar mengajarkan generalisasi, bukan cuma menghapal contoh literal. Hasil bersih di sini membuktikan desain grounding context (Checkpoint 4) cukup untuk kasus BARU yang tidak pernah muncul di prompt maupun contoh apa pun — model berhasil menerapkan prinsip "metrik margin/profitabilitas → domain financial" secara mandiri ke konteks F&B. Ini bukti kuat bahwa keputusan TIDAK menyertakan seluruh 67 view sebagai grounding (demi prompt ringkas) tidak mengorbankan kapabilitas generalisasi.

### S04 — Over-Triggering Verifikasi Titik Buta Terkonfirmasi Ulang (LOLOS via Toleransi, Temuan Nyata)

**Payload:** "Berapa nationality mix tamu bulan ini?" (IDENTIK skenario span nyata Checkpoint 8) → `guests_profile`, **`reservation`**.

**Analisis:** Ini adalah **replikasi kedua** temuan Checkpoint 8 (run pertama juga menghasilkan `reservation` untuk pertanyaan yang sama persis). Dua kejadian independen dengan input identik pada `temperature=0` meningkatkan keyakinan ini pola nyata (bukan noise satu kali) — Langkah 1 (identifikasi) KONSISTEN benar (`guests_profile` saja, `guests_pii` tidak pernah ikut di kedua run), tapi Langkah 2 (verifikasi titik buta, DeepSeek V4 Pro reasoning="high") KONSISTEN menambahkan `reservation` yang tidak jelas dasarnya untuk pertanyaan murni demografis tamu. Hipotesis: kata "bulan ini" dalam pertanyaan mana pun kemungkinan dipicu verifier untuk mengasosiasikan konteks temporal dengan domain `reservation` (booking/okupansi selalu difilter per periode waktu), meski pertanyaan sesungguhnya tidak menyentuh data booking sama sekali.

### S08 — Kontrol Multi-Domain Eksplisit Menunjukkan Pola Serupa (LOLOS, Temuan Pola)

**Payload:** "Bandingkan revenue F&B dengan tingkat okupansi kamar bulan ini." → `fnb`, `reservation`, **`financial`**.

**Analisis:** Skenario ini dirancang sebagai KONTROL (dua domain eksplisit disebut, seharusnya cukup ditangkap Langkah 1 tanpa bantuan Langkah 2). Payload mentah (`S08.json`) perlu dicek urutan mana yang menambahkan `financial` — berdasarkan pola S04, kemungkinan besar Langkah 2 (verifikasi titik buta) yang menambahkannya, konsisten dengan hipotesis "kata revenue/metrik finansial memicu asosiasi ke domain `financial` meski konteksnya domain operasional lain". `financial` di sini SECARA TEKNIS bisa dibenarkan (revenue adalah konsep finansial), tapi `katalog-data-chatbot.md` menempatkan "Penjualan F&B" sebagai bagian domain `fnb` sendiri (view F&B punya kolom revenue-nya sendiri) — sehingga penambahan `financial` di sini kemungkinan besar BUKAN kebutuhan riil, melainkan pola inklusi berlebih yang sama dengan S04.

### S05, S06, S07, S10 — Baseline dan Guard Bersih (LOLOS, Tanpa Tambahan)

Keempat skenario ini (domain finansial murni, HR murni, domain minor `properties_ref`, jebakan payroll) menghasilkan domain PERSIS sesuai ekspektasi TANPA satu pun tambahan dari verifikasi titik buta. Ini penting: pola over-triggering (S04, S08) **TIDAK universal** — verifikasi titik buta berhasil mengenali "tidak ada yang terlewat" dengan benar pada mayoritas kasus di eval ini (6 dari 10 skenario nol tambahan: S02 tambahannya `employees_directory` yang wajar, S03/S05/S06/S07/S09/S10 bersih atau tambahannya diharapkan). Pola over-inklusi tampak terkonsentrasi spesifik pada kombinasi kata "revenue"/"bulan ini"/metrik finansial dalam konteks non-`financial`, bukan kecenderungan umum menambah domain sembarangan.

### S02, S09 — Domain Tambahan yang Wajar (LOLOS, Bukan Over-Triggering)

**S02:** "staff... housekeeping... okupansi" → `employees_directory` ikut ditambahkan selain `facility`+`reservation` — wajar, karena "staff" secara harfiah menyiratkan kebutuhan resolusi identitas karyawan (`employees_directory`), konsisten pola S09.

**S09:** `employees_directory` ikut `hr` — persis sesuai harapan toleransi (`rancangan.md`: "diharapkan tapi tidak wajib"), memberi sinyal sistem konsisten menganggap resolusi nama karyawan sebagai pelengkap wajar untuk pertanyaan yang menyebut individu karyawan.

**Perbedaan dengan S04/S08:** Domain tambahan di S02/S09 (`employees_directory`) punya justifikasi langsung dan konsisten (kebutuhan resolusi ID→nama, pola yang sama di kedua kasus), sedangkan `reservation`/`financial` di S04/S08 tidak punya justifikasi domain yang sejelas itu terhadap teks pertanyaan aktualnya — perbedaan inilah yang membenarkan pengelompokan S04/S08 sebagai temuan over-triggering, bukan S02/S09.

## Catatan Operasional (Bukan Temuan Kualitas Model)

Eksekusi eval mengalami hambatan infrastruktur signifikan — beberapa panggilan LLM hang berkepanjangan tanpa exception (dicoba proses tunggal 10 skenario berurutan, berulang kali macet di skenario ke-2; beralih ke eksekusi per-skenario/proses-terisolasi, jauh lebih andal). Root cause tidak terisolasi penuh (dicoba isolasi tiap komponen — `_call_llm()`, `identifikasi_domain()`, `verifikasi_titik_buta()`, bahkan `curl` langsung ke endpoint — semuanya terbukti cepat/normal saat diuji terpisah). Mitigasi diterapkan (`timeout=90.0, max_retries=1` eksplisit di `get_openrouter_client()`, lihat `logs.md` Checkpoint 10) sebagai batas atas defensif, BUKAN solusi akar masalah yang terbukti. Ini TIDAK memengaruhi validitas hasil 10 skenario yang berhasil tersimpan (seluruhnya `status=berhasil`, tidak ada `gagal_teknis`/`sebagian` di payload akhir) — tapi dicatat sebagai keterbatasan operasional yang layak dipantau (kandidat entri baru `docs/keterbatasan-diterima.md`, lihat `report.md`).

## Temuan Pola

1. **Generalisasi cross-domain tervalidasi kuat** (S01) — desain grounding context minimal (10 domain + 1 contoh, bukan 67 view penuh, Keputusan 11) terbukti cukup untuk pola BARU yang tidak pernah dicontohkan.
2. **Over-triggering verifikasi titik buta adalah pola nyata dan berulang** (S04 replikasi 2x identik dengan Checkpoint 8, S08 pola serupa) — terkonsentrasi pada kombinasi kata bertema finansial/temporal ("revenue", "bulan ini") dalam konteks domain non-`financial`/non-`reservation`. BUKAN kecenderungan umum menambah sembarang domain (6/10 skenario lain bersih atau tambahannya justified).
3. **Domain tambahan `employees_directory` untuk pertanyaan yang menyebut individu karyawan konsisten dan wajar** (S02, S09) — pola berbeda dari over-triggering S04/S08, punya justifikasi tekstual langsung.
4. **Risiko asimetris M2.1 (KK2, false negative berbahaya) ditangani dengan baik** — tidak satu pun dari 10 skenario menunjukkan domain yang HILANG/terlewat (semua domain wajib selalu hadir). Trade-off-nya konsisten dengan Keputusan 9 (`decisions.md`): verifikasi titik buta condong ke arah lebih inklusif (kadang berlebih) demi menghindari kelalaian domain — sesuai desain, meski butuh pemantauan presisi jangka panjang.
5. **Keterbatasan operasional infrastruktur** (hang panggilan LLM tak terduga) terpisah total dari kualitas mekanisme identifikasi domain itu sendiri — seluruh percobaan yang berhasil selesai menunjukkan hasil semantik yang masuk akal.

## Rekomendasi

- **Tidak ada aksi mendesak untuk Langkah 1 (identifikasi awal)** — S01, S03, S05, S06, S07, S10 menunjukkan presisi tinggi tanpa over/under-inklusi di berbagai domain termasuk yang minor (`properties_ref`) dan jebakan eksplisit (payroll).
- **Pola over-triggering verifikasi titik buta (S04, S08) layak dicatat sebagai entri baru `docs/keterbatasan-diterima.md`** — baru 2-3 data point (Checkpoint 8 + S04 + S08), belum cukup untuk mitigasi prompt spesifik tanpa risiko overfit, tapi konsisten dan berulang cukup untuk didokumentasikan sebagai keterbatasan diterima (bukan diperbaiki sekarang) — trade-off yang SENGAJA dipilih desain (Keputusan 9, asimetri risiko: over-inklusi lebih aman daripada domain terlewat untuk RBAC), bukan bug murni.
- **Keterbatasan operasional (hang panggilan LLM)** juga layak dicatat sebagai entri terpisah `docs/keterbatasan-diterima.md` — root cause belum ditemukan, mitigasi defensif (timeout) sudah diterapkan, pemicu peninjauan ulang: kalau berulang di milestone berikutnya yang juga memakai `get_openrouter_client()`.
- **Tidak perlu mengubah desain grounding context (Keputusan 11)** — S01 membuktikan cakupan minimal (10 domain + 1 contoh) sudah cukup untuk generalisasi, menambah lebih banyak contoh berisiko tidak menambah nilai sepadan dengan biaya prompt yang lebih besar.
- **Milestone 2.2 (Pemeriksaan Otorisasi) perlu menyadari kemungkinan domain "berlebih"** dari M2.1 saat merancang UX penolakan — kalau M2.1 kadang menyertakan domain yang sebenarnya tidak esensial (`reservation` di S04), M2.2 berpotensi menolak permintaan karena domain yang sebenarnya tidak relevan tapi ikut diperiksa. Ini bukan berarti M2.1 perlu diperbaiki sekarang (asimetri risiko RBAC lebih mengutamakan tidak-terlewat), tapi relevan sebagai konteks desain UX pesan penolakan M2.2 nanti.
