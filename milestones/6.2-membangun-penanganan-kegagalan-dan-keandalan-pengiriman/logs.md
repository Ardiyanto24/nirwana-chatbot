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

**Commit:** `f3e26b8` — `docs(milestone-6.2): keputusan desain checkpoint 1`

---

## Checkpoint 2 — Config Retry/Queue + Wiring `exporterhelper`

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 2 — `Config` Diperluas Retry/Queue

**Kesesuaian dengan plan:** Sesuai plan pada substansi (Config diperluas retry+queue), MENYIMPANG pada detail implementasi — plan awal (`decisions.md` Keputusan 1) menyebut "field custom flat per-parameter" (`retry_enabled`, `retry_initial_interval`, dst), realisasinya memakai TIPE RESMI `configretry.BackOffConfig`/`exporterhelper.QueueBatchConfig` langsung sebagai sub-field `Config` (mapstructure `retry_on_failure`/`sending_queue`) — pola idiomatik yang dipakai SELURUH exporter resmi OTel Collector (mis. `otlpexporter`), ditemukan saat implementasi dimulai (bukan diantisipasi di riset plan). Perubahan ini TIDAK mengubah keputusan itu sendiri (tetap "YAML-configurable", tetap tipe/nilai default yang sama) — murni penamaan field yang lebih baik, tidak butuh `AskUserQuestion` ulang.

**Apa yang dilakukan**
`Config` (`factory.go`) diperluas: `RetrySettings configretry.BackOffConfig` (`mapstructure:"retry_on_failure"`), `QueueSettings configoptional.Optional[exporterhelper.QueueBatchConfig]` (`mapstructure:"sending_queue"`), `BufferEvictionTTL time.Duration` (`mapstructure:"buffer_eviction_ttl"`, default 60 menit). `createDefaultConfig()` mengisi `RetrySettings`/`QueueSettings` dari `configretry.NewDefaultBackOffConfig()`/`exporterhelper.NewDefaultQueueConfig()` — confmap otomatis meng-merge override YAML di atas default ini tanpa logic fallback manual. `createTracesExporter()` menerapkan `exporterhelper.WithRetry(c.RetrySettings)`+`exporterhelper.WithQueue(c.QueueSettings)`. `Config.Validate()` ditambah pengecekan `BufferEvictionTTL > 0`.

**Temuan**
`configoptional.Optional[T].Get()` mengembalikan pointer (`*T`) yang bisa dimutasi langsung tanpa perlu method setter khusus — memudahkan pola "ambil default, override field yang perlu" kalau dibutuhkan nanti. `request.SizerType` (dipakai field `Sizer` di `QueueBatchConfig`/`BatchConfig`) adalah tipe dari package `internal/request` — TIDAK bisa dikonstruksi langsung dari luar modul `exporterhelper`, tapi ini TIDAK masalah karena field itu tidak pernah disentuh manual (selalu warisan dari `NewDefaultQueueConfig()`).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`go build ./...` bersih, `gofmt -l .` bersih setelah `gofmt -w`. `docker compose up -d --build otel-collector` (build ke-5 sesi ini, ~8-9 menit) selesai exit 0, container `Up`, `docker logs --since 2m` menunjukkan startup bersih tanpa error/fatal/panic (`"Everything is ready. Begin running and processing data."`) — config YAML baru (`retry_on_failure`/`sending_queue`/`buffer_eviction_ttl`) ter-parse tanpa error. 3 container lain (Jaeger/Prometheus/Grafana) tetap `Up` tanpa terganggu (regresi negatif).

**Commit:** `6db6519` — `feat(milestone-6.2): retry dan queue exporter supabase via exporterhelper`

### Task 3 — `otel-collector-config.yaml` Diperluas

**Kesesuaian dengan plan:** Sesuai plan — digabung dalam commit yang sama dengan Task 2 (perubahan Go + YAML saling bergantung, tidak bermakna dipisah kategori commit karena keduanya `feat` yang sama, mirror preseden M6.1 Checkpoint 8).

**Apa yang dilakukan**
`exporters.supabase` diperluas nilai eksplisit (`retry_on_failure.{enabled,initial_interval,max_interval,max_elapsed_time,multiplier,randomization_factor}`, `sending_queue.{queue_size,num_consumers,batch.{flush_timeout,min_size}}`, `buffer_eviction_ttl`) — nilai SAMA PERSIS default resmi `exporterhelper`, ditulis eksplisit supaya operator tidak perlu baca kode Go.

**Hasil Verifikasi:** sama dengan Task 2 (satu siklus build+deploy).

**Commit:** `6db6519` (sama dengan Task 2)

---

## Checkpoint 3 — Unit Test Config

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 4 — `factory_test.go` Baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`factory_test.go` (baru, mirror gaya stdlib `testing` polos existing di `buffer_test.go`/`mapping_test.go`/`storage_test.go` — TIDAK memakai `testify`, konsisten style project meski `testify` tersedia sebagai indirect dep). 5 test: nilai default `createDefaultConfig()` (retry enabled+InitialInterval 5s+MaxElapsedTime 5m, queue NumConsumers 10+QueueSize 1000, BufferEvictionTTL 60m) sesuai resmi `exporterhelper`; `confmap.Unmarshal()` YAML SEBAGIAN (hanya `max_elapsed_time`+`num_consumers`+`buffer_eviction_ttl` disebut) — field yang TIDAK disebut (`InitialInterval`, `QueueSize`) HARUS tetap default, field yang disebut HARUS ter-override; `Validate()` DSN kosong/`BufferEvictionTTL` nol-negatif ditolak, kombinasi valid lolos.

**Temuan**
Test `TestConfig_UnmarshalYAMLOverrideSebagianSajaMempertahankanDefaultLain` BERHASIL pada percobaan pertama — membuktikan langsung (bukan asumsi) bahwa desain "embed tipe resmi `configretry`/`exporterhelper` sebagai sub-field, andalkan `confmap` untuk merge" (Task 2) genuinely bekerja tanpa perlu logic fallback manual buatan sendiri.

**Error/Kegagalan**
Satu bug kecil di test SENDIRI (bukan di kode produksi) sebelum dijalankan: `cfg.QueueSettings.Get().HasValue()` — salah panggil `HasValue()` (method pada `Optional[T]`) di atas hasil `Get()` (yang mengembalikan `*T`, bukan `Optional[T]`). Diperbaiki sebelum run pertama (`cfg.QueueSettings.Get() == nil` saja sudah cukup untuk assert terisi).

**Diagnosis dan Perbaikan**
Baca ulang signature `Optional[T].Get() *T` vs `Optional[T].HasValue() bool` (dua method berbeda, tipe penerima berbeda) — koreksi langsung di `factory_test.go` sebelum eksekusi.

**Hasil Verifikasi**
`go test ./... -v` — 24 test total (5 baru + 19 existing M6.1), SEMUA PASS, 0 gagal. `go mod tidy` dijalankan (4 package baru jadi direct dependency, sebelumnya indirect) — `go build`+`go test` tetap bersih setelahnya.

**Commit:** *(lihat commit setelah entri log ini)*

---
