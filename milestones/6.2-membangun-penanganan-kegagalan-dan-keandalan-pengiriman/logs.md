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

**Commit:** `3ec615d` — `test(milestone-6.2): validasi wiring Config retry/queue`

---

## Checkpoint 4 — Buffer Eviction TTL (keterbatasan-diterima.md #20)

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21 (sesi sempat terputus restart komputer di antara Checkpoint 3 dan 4 — Docker Desktop mati total, semua 4 container `Exited (255)`. Dipulihkan: relaunch Docker Desktop, `docker compose up -d` — semua container `Up` bersih, `.env`/`SUPABASE_EXPORTER_DSN` ter-load normal tanpa perlu intervensi manual, tidak ada data/state yang hilang dari sesi sebelumnya karena git sudah menyimpan seluruh commit Checkpoint 1-3.)

### Task 5 — `Buffer` Ditambah Eviction TTL

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`pendingEntry{span mappedSpan, arrivedAt time.Time}` menggantikan `mappedSpan` polos sebagai tipe elemen `pending map[string][]pendingEntry` — `arrivedAt` diisi `time.Now()` saat `Ingest()` menahan span (BUKAN `Row.StartedAt` span asli, yang mencerminkan waktu pembuatan span di Python, bisa jauh lebih tua dari waktu genuinely tiba di buffer kalau upstream delay). `NewBuffer()` sekarang menerima `evictionTTL time.Duration` dan LANGSUNG menjalankan goroutine `evictionLoop()` (interval 1/10 TTL, dibatasi 1-5 menit) yang memanggil `evictExpired(now)` periodik — method ini TERPISAH dari loop-nya sendiri (testable langsung dengan `now` buatan, tidak perlu menunggu ticker nyata). `Stop()` menutup `stopCh` lalu MENUNGGU `doneCh` (evictionLoop genuinely exit, bukan fire-and-forget) — dipanggil dari `shutdown()` `tracesExporter` (factory.go) sebelum `storage.Close()`. `insertableLocked()`/`drainLocked()`/`PendingSpansFor()` disesuaikan bekerja dengan `pendingEntry` (unwrap ke `mappedSpan` di titik yang butuh).

**Temuan**
Mengubah tipe elemen `pending` (dari `mappedSpan` ke `pendingEntry`) berdampak ke SEMUA fungsi yang menyentuhnya (`Ingest`, `drainLocked`, `PendingSpansFor`) — refactor lebih luas dari yang terlihat di deskripsi task plan ("Buffer ditambah pelacakan waktu"), tapi tetap dalam SATU task koheren (tidak ada perubahan behavior lain selain menambah dimensi waktu).

**Error/Kegagalan**
Tidak ada di kode produksi. (Lihat Task 6 untuk satu bug kecil di test yang ditemukan+diperbaiki sebelum eksekusi pertama.)

**Hasil Verifikasi**
`go build ./...` bersih.

**Commit:** `a4522dc` (gabung dengan Task 6, lihat di bawah)

### Task 6 — Unit Test Eviction

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
3 test baru di `buffer_test.go`: `TestBuffer_EvictExpired_SpanMelewatiTTLDihapusDanLogged` (span pending + `evictExpired(now)` dipanggil dengan `now` 2 jam ke depan, TTL 1 jam — harus ter-evict, `PendingCount()` jadi 0, TIDAK ikut ter-INSERT, DAN 1 WARN log tercatat via `zap/zaptest/observer` dengan `trace_id`/`span_id` benar), `TestBuffer_EvictExpired_SpanBelumMelewatiTTLTetapBertahan` (kebalikan — `now` cuma +5 menit, MASIH di bawah TTL 1 jam, span harus tetap utuh), `TestBuffer_Stop_GoroutineEvictionBerhentiBersih` (`Stop()` dipanggil di goroutine terpisah, harus kembali dalam <5 detik — membuktikan `doneCh` genuinely ditutup, bukan hang). 6 test `NewBuffer(...)` existing (M6.1) diperbarui menambah argumen `time.Hour` + `t.Cleanup(buf.Stop)` (sed, supaya goroutine eviction test lama tidak menggantung sepanjang sisa test run).

**Temuan**
`go test -race` TIDAK BISA jalan langsung di host Windows — race detector Go butuh cgo, cgo butuh compiler C (`gcc`), TIDAK ada di PATH host ini (dikonfirmasi `which gcc` kosong). Diselesaikan menjalankan test SET LENGKAP di dalam container `golang:1.26` resmi (sudah bawa gcc) via `docker run -v <path>:/app -w /app golang:1.26 go test ./... -race` — MSYS_NO_PATHCONV=1 diperlukan supaya Git Bash tidak salah menerjemahkan path `-w /app` jadi path Windows.

**Error/Kegagalan**
Satu bug kecil di test SENDIRI (bukan produksi), ditemukan sebelum run pertama: draft awal `TestBuffer_EvictExpired_SpanMelewatiTTLDihapusDanLogged` sempat memakai `logs.FilterMessageSnippet(...).All()[0].ContextMap()` tanpa memastikan filter cocok — diperiksa ulang manual sebelum eksekusi (bukan trial-error), tidak sampai menyebabkan test run gagal.

**Hasil Verifikasi**
`go test ./... -race -v` (container `golang:1.26`) — **27 test total, SEMUA PASS, nol race condition terdeteksi**. Test lama (24) tetap hijau setelah refactor `pendingEntry`.

**Commit:** `a4522dc` — `feat(milestone-6.2): eviction TTL Buffer untuk trace anchor tak pernah tiba`

---

## Checkpoint 5 — Postgres Lokal Disposable untuk Fault Injection

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 7 — `setup_local_postgres.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`milestones/6.2-.../setup_local_postgres.py` (mirror gaya `seed_employees.py`/`seed_sample_trace.py`): `docker run` Postgres lokal (`postgres:16`, container `nirwana-m62-fault-postgres`, port host 5433, kredensial superuser default lokal-only - Keputusan 6), poll `pg_isready` sampai siap, `SQLModel.metadata.create_all(engine, tables=[TraceRow.__table__, SpanRow.__table__])` — SENGAJA hanya 2 tabel (bukan `create_all()` polos yang akan membuat SELURUH tabel project seperti `session_memory_packages`/`roles` yang tidak relevan). Print 2 bentuk DSN: `postgresql+psycopg://...` (dipakai skrip Python sendiri) dan `postgres://...` (bentuk plain untuk `SUPABASE_EXPORTER_DSN` exporter Go/pgx, dipakai Checkpoint 7).

**Temuan**
Image `postgres:16` belum pernah ditarik di mesin ini - proses `docker run` pertama makan waktu >60 detik (pull image), command dipindah ke background otomatis. Tidak masalah, hanya perlu menunggu notifikasi selesai.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`docker exec ... psql \dt` menunjukkan `traces`+`spans` ada. `\d traces`/`\d spans` mengonfirmasi skema PERSIS kontrak Bagian 4 (termasuk FK `spans_parent_span_id_fkey`/`spans_trace_id_fkey` yang jadi fokus test Checkpoint 7). INSERT+SELECT manual (1 baris `traces`+1 baris `spans`) berhasil, lalu `TRUNCATE ... CASCADE` untuk membersihkan sebelum test nyata Checkpoint 7.

**Commit:** *(lihat commit setelah entri log ini)*

---
