# Logs — Milestone 5.1: Membangun Dashboard Grafana untuk Trace dan Metrics

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Sebelum plan ditulis, dilakukan riset 3-jalur paralel (2 agent Explore + 1 agent Plan) mencakup: isi lengkap `docs/02-implementation-plan/rancangan-observability-dashboard.md` dan bagian relevan `docs/01-architecture/rancangan-observability-ai-chatbot.md`, state nyata `infra/observability/` (docker-compose, config Collector, Prometheus), kode instrumentasi existing (`src/observability/`, span `invoke_agent`, `error.type`, `prompt.id`), `docs/keputusan-tertunda.md` dan `docs/keterbatasan-diterima.md`, serta struktur ketiga template governance. Temuan riset dipakai agent Plan untuk mendesain mekanisme konkret 4 panel M5.1, lalu satu pertanyaan genuinely-terbuka (hosting Grafana) diajukan ke user lewat `AskUserQuestion` sebelum plan final ditulis dan disetujui (`ExitPlanMode`). Setelah plan disetujui, `milestones/5.1-membangun-dashboard-grafana/decisions.md` ditulis berisi 9 entri keputusan (1 Jenis A genuinely-terbuka, 8 Jenis B preseden/forced) mengikuti `template-decisions.md`.

**Temuan**
- Gap teknis material: `otel-collector-config.yaml` saat ini tidak punya `spanmetricsconnector` — 3 dari 4 panel M5.1 (latency per layer, distribusi status, frekuensi error.type) butuh data agregat time-series yang hanya tersedia lewat Prometheus, bukan lewat Jaeger datasource native (yang hanya mendukung list-of-traces, bukan agregasi).
- Dimension yang dibutuhkan spanmetrics (`prompt.id`, `error.type`) sudah terpasang di instrumentasi existing (15 lokasi dan 9 file berturut-turut) — tidak perlu menyentuh kode 9 layer PIC 1-4.
- Sinyal status level-turn positif (mencakup `berhasil`) hanya tersedia lewat atribut `riwayat.status` pada span `riwayat.simpan` (`src/orchestration/riwayat_percakapan.py:58`, dibangun M7.18) — `error.type` di layer lain hanya terpasang di jalur kegagalan.
- `docs/keputusan-tertunda.md` #4 py trigger literal "Milestone 5.x mulai" yang secara teknis terpicu oleh dimulainya M5.1, tapi item itu (skema `DataVisualisasi`) tidak actionable dalam lingkup M5.1 sendiri (beda domain data dari trace/span Grafana) — dicatat sebagai klarifikasi scope di Keputusan 9, revisit substantif tetap ditunda ke M5.2.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` lengkap dengan 9 entri, setiap entri py section "Opsi yang Dipertimbangkan tapi Ditolak" terisi (termasuk entri forced yang menyatakan eksplisit "tidak ada alternatif... forced by X" bila relevan), dan Daftar Isi Keputusan di akhir dokumen mencantumkan seluruh 9 entri dengan Checkpoint Terkait.

**Commit:** `6ba1651` — `docs(milestone-5.1): keputusan desain dashboard Grafana`

---

## Checkpoint 2 — Fondasi Grafana (Service + Datasource)

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 2 — Tambah service Grafana + provisioning datasource

**Kesesuaian dengan plan:** Menyimpang dari plan pada satu detail: host port Grafana dipindah dari `3000:3000` (rencana awal) ke `3001:3000` — lihat "Temuan" dan "Diagnosis dan Perbaikan" di bawah. Sisanya (image `grafana-oss:latest`, provisioning-as-code, kredensial via `.env`) sesuai plan/`decisions.md` Keputusan 2, 3, 6.

**Apa yang dilakukan**
- Tambah service `grafana` ke `infra/observability/docker-compose.yml` (image `grafana/grafana-oss:latest`, volume named `grafana-data` + bind mount `./grafana/provisioning` dan `./grafana/dashboards` read-only, `depends_on: [jaeger, prometheus]`).
- Tulis `infra/observability/grafana/provisioning/datasources/datasources.yaml` (datasource Jaeger `http://jaeger:16686` + Prometheus `http://prometheus:9090`, `access: proxy`, `editable: false` untuk menegaskan sumber kebenaran ada di file, bukan UI).
- Tambah `GRAFANA_ADMIN_PASSWORD=` ke `.env.example` (kosong, dengan komentar) dan isi nilai nyata (random, `secrets.token_urlsafe(18)`) di `.env` lokal.
- Update `infra/observability/README.md`: tabel service, section baru "Grafana (Milestone 5.1)".
- Jalankan Docker Desktop (belum aktif di awal sesi kerja), tunggu engine siap, lalu `docker compose --env-file ../../.env up -d`.

**Temuan**
- `docker compose ps`/`docker inspect` menunjukkan container `nirwana-grafana` start SUKSES tapi port host `3000` **tidak terpublish** (`NetworkSettings.Ports` kosong meski `HostConfig.PortBindings` menyatakan intent `3000`) — tanpa error eksplisit dari `docker compose up`.
- Investigasi (`Get-NetTCPConnection -LocalPort 3000`, `docker ps` native): port 3000 di host Windows sudah dipakai proses Docker Desktop lain (`com.docker.backend`/`wslrelay`) yang membungkus container `k8s_grafana_grafana-...` — sebuah cluster Kubernetes lokal (Docker Desktop) milik project LAIN yang tidak berkaitan (`churn-prediction`, monitoring stack) yang kebetulan juga menjalankan Grafana di port 3000. Ini persis risiko yang sudah diantisipasi di plan ("Risiko & Mitigasi": "Port 3000 bentrok dengan proses lain di mesin developer").
- Container/proses tersebut milik environment lain di luar cakupan project ini — TIDAK disentuh/dimatikan.

**Error/Kegagalan (jika ada)**
Tidak ada error eksplisit dari Docker — kegagalan silent (port binding tidak terpasang tanpa pesan error di `docker compose up` maupun `docker logs`).

**Diagnosis dan Perbaikan (jika ada error)**
Diagnosis: `Get-NetTCPConnection -LocalPort 3000` mengonfirmasi port sudah terpakai oleh proses lain di host sebelum Grafana kita mencoba bind. Perbaikan: ganti port host di `docker-compose.yml` dari `3000:3000` ke `3001:3000` (port container tetap 3000, hanya host mapping yang berubah), verifikasi `3001` bebas terlebih dahulu, lalu `docker compose up -d grafana` untuk recreate container dengan mapping baru. `README.md` dan `.env.example` diperbarui mengikuti port baru ini.

**Hasil Verifikasi**
- `docker inspect nirwana-grafana --format '{{json .NetworkSettings.Ports}}'` → `{"3000/tcp":[{"HostIp":"0.0.0.0","HostPort":"3001"},{"HostIp":"::","HostPort":"3001"}]}` — port terpasang benar.
- `curl http://localhost:3001/api/health` → `200`, body `{"database":"ok","version":"13.0.2","commit":"3fcdbc5a"}`.
- `GET /api/datasources` (auth admin) menunjukkan 2 datasource (`Jaeger`, `Prometheus`), keduanya `"readOnly":true` (bukti provisioning-as-code, bukan input manual UI).
- Health check per-datasource: Jaeger → `{"message":"Data source is working","status":"OK"}`; Prometheus → `{"status":"OK","message":"Successfully queried the Prometheus API."}` — bukti koneksi nyata ke kedua sumber data, bukan asumsi config benar.

**Commit:** `01df9c7` — `feat(milestone-5.1): tambah service Grafana self-hosted + provisioning datasource`; `a6303ac` — `docs(milestone-5.1): logs checkpoint 2`

---

## Checkpoint 3 — spanmetricsconnector di Collector

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 3 — Tambah connector spanmetrics ke otel-collector-config.yaml

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian nama komponen (lihat Temuan) yang tidak mengubah desain pipeline itu sendiri.

**Apa yang dilakukan**
Tambah section `connectors.spanmetrics` (dimension `prompt.id` + `error.type`, `metrics_flush_interval: 15s`) dan dua pipeline baru ke `otel-collector-config.yaml`: `traces/spanmetrics` (receiver `otlp` sama, exporter → connector) dan `metrics/spanmetrics` (receiver connector, exporter `prometheus` reuse existing). Pipeline `traces`/`metrics` existing tidak diubah.

**Temuan**
Restart pertama Collector memunculkan warning: `"spanmetrics" alias is deprecated; use "span_metrics" instead`. Connector tetap berfungsi (bukan error fatal), tapi nama alias ini sudah ditandai upstream untuk dihapus di rilis mendatang — dibiarkan berarti menanam utang teknis laten yang akan pecah begitu image `latest` naik versi. Diperbaiki langsung dalam checkpoint yang sama (bukan ditunda): rename component id `spanmetrics` → `span_metrics` di `connectors:` dan referensi `exporters`/`receivers` pipeline (nama pipeline `traces/spanmetrics`/`metrics/spanmetrics` sendiri TIDAK diganti, itu label pipeline bebas-nama, bukan alias connector).

**Error/Kegagalan (jika ada)**
Warning deprecation (bukan error fatal) — lihat Temuan. Tidak ada error lain.

**Diagnosis dan Perbaikan (jika ada error)**
Diagnosis: dibaca langsung dari log Collector (`docker logs nirwana-otel-collector`), pesan warning eksplisit menyebut nama pengganti. Perbaikan: `sed` rename `spanmetrics`→`span_metrics` di scope `connectors:`/`exporters:`/`receivers:` component id, restart Collector, konfirmasi log startup kedua tidak lagi memunculkan warning tersebut (`"otelcol.component.id": "span_metrics"` bersih tanpa baris `warn`).

**Hasil Verifikasi**
Log startup Collector setelah perbaikan bersih dari warning; `spanmetricsconnector` berhasil "Building"+"Starting" dengan component id `span_metrics`.

**Commit:** `4684cb7` — `feat(milestone-5.1): tambah spanmetricsconnector ke otel-collector-config` (digabung dengan Task 4, satu perubahan config)

---

### Task 4 — Verifikasi nyata: span dummy → metrik Prometheus

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Jalankan `uv run python infra/observability/smoke_test/send_dummy_span.py` (trace_id `58b314e14592b797d401be814379c5d3`), tunggu `metrics_flush_interval` (15s) + siklus scrape Prometheus (15s), lalu query `GET /api/v1/label/__name__/values` dan `GET /api/v1/query?query=traces_span_metrics_calls_total` di Prometheus API.

**Temuan**
Nama metrik persis yang dihasilkan (dicatat sesuai Keputusan 4 `decisions.md` — dikonfirmasi empiris, bukan diasumsikan): `traces_span_metrics_calls_total` (counter) dan `traces_span_metrics_duration_milliseconds_bucket`/`_count`/`_sum` (histogram). Label yang muncul otomatis: `span_name`, `span_kind`, `status_code`, `service_name`, `job`, `instance` — dimension custom `prompt.id`/`error.type` TIDAK muncul di span dummy ini karena `send_dummy_span.py` (emitter smoke test generik) memang tidak memasang atribut itu; dimension custom akan muncul saat turn nyata (Checkpoint 4/6) dari kode layer yang genuinely memasang `prompt.id`/`error.type`.

**Error/Kegagalan (jika ada)**
Tidak ada. (Query pertama sesaat setelah span dikirim sempat belum menunjukkan metrik baru — bukan kegagalan, murni belum lewat satu siklus flush+scrape; muncul benar setelah menunggu lebih lama.)

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`GET /api/v1/label/__name__/values` menampilkan 4 metrik baru (`traces_span_metrics_calls_total`, `traces_span_metrics_duration_milliseconds_{bucket,count,sum}`) setelah span dummy dikirim — bukti pipeline `traces/spanmetrics`→`metrics/spanmetrics` benar-benar mengalir data nyata, bukan hanya valid secara syntax config.

**Commit:** `4684cb7` (sama dengan Task 3); `94409d1` — `docs(milestone-5.1): logs checkpoint 3`

---

## Checkpoint 4 — Panel Daftar Trace + Waterfall (KK1)

**Mulai:** 2026-08-20 · **Selesai:** *(belum, in progress)*

### Task 5 — Buat dashboard JSON dengan panel Daftar Trace + Detail Trace/Waterfall

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `infra/observability/grafana/provisioning/dashboards/dashboards.yaml` (provider file-based, path `/var/lib/grafana/dashboards`) dan `infra/observability/grafana/dashboards/observability.json` (dashboard `nirwana-chatbot-observability`, 2 panel tipe `traces` berdatasource Jaeger `uid=PC9A941E8F2E49454`: "Daftar Trace (Search)" dengan variable `$tags` untuk filter, dan "Detail Trace / Waterfall" dengan variable `$traceId`). Hapus placeholder `.gitkeep` di `grafana/dashboards/` (sudah terisi file nyata). Restart container `grafana` agar provider baru termuat.

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`GET /api/search?query=` (auth admin) menunjukkan dashboard `nirwana-chatbot-observability` ter-load lewat provisioning — bukti file JSON valid dan provider terbaca.

**Commit:** *(digabung dengan Task 6, satu checkpoint)*

---

### Task 6 — Verifikasi nyata KK1: turn sungguhan → trace di Grafana

**Kesesuaian dengan plan:** Sesuai plan pada tujuan akhir, tapi mengalami kejadian tak terduga di percobaan pertama (lihat Error/Kegagalan) — konsisten pola `docs/keterbatasan-diterima.md` #7 yang sudah berulang kali terjadi di milestone lain (M7.12, M7.16, M7.17).

**Apa yang dilakukan**
Jalankan `chatbot_api` lokal (`nirwana-database/scripts/chatbot_api/`, `python -m uvicorn main:app --host 127.0.0.1 --port 8000`, terverifikasi `GET /health` → `200`) dan server aplikasi (`uv run uvicorn src.main:app --port 8001`, terverifikasi `GET /docs` → `200`). Kirim `POST /v1/turns` dengan payload contoh nyata dari `docs/panduan-integrasi-frontend.md` Bagian 3.1 (`session_id="milestone-5.1-cp4-kk1"`, pertanyaan occupancy rate Juni 2026, `role_title="General Manager"`).

**Temuan**
Percobaan pertama HANG >17 menit tanpa respons — jauh melampaui "beberapa menit" yang didokumentasikan wajar. Diagnostik dilakukan SEBELUM menyimpulkan gagal (dipicu juga oleh pertanyaan user yang meragukan apakah `chatbot_api` benar-benar aktif): `Get-NetTCPConnection`+`Get-Process` mengonfirmasi KEDUA server genuinely listening di port yang benar dengan PID yang cocok persis log startup masing-masing (`chatbot_api` PID 3808 di :8000, app PID 17904 di :8001), dan ADA koneksi `Established` dari client curl ke :8001 — membuktikan request benar-benar sampai dan diproses server, bukan gagal connect. `chatbot_api.log` sepanjang hang hanya berisi 2 baris health-check (tidak ada panggilan data) — bukti hang terjadi SEBELUM mencapai layer Execution (di salah satu 7 layer sebelumnya: Input/Context Resolution/Decomposition/Domain Gate/Retriever/Query Engine/Verification Gate).

**Error/Kegagalan (jika ada)**
Hang tanpa exception pada percobaan pertama (`session_id="milestone-5.1-cp4-kk1"`) — tidak ada pesan error, koneksi TCP tetap `Established` tanpa data. Cocok pola `docs/keterbatasan-diterima.md` #7.

**Diagnosis dan Perbaikan (jika ada error)**
Diagnosis dilakukan bertahap, didorong lebih jauh dari preseden M7.16 karena percobaan retry sederhana TIDAK berhasil:
1. Proses request lama (percobaan 1) di-stop (`TaskStop` pada task background curl), dikonfirmasi koneksi `Established` di :8001 hilang. Proses server aplikasi (PID 17904) di-restart bersih (`Stop-Process -Force` + relaunch `uvicorn`). Retry dengan `session_id` baru (`milestone-5.1-cp4-kk1-retry1`) + `--max-time 240` di sisi client (percobaan 2) — **juga habis waktu** (`curl_exit=28`, `http_status=000`), `chatbot_api.log` masih hanya 2 baris health-check (belum mencapai Execution).
2. `Get-Process`+`Get-NetTCPConnection` terhadap PID server yang baru (21992) menunjukkan CPU 5.9s terpakai dan koneksi `Established` nyata ke `104.18.2.115:443` (×3, IP di balik Cloudflare — konsisten OpenRouter) serta ke `54.255.219.82:5432` (Postgres/Supabase, ekspektasi normal) — proses genuinely aktif menunggu jawaban LLM, bukan freeze total.
3. Isolasi lebih dalam: script Python terpisah (`test_openrouter_single_call.py`, di luar pipeline) memanggil `get_openrouter_client()` untuk SATU chat completion ringan (`qwen/qwen3-32b`, 1 prompt pendek) — hang >120 detik (`timeout 120` shell membunuh proses, exit 124), TANPA exception meski `timeout=90.0` eksplisit terpasang di client — mengonfirmasi timeout SDK sendiri tidak terpicu.
4. Isolasi ke level paling dasar: `curl` LANGSUNG ke `https://openrouter.ai/api/v1/chat/completions` (bypass SDK/`openai` package Python sepenuhnya) dengan API key asli — **juga hang**, `--max-time 60` habis (`curl_exit=28`) tanpa body respons lengkap. Sebagai pembanding kontrol: `GET https://openrouter.ai/api/v1/models` (endpoint non-inference) di jendela waktu yang sama merespons `200 OK` cepat dan normal (DNS resolve bersih via `nslookup`, TLS handshake sukses).
5. Kesimpulan: root cause genuinely infra backend OpenRouter untuk endpoint completions saat itu — BUKAN bug kode/konfigurasi project ini (dibuktikan negatif di setiap lapisan: pipeline, SDK, raw HTTP). Dicatat sebagai recurrence `docs/keterbatasan-diterima.md` #7 (isolasi lebih dalam dari recurrence M7.16 sebelumnya — kali ini sampai level `curl` mentah).

Ditanyakan ke user (`AskUserQuestion`) bagaimana melanjutkan mengingat retry sederhana sudah 2× gagal dan root cause terbukti eksternal. **Keputusan user**: kerjakan bagian yang TIDAK butuh panggilan LLM sekarang (panel dashboard, config), verifikasi real-turn KK1/KK2 ditunda sampai OpenRouter stabil — dicatat eksplisit, BUKAN diam-diam dilewati. Milestone TETAP berstatus belum selesai sampai verifikasi nyata benar-benar terlaksana.

**Hasil Verifikasi**
BELUM TERPENUHI — diblokir prasyarat eksternal (OpenRouter). Task 6 (dan turunannya Task 8/Task 10 di Checkpoint 5/6) ditandai **BLOCKED-EXTERNAL**, ditinjau ulang begitu OpenRouter kembali stabil. Bukan kegagalan implementasi M5.1 — seluruh komponen non-LLM (dashboard, datasource, spanmetricsconnector) sudah terbukti bekerja (Checkpoint 1-3, Task 5).

**Commit:** tidak ada perubahan kode untuk task ini sendiri (murni diagnosis) — dicatat bersama commit `docs` checkpoint ini

---

### Catatan Penyimpangan — Mengerjakan Task Buildable Mendahului Verifikasinya (atas instruksi user)

**Kesesuaian dengan plan:** Menyimpang dari urutan checkpoint sekuensial ketat CLAUDE.md ("jangan lanjut ke checkpoint berikutnya jika checkpoint sekarang belum diverifikasi") — dilakukan ATAS INSTRUKSI EKSPLISIT user setelah `AskUserQuestion` ("kerjakan apa yang bisa dikerjakan, milestone berarti statusnya belum selesai. catat ini untuk real test llm nya akan dilakukan setelah kondisi openrouter stabil"). Bagian TASK (definisi panel) dari Checkpoint 5 (Task 7) dan Checkpoint 6 (Task 9) dikerjakan sekarang karena murni config, TIDAK butuh panggilan LLM — bagian VERIFIKASI (Task 8, Task 10) tetap menunggu turn nyata, sama seperti Task 6.

**Apa yang dilakukan**
1. **Temuan gap saat menyiapkan panel "Distribusi Status"**: `otel-collector-config.yaml` Checkpoint 3 hanya mendaftarkan dimension `prompt.id`+`error.type` di `span_metrics` — TIDAK termasuk `riwayat.status`, padahal `decisions.md` Keputusan 5 sudah menyatakan itu sumber panel ini. Diperbaiki: tambah `- name: riwayat.status` ke `dimensions:`, restart Collector, log startup bersih tanpa error.
2. Tambah 3 panel ke `infra/observability/grafana/dashboards/observability.json`: "Latency per Layer (p95)" (timeseries, Prometheus, `histogram_quantile(0.95, sum(rate(traces_span_metrics_duration_milliseconds_bucket[5m])) by (le, span_name))`), "Distribusi Status (per turn)" (piechart, `sum(traces_span_metrics_calls_total{span_name="riwayat.simpan"}) by (riwayat_status)`), "Frekuensi error.type" (barchart, `sum(traces_span_metrics_calls_total{error_type!=""}) by (error_type)`).
3. Restart Grafana, verifikasi kelima panel (2 dari Task 5 + 3 baru) ter-load lewat `GET /api/dashboards/uid/nirwana-chatbot-observability`.

**Temuan**
Gap dimension `riwayat.status` di atas — satu-satunya temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Lihat poin 1 "Apa yang dilakukan" di atas.

**Hasil Verifikasi**
`GET /api/dashboards/uid/nirwana-chatbot-observability` (auth admin) mengembalikan `200` dengan 5 panel: `traces`×2 (Task 5, KK1), `timeseries` (Task 7, latency), `piechart`+`barchart` (Task 9, KK2) — bukti config/provisioning valid dan diterima Grafana. **BUKAN bukti data benar** (belum ada data nyata mengalir karena Task 6/8/10 masih BLOCKED-EXTERNAL) — panel-panel ini akan tampil kosong sampai turn nyata berhasil dan diverifikasi.

**Commit:** `f4de0bb` — `feat(milestone-5.1): panel daftar trace, waterfall, latency, distribusi status, error.type`

---
