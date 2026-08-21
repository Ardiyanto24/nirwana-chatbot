# Logs — Milestone 6.2: Membangun Penanganan Kegagalan dan Keandalan Pengiriman

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset teknis mendalam sebelum plan ditulis: baca langsung source `exporterhelper@v0.159.0` dan `configretry@v1.65.0` dari Go module cache lokal (`C:\Users\LENOVO\go\pkg\mod`) — bukan asumsi dari dokumentasi luar. Konfirmasi konkret: `exporterhelper.NewTraces()` M6.1 TIDAK memakai `WithRetry`/`WithQueue` sama sekali (default keduanya adalah DISABLED, dikonfirmasi dari komentar resmi `common.go`/`queue_batch.go`); `configretry.NewDefaultBackOffConfig()` dan `exporterhelper.NewDefaultQueueConfig()` memberi nilai default siap pakai; `base_exporter_test.go`/`queue_sender.go` mengonfirmasi `exporterhelper` SUDAH otomatis logging "Exporting failed. Dropping data." saat retry habis, lewat `zap.Logger` yang sama dengan yang sudah diteruskan ke `Buffer` (addendum M6.1 sebelumnya) — tidak butuh kode tambahan untuk requirement itu.

3 pertanyaan genuinely terbuka diajukan via `AskUserQuestion` (retry/queue config exposure, metodologi fault-injection KK1, TTL eviction Buffer) — SEMUA rekomendasi diterima user. `decisions.md` ditulis dengan 3 Keputusan Jenis A (hasil AskUserQuestion) + 4 Keputusan Jenis B (turunan dari riset: tidak ada SQL batching, NumConsumers default, superuser lokal disposable, logging retry-habis gratis dari exporterhelper).

**Temuan**
`Buffer.Ingest()` (hasil addendum bug-fix M6.1 sebelumnya) sudah dirancang tahan urutan-kedatangan-apa-pun (`written` set + `insertableLocked()` + `drainLocked()` kaskade) — retry/queue yang berpotensi mengirim ulang atau memproses out-of-order TIDAK memperkenalkan risiko korupsi data baru, karena idempoten via `ON CONFLICT` dan tidak pernah mengasumsikan urutan kedatangan tertentu sejak desain itu diperbaiki. Ini menyederhanakan penilaian risiko M6.2 — retry/queue murni "tambahan aman", bukan perubahan yang perlu mendesain ulang Buffer dari nol.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`decisions.md` lengkap sesuai `template-decisions.md` — 7 entri (3 Jenis A + 4 Jenis B), tiap entri Jenis A memuat Opsi yang Dipertimbangkan tapi Ditolak.

**Commit:** *(lihat commit setelah entri log ini)*

---
