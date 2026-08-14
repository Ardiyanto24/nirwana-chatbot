# Logs — Milestone 1.1: Penyiapan OTel Collector sebagai Fondasi Observability Bersama

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

---

## Checkpoint 1 — Inisialisasi Proyek Python (uv)

**Mulai:** 2026-08-14 15:10 · **Selesai:** 2026-08-14 15:20

### Task 1 — Inisialisasi `pyproject.toml` via `uv init`

**Kesesuaian dengan plan:** Menyimpang dari plan, dikoreksi di tempat — lihat "Temuan" dan "Diagnosis dan Perbaikan" di bawah.

**Apa yang dilakukan**
`uv` belum terinstal di lingkungan kerja (`uv --version` gagal baik di Bash maupun PowerShell). Diinstal via `winget install --id=astral-sh.uv -e` (v0.12.4), berhasil. Karena PATH belum ter-refresh di sesi shell yang sama, seluruh pemanggilan `uv` selanjutnya di checkpoint ini memakai path penuh `$env:LOCALAPPDATA\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`.

Percobaan pertama: `uv init --name nirwana-chatbot --python 3.13` (tanpa flag layout eksplisit).

**Temuan**
Percobaan pertama ternyata membuat `src/nirwana_chatbot/__init__.py` (src-layout package) beserta `pyproject.toml` dengan `[build-system]` (`uv_build`) dan `[project.scripts]` entry point — artinya `uv init` default di versi ini men-setup proyek sebagai package Python yang bisa di-build, termasuk mengambil keputusan struktur `src/nirwana_chatbot/`. Ini melanggar Batasan Mengikat di plan: struktur `src/` sengaja ditunda ke awal Milestone 1.2, dan Milestone 1.1 tidak boleh diam-diam memutuskannya.

**Error/Kegagalan (jika ada)**
Tidak ada error teknis — ini kesalahan asumsi flag default `uv init`, bukan kegagalan perintah.

**Diagnosis dan Perbaikan (jika ada error)**
Dihapus seluruh output percobaan pertama (`src/`, `README.md`, `pyproject.toml`, `.python-version` — semuanya masih untracked git, aman dihapus, dikonfirmasi via `git status --short` sebelum menghapus). Dijalankan ulang dengan `uv init --bare --name nirwana-chatbot --description "AI Chatbot RBAC backend - Nirwana Hospitality Group" --python 3.13 --vcs none` — `--bare` membuat `pyproject.toml` minimal saja (tanpa `src/`, tanpa `[build-system]`, tanpa `README.md`), sesuai kebutuhan: proyek ini bukan package yang di-build/didistribusikan, dan struktur `src/` memang belum jadi cakupan milestone ini.

**Hasil Verifikasi**
`pyproject.toml` hasil `--bare` hanya berisi `[project]` (name, version, description, requires-python, dependencies) — tidak ada `src/`, tidak ada `[build-system]`. Dikonfirmasi via `cat pyproject.toml` dan `ls -la` (tidak ada folder `src/` di root).

**Commit:** `f048cb0` — `chore(milestone-1.1): inisialisasi proyek python dengan uv`

---

### Task 2 — Tambah dependency OTel

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv add opentelemetry-sdk opentelemetry-api opentelemetry-exporter-otlp-proto-grpc`.

**Temuan**
`uv` otomatis membuat `.venv` baru dan resolve 11 paket (termasuk transitive dependencies: `grpcio`, `protobuf`, `googleapis-common-protos`, `opentelemetry-semantic-conventions`, `opentelemetry-proto`, `opentelemetry-exporter-otlp-proto-common`, `typing-extensions`). Paket `opentelemetry-semantic-conventions==0.65b0` ikut terpasang sebagai transitive dependency — ini akan berguna langsung di Checkpoint 3 untuk mengunci versi konvensi atribut GenAI, karena paket ini yang menyediakan definisi atribut `gen_ai.*` resmi.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Output `uv add` menunjukkan 10 paket ter-install tanpa error, `uv.lock` ter-generate.

**Commit:** `f048cb0` — `chore(milestone-1.1): inisialisasi proyek python dengan uv`

---

### Task 3 — Verifikasi `uv sync` bersih

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`.venv` dihapus (`rm -rf .venv`), lalu `uv sync` dijalankan ulang dari `uv.lock`, diikuti `uv run python -c "import opentelemetry; print(...)"`.

**Temuan**
`uv sync` dari lockfile berhasil rebuild `.venv` dan install 10 paket persis sama seperti sebelumnya (versi terkunci konsisten), dalam waktu jauh lebih singkat (162ms install, dibanding beberapa detik saat `uv add` pertama kali karena harus resolve+download).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Output `uv run python -c "import opentelemetry; ..."` mencetak `opentelemetry import OK, version module loaded` tanpa exception.

**Commit:** `f048cb0` — `chore(milestone-1.1): inisialisasi proyek python dengan uv`

---

### Task 3a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri logs di atas ditulis. `.venv/.gitignore` dikonfirmasi otomatis dibuat oleh `uv` berisi `*` (self-exclude), sehingga `.venv` tidak perlu ditambahkan manual ke `.gitignore` root — dikonfirmasi lewat `git status --short` yang hanya menampilkan `pyproject.toml` dan `uv.lock` sebagai untracked baru (tidak ada jejak `.venv`).

**Temuan**
`.gitignore` root sudah ada sebelumnya berisi entri tidak terkait Python (`.env`, `.agents/`, `.claude/`, `skills-lock.json`, `CLAUDE.md`) — tidak diubah, di luar cakupan checkpoint ini.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`git status --short` sebelum commit menunjukkan hanya `pyproject.toml` dan `uv.lock` sebagai file baru yang relevan (plus `.gitignore` modified dan `docs/CLAUDE.md` deleted, keduanya pre-existing dari sebelum sesi ini dan di luar cakupan milestone ini — tidak ikut di-stage).

**Commit:** `f048cb0` — `chore(milestone-1.1): inisialisasi proyek python dengan uv`

---

## Checkpoint 2 — Docker Compose: Collector + Jaeger + Prometheus

**Mulai:** 2026-08-14 15:22 · **Selesai:** 2026-08-14 15:35

### Task 4 — Tulis `otel-collector-config.yaml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/otel-collector-config.yaml`: receiver `otlp` (grpc `0.0.0.0:4317`, http `0.0.0.0:4318`), processor `memory_limiter` (limit 512MiB/spike 128MiB) + `batch` + `attributes` (upsert `deployment.environment=local-dev` sebagai contoh enrichment), exporter jalur privat (trace ke Jaeger via OTLP, metrics via exporter `prometheus` di `:8889`), dan blok komentar eksplisit untuk slot exporter publik PIC 6 (tidak diaktifkan, hanya dokumentasi bentuknya).

**Temuan**
Jaeger all-in-one modern (image `latest`) sudah punya receiver OTLP bawaan di port 4317/4318 di dalam network Docker — jadi trace dikirim dari Collector ke Jaeger lewat OTLP juga (`otlp_grpc/jaeger` exporter mengarah ke `jaeger:4317`), bukan format lama Jaeger-native (`jaeger` exporter/thrift). Port OTLP milik container `jaeger` sengaja **tidak** dipetakan ke host, supaya Collector tetap jadi satu-satunya titik penerima OTLP dari luar (kontrak "titik penerima tunggal").

**Error/Kegagalan (jika ada)**
Tidak ada saat penulisan file.

**Hasil Verifikasi**
*(digabung dengan Task 7, lihat di bawah — file config baru bisa diverifikasi setelah container jalan)*

**Commit:** *(lihat Task 7a)*

---

### Task 5 — Tulis `prometheus.yml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/prometheus.yml`: satu scrape job `otel-collector` mengarah ke `otel-collector:8889` (endpoint exporter `prometheus` di Collector), interval 15s.

**Temuan** Tidak ada. **Error/Kegagalan** Tidak ada.

**Hasil Verifikasi:** *(digabung dengan Task 7)*

**Commit:** *(lihat Task 7a)*

---

### Task 6 — Tulis `docker-compose.yml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/docker-compose.yml`: service `otel-collector` (image `otel/opentelemetry-collector-contrib:latest`, port host 4317/4318/8889), `jaeger` (image `jaegertracing/all-in-one:latest`, hanya port UI 16686 dipetakan ke host), `prometheus` (image `prom/prometheus:latest`, port UI 9090). Tag image sengaja `latest` (bukan versi tertentu yang mungkin sudah tidak ada saat dijalankan) karena ini stack verifikasi lokal, bukan deployment produksi — dicatat sebagai keputusan turunan implementasi bebas.

**Temuan** Tidak ada. **Error/Kegagalan** Tidak ada.

**Hasil Verifikasi:** *(digabung dengan Task 7)*

**Commit:** *(lihat Task 7a)*

---

### Task 7 — Jalankan `docker compose up -d`, verifikasi service

**Kesesuaian dengan plan:** Sesuai plan, dengan satu perbaikan kecil di tengah jalan (lihat Temuan).

**Apa yang dilakukan**
`docker compose up -d` dijalankan (image ditarik pertama kali, berjalan di background ~3 menit karena unduhan). Setelah selesai: `docker compose ps` dicek, log `otel-collector` dicek, dan Jaeger UI (`curl -o /dev/null -w "%{http_code}" http://localhost:16686`) serta Prometheus UI (`http://localhost:9090`) dicek reachability-nya.

**Temuan**
Log startup pertama Collector menampilkan warning: `"otlp" alias is deprecated; use "otlp_grpc" instead` untuk exporter `otlp/jaeger` — versi `otel/opentelemetry-collector-contrib:latest` yang tertarik adalah v0.158.0, di mana alias exporter type `otlp` (untuk gRPC) sudah deprecated. Diperbaiki dengan mengubah component id exporter dari `otlp/jaeger` menjadi `otlp_grpc/jaeger` di `otel-collector-config.yaml` (Task 4) dan referensinya di pipeline `traces`, lalu `docker compose restart otel-collector`. Log startup kedua tidak lagi menampilkan warning tersebut.

**Error/Kegagalan (jika ada)**
Warning deprecation di atas (bukan error fatal, container tetap "Everything is ready" pada percobaan pertama) — tetap diperbaiki karena dasarnya jelas (pesan warning eksplisit menyebut pengganti yang benar) dan murah diperbaiki sebelum commit, menghindari technical debt di titik paling awal proyek.

**Diagnosis dan Perbaikan**
Lihat Temuan di atas — perbaikan berupa rename component id, bukan perubahan perilaku fungsional.

**Hasil Verifikasi**
- `docker compose ps`: ketiga service (`nirwana-otel-collector`, `nirwana-jaeger`, `nirwana-prometheus`) berstatus `Up`.
- Log `otel-collector` (setelah fix): tidak ada baris `error`/`warn` konfigurasi, diakhiri `"Everything is ready. Begin running and processing data."` untuk kedua receiver (grpc `:4317`, http `:4318`).
- Jaeger UI (`http://localhost:16686`): HTTP 200.
- Prometheus UI (`http://localhost:9090`): HTTP 302 (redirect ke `/graph`, perilaku normal Prometheus di root path).

**Commit:** *(lihat Task 7a)*

---

### Task 7a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 2 di atas ditulis. File di-stage: `infra/observability/{docker-compose.yml,otel-collector-config.yaml,prometheus.yml}` dan `milestones/1.1-fondasi-collector/logs.md`.

**Hasil Verifikasi**
`git status --short` dicek sebelum staging untuk memastikan hanya file Checkpoint 2 yang ikut (tidak termasuk `.gitignore`/`docs/CLAUDE.md` yang pre-existing di luar cakupan).

**Commit:** *(diisi setelah commit dieksekusi)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — penyimpangan Task 1 (flag `uv init`) dan Task 7 (rename exporter `otlp`→`otlp_grpc`) adalah koreksi di dalam task yang sudah direncanakan, bukan task/checkpoint baru di luar plan.
