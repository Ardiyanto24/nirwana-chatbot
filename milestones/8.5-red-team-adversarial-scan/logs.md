# Logs — Milestone 8.5: Red-Team / Adversarial Security Scan (Terjadwal)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (2 agent Explore paralel) mengonfirmasi cakupan M8.5 genuinely baru (tidak ada preseden keputusan/keterbatasan di project), memetakan kapabilitas nyata `promptfoo redteam` (plugin/strategi, mekanisme data egress default ke `api.promptfoo.app`, ketidakcocokan grader bawaan dengan output JSON classifier Domain Gate), dan mengonfirmasi ZERO instruksi pertahanan injection di keempat prompt Domain Gate. Diajukan ke user via `AskUserQuestion` (3 pertanyaan): (1) mekanisme hybrid (harvest lokal + kurasi manual) vs native redteam penuh vs manual sepenuhnya — user pilih hybrid; (2) data egress dipaksa lokal (OpenRouter) vs biarkan default `api.promptfoo.app` — user pilih dipaksa lokal; (3) repeat 1x vs repeat N=3 sebelum vonis final (mengingat `keterbatasan-diterima.md` #21 — baseline ~90% pass rate pra-existing di KEDUA prompt target) — user pilih repeat N=3 (BERBEDA dari rekomendasi 1x).

Menulis `milestones/8.5-red-team-adversarial-scan/decisions.md` (8 keputusan: 3 Jenis A + 5 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template, ketiga keputusan `AskUserQuestion` tercermin akurat termasuk keputusan user yang berbeda dari rekomendasi (Keputusan 3, repeat N=3).

**Commit:** (menyusul)

---
