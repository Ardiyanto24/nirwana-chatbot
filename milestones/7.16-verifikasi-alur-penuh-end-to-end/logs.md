# Logs — Milestone 7.16: Sambungan 11 (Verifikasi Alur Penuh End-to-End)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan menemukan `proses_turn()` sudah mengimplementasikan seluruh 9 layer sejak M7.15 selesai — M7.16 tidak butuh kode produksi baru sama sekali (pola sama seperti M7.2/M7.3). Menulis `milestones/7.16-verifikasi-alur-penuh-end-to-end/decisions.md` — 7 entri, seluruhnya Jenis B (forced/preseden), termasuk klarifikasi eksplisit user ("tidak perlu ada uji yang membutuhkan data terbaru") sebagai sumber paksaan Keputusan 2.

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap dengan 7 entri + Daftar Isi Keputusan.

**Commit:** `82fac6f` — `docs(milestone-7.16): keputusan`

---

## Checkpoint 2 — Peta Kejadian Eval

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 2 — Tulis rancangan.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/7.16-verifikasi-alur-penuh-end-to-end/rancangan.md` — 3 kejadian: E01 (kebutuhan tunggal sederhana, reuse `evals/7.9-.../E01.json`), E02 (kebutuhan dengan wave, reuse `evals/7.14-.../E01.json`), E03 (rujukan lintas-turn, `history` fiktif mirror `evals/7.7-.../E01.json`). Grep `start_as_current_span(` langsung ke `src/` (sudah dilakukan sebelum plan ditulis) dipakai menyusun tabel pemetaan 9 layer → nama span di `decisions.md` Keputusan 5, direplikasi di rancangan.md.

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual `rancangan.md` — 3 kejadian dengan invarian mekanisme jelas.

**Commit:** `d2ef249` — `docs(milestone-7.16): peta kejadian eval`

---

## Checkpoint 3 — Eksekusi Nyata

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20 (mencakup jeda istirahat + 2x hang E03)

**Catatan operasional:** Sesi kerja dijeda atas permintaan user ("tolong hentikan dulu semua proses di background, saya ingin beristirahat dulu") di tengah percobaan pertama E03 (proses eval + loop monitor dihentikan bersih via `TaskStop`, dikonfirmasi tidak ada proses `python`/`uv` tersisa). Saat sesi dilanjutkan ("lanjutkan kembali"), `chatbot_api` dan Docker/Jaeger ditemukan sudah mati total (`curl` timeout `000`, tidak ada proses `python`/`docker` tersisa) — dinyalakan ulang (`uvicorn` dari `nirwana-database/scripts/chatbot_api/`, `docker compose up -d` di `infra/observability/`), dikonfirmasi `/health`+`/api/services` 200 sebelum lanjut. **Akibat langsung**: restart Docker MENGHAPUS seluruh trace Jaeger sebelumnya (in-memory, tanpa volume persisten) — trace E01/E02 (dari sebelum jeda) tidak bisa di-query ulang setelah restart, tapi hasil `cakupan_span` sudah tersimpan di `payloads/E01.json`/`E02.json` SEBELUM restart terjadi, jadi tidak ada data yang hilang.

### Task 3 — Tulis `run_eval.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Adaptasi `evals/7.14-sambungan-execution/run_eval.py`: `_serialize_result()` diperluas 15 field `KeadaanTurn` lengkap (termasuk `ketergantungan`/`rewrite`/`session_memory`/`paket_narasi`/`interpretation` yang belum ada di versi M7.14), fungsi baru `_analisis_cakupan_span()` menggantikan `_analisis_urutan_wave()` M7.14 — mengecek presensi span unik per layer (`UNIQUE_LAYER_SPANS`) + window waktu untuk span "chat" ambigu (dibatasi `domain_gate.identifikasi_semua`/`orchestration.susun_paket_narasi`).

**Hasil Verifikasi**
Review kode manual sebelum eksekusi.

### Task 4 — Jalankan `run_eval.py`

**Kesesuaian dengan plan:** Sesuai plan, DIPERLUAS untuk E03 (3 percobaan, lihat Temuan/Error).

**Apa yang dilakukan**
`chatbot_api`+Jaeger dikonfirmasi `up` sebelum mulai. Jalankan `run_eval.py` — E01 selesai ~14 menit (5 panggilan LLM sekuensial sampai `domain_gate.identifikasi_semua`, lanjut penuh sampai Interpretation), E02 selesai ~15 menit setelah E01 (wave loop 2 wave, replikasi persis M7.14). E03 (percobaan 1, `session_id=eval-7.16-e03`) **hang tanpa exception** setelah maju sampai `retriever.cari_kandidat_view` (23 span, offset ~236s) — terdeteksi lewat laporan user ("di dashboard openrouter request terakhir kali masuk lebih dari 20 menit yang lalu") dikonfirmasi lewat inspeksi trace Jaeger langsung (span terakhir + CPU proses nyaris nol/flat) — dihentikan paksa (`Stop-Process`).

Ditulis `retry_e03.py` (reuse fungsi `run_eval.py` via `importlib`) — percobaan 2 (`session_id=eval-7.16-e03b`) dipantau AKTIF lewat `Monitor` (polling jumlah span Jaeger tiap 60s, ambang macet 5 tick tanpa span baru) — maju LEBIH JAUH (38 span, sampai akhir Retriever/awal Query Engine, offset ~676s) sebelum **hang lagi** (5 tick tanpa span baru, CPU proses 11.45→11.59 nyaris flat) — dihentikan paksa. Percobaan 3 (`session_id=eval-7.16-e03c`) dipantau sama, maju TERUS tanpa stale-tick berkepanjangan sampai `SELESAI` — **berhasil penuh**, `ketergantungan.is_dependent=True`/`referenced_turn_index=1`, `session_memory=[]` (dipanggil, kosong — sesuai desain, bukan `None`), `wave_count=2`, narasi jujur melaporkan status `sebagian` dengan angka nyata dari `chatbot_api`.

**Temuan**
1. **Bug verifikasi (bukan bug produksi)**: `_analisis_cakupan_span()` awalnya mewajibkan span `matching.evaluate` untuk SEMUA skenario — ternyata `match_atomic_intents()` (M1.7 Keputusan 4) mengambil fast-path NOL panggilan LLM (span ini genuinely tidak terbuka) kalau tidak ada kandidat `session_memory` berstatus `BERHASIL`, kondisi yang SELALU benar untuk E01/E02/E03 (tidak satu pun py histori "selesai" nyata) — replikasi temuan M7.9 (`jumlah_matching_evaluate: 0` di trace `evals/7.9-.../E01.json`, seharusnya sudah diantisipasi saat plan ditulis). Diperbaiki: `matching.evaluate` dikeluarkan dari `UNIQUE_LAYER_SPANS`, dilacak terpisah sebagai field informasional `matching_evaluate_ada`. Setelah koreksi, ketiga skenario `lengkap=True`.
2. **Hang 2x berturut-turut KHUSUS E03** (E01/E02 sukses percobaan pertama) — pola identik `docs/keterbatasan-diterima.md` #7 (I/O-bound blocking tanpa exception, CPU nyaris nol), kemungkinan besar karena E03 (pertanyaan komparatif, Decomposition 2-3 atomic intent × Retriever kecukupan per-item) py rantai panggilan LLM lebih panjang dari E01, memberi lebih banyak kesempatan kena hang infra acak — bukan bug spesifik E03.

**Error/Kegagalan**
2x hang E03 (lihat Temuan 2), keduanya dihentikan paksa via `Stop-Process`/`TaskStop`, tidak ada payload parsial tersimpan (proses mati sebelum `_simpan()` terpanggil).

**Diagnosis dan Perbaikan**
Hang: didiagnosis sebagai instans berulang `docs/keterbatasan-diterima.md` #7 (bukan bug kode M7.16 — mekanisme `get_openrouter_client()` timeout=90s+max_retries=1 sudah dipasang M2.1, tapi tidak menjamin 100% kasus hang tertangkap, sesuai catatan asli entri itu). Ditangani lewat retry dengan `session_id` baru + pemantauan aktif Jaeger (bukan menunggu buta) — BUKAN "diperbaiki" dari sisi kode, karena root cause tetap di luar kendali proyek ini. Bug verifikasi `matching.evaluate`: diperbaiki langsung di `run_eval.py` (lihat Temuan 1).

**Hasil Verifikasi**
3 `trace_id` nyata tersimpan (`payloads/E01.json`/`E02.json`/`E03.json` — E01/E02 dari sebelum restart Docker, trace-nya sendiri sudah tidak bisa di-query ulang tapi `cakupan_span` yang tersimpan sudah cukup untuk verifikasi). Grep secret kosong (1 false-positive `authorization.check`, dikonfirmasi bukan kredensial).

**Commit:** `0e52118` — `test(milestone-7.16): eksekusi nyata alur penuh end-to-end`

---

## Checkpoint 4 — Audit

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 5 — Tulis audit.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/7.16-verifikasi-alur-penuh-end-to-end/audit.md` — verdict kedua KK M7.16 TERPENUHI PENUH ketiga skenario (setelah koreksi verdict `matching.evaluate`), analisis lengkap per kejadian (E01 rentang layer baru terbukti, E02 bukti gabungan gap-M7.15+Execution-nyata dalam satu turn, E03 akhirnya `SEBAGIAN` nyata setelah 3 percobaan), bagian "Insiden Operasional" (jeda istirahat+restart infra, 2x hang E03), "Temuan Metodologi" (bug verifikasi `matching.evaluate`). Menambah addendum recurrence ke `docs/keterbatasan-diterima.md` #7 (dipicu oleh trigger (a) entri itu sendiri).

**Temuan**
Tidak ada temuan tak terduga di luar yang sudah dicatat Checkpoint 3.

**Hasil Verifikasi**
Review isi `audit.md` mencerminkan `payloads/*.json` apa adanya, termasuk nilai `lengkap=False` asli (dari skrip sebelum diperbaiki) yang TIDAK diubah — verdict terkoreksi didokumentasikan terpisah di audit, bukan menimpa data mentah.

**Commit:** `7851e2b` — `docs(milestone-7.16): audit` (juga mencakup `logs.md` Checkpoint 1-3)

---

## Checkpoint 5 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 6-8 — Finalisasi logs.md, tulis report.md, update status proyek

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Finalisasi `logs.md` (checkpoint ini). Tulis `milestones/7.16-verifikasi-alur-penuh-end-to-end/report.md` — kedua KK dipetakan terpenuhi penuh, konfirmasi eksplisit "Catatan Serah Terima" (`rancangan-orkestrasi-api.md` bagian akhir) soal span `invoke_agent` siap dipakai PIC 5. Update tabel "Status Proyek" `CLAUDE.md`+`AGENT.md` (working tree saja, gitignored) — M7.16 selesai, **11/11 Sambungan Level 2 selesai, PIC 7 LEVEL 2 SELESAI SEPENUHNYA**, M7.17 (Endpoint API) berikutnya.

**Hasil Verifikasi**
Baca ulang `report.md` — KK M7.16 dipetakan jujur "Terpenuhi Penuh" dengan bukti konkret (bukan diklaim tanpa dasar), termasuk catatan transparan soal koreksi bug verifikasi dan 2x hang E03. `CLAUDE.md`/`AGENT.md` diperbarui working tree, TIDAK di-commit.

**Commit:** `docs(milestone-7.16): logs, report` (CLAUDE.md/AGENT.md TIDAK termasuk — gitignored, working tree saja) + `docs(keterbatasan-diterima): recurrence hang E03 M7.16` (perubahan file backlog project-wide, dipisah dari commit milestone)

---
