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

**Commit:** (menyusul)

---
