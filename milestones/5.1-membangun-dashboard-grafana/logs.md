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

**Commit:** *(diisi setelah commit checkpoint ini)*

---
