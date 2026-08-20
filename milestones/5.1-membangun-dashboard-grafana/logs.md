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

**Commit:** *(diisi setelah commit checkpoint ini)*

---
