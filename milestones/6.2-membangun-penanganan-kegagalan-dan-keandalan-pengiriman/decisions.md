# Decisions — Milestone 6.2: Membangun Penanganan Kegagalan dan Keandalan Pengiriman

Dokumen ini mencatat setiap keputusan desain untuk Milestone 6.2 (PIC 6, Custom Exporter Go) — melengkapi exporter dasar M6.1 dengan retry, batching volume tinggi, dan eviction `Buffer`.

---

## Keputusan 1: Retry/Queue Configurable via YAML, Bukan Hardcode Go

**Status:** Diputuskan sebelum implementasi (dari plan, dikonfirmasi `AskUserQuestion`).

**Latar Belakang**
Riset kode `exporterhelper@v0.159.0` (Go module cache lokal) mengonfirmasi `exporterhelper.NewTraces()` di M6.1 (`factory.go`) TIDAK memakai `WithRetry`/`WithQueue` sama sekali — dokumentasi resmi package eksplisit: "The default configretry.BackOffConfig is to disable retries" dan "The default QueueBatchConfig is to disable queueing". Menambahkan mekanisme ini butuh keputusan apakah parameternya (interval retry, ukuran queue, dst) di-hardcode di kode Go atau diekspos ke `otel-collector-config.yaml` — tidak ada preseden literal di dokumen sumber mana pun yang mengunci pilihan ini.

**Keputusan yang Dipilih**
Field baru ditambahkan ke `Config` struct (`factory.go`, mapstructure) untuk retry (`retry_enabled`, `retry_initial_interval`, `retry_max_interval`, `retry_max_elapsed_time`, `retry_multiplier`, `retry_randomization_factor`) dan queue (`queue_size`, `num_consumers`, `batch_flush_timeout`, `batch_min_size`) — diekspos di `infra/observability/otel-collector-config.yaml` bagian `exporters.supabase` dengan nilai eksplisit.

**Alasan**
Konsisten dengan cara SELURUH komponen lain di pipeline Collector ini dikonfigurasi — `batch.timeout` (5s), `memory_limiter.limit_mib` (512) sudah eksplisit di YAML sejak M1.1, bukan hardcode di kode processor bawaan. Menjaga pola yang sama membuat `otel-collector-config.yaml` tetap jadi satu-satunya tempat operator perlu melihat untuk memahami perilaku SELURUH pipeline, tanpa perlu baca kode Go untuk tahu berapa lama retry window exporter Supabase.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hardcode default sensible di `factory.go`** (`configretry.NewDefaultBackOffConfig()`/`exporterhelper.NewDefaultQueueConfig()` langsung, tanpa expose ke YAML) — lebih sederhana secara implementasi, tapi tuning parameter (mis. memperpanjang `MaxElapsedTime` kalau observasi produksi menunjukkan gangguan Supabase lebih lama dari 5 menit) akan butuh ubah kode Go + rebuild `ocb` (~8-9 menit per rebuild, preseden sesi M6.1 sebelumnya) tiap kali — jauh lebih mahal dibanding edit YAML + restart container.

**Dampak**
`custom-exporter/supabaseexporter/factory.go` (Config struct + createTracesExporter), `infra/observability/otel-collector-config.yaml` (exporters.supabase). Field YAML kosong tetap fallback ke default resmi `exporterhelper` (tidak ada nilai "kosong = error").

---

## Keputusan 2: Fault Injection KK1 via Postgres Lokal Disposable

**Status:** Diputuskan sebelum implementasi (dari plan, dikonfirmasi `AskUserQuestion`).

**Latar Belakang**
KK1 M6.2 ("simulasi gangguan sesaat... span yang akhirnya tetap tertulis lewat mekanisme retry") butuh cara mensimulasikan "Supabase tidak terjangkau" secara NYATA dan TERKONTROL, TANPA me-restart proses Collector (restart akan mengosongkan `Buffer`/queue in-memory dan membuat bukti "retry berhasil" rancu dengan "redrain dari nol setelah restart" — dua mekanisme yang sangat berbeda tapi bisa terlihat sama dari luar kalau tidak hati-hati). Supabase sendiri adalah layanan cloud eksternal yang tidak bisa "dipause" langsung oleh sesi kerja ini.

**Keputusan yang Dipilih**
Postgres lokal disposable (`docker run postgres`, skema `traces`/`spans` dibuat lewat `SQLModel.metadata.create_all()` reuse `src/db/models.py` `TraceRow`/`SpanRow`) dijalankan terpisah dari stack utama. DSN exporter diarahkan ke sana SEKALI di awal test (satu restart Collector sebagai titik mulai, bukan mid-test). `docker stop`/`docker start` container Postgres lokal itu untuk simulasi outage — Collector utama TIDAK disentuh sama sekali selama simulasi berlangsung. Supabase asli tidak pernah terlibat dalam test ini.

**Alasan**
Satu-satunya cara mensimulasikan outage yang GENUINELY terkontrol (bisa distop/dinyalakan ulang presisi kapan saja) dan REVERSIBLE tanpa risiko mengganggu layanan cloud pihak ketiga (Supabase) yang juga dipakai bagian lain sistem (dashboard publik M5.2-5.4). Karena Collector tidak di-restart, bukti "span akhirnya tertulis" genuinely berasal dari mekanisme retry+queue in-memory `exporterhelper`, bukan efek samping restart.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`docker network disconnect`/`reconnect` container Collector** — lebih "real" (memutus konektivitas ke Supabase asli sungguhan), tapi memutus SELURUH konektivitas outbound Collector (termasuk trafik lain kalau ada) dan kurang presisi/reversibel dibanding kontainer disposable yang genuinely didedikasikan untuk test ini saja.
- **Ubah DSN ke alamat salah + restart Collector saat pulih** — ditolak eksplisit di latar belakang: restart akan mencampur dua mekanisme berbeda (retry in-memory vs redrain pasca-restart), tidak membuktikan KK1 secara literal.

**Dampak**
Skrip baru `milestones/6.2-.../setup_local_postgres.py` (Checkpoint 5), tidak menyentuh `DATABASE_URL`/Supabase produksi. Kredensial Postgres lokal murni test-only, tidak pernah di-commit sebagai secret nyata (default lokal, bukan kredensial produksi apa pun).

---

## Keputusan 3: TTL Eviction Buffer — 60 Menit

**Status:** Diputuskan sebelum implementasi (dari plan, dikonfirmasi `AskUserQuestion`).

**Latar Belakang**
`docs/keterbatasan-diterima.md` #20 mewajibkan M6.2 meninjau ulang eviction untuk `Buffer` in-memory (trace yang span akarnya tidak pernah tiba tertahan selamanya, risiko memory leak lambat). Menentukan nilai TTL adalah trade-off nyata: TTL yang terlalu pendek berisiko meng-evict span dari turn yang GENUINELY masih berjalan (lambat, bukan crash) — project ini punya riwayat nyata hang LLM sampai ~24.7 menit (`keterbatasan-diterima.md` #7, recurring beberapa kali across M7.12/M5.1/M6.1), sehingga angka TTL bukan pilihan sembarang.

**Keputusan yang Dipilih**
TTL eviction default 60 menit — jauh di atas worst-case hang yang pernah tercatat (~25 menit), configurable via `Config.buffer_eviction_ttl` (YAML, konsisten Keputusan 1).

**Alasan**
Tujuan eviction di M6.2 adalah jaring pengaman untuk proses yang GENUINELY crash/mati (`proses_turn()` crash sebelum `invoke_agent` selesai, atau Collector di-restart di tengah trace berjalan) — BUKAN mekanisme pembersihan operasional harian. Margin besar (60 menit vs observasi terpanjang ~25 menit) memastikan TTL nyaris tidak pernah salah meng-evict turn yang masih hidup meski lambat, sekaligus tetap membatasi memori untuk kasus benar-benar mati (bukan unbounded selamanya seperti M6.1).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **TTL pendek, 10-15 menit** — membatasi memori lebih ketat, tapi py risiko nyata meng-evict span dari turn yang masih genuinely berjalan saat kebetulan mengalami hang LLM terpanjang yang pernah tercatat project ini — span itu makin tidak akan pernah masuk Supabase sekalipun turn akhirnya selesai, kontraproduktif terhadap tujuan M6.2 sendiri ("keandalan pengiriman").

**Dampak**
`custom-exporter/supabaseexporter/buffer.go` (goroutine ticker eviction, Checkpoint 4), `Config.buffer_eviction_ttl` (YAML, default 60m kalau tidak diisi).

---

## Keputusan 4 (Jenis B): Tidak Ada SQL-Level Multi-Row Batch INSERT

**Sumber Paksaan**
Bukti empiris verifikasi produksi M6.1 (trace `0767cf9b32464b44cca43e8d5d810295`, 39 span; trace `f831b5b7...`, 44 span) — pola `Exec()` single-row per span yang sudah ada (`storage.go`) TERBUKTI bekerja tanpa masalah performa untuk volume yang realistis di project ini ("puluhan span sekaligus" per KK2 literal).

**Keputusan yang Diikuti**
`storage.go` TIDAK diubah untuk mendukung multi-row `INSERT ... VALUES (...), (...), ...` — retry+queue (Keputusan 1) dan eviction (Keputusan 3) sudah cukup untuk memenuhi KK1+KK2 literal.

**Catatan Ketergantungan**
Menambah SQL batching sekarang adalah optimasi tanpa bukti masalah nyata yang perlu diperbaiki — bertentangan prinsip "jangan over-engineer" (`CLAUDE.md`). Kalau volume produksi nyata di masa depan TERBUKTI menyebabkan masalah performa (belum pernah terjadi), ini bisa ditinjau ulang sebagai keterbatasan/perbaikan baru saat itu, bukan diantisipasi sekarang tanpa bukti.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by bukti empiris di atas, bukan keputusan desain yang genuinely dipertimbangkan dua arah.

---

## Keputusan 5 (Jenis B): `NumConsumers` Queue Dibiarkan Default (10)

**Sumber Paksaan**
Desain `Buffer.Ingest()` (M6.1, addendum bug-fix sebelumnya) — seluruh method dibungkus `sync.Mutex` (`b.mu.Lock()`) untuk KESELURUHAN durasi eksekusi termasuk panggilan Postgres di dalamnya.

**Keputusan yang Diikuti**
`num_consumers` di `Config` (Keputusan 1) tetap memakai default `exporterhelper` (10) kalau tidak diisi eksplisit di YAML — TIDAK diturunkan paksa ke 1 di kode Go.

**Catatan Ketergantungan**
Mutex `Buffer.mu` membuat SELURUH goroutine consumer queue efektif terserialisasi saat mengakses `Buffer` — menaikkan `NumConsumers` tidak memberi paralelisme nyata untuk exporter ini SPESIFIK, tapi juga tidak menyebabkan bug (goroutine ekstra hanya antre menunggu lock, bukan korupsi state). Menurunkan paksa ke 1 butuh justifikasi kuat (mis. bukti overhead goroutine idle jadi masalah nyata) yang tidak ada — default tetap aman dan lebih predictable bagi siapa pun yang membaca `otel-collector-config.yaml` mengharapkan perilaku standar `exporterhelper`.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by karakteristik `Buffer.mu` di atas, murni catatan kenapa TIDAK ada override, bukan pilihan dua arah yang genuinely dipertimbangkan.

---

## Keputusan 6 (Jenis B): Postgres Lokal Disposable Pakai Superuser Default

**Sumber Paksaan**
Tujuan Postgres lokal (Keputusan 2) murni fault-injection mekanisme retry — bukan pengujian keamanan/least-privilege (itu sudah dibuktikan M6.1 Checkpoint 4 terhadap Supabase asli, role `nirwana_exporter_writer`).

**Keputusan yang Diikuti**
Postgres lokal disposable memakai user superuser default image resmi (`postgres`), TIDAK mereplikasi provisioning role write-only M6.1 Checkpoint 4.

**Catatan Ketergantungan**
Mereplikasi role restriktif untuk instance yang hidup beberapa menit lalu dibuang tidak menambah nilai verifikasi apa pun untuk KK1 (yang murni soal retry timing, bukan soal privilege) — kredensial ini tidak pernah menyentuh Supabase asli maupun disimpan permanen.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by cakupan sempit tujuan Postgres lokal ini.

---

## Keputusan 7 (Jenis B): "Pencatatan Saat Retry Habis" Tidak Butuh Kode Tambahan

**Sumber Paksaan**
Baca langsung source `exporterhelper@v0.159.0/internal/queue_sender.go`+`base_exporter_test.go` (Go module cache lokal) — `logger.Error("Exporting failed. Dropping data."+exportFailureMessage, zap.Error(errSend), zap.Int("dropped_items", itemsCount))` SUDAH dipanggil otomatis oleh `exporterhelper` sendiri saat retry habis (`MaxElapsedTime` terlewati) atau queue penuh, memakai `zap.Logger` yang SAMA (`set.TelemetrySettings.Logger`) yang sudah diteruskan ke `Buffer` sejak addendum M6.1 sebelumnya.

**Keputusan yang Diikuti**
KK M6.2 "pencatatan (log internal Collector, bukan span baru) ketika penulisan ke Supabase benar-benar gagal setelah batas percobaan ulang habis" terpenuhi OTOMATIS begitu Keputusan 1 (`WithRetry`+`WithQueue`) diterapkan — tidak ada kode logging tambahan yang perlu ditulis khusus untuk sub-requirement ini.

**Catatan Ketergantungan**
Menulis ulang logging serupa di kode kita sendiri akan jadi duplikasi tidak perlu terhadap mekanisme yang sudah disediakan package resmi upstream.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by perilaku `exporterhelper` yang sudah terverifikasi lewat pembacaan source langsung.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Retry/Queue configurable via YAML, bukan hardcode Go | A | Plan |
| 2 | Fault injection KK1 via Postgres lokal disposable | A | Plan |
| 3 | TTL eviction Buffer — 60 menit | A | Plan |
| 4 | Tidak ada SQL-level multi-row batch INSERT | B | Plan |
| 5 | `NumConsumers` queue dibiarkan default (10) | B | Plan |
| 6 | Postgres lokal disposable pakai superuser default | B | Plan |
| 7 | "Pencatatan saat retry habis" tidak butuh kode tambahan | B | Plan |
