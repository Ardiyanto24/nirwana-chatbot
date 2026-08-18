# Audit — Sambungan 4: (Decomposition + Tarik Memory) → Pencocokan (Milestone 7.9)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) dijalankan lokal sepanjang eksekusi.

## Ringkasan

**6/6 kejadian sesuai ekspektasi VERDICT** (status match, jumlah span Pencocokan, arsip ulang) — satu koreksi kecil pada E02 (dicatat di "Temuan Metodologi"): jumlah atomic_intent yang diprediksi `rancangan.md` meleset (diprediksi 1/tunggal, aktual 3/majemuk_bergantung), TAPI verdict inti (fast-path, semua `perlu_eksekusi`, 0 span Pencocokan) tetap tepat sesuai prediksi.

| ID | Ekspektasi status | Aktual status | Ekspektasi span (`matching.evaluate`+`chat`) | Aktual span | Verdict |
|---|---|---|---|---|---|
| E01 | `[perlu_eksekusi]` | `[perlu_eksekusi]` | 0+0 | 0+0 | ✅ |
| E02 | `[perlu_eksekusi]` (diprediksi 1 intent) | `[perlu_eksekusi, perlu_eksekusi, perlu_eksekusi]` (3 intent) | 0+0 | 0+0 | ✅ (verdict tepat, jumlah intent meleset — lihat Temuan Metodologi) |
| E03 | `[selesai]` | `[selesai]` | 1+1 | 1+1 | ✅ — **bukti KK literal utama** |
| E04 | `[perlu_eksekusi]` | `[perlu_eksekusi]` | 1+1 | 1+1 | ✅ — anti false-positive |
| E05 | `[perlu_eksekusi]` | `[perlu_eksekusi]` | 0+0 | 0+0 | ✅ — filter internal via pipeline nyata |
| E06 | `[perlu_eksekusi, selesai, perlu_eksekusi]` | `[perlu_eksekusi, selesai, perlu_eksekusi]` | 1+3 | 1+3 | ✅ — granularitas per-intent, PERSIS sesuai prediksi |

## Analisis Per Kejadian

### E01 — Tarik Memory tidak dipanggil (LOLOS)

`trace_id=4520c447e9b7ac9c6a6348622b0d6126`. `ketergantungan.is_dependent=False` → `session_memory=None`. 1 atomic_intent ("occupancy Juni 2026"), `status=perlu_eksekusi`, `paket=None`. **0 span** `matching.evaluate`/`chat` — dikonfirmasi lewat query Jaeger langsung, `match_atomic_intents()` genuinely return sebelum membuka span apa pun.

### E02 — Tarik Memory dipanggil, genuinely kosong (LOLOS, dengan koreksi)

`trace_id=1dcf20899c2c7c1453285da15fee77db`. `ketergantungan.is_dependent=True`, `referenced_turn_index=1` → `session_memory=[]` (dipanggil, DB genuinely kosong untuk sesi ini). Rewrite: "Berapa revenue reservasi bulan Februari 2026 dibandingkan dengan Maret 2026?" (resolusi "bulan sebelumnya" dari Maret 2026 → Februari 2026, PLUS mempertahankan bulan asal Maret 2026 sebagai perbandingan — pola identik M7.8 E01: pertanyaan komparatif menyebut KEDUA sisi).

**Koreksi terhadap `rancangan.md`:** payload E02 diwariskan dari skenario M7.6/M7.7 ("Bandingkan dengan bulan sebelumnya") yang ternyata JUGA berupa pertanyaan komparatif — `rancangan.md` salah asumsi Decomposition-nya `tunggal` (1 atomic_intent), aktualnya `majemuk_bergantung` (3 atomic_intents: Februari independen, Maret independen, perbandingan bergantung), mirror pola E06/M7.8 E01. **Verdict inti TIDAK terpengaruh**: `session_memory=[]` tetap membuat filter `match_atomic_intents()` kosong, SEMUA 3 atomic_intent tetap `perlu_eksekusi`, **0 span** `matching.evaluate`/`chat` — persis prediksi "fast-path, origin dipanggil-tapi-kosong". Dicatat di sini sebagai koreksi transparan, bukan disembunyikan (`rancangan.md` tidak diedit retroaktif).

### E03 — Match nyata (LOLOS — bukti KK literal utama)

`trace_id=f2499243f2ebd966370740db0de116c1`. Seeding: `SessionMemoryPackage(teks_kebutuhan="Berapa occupancy rate bulan April 2026?", status=berhasil)` di turn 1. Turn 2 ("Berapa lagi occupancy April 2026 itu?") → Rewrite: "Berapa occupancy rate bulan April 2026?" (identik). Decomposition tunggal, 1 atomic_intent teks identik. Pencocokan: **`status=selesai`**, `paket` merujuk PERSIS baris yang diseed (`atomic_intent_id=a6d4482e-...` sama). **1 span** `matching.evaluate` + **1 span** `chat`, dikonfirmasi lewat relasi parent (`chat` yang `parentSpanID`-nya persis span `matching.evaluate`).

**Kesimpulan: Kriteria Keberhasilan literal Milestone 7.9 TERPENUHI PENUH** — atomic intent yang jelas merujuk hasil turn sebelumnya berhasil dicocokkan benar, dengan KEDUA jalur (Decomposition dari `decompose_question()` nyata, kandidat dari `retrieve_session_memory()` nyata membaca baris yang benar-benar tersimpan) genuinely dari pipeline `proses_turn()`, bukan data buatan yang disusun manual menyerupai output kedua jalur itu.

### E04 — Anti false-positive (LOLOS)

`trace_id=a1ff9e953e718ac9c2c2429527974097`. Seeding sama seperti E03 (kandidat occupancy April 2026, `status=berhasil`). Turn 2 ("Sekarang gimana dengan revenue F&B bulan yang sama?") → Rewrite: "Berapa revenue F&B April 2026?" — periode (April 2026) diwarisi dari referensi turn 1, TAPI metrik (revenue F&B) genuinely baru. Pencocokan: **`status=perlu_eksekusi`**, `paket=None` — TIDAK match meski kandidat tersedia dan periode SAMA persis (April 2026) — model Pencocokan benar membedakan domain/metrik, bukan sekadar overlap periode. **1 span** `matching.evaluate` + **1 span** `chat` (kandidat genuinely dievaluasi, bukan fast-path — beda dari E01/E02/E05 yang 0 span karena kandidat kosong dari awal).

### E05 — Filter internal via pipeline nyata (LOLOS)

`trace_id=a86654e2df176150ba3fc2259a11e136`. Seeding: `SessionMemoryPackage(..., status=gagal_teknis)` di turn 1 — DENGAN SENGAJA bukan `berhasil`. Turn 2 payload IDENTIK E03 ("Berapa lagi occupancy April 2026 itu?"), supaya perbedaan HANYA di status kandidat. `retrieve_session_memory()` mengembalikan baris itu apa adanya (tidak filter status) → `session_memory` di `KeadaanTurn` NON-KOSONG (1 item). TAPI `match_atomic_intents()` memfilter ke `status=berhasil` saja → filtered kosong → fast-path: `status=perlu_eksekusi`, **0 span** `matching.evaluate`/`chat`.

**Kesimpulan:** filter internal M1.7 (`status=berhasil` saja, Keputusan 4 M1.7) terbukti bekerja benar lewat DATA PIPELINE NYATA (Tarik Memory sungguhan mengembalikan baris non-berhasil, bukan `AtomicIntentMatch`/`SessionMemoryPackage` buatan tangan langsung dipassing ke fungsi Pencocokan) — pembuktian yang lebih kuat dari test M1.7 asli (yang memakai data hand-crafted).

### E06 — Majemuk campuran (LOLOS — granularitas per-intent, PERSIS sesuai prediksi)

`trace_id=165bb6ec837dc55001f225efa2482578`. Seeding sama seperti E03/E04/E05 (occupancy April 2026, `status=berhasil`). Turn 2 ("Bandingkan dengan occupancy satu tahun sebelumnya.") — payload identik `evals/7.8-.../` E01. Rewrite: "Berapa occupancy rate bulan April 2025 dibandingkan dengan occupancy rate bulan April 2026?". Decomposition `majemuk_bergantung`, 3 atomic_intents: April 2025 (independen), April 2026 (independen), perbandingan (bergantung pada keduanya).

**Hasil Pencocokan CAMPURAN, PERSIS prediksi:**
1. "occupancy April 2025" → `perlu_eksekusi` (tidak ada kandidat).
2. "occupancy April 2026" → **`selesai`**, `paket` merujuk baris yang diseed.
3. "perbandingan April 2025 vs April 2026" → `perlu_eksekusi` (tidak ada kandidat untuk hasil perbandingan itu sendiri).

**1 span** `matching.evaluate` + **3 span** `chat` (satu per atomic_intent, pool kandidat sama untuk ketiganya — dikonfirmasi lewat relasi parent, ketiga `chat` sama-sama anak span `matching.evaluate` yang sama).

**Arsip ulang dikonfirmasi lewat query DB langsung** (`retrieve_session_memory("eval-7.9-e06", 2)`, BUKAN asumsi kode): **1 baris** tersimpan (bukan 3 — hanya intent yang `selesai` yang diarsip, sesuai `archive_matched_packages()`), `atomic_intent_id` PERSIS dipertahankan dari baris asal (`5eb1ef98-...`), `turn_index` diperbarui ke 2, `sumber` dibangun ulang jadi `"session_memory (turn 1)"` (dari `"eksekusi_baru"` semula) — persis mekanisme `_sumber_arsip()` M1.7.

**Kesimpulan: Kriteria Keberhasilan M7.9 diperkuat lebih jauh dari E03** — granularitas PER-INTENT terbukti benar dalam SATU turn yang sama: sebagian atomic_intent match, sebagian tidak, tanpa saling mengganggu, keduanya dari Decomposition majemuk nyata (bukan dua turn terpisah yang disusun seolah majemuk).

## Temuan Metodologi

**Koreksi prediksi E02** (dicatat eksplisit, bukan disembunyikan): `rancangan.md` memprediksi Decomposition `tunggal` untuk payload E02, padahal payload itu (diwariskan dari skenario M7.6/M7.7, "Bandingkan dengan bulan sebelumnya") sendiri adalah pertanyaan KOMPARATIF — pola yang sama seperti M7.8 E01/M7.9 E06 (Decomposition majemuk_bergantung untuk kalimat perbandingan). Pelajaran untuk milestone Sambungan berikutnya yang mendesain payload eval: payload yang mengandung kata "bandingkan"/kalimat komparatif SELALU berisiko menghasilkan Decomposition majemuk, bukan tunggal — perlu diantisipasi eksplisit di `rancangan.md`, bukan diasumsikan tunggal secara default. Tidak mengubah VERDICT kejadian manapun di milestone ini (hasil aktual tetap sesuai ekspektasi mekanisme yang diuji).

**Konfirmasi silang E03/E05**: payload turn 2 IDENTIK persis antara E03 dan E05 ("Berapa lagi occupancy April 2026 itu?") — satu-satunya variabel yang diubah adalah `status` kandidat yang diseed (`berhasil` vs `gagal_teknis`). Hasil berbeda total (match vs fast-path) MURNI karena filter status internal `match_atomic_intents()`, mengisolasi variabel dengan bersih — desain yang direkomendasikan untuk kejadian pembanding di milestone Sambungan berikutnya.
