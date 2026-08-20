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

**Commit:** *(diisi setelah commit checkpoint ini)*

---
