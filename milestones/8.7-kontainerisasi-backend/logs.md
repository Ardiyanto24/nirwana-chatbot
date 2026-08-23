# Logs — Milestone 8.7: Kontainerisasi Backend (+ Restrukturisasi Branch Git)

Dokumen ini mencatat peristiwa nyata sepanjang Milestone 8.7 dikerjakan (2026-08-23).

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/8.7-kontainerisasi-backend/decisions.md`, 12 keputusan mencakup kronologi lengkap evolusi model branch (5 putaran `AskUserQuestion` di Plan Mode).

**Hasil Verifikasi**
Review manual mencakup seluruh keputusan plan.

**Commit:** `47c6ffb` — `docs(milestone-8.7): decisions`

---

## Checkpoint 2 — Addendum Dokumen Sumber

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 2 — Addendum `rancangan-ci-cd.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan bagian "Addendum (2026-08-23, Milestone 8.7)" di `docs/02-implementation-plan/rancangan-ci-cd.md` — tabel pemetaan branch→fungsi→environment, dampak eksplisit ke M8.8-8.10.

**Temuan**
`rancangan-ci-cd.md` sendiri ternyata belum pernah di-commit (untracked sejak sesi perencanaan PIC 8, sebelum M8.1) — dibawa masuk bersamaan dengan addendum ini (commit sama), dicatat transparan di pesan commit.

**Commit:** `feea8a0` — `docs: commit dokumen sumber PIC 8 + addendum M8.7 model 3-branch`

---

## Checkpoint 3 — Push `main` Tertunda + Buat Branch `staging`/`develop`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 3-4 — Push + buat branch

**Kesesuaian dengan plan:** Sesuai plan. Konfirmasi eksplisit diminta via `AskUserQuestion` — user menjawab "Ya, lanjutkan".

**Apa yang dilakukan**
`git push origin main` (5 commit tertunda dari M8.6+M8.7 Checkpoint 1-2). `git branch develop main` + `git branch staging main`, push keduanya.

**Hasil Verifikasi**
`git ls-remote origin refs/heads/{main,develop,staging}` — ketiganya identik di `feea8a0c4bce72e71c8fc65eb18ee4adefc1c7f4`.

---

## Checkpoint 4 — Perluas Trigger `ci.yml` ke 3 Branch

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 5

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`on.push.branches`/`on.pull_request.branches` diubah `[main]` → `[main, develop, staging]`.

**Hasil Verifikasi**
Diff hanya 2 baris di blok `on:`, 13 job existing tidak tersentuh (dikonfirmasi Checkpoint 5).

**Commit:** `391343a` — `fix(ci): perluas trigger ci.yml ke branch develop dan staging`

---

## Checkpoint 5 — Verifikasi Nyata Perluasan Trigger

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 6

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`staging` di-fast-forward ke `main`, push commit percobaan kecil (komentar) ke `staging`, lalu `develop` di-fast-forward ke `staging` dan push.

**Hasil Verifikasi**
`gh run list --branch staging`/`--branch develop` menunjukkan run nyata (`32644169066`, `32644190822`) — 13 job existing SEMUA jalan sama seperti di `main` (job path-filtered `test-python-llm`/`prompt-eval` genuinely skip bersih, `test-gate`/`prompt-eval-gate` tetap lolos).

**Commit:** `1d80bc5` (di `staging`/`develop`, komentar penanda verifikasi — tidak di-cherry-pick ke `main`, dibiarkan mengalir natural lewat merge berikutnya).

---

## Checkpoint 6 — Perbaikan `tracing.py`: OTLP Endpoint via Env Var

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 7

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`OTLP_ENDPOINT = "localhost:4317"` → `os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")`.

**Hasil Verifikasi**
`uv run python -c "..."` dua kali: tanpa env var → `localhost:4317` (default terjaga); dengan `OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317` → nilai itu yang dipakai. `ruff check` bersih.

**Commit:** `7328efb` — `fix(observability): OTLP_ENDPOINT via env var OTEL_EXPORTER_OTLP_ENDPOINT`

---

## Checkpoint 7 — Endpoint `GET /health`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 8

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Route `GET /health` ditambahkan di `src/main.py`, langsung setelah `app = FastAPI(...)`.

**Hasil Verifikasi**
`uv run uvicorn src.main:app --port 8001` lokal, `curl http://localhost:8001/health` → `200 {"status":"ok"}`.

**Commit:** `484bac1` — `feat(api): tambah endpoint GET /health`

---

## Checkpoint 8 — `.dockerignore`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 9

**Kesesuaian dengan plan:** Sesuai plan.

**Commit:** `514261c` — `feat: tambah .dockerignore`

---

## Checkpoint 9 — `Dockerfile` Backend

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 10

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`Dockerfile` 2-stage: builder (`python:3.13-slim`+`uv` dari `ghcr.io/astral-sh/uv:latest`, `uv sync --frozen --no-dev`), runtime (`python:3.13-slim` polos, copy `.venv`+`src/`, `CMD python -m uvicorn ... --host 0.0.0.0`).

**Commit:** `63053cf` — `feat: Dockerfile backend multi-stage`

---

## Checkpoint 10 — Verifikasi Build+Run Lokal

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 11

**Kesesuaian dengan plan:** Sesuai plan.

**Temuan**
Docker Desktop TIDAK berjalan di awal Checkpoint ini (`docker info` gagal connect) — dijalankan via `Start-Process "Docker Desktop.exe"`, ditunggu sampai daemon ready (`until docker info` loop, ~30-60 detik).

**Hasil Verifikasi**
`docker build -t nirwana-chatbot-backend:local .` sukses (~25s image kecil, cache layer bekerja). Container dijalankan dengan env var placeholder (DATABASE_URL/OPENROUTER_API_KEY/CHATBOT_API_BASE_URL dummy — `/health` tidak menyentuhnya). `curl /health` → 200, `curl /docs` → 200.

---

## Checkpoint 11-12 — CI Job `build-and-push-backend` dan `build-and-push-exporter`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23 (setelah 1 iterasi perbaikan, lihat Checkpoint 13)

### Task 12-13

**Kesesuaian dengan plan:** Sesuai plan (versi action awal keliru, diperbaiki di Checkpoint 13 — lihat di bawah).

**Apa yang dilakukan**
2 job baru ditambahkan `ci.yml`: `runs-on: ubuntu-24.04-arm`, `permissions: {contents: read, packages: write}` (pertama kali dipakai di file ini), `docker/setup-buildx-action`+`docker/login-action`+`docker/build-push-action`, tag `<branch>-<sha>` selalu + `latest`(main)/`staging`(develop), Trivy non-blocking. Job jalan di `push` MAUPUN `pull_request` (build-only tanpa push di PR — forced supaya bisa jadi required check `develop`/`main` tanpa gotcha "job tidak pernah jalan").

**Commit:** `c069748` — `feat(ci): job build-and-push-backend dan build-and-push-exporter`

---

## Checkpoint 13 — Verifikasi Nyata: Image ARM64 di `ghcr.io`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 14

**Kesesuaian dengan plan:** Menyimpang dari plan — percobaan pertama GAGAL, butuh 1 putaran diagnosis+perbaikan sebelum berhasil.

**Apa yang dilakukan**
`staging` di-fast-forward ke `main` (bawa Checkpoint 6-12), push. `develop` di-fast-forward ke `staging`, push.

**Error/Kegagalan**
Run pertama di `staging` (`32644890190`) GAGAL di step "Set up job" untuk KEDUA job baru:
```
##[error]Unable to resolve action `aquasecurity/trivy-action@0.28.0`, unable to find version `0.28.0`
```
Runner ARM64 sendiri berhasil provision benar (image `ubuntu-24.04-arm`, `packages: write` permission granted) — murni salah tag versi action.

**Diagnosis dan Perbaikan**
Dicek via `gh api repos/aquasecurity/trivy-action/tags` — tag asli pakai prefix `v` (`v0.36.0`, bukan `0.28.0`). Sekalian dicek 3 action Docker lain yang dipakai (`docker/setup-buildx-action`, `docker/login-action`, `docker/build-push-action`) — SEMUA versi yang ditulis di plan (`@v3`/`@v3`/`@v6`) TERNYATA sudah usang (versi riil terkini `@v4`/`@v4`/`@v7`, dikonfirmasi `gh api repos/.../tags` masing-masing sebelum commit perbaikan). Seluruhnya diperbaiki sekaligus di `main`, lalu di-merge-propagate ke `staging`→`develop`.

**Hasil Verifikasi**
Run kedua di `staging` (`32645112739`) SUKSES penuh, termasuk `build-and-push-backend`(38s)+`build-and-push-exporter`(1m55s). Push ke `main` (fix commit itu sendiri) JUGA memicu run nyata (`32645101879`) yang sukses. `develop` disinkronkan, run (`32645946815`) juga sukses.

Bukti ARM64 nyata (bukan asumsi):
- `docker manifest inspect -v ghcr.io/ardiyanto24/nirwana-chatbot-backend:latest` → `{"architecture": "arm64", "os": "linux"}`. Sama untuk `nirwana-otelcol:latest`.
- Tag scheme dikonfirmasi PERSIS sesuai desain: `staging-d718453` (dari push `staging`, tanpa tag mengambang), `develop-<sha>`+`:staging` (dari `develop`), `main-<sha>`+`:latest` (dari `main`) — dicek satu-satu via `docker manifest inspect` masing-masing tag.
- **Container ARM64 asli di-pull dan dijalankan nyata** (`docker run --platform linux/arm64`, emulasi QEMU di mesin dev amd64 — lambat, ~90 detik sampai responsif, TAPI genuinely boot tanpa crash): `curl /health` → `200 {"status":"ok"}`, log container menunjukkan `Uvicorn running on http://0.0.0.0:8001` — MEMBUKTIKAN `psycopg[binary]`/`uvloop`/`httptools` genuinely ter-load benar di ARM64, bukan diasumsikan dari kompatibilitas wheel semata.

**Baseline Trivy (dicatat, TIDAK memblokir job — Keputusan 9):**
- Backend image (`python:3.13-slim` + dependency): OS-level 189 temuan (UNKNOWN 6, LOW 66, MEDIUM 64, HIGH 50, CRITICAL 3); dependency Python 3 temuan (MEDIUM 1, HIGH 2 — termasuk `msgpack` 1.1.2 HIGH, fix tersedia 1.2.1, transitive dependency).
- Exporter image (`alpine`+Go binary): 1 temuan (UNKNOWN 1) — jauh lebih bersih, konsisten base image minimal.

Kebijakan blocking (threshold severity) BELUM diputuskan — dicatat sebagai keputusan tertunda baru di `docs/keputusan-tertunda.md` (Task 17/Bagian 6 report.md).

**Commit:** `3d55703` — `fix(ci): perbaiki versi action Docker/Trivy yang salah tag`

---

## Checkpoint 14 — Branch Protection `develop` + `main`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 15

**Kesesuaian dengan plan:** Sesuai plan. Konfirmasi eksplisit `AskUserQuestion` — user menjawab "Ya, lanjutkan".

**Apa yang dilakukan**
`gh api .../branches/main/protection -X PUT` (9→11 context, tambah `build-and-push-backend`+`build-and-push-exporter`). `gh api .../branches/develop/protection -X PUT` (11 context, sama seperti main). `staging` TIDAK disentuh.

**Hasil Verifikasi**
`gh api .../branches/main/protection --jq '.required_status_checks.contexts | length'` → 11. Sama untuk `develop`. `gh api .../branches/staging/protection` → `404 Branch not protected` (sesuai desain).

---

## Task/Checkpoint di Luar Plan

Tidak ada checkpoint BARU di luar plan — seluruh penyimpangan (versi action salah di Checkpoint 11-13) tercatat sebagai koreksi DI DALAM checkpoint yang sudah direncanakan, bukan pekerjaan baru yang lahir dari temuan tak terduga struktural.
