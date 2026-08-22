# Logs — Milestone 8.3: RBAC/Authorization Regression Gate

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (agent Explore) membaca `milestones/7.11-.../` s.d. `milestones/7.14-.../` + folder `evals/` masing-masing — menemukan 5 skenario zero-leakage terbukti nyata (`gop_margin`, F&B all-denied, HR Staff "Budi", Maintenance Staff "Andi", CEO baseline), SEMUANYA belum py representasi regression test permanen (hanya pernah dibuktikan sekali via eval real-LLM/real-DB). Diajukan ke user via `AskUserQuestion`: (1) klasifikasi LLM di-mock/fix vs real API call — user pilih mock (fokus enforcement, hindari flakiness OpenRouter yang sudah 3x terbukti); (2) cakupan minimal (`gop_margin` saja) vs comprehensive (5 skenario) — user pilih comprehensive.

Menulis `milestones/8.3-rbac-regression-gate/decisions.md` (7 keputusan: 2 Jenis A + 5 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template, kedua keputusan `AskUserQuestion` tercermin akurat.

**Commit:** `1e9eb9f` — `docs(milestone-8.3): keputusan`

---

## Checkpoint 2 — Package `tests/rbac_regression/` + Fixture Bersama

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 2 — Kerangka + penentuan rantai fungsi empiris

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `evals/7.11-sambungan-retriever/payloads/E01.json` — data historis LENGKAP skenario `gop_margin` (domain teridentifikasi, keputusan otorisasi per-domain, kandidat BM25+skor, `view_name_final`). Verifikasi empiris rantai fungsi deterministik (sesuai instruksi plan, bukan asumsi):

1. `cari_bm25(teks, domain_diizinkan)` (`src/layers/retriever/pencarian_bm25.py`) dipanggil langsung dengan `OPENROUTER_API_KEY=""` — **4 milidetik**, `perlu_fallback=False` untuk KEDUA sub-kebutuhan gop_margin, skor kandidat cocok PERSIS data historis (`11.414159413192564`). Genuinely 100% deterministik (library `rank_bm25`, bukan API) — TIDAK ADA jalur ke `cari_embedding`/LLM untuk skenario ini.
2. `periksa_otorisasi_semua()` dipanggil nyata (role "Front Office Staff") — hasil PERSIS cocok historis (`financial` DENY, `reservation`+`properties_ref` ALLOW).
3. `tegakkan_constraint_cakupan_individu()` (`verifikasi_gate.py`) dikonfirmasi fungsi PURE (tanpa LLM/DB) — cocok untuk skenario Budi/Andi (Checkpoint 5-6).

**Keputusan desain:** Cakupan "zero-leakage" dibuktikan sampai level CANDIDATE GENERATION (`cari_bm25`), BUKAN sampai `evaluasi_kecukupan_struktural`/`nilai_kecocokan_makna` (M3.2, berpotensi LLM) — klaim inti RBAC ("domain ditolak tidak pernah muncul sebagai opsi") sudah genuinely terbukti di level pencarian kandidat; relevansi/pemilihan candidate terbaik adalah concern kualitas retrieval, bukan concern kebocoran, sudah tercakup test unit Retriever M3.1-3.3 terpisah.

Buat `tests/rbac_regression/__init__.py`+`test_zero_leakage.py` (docstring lengkap menjelaskan filosofi file, helper `_buat_atomic_intent()`+`_domain_diizinkan()`). Perbarui tabel "Struktur Repository" `CLAUDE.md`+`AGENT.md`.

**Hasil Verifikasi**
`uv run pytest tests/rbac_regression/ --collect-only` → "no tests collected" (0 test, wajar - kerangka). `ruff check`+`format --check` → bersih (2 import awal dihapus, belum dipakai sampai Checkpoint 3+).

**Commit:** `e4c79ab` — `feat(milestone-8.3): kerangka package tests/rbac_regression`

---

## Checkpoint 3 — Skenario 1: `gop_margin`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 3 — Encode skenario `gop_margin`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_gop_margin_financial_ditolak_view_reservation_tetap_benar()` — domain teridentifikasi di-fix `[reservation, financial, properties_ref]` (hasil historis M2.1), `periksa_otorisasi_semua()` NYATA (Front Office Staff), `cari_bm25()` NYATA dengan `domain_diizinkan` hasil otorisasi. Assert: `financial` ditolak, TIDAK ADA kandidat domain `financial`, kandidat `v_reservation_gop_impact_monthly` tetap ditemukan.

**Hasil Verifikasi**
`ruff check`+`format --check` → bersih. `OPENROUTER_API_KEY="" uv run pytest tests/rbac_regression/ -v` → **1 passed, 2.43 detik** — genuinely tanpa LLM.

**Commit:** `48a20c6` — `test(milestone-8.3): skenario zero-leakage - gop_margin`

---

## Checkpoint 4 — Skenario 2: F&B Staff All-Denied

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 4 — Encode skenario F&B Staff

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_fb_staff_seluruh_domain_ditolak_tidak_crash()` — reuse `evals/7.11-.../E03.json` (domain teridentifikasi `[financial]` saja, F&B Staff). Verifikasi empiris dulu (`cari_bm25` dengan `domain_diizinkan=[]`): `kandidat=[]`, `perlu_fallback=True` — dicatat TANPA memicu fallback sungguhan (fungsi diuji berhenti di `cari_bm25`, tidak lanjut ke `_kumpulkan_kandidat`/`cari_embedding`).

**Hasil Verifikasi**
`ruff check`+`format --check` → bersih. `OPENROUTER_API_KEY="" uv run pytest tests/rbac_regression/ -v` → **2 passed**, 1.95 detik.

**Commit:** `b9de2ce` — `test(milestone-8.3): skenario zero-leakage - F&B Staff all-denied`

---

## Checkpoint 5 — Skenario 3: HR Staff "Budi"

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 5 — Encode skenario Budi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_budi_hr_staff_koreksi_paksa_employee_id()` — reuse `evals/7.13-.../E01.json` (HR Staff, `employee_id="emp-eval"`, constraint cakupan-individu terdeteksi True dari hasil historis M2.3). `QueryEngineRequest` dibangun dengan `employee_id` SENGAJA salah ("emp-budi-salah", simulasi hasil LLM yang bisa keliru), panggil `tegakkan_constraint_cakupan_individu()` NYATA (pure function, tanpa LLM/DB) — assert `employee_id` ditimpa paksa ke `"emp-eval"`, field lain (`full_name`) tidak berubah.

**Hasil Verifikasi**
`ruff check`+`format --check` → bersih. `uv run pytest tests/rbac_regression/ -v` → **3 passed**, 2.37 detik.

**Commit:** `842e544` — `test(milestone-8.3): skenario zero-leakage - HR Staff Budi`

---

## Checkpoint 6 — Skenario 4: Maintenance Staff "Andi"

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 6 — Encode skenario Andi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_andi_maintenance_staff_domain_berbeda_koreksi_tetap_benar()` — reuse `evals/7.13-.../E03.json` (Maintenance Staff, domain `[facility, employees_directory]`, `employees_directory` DITOLAK tapi `facility` diizinkan — dikonfirmasi via `periksa_otorisasi_semua()` nyata). Constraint cakupan-individu tetap terdeteksi (di-fix), koreksi paksa `employee_id` tetap benar meski salah satu domain sumber identifikasi ditolak — bukti kedua independen (domain beda dari Budi/`hr`).

**Hasil Verifikasi**
`ruff check`+`format --check` → bersih. `uv run pytest tests/rbac_regression/ -v` → **4 passed**, 2.33 detik.

**Commit:** `466dc57` — `test(milestone-8.3): skenario zero-leakage - Maintenance Staff Andi`

---

## Checkpoint 7 — Skenario 5: CEO Baseline (Kontrol)

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 7 — Encode skenario CEO

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_ceo_baseline_tidak_ada_penolakan_atau_koreksi_palsu()` — reuse `evals/7.11-.../E02.json` (CEO tanya occupancy rate, domain teridentifikasi `[reservation, properties_ref]`, KEDUANYA diizinkan hasil historis M2.1). Berbeda dari Checkpoint 3-6 (semuanya membuktikan penolakan/koreksi BENAR terjadi), skenario ini kontrol anti-false-positive: `_domain_diizinkan()` NYATA harus mengembalikan kedua domain utuh (tidak ada yang keliru ditolak), DAN `tegakkan_constraint_cakupan_individu()` NYATA dengan `constraint.terdeteksi=False` (pertanyaan agregat, bukan individu) harus mengembalikan `terkoreksi=False` dengan params tidak berubah sama sekali.

**Hasil Verifikasi**
`ruff format`+`check` → bersih (2 file tidak berubah). `OPENROUTER_API_KEY="" uv run pytest tests/rbac_regression/ -v` → **5 passed, 2.30 detik** — genuinely tanpa LLM. Seluruh 5 skenario zero-leakage rencana plan sekarang terkodekan permanen.

**Commit:** `625099f` — `test(milestone-8.3): skenario zero-leakage - CEO baseline`

---

## Checkpoint 8 — Test "Sengaja Dibuat Gagal" (KK2 Sumber)

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 8 — Test deteksi kebocoran buatan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_sengaja_dibuat_gagal_assertion_zero_leakage_genuinely_mendeteksi()` — mereplikasi PERSIS alur `test_gop_margin_...` (Checkpoint 3), TAPI `periksa_otorisasi_semua()` di-`monkeypatch` (fixture pytest bawaan) ke `_otorisasi_bocor_sengaja()` yang SENGAJA mengizinkan seluruh domain termasuk `financial`. Dua lapis pembuktian: (1) assert eksplisit sebelum `pytest.raises` bahwa `Domain.FINANCIAL` genuinely muncul di `domain_diizinkan_bocor` (membuktikan monkeypatch benar-benar mengubah perilaku, bukan no-op); (2) `pytest.raises(AssertionError, match="KEBOCORAN")` membungkus assertion PERSIS sama (pesan sama persis) dengan yang dipakai skenario `gop_margin` asli — membuktikan assertion itu GENUINELY terpicu saat constraint dilonggarkan, bukan assertion yang kebetulan selalu lolos apapun kondisinya. Test ini sendiri harus PASS (mekanisme deteksi bekerja), beda filosofis dari 5 skenario Checkpoint 3-7 (yang membuktikan gate LOLOS untuk kasus aman).

**Hasil Verifikasi**
`ruff format`+`check` → bersih. `OPENROUTER_API_KEY="" uv run pytest tests/rbac_regression/ -v` → **6 passed, 2.30 detik**. Seluruh KK2 sumber (deteksi kebocoran buatan) terbukti sebagai unit test — verifikasi CI nyata (kode produksi dilonggarkan, bukan cuma test) menyusul Checkpoint 11.

**Commit:** `1ea9c06` — `test(milestone-8.3): skenario zero-leakage - sengaja dibuat gagal`

---

## Checkpoint 9 — Job `rbac-regression` di `ci.yml`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 9 — Tambah job CI

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah job `rbac-regression` baru di `.github/workflows/ci.yml` (antara `test-python-llm` dan `go-test`) — `uv run pytest tests/rbac_regression/ -v`, `env: DATABASE_URL` saja (secret sudah ada dari M8.2, `OPENROUTER_API_KEY` SENGAJA tidak diberikan, konsisten Keputusan 1+4). Job terpisah TOTAL dari `test-python-fast`/`test-python-llm`/`test-gate` (Keputusan 3) — tidak ditambahkan ke `needs:` job aggregator manapun, akan jadi required status check independen di Checkpoint 10.

**Hasil Verifikasi**
`go install github.com/rhysd/actionlint/cmd/actionlint@latest` (preseden M8.1/M8.2) → `actionlint .github/workflows/ci.yml` → **0 temuan**. Verifikasi fungsional nyata (run CI sungguhan) menyusul Checkpoint 11.

**Commit:** (menyusul)

---
