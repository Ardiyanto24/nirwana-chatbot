# Logs — Milestone 8.4: LLM Eval Gate (Promptfoo → CI)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (agent Explore + bacaan langsung) memetakan 17 config `promptfooconfig.yaml` (koreksi dari "18" di `rancangan-ci-cd.md:83`), mapping 1:1 bersih ke 17 prompt `src/prompts/`, mekanisme provider Python bersama (`config.prompt_id`/`config.model` inline YAML, tanpa `apiKey`/`env:`), dan konfirmasi `push_results.py`+`src.prompts.loader.load_prompt()` sudah tersedia reusable. Diajukan ke user via `AskUserQuestion` (4 pertanyaan): (1) granularitas filter per-file vs per-layer — user pilih per-file; (2) gap grup `retriever` M8.2 — user pilih "perbaiki sekarang"; (3) mekanisme gate 100% vs threshold persentase — user pilih 100%; (4) push ke Supabase dari CI masuk cakupan sekarang vs ditunda — user pilih masuk cakupan.

**Koreksi riset penting**: SETELAH jawaban user untuk pertanyaan (2), riset lanjutan (grep `pytestmark_llm` di `tests/layers/retriever/`) menemukan premis pertanyaan itu SEBAGIAN keliru — `tests/layers/retriever/` genuinely 100% ter-mock (nihil test yang butuh `OPENROUTER_API_KEY`), jadi TIDAK ADA gap nyata di job `test-python-llm` M8.2 untuk retriever. Jawaban user ("perbaiki sekarang") tetap dihormati substantif — retriever tetap dapat path-filter penuh — tapi implementasinya lewat cakupan native 17-filter M8.4 sendiri (Keputusan 2, decisions.md), BUKAN perubahan ke job M8.2. Dikonfirmasi eksplisit di plan sebelum `ExitPlanMode`, TIDAK disembunyikan sebagai penyesuaian diam-diam.

Menulis `milestones/8.4-llm-eval-gate/decisions.md` (9 keputusan: 4 Jenis A + 5 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template, keempat keputusan `AskUserQuestion` tercermin akurat termasuk narasi koreksi riset Keputusan 2.

**Commit:** (menyusul)

---
