# Observability — Fondasi Bersama (Milestone 1.1) + Dashboard Grafana (Milestone 5.1)

Fondasi OTel Collector lokal yang dipakai bersama oleh seluruh 9 layer AI Chatbot (PIC 1-4), plus dashboard Grafana self-hosted (PIC 5, Milestone 5.1) di atasnya. Dokumen ini untuk PIC lain yang perlu mengarahkan instrumentasi mereka ke sini — bukan dokumentasi arsitektur (lihat `docs/01-architecture/rancangan-observability-ai-chatbot.md` untuk itu).

## Menjalankan Stack

Isi `GRAFANA_ADMIN_PASSWORD` di `.env` (lihat `.env.example`) sebelum menjalankan stack.

```bash
cd infra/observability
docker compose up -d
```

Empat service akan berjalan:

| Service | Fungsi | Akses |
|---|---|---|
| `otel-collector` | Titik penerima OTLP **tunggal** untuk seluruh 9 layer | grpc `localhost:4317`, http `localhost:4318` |
| `jaeger` | Penyimpanan & UI trace (jalur privat) | UI `http://localhost:16686` |
| `prometheus` | Penyimpanan & UI metrics (jalur privat) | UI `http://localhost:9090` |
| `grafana` | Dashboard privat di atas Jaeger+Prometheus (Milestone 5.1) | UI `http://localhost:3001` (login `admin`/`$GRAFANA_ADMIN_PASSWORD`) — host port 3001, bukan 3000 default, karena 3000 dipakai proses lain di mesin developer (lihat `milestones/5.1-membangun-dashboard-grafana/logs.md` Checkpoint 2) |

Hentikan dengan `docker compose down` (dari folder yang sama).

## Grafana (Milestone 5.1)

Self-hosted, bukan Grafana Cloud (alasan lengkap: `milestones/5.1-membangun-dashboard-grafana/decisions.md` Keputusan 1) — Grafana Cloud hosted eksternal tidak bisa menjangkau Jaeger/Prometheus di jaringan Docker Compose lokal ini tanpa tunnel tambahan.

Datasource dan dashboard didefinisikan **provisioning-as-code** (Keputusan 3), bukan diklik manual lewat UI — file-nya di-commit git dan di-mount read-only ke container:
- `grafana/provisioning/datasources/datasources.yaml` — datasource Jaeger + Prometheus.
- `grafana/provisioning/dashboards/dashboards.yaml` + `grafana/dashboards/*.json` — dashboard panel.

Perubahan lewat UI Grafana saat debugging TIDAK persisten (hilang saat container restart, by design) — perubahan permanen wajib dituliskan balik ke file provisioning di atas.

## Endpoint yang Dipakai Instrumentasi Kamu (PIC 2-4)

Arahkan OTel SDK ke:
- **gRPC:** `localhost:4317` (direkomendasikan, dipakai skrip verifikasi di sini)
- **HTTP:** `localhost:4318`

Jangan membuat instance Collector sendiri — seluruh layer berbagi satu Collector ini. Kalau kamu menjalankan Collector ini di mesin/container berbeda dari kode instrumentasimu, ganti `localhost` dengan host yang sesuai.

## Pipeline Collector

Config: [`otel-collector-config.yaml`](otel-collector-config.yaml).

- **Trace:** `otlp` receiver → `memory_limiter`, `batch`, `attributes` (enrichment) → exporter `otlp_grpc/jaeger` (jalur privat, aktif).
- **Metrics:** `otlp` receiver → processor sama → exporter `prometheus` di `:8889` (di-scrape `prometheus.yml`, jalur privat, aktif).
- **Slot jalur publik (untuk PIC 6):** dikomentari eksplisit di `otel-collector-config.yaml`, belum aktif. Diisi Milestone 6.1 (`rancangan-custom-exporter-supabase.md`) dengan custom exporter Go ke Supabase — **jangan hapus komentarnya**, tinggal isi dan daftarkan ke pipeline `traces`.

## Versi Konvensi Atribut GenAI (`gen_ai.*`) yang Dikunci

Lihat [`src/observability/genai_semconv.py`](../../src/observability/genai_semconv.py) — modul ini adalah sumber kebenaran satu-satunya untuk nama atribut `gen_ai.*` yang dipakai proyek ini (dipindah dari `infra/observability/` ke `src/observability/` di Milestone 1.2, begitu struktur `src/` diputuskan). **Import konstantanya dari sini, jangan hardcode string `"gen_ai.xxx"` sendiri di kode masing-masing layer.**

Ringkasan status per 2026-08-14 (detail lengkap di `docs/keterbatasan-diterima.md` #1): governance spesifikasi GenAI baru pindah ke repo `open-telemetry/semantic-conventions-genai` (2026-06-12), belum ada rilis paket Python resmi di sana. Proyek ini memakai `opentelemetry-semantic-conventions==0.65b0` (dipin di `uv.lock`) sebagai sumber nilai string, dikonfirmasi identik dengan dokumentasi repo baru.

## Cara Verifikasi Instrumentasimu Benar-Benar Sampai

Cara paling cepat: jalankan salah satu skrip di [`smoke_test/`](smoke_test/) sebagai referensi pola, lalu adaptasi untuk layer-mu:

```bash
uv run python infra/observability/smoke_test/send_dummy_span.py
```

Skrip mencetak `trace_id=<hex>`. Cek langsung lewat Jaeger API (tanpa buka browser):

```bash
curl -s "http://localhost:16686/api/traces/<trace_id>"
```

Untuk metric, cek lewat Prometheus API:

```bash
curl -s "http://localhost:9090/api/v1/query?query=<nama_metric>"
```

Kalau trace/metric-mu muncul di sini, instrumentasimu sudah benar terhubung ke Collector yang sama dengan seluruh layer lain.

## Referensi

- `docs/01-architecture/rancangan-observability-ai-chatbot.md` — kontrak span per layer (Bagian 2), arsitektur pipeline (Bagian 3), skema Supabase (Bagian 4).
- `milestones/1.1-fondasi-collector/` — plan, decisions, logs, report milestone ini.
