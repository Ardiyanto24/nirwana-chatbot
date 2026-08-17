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

## Checkpoint 3 — Prompt + Config Plumbing

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — Konstanta Model

**Apa yang dilakukan**
`OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST = "deepseek/deepseek-v4-pro"` ditambahkan ke `src/config/llm.py` + entri docstring.

### Task 5 — Prompt `verifikasi_bentuk_request.md`

**Apa yang dilakukan**
`src/prompts/query_engine/verifikasi_bentuk_request.md` (baru, `id: query_engine.verifikasi_bentuk_request`, v1) — instruksi eksplisit MENOLAK menilai ulang `view_name` (sudah dipastikan pre-check), fokus HANYA kecukupan `params` terhadap `label_bentuk_jawaban`. Panduan kecukupan per LIMA label (`nilai_tunggal`/`tren`/`perbandingan`/`peringkat`/`komposisi`) ditulis eksplisit satu per satu, grounded pada grain view yang diberikan sebagai konteks. Format keluaran `{"lolos": bool, "alasan": str|null}`.

**Temuan** Tidak ada temuan baru. **Error/Kegagalan** Tidak ada.

**Hasil Verifikasi**
`load_prompt("query_engine.verifikasi_bentuk_request")` sukses, `id=query_engine.verifikasi_bentuk_request`, `version=1`. `.render()` smoke test tanpa variabel Jinja2 tambahan (prompt ini tidak butuh `render_context`, beda dari `kecocokan_makna_*` yang butuh `catatan_lintas_domain`) — sukses, panjang render 3095 karakter.

**Commit:** `184c92d` (konstanta) + `85528df` (prompt)

---

## Checkpoint 4 — Pre-Check + LLM Call + Orkestrator

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6-8 — Implementasi `verifikasi_bentuk_request.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/layers/query_engine/verifikasi_bentuk_request.py` (baru): `_view_name_sesuai_retriever()` (pre-check Kriteria 1, string equality); `_call_llm()`+`_parse_response()` (Kriteria 2, DeepSeek V4 Pro `reasoning="high"`, parse `{"lolos": bool, "alasan": str|null}`, fallback alasan generik kalau LLM lupa mengisi saat `lolos=false`); `verifikasi_bentuk_request_atomic_intent()` (orkestrator single-item — pre-check dulu, short-circuit tanpa span `chat` kalau gagal, baru buka span+panggil LLM kalau lolos); `verifikasi_bentuk_request_semua()` (orkestrator batch, span pembungkus `query_engine.verifikasi_bentuk_request_semua`, statistik agregat `lolos_count`/`perlu_revisi_count`/`gagal_teknis_count`).

### Task 9 — Unit Test

**Apa yang dilakukan**
`tests/layers/query_engine/test_verifikasi_bentuk_request.py` (baru, 16 test): pure function (`_view_name_sesuai_retriever`, `_build_user_prompt`, `_parse_response` — 5 test termasuk fallback alasan); orkestrator mocked LLM (pre-check gagal dengan `_call_llm` di-monkeypatch untuk `raise AssertionError` kalau terpanggil — MEMBUKTIKAN LLM benar-benar tidak dipanggil, mirror pola pembuktian pre-filter M2.3; pre-check lolos + lolos=True; pre-check lolos + lolos=False+alasan; API error/empty choices/JSON rusak → GAGAL_TEKNIS); `verifikasi_bentuk_request_semua()` statistik agregat untuk campuran 3 item (1 lolos, 1 perlu_revisi dari LLM, 1 perlu_revisi dari pre-check) — dibuktikan `_call_llm` cuma terpanggil 2x (item ke-3 short-circuit).

**Temuan** Tidak ada temuan baru — desain sesuai plan tanpa penyesuaian. **Error/Kegagalan** Tidak ada — seluruh 16 test M3.5 lolos di percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/query_engine/ -v` → **62 passed** (46 test M3.1-3.4 tanpa regresi + 16 test baru M3.5), nol network call nyata.

**Commit:** `e47f92d` (implementasi) + `21d2fa2` (test)

---

## Checkpoint 5 — Eval Nyata

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 10-12 — Rancangan, Eksekusi, Audit

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`evals/3.5-verifikasi-bentuk-request/rancangan.md` — 5 skenario (S01 kepatuhan sumber KK1, S02 tren rentang sempit KK2, S03-S04 kontrol positif, S05 replikasi PERSIS payload `evals/3.4-penyusunan-request/payloads/S04.json`). `run_eval.py` dijalankan nyata ke OpenRouter (DeepSeek V4 Pro `reasoning="high"`) — **5/5 skenario lolos di run pertama**, tanpa perlu iterasi prompt.

**Temuan**
Tiga temuan didokumentasikan `audit.md`: (1) S01 `alasan` PERSIS string deterministik pre-check, bukti langsung LLM tidak dilibatkan; (2) S05 menangkap masalah LEBIH DALAM dari ekspektasi (grain-mismatch: params tanpa filter `room_type` akan menghasilkan banyak baris, bukan sekadar mengomentari nilai `occupancy_rate` aneh) — bukti penalaran genuinely grain-vs-label, bukan pattern-matching; (3) ketidakkonsistenan nyata S04 vs S05 (gap struktural serupa - tanpa filter `room_type` - tapi verdict berbeda, `lolos=true` vs `lolos=false`) — dicatat transparan sebagai observasi, BUKAN memicu revisi prompt (baru 1 titik data, dampak rendah, tidak melanggar KK sumber manapun).

**Error/Kegagalan**
Tidak ada — seluruh 5 panggilan LLM sukses di percobaan pertama, tanpa API error/timeout.

**Hasil Verifikasi**
Payload lengkap tersimpan `evals/3.5-verifikasi-bentuk-request/payloads/S01.json` s.d. `S05.json`, dibaca ulang manual untuk memverifikasi kualitas `alasan` (bukan cuma cek boolean `lolos`).

**Commit:** `941c069`

---
