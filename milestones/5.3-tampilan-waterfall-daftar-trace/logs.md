# Logs — Milestone 5.3: Membangun Tampilan Waterfall Trace dan Daftar Turn

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset 2-jalur paralel (2 agent Explore) mencakup: isi lengkap `docs/02-implementation-plan/rancangan-observability-dashboard.md` (fokus M5.3), state nyata kode M5.2 (`trace-tree.ts`, `traces.ts`, seluruh struktur `dashboard/src/`), dan repo tetangga `nirwana-database/web/` (konvensi Next.js). Satu agent Plan mendesain mekanisme konkret (rendering waterfall tanpa library chart, `listTraces()` filter SQL-side, breakdown checkpoint) — dikonfirmasi baca langsung dokumentasi resmi Next.js (`dashboard/node_modules/next/dist/docs/`) dan `postgres/README.md` untuk pola `searchParams`/fragment SQL dinamis. Tidak ada pertanyaan `AskUserQuestion` — seluruh keputusan derivable dari precedent/penalaran teknis. Plan ditulis dan disetujui (`ExitPlanMode`). Setelah plan disetujui, `milestones/5.3-tampilan-waterfall-daftar-trace/decisions.md` ditulis berisi 10 entri keputusan (seluruhnya Jenis B).

**Temuan**
- Data sample M5.2 (`sample-6d7f5cea8dfd`) tidak cukup untuk membuktikan KK1 (butuh multi-wave) maupun KK2 (butuh span gagal) — perlu data sample baru sebelum verifikasi UI bisa dilakukan (Checkpoint 2).
- Atribut span wave (`wave.index`/`wave.intent_count`) dikonfirmasi persis dari `src/orchestration/turn_pipeline.py:234-237`.
- Precedent zero-chart-dependency dikonfirmasi ganda (`dashboard/` dan `nirwana-database/web/` sama-sama nol dependency chart) — mengonfirmasi waterfall bisa dibangun plain CSS/Tailwind tanpa dependency baru.
- Pelajaran insiden akses `localhost:3000` sesi sebelumnya (M5.2 lanjutan) dijadikan Keputusan 10 — verifikasi UI wajib lewat tool Browser, bukan `curl`.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` lengkap dengan 10 entri, setiap entri py "Opsi yang Dipertimbangkan tapi Ditolak" terisi, Daftar Isi Keputusan mencantumkan seluruh 10 entri dengan Checkpoint Terkait.

**Commit:** `68b4773` — `docs(milestone-5.3): keputusan desain waterfall dan daftar trace`

---

## Checkpoint 2 — Data Sample Tambahan (KK1 Multi-Wave + KK2 Span Gagal)

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 2 — Tulis seed_kk_scenarios.py

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `seed_kk_scenarios.py` (mirror `seed_sample_trace.py`, helper `_build_trace()` bersama untuk dua skenario) — trace multi-wave (29 span, root `invoke_agent` + pipeline standar + DUA span `orchestration.wave` sibling `wave.index=1`/`2` masing-masing dengan child `verification_gate`+`execution` sendiri, seluruh `error_type=null`, `status="berhasil"`) dan trace gagal (27 span, 2× `authorization.check` dengan `rbac.domain="financial"`/`rbac.decision="deny"`/`error_type="ditolak_otorisasi"` mirror skenario nyata `gop_margin` M5.1, 1× `execution.eksekusi_atomic_intent_semua` dengan `error_type="gagal_teknis"` mirror jalur revisi-400-exhausted M7.14, `status="sebagian"`). Atribut span (`wave.index`/`wave.intent_count`, `rbac.domain`/`rbac.decision`, `error.type`) dikonfirmasi persis dari `src/orchestration/turn_pipeline.py:234-237` dan `src/layers/domain_gate/otorisasi.py:49-56` sebelum ditulis.

**Temuan**
Tidak ada temuan tak terduga pada desain data itu sendiri (lihat Task 3 untuk bug eksekusi).

**Error/Kegagalan (jika ada)**
Tidak ada pada task ini.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Ditunda ke Task 3 (verifikasi query nyata setelah script dijalankan).

**Commit:** `7825277` — `feat(milestone-5.3): seed data sample multi-wave dan span gagal` (digabung Task 3)

---

### Task 3 — Jalankan script + verifikasi query nyata

**Kesesuaian dengan plan:** Sesuai plan, dengan satu bug kecil ditemukan+diperbaiki (lihat Error/Kegagalan) — tidak mengubah data yang sudah tersimpan.

**Apa yang dilakukan**
Jalankan `seed_kk_scenarios.py`. Verifikasi via query Python langsung ke Supabase: jumlah span per trace, span `orchestration.wave` (parent+`wave.index`), span dengan `error_type` terisi.

**Temuan**
Tidak ada temuan baru di luar bug eksekusi di bawah.

**Error/Kegagalan (jika ada)**
```
sqlalchemy.orm.exc.DetachedInstanceError: Instance <TraceRow ...> is not bound to a Session; attribute refresh operation cannot proceed
```
Terjadi di `print()` SETELAH kedua commit (trace, lalu span) sudah sukses — mengakses `mw_trace.trace_id` di luar blok `with Session(...)` memicu SQLAlchemy mencoba refresh atribut dari session yang sudah ditutup (`expire_on_commit` default `True`).

**Diagnosis dan Perbaikan (jika ada error)**
Diagnosis: dikonfirmasi data SUDAH tersimpan benar (bug murni di baris print, bukan di transaksi DB) — query langsung ke `TraceRow` sesudahnya menunjukkan kedua trace baru ada dengan `session_id` yang benar. Perbaikan: capture `trace_id` ke variabel lokal SEBELUM masuk blok `with Session(...)` (aman karena `trace_id` diset eksplisit di kode, bukan auto-generated oleh DB) — tidak perlu re-run script, data existing tetap dipakai.

**Hasil Verifikasi**
- `sample-mw-e2a07d4512`: 29 span, 2 span `orchestration.wave` (`wave1`/`wave2`) SAMA-SAMA anak langsung `...-root` dengan `wave.index=1`/`2` — struktur sibling benar (KK1). 0 span `error_type` terisi.
- `sample-fail-37d0b3fd05`: 27 span, 3 span `error_type` terisi — 2× `ditolak_otorisasi` (`rbac.domain="financial"`) + 1× `gagal_teknis` — persis desain (KK2).
- Trace M5.2 (`sample-6d7f5cea8dfd`) tetap utuh, tidak tersentuh (dikonfirmasi tetap muncul di listing `TraceRow`).

**Commit:** `0486966` — `docs(milestone-5.3): logs checkpoint 2`

---
