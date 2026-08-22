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

**Commit:** (menyusul)

---
