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

**Commit:** (menyusul)

---
