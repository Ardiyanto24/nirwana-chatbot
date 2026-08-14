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

**Commit:** `8c2e73d` — `feat(milestone-1.1): konfigurasi otel collector, jaeger, prometheus via docker compose`

---

### Task 5 — Tulis `prometheus.yml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/prometheus.yml`: satu scrape job `otel-collector` mengarah ke `otel-collector:8889` (endpoint exporter `prometheus` di Collector), interval 15s.

**Temuan** Tidak ada. **Error/Kegagalan** Tidak ada.

**Hasil Verifikasi:** *(digabung dengan Task 7)*

**Commit:** `8c2e73d` — `feat(milestone-1.1): konfigurasi otel collector, jaeger, prometheus via docker compose`

---

### Task 6 — Tulis `docker-compose.yml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/docker-compose.yml`: service `otel-collector` (image `otel/opentelemetry-collector-contrib:latest`, port host 4317/4318/8889), `jaeger` (image `jaegertracing/all-in-one:latest`, hanya port UI 16686 dipetakan ke host), `prometheus` (image `prom/prometheus:latest`, port UI 9090). Tag image sengaja `latest` (bukan versi tertentu yang mungkin sudah tidak ada saat dijalankan) karena ini stack verifikasi lokal, bukan deployment produksi — dicatat sebagai keputusan turunan implementasi bebas.

**Temuan** Tidak ada. **Error/Kegagalan** Tidak ada.

**Hasil Verifikasi:** *(digabung dengan Task 7)*

**Commit:** `8c2e73d` — `feat(milestone-1.1): konfigurasi otel collector, jaeger, prometheus via docker compose`

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

**Commit:** `8c2e73d` — `feat(milestone-1.1): konfigurasi otel collector, jaeger, prometheus via docker compose`

---

### Task 7a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 2 di atas ditulis. File di-stage: `infra/observability/{docker-compose.yml,otel-collector-config.yaml,prometheus.yml}` dan `milestones/1.1-fondasi-collector/logs.md`.

**Hasil Verifikasi**
`git status --short` dicek sebelum staging untuk memastikan hanya file Checkpoint 2 yang ikut (tidak termasuk `.gitignore`/`docs/CLAUDE.md` yang pre-existing di luar cakupan).

**Commit:** `8c2e73d` — `feat(milestone-1.1): konfigurasi otel collector, jaeger, prometheus via docker compose`

---

## Checkpoint 3 — Skrip Verifikasi Span/Metric Dummy + Kunci Versi GenAI Semconv

**Mulai:** 2026-08-14 15:40 · **Selesai:** 2026-08-14 16:10

### Task 8 — Cek versi terkini OTel GenAI Semantic Conventions

**Kesesuaian dengan plan:** Sesuai plan, tapi hasilnya jauh lebih signifikan dari yang dibayangkan saat plan ditulis — lihat Temuan.

**Apa yang dilakukan**
Diperiksa dulu paket `opentelemetry-semantic-conventions==0.65b0` yang sudah ter-install (transitive dependency dari Checkpoint 1). File `.venv/Lib/site-packages/opentelemetry/semconv/_incubating/attributes/gen_ai_attributes.py` dibaca langsung. Lalu dicari konfirmasi resmi lewat web search + fetch ke beberapa sumber: GitHub `open-telemetry/semantic-conventions-genai`, halaman resmi `opentelemetry.io/docs/specs/semconv/gen-ai/`, dan registry attribute `gen-ai.md` di repo baru.

**Temuan**
Seluruh konstanta `gen_ai.*` di paket `opentelemetry-semantic-conventions` (termasuk yang dipakai proyek ini: `GEN_AI_OPERATION_NAME`, `GEN_AI_REQUEST_MODEL`, `GEN_AI_CONVERSATION_ID`, `GEN_AI_USAGE_INPUT_TOKENS`, `GEN_AI_USAGE_OUTPUT_TOKENS`) sudah ditandai "Deprecated" di docstring-nya, dengan catatan "Moved to the OpenTelemetry GenAI semantic conventions repository". Dikonfirmasi via web search: governance spesifikasi GenAI pindah dari repo utama `open-telemetry/semantic-conventions` ke repo terpisah `open-telemetry/semantic-conventions-genai` sejak rilis `semantic-conventions v1.42.0` (2026-06-12). Per pengecekan ini (2026-08-14), repo baru tersebut **belum punya release/tag resmi maupun paket PyPI generated-code sendiri** — dikonfirmasi lewat `WebFetch` ke halaman Releases repo baru ("There aren't any releases here"). Namun nilai string atribut itu sendiri **tidak berubah** — dikonfirmasi dengan membandingkan langsung ke `docs/registry/attributes/gen-ai.md` di repo baru: `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.conversation.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` semuanya identik, status "Development" (belum ada yang "Stable").

Diverifikasi juga secara teknis bahwa mengakses konstanta ini di Python **tidak** memicu `DeprecationWarning` runtime (dites dengan `python -W error::DeprecationWarning`) — status "Deprecated" murni catatan dokumentasi/docstring, bukan decorator `@deprecated` aktif.

Keputusan praktis: tetap memakai paket `opentelemetry-semantic-conventions==0.65b0` (dipin lewat `uv.lock`) sebagai sumber string konstanta, karena ini satu-satunya sumber konstanta Python yang ter-install & ter-versi saat ini — bukan mengabaikan status deprecated, tapi pilihan sadar karena tidak ada alternatif yang lebih baik tersedia. Dicatat sebagai keterbatasan diterima (lihat Task 9 dan `docs/keterbatasan-diterima.md`).

**Error/Kegagalan (jika ada)**
Tidak ada error teknis — ini murni temuan riset yang mengubah bentuk pekerjaan Task 8/9 dari "cek versi lalu catat" (dibayangkan sederhana di plan) menjadi "cek versi, temukan perpindahan repo governance yang baru terjadi ~2 bulan lalu, verifikasi nilai atribut belum berubah, dan catat keterbatasan secara eksplisit".

**Hasil Verifikasi**
Web search + WebFetch ke: `github.com/open-telemetry/semantic-conventions-genai`, `opentelemetry.io/docs/specs/semconv/gen-ai/`, `github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/registry/attributes/gen-ai.md`, `github.com/open-telemetry/semantic-conventions-genai/releases`. Uji lokal `uv run python -W error::DeprecationWarning -c "..."` tidak melempar exception.

**Commit:** `746301a` — `feat(milestone-1.1): skrip verifikasi span/metric dummy dan kunci versi genai semconv`

---

### Task 9 — Tulis `genai_semconv.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/genai_semconv.py`: docstring modul menjelaskan temuan Task 8 secara lengkap (perpindahan governance, status pre-stable, alasan tetap memakai paket lama), konstanta `GENAI_SEMCONV_SPEC_STATUS`/`GENAI_SEMCONV_SPEC_SOURCE`/`GENAI_SEMCONV_PYTHON_PACKAGE` sebagai metadata versi terkunci, dan re-export lima konstanta atribut yang dipakai proyek ini dari `opentelemetry.semconv._incubating.attributes.gen_ai_attributes`.

**Temuan**
Modul stabil (`opentelemetry.semconv.attributes`, tanpa `_incubating`) tidak punya file `gen_ai_attributes.py` sama sekali — dikonfirmasi lewat pencarian file di `.venv`. Ini bukan kesalahan, memang konvensi standar OTel Python: atribut eksperimental/pre-stable selalu ditaruh di bawah `_incubating`, jadi mengimpor dari path itu adalah cara yang benar, bukan workaround.

**Error/Kegagalan (jika ada)** Tidak ada.

**Hasil Verifikasi:** *(digabung dengan Task 11)*

**Commit:** `746301a` — `feat(milestone-1.1): skrip verifikasi span/metric dummy dan kunci versi genai semconv`

---

### Task 10 — Tulis `send_dummy_span.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/smoke_test/send_dummy_span.py`: setup `TracerProvider`+`OTLPSpanExporter` dan `MeterProvider`+`OTLPMetricExporter` (keduanya ke `localhost:4317`, `insecure=True`), mengirim satu trace berisi span induk `invoke_agent` (atribut `session.id`, `turn.index`) dan span anak `chat` (atribut `gen_ai.*` dari `genai_semconv.py` + `smoke_test.marker`), plus satu metric counter `smoke_test.dummy_counter`.

**Temuan**
Karena `genai_semconv.py` bukan bagian dari paket ter-install (dan struktur `src/` sengaja belum ada), impor lintas-file di `infra/observability/` butuh manipulasi `sys.path` manual (menambahkan folder induk skrip ke `sys.path`) — pola standar untuk skrip standalone tanpa packaging, didokumentasikan lewat komentar di kode kenapa ini diperlukan.

**Error/Kegagalan (jika ada)** Tidak ada — skrip jalan sukses di percobaan pertama.

**Hasil Verifikasi:** *(lihat Task 11)*

**Commit:** `746301a` — `feat(milestone-1.1): skrip verifikasi span/metric dummy dan kunci versi genai semconv`

---

### Task 11 — Jalankan skrip, verifikasi di Jaeger & Prometheus

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv run python infra/observability/smoke_test/send_dummy_span.py` dijalankan dari root repo. Skrip mencetak `trace_id=029ce450fc0631e4d44cb36680aac90d`. Trace itu di-query langsung lewat Jaeger API (`GET /api/traces/029ce450fc0631e4d44cb36680aac90d`), dan metric di-query lewat Prometheus HTTP API (`GET /api/v1/query?query=smoke_test_dummy_counter_total`).

**Hasil Verifikasi**
- **Jaeger API** mengembalikan 1 trace berisi 2 span: `invoke_agent` (induk, atribut `session.id=milestone-1.1-smoke-test`, `turn.index=1`, `deployment.environment=local-dev` dari processor enrichment) dan `chat` (anak, `CHILD_OF` `invoke_agent`, atribut `gen_ai.operation.name=chat`, `gen_ai.request.model=dummy-model-smoke-test`, `gen_ai.conversation.id=milestone-1.1-smoke-test`, `gen_ai.usage.input_tokens=10`, `gen_ai.usage.output_tokens=5`, `smoke_test.marker=milestone-1.1-primary`). `processes.p1.serviceName=milestone-1.1-smoke-test-primary`.
- **Prometheus API** mengembalikan hasil query `smoke_test_dummy_counter_total` dengan `value=1`, label `smoke_test_marker=milestone-1.1-primary`, `deployment_environment=local-dev`, `job=otel-collector`, `exported_job=milestone-1.1-smoke-test-primary` — membuktikan metric benar-benar melewati pipeline Collector (label `job`/`instance` dari scrape Prometheus, label `exported_job`/`exported_instance` dari resource asli si pengirim, sesuai perilaku standar relabeling Prometheus saat nama label bentrok).

Kedua bukti di atas membuktikan Kriteria Keberhasilan sumber #1 dan #3 (span dummy terlihat di Jaeger dengan atribut benar; versi GenAI semconv terkunci eksplisit di kode).

**Commit:** `746301a` — `feat(milestone-1.1): skrip verifikasi span/metric dummy dan kunci versi genai semconv`

---

### Task 11a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 3 di atas ditulis (Task 8-11 digabung penulisannya karena saling terkait erat). File di-stage: `infra/observability/genai_semconv.py`, `infra/observability/smoke_test/send_dummy_span.py`, `milestones/1.1-fondasi-collector/logs.md`.

**Hasil Verifikasi**
`git status --short` dicek sebelum staging.

**Commit:** `746301a` — `feat(milestone-1.1): skrip verifikasi span/metric dummy dan kunci versi genai semconv`

---

## Checkpoint 4 — Verifikasi Fondasi Bersama (Simulasi Multi-Emitter)

**Mulai:** 2026-08-14 16:15 · **Selesai:** 2026-08-14 16:30

### Task 12 — Tulis `send_dummy_span_secondary.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `infra/observability/smoke_test/send_dummy_span_secondary.py`: `service.name` berbeda (`milestone-1.1-smoke-test-secondary`), dan sengaja memakai bentuk span non-LLM `input.validate` (kontrak Bagian 2 dokumen observability untuk Input Layer) — bukan `chat`/`gen_ai.*` seperti skrip primer — supaya secara struktural jelas berbeda, bukan sekadar duplikat skrip pertama dengan nama lain.

**Temuan** Tidak ada temuan baru — pola setup tracing sama seperti Task 10, disederhanakan (tanpa metrics, tanpa span induk `invoke_agent`, karena tujuannya cukup membuktikan span independen sampai ke Collector yang sama).

**Error/Kegagalan (jika ada)** Tidak ada.

**Hasil Verifikasi:** *(lihat Task 13)*

**Commit:** *(lihat Task 13a)*

---

### Task 13 — Jalankan kedua skrip terpisah, verifikasi dua trace independen

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dijalankan dua kali `uv run python ...` sebagai dua proses berurutan-tapi-independen (bukan dipanggil dari satu proses/skrip pemanggil bersama): `send_dummy_span.py` (primer) menghasilkan `trace_id=0b7eac5b771ed638828c02e738292793`, `send_dummy_span_secondary.py` (sekunder) menghasilkan `trace_id=d60dcc0532ed143743dcaa6817f2b075`. Keduanya di-query terpisah lewat Jaeger API.

**Hasil Verifikasi**
- Trace primer: `GET /api/traces/0b7eac5b771ed638828c02e738292793` → span `chat` + `invoke_agent`, `serviceName=milestone-1.1-smoke-test-primary`.
- Trace sekunder: `GET /api/traces/d60dcc0532ed143743dcaa6817f2b075` → span `input.validate`, `serviceName=milestone-1.1-smoke-test-secondary`.

Dua `trace_id` berbeda, dua `service.name` berbeda, masing-masing dari proses Python terpisah yang dijalankan independen, keduanya diterima dan diteruskan dengan benar oleh **satu instance Collector yang sama** — membuktikan fondasi bersama benar-benar bisa dipakai tanpa instance terpisah per pengirim, sejauh yang bisa dibuktikan lewat simulasi (lihat catatan keterbatasan di `report.md`: ini simulasi, bukan bukti dari PIC 2/3/4 sungguhan, karena keduanya belum dimulai).

**Commit:** *(lihat Task 13a)*

---

### Task 13a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 4 di atas ditulis. File di-stage: `infra/observability/smoke_test/send_dummy_span_secondary.py`, `milestones/1.1-fondasi-collector/logs.md`.

**Hasil Verifikasi** `git status --short` dicek sebelum staging.

**Commit:** *(diisi setelah commit dieksekusi)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — penyimpangan Task 1 (flag `uv init`) dan Task 7 (rename exporter `otlp`→`otlp_grpc`) adalah koreksi di dalam task yang sudah direncanakan, bukan task/checkpoint baru di luar plan. Temuan Task 8 (perpindahan governance GenAI semconv) memperluas *kedalaman* Task 8/9 secara signifikan dan memicu inisialisasi `docs/keterbatasan-diterima.md` lebih awal dari rencana semula di plan (plan menyebutnya "diinisialisasi di Checkpoint 5" lewat tabel Risiko & Mitigasi, tapi nyatanya diinisialisasi di Checkpoint 3 begitu keterbatasannya ditemukan) — konsisten dengan prinsip "jangan tunda ke penutupan" yang sama seperti aturan `logs.md`+commit per checkpoint.
