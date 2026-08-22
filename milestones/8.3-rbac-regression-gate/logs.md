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

**Commit:** (menyusul)

---
