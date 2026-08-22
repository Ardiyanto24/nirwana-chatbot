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

**Commit:** (menyusul, digabung task ini)

---
