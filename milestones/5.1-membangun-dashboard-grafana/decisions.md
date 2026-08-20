# Decisions — Milestone 5.1: Membangun Dashboard Grafana untuk Trace dan Metrics

Dokumen ini mencatat keputusan desain yang diambil untuk Milestone 5.1, seluruhnya ditentukan sebelum implementasi dimulai (dari Plan Mode, riset 2 agent Explore + 1 agent Plan, diverifikasi ulang baca langsung file kunci).

---

## Keputusan 1: Hosting Grafana — Self-hosted vs Grafana Cloud

**Status:** Diputuskan sebelum implementasi (dari plan), dikonfirmasi user via `AskUserQuestion`.

**Latar Belakang**
Dokumen `rancangan-observability-dashboard.md` menyebut "Grafana Cloud versi gratis tidak menyediakan fitur publish dashboard ke publik" sebagai alasan kenapa ada dua dashboard terpisah (Grafana privat vs Next.js+Supabase publik) — tapi tidak secara eksplisit mewajibkan M5.1 sendiri memakai Grafana Cloud. Keputusan tech stack memang sengaja diserahkan ke saat pengerjaan nyata ("Milestone tidak menentukan tech stack, library, atau arsitektur detail secara spesifik"). Ini genuinely terbuka: dua opsi (self-hosted vs Grafana Cloud) sama-sama teknis valid di permukaan.

**Keputusan yang Dipilih**
Grafana **self-hosted**, sebagai service Docker baru di `infra/observability/docker-compose.yml` yang sama dengan `otel-collector`/`jaeger`/`prometheus`.

**Alasan**
1. Dashboard Grafana memang didesain **privat** (`rancangan-observability-ai-chatbot.md` Prinsip Fondasi #2: "Privat (Jaeger+Prometheus+Grafana) — tooling debugging teknis untuk pemilik project... tidak dipublikasikan"). Alasan dokumen menyebut "Grafana Cloud" (limitasi publish ke publik) karena itu tidak relevan untuk M5.1 — publish-ke-publik sengaja dipindah ke Next.js+Supabase (M5.2-5.4).
2. Grafana Cloud (hosted eksternal) secara fungsional **tidak bisa menjangkau** `jaeger:16686`/`prometheus:9090` yang berjalan di jaringan Docker Compose lokal developer tanpa tunnel/agent tambahan (mis. Grafana Alloy, ngrok) — komponen infrastruktur baru yang tidak disebut di dokumen manapun dan memperluas scope M5.1 di luar 8 dokumen sumber kebenaran.
3. Preseden M1.1 identik: 3 service existing (Collector, Jaeger, Prometheus) semua self-hosted docker-compose, image tag `latest`. Menambah Grafana sebagai service ke-4 adalah kelanjutan pola.
4. Concern "data hilang saat restart container" dimitigasi arsitektural (lihat Keputusan 3), bukan diterima sebagai risiko.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Grafana Cloud (free tier)** — ditolak karena blocker fungsional reachability ke data source lokal (poin 2 di atas), dan fitur yang jadi alasan disebut dokumen (publish publik) memang tidak relevan untuk dashboard privat.

**Dampak**
Murni internal M5.1. Tidak ada dampak lintas-pekerjaan — M5.2-5.4 (Next.js+Supabase) tetap jadi jalur publik terpisah sesuai desain awal, tidak terpengaruh keputusan hosting Grafana ini.

---

## Keputusan 2: Edisi dan Versi Image Grafana

**Sumber Paksaan**
Preseden `milestones/1.1-fondasi-collector/decisions.md` Keputusan 4 (tag `latest` untuk seluruh image observability, trade-off reproducibility vs staleness sudah diterima eksplisit di sana) + prinsip arsitektur "jangan membangun kapabilitas di luar cakupan" (fitur Grafana Enterprise berlisensi tidak dibutuhkan skenario M5.1).

**Keputusan yang Diikuti**
Image `grafana/grafana-oss:latest` — edisi OSS (bukan `grafana/grafana` yang membawa fitur Enterprise berlisensi terbuka tapi butuh lisensi untuk diaktifkan), tag `latest` konsisten 3 service lain di `docker-compose.yml` yang sama.

**Catatan Ketergantungan**
Kalau di masa depan M5.1 (atau follow-up-nya) ternyata butuh fitur Enterprise (mis. reporting berlangganan), keputusan ini perlu direvisit — tapi tidak ada indikasi kebutuhan itu di dokumen sumber manapun.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden tag `latest` M1.1 dan tidak adanya kebutuhan fitur berlisensi di scope M5.1.

---

## Keputusan 3: Provisioning-as-Code untuk Datasource dan Dashboard

**Sumber Paksaan**
Pola existing `otel-collector-config.yaml`/`prometheus.yml` (file config di-mount read-only dari git, bukan diedit lewat UI container) + prinsip project "verifikasi nyata, reproducible" (`CLAUDE.md` "Cara Memulai Sesi Kerja": bukti harus bisa ditelusuri ulang, bukan state di browser seseorang yang tidak tercatat).

**Keputusan yang Diikuti**
Datasource Grafana (`infra/observability/grafana/provisioning/datasources/datasources.yaml`) dan dashboard (`infra/observability/grafana/provisioning/dashboards/dashboards.yaml` + `infra/observability/grafana/dashboards/observability.json`) didefinisikan sebagai file yang di-commit git, load otomatis saat container start via mekanisme provisioning resmi Grafana. Volume Docker (`grafana-data:/var/lib/grafana`) hanya cache sekunder (histori login dsb), bukan sumber kebenaran konfigurasi — restart container tidak menghilangkan datasource/dashboard.

**Catatan Ketergantungan**
Kalau konfigurasi diubah manual lewat UI Grafana saat debugging, perubahan itu HILANG saat container di-restart (by design) — perubahan permanen wajib dituliskan balik ke file provisioning. Ini konsisten dengan cara kerja `otel-collector-config.yaml` yang sudah jadi kebiasaan project ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Konfigurasi manual lewat UI Grafana (click-ops)** — ditolak karena tidak reproducible, tidak bisa di-review lewat git diff, dan menyimpang dari pola seluruh config observability lain di project ini.

---

## Keputusan 4: spanmetricsconnector di Collector — Pipeline Baru, Dimension, dan Verifikasi Nama Metrik

**Status:** Ditemukan di tengah riset plan (gap teknis: `otel-collector-config.yaml` saat ini tidak punya mekanisme derivasi metrik agregat dari span, padahal 3 dari 4 panel M5.1 butuh data time-series/agregat yang hanya tersedia lewat Prometheus, bukan lewat Jaeger datasource native).

**Latar Belakang**
Grafana's Jaeger datasource (dikonfirmasi lewat riset kapabilitas: mode query "Search" dan "TraceID") bisa langsung dipakai untuk daftar trace + waterfall span individual, tapi TIDAK mendukung agregasi time-series (rata-rata durasi per layer, hitung kemunculan tag dalam rentang waktu). Panel "latency per layer", "distribusi status", dan "frekuensi error.type" genuinely butuh data di Prometheus — yang berarti butuh derivasi metrik dari span, yang saat ini tidak ada di pipeline Collector manapun.

**Keputusan yang Dipilih**
Tambah connector `spanmetrics` sebagai **pipeline baru aditif** di `otel-collector-config.yaml`: `traces/spanmetrics` (receiver `otlp` yang sama secara fan-out) → connector `spanmetrics` → `metrics/spanmetrics` (exporter `prometheus` yang sama, reuse). Pipeline `traces` existing menuju Jaeger **tidak diubah satu baris pun**. Dimension yang dipakai: `prompt.id` (disambiguator ~12 span `chat` yang nama-nya reused lintas layer — sudah terpasang di 15 lokasi kode existing) dan `error.type` (sudah terpasang di 9 file dengan nilai sesuai taksonomi) — keduanya zero-touch ke instrumentasi 9 layer PIC 1-4. Nama metrik persis yang dihasilkan connector (bervariasi antar versi image `latest`) dikonfirmasi empiris via `curl localhost:9090/api/v1/label/__name__/values` saat implementasi Checkpoint 3, dicatat di `logs.md` — tidak diasumsikan dari dokumentasi versi tertentu.

**Alasan**
Menambah connector adalah penambahan pipeline BARU secara OTel Collector fan-out (satu receiver `otlp` bisa dirujuk banyak pipeline sekaligus) — PIC 1-4 tidak akan melihat span mereka hilang/berubah bentuk di Jaeger karena pipeline yang mereka pakai (`traces`→Jaeger) sama sekali tidak disentuh. Ini menghormati batasan "PIC 5 murni konsumen, tidak boleh mengganggu instrumentasi PIC 1-4" sekaligus tetap memenuhi kebutuhan data agregat yang genuinely tidak bisa dipenuhi Jaeger datasource sendirian.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Emit metric custom langsung dari kode aplikasi (src/layers/) untuk tiap layer** — ditolak: lebih invasif (perlu menyentuh 9 layer PIC 1-4 yang sudah selesai), melanggar prinsip M5.1 murni konsumen.
- **Panel agregat dibangun dari Jaeger datasource langsung (search+filter manual, dihitung manual)** — ditolak: Jaeger datasource Grafana tidak punya kapabilitas aggregation/percentile/count-by-tag server-side, hanya list-of-traces.
- **Mengasumsikan nama metrik spanmetrics dari dokumentasi upstream tanpa verifikasi empiris** — ditolak: image bertag `latest`, konvensi penamaan connector ini beberapa kali berubah antar rilis upstream OTel Collector Contrib.

**Dampak**
File `infra/observability/otel-collector-config.yaml` adalah file bersama (dipakai PIC 1-4 juga) — perubahan ini aditif murni, tidak ada dampak fungsional ke pipeline traces existing. Perlu dicatat di `infra/observability/README.md` agar PIC lain yang membaca file ini paham ada pipeline metrics tambahan.

---

## Keputusan 5: Sumber Data Panel "Distribusi Status"

**Sumber Paksaan**
Taksonomi status baku project (`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/`terblokir_ketergantungan`) + kode existing `src/orchestration/riwayat_percakapan.py:58` (`simpan_riwayat_turn()`, dibangun M7.18) yang memasang atribut `riwayat.status` pada span `riwayat.simpan`.

**Keputusan yang Diikuti**
Panel "Distribusi Status" bersumber dari dimension `riwayat.status` pada span `riwayat.simpan` (via spanmetricsconnector, Keputusan 4) — level TURN, bukan level atomic-intent. Ini satu-satunya sinyal status yang sudah terpasang dan mencakup nilai positif `berhasil` (atribut `error.type` di layer lain HANYA dipasang di jalur kegagalan, tidak pernah `error.type=berhasil`, jadi tidak bisa dipakai sendirian untuk merepresentasikan distribusi status penuh).

**Catatan Ketergantungan**
Panel ini melengkapi (bukan duplikat) Panel "Frekuensi error.type" (Keputusan berikutnya, level span/atomic-intent) — kalau `riwayat_percakapan.py` di masa depan berubah bentuk atau atribut `riwayat.status` dihapus, panel ini akan rusak dan perlu disesuaikan mengikuti pemilik kode tersebut (PIC 7).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menghitung "distribusi status" dari agregasi `error.type` seluruh span di satu trace secara manual di sisi Grafana** — ditolak: lebih rumit (butuh logic agregasi lintas-span di level query), sementara `riwayat.status` sudah menyediakan status level-turn yang sudah diagregasi deterministik oleh `tentukan_status_keseluruhan_turn()`.

---

## Keputusan 6: Kredensial Admin Grafana

**Sumber Paksaan**
Prinsip arsitektur "Rahasia tidak boleh di-hardcode atau di-commit" (`CLAUDE.md`) + pola existing `.env`/`.env.example` untuk `OPENROUTER_API_KEY`, `DATABASE_URL`, `CHATBOT_API_BASE_URL`.

**Keputusan yang Diikuti**
`GRAFANA_ADMIN_PASSWORD` ditambahkan ke `.env.example` (kosong, dengan komentar penjelasan) dan diisi nyata di `.env` lokal (gitignored). Docker Compose membaca lewat `environment: GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}`.

**Catatan Ketergantungan**
Tidak ada — pola ini sudah established, tidak ada ruang variasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by prinsip arsitektur dan pola existing.

---

## Keputusan 7: Mekanisme Verifikasi KK1 dan KK2 — Turn Nyata via HTTP

**Sumber Paksaan**
Teks KK1 eksplisit: "Trace dari satu turn percakapan nyata (dicoba dari sistem yang sudah berjalan, bukan data dummy)..." + preseden verifikasi-nyata M7.14/7.16/7.17/7.18 (seluruhnya membuktikan lewat eksekusi sungguhan, bukan mock).

**Keputusan yang Diikuti**
Verifikasi KK1 (Checkpoint 4) dan KK2 (Checkpoint 6) memakai turn nyata lewat `POST /v1/turns` dengan `chatbot_api` lokal + `uvicorn src.main:app` + stack `docker compose` observability (4 service) berjalan bersamaan — bukan payload dummy yang dikirim langsung ke Collector.

**Catatan Ketergantungan**
Ketergantungan pada seluruh stack (server aplikasi + `chatbot_api` lokal + observability stack) berjalan bersamaan menambah kompleksitas operasional verifikasi dibanding memakai `smoke_test/send_dummy_span.py` — tapi ini tidak bisa dihindari karena KK1 secara literal menolak "data dummy".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Memakai `smoke_test/send_dummy_span.py` untuk memenuhi KK1** — ditolak eksplisit oleh teks KK1 sendiri ("bukan data dummy"). Tetap dipakai HANYA untuk verifikasi plumbing spanmetricsconnector di Checkpoint 3 (bukan pembuktian KK1/KK2).

---

## Keputusan 8: Skenario Uji Terkontrol untuk KK2

**Sumber Paksaan**
Preseden berulang M7.3/M7.10/M7.11/M7.12 — skenario "Front Office Staff bertanya domain `financial` (`gop_margin`)" dipakai berulang kali dengan hasil konsisten (`ditolak_otorisasi`) sebagai bukti RBAC-denial project ini.

**Keputusan yang Diikuti**
Checkpoint 6 mereuse skenario `gop_margin` persis (bukan dikarang ulang) untuk membuktikan `error.type=ditolak_otorisasi` menonjol di panel. Skenario kedua (turn Execution biasa) dibiarkan berjalan natural — per `docs/keterbatasan-diterima.md` #15 (data `chatbot_api` lokal stale), kemungkinan besar akan menghasilkan `gagal_teknis`/`sebagian` secara alami tanpa perlu direkayasa, sesuai temuan M7.14.

**Catatan Ketergantungan**
Kalau `docs/keterbatasan-diterima.md` #15 sudah teratasi (data `chatbot_api` lokal di-refresh) sebelum Checkpoint 6 dikerjakan, skenario kedua mungkin menghasilkan `berhasil` alih-alih `gagal_teknis` — itu justru bukti tambahan yang baik (panel bisa menampilkan `berhasil` juga), bukan kegagalan verifikasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Merekayasa kegagalan teknis secara paksa (mis. mematikan `chatbot_api` sementara)** — ditolak: preseden project (M7.14) menunjukkan `gagal_teknis` sudah muncul alami dari kondisi data stale yang genuinely ada di lingkungan kerja, tidak perlu direkayasa buatan.

---

## Keputusan 9: Status `docs/keputusan-tertunda.md` #4 Relatif terhadap M5.1

**Sumber Paksaan**
Entri #4 (skema `DataVisualisasi` M4.5 untuk 3 label selain `tren`/`nilai_tunggal`) py pemicu peninjauan ulang literal "Milestone 5.x (Observability Dashboard) benar-benar mulai" — dan M5.1 adalah milestone pertama PIC 5 yang benar-benar dimulai.

**Keputusan yang Diikuti**
Trigger dinyatakan terpicu (dicatat di sini sebagai bukti), tapi TIDAK ditindaklanjuti secara substantif dalam M5.1 — karena `DataVisualisasi` adalah skema JAWABAN chatbot (dikonsumsi Next.js dashboard publik, M5.2-5.4), sedangkan M5.1 murni memvisualisasikan data trace/span observability lewat Grafana (skema `traces`/`spans`, sama sekali berbeda). Revisit substantif entri #4 tetap ditunda ke M5.2, saat kebutuhan chart library Next.js benar-benar konkret.

**Catatan Ketergantungan**
Kalau M5.2 dimulai dan entri #4 tetap belum direvisit, itu jadi gap yang perlu ditangani PIC 5 di sana — dicatat sebagai follow-up di `report.md` M5.1 Bagian 6.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Merevisit skema `DataVisualisasi` di M5.1 juga** — ditolak: M5.1 sama sekali tidak menyentuh data itu, revisit tanpa kebutuhan konkret hanya akan jadi spekulasi, melanggar prinsip "jangan membangun kapabilitas di luar cakupan yang eksplisit dibutuhkan".

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Hosting Grafana — Self-hosted vs Grafana Cloud | A | Plan |
| 2 | Edisi dan Versi Image Grafana | B | Plan |
| 3 | Provisioning-as-Code untuk Datasource dan Dashboard | B | Plan |
| 4 | spanmetricsconnector di Collector — Pipeline, Dimension, Verifikasi Nama Metrik | B | Plan (riset) → Checkpoint 3 |
| 5 | Sumber Data Panel "Distribusi Status" | B | Plan (riset) → Checkpoint 6 |
| 6 | Kredensial Admin Grafana | B | Checkpoint 2 |
| 7 | Mekanisme Verifikasi KK1 dan KK2 — Turn Nyata via HTTP | B | Checkpoint 4, 6 |
| 8 | Skenario Uji Terkontrol untuk KK2 | B | Checkpoint 6 |
| 9 | Status `docs/keputusan-tertunda.md` #4 Relatif terhadap M5.1 | B | Plan |
