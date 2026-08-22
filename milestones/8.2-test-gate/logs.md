# Logs — Milestone 8.2: Test Gate — Unit & Integration

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan menemukan: dari 705 test, ~48 (8 dari 12 unit M8.1) genuinely butuh `OPENROUTER_API_KEY`/`DATABASE_URL` (mekanisme `skipif` sudah ada). Percobaan pengukuran pertama (`env -u` unset kredensial) keliru — `.env` lokal ikut termuat ulang `load_dotenv()`, dikoreksi dengan baca kode (`.gitignore`+`load_dotenv()` no-op) bukan run coba-coba berikutnya (menghindari insiden `.env` sempat ke-rename tanpa restore tepat waktu saat percobaan verifikasi kedua — segera dipulihkan, integritas file dikonfirmasi).

Diajukan ke user via `AskUserQuestion`: kredensial CI provisioned atau tidak — user memilih "full CI tapi path-filtered per layer" (bukan salah satu dari 3 opsi yang saya ajukan awal). Diskusi lanjutan (user eksplisit minta dijelaskan standar industri untuk deteksi "layer mana yang berubah" sebelum plan ditulis) — 4 pendekatan diajukan (`dorny/paths-filter`, `pytest-testmon`, native `on: paths:`, tooling monorepo besar), user pilih `dorny/paths-filter`. Plan sempat diajukan prematur sebelum diskusi ini tuntas — dikoreksi eksplisit atas permintaan user ("jangan buat plan dulu, saya diatas masih bertanya").

Menulis `milestones/8.2-test-gate/decisions.md` (9 keputusan: 2 Jenis A + 7 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template, kedua keputusan `AskUserQuestion`+diskusi tercermin akurat.

**Commit:** `4450d6e` — `docs(milestone-8.2): keputusan`

---

## Checkpoint 2 — Job `go-test`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 2 — Tambah job `go-test`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah job `go-test` di `ci.yml`, `working-directory: custom-exporter/supabaseexporter`, langkah `go test ./...`. Posisi sebelum `gitleaks` (mengikuti urutan job existing, tidak mengubah job M8.1).

**Hasil Verifikasi**
`actionlint` → 0 temuan. `go test ./...` lokal → `ok`. Verifikasi nyata GitHub Actions menyusul Checkpoint 7 (push pertama).

**Commit:** `b84e43f` — `feat(milestone-8.2): job go-test`

---

## Checkpoint 3 — Job `test-python-fast`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 3 — Tambah job `test-python-fast`

**Kesesuaian dengan plan:** Penyesuaian signifikan ditemukan mid-implementation (Keputusan 10, `decisions.md`).

**Apa yang dilakukan**
Rencana awal (`--ignore` 8 file bergerbang) diganti sebelum implementasi: `--ignore` per-file akan menciptakan celah cakupan di file campuran gated+non-gated. Diganti `pytest tests/` polos, mengandalkan `skipif` existing per-fungsi.

Verifikasi lokal AMAN (belajar dari insiden `.env` rename M8.1) — pakai `VAR="" uv run pytest ...` (env var di-set KOSONG, bukan di-unset/file di-rename; `python-dotenv` default `override=False` tidak menimpa var yang sudah "ada" meski kosong) — TIDAK PERNAH menyentuh `.env` asli. Percobaan pertama (`OPENROUTER_API_KEY=""` + `DATABASE_URL=""` keduanya kosong) menemukan **27 test GAGAL + 1 collection ERROR** (`tests/test_main.py`, `tests/layers/test_input_layer.py`, `tests/orchestration/test_turn_pipeline.py`) — bukan skip bersih. Investigasi: `src/config/roles.py::load_valid_roles()` (database-backed sejak M1.5) dipanggil dari validasi `TurnPayload.role_title`, dampaknya jauh lebih luas dari 8 grup yang dipetakan plan. Dicatat **Keputusan 10**: `DATABASE_URL` (cepat+andal) disediakan ke `test-python-fast`, HANYA `OPENROUTER_API_KEY` (mahal+flaky, terbukti 3x M8.1) yang tetap tanpa kredensial di job ini.

Percobaan kedua (`OPENROUTER_API_KEY=""` saja, `DATABASE_URL` asli dari `.env`): **670 passed, 35 skipped, 17.33 detik** — nol gagal. Daftar skip presisi diambil (`-v -rs`) untuk merevisi tabel pemetaan Checkpoint 4: HANYA 5 grup (bukan 8) genuinely masih py test `OPENROUTER_API_KEY`-gated (`verification_gate`+`orchestration` sepenuhnya tercakup baseline; `execution` py 1 skip TAPI alasannya bukan kredensial, deliberate-skip permanen).

`ci.yml` diberi `env: DATABASE_URL: ${{ secrets.DATABASE_URL }}` di job `test-python-fast`, komentar menjelaskan alasan asimetri (DB diberi, LLM tidak).

**Hasil Verifikasi**
`actionlint` → 0 temuan (2x, setelah tambah job dan setelah tambah `env:`). Verifikasi fungsional lokal: 670 passed/35 skipped/17.33s (dengan `DATABASE_URL` asli+`OPENROUTER_API_KEY=""`). Verifikasi nyata GitHub Actions (dengan secret asli tersimpan sebagai GitHub Secret, bukan var lokal) menyusul Checkpoint 7.

**Commit:** `1ce6c11` — `feat(milestone-8.2): job test-python-fast`

---

## Checkpoint 4 — `dorny/paths-filter` + job `test-python-llm`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 4 — Tambah step path-filter + job path-filtered

**Kesesuaian dengan plan:** Sesuai plan (dengan tabel grup direvisi 8→5 sesuai Keputusan 10 Checkpoint 3).

**Apa yang dilakukan**
Job `changes` baru (step `dorny/paths-filter@v3`) — 5 grup (`context_resolution`, `decomposition`, `domain_gate`, `query_engine`, `interpretation`) + `shared` (`src/config/llm.py`, `src/prompts/loader.py`, Keputusan 6). Tiap grup mencakup `src/layers/<nama>/**`, schema terkait, config terkait, DAN `src/prompts/<nama>/**` (Keputusan 7).

Job `test-python-llm` — `needs: changes`, `if:` di level job (union OR seluruh grup) supaya job SKIP BERSIH (bukan cuma langkah kosong) kalau tidak ada grup relevan berubah — step "Bangun daftar file test target" pakai `env:` untuk membawa nilai `needs.changes.outputs.*` ke bash (bukan interpolasi `${{ }}` langsung di script, praktik lebih aman) lalu `pytest <daftar file>` dengan KEDUA secret (`OPENROUTER_API_KEY`+`DATABASE_URL`).

**Hasil Verifikasi**
`actionlint` → 0 temuan. Sanity check lokal: union SEMUA 11 file (skenario `shared=true`) → `pytest --collect-only` → 69 test collected, tidak ada error path. Verifikasi FUNGSIONAL (union benar-benar path-filtered sesuai grup yang berubah, dengan secret asli) tidak bisa dites sampai secret GitHub genuinely ada — menyusul Checkpoint 9-10.

**Commit:** `78bdddb` — `feat(milestone-8.2): job test-python-llm path-filtered`

---

## Checkpoint 5 — Job Aggregator `test-gate`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 5 — Tambah job `test-gate`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Job `test-gate` — `needs: [test-python-fast, go-test, test-python-llm]`, `if: always()` (wajib, tanpa ini job ikut ter-skip otomatis kalau salah satu `needs` skip). Step tunggal memeriksa `needs.*.result` eksplisit: `test-python-fast`+`go-test` WAJIB `success`; `test-python-llm` boleh `success` ATAU `skipped` (skip union-kosong itu sah), selain itu `exit 1` dengan pesan `::error::` jelas job mana yang gagal.

**Hasil Verifikasi**
`actionlint` → 0 temuan. Logic diverifikasi baca manual (tidak bisa dites nyata sampai ada run CI sungguhan dengan kombinasi hasil beragam — menyusul Checkpoint 7+).

**Commit:** `91b87c8` — `feat(milestone-8.2): job test-gate aggregator`

---

## Checkpoint 6 — User Menambahkan Secret

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 6 — Verifikasi keberadaan secret

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
User menjalankan `gh secret set OPENROUTER_API_KEY`/`DATABASE_URL` sendiri (saya hanya memberi contoh command, TIDAK menjalankannya — larangan keamanan memasukkan API key).

**Hasil Verifikasi**
`gh secret list --repo Ardiyanto24/nirwana-chatbot` → kedua nama secret terkonfirmasi ada (`DATABASE_URL`, `OPENROUTER_API_KEY`), timestamp `2026-08-22`. Nilai TIDAK terlihat/tidak diperiksa (`gh secret list` memang tidak pernah menampilkan nilai).

**Commit:** Tidak ada — perubahan GitHub Settings murni oleh user, tidak ada file repo yang berubah.

---

## Checkpoint 7 — Push Pertama + Verifikasi Dasar

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 7 — Push + amati run CI nyata

**Kesesuaian dengan plan:** Sesuai plan, dengan 1 bug nyata ditemukan+diperbaiki mid-checkpoint (Keputusan 11).

**Apa yang dilakukan**
User mengonfirmasi izin push (`AskUserQuestion`). Push 6 commit Checkpoint 1-6 (`d716990..d570b09`) — run CI nyata pertama (`32558796535`) terpicu.

**Hasil run pertama:** `changes`✓, `go-test`✓, `gitleaks`✓, `golangci-lint`✓, `ruff`✓, `dependency-scan`✓ (job M8.1 tidak terpengaruh), `test-python-llm` SKIP bersih (union kosong — push ini cuma menyentuh `.github/`+`milestones/`+`docs/`, benar TIDAK memicu grup manapun). **`test-python-fast` GAGAL** (1 test) — `test-gate` BENAR mendeteksinya sebagai kegagalan (bukti logic aggregator Checkpoint 5 bekerja: `test-python-llm` yang skip TIDAK menggagalkan gate, tapi `test-python-fast` yang genuinely gagal MENGGAGALKAN gate).

Investigasi (Keputusan 11): `test_klasifikasi_respons_revisi.py::test_400_lalu_200_di_revisi_kedua_berhasil` genuinely memanggil `CHATBOT_API_BASE_URL` (kredensial ketiga, instance lokal, mustahil disediakan CI cloud) karena lupa mock `panggil_meta_chatbot_api()` — gap maintenance dari revisit M4.2 yang cuma menyentuh helper `_patch_raw()` di file saudaranya (`test_klasifikasi_respons.py`), bukan duplikatnya di file ini. Diperbaiki: tambah `_patch_meta_tidak_diketahui()` (mirror persis), dipanggil di satu-satunya test yang genuinely mencapai `BERHASIL`.

**Hasil Verifikasi**
Lokal: `pytest tests/layers/execution/test_klasifikasi_respons_revisi.py` → 5/5 passed. `ruff check`+`format --check` → bersih. Full suite meniru kondisi CI persis (`OPENROUTER_API_KEY=""`+`CHATBOT_API_BASE_URL=""`+`DATABASE_URL` asli) → **670 passed, 35 skipped, 18.53s, 0 gagal**.

**Commit:** `9338677` — `fix(milestone-8.2): mock panggil_meta_chatbot_api di test revisi 400`

**Run kedua (`32558994822`, konklusi `success`):** `changes`✓, `go-test`✓, `test-python-fast`✓ (genuinely lolos setelah fix), `gitleaks`✓, `golangci-lint`✓, `ruff`✓, `dependency-scan`✓, `test-python-llm` SKIP bersih (union kosong, 0 detik), **`test-gate`✓** — MEMBUKTIKAN NYATA `test-python-llm` yang skip TIDAK menggagalkan gate (Keputusan 8 tervalidasi end-to-end untuk kasus "tidak ada grup relevan berubah").

---

## Checkpoint 8 — Update Branch Protection

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 8 — Tambah 3 required status check baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
User mengonfirmasi izin (`AskUserQuestion`). `gh api repos/Ardiyanto24/nirwana-chatbot/branches/main/protection -X PUT` — `required_status_checks.checks` diperluas dari 4 (M8.1) jadi 7 context: `+go-test`, `+test-python-fast`, `+test-gate` (BUKAN `test-python-llm`, sesuai Keputusan 8 — job itu genuinely SKIP by design saat tidak relevan).

**Hasil Verifikasi**
Re-fetch `--jq '.required_status_checks.contexts'` → 7 context terkonfirmasi persis seperti yang di-set.

**Commit:** `0498e33` — `chore(milestone-8.2): tambah 3 required status check baru`

---

## Checkpoint 9 — PR Percobaan #1: `test-python-fast`

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 9 — Buat branch percobaan + buka PR

**Kesesuaian dengan plan:** Sesuai plan, dengan 2 kesalahan ditemukan+diperbaiki mid-checkpoint.

**Apa yang dilakukan**
Branch `test/m8-2-fast-gate-percobaan`, file baru berisi 1 assertion sengaja gagal (`assert 1 == 2`), murni deterministik di luar 5 grup path-filter.

**Kesalahan 1 (ditemukan sebelum push kedua):** Nama file awal `_ci_gate_percobaan_m8_2_fast.py` (awalan underscore) TIDAK terdeteksi konvensi discovery pytest (`test_*.py`/`*_test.py`) — run CI pertama (`32559342176`) menunjukkan `test-python-fast`✓ LOLOS (SALAH, seharusnya gagal) karena test-nya genuinely tidak pernah dikoleksi (`705 tests collected`, sama seperti sebelum file ditambahkan, dikonfirmasi lokal). Diperbaiki: `git mv` ke `test_ci_gate_percobaan_m8_2_fast.py`, diverifikasi lokal (`1 failed`) sebelum push ulang.

**Kesalahan 2 (ditemukan saat commit fix):** `git add -A` (bukan menambahkan file spesifik) ikut men-stage+commit 2 perubahan pra-existing yang TIDAK terkait (`docs/CLAUDE.md` terhapus, `docs/02-implementation-plan/rancangan-ci-cd.md` untracked) — pelanggaran langsung praktik "review apa yang di-`git add`" yang seharusnya diikuti. Diperbaiki SEBELUM push: `git checkout HEAD~1 -- docs/CLAUDE.md` (kembalikan ke index+worktree dari commit sebelum insiden) + `git rm --cached rancangan-ci-cd.md` (untrack, file tetap di disk) + `git commit --amend` + `rm docs/CLAUDE.md` (hapus lagi dari worktree saja, replikasi persis state "unstaged deletion" semula) — diverifikasi `git status --short` menunjukkan tepat 1 file berubah (rename) sebelum `force-with-lease` push ke branch percobaan (aman, BUKAN `main`).

User mengonfirmasi izin (`AskUserQuestion`, sekaligus Checkpoint 10) sebelum push+PR pertama kali dibuka.

### Task 10 — Amati hasil CI nyata, tutup PR

**Hasil Verifikasi**
Run CI nyata setelah fix (`32559487377`): **`test-python-fast` GAGAL**, `test-python-llm` tetap SKIP (union kosong, benar tidak relevan), **`test-gate` GAGAL** dengan pesan eksplisit `"X test-python-fast tidak lolos (failure)"` — KK2 sumber M8.2 (tier fast) TERPENUHI PENUH.

`gh pr close 2 --delete-branch` — PR ditutup TANPA merge, branch dihapus. `git status -sb` setelah kembali ke `main` dikonfirmasi PERSIS sama seperti sebelum checkpoint ini (`docs/CLAUDE.md`/`rancangan-ci-cd.md` tidak berubah) — insiden `git add -A` tidak meninggalkan jejak di `main`.

**Commit:** Branch percobaan `fe5b3d1` (setelah amend) tidak pernah masuk `main` (dihapus). Log ini menyusul commit dokumentasi berikut.

---
