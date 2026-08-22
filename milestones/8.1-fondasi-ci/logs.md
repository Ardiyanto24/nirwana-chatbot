# Logs — Milestone 8.1: Fondasi CI — Kebersihan Kode & Rahasia

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (baca `rancangan-ci-cd.md`, template governance, inventaris repo nyata) menemukan: prasyarat "push ke origin" sudah terpenuhi (`git fetch` mengonfirmasi `main`=`origin/main`, berbeda dari catatan dokumen "199 commit ahead"); repo `Ardiyanto24/nirwana-chatbot` PUBLIC (`gh repo view`); tidak ada tool (`ruff`/`golangci-lint`/`gitleaks`/`pip-audit`/`govulncheck`) terpasang lokal; `go.mod`/`go.sum` sebenarnya di `custom-exporter/supabaseexporter/` bukan `custom-exporter/` root; tidak ada branch protection aktif (`gh api` → 404). Tiga keputusan diajukan ke user via `AskUserQuestion` (rule ruff, kebijakan CVE, branch protection) — user minta penjelasan lebih detail untuk opsi rule ruff sebelum memilih, diberi contoh kode konkret per tingkatan, user pilih Baseline (E,F,I,UP,B,SIM) dengan catatan upgrade ke Ketat dicatat sebagai keputusan tertunda. Zero-tolerance dipilih untuk kebijakan CVE. Branch protection dipilih nyala sekarang.

Setelah draf plan pertama (checkpoint pembersihan lint tunggal untuk seluruh `src/`+`tests/`), user meminta pendekatan lebih aman: analisis fitur yang ada dulu, bersihkan per-fitur. Inventaris `src/` dilakukan (Glob), menghasilkan 12 unit (9 layer arsitektur + Orchestration + Support lintas-layer + Go exporter) dengan jumlah file kode+test masing-masing dihitung eksplisit. Dua keputusan tambahan diajukan via `AskUserQuestion`: granularitas (per layer arsitektur, 12 unit — dipilih) dan urutan (risiko/ukuran terkecil dulu — dipilih, bukan urutan alur 9-layer).

Menulis `milestones/8.1-fondasi-ci/decisions.md` (15 keputusan: 5 Jenis A + 10 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template, seluruh 5 keputusan `AskUserQuestion` tercermin akurat, seluruh keputusan turunan menyebut sumber paksaan eksplisit.

**Commit:** `7d2b4cc` — `docs(milestone-8.1): keputusan`

---

## Checkpoint 2 — Scan Rahasia Riwayat Penuh

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 2 — Full-history gitleaks scan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`go install github.com/zricethezav/gitleaks/v8@latest` (path modul sebenarnya `zricethezav/gitleaks`, bukan `gitleaks/gitleaks` seperti percobaan pertama — org GitHub `gitleaks` menaungi repo tapi path modul Go tetap nama lama maintainer; dikoreksi begitu `go install` gagal dengan pesan "module declares its path as..."). Resolve ke `v8.30.1`. Binary terpasang di `C:\Users\LENOVO\go\bin\gitleaks.exe`.

Jalankan `gitleaks detect --source . -v` dari root repo (default scan SELURUH riwayat git, bukan cuma working tree — sesuai kebutuhan checkpoint ini karena repo baru terkonfirmasi PUBLIC di Checkpoint 1).

**Hasil Verifikasi**
Output nyata: "654 commits scanned", "scanned ~6243890 bytes (6.24 MB) in 1.07s", **"no leaks found"**. Nol temuan — baik rahasia asli maupun false-positive. Tidak perlu `.gitleaksignore`.

**Temuan**
Riwayat 199+ commit yang baru live publik (dikonfirmasi Checkpoint 1) genuinely bersih dari kredensial — tidak ada eskalasi yang diperlukan, checkpoint lanjut normal ke Checkpoint 3.

**Commit:** `3ca9bc1` — `docs(milestone-8.1): verifikasi bebas-rahasia riwayat commit penuh`

---

## Checkpoint 3 — Ruff: Konfigurasi Global

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 3 — Tambah `ruff` + tulis `[tool.ruff]`

**Kesesuaian dengan plan:** Sesuai plan, dengan 1 keputusan tambahan ditemukan di tengah checkpoint (lihat Temuan).

**Apa yang dilakukan**
`uv add --dev ruff` (resolve `ruff==0.16.4`). Tulis `[tool.ruff]` (`target-version="py313"`) + `[tool.ruff.lint]` (`select=["E","F","I","UP","B","SIM"]`) di `pyproject.toml`.

**Temuan**
`uv run ruff check src/ tests/` awal menunjukkan 933 temuan — 867 (93%) adalah `E501`. Uji coba `ruff format` di salinan scratch (`$TEMP`, bukan repo) mengurangi jadi 551, analisis distribusi (median 113 char, mean 132, max 515 char) menunjukkan mayoritas tidak bisa dibereskan formatter. Diajukan ke user via `AskUserQuestion` dengan data konkret (opsi keluarkan E501 / naikkan line-length 120 / pertahankan apa adanya) — user pilih **keluarkan E501** (`ignore=["E501"]`). Dicatat sebagai **Keputusan 16** (Jenis A, ditemukan Checkpoint 3) di `decisions.md`. Setelah `ignore` ditambahkan, total temuan turun ke **66** (53 auto-fixable, 13 manual) — skala realistis untuk 12 checkpoint berikutnya.

**Hasil Verifikasi**
`uv run ruff check src/ tests/` berhasil dieksekusi dengan config baru (exit 1 karena masih ada 66 temuan yang belum dibersihkan — itu memang cakupan Checkpoint 4-15, bukan checkpoint ini). Config sendiri valid (tidak ada error parsing TOML/config).

**Commit:** `0ff978f` — `chore(milestone-8.1): konfigurasi global ruff` (kode); `docs` menyusul untuk decisions.md+logs.md

---

## Checkpoint 4 — Bersihkan Unit 1: Input Layer

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 4 — Ruff fix Unit 1

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv run ruff format` + `uv run ruff check --fix` pada 3 file Unit 1. 2 dari 3 temuan awal auto-fixed (`UP035` import `Self` dari `typing_extensions`→`typing` di `turn_payload.py`, plus 1 lain setelah format). 1 temuan non-autofix (`SIM105` di `input_layer.py`, try/except/pass untuk `turn.index` span attribute best-effort) diperbaiki manual: diganti `contextlib.suppress(TypeError, ValueError)` — murni perubahan gaya, semantik identik.

**Hasil Verifikasi**
`ruff check` + `ruff format --check` pada 3 file → "All checks passed!" / "3 files already formatted". `uv run pytest tests/layers/test_input_layer.py` → 12/12 passed.

**Commit:** `e718cac` — `chore(milestone-8.1): pembersihan ruff - Input Layer`

---

## Checkpoint 5 — Bersihkan Unit 2: Verification Gate

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 5 — Ruff fix Unit 2

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 4 file Unit 2. Seluruh 3 temuan (2× `I001` import unsorted, 1× `UP035` `typing_extensions.Self`) auto-fixed, 0 manual.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"4 files already formatted". `uv run pytest tests/layers/verification_gate/` → 26/26 passed.

**Commit:** `96a0a39` — `chore(milestone-8.1): pembersihan ruff - Verification Gate` (termasuk logs.md checkpoint ini)

---

## Checkpoint 6 — Bersihkan Unit 3: Decomposition

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 6 — Ruff fix Unit 3 + audit/migrasi UP042 lintas-unit

**Kesesuaian dengan plan:** Sesuai plan, dengan 1 keputusan tambahan ditemukan di tengah checkpoint (lihat Temuan — Keputusan 17).

**Apa yang dilakukan**
`ruff check` pada 7 file Unit 3 menunjukkan `UP035` (auto-fix) + 2x `UP042` (`class X(str, Enum)` -> `StrEnum`, ditandai "unsafe"). Uji empiris (`str(Old.A)`="Old.A" vs `str(New.A)`="a") mengonfirmasi beda perilaku nyata. Cek lebih lanjut: 9 lokasi `UP042` total tersebar `src/schemas/{decomposition,domain_gate,matching,retriever,session_memory}.py`, dipakai 49 file lintas hampir seluruh layer.

Diajukan ke user via `AskUserQuestion` - user pilih "terapkan tapi audit dulu". Agent Explore mengaudit SELURUH `src/`+`tests/` untuk pemakaian `str()`/f-string/`.format()`/span-attribute ke-9 enum: konfirmasi 38 titik `.value` eksplisit di 19 file (termasuk titik krusial `verifikasi.py:49-50` yang membangun prompt LLM verifikasi Decomposition - dicek manual, memakai `ai.relasi.value`/`ai.label_bentuk_jawaban.value`, BUKAN `str()` mentah), HANYA 1 titik kosmetik berisiko (`tests/layers/domain_gate/test_konteks_domain.py:16`, teks pesan assert-fail saja). Dicatat sebagai **Keputusan 17** (Jenis A, ditemukan Checkpoint 6).

Terapkan `ruff check --fix --unsafe-fixes --select UP042 src/` (project-wide, 9/9 fixed). Lanjutkan pembersihan normal Unit 3 sendiri (`ruff format`+`check --fix` pada 7 file) - 3 temuan tambahan auto-fixed, 0 manual.

**Hasil Verifikasi**
Unit 3: `ruff check`+`format --check` pada 7 file -> "All checks passed!"/"7 files already formatted". `uv run pytest tests/layers/decomposition/` -> 5 passed, **1 failed** (`test_kelompok_b_verifikasi_menangkap_pemecahan_keliru`).

Migrasi UP042 lintas-unit: `uv run pytest tests/` FULL SUITE (705 test, 498.98s) -> **698 passed, 6 failed, 1 skipped**. Investigasi causality untuk 6 kegagalan (SEMUANYA di modul real-LLM-call): (1) re-run 6 test dalam isolasi - 1 (`test_kelompok_a_rujukan...`) langsung PASSED, mengonfirmasi flaky; (2) `git stash` KHUSUS 5 file schema UP042 (kembali ke kode lama `(str, Enum)`), re-run 3 test yang masih gagal - **2 dari 3 GAGAL IDENTIK tanpa perubahan saya sama sekali** (`test_titik_buta_...`, `test_guard_anti_false_positive_...`, keduanya `result.gagal=True` - bukan soal string formatting, `verifikasi_cakupan_individu` murni panggilan LLM klasifikasi); (3) `test_kelompok_b_verifikasi_menangkap_pemecahan_keliru` PASSED sekali tanpa perubahan, lalu GAGAL LAGI setelah `git stash pop` (perubahan dikembalikan) saat re-run Unit 3 penuh - diverifikasi manual `verifikasi.py:49-50` membangun prompt via `.value` eksplisit (bukan `str()` mentah), TIDAK ADA jalur kausal yang mungkin ke perubahan StrEnum. Kesimpulan: seluruh 6 kegagalan adalah non-determinisme LLM pra-eksisting (pola sudah didokumentasikan berulang di project ini - `docs/keterbatasan-diterima.md` #7 dkk.), BUKAN regresi dari migrasi StrEnum maupun pembersihan Unit 3.

`git stash pop` mengembalikan perubahan Unit 3+UP042 sebelum commit.

**Temuan**
Keputusan 17 (lihat `decisions.md`) - migrasi UP042 diterapkan project-wide di checkpoint ini, bukan ditunda per-unit. Unit 10 (`matching.py`, `session_memory.py`), Unit 11 (`retriever.py`), Unit 12 (`domain_gate.py`) akan menemukan skema mereka sudah bersih `UP042` saat checkpoint masing-masing nanti.

**Commit:** `8316ff3` — `chore(milestone-8.1): pembersihan ruff - Decomposition + migrasi StrEnum`

---

## Checkpoint 7 — Bersihkan Unit 4: Go Exporter

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 7 — Konfigurasi `.golangci.yml` + fix

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest` (v2.13.1). Tulis `.golangci.yml` di `custom-exporter/supabaseexporter/` (`version: "2"`, `linters.default: standard` + `enable: [gosec]`). `golangci-lint run --fix` menemukan 1 temuan: `staticcheck QF1008` di `factory.go:84` (`set.TelemetrySettings.Logger` → `set.Logger`) — SEBELUM menerima fix ini, dicek manual: `TelemetrySettings` adalah embedded field (anonymous) di struct `exporter.Settings`, `QF1008` murni penyederhanaan selector field embedded Go (dijamin identik oleh compiler Go, bukan perubahan API/perilaku) — diverifikasi dengan revert+re-run `golangci-lint run` tanpa `--fix` untuk melihat pesan lint mentahnya sebelum menerima fix.

**Hasil Verifikasi**
`golangci-lint run` → "0 issues." `go test ./...` → 18/18 PASS (termasuk test `Buffer`/retry/queue/eviction M6.2 yang sensitif terhadap regresi).

**Commit:** `22d98b0` — `chore(milestone-8.1): konfigurasi dan pembersihan golangci-lint exporter`

---

## Checkpoint 8 — Bersihkan Unit 5: Interpretation

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 8 — Ruff fix Unit 5

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 9 file Unit 5. Seluruh 6 temuan (5x `I001` import unsorted, 1x `UP035`) auto-fixed, 0 manual.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"9 files already formatted". `uv run pytest tests/layers/interpretation/` → **34/34 passed** (40.74s) — termasuk 2 test konektivitas real-LLM yang sebelumnya gagal karena `GAGAL_TEKNIS` di Checkpoint 6 (lihat investigasi causality di sana); kali ini lolos bersih, mengonfirmasi ulang itu memang non-determinisme LLM sesaat, bukan bug.

**Commit:** `4874931` — `chore(milestone-8.1): pembersihan ruff - Interpretation`

---

## Checkpoint 9 — Bersihkan Unit 6: Orchestration

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 9 — Ruff fix Unit 6

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 10 file Unit 6. 5 dari 6 temuan (`I001` import unsorted) auto-fixed. 1 non-autofix (`SIM105` di `turn_pipeline.py:192`, try/except/pass untuk `turn.index` span attribute — pola identik Unit 1) diperbaiki manual: `contextlib.suppress(TypeError, ValueError)` + tambah `import contextlib`.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"10 files already formatted". `uv run pytest tests/orchestration/` → 41/41 passed (5.39s).

**Commit:** `d9b3c3c` — `chore(milestone-8.1): pembersihan ruff - Orchestration`

---

## Checkpoint 10 — Bersihkan Unit 7: Query Engine

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 10 — Ruff fix Unit 7

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 11 file Unit 7. Seluruh 9 temuan (6x `I001`, 1x `UP035`, 1x `SIM300` Yoda condition) auto-fixed, 0 manual.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"11 files already formatted". `uv run pytest tests/layers/query_engine/` → 75/75 passed (11.96s).

**Commit:** `302beff` — `chore(milestone-8.1): pembersihan ruff - Query Engine`

---

## Checkpoint 11 — Bersihkan Unit 8: Support (lintas-layer)

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 11 — Ruff fix Unit 8 + verifikasi full suite

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 11 file Unit 8. Seluruh 5 temuan (2x `UP017` `datetime.UTC`, `UP035` `AsyncIterator`, `UP033` `functools.cache`, `I001`) auto-fixed, 0 manual. **`src/config/{llm,database,roles,employees}.py` dan `src/observability/{tracing,genai_semconv}.py` genuinely 0 temuan — TIDAK berubah sama sekali** (dikonfirmasi `git diff --stat` kosong).

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"11 files already formatted". **Full suite** `uv run pytest tests/` (per catatan blast-radius Unit 8) → 697 passed, **7 failed**, 1 skipped (404.62s) — seluruh 7 kegagalan di modul `domain_gate` (`test_domain_gate.py` x3, `test_verifikasi_titik_buta.py` x2, `test_verifikasi_cakupan_individu.py` x2, kedua terakhir SAMA PERSIS dengan 2 kegagalan yang sudah diinvestigasi tuntas di Checkpoint 6).

**Investigasi causality:** (1) `git diff --stat src/config/ src/observability/` KOSONG — membuktikan `llm.py`/`database.py`/dkk. byte-identik dengan sebelum checkpoint ini, sehingga TIDAK MUNGKIN jadi penyebab (file-file yang benar-benar diedit hanya `db/models.py`, `main.py`, `prompts/loader.py`, tidak satu pun diimpor `domain_gate`). (2) Re-run 5 test yang gagal dalam isolasi → **gagal identik 5/5** (konsisten, bukan random). (3) Baca kode `verifikasi_titik_buta.py:111-127`: `except APIError` DAN guard `if not response.choices:` SAMA-SAMA mengembalikan `gagal=True` — pola defensif yang SUDAH benar ada (beda dari 5 titik rentan `docs/keterbatasan-diterima.md` #17 yang belum py guard ini). Root cause: karakteristik reliabilitas OpenRouter yang sudah didokumentasikan berulang sejak M2.1 (`docs/keterbatasan-diterima.md` #7, "kadang hang/gagal tanpa exception, root cause di luar kendali kode project") — BUKAN regresi dari pembersihan Unit 8, dan bukan celah kode baru (guard defensifnya sudah benar, cuma mendeteksi kegagalan API nyata yang sedang terjadi saat sesi ini berjalan).

Tidak ada tindakan perbaikan diambil — konsisten preseden M5.1/M6.1/M7.12/M7.16/M7.17 (karakteristik infrastruktur di luar cakupan wajar, tidak dicoba "diperbaiki" definitif di level kode).

**Commit:** `c57a229` — `chore(milestone-8.1): pembersihan ruff - Support lintas-layer`

---

## Checkpoint 12 — Bersihkan Unit 9: Execution

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 12 — Ruff fix Unit 9

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 13 file Unit 9. 8 dari 9 temuan (`I001`, `UP017` datetime.UTC x4, `UP035`) auto-fixed. 1 non-autofix (`F841` variabel `kelas_span_asli` tidak terpakai di `test_pemanggilan_chatbot_api.py:296`) diperbaiki manual — dibaca konteks penuh dulu (bukan cuma percaya saran ruff): variabel murni dead code, `monkeypatch.setattr` di baris berikutnya sudah auto-revert via fixture pytest, tidak ada restorasi manual yang hilang. Dihapus.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"13 files already formatted". `uv run pytest tests/layers/execution/` → 90 passed, 1 skipped (pra-eksisting) — 15.51s.

**Commit:** `bd52285` — `chore(milestone-8.1): pembersihan ruff - Execution`

---

## Checkpoint 13 — Bersihkan Unit 10: Context Resolution

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 13 — Ruff fix Unit 10

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 14 file Unit 10. Seluruh 4 temuan auto-fixed — 2x `F401` (`enum.Enum` tidak terpakai di `matching.py`/`session_memory.py`, sisa residu migrasi `StrEnum` Checkpoint 6), 1x `UP035`, 1x `F401` import tidak terpakai di test. 0 manual.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"14 files already formatted". `uv run pytest tests/layers/context_resolution/` → 14/14 passed (61.12s).

**Commit:** `32e4314` — `chore(milestone-8.1): pembersihan ruff - Context Resolution`

---

## Checkpoint 14 — Bersihkan Unit 11: Retriever

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 14 — Ruff fix Unit 11

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 21 file Unit 11. 8 dari 9 temuan (4x `I001`, `UP033` functools.cache, `SIM114`, `F401` enum.Enum sisa residu Checkpoint 6, `UP035`) auto-fixed. 1 non-autofix (`B905` `zip()` tanpa `strict=` di `pencarian_bm25.py:155`) diperbaiki manual — dibaca konteks penuh: `view_names`/`skor_semua` DIJAMIN sama panjang (keduanya berasal dari `_view_names()` yang sama, dipakai identik saat membangun index BM25 maupun daftar nama). Tambah `strict=True` eksplisit — pilihan yang BENAR di sini (bukan `strict=False`), karena gagal cepat kalau invarian ini pernah rusak lebih sesuai prinsip "kejujuran terhadap keterbatasan" daripada diam-diam memotong data yang tidak sejajar.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"21 files already formatted". `uv run pytest tests/layers/retriever/` → 125/125 passed (6.36s).

**Commit:** `fde501a` — `chore(milestone-8.1): pembersihan ruff - Retriever`

---

## Checkpoint 15 — Bersihkan Unit 12: Domain Gate

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 15 — Ruff fix Unit 12 (unit terakhir/terbesar)

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ruff format` + `ruff check --fix` pada 22 file Unit 12. Seluruh 7 temuan (3x `I001`, 3x `UP035`, 1x `F401` enum.Enum sisa residu Checkpoint 6) auto-fixed, 0 manual.

**Hasil Verifikasi**
`ruff check`+`format --check` → "All checks passed!"/"22 files already formatted". `uv run pytest tests/layers/domain_gate/` → 249 passed, **7 failed** (178.08s) — **SET KEGAGALAN IDENTIK PERSIS** dengan Checkpoint 11 (sama 7 nama test, sama pesan `gagal=True`). Diverifikasi TIDAK ada regresi baru: `git diff src/layers/domain_gate/verifikasi_titik_buta.py` menunjukkan murni reflow whitespace `ruff format` (line-wrap ekspresi panjang, nol perubahan logika/kondisi). Kegagalan ke-3 kalinya dengan signature identik mengonfirmasi ULANG ini karakteristik reliabilitas OpenRouter pra-eksisting (`docs/keterbatasan-diterima.md` #7) yang sedang aktif terjadi sepanjang sesi kerja ini — bukan regresi Unit 12, tidak ada tindakan perbaikan diambil (konsisten Checkpoint 11).

**12/12 unit pembersihan lint (Checkpoint 4-15) SELESAI.**

**Commit:** (menyusul)

---
