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

**Commit:** (menyusul)

---
