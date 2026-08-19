# Logs — Milestone 7.12: Sambungan 7 (Retriever → Query Engine)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (Plan Mode) menemukan bahwa Query Engine (M3.4-3.5) sudah tersambung internal penuh sejak M7.4 dan tidak py gap tersembunyi seperti M7.11 (M2.2/M2.3) — tapi layer-nya sama sekali tidak py fungsi batch level-list untuk gabungan Langkah 1+2 (`susun_dan_verifikasi_request_atomic_intent()` M7.4 cuma per-item). Satu keputusan genuinely terbuka diajukan ke user lewat `AskUserQuestion`: bentuk field `KeadaanTurn.query_engine` — pertahankan tuple `list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` apa adanya (dikonfirmasi user, setelah dijelaskan tidak ada blocker teknis) vs bungkus skema baru bernama. Menulis `milestones/7.12-sambungan-query-engine/decisions.md` — 9 keputusan (1 Jenis A dari `AskUserQuestion`, 8 Jenis B forced by kontrak/preseden, termasuk preseden SAMA-FOLDER `verifikasi_bentuk_request_semua()` yang memperkuat pola batch-wrapper M7.11).

**Temuan**
Ditemukan perbedaan prinsip penting dari M7.11: item Retriever dengan `view_name_final=None` WAJIB di-skip (forced by signature `view_name: str` non-Optional `susun_request_atomic_intent()`), BEDA dari M7.11 Keputusan 7 (Retriever sengaja tidak memfilter karena callee-nya terbukti aman menerima input kosong). Dicatat eksplisit sebagai Keputusan 4 supaya tidak disamakan keliru dengan preseden M7.11.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap dengan 9 entri + Daftar Isi Keputusan, format Jenis A/B sesuai template resmi.

**Commit:** `d046162` — `docs(milestone-7.12): keputusan sambungan query engine`

---

## Checkpoint 2 — Bangun `susun_dan_verifikasi_request_semua()` Baru

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 2-3 — Fungsi batch baru + unit test standalone

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `src/layers/query_engine/query_engine.py` lengkap + `tests/layers/query_engine/test_query_engine.py` untuk memahami konvensi mock (`monkeypatch.setattr(query_engine_module, ...)`, `unittest.mock.patch` untuk test LLM nyata) dan pola tracer (`_TRACER_NAME` per-module `"query_engine.<nama_module>"`). Dicek `verifikasi_bentuk_request_semua()` (existing) untuk pola span pembungkus — ditemukan atribut span-nya `"verifikasi_bentuk_request.intent_count"` (bukan `"intent.count"` polos seperti 4 fungsi `_semua()` era orkestrasi M7.x) — tetap dipakai `"intent.count"` sesuai `decisions.md` Keputusan 8 (mengikuti garis keturunan preseden M7.x, bukan fungsi lama pra-orkestrasi), dicatat sebagai observasi bukan diikuti.

Tambah `_TRACER_NAME = "query_engine.query_engine"` + fungsi `susun_dan_verifikasi_request_semua(daftar_retriever: list[HasilKecukupanStruktural]) -> list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` di `query_engine.py` — filter `view_name_final is not None`, panggil `susun_dan_verifikasi_request_atomic_intent(item.atomic_intent, item.view_name_final)` per item, span pembungkus `query_engine.susun_dan_verifikasi_request_semua` dengan `intent.count`.

Tulis 4 unit test baru: (1) dipanggil dengan `atomic_intent`+`view_name_final` benar; (2) item `view_name_final=None` di-skip (assert TIDAK terpanggil); (3) urutan+panjang dipertahankan pada campuran; (4) list kosong -> hasil kosong.

**Temuan**
Test pertama gagal: `HasilKecukupanStruktural` py `model_validator` yang mensyaratkan `view_name_final` (kalau terisi) HARUS berkorespondensi dengan salah satu `KecukupanKandidat` di `kecukupan` dengan `cukup=True` — helper fixture awal `_buat_hasil_kecukupan()` memakai `kecukupan=[]` kosong terlepas nilai `view_name_final`, melanggar validator ini (tidak diketahui dari riset plan, ketahuan baru saat run test pertama).

**Error/Kegagalan (jika ada)**
`pydantic_core._pydantic_core.ValidationError: view_name_final wajib salah satu kandidat berlabel cukup=True di kecukupan - tidak boleh memilih view yang tidak pernah dinyatakan cukup` — 2 dari 4 test baru gagal (yang memakai `view_name_final` terisi).

**Diagnosis dan Perbaikan (jika ada error)**
Diperbaiki: helper `_buat_hasil_kecukupan()` direvisi membangun `KecukupanKandidat` valid (via `KandidatView`, `cukup=True`) saat `view_name_final` terisi, `kecukupan=[]` tetap dipakai HANYA saat `view_name_final=None`. Tidak menyentuh kode produksi (`query_engine.py`) — murni perbaikan fixture test.

**Hasil Verifikasi**
`uv run pytest tests/layers/query_engine/ -v -k "not konektivitas"` — 74/74 test PASSED (70 existing + 4 baru, 1 test LLM nyata existing sengaja di-deselect), regresi nol.

**Commit:** `ffbff2a` (feat) + `4042cde` (test)

---

## Checkpoint 3 — Sambungan Query Engine: Implementasi

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 4-5 — Extend `KeadaanTurn` + wiring `susun_dan_verifikasi_request_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah field `query_engine: list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` di `KeadaanTurn` (field TERAKHIR, melengkapi 11 field total) — import `HasilPenyusunanRequest`/`HasilVerifikasiBentukRequest` dari `src.schemas.query_engine`. Di `turn_pipeline.py`: import `susun_dan_verifikasi_request_semua`, panggil sekuensial setelah `retriever_result` final, isi field `query_engine`. Ini SECARA RESMI Sambungan 7 (Retriever -> Query Engine) yang jadi judul asli M7.12.

**Temuan**
Tidak ada — pola identik Checkpoint 3/7 M7.11, disiplin satu-field-per-checkpoint dipertahankan.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run python -c "..."` mengonfirmasi `'query_engine' in KeadaanTurn.model_fields` -> `True`, urutan 11 field sesuai rencana, `susun_dan_verifikasi_request_semua` tersedia di `turn_pipeline` module.

**Commit:** `73a7190` — `feat(milestone-7.12): sambungkan query engine ke proses_turn`

---

## Checkpoint 4 — Sambungan Query Engine: Test Deterministik

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 6-7 — Extend test existing + test connectivity baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah konstanta `_QUERY_ENGINE_DUMMY = []`. Extend 11 dari 12 test existing dengan mock `susun_dan_verifikasi_request_semua` (kegagalan cabang paralel tetap tidak berubah, exception menjalar sebelum titik ini — pola identik 3 checkpoint sebelumnya). Tulis test baru `test_orkestrator_query_engine_menerima_retriever_result_persis` — spy merekam `retriever_result` (identity check terhadap `HasilKecukupanStruktural` buatan tangan), menutup rantai 4 test connectivity M7.11-7.12 (Otorisasi, Cakupan Individu, Retriever, Query Engine) yang masing-masing membuktikan SATU sambungan spesifik dalam rantai penuh Domain Gate -> Retriever -> Query Engine. Tambah import `HasilKecukupanStruktural` dari `src.schemas.retriever`.

**Temuan**
Total test file kini 12 test (dari 11 sebelum M7.12 dimulai) — pola mock berlapis (tiap checkpoint sambungan menambah satu `monkeypatch.setattr` baru ke SEMUA test existing) tetap scalable meski file terus bertambah, konsisten observasi M7.11 Checkpoint 8.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_turn_pipeline.py -v` — 12/12 test PASSED (11 existing + 1 baru), 6.30s, tanpa panggilan LLM/DB nyata.

**Commit:** `0bac42a` — `test(milestone-7.12): test deterministik sambungan query engine`

---

## Checkpoint 5 — Peta Kejadian

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 8 — Tulis `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `evals/7.11-sambungan-retriever/rancangan.md` lengkap untuk mirror struktur+gaya persis. Reuse 3 skenario yang SUDAH terbukti bekerja di M7.11 (E01 gop_margin/Front Office Staff, E03 F&B Staff/domain kosong, E04 HR Staff), teks pertanyaan IDENTIK tapi `session_id` BARU (`eval-7.12-eXX`) per preseden Keputusan 6 M7.10. Tulis `evals/7.12-sambungan-query-engine/rancangan.md` — 3 kejadian, ekspektasi ditulis sebagai INVARIAN MEKANISME (verifikasi `request.view_name` dibandingkan terhadap `view_name_final` HASIL RUN ITU SENDIRI, bukan nilai literal hardcoded dari payload M7.11) mengikuti pelajaran metodologi `audit.md` M7.10/M7.11.

**Temuan**
Tidak ada temuan baru — murni penulisan dokumen berdasar riset plan yang sudah lengkap.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review manual `rancangan.md` — 3 kejadian, tiap kejadian py ekspektasi konkret + rujukan eksplisit ke hasil nyata M7.11 sebagai referensi (bukan jaminan), section "Catatan Non-Determinisme" eksplisit menjelaskan metodologi perbandingan run-terhadap-dirinya-sendiri.

**Commit:** *(dicatat di commit berikutnya)*

---
