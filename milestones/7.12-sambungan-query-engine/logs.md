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

**Commit:** `8edf468` — `docs(milestone-7.12): peta kejadian eval`

---

## Checkpoint 6 — Eksekusi Nyata

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 9-10 — `run_eval.py` + eksekusi + verifikasi Jaeger

**Kesesuaian dengan plan:** Sesuai plan, dengan satu insiden operasional (hang, ditemukan+diatasi — lihat Error/Kegagalan).

**Apa yang dilakukan**
Sebelum menulis `run_eval.py`: konfirmasi span "chat" M3.4 (`penyusunan_request.py`)/M3.5 (`verifikasi_bentuk_request.py`) sama-sama merekam tag `request.domain`/`request.view_name` (konstanta `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME`, `src/observability/genai_semconv.py`) — dipakai sebagai bukti pendukung Jaeger, verifikasi UTAMA tetap inspeksi langsung return value Python (`hasil.query_engine[i][*].request.view_name` vs `hasil.retriever[i].view_name_final`, dicocokkan per `atomic_intent_id`, konsisten pendekatan M7.11).

Tulis `evals/7.12-sambungan-query-engine/run_eval.py` — helper `_verifikasi_view_name_konsisten()` dan `_ringkas_span()`. Docker (Jaeger+Collector+Prometheus) dikonfirmasi SUDAH `up` dari sesi M7.11 (`docker ps`), tidak perlu `docker compose up -d` ulang.

**Temuan**
Seluruh 3 kejadian (run kedua, setelah retry) `view_name_persis_sama=True` untuk item yang diteruskan, `skip_benar=True` untuk item `view_name_final=None` (E02). E01 kali ini menghasilkan 3 atomic intent yang KETIGANYA `view_name_final=v_reservation_gop_impact_monthly` (berbeda komposisi dari run M7.11 sebelumnya yang cuma 1 dari 3 intent memakai view ini) — non-determinisme Decomposition dikenal, dicatat di `audit.md`, tidak memengaruhi verdict (justru 3 bukti independen sekaligus).

**Error/Kegagalan (jika ada)**
**Percobaan PERTAMA (`run_eval.py` dijalankan via background task) HANG** — terdeteksi lewat laporan user langsung ("saya melihat di dashboard openrouter request terakhir masuk 11 menit yang lalu") saat proses masih "running" tanpa output. Diverifikasi via query Jaeger API langsung terhadap trace E01 yang sedang berjalan: span LLM ("chat") ke-7 selesai, TAPI gap sampai saat pengecekan mencapai **~1481 detik (~24.7 menit)** — jauh melewati batas aman `timeout=90.0, max_retries=1` (~180 detik terburuk) yang sudah dikonfigurasi `get_openrouter_client()` justru untuk mencegah kasus ini (`docs/keterbatasan-diterima.md` #7, "Panggilan LLM... Kadang Hang Berkepanjangan Tanpa Exception").

**Diagnosis dan Perbaikan (jika ada error)**
Bukan bug kode M7.12 — konsisten kategori masalah infrastruktur/provider yang SUDAH terdokumentasi `docs/keterbatasan-diterima.md` #7, sebelumnya diterima sebagai keterbatasan (bukan diperbaiki) karena root cause tidak bisa diisolasi pasti. Ditangani dengan proses stop paksa (`TaskStop`) atas proses yang hang, dijalankan ULANG dari awal (tidak ada payload E01 yang sempat tersimpan — `_simpan()` hanya terpanggil setelah `runner()` selesai, jadi tidak ada state parsial yang perlu dibersihkan). Run KEDUA dipantau AKTIF via query Jaeger berkala (bukan menunggu buta sampai selesai) — progres sehat (gap antar-span turun ke puluhan detik), selesai normal ~15 menit kemudian, 3/3 kejadian lolos.

**Catatan untuk `docs/keterbatasan-diterima.md` #7**: entri itu mengklaim mitigasi timeout membatasi "~180s terburuk per panggilan" — insiden hang M7.12 ini (~24.7 menit tanpa progres) MELEBIHI klaim itu jauh, mengindikasikan timeout tidak selalu efektif mencegah hang total (mungkin hang terjadi di titik yang tidak tercakup `timeout` client, mis. saat menunggu koneksi awal terbentuk). Data point baru, TIDAK diupdate ke `keterbatasan-diterima.md` di checkpoint ini (di luar cakupan dokumentasi M7.12 murni) — dicatat di sini untuk visibilitas, layak jadi follow-up.

**Hasil Verifikasi**
Payload lengkap tersimpan `evals/7.12-sambungan-query-engine/payloads/{E01,E02,E03}.json`, dikonfirmasi tanpa secret (`grep` sebelum commit). 3 `trace_id` dicatat, span Jaeger (`query_engine.susun_dan_verifikasi_request_semua` dengan `intent.count`, span `chat` dengan `request.view_name`) dikonfirmasi konsisten dengan hasil Python.

**Commit:** `a847019` — `test(milestone-7.12): eksekusi nyata 3 kejadian`

---

## Checkpoint 7 — Audit

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 11 — Tulis `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `evals/7.12-sambungan-query-engine/audit.md` — tabel ringkasan verdict per kejadian, analisis dengan `trace_id`+rincian tiap atomic intent, section "Temuan Metodologi" mencatat transparan non-determinisme Decomposition E01 DAN insiden hang eksekusi (ringkasan, rujuk `logs.md` untuk kronologi lengkap) sebagai temuan operasional yang melampaui klaim mitigasi `docs/keterbatasan-diterima.md` #7.

**Temuan**
Tidak ada temuan baru di luar yang sudah dicatat Checkpoint 6 — `audit.md` murni menyusun+menganalisis hasil yang sudah terkumpul.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review isi `audit.md` mencerminkan `payloads/*.json` apa adanya — tidak ada klaim yang tidak didukung data aktual.

**Commit:** *(dicatat di commit berikutnya)*

---
