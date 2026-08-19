# Logs — Milestone 7.13: Sambungan 8 (Query Engine → Verification Gate)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan menemukan Verification Gate (M2.4) sudah matang penuh (real DB fixture, dikonfirmasi audit M7.1), tidak ada gap tersembunyi seperti M7.11 — tapi seperti M7.11/M7.12, belum py fungsi batch level-list. Ditemukan kerumitan baru: `verifikasi_gate()` butuh fan-in dari TIGA sumber (`query_engine_result`, `retriever_result`, `cakupan_individu_result`) yang perlu dicocokkan per `atomic_intent_id` (bukan satu list linear seperti M7.11/M7.12), dan `HasilVerifikasiGate` (skema M2.4) ternyata TIDAK membawa field `atomic_intent` — satu-satunya skema hasil layer di project yang begitu. Dua keputusan genuinely terbuka diajukan ke user lewat `AskUserQuestion`: bentuk return batch (tuple vs skema baru — dikonfirmasi tuple, konsisten M7.12) dan penanganan item `lolos=False` dari M3.5 (dikonfirmasi di-skip, demi kejujuran keterbatasan). Menulis `milestones/7.13-sambungan-verification-gate/decisions.md` — 11 keputusan (2 Jenis A dari `AskUserQuestion`, 9 Jenis B forced).

**Temuan**
Verifikasi langsung `src/schemas/verification_gate.py` mengonfirmasi ketiadaan field `atomic_intent` di `HasilVerifikasiGate` SEBELUM mengajukan pertanyaan ke user — memastikan pertanyaan diajukan berdasar fakta kode, bukan asumsi laporan agent riset semata.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap dengan 11 entri + Daftar Isi Keputusan, format Jenis A/B sesuai template resmi.

**Commit:** `0df483e` — `docs(milestone-7.13): keputusan sambungan verification gate`

---

## Checkpoint 2 — Bangun `verifikasi_gate_semua()` Baru

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 2-3 — Fungsi batch baru + unit test standalone

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `tests/layers/verification_gate/test_verifikasi_gate.py` (logic/orkestrator) dan `test_verification_gate.py` (schema validator, file terpisah) untuk memahami konvensi test existing. Tambah `verifikasi_gate_semua(query_engine_result, retriever_result, cakupan_individu_result, employee_id) -> list[tuple[AtomicIntent, HasilVerifikasiGate]]` di `verifikasi_gate.py` — bangun lookup dict `retriever_by_id`/`constraint_by_id` (key `atomic_intent_id`), filter item `hasil_verifikasi is None or not hasil_verifikasi.lolos`, panggil `verifikasi_gate(hasil_verifikasi.request, constraint, employee_id, view_name_final)` per item lolos filter, span pembungkus `verification_gate.verifikasi_gate_semua` dengan `intent.count`.

Tulis 6 unit test baru: (1) dipanggil dengan argumen benar dari sumber yang tepat; (2) skip `hasil_verifikasi=None`; (3) skip `lolos=False`; (4) **multi-item TIDAK TERTUKAR** — dua atomic intent berbeda dengan urutan list SENGAJA dibalik antar sumber (retriever/constraint), memverifikasi pencocokan murni via `atomic_intent_id` bukan kebetulan sejajar by index (mitigasi Risiko utama di plan); (5) urutan+panjang dipertahankan pada campuran 3 kondisi; (6) list kosong -> hasil kosong.

**Temuan**
Test DB-dependent existing (`test_orkestrator_kk1/2/3`, butuh `DATABASE_URL`) ikut lolos tanpa di-skip — mengonfirmasi environment kerja saat ini py akses database nyata (fixture `load_employees()`), bukan cuma test mocked.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/ -v` — 26/26 test PASSED (20 existing + 6 baru), 10.41s, regresi nol.

**Commit:** `ee57584` (feat) + `2b0e558` (test)

---

## Checkpoint 3 — Sambungan Verification Gate: Implementasi

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 4-5 — Extend `KeadaanTurn` + wiring `verifikasi_gate_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah field `verification_gate: list[tuple[AtomicIntent, HasilVerifikasiGate]]` di `KeadaanTurn` — field TERAKHIR, melengkapi 12 field total. Import `AtomicIntent` (belum ada sebelumnya di `orchestration.py`, cukup ditambahkan ke import existing `src.schemas.decomposition`) dan `HasilVerifikasiGate` dari `src.schemas.verification_gate`. Di `turn_pipeline.py`: import `verifikasi_gate_semua`, panggil `verifikasi_gate_semua(query_engine_result, retriever_result, cakupan_individu_result, payload.employee_id)` sekuensial setelah `query_engine_result` final — SATU pemanggilan menerima TIGA argumen list sekaligus (beda dari seluruh Sambungan sebelumnya yang cuma menerima SATU list dari langkah tepat sebelumnya), mencerminkan fan-in 3 sumber yang sudah diantisipasi di plan.

**Temuan**
Tidak ada — pola field/wiring identik checkpoint implementasi sebelumnya, hanya jumlah argumen pemanggilan yang lebih banyak (forced by desain fan-in, sudah diantisipasi Keputusan 7 `decisions.md`).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run python -c "..."` mengonfirmasi `'verification_gate' in KeadaanTurn.model_fields` -> `True`, urutan 12 field sesuai rencana, `verifikasi_gate_semua` tersedia di `turn_pipeline` module.

**Commit:** `076a33a` — `feat(milestone-7.13): sambungkan verification gate ke proses_turn`

---

## Checkpoint 4 — Sambungan Verification Gate: Test Deterministik

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 6-7 — Extend test existing + test connectivity baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah konstanta `_VERIFICATION_GATE_DUMMY = []`. Extend 12 dari 13 test existing dengan mock `verifikasi_gate_semua` (kegagalan cabang paralel tetap tidak berubah, pola identik 4 checkpoint sebelumnya) — mock kali ini py 4 parameter (`query_engine_result, retriever_result, cakupan_individu_result, employee_id`), beda dari mock sebelumnya yang cuma 1-2 parameter, mencerminkan fan-in 3 sumber. Tulis test baru `test_orkestrator_verification_gate_menerima_query_engine_retriever_cakupan_individu_employee_id_persis` — spy merekam SEMUA 4 argumen sekaligus (identity check untuk 3 list, value check untuk `employee_id`), menutup rantai 5 test connectivity M7.11-7.13 (Otorisasi, Cakupan Individu, Retriever, Query Engine, Verification Gate).

**Temuan**
Tidak ada temuan tak terduga — pola mock berlapis tetap scalable meski jumlah argumen per mock individual bertambah (4 parameter untuk `verifikasi_gate_semua`, terbanyak sejauh ini).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_turn_pipeline.py -v` — 13/13 test PASSED (12 existing + 1 baru), 9.00s, tanpa panggilan LLM/DB nyata.

**Commit:** `8ae48a4` (test) + `d86c681` (docs)

---

## Checkpoint 5 — Peta Kejadian

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 8 — Tulis rancangan.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `evals/2.3-deteksi-cakupan-individu/payloads/S01.json`+`S02.json` (skenario HR "review kinerja Budi" dan Maintenance "tiket Andi"), `evals/7.11-.../payloads/E01.json`, dan `evals/7.12-.../payloads/E01.json` untuk menyusun 3 kejadian di `evals/7.13-sambungan-verification-gate/rancangan.md`: E01 (HR Staff, reuse S01/M7.11 E04/M7.12 E03, `terdeteksi=True` -> koreksi paksa `employee_id` diharapkan), E02 (Front Office Staff, reuse gop_margin M7.11 E01/M7.12 E01, `terdeteksi=False` semua intent -> kontrol negatif tanpa koreksi), E03 (Maintenance Staff, reuse S02, `session_id` DAN skenario yang belum pernah dieksekusi di Sambungan Level 2 manapun -> bukti independen ketiga). Ekspektasi ditulis sebagai invarian per-item (bukan jumlah tetap), konsisten preseden non-determinisme M7.9-7.12.

**Temuan**
Inspeksi langsung `evals/7.12-.../payloads/E01.json` (skenario gop_margin, dipakai lagi sebagai E02) menemukan HANYA 1 dari 3 atomic intent run itu yang `HasilVerifikasiBentukRequest.lolos=True` — 2 lainnya `lolos=False` (params kosong, M3.5 menolak). Ini eksplisit dicatat di `rancangan.md` sebagai skenario nyata yang akan di-SKIP oleh `verifikasi_gate_semua()` (Keputusan 2 M7.13) kalau berulang — E02 karena itu diposisikan sebagai kontrol negatif pelengkap, BUKAN sumber utama bukti KK (E01+E03 yang utama, sesuai Kriteria Keberhasilan plan).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review manual `rancangan.md` — 3 kejadian, invarian mekanisme (termasuk logika koreksi paksa `tegakkan_constraint_cakupan_individu()`, dikutip langsung dari `verifikasi_gate.py` baris 65-80) dan tabel ringkasan ekspektasi lengkap.

**Commit:** `16affa9` — `docs(milestone-7.13): peta kejadian eval`

---

## Checkpoint 6 — Eksekusi Nyata

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 9-10 — Tulis run_eval.py + jalankan real

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `evals/7.13-sambungan-verification-gate/run_eval.py` (mirror `evals/7.12-.../run_eval.py`) — verifikasi substantif `_verifikasi_koreksi_konsisten()` mencocokkan `hasil.verification_gate` terhadap `hasil.cakupan_individu` via `atomic_intent_id`, cek invarian: `terdeteksi=True` -> `request_final.params["employee_id"]==payload.employee_id`; `terdeteksi=False` -> `terkoreksi=False` dan params tidak berubah. `_ringkas_span()` mengekstrak `verification_gate.verifikasi_gate_semua` (`intent.count`) dan span `verification_gate.check` (`check_name="constraint_cakupan_individu"`, `verification.terkoreksi`) dari Jaeger.

Cek Docker: `docker compose ps` di `infra/observability/` kosong (stack TIDAK `up`, beda dari asumsi awal M7.11-7.12 session) — `docker compose up -d` dijalankan dulu (Jaeger+Collector+Prometheus), dikonfirmasi Jaeger API `http://localhost:16686/api/services` -> 200 sebelum eksekusi.

Jalankan `run_eval.py` di background dengan timeout 10 menit (mengacu insiden hang M7.12 ~24.7 menit) — kali ini SELESAI LANCAR percobaan pertama, exit code 0, tanpa hang. 3/3 kejadian `koreksi_benar=True` untuk seluruh item (E01: 1/1, E02: 3/3, E03: 1/1).

**Temuan**
Sebelum eksekusi eval, regresi penuh (`tests/orchestration/`, `tests/layers/{verification_gate,query_engine,retriever,domain_gate}/`, dikecualikan test konektivitas) dijalankan ulang di background sebagai langkah kebersihan sebelum Checkpoint 5-6 — percobaan PERTAMA gagal exit code 4 (dicurigai artefak transisi foreground->background tool, bukan bug nyata, output terpotong tanpa pesan error jelas), percobaan KEDUA lolos penuh 493/493 test dalam 300.95s (real DB fixture, bukan hang - genuinely 5 menit).

E02 (baseline) menghasilkan komposisi berbeda dari prediksi `rancangan.md`: 5 atomic intent (bukan 3), dan SEMUA 3 yang mencapai Query Engine `lolos=True` (bukan 1/3 seperti run M7.12 E01) - non-determinisme dikenal (`docs/keterbatasan-diterima.md` #3), dicatat transparan di `audit.md`, TIDAK memengaruhi verdict KK (E02 murni kontrol negatif pelengkap, bukan sumber utama bukti).

**Error/Kegagalan (jika ada)**
Regresi percobaan pertama exit code 4 (lihat Temuan) - diselesaikan dengan rerun, tidak ada perubahan kode diperlukan (bukan bug M7.13).

**Diagnosis dan Perbaikan (jika ada error)**
Rerun regresi di background dengan pengamatan output langsung (bukan asumsi exit code dari notifikasi task pertama) - lolos bersih percobaan kedua.

**Hasil Verifikasi**
`payloads/{E01,E02,E03}.json` tersimpan lengkap, seluruh `trace_id` terverifikasi via Jaeger API (span `verification_gate.verifikasi_gate_semua`+`verification_gate.check` ditemukan), grep secret pada payload+kode kosong.

**Commit:** *(dicatat di commit berikutnya)*

---

## Checkpoint 7 — Audit

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 11 — Tulis audit.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `evals/7.13-sambungan-verification-gate/audit.md` — tabel ringkasan verdict 3/3 LOLOS, analisis per kejadian dengan `trace_id` konkret, kutipan langsung nilai `request.params`/`request_final.params` sebelum-sesudah koreksi untuk E01/E03, penjelasan transparan penyimpangan komposisi E02 dari prediksi.

**Temuan**
Tidak ada temuan tak terduga di luar yang sudah dicatat Checkpoint 6 - seluruh 5 item lintas 3 kejadian menunjukkan pencocokan `atomic_intent_id` yang benar (constraint/view_name_final tidak tertukar), konsisten unit test Checkpoint 2.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review isi `audit.md` mencerminkan `payloads/*.json` apa adanya - seluruh angka (params sebelum/sesudah, trace_id, constraint.terdeteksi) dikutip langsung dari file JSON tersimpan.

**Commit:** `bd149f4` — `docs(milestone-7.13): audit hasil eksekusi nyata`

---

## Checkpoint 8 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 12-14 — Finalisasi logs.md, tulis report.md, update status proyek

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `milestones/7.13-sambungan-verification-gate/report.md` — 6 bagian sesuai template resmi: ringkasan hasil, KK sumber vs bukti nyata (dipetakan ke E01+E03, `trace_id` konkret), cara kerja+diagram Mermaid (fan-in 3 sumber via lookup dict, jalur skip dua sumber paksaan berbeda), perubahan dari plan (insiden regresi exit 4 + docker stack belum up, keduanya operasional bukan penyimpangan rencana), keterbatasan (tidak ada insiden hang, beda dari M7.12), follow-up (M7.14 berikutnya, 8/11 Sambungan Level 2 selesai). Update tabel "Status Proyek" di `CLAUDE.md`+`AGENT.md` (working tree saja, gitignored) — M7.13 ditandai Selesai, ringkasan naratif ditambahkan mirror pola M7.6-7.12.

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Baca ulang `report.md` — KK M7.13 sumber (1 kriteria literal) terpetakan ke bukti aktual dengan `trace_id` konkret (E01 `cdec6444...`, E03 `f49d161a...`). `CLAUDE.md`/`AGENT.md` diperbarui di working tree, TIDAK di-commit (gitignored, konsisten preseden M7.6-7.12).

**Commit:** `docs(milestone-7.13): logs, report` (CLAUDE.md/AGENT.md TIDAK termasuk — gitignored, working tree saja)

---
