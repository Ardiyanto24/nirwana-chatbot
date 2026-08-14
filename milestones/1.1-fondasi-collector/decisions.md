# Decisions — Milestone 1.1: Penyiapan OTel Collector sebagai Fondasi Observability Bersama

## Keputusan 1: Dependency Manager Python untuk Seluruh Proyek

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Repo belum punya kode Python sama sekali sebelum Milestone 1.1. Pemilihan dependency manager berdampak ke seluruh proyek (PIC 2-4 mengikuti konvensi yang sama), bukan cuma milestone ini, dan genuinely tidak bisa ditarik dari dokumen sumber manapun — dokumen implementasi eksplisit menyerahkan pilihan tech stack ke saat pengerjaan nyata.

**Keputusan yang Dipilih**
`uv` (Astral) sebagai dependency manager dan package runner untuk seluruh proyek Python.

**Alasan**
Kecepatan resolve/install jauh lebih tinggi dari alternatif, satu tool untuk venv+install+run (mengurangi jumlah tool yang perlu dipelajari PIC lain), lockfile otomatis (`uv.lock`), dan adopsi industri yang naik cepat untuk proyek baru di rentang 2024-2026.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Poetry** — lebih matang/lama dipakai luas, tapi lebih lambat dari `uv` dan konfigurasi `[tool.poetry]` di `pyproject.toml` lebih verbose.
- **pip + requirements.txt** — paling universal dan masih paling banyak dipakai di industri secara keseluruhan (terutama codebase lama/enterprise), tapi tanpa lockfile bawaan (versi bisa drift antar mesin) kecuali ditambah `pip-tools` terpisah.
- **Pipenv** — sempat jadi rekomendasi resmi PyPA, tapi popularitasnya menurun signifikan sejak 2022-an, komunitas cenderung pindah ke Poetry/`uv`, kurang direkomendasikan untuk proyek baru di 2026.

**Dampak**
Berlaku untuk seluruh proyek — PIC 2-4 mengikuti konvensi `uv` yang sama saat instrumentasi mereka mulai menambahkan dependency Python. `pyproject.toml` dan `uv.lock` di root repo menjadi satu-satunya sumber kebenaran dependency.

---

## Keputusan 2: Struktur Pipeline Collector (Endpoint, Processor, Fan-out 2 Jalur)

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 3 (diagram arsitektur pipeline, baris 49-93): endpoint OTLP/gRPC `localhost:4317`, struktur Receiver→Processor(`batch`,`memory_limiter`,`attributes`)→Exporter fan-out ke jalur privat (Jaeger+Prometheus, aktif) dan jalur publik (slot kosong untuk PIC 6).

**Keputusan yang Diikuti**
Konfigurasi `otel-collector-config.yaml` mengikuti persis struktur ini — tidak ada penyimpangan.

**Catatan Ketergantungan**
PIC 2-4 mengarahkan instrumentasi mereka ke endpoint yang sama persis (`localhost:4317`), dan PIC 6 bergantung pada slot exporter kedua yang formatnya sudah disiapkan di sini. Mengubah struktur ini sepihak di milestone lain akan merusak kontrak yang sudah dijanjikan ke seluruh PIC.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kontrak dokumen observability.

---

## Keputusan 3: Docker Compose untuk Orkestrasi Lokal (Collector + Jaeger + Prometheus)

**Sumber Paksaan**
`rancangan-context-decomposition.md` Milestone 1.1 Lingkup (baris 28): "Menyiapkan satu proses OTel Collector yang berjalan lokal (mis. lewat Docker)" — dikombinasikan dengan Docker yang sudah terverifikasi tersedia di lingkungan kerja (`docker --version` 29.2.1, `docker compose` v5.0.2) sebelum plan ditulis.

**Keputusan yang Diikuti**
Tiga service (`otel-collector`, `jaeger`, `prometheus`) dijalankan lewat satu `docker-compose.yml` di `infra/observability/`.

**Catatan Ketergantungan**
Bukan kontrak wajib ketat (dokumen sumber eksplisit menyebutnya sebagai *contoh*, bukan keharusan) — tapi tidak ada alasan kuat untuk memilih pendekatan lain (mis. instalasi manual biner) mengingat Docker sudah tersedia dan jauh lebih mudah direproduksi PIC lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Instalasi manual biner Jaeger/Prometheus/Collector langsung di OS** — ditolak karena jauh lebih sulit direproduksi antar mesin PIC yang berbeda, dan tidak disebut sebagai pola di dokumen manapun.

---

## Keputusan 4: Tag Image Docker `latest` (Bukan Versi Terkunci)

**Status:** Ditemukan di tengah implementasi pada Checkpoint 2.

**Latar Belakang**
Saat menulis `docker-compose.yml`, perlu diputuskan apakah image (`otel/opentelemetry-collector-contrib`, `jaegertracing/all-in-one`, `prom/prometheus`) dikunci ke versi tertentu atau memakai tag `latest`. Tidak ada preseden dari dokumen manapun soal ini — genuinely keputusan implementasi.

**Keputusan yang Dipilih**
Tag `latest` untuk ketiga image.

**Alasan**
Stack ini adalah alat verifikasi lokal (bukan deployment produksi) — nomor versi spesifik yang diketahui saat plan ditulis berisiko sudah tidak tersedia lagi di registry saat benar-benar dijalankan (image lama di-deprecate/dihapus), menyebabkan `docker compose up` gagal tanpa alasan yang jelas bagi PIC lain yang menjalankan ulang stack ini di kemudian hari.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Versi terkunci spesifik (mis. `otel/opentelemetry-collector-contrib:0.114.0`)** — ditolak karena nomor versi yang terlihat "terbaru" saat penulisan plan/kode berisiko sudah usang atau ditarik dari registry di kemudian hari; lebih cocok untuk deployment produksi (di luar cakupan milestone ini) daripada stack verifikasi lokal.

**Dampak**
PIC lain yang menjalankan `docker compose up -d` di `infra/observability/` akan selalu menarik versi image terbaru saat itu — perilaku Collector/Jaeger/Prometheus bisa sedikit berbeda antar waktu (mis. warning deprecation baru seperti yang ditemukan di Checkpoint 2, lihat Keputusan 5). Ini trade-off yang disadari, bukan diabaikan.

---

## Keputusan 5: Exporter Type `otlp` → `otlp_grpc` (Perbaikan Deprecation)

**Status:** Ditemukan di tengah implementasi pada Checkpoint 2, Task 7.

**Latar Belakang**
Log startup pertama `otel-collector` (image `latest`, resolve ke v0.158.0) menampilkan warning: `"otlp" alias is deprecated; use "otlp_grpc" instead` untuk exporter `otlp/jaeger`. Bukan keputusan yang direncanakan di plan (plan tidak menyebutkan nama exporter type spesifik), ditemukan langsung dari log runtime.

**Keputusan yang Dipilih**
Component id exporter diubah dari `otlp/jaeger` menjadi `otlp_grpc/jaeger`.

**Alasan**
Warning eksplisit menyebut pengganti yang benar, perbaikan murah (rename saja, tidak ada perubahan perilaku), dan menghindari technical debt di titik paling awal proyek — instrumentasi PIC 2-4 nanti akan mencontoh pola dari milestone ini, jadi lebih baik pola yang dicontoh sudah bersih dari warning deprecation sejak awal.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Membiarkan warning apa adanya (tidak fatal, container tetap jalan)** — ditolak karena murah diperbaiki dan berisiko diikuti PIC lain sebagai "pola yang dianggap benar" kalau dibiarkan di kode referensi Milestone 1.1.

**Dampak**
Murni internal `otel-collector-config.yaml` — tidak berdampak ke PIC lain karena mereka hanya perlu tahu endpoint OTLP (`localhost:4317`), bukan detail nama exporter type di sisi Collector.

---

## Keputusan 6: Tetap Memakai `opentelemetry-semantic-conventions==0.65b0` untuk Konstanta `gen_ai.*` Meski Statusnya "Deprecated"

**Status:** Ditemukan di tengah implementasi pada Checkpoint 3, Task 8.

**Latar Belakang**
Saat mengunci versi konvensi atribut GenAI (kewajiban eksplisit Milestone 1.1), ditemukan seluruh konstanta `gen_ai.*` di paket `opentelemetry-semantic-conventions` ditandai "Deprecated" di docstring — governance spesifikasi GenAI pindah ke repo terpisah `open-telemetry/semantic-conventions-genai` sejak rilis `semantic-conventions v1.42.0` (2026-06-12). Detail lengkap riset ada di `logs.md` Checkpoint 3 Task 8.

**Keputusan yang Dipilih**
Tetap memakai paket `opentelemetry-semantic-conventions==0.65b0` (dipin di `uv.lock`) sebagai sumber string konstanta `gen_ai.*`, diimpor lewat satu modul terisolasi `infra/observability/genai_semconv.py`. Dicatat sebagai keterbatasan diterima di `docs/keterbatasan-diterima.md` #1, dengan pemicu peninjauan ulang eksplisit.

**Alasan**
Repo baru (`open-telemetry/semantic-conventions-genai`) belum punya release/tag resmi maupun paket PyPI generated-code sendiri per tanggal pengecekan (dikonfirmasi lewat `WebFetch` ke halaman Releases-nya). Nilai string atribut yang dipakai proyek ini dikonfirmasi identik antara paket lama dan dokumentasi repo baru — tidak ada rename, hanya perpindahan governance. Tidak memakai apa pun sama sekali bukan pilihan (Milestone 1.1 wajib mengunci versi ini secara eksplisit), dan tidak ada sumber Python yang lebih otoritatif tersedia saat ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hardcode string atribut manual tanpa dependency ke paket manapun** — ditolak karena kehilangan jaminan versi yang bisa dipin/dilacak lewat `uv.lock`, dan tetap butuh sumber acuan yang sama (dokumentasi repo baru) untuk memastikan nilainya benar.
- **Menunda Milestone 1.1 sampai repo baru merilis paket resmi** — ditolak karena tidak ada linimasa yang diketahui, dan konvensi ini memang secara eksplisit didesain "pre-stable" oleh OTel sendiri (dicatat di header `rancangan-observability-ai-chatbot.md`) — menunggu stabil sepenuhnya bertentangan dengan ekspektasi dokumen sumber sendiri.

**Dampak**
PIC 2-4 wajib mengimpor konstanta `gen_ai.*` dari `infra/observability/genai_semconv.py`, bukan hardcode string sendiri — supaya kalau terjadi perubahan nyata di masa depan, cukup satu file yang perlu diperbarui. Lihat pemicu peninjauan ulang lengkap di `docs/keterbatasan-diterima.md` #1.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Dependency manager Python: `uv` | A | Plan |
| 2 | Struktur pipeline Collector (endpoint, processor, fan-out) | B | Plan / Checkpoint 2 |
| 3 | Docker Compose untuk orkestrasi lokal | B | Plan / Checkpoint 2 |
| 4 | Tag image Docker `latest` | A | Checkpoint 2 |
| 5 | Exporter type `otlp` → `otlp_grpc` | A | Checkpoint 2 |
| 6 | Tetap memakai `opentelemetry-semantic-conventions==0.65b0` meski deprecated | A | Checkpoint 3 |
