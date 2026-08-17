# Logs — Milestone 3.5: Verifikasi Bentuk Request

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.5-verifikasi-bentuk-request/decisions.md`: 13 keputusan, SELURUHNYA Jenis B (forced/turunan) — dinyatakan eksplisit tidak ada Jenis A, konsisten anjuran template plan untuk kasus ini. Mencakup: mekanisme hybrid pre-check+LLM (Keputusan 1-4), model verifier DeepSeek V4 Pro (Keputusan 5), larangan retry balik ke M3.4 (Keputusan 6), `request` output selalu utuh (Keputusan 7), signature flat-args (Keputusan 8), skema gabungan status+lolos+alasan (Keputusan 9), lokasi file skema/implementasi (Keputusan 10-11), observability reuse atribut M3.4 (Keputusan 12), orkestrator batch (Keputusan 13).

**Temuan**
Tidak ada temuan baru di luar yang sudah tercatat di plan (Context "Temuan Penting").

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh 13 butir "Keputusan Desain Turunan" di plan punya entri `decisions.md` dengan "Opsi yang Dipertimbangkan tapi Ditolak".

**Commit:** `c1d9bc4` — `docs(milestone-3.5): decisions.md keputusan awal`

---

## Checkpoint 2 — Skema `HasilVerifikasiBentukRequest`

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 2 — Tambahkan `HasilVerifikasiBentukRequest`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan kelas `HasilVerifikasiBentukRequest` ke `src/schemas/query_engine.py` (file M3.4 yang sudah ada) — field `atomic_intent`, `request: QueryEngineRequest` (non-optional), `status: StatusEksekusi`, `lolos: bool | None`, `alasan: str | None`. Validator `status_lolos_alasan_konsisten()` menegakkan aturan tiga-arah persis sesuai `decisions.md` Keputusan 9.

### Task 3 — Test Matriks Validator

**Apa yang dilakukan**
Menambahkan 10 test ke `tests/layers/query_engine/test_query_engine_schema.py` (file sudah ada): 3 kombinasi valid (gagal_teknis+lolos=None+alasan=None; berhasil+lolos=True+alasan=None; berhasil+lolos=False+alasan terisi), 6 kombinasi invalid (gagal_teknis+lolos terisi; gagal_teknis+alasan terisi; berhasil+lolos=None; lolos=True+alasan terisi; lolos=False+alasan=None; request=None), 1 parametrized test status lain (sebagian/ditolak_otorisasi/terblokir_ketergantungan, 3 kasus).

**Temuan** Tidak ada temuan baru. **Error/Kegagalan** Tidak ada — seluruh 19 test (9 lama M3.4 + 10 baru M3.5) lolos di percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/query_engine/test_query_engine_schema.py -v` → **19 passed** (9 test M3.4 tidak terdampak, regresi nol; 10 test baru M3.5 seluruhnya hijau).

**Commit:** `6cacc07` (skema) + `b91c268` (test)

---
