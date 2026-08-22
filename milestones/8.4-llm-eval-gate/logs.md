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

**Commit:** `2c7b242` — `docs(milestone-8.4): keputusan`

---

## Checkpoint 2 — Wrapper `run_and_push.py` + Verifikasi Lokal 1 Config

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 2 — Bangun wrapper + verifikasi end-to-end

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Verifikasi empiris dulu flag concurrency CLI: `npx promptfoo eval --help` (dari `prompt_reliability/`) mengonfirmasi `-j, --max-concurrency <number>` (default: 4) — sesuai dugaan awal di plan, dikunci ke nilai rendah `2` di wrapper (Keputusan 8, riwayat hang OpenRouter). Bangun `prompt_reliability/run_and_push.py` — terima 1 path config, extract `prompt_id`/`model` dari YAML (`yaml.safe_load(...)["providers"][0]["config"]`), `version` via `src.prompts.loader.load_prompt(prompt_id).version` (live, bukan hardcode), jalankan `npx promptfoo eval -c <config> --output <tmp>.json --max-concurrency 2 --no-progress-bar` via `subprocess.run` (portabilitas Windows: `shell=True` HANYA saat `platform.system()=="Windows"`, supaya shim `.cmd` npx ter-resolve — Linux CI tetap `shell=False`), import `push_results()` LANGSUNG (bukan subprocess CLI kedua, Keputusan 6) untuk push hasil apa pun exit code-nya, lalu propagate exit code Promptfoo apa adanya ke caller (Keputusan 3).

**Hasil Verifikasi**
`ruff check` bersih, `ruff format` (1 baris disesuaikan). Run lokal nyata `PROMPTFOO_PYTHON=.venv/Scripts/python.exe uv run python prompt_reliability/run_and_push.py prompt_reliability/decomposition/verifikasi.promptfooconfig.yaml` (config termurah, 2 test case) → **2/2 PASSED, 26 detik, exit code 0**, `push 2 baris ke prompt_eval_runs` tercetak. **Dikonfirmasi NYATA lewat query SQL langsung ke Supabase** (bukan percaya log semata) — 2 baris `PromptEvalRunRow` ditemukan (`prompt_id=decomposition.verifikasi`, `prompt_version=1` benar diextract dari frontmatter, `model=deepseek/deepseek-v4-pro` benar diextract dari YAML, `verdict=lolos` keduanya, `git_commit_hash` cocok HEAD saat itu, `scenario_id` sesuai deskripsi test case).

**Commit:** `5b1d0cc` — `feat(milestone-8.4): wrapper run_and_push.py`

---

## Checkpoint 3 — Job `changes-prompts` (17 Filter + `shared`)

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 3 — Tambah job filter path presisi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah job `changes-prompts` di `.github/workflows/ci.yml` (antara `rbac-regression` dan `go-test`) — `dorny/paths-filter@v3`, 17 filter key (satu per pasangan prompt/config, 1:1 sesuai riset Checkpoint sebelum plan) + 1 filter `shared`. 6 dari 17 filter (4 domain_gate + 2 retriever `kecocokan_makna_*`) menyertakan path file Python `render_context` (`src/layers/domain_gate/<nama>.py`, `src/layers/retriever/kecocokan_makna.py`) — dikonfirmasi file-file itu genuinely ada (`ls` langsung) sebelum ditulis ke filter. `shared` mencakup `provider.py`/`push_results.py`/`run_and_push.py` (BARU, Checkpoint 2 — bug di sini mempengaruhi SEMUA config)/`package.json`/`package-lock.json`/`src/prompts/loader.py`/`src/config/llm.py`.

**Hasil Verifikasi**
`actionlint .github/workflows/ci.yml` → **0 temuan**.

**Commit:** (menyusul)

---
