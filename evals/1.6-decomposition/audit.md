# Audit — Pengujian Decomposition (Milestone 1.6)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-15), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap skenario ada di `payloads/<ID>.json`. Model: `qwen/qwen3-32b` (Klasifikasi+Pemecahan), `deepseek/deepseek-v4-pro` reasoning="high" (Verifikasi).

## Ringkasan

**8/13 skenario dengan check otomatis lolos** (S13 eksploratif, tidak di-check otomatis). Berbeda dari eval M1.3/M1.4 (mayoritas "gagal" ternyata false-negative alat ukur atau kasus ambigu bertoleransi), **kelima skenario REVIEW di sini adalah temuan nyata dan substantif** — bukan kesalahan metodologi eval. Pola paling signifikan: **`retry_count` di seluruh 13 skenario cuma bernilai 0 (langsung benar) atau tepat 2 (exhausted/gagal total)** — TIDAK ADA satu pun kasus yang membaik lalu berhasil di percobaan kedua. Retry-dengan-feedback tidak menunjukkan bukti perbaikan pada 5/5 kasus gagal yang teramati.

| ID | Klasifikasi | N Intent | Verifikasi | Retry | Verdict | Kategori Temuan |
|---|---|---|---|---|---|---|
| S01 | tunggal | 1 | True | 0 | ✅ Lolos | — |
| S02 | majemuk_independen | 2 | True | 0 | ✅ Lolos | — |
| S03 | majemuk_bergantung | 3 | True | 0 | ✅ Lolos | — |
| S04 | majemuk_bergantung | 4 | True | 0 | ✅ Lolos | — |
| S05 | tunggal | 1 | **False** | **2 (exhausted)** | ❌ **Temuan** | Taksonomi label tidak cukup (deskriptif) |
| S06 | majemuk_bergantung | 6 | **False** | **2 (exhausted)** | ❌ **Temuan** | Over-dekomposisi (kebutuhan tak diminta) |
| S07 | tunggal | 2 | **False** | **2 (exhausted)** | ❌ **Temuan** | Taksonomi label tidak cukup (multi-nilai) |
| S08 | tunggal | 1 | **False** | **2 (exhausted)** | ❌ **Temuan** | Mislabel meski label benar tersedia |
| S09 | tunggal | 1 | True | 0 | ✅ Lolos | — |
| S10 | majemuk_independen | 2 | True | 0 | ✅ Lolos — **kritis, aman** | — |
| S11 | — | — | False (benar) | — | ✅ Lolos | — |
| S12 | majemuk_independen | 4 | True | 0 | ✅ Lolos | — |
| S13 | majemuk_bergantung | **11** | True | 0 | ℹ️ Eksploratif | Kompleksitas tinggi TIDAK gagal |
| S14 | majemuk_independen | 1 | **False** | **2 (exhausted)** | ❌ **Temuan** | Disagreement filosofi atomicity |

## Analisis Per Skenario Penting

### S10 — Jebakan Overlap Leksikal (LOLOS, Paling Kritis)

**Payload:** "Berapa revenue F&B bulan ini, dan berapa revenue reservasi bulan ini?" — dua metrik revenue, domain beda, TIDAK diminta dibandingkan.

**Hasil:** `majemuk_independen`, 2 kebutuhan, KEDUANYA independen — **benar**, model tidak terjebak kemiripan kata "revenue"+"bulan ini" untuk memaksakan relasi bergantung/perbandingan yang tidak diminta.

**Kenapa penting:** Skenario paling berisiko untuk false-positive relasi (mirror semangat S12 M1.3, S12 M1.4) — hasil bersih di sini memberi keyakinan tinggi terhadap mekanisme dasar, konsisten pola "diskriminasi leksikal-vs-semantik kuat" yang juga ditemukan di M1.3/M1.4.

### S05, S07 — Taksonomi `label_bentuk_jawaban` Tidak Cukup (GAGAL, Exhausted)

**S05** ("Bagaimana performa Front Office bulan ini?"): Verifier menolak label `nilai_tunggal` — "mengharapkan deskripsi atau ringkasan performa, bukan nilai tunggal." **Tidak ada satu pun dari 5 label yang benar-benar cocok** untuk pertanyaan deskriptif/naratif terbuka semacam ini.

**S07** ("Bagaimana tren occupancy rate 6 bulan terakhir?"): Verifier menolak kebutuhan pendukung "occupancy rate tiap bulan dalam 6 bulan" berlabel `nilai_tunggal`, secara eksplisit menyarankan **"nilai_berganda" atau "deret_waktu"** — dua label yang **tidak ada dalam taksonomi 5-nilai yang dikunci arsitektur**.

**Analisis:** Ini BUKAN kesalahan Pemecahan (Qwen3-32B) — modelnya sudah memilih label "paling dekat" yang tersedia dari 5 opsi. Ini gap taksonomi `label_bentuk_jawaban` itu sendiri (dikunci `arsitektur-ai-chatbot-rbac.md` §7, kontrak bersama PIC 1/PIC 4) — beberapa bentuk kebutuhan genuinely tidak punya label yang pas: (a) jawaban naratif/deskriptif terbuka, (b) kebutuhan pendukung multi-nilai yang jadi INPUT untuk tren (bukan tren itu sendiri).

**Kesimpulan:** Bukan bug M1.6 — gap arsitektur yang ditemukan lewat testing nyata, layak dicatat sebagai temuan lintas-milestone (lihat Rekomendasi).

### S08 — Mislabel Meski Label Benar Tersedia (GAGAL, Exhausted)

**Payload:** "Siapa 5 staff dengan rating kepuasan tamu tertinggi bulan ini?" — kasus peringkat yang jelas, label `peringkat` SUDAH ada di taksonomi.

**Hasil:** Pemecahan tetap memilih `nilai_tunggal`, ditolak Verifikasi ketiga kalinya berturut-turut ("seharusnya label 'daftar' atau 'list'" — verifier bahkan tidak menyebut `peringkat` yang sebenarnya sudah tersedia dan tepat).

**Analisis:** Beda dari S05/S07 (gap taksonomi genuine), ini murni kesalahan Pemecahan yang PERSISTEN — retry dengan feedback verifier 2× tidak memperbaikinya sama sekali. Kemungkinan `_SYSTEM_PROMPT` `pemecahan.py` kurang menekankan `peringkat` sebagai pilihan untuk pertanyaan "siapa/apa saja top-N" secara eksplisit.

### S06 — Over-Dekomposisi (GAGAL, Exhausted)

**Payload:** Perbandingan rating FO vs HK + tren 3 bulan masing-masing (2 permintaan eksplisit: bandingkan rata-rata, DAN tren masing-masing).

**Hasil:** Pemecahan menghasilkan 6 kebutuhan, termasuk kebutuhan ke-6 "Bandingkan tren 3 bulan terakhir FO vs HK" yang **tidak pernah diminta** (user cuma minta tren MASING-MASING, bukan perbandingan ANTAR-tren).

**Analisis:** Kebalikan dari kegagalan M1.3/M1.4 (biasanya *under*-capture) — ini kasus *over*-capture, mengarang kebutuhan tambahan yang terdengar masuk akal tapi tidak diminta. Retry 2× tidak berhasil menghapus kebutuhan berlebih ini.

### S14 — Disagreement Filosofi Atomicity (GAGAL, Exhausted)

**Payload:** "Berapa total revenue... yang digabung jadi satu angka bulan ini?" — user eksplisit minta SATU angka gabungan.

**Hasil:** Pemecahan tetap 1 kebutuhan (`tunggal`), tapi Verifier menuntut dipecah jadi per-departemen + penjumlahan, beralasan "total revenue gabungan memerlukan data revenue per departemen terlebih dahulu."

**Analisis:** Genuinely area abu-abu — user secara eksplisit minta hasil gabungan (bukan breakdown), tapi Verifier menerapkan definisi "atomik" yang lebih ketat (kalau nilai akhir SECARA LOGIS berasal dari beberapa sumber, itu bukan atomik meski usernya minta satu angka). Bukan kesalahan yang jelas salah di salah satu sisi — perbedaan interpretasi yang defensible dari kedua model.

### S13 — Kompleksitas Tinggi TIDAK Memprediksi Kegagalan (Eksploratif)

**Payload:** Skenario paling rumit yang dirancang (3 entitas × 3 dimensi + perbandingan + peringkat, dirancang untuk memancing retry-exhausted).

**Hasil:** 11 atomic intent (9 nilai dasar + 1 perbandingan + 1 peringkat), struktur relasi BENAR SEMUA, **valid di percobaan pertama** (`retry_count=0`).

**Kesimpulan:** Skenario yang saya duga PALING mungkin memicu kegagalan justru paling bersih. Kegagalan nyata (S05-S08, S14) semuanya soal *nuansa pemilihan label* atau *batas atomicity*, BUKAN soal volume/kompleksitas struktural murni.

## Temuan Pola

1. **Retry-dengan-feedback tidak menunjukkan bukti perbaikan sama sekali** — pola paling signifikan. `retry_count` selalu 0 atau 2 (exhausted), tidak pernah 1. Di 5/5 kasus gagal, feedback verifier (disisipkan jelas ke prompt retry) tidak mengubah keputusan Pemecahan sama sekali dari percobaan pertama ke kedua/ketiga. Ini mempertanyakan efektivitas nyata mekanisme retry (Keputusan 3 `decisions.md`) — BUKAN berarti keputusan itu salah (baru 5 data point), tapi data belum menunjukkan manfaat "self-healing" yang diharapkan.
2. **Kegagalan berkorelasi dengan pemilihan `label_bentuk_jawaban`, bukan dengan struktur relasi/atomicity dasar** — struktur relasi (independen/bergantung, bounds-check `bergantung_pada`) benar di SEMUA 13 skenario termasuk yang gagal verifikasi (S05-S08, S14 semuanya punya struktur relasi valid, cuma label/cakupan yang dipermasalahkan).
3. **Taksonomi `label_bentuk_jawaban` (5 nilai) py gap nyata** untuk 2 dari 5 kegagalan (S05, S07) — bukan kesalahan implementasi M1.6, tapi keterbatasan kontrak arsitektur yang dikunci di §7, ditemukan lewat testing nyata.
4. **Kompleksitas/volume TIDAK memprediksi kegagalan** — S13 (11 intent) lolos bersih di percobaan pertama, sementara S05/S08 (1 intent!) gagal exhausted.
5. **Diskriminasi leksikal-vs-semantik tetap kuat** (S10, konsisten temuan M1.3/M1.4) — anti-false-positive relasi bekerja baik.

## Rekomendasi

- **Tidak ada aksi mendesak untuk struktur relasi/bounds-check** — bekerja benar di semua 13 skenario tanpa kecuali, termasuk kasus paling kompleks (S13).
- **Taksonomi `label_bentuk_jawaban` layak ditinjau ulang** (S05, S07) — tapi ini kontrak bersama PIC 1/PIC 4 (Keputusan 8 `decisions.md`), TIDAK bisa diubah sepihak M1.6. Direkomendasikan dicatat sebagai temuan lintas-milestone (kandidat `docs/keterbatasan-diterima.md` project-wide) untuk dipertimbangkan bersama pemilik kontrak sebelum Milestone 4.x (Execution/Interpretation, konsumen `label_bentuk_jawaban` berikutnya) mulai.
- **Efektivitas mekanisme retry perlu data lebih banyak sebelum dievaluasi ulang** — 5 data point kegagalan semuanya exhausted tanpa perbaikan sama sekali adalah sinyal, tapi belum cukup untuk mengubah kebijakan (Keputusan 3) yang baru saja diputuskan user. Kalau pola sama berulang di eval milestone berikutnya yang serupa, pertimbangkan: feedback lebih actionable/terstruktur (bukan cuma prose alasan) ke prompt retry, atau reconsider apakah retry benar-benar menambah nilai dibanding cukup flag-and-pass-through (opsi yang sebelumnya ditolak user).
- **`_SYSTEM_PROMPT` `pemecahan.py` bisa diperkuat** dengan contoh eksplisit kapan pakai `peringkat` (S08 mislabel meski opsi tersedia) dan instruksi eksplisit "jangan menambah kebutuhan yang tidak diminta literal" (S06 over-dekomposisi) — perbaikan prompt yang masuk akal untuk milestone mendatang, TIDAK dilakukan sekarang (butuh lebih banyak data sebelum mengubah prompt produksi berdasarkan sedikit temuan, konsisten preseden M1.3).
- **S14 (atomicity gabungan vs breakdown)** — bukan bug, tapi ambiguitas desain yang layak diklarifikasi eksplisit ke pemilik arsitektur kalau muncul lagi: apakah kebutuhan "gabungan/total" secara eksplisit diminta user boleh tetap 1 atomic intent, atau HARUS selalu dipecah ke sumber-sumbernya?
