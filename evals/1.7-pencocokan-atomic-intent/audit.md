# Audit — Pengujian Pencocokan Atomic Intent × Data Session Memory (Milestone 1.7)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-15, dijalankan DUA kali — S07 memicu penambahan S11 di tengah proses, lihat Analisis), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap skenario ada di `payloads/<ID>.json`. Model: `qwen/qwen3-32b` (satu-satunya, Keputusan 3 `decisions.md`), `temperature=0`.

## Ringkasan

**9/11 skenario dengan check otomatis lolos** (run kedua, dengan S11 tambahan). Berbeda dari pola M1.6 (5 REVIEW = temuan substantif murni) dan pola M1.3/M1.4 (mayoritas REVIEW = false-negative alat ukur), **M1.7 campuran keduanya**: S07 adalah artefak desain skenario penulis (dikonfirmasi lewat S11 retest), sementara S09 adalah **temuan nyata** — konfirmasi langsung pola recency-bias/distractor-confusion yang sudah tercatat `docs/keterbatasan-diterima.md` #3, PLUS temuan baru soal non-determinisme `temperature=0` pada model ini.

| ID | N Atomic Intent | Hasil | Verdict | Kategori |
|---|---|---|---|---|
| S01 | 1 | selesai → kandidat benar | ✅ Lolos | — |
| S02 | 1 | perlu_eksekusi | ✅ Lolos — **kritis, aman** | — |
| S03 | 1 | perlu_eksekusi | ✅ Lolos | — |
| S04 | 1 | perlu_eksekusi (0 panggilan LLM — filter bekerja) | ✅ Lolos | — |
| S05 | 1 | perlu_eksekusi (0 panggilan LLM — filter bekerja) | ✅ Lolos | — |
| S06 | 2 | [a] selesai, [b] perlu_eksekusi | ✅ Lolos | — |
| S07 | 2 | [a] selesai, [b] perlu_eksekusi (bukan yang diharapkan) | ⚠️ REVIEW → **artefak desain skenario** | Paraphrase ambigu, bukan bug |
| S08 | 1 | selesai → kandidat index 3 (dari 4) | ✅ Lolos | — |
| S09 | 1 | perlu_eksekusi (run 1: selesai benar; run 2: perlu_eksekusi) | ⚠️ REVIEW (run kedua) → **Temuan nyata** | Distractor confusion + non-determinisme temp=0 |
| S10 | 1 | perlu_eksekusi | ✅ Lolos | — |
| S11 | 2 | [a] selesai, [b] selesai — keduanya kandidat sama | ✅ Lolos | Retest S07, mengonfirmasi Keputusan 6 |

## Analisis Per Skenario Penting

### S02, S03 — Anti False-Positive Entitas Kunci (LOLOS, Kritis)

**S02:** "occupancy rate Mei 2026" vs kandidat "occupancy rate bulan April 2026" (topik identik, bulan beda) → `perlu_eksekusi` — **benar**, model tidak terjebak kemiripan topik "occupancy rate" untuk memaksakan kecocokan yang salah bulan.

**S03:** "revenue F&B bulan Maret 2026" vs kandidat "jumlah komplain tamu F&B bulan Maret 2026" (domain sama, metrik beda) → `perlu_eksekusi` — **benar**, model membedakan metrik meski domain+bulan sama persis.

**Kenapa penting:** Ini yang membenarkan Keputusan 1 (LLM semantik, bukan deterministik string/keyword-overlap) — false-positive di sini akan diam-diam memberi data SALAH sebagai "selesai", risiko paling berbahaya di seluruh mekanisme M1.7 (lihat `decisions.md` Keputusan 2, asumsi asimetri risiko). Hasil bersih di kedua skenario memberi keyakinan tinggi bahwa prompt konservatif (Checkpoint 4) bekerja sesuai desain.

### S04, S05 — Filter Status Bekerja dengan Nol Panggilan LLM (LOLOS)

Kandidat dengan teks **identik persis** ke atomic intent baru, tapi `status=gagal_teknis` (S04) / `status=sebagian` (S05), difilter habis SEBELUM sampai ke LLM (Keputusan 4) — dikonfirmasi lewat payload: `results` langsung `perlu_eksekusi` tanpa span `chat` (jalur pintas Checkpoint 4). Membuktikan filter bekerja bahkan pada kasus PALING SULIT untuk filter murni string-based (teks sama persis) — keputusan Jenis A penulis (Keputusan 4) tervalidasi nyata, bukan cuma asumsi desain.

### S07 — Non-Eksklusivitas: Ternyata Artefak Desain Skenario, Bukan Bug (REVIEW → Diluruskan lewat S11)

**Payload:** [a] "berapa occupancy April 2026", [b] "occupancy rate bulan April **kemarin**" vs kandidat "occupancy rate bulan April 2026".

**Hasil:** [a] cocok benar. [b] **tidak cocok** ("kemarin" tanpa tahun eksplisit, beda dari [a] yang eksplisit "2026").

**Analisis:** Saat menulis skenario, "bulan April kemarin" dimaksud sebagai paraphrase [a] — tapi frasa ini genuinely ambigu secara temporal (tidak eksplisit tahun, "kemarin" bisa dibaca "bulan lalu" yang mengasumsikan kita sedang di Mei) — BUKAN paraphrase murni seperti yang dimaksud. Model menolak mencocokkan karena ragu — ini justru PERSIS perilaku konservatif yang diminta desain (Keputusan 2: "kalau ragu, matched=false"), bekerja dengan benar terhadap skenario yang (tanpa sengaja) mengandung ambiguitas nyata, bukan sekadar paraphrase bersih.

**Tindak lanjut:** Ditambahkan S11 dengan paraphrase yang benar-benar tidak ambigu ("nilai occupancy rate untuk periode April 2026", eksplisit tahun sama seperti [a]) — **S11 LOLOS penuh, kedua atomic intent sama-sama cocok ke kandidat yang sama**, mengonfirmasi Keputusan 6 (tidak ada eksklusivitas) genuinely bekerja seperti didesain. S07 tetap disimpan apa adanya di `payloads/` (bukan dihapus) sebagai bukti transparansi proses, diklasifikasi ulang di sini sebagai artefak desain skenario, bukan temuan mekanisme.

### S09 — Distractor Confusion + Non-Determinisme `temperature=0` (REVIEW, Temuan Nyata)

**Payload:** Kandidat [1] "occupancy rate Februari 2026" (BENAR), [2] "revenue F&B Maret 2026" (pengisi, topik lain), [3] "occupancy rate April 2026" (SALAH bulan, posisi PALING AKHIR). Atomic intent baru: "berapa occupancy Februari 2026".

**Hasil run pertama:** `selesai`, kandidat index 1 (BENAR) — sesuai ekspektasi, TIDAK terjadi recency bias (tidak salah pilih index 3).

**Hasil run kedua** (setelah menambah S11 dan menjalankan ulang SELURUH skenario dari awal, prompt+kandidat identik persis, `temperature=0`): `perlu_eksekusi` — model gagal mencocokkan SAMA SEKALI, bahkan ke kandidat index 1 yang objektif benar dan tidak ambigu.

**Analisis — dua temuan sekaligus:**
1. **`temperature=0` TIDAK menjamin determinisme penuh** untuk `qwen/qwen3-32b` via OpenRouter — prompt dan kandidat identik persis menghasilkan keputusan berbeda di dua run terpisah. Ini realitas teknis provider/model (kemungkinan routing MoE non-deterministik atau batching inferensi), bukan bug kode M1.7.
2. **Mode kegagalan BUKAN recency bias klasik** (yang diantisipasi di `rancangan.md`: salah pilih index 3 karena posisi akhir) — melainkan **distractor confusion**: kehadiran kandidat bertopik mirip (index 3, occupancy tapi beda bulan) membuat model TIDAK YAKIN bahkan terhadap kandidat yang objektif benar (index 1), sehingga menolak mencocokkan APA PUN. Ini arah kegagalan yang AMAN (fallback ke `perlu_eksekusi`, bukan false-positive ke index 3) — konsisten desain Keputusan 2 (asimetri risiko: false negative aman/murah) — tapi tetap mengurangi recall/kegunaan mekanisme pada kasus pool kandidat yang punya distractor topikal.

**Relevansi:** Berkorelasi langsung dengan `docs/keterbatasan-diterima.md` #3 (recency bias LLM pada rujukan ambigu-multi-kandidat, sudah teramati M1.3+M1.4) — manifestasi di M1.7 sedikit berbeda (confusion→non-match, bukan salah-pilih), tapi akar fenomenanya sama: LLM kesulitan disambiguasi saat ada ≥2 kandidat yang topikal mirip. Dicatat sebagai entri baru terkait di `docs/keterbatasan-diterima.md` (lihat `report.md` Bagian 5).

### S08 — Presisi Pemilihan pada Pool Besar (LOLOS)

4 kandidat topik identik (occupancy Januari-April 2026), atomic intent baru menyasar Maret — model memilih index 3 (Maret) dengan TEPAT, tidak tertukar ke bulan lain meski ke-4 kandidat sangat mirip secara leksikal. Berbeda dari S09 (yang punya distractor + posisi tersusun sengaja untuk memancing bias), di sini SEMUA kandidat topik sama (occupancy, beda bulan berurutan) dan model tetap presisi — mengindikasikan kegagalan S09 lebih terkait pola spesifik (distractor topik BEDA di tengah + kandidat SALAH di posisi akhir) daripada sekadar "banyak kandidat mirip".

## Temuan Pola

1. **Filter kandidat status=berhasil (Keputusan 4) tervalidasi nyata** — S04/S05 membuktikan filter bekerja bahkan pada kasus tersulit (teks identik persis, cuma status beda), dengan nol panggilan LLM (efisiensi sesuai desain).
2. **Prompt konservatif (Keputusan 2) bekerja sesuai desain di ARAH yang benar** — S02/S03/S09 semuanya gagal ke arah AMAN (`perlu_eksekusi`), TIDAK PERNAH ke arah berbahaya (false-positive match ke kandidat salah). Bahkan S09 (temuan nyata soal distractor confusion) tetap gagal ke arah aman, bukan memilih index 3 yang salah.
3. **Non-eksklusivitas (Keputusan 6) genuinely tervalidasi** lewat S11 (setelah S07 dikoreksi) — dua atomic intent berbeda boleh dan memang bisa sama-sama cocok ke kandidat yang sama tanpa error.
4. **`temperature=0` tidak menjamin determinisme penuh** pada model ini via OpenRouter (S09 run 1 vs run 2 berbeda hasil dengan input identik) — relevan untuk milestone LLM manapun berikutnya yang mengandalkan reproduksibilitas hasil untuk debugging/testing.
5. **Distractor topikal (bukan cuma posisi/recency) memicu ketidakpastian model** — S09 menunjukkan mode kegagalan lebih halus dari sekadar "pilih yang paling akhir": kehadiran kandidat topik-mirip-tapi-salah bisa membuat model ragu bahkan terhadap kandidat yang objektif tidak ambigu.
6. **Skenario eval bisa mengandung ambiguitas tak disengaja** (S07) — penting membedakan "model gagal" dari "skenario yang dirancang penulis ternyata ambigu" sebelum menyimpulkan temuan; S11 sebagai retest langsung menjawab keraguan ini dengan bukti, bukan asumsi.

## Rekomendasi

- **Tidak ada aksi mendesak untuk mekanisme filter status atau prompt konservatif** — keduanya bekerja benar di seluruh skenario, termasuk kasus tersulit yang dirancang (S04/S05 teks identik, S02/S03 topik sangat mirip).
- **Pola distractor-confusion (S09) layak dipantau lintas milestone**, digabung ke entri `docs/keterbatasan-diterima.md` #3 (recency bias) sebagai manifestasi baru dari fenomena yang sama — BUKAN entri terpisah, karena akar penyebabnya identik (kesulitan disambiguasi multi-kandidat topikal mirip). Baru 1 data point tambahan di M1.7 (setelah 2 dari M1.3/M1.4) — belum cukup untuk mitigasi spesifik, tapi pola berulang lintas 3 milestone dan 2 mekanisme berbeda (deteksi ketergantungan turn, rewrite, sekarang pencocokan) mulai menunjukkan ini karakteristik umum, bukan kebetulan.
- **Non-determinisme `temperature=0` perlu dicatat sebagai keterbatasan teknis** (kandidat baru `docs/keterbatasan-diterima.md`, lihat `report.md` Bagian 5) — relevan bukan cuma untuk M1.7, tapi seluruh milestone LLM proyek yang mengandalkan `temperature=0` untuk konsistensi (M1.3, M1.4, M1.6 juga memakainya). Belum ada bukti ini memengaruhi Kriteria Keberhasilan formal manapun (test suite Checkpoint 7 lolos 3/3 di percobaan tunggal), tapi berarti re-run eval/debugging TIDAK selalu bisa mengasumsikan hasil identik.
- **Tidak perlu mengubah kebijakan non-eksklusivitas (Keputusan 6)** — S11 memberi bukti langsung ia bekerja seperti didesain begitu ambiguitas skenario dihilangkan.
- **Proses menulis eval sendiri perlu kehati-hatian ekstra soal ambiguitas skenario** (S07) — untuk milestone berikutnya yang menguji paraphrase, pastikan payload benar-benar unambiguous secara eksplisit (mis. selalu sertakan tahun eksplisit untuk skenario waktu) supaya hasil REVIEW tidak bercampur antara "mekanisme gagal" vs "skenario penulis ambigu".
