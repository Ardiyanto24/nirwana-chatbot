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

## Checkpoint 6 — Reliability Testing Promptfoo (Native)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 13-14 — Config + Eksekusi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`prompt_reliability/query_engine/verifikasi_bentuk_request.promptfooconfig.yaml` — 4 skenario native (S02-S05, `user_prompt` diambil PERSIS dari `_build_user_prompt()` nyata via skrip verifikasi sekali-pakai, dihapus setelah dipakai). S01 (pre-check gagal) SENGAJA TIDAK disertakan — tidak menyentuh prompt/LLM sama sekali, konsisten catatan Task 13 plan. Dijalankan `npx promptfoo eval` (Node.js, `PROMPTFOO_PYTHON` diarahkan ke `.venv/`) — **4/4 lolos di run pertama (100%)**, tanpa perlu revisi prompt (prompt tetap v1).

**Temuan**
Tidak ada temuan tooling baru (assertion JS ditulis langsung pakai `return` eksplisit sejak awal, belajar dari bug M3.3 Checkpoint 14/7). Hasil Promptfoo mengonfirmasi ULANG temuan eval Checkpoint 5 (S05 reasoning grain-mismatch, bukan sekadar nilai aneh) via jalur independen kedua — replikasi silang yang konsisten.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`push_results.py` → **`Berhasil push 4 baris ke prompt_eval_runs`** (Supabase), diverifikasi lewat output skrip langsung.

**Commit:** `1ffb45d`

---

## Checkpoint 7 — Verifikasi Jaeger Nyata

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 15 — Jalankan Nyata + Verifikasi Trace

**Kesesuaian dengan plan:** Sesuai plan (termasuk verifikasi opsional pre-check).

**Apa yang dilakukan**
Docker Desktop dinyalakan, `infra/observability` (Collector+Jaeger+Prometheus) dijalankan. Skrip verifikasi (`scratchpad/verify_m35_span.py`, tidak di-commit, mirror pola M3.1/M3.3/M3.4) menjalankan `verifikasi_bentuk_request_atomic_intent()` NYATA (Collector lokal aktif) untuk DUA skenario: (1) request valid `v_reservation_room_type_daily` (lolos pre-check, memanggil LLM); (2) request dengan `view_name` sengaja tidak sesuai `view_name_tervalidasi_retriever` (gagal pre-check, TIDAK memanggil LLM). Trace diambil langsung dari Jaeger HTTP API.

**Temuan**
Trace skenario (1) `b75702b73540855d7e5e18df835870e7`: span `"chat"` membawa SELURUH atribut wajib — `gen_ai.operation.name=chat`, `gen_ai.request.model=deepseek/deepseek-v4-pro`, `gen_ai.usage.input_tokens=1445`, `prompt.id=query_engine.verifikasi_bentuk_request`, `prompt.version=1`, `request.domain=reservation`, `request.view_name=v_reservation_room_type_daily`, plus atribut custom `query_engine.verifikasi_bentuk_request.lolos=True`. **Trace skenario (2) `723e581591cb1284143a6c65afc20037`: HANYA berisi span `invoke_agent` (pembungkus skrip verifikasi) — TIDAK ADA span `"chat"` sama sekali** — bukti langsung dan konkret bahwa jalur pintas pre-check (`decisions.md` Keputusan 3) benar-benar aktif: LLM tidak pernah dipanggil, span `chat` tidak pernah dibuka, persis sesuai desain.

**Error/Kegagalan**
Tidak ada. Catatan operasional: Docker Desktop tidak otomatis berjalan di awal sesi, perlu dinyalakan manual (`Start-Process`) + tunggu daemon siap (~10 detik) sebelum `docker compose up -d` bisa jalan — bukan kegagalan proyek, murni state environment lokal.

**Hasil Verifikasi**
`curl http://localhost:16686/api/traces?service=nirwana-chatbot-m35-verify` — dua trace_id di atas, atribut DAN keberadaan/ketiadaan span `chat` dicek programatik (Python, bukan baca visual manual).

**Commit:** *(skrip verifikasi murni operasional di scratchpad, tidak di-commit — konsisten preseden M3.1/M3.3/M3.4)*

---

## Checkpoint 8 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 16 — Finalisasi `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`decisions.md` sudah memuat "Daftar Isi Keputusan" penuh (13 keputusan) sejak Checkpoint 1 — dikonfirmasi ulang tidak perlu addendum (prompt TIDAK direvisi sepanjang milestone, tetap v1).

### Task 17 — Tulis `logs.md`

**Apa yang dilakukan**
Dokumen ini sendiri — dibangun bertahap per checkpoint sepanjang milestone berjalan (commit `c1d9bc4`, `d2827fd`, `2b1978e`, `befb9da`, `2a6d424`, `55d6ef8`); entri Checkpoint 8 ini melengkapi bagian penutup.

### Task 18 — Tulis `report.md`

**Apa yang dilakukan**
`milestones/3.5-verifikasi-bentuk-request/report.md` — enam bagian: ringkasan, KK1-2 vs bukti nyata, keputusan final relevan, perubahan dari plan (tidak ada — prompt tidak direvisi), keterbatasan/item provisional (ketidakkonsistenan S04/S05, jalur perbaikan tetap di luar cakupan), diagram arsitektur Mermaid, dan **konfirmasi eksplisit Catatan Serah Terima `rancangan-retrieval-query.md` TERPENUHI PENUH** — PIC 3 (Retriever + Query Engine, M3.1-3.5) SELESAI SEPENUHNYA.

### Task 19 — Perbarui `CLAUDE.md`/`AGENT.md`

**Apa yang dilakukan**
Tabel "Struktur Repository" diperbarui: baris `milestones/` (tambah M3.5), baris `src/` (subpackage `query_engine/verifikasi_bentuk_request.py` + `src/schemas/query_engine.py` diperluas), baris `src/prompts/` (`verifikasi_bentuk_request.md` v1), baris `tests/` (62 test total `tests/layers/query_engine/`), baris `evals/` (`evals/3.5-.../`, 5/5 lolos), baris `prompt_reliability/` (13 config). Section "Status Saat Ini": bullet baru "Milestone 3.5 (Verifikasi Bentuk Request) SELESAI" (mirror pola M3.1-3.4), bullet "Urutan pengerjaan yang disarankan" diperbarui menunjuk Milestone 4.x (Execution & Interpretation) sebagai langkah berikutnya, bullet "Keputusan tertunda" ditambah mention #3 (sebelumnya terlewat di prosa meski sudah ada di tabel struktur repo), bullet "Model per langkah dan provider routing" diperbarui menyebut model M3.4+M3.5 dan mengganti "Milestone 3.4+" jadi "Milestone 4.x". `AGENT.md` disinkronkan persis (`cp` + `diff -q` — identik, nol perbedaan).

**Hasil Verifikasi** `diff -q CLAUDE.md AGENT.md` → tidak ada output (identik).

**Commit:** *(CLAUDE.md/AGENT.md sengaja TIDAK di-track git — diperbarui di working tree saja, dibaca sistem tiap sesi, bukan artefak git)*

---

## Ringkasan Penutupan Milestone 3.5

- **8 checkpoint, 19 task** — seluruhnya selesai dan terverifikasi nyata (bukan simulasi/mock untuk bagian yang sifatnya perilaku LLM).
- **62 unit test** di `tests/layers/query_engine/` (46 M3.4 + 16 M3.5 baru) — seluruhnya hijau, nol network call nyata (mocked LLM), termasuk pembuktian pre-check short-circuit via monkeypatch raise.
- **Eval nyata**: 5 skenario, 5/5 lolos di run pertama — termasuk replikasi PERSIS temuan nyata S04 M3.4 (`occupancy_rate: "nilai_tunggal"`) yang berhasil ditangkap dengan reasoning grain-mismatch lebih dalam dari ekspektasi.
- **Promptfoo**: 4 skenario, 4/4 lolos di run pertama — 4 baris terverifikasi di `prompt_eval_runs` Supabase, prompt TIDAK direvisi (tetap v1).
- **Jaeger**: DUA trace nyata — satu membuktikan span `chat` lengkap (`b75702b73540855d7e5e18df835870e7`), satu membuktikan span `chat` TIDAK ADA SAMA SEKALI saat pre-check short-circuit (`723e581591cb1284143a6c65afc20037`) — bukti konkret arsitektur hybrid bekerja sesuai desain.
- **Satu observasi kualitas** (ketidakkonsistenan verdict S04 vs S05, gap struktural serupa) dicatat transparan, tidak memicu revisi (baru 1 titik data, dampak rendah, tidak melanggar KK sumber manapun).
- **PIC 3 (Retriever + Query Engine, Milestone 3.1-3.5) SELESAI SEPENUHNYA.** Catatan Serah Terima `rancangan-retrieval-query.md` terpenuhi penuh — dikonfirmasi eksplisit di `report.md`. Langkah berikutnya yang disarankan: Milestone 4.x (Execution & Interpretation, PIC 4).
