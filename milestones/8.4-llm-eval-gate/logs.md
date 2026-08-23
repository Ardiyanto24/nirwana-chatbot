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

**Commit:** `2390bff` — `ci(milestone-8.4): job changes-prompts (17 filter)`

---

## Checkpoint 4 — Job `prompt-eval`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 4 — Tambah job eksekusi config relevan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah job `prompt-eval` (needs: `changes-prompts`) — `if:` OR 18 kondisi (17 filter + `shared`), `timeout-minutes: 45` (Keputusan 8, mengingat riwayat hang OpenRouter). Steps: `actions/setup-node@v4` (Node 22, PERTAMA di repo) + `npm ci` (working-directory `prompt_reliability`) + `astral-sh/setup-uv@v5`+`uv sync` + `actions/cache@v4` untuk `PROMPTFOO_CACHE_PATH` (job-level `env:`, key statis per-OS) + step "Bangun daftar config" (bash, mirror pola M8.2 `test-python-llm` — `SHARED=true` union SEMUA 17 config, selain itu per-filter individual) + step loop `run_and_push.py` per config (akumulasi `FAILED` lewat `||`, TIDAK berhenti di config pertama gagal, `exit $FAILED` di akhir). Env `OPENROUTER_API_KEY`+`DATABASE_URL` (secret M8.2) + `PROMPTFOO_PYTHON=${{ github.workspace }}/.venv/bin/python` (path venv Linux CI, beda dari `Scripts/python.exe` Windows lokal).

**Hasil Verifikasi**
`actionlint .github/workflows/ci.yml` → **0 temuan**.

**Commit:** `8c94556` — `ci(milestone-8.4): job prompt-eval`

---

## Checkpoint 5 — Aggregator `prompt-eval-gate`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 5 — Tambah aggregator skip-tolerant

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah job `prompt-eval-gate` (needs: `prompt-eval`, `if: always()`) — sukses kalau `prompt-eval` `success` ATAU `skipped` (union 17 filter kosong, sah — kondisi PALING UMUM), gagal kalau `failure`. Mirror mekanisme `test-gate` (Keputusan 8, M8.2) TAPI job terpisah (Keputusan 5, decisions.md M8.4) supaya pesan gagal "prompt reliability gagal" tidak tercampur "unit test Python gagal".

**Hasil Verifikasi**
`actionlint .github/workflows/ci.yml` → **0 temuan**.

**Commit:** `305930a` — `ci(milestone-8.4): aggregator prompt-eval-gate`

---

## Checkpoint 6 — Sanity Check Lokal: Konstruksi Daftar Config

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 6 — Simulasi bash TANPA panggilan LLM

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Salin PERSIS logic step "Bangun daftar config yang relevan" dari `ci.yml` ke script scratch, jalankan 4 kombinasi env var: (1) hanya `DGI=true` → 1 config diharapkan; (2) `SHARED=true` → 17 config diharapkan; (3) `RKG=true`+`IN=true` (dua layer beda) → 2 config diharapkan; (4) semua `false` → 0 config diharapkan (kondisi yang bikin `if:` job `prompt-eval` genuinely skip). Seluruh 17 path config hasil Kombinasi 2 juga diverifikasi genuinely ada di filesystem (bukan asumsi nama file benar).

**Hasil Verifikasi**
Keempat kombinasi menghasilkan PERSIS jumlah+isi config sesuai ekspektasi manual — Kombinasi 1: 1 config (`domain_gate/identifikasi`); Kombinasi 2: 17/17 config, SEMUANYA dikonfirmasi `-f` ada di disk; Kombinasi 3: 2 config lintas-layer (`retriever/kecocokan_makna_generate`+`interpretation/narasi`); Kombinasi 4: string kosong. Script scratch dihapus setelah verifikasi.

**Commit:** (tidak ada — verifikasi murni, tidak ada perubahan file repo; dicatat di sini)

---

## Checkpoint 7 — Push Baseline + Verifikasi Run Nyata

**Mulai:** 2026-08-23 · **Selesai:** (berjalan)

### Task 7 — Push Checkpoint 1-6 ke main

**Kesesuaian dengan plan:** Penyimpangan ditemukan saat eksekusi — dicatat transparan di bawah.

**Apa yang dilakukan**
Izin eksplisit diminta+diperoleh (`AskUserQuestion`). `git push origin main` (`f660dc1..45fbf22`, 6 commit).

**Koreksi ekspektasi plan**: plan mengasumsikan push ini akan menghasilkan `changes-prompts`/`prompt-eval` SKIP bersih ("commit ini sendiri TIDAK menyentuh `src/prompts/**`/`prompt_reliability/**/*.yaml`") — asumsi ini KELIRU. `prompt_reliability/run_and_push.py` (dibuat Checkpoint 2, `5b1d0cc`) SENDIRI adalah salah satu path filter `shared` (ditulis di Checkpoint 3, `2390bff`) — karena file itu genuinely BARU di push ini, `dorny/paths-filter` benar mendeteksinya sebagai perubahan, `shared=true` terpicu, `prompt-eval` menjalankan SEMUA 17 config secara nyata (bukan skip). Ini BUKAN bug — mekanisme filter bekerja PERSIS seperti dirancang (file `shared` yang berubah memicu seluruh cakupan) — cuma prediksi "skip bersih" di plan yang tidak memperhitungkan bahwa wrapper barunya sendiri termasuk trigger `shared`. Run nyata `32603441193` diamati (bukan dihentikan) — jadi checkpoint ini SEKALIGUS jadi bukti pertama "`shared` benar-benar memicu seluruh 17 config", bukan cuma checkpoint verifikasi-skip seperti direncanakan.

**Hasil Verifikasi**
Run `32603441193` selesai **17m58s**, `prompt-eval` **GAGAL** (exit 1), `prompt-eval-gate` genuinely meneruskan kegagalan (mekanisme aggregator TERBUKTI bekerja, sisi positifnya). Rincian per config (urutan sesuai daftar `shared`, dari log `gh run view --job 97105007382 --log`):

| Config | Hasil |
|---|---|
| context_resolution/turn_dependency | 5/6 (83%) |
| context_resolution/rewrite | 5/5 (100%) |
| context_resolution/matching | 5/5 (100%) |
| decomposition/klasifikasi | 4/5 (80%) |
| decomposition/pemecahan | 3/3 (100%) |
| decomposition/verifikasi | 2/2 (100%) |
| domain_gate/identifikasi | 9/10 (90%) |
| domain_gate/verifikasi_titik_buta | 9/10 (90%) |
| domain_gate/deteksi_cakupan_individu | 10/10 (100%) |
| domain_gate/verifikasi_cakupan_individu | 10/10 (100%) |
| retriever/kecocokan_makna_generate | 8/8 (100%) |
| retriever/kecocokan_makna_verifikasi | 6/8 (75%) |
| retriever/kecukupan_struktural_fallback | 4/4 (100%) |
| query_engine/penyusunan_request | 4/4 (100%) |
| query_engine/verifikasi_bentuk_request | 3/4 (75%) |
| interpretation/narasi | 13/13 (100%) |
| interpretation/verifikasi_kesetiaan | 8/10 (80%) |
| **Total** | **108/117 (92.3%)** |

**Temuan material — dibawa ke user, TIDAK diputuskan sepihak**: dikonfirmasi via `git diff --stat f660dc1..45fbf22 -- src/prompts/ prompt_reliability/*.yaml prompt_reliability/*/*.yaml` → **KOSONG, nol perubahan** — seluruh 9 skenario gagal di 8 config adalah PERILAKU PRA-EXISTING prompt produksi, BUKAN disebabkan apa pun di Milestone 8.4 (yang sama sekali tidak menyentuh isi prompt/config). Ini genuinely baru pertama kali terukur sebagai gate CI blocking — sebelumnya `prompt_reliability/` hanya dijalankan manual/ad-hoc, README `Status` bahkan sudah mencatat preseden "7/8 lolos" untuk config retriever sebagai hasil YANG DITERIMA saat M3.2 ditutup (bukan dianggap kegagalan). Ini KONTRADIKSI langsung dengan premis Keputusan 3 (decisions.md — "assertion dirancang sebagai pemeriksaan biner", diasumsikan berarti gate 100% config-level wajar) — realitanya beberapa config PRODUKSI memang tidak pernah dirancang/diverifikasi 100% pass rate secara historis. Dibawa ke user via `AskUserQuestion` sebelum lanjut Checkpoint 8 (supaya `prompt-eval-gate` tidak langsung jadi required check yang high-friction untuk PR yang genuinely tidak menyentuh prompt manapun).

**Commit:** `be25695` — `docs(milestone-8.4): catat temuan run nyata - 108/117 (92.3%) pass rate`

Addendum: `e551b9b` — `docs(milestone-8.4): konfirmasi ulang gate 100% + catat keterbatasan #21` (user mengonfirmasi Keputusan 3 dipertahankan via `AskUserQuestion`, entri baru `docs/keterbatasan-diterima.md` #21).

---

## Checkpoint 8 — Update Branch Protection

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 8 — Tambah required status check `prompt-eval-gate`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Izin eksplisit diminta+diperoleh (`AskUserQuestion`, eksplisit menyebut risiko check ini kemungkinan MERAH saat ini karena Checkpoint 7). `gh api repos/Ardiyanto24/nirwana-chatbot/branches/main/protection -X PUT` (pola sama preseden M8.2/M8.3) — `required_status_checks.contexts` diperluas dari 8 jadi 9: `+prompt-eval-gate`. Setting lain dipertahankan identik.

**Hasil Verifikasi**
Re-fetch `--jq '.required_status_checks.contexts | length, .'` → **9 context** terkonfirmasi persis, termasuk `prompt-eval-gate`.

**Commit:** (tidak ada — perubahan setting GitHub, bukan file repo)

---

## Checkpoint 9 — PR Percobaan #1: Presisi Filter (KK1)

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 9 — Sentuh satu prompt, buktikan presisi

**Kesesuaian dengan plan:** Penyesuaian kecil — plan sempat menyebut `domain_gate/identifikasi.md` (mengikuti "mis." KK literal) sebagai kandidat, TAPI diganti `decomposition/pemecahan` (config yang terkonfirmasi 100% reliable di run Checkpoint 7, 3/3) supaya bukti presisi TIDAK tercampur dengan flakiness pra-existing #21 — `identifikasi.md` disimpan untuk Checkpoint 10 (sengaja-gagal) di mana kegagalan justru yang diinginkan.

**Apa yang dilakukan**
Izin eksplisit diminta+diperoleh. Branch `percobaan/m8-4-precisi-filter-pemecahan` — `src/prompts/decomposition/pemecahan.md` disentuh (bump `version` 1→2 + klarifikasi kecil non-breaking "index tidak boleh duplikat", diverifikasi dulu tidak bentrok assertion existing). Push + `gh pr create` → PR [#5](https://github.com/Ardiyanto24/nirwana-chatbot/pull/5).

**Hasil Verifikasi**
`gh pr checks 5 --watch` (run `32612628760`) → **`prompt-eval` PASS nyata (1m57s)**, `prompt-eval-gate` PASS, SELURUH 9 required check hijau (termasuk `prompt-eval-gate` untuk PERTAMA KALI sebagai required check). Log job (`gh run view --job 97127945468 --log`) dikonfirmasi: **HANYA 1 `::group::` block** (bukan 17), `Running 3 test cases` (persis jumlah skenario `decomposition/pemecahan`), `3 passed (100%)` — config lain (16 sisanya) TIDAK ikut jalan. PR ditutup TANPA merge, branch dihapus lokal+remote, `git status`/`checkout main` mengonfirmasi `pemecahan.md` kembali ke versi asli (`version: 1`).

**Commit:** (tidak ada di `main` — seluruh perubahan hidup HANYA di branch throwaway yang sudah dihapus)

---
