# Decisions — Milestone 8.7: Kontainerisasi Backend (+ Restrukturisasi Branch Git)

Dokumen ini mencatat setiap keputusan desain untuk Milestone 8.7, ditentukan sebelum implementasi dimulai lewat Plan Mode (5 putaran `AskUserQuestion`, termasuk 3 putaran koreksi bertahap saat memahami maksud user soal "coba dulu sebelum stabil di main").

---

## Keputusan 1: Dockerfile Multi-Stage, Mirror Gaya `custom-exporter/Dockerfile`

**Sumber Paksaan**
`docs/02-implementation-plan/rancangan-ci-cd.md`, Milestone 8.7 Lingkup: "mirror pola multi-stage `custom-exporter/Dockerfile` yang sudah ada (konsisten gaya, bukan pola baru)".

**Keputusan yang Diikuti**
`Dockerfile` baru di root repo memakai 2 stage: `builder` (install dependency+build venv) dan runtime (image minimal, copy hasil build saja) — mirror struktur `custom-exporter/Dockerfile` (`build` stage golang → runtime stage alpine).

**Catatan Ketergantungan**
Menyimpang dari pola ini (mis. single-stage) akan menghasilkan image jauh lebih besar (membawa toolchain build) dan tidak konsisten gaya project.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kalimat Lingkup dokumen sumber secara verbatim.

---

## Keputusan 2: Base Image `python:3.13-slim`

**Sumber Paksaan**
`pyproject.toml` baris 5: `requires-python = ">=3.13"`. Dokumen sumber M8.7 eksplisit menyebut `python:3.13-slim`. Riset eksternal mengonfirmasi image ini multi-arch resmi (termasuk `linux/arm64`).

**Keputusan yang Diikuti**
Kedua stage Dockerfile memakai `python:3.13-slim` sebagai base.

**Catatan Ketergantungan**
Versi Python image harus tetap sinkron dengan `requires-python` kalau nanti di-upgrade — perubahan salah satu wajib diikuti perubahan yang lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kombinasi `pyproject.toml` + dokumen sumber.

---

## Keputusan 3: Build Dependency via `uv`, Runtime TANPA Wrapper `uv run`

**Sumber Paksaan**
Preseden project: seluruh dependency management sejak M1.1 memakai `uv` (`uv.lock` sudah ada, terkonfirmasi py marker `aarch64`/`manylinux` 404× lewat riset — siap dipakai `uv sync --frozen` tanpa config tambahan). Untuk RUNTIME, forced oleh temuan nyata `milestones/7.17-membangun-endpoint-api/logs.md` (proses `uvicorn` yang di-spawn lewat `uv run` jadi orphan saat `.terminate()` di Windows — wrapper `uv run` tidak forward sinyal proses dengan benar ke child-nya) — meski temuan itu spesifik Windows, di dalam container proses CMD jadi PID 1 dan WAJIB menerima `SIGTERM` (`docker stop`) dengan benar untuk graceful shutdown; menghindari lapisan wrapper apa pun di titik paling kritis ini adalah langkah aman yang tidak mahal (dependency sudah "dibekukan" ke `.venv/` di build stage, tidak perlu `uv` lagi di runtime).

**Keputusan yang Diikuti**
Build stage: `uv sync --frozen --no-dev`. Runtime stage: `.venv/` di-copy dari build stage, `CMD` memanggil `python -m uvicorn` LANGSUNG (bukan `uv run uvicorn`).

**Catatan Ketergantungan**
Kalau ada dependency baru butuh env var khusus saat runtime yang biasanya di-inject `uv run` dari `.env`, itu TIDAK akan terjadi lagi — tapi ini sudah konsisten karena container selalu menerima env var dari luar (`docker run -e`/compose `environment:`), bukan dari file `.env` yang dibaca `python-dotenv` (`load_dotenv()` tetap dipanggil di kode, tapi tidak menemukan file `.env` di container — aman, `os.environ.get()` tetap membaca env var asli proses).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`CMD ["uv", "run", "uvicorn", ...]` di runtime image** — dipertimbangkan karena lebih ringkas ditulis, ditolak karena preseden M7.17 menunjukkan `uv run` tidak bisa dipercaya penuh untuk process/signal management, dan tidak ada manfaat nyata memakainya di runtime image yang sudah py `.venv/` lengkap.

---

## Keputusan 4: `OTLP_ENDPOINT` via Env Var Standar `OTEL_EXPORTER_OTLP_ENDPOINT`

**Sumber Paksaan**
Dokumen sumber M8.7: "Menyesuaikan endpoint OTLP untuk jaringan Docker (`otel-collector:4317` lewat DNS internal compose, alih-alih `localhost:4317`)". Nama env var `OTEL_EXPORTER_OTLP_ENDPOINT` adalah konvensi semantik RESMI OpenTelemetry SDK (bukan nama custom) — forced by standar industri, memudahkan siapa pun yang familiar OTel langsung mengenali variabelnya.

**Keputusan yang Diikuti**
`src/observability/tracing.py`: `OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")` — default TETAP `localhost:4317` supaya perilaku non-container (dev lokal, `next dev`-setara untuk backend) TIDAK berubah sama sekali.

**Catatan Ketergantungan**
`docker-compose.yml` produksi (M8.9, belum dibangun) nanti WAJIB set `OTEL_EXPORTER_OTLP_ENDPOINT=otel-collector:4317` untuk service backend — dicatat sebagai follow-up eksplisit di `report.md`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Nama env var custom (mis. `NIRWANA_OTLP_ENDPOINT`)** — ditolak, tidak ada alasan menghindari konvensi resmi OTel yang sudah ada.

---

## Keputusan 5: `build-and-push-backend` dan `build-and-push-exporter` sebagai DUA Job Terpisah

**Sumber Paksaan**
Preseden konsisten `ci.yml` sepanjang M8.1-8.5: Python dan Go SELALU dipisah jadi job berbeda (`ruff` vs `golangci-lint`, `test-python-fast`/`test-python-llm` vs `go-test`) — `dependency-scan` adalah SATU-SATUNYA pengecualian (audit gabungan `pip-audit`+`govulncheck`, bukan build).

**Keputusan yang Diikuti**
Dua job terpisah di `ci.yml`, masing-masing membangun+push satu image (backend Python, `custom-exporter` Go).

**Catatan Ketergantungan**
Kegagalan salah satu job (mis. backend gagal build) tidak menghalangi job lain (exporter) untuk tetap sukses — memberi sinyal kegagalan yang presisi, konsisten filosofi pemisahan job existing.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu job `build-and-push` dengan 2 step build berurutan** — ditolak, tidak konsisten pola pemisahan Python/Go yang sudah dipegang project sejak M8.1.

---

## Keputusan 6: Kategori Commit — `fix` untuk Territory Milestone Lain, `feat` untuk Konten Baru M8.7

**Status:** Diputuskan sebelum implementasi (dari plan, instruksi eksplisit user).

**Latar Belakang**
Milestone ini genuinely menyentuh file/setting yang dibangun milestone lain (`ci.yml` trigger — milik M8.1-8.5; `tracing.py` — milik M1.1/M1.2; branch protection — setting yang sama yang diperluas M8.1-8.4) SEKALIGUS menambah konten baru murni milik M8.7 sendiri (`Dockerfile`, `.dockerignore`, endpoint `/health`, 2 job CI baru). Konvensi commit project (Conventional Commits) tidak otomatis membedakan ini tanpa arahan eksplisit.

**Keputusan yang Dipilih**
- `fix`: perubahan pada `ci.yml` (trigger existing), `tracing.py` (env var), branch protection (setting GitHub).
- `feat`: `Dockerfile`, `.dockerignore`, endpoint `/health`, job `build-and-push-backend`/`build-and-push-exporter` (baris BARU ditambahkan ke `ci.yml`, meski di file yang sama dengan perubahan `fix` trigger — dipisah commit).

**Alasan**
User eksplisit meminta pemisahan ini saat mengonfirmasi cakupan "selesaikan semua sekarang di M8.7" — mengakui bahwa sebagian pekerjaan ini genuinely "memperbaiki/menyesuaikan" infrastruktur lama untuk kebutuhan baru (bukan cacat, tapi penyesuaian retroaktif), bukan fitur baru milik M8.7 semata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Semua commit `feat(milestone-8.7)` tanpa pembedaan** — ditolak eksplisit oleh user.

**Dampak**
Checkpoint 4 (trigger `ci.yml`) dan Checkpoint 6 (`tracing.py`) di-commit `fix`; Checkpoint 7-9, 11-12 di-commit `feat`.

---

## Keputusan 7: Evolusi Model Branch — Kronologi Lengkap

**Status:** Diputuskan sebelum implementasi (dari plan, lewat 3 putaran koreksi bertahap `AskUserQuestion`).

**Latar Belakang**
Pertanyaan awal (putaran 1) menawarkan 2 opsi sederhana untuk trigger job `build-and-push`: "push ke main saja" vs "build-only di PR, push di main" — KEDUANYA murni soal kapan CI membangun image, TIDAK mengasumsikan branch permanen baru. User menyatakan bingung dan menjelaskan maksudnya sendiri: "ada layer dimana sudah stabil bisa diuji coba dulu, nah main digunakan untuk benar benar stabil" — mengindikasikan kebutuhan yang JAUH lebih besar dari sekadar trigger CI.

**Evolusi Klarifikasi (3 putaran):**
1. **Putaran 2**: diajukan "Level 1" (cuma cek build berhasil, tanpa environment sungguhan) vs "Level 2" (ada environment staging yang benar-benar jalan). User pilih **Level 2**.
2. **Putaran 3**: diajukan lokasi staging — 1 VPS sama (port/container terpisah) vs 2 VPS terpisah. User pilih **1 VPS sama, port/container terpisah** (konsisten kuota Always Free Oracle, tidak menambah biaya).
3. **Putaran 4**: diajukan model branch konkret — usulan agent "main=auto-staging, git tag=promosi production" (TANPA branch permanen baru) vs "branch staging/develop terpisah dari main". User TIDAK setuju usulan agent, eksplisit menjawab **"saya lebih ke ingin staging -> develop -> main"**.
4. **Putaran 5**: diklarifikasi apakah "staging" di sini nama branch atau nama environment, dan berapa branch permanen (2 vs 3). User memilih eksplisit **3 branch git: `staging`, `develop`, `main`**.

**Keputusan yang Dipilih (Final)**
3 branch git permanen dengan pemetaan:
- `staging` (branch) — kerja harian, commit langsung (TANPA branch protection), TIDAK deploy ke environment mana pun. CI (`ci.yml` existing) tetap jalan penuh di sini sebagai gate kualitas kode dasar.
- `develop` (branch) — hasil promosi dari `staging` (lewat PR, digate branch protection). Push/merge ke sini memicu build+push image bertag `staging` (nama tag mengikuti nama ENVIRONMENT tujuan, bukan nama branch — lihat Keputusan 8) — dipakai deploy ke environment STAGING di VPS (mekanisme deploy sungguhan sendiri BARU dibangun M8.10, M8.7 cuma menyiapkan image-nya).
- `main` (branch) — hasil promosi dari `develop` (lewat PR, digate branch protection). Push/merge ke sini memicu build+push image bertag `latest` — dipakai deploy ke environment PRODUCTION.

**Alasan**
User secara eksplisit dan konsisten (3 putaran klarifikasi) menghendaki model gitflow 3-tingkat, BUKAN model 2-branch yang diusulkan agent sebagai alternatif lebih sederhana — keputusan akhir mengikuti preferensi user apa adanya, bukan rekomendasi awal agent.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **"main=auto-staging, git tag=promosi production" (TANPA branch baru)** — diusulkan eksplisit oleh agent sebagai opsi yang tidak mengubah kebiasaan commit-langsung-ke-main 24+ milestone sebelumnya, TAPI DITOLAK user yang eksplisit menghendaki branch permanen terpisah.
- **2 branch (`develop`+`main` saja, "staging" jadi nama environment bukan branch)** — diajukan sebagai penyederhanaan di putaran klarifikasi terakhir, DITOLAK user yang tetap memilih 3 branch git sungguhan.
- **2 VPS terpisah untuk staging vs production** — dipertimbangkan untuk isolasi penuh resource, ditolak user demi menghindari biaya/kompleksitas provisioning ganda (kuota Always Free Oracle terbatas).

**Dampak**
Ini adalah keputusan PALING BESAR di milestone ini — mengubah cakupan M8.7 dari "sekadar Dockerfile" jadi mencakup restrukturisasi `ci.yml` trigger, branch protection `develop`+`main`, dan skema tag image. JUGA mengubah asumsi dasar `rancangan-ci-cd.md` untuk M8.8 (provisioning perlu alokasi 2 environment sejak awal), M8.9 (topologi/reverse-proxy perlu 2 port/subdomain), M8.10 (deploy pipeline perlu tahu branch→environment mapping) — didokumentasikan sebagai addendum resmi di dokumen sumber (Checkpoint 2, lihat Keputusan 10).

---

## Keputusan 8: Skema Tag Image — `<branch>-<sha>` Selalu + Tag Mengambang per Environment

**Status:** Diputuskan sebelum implementasi (dari plan, gabungan jawaban `AskUserQuestion` putaran 1 + penyesuaian setelah Keputusan 7 final).

**Latar Belakang**
Jawaban awal user (putaran 1, sebelum model 3-branch mengkristal) memilih "latest + commit SHA" untuk skema tag secara umum. Setelah model 3-branch+2-environment diputuskan (Keputusan 7), skema itu perlu disesuaikan supaya tiap environment py cara pull yang jelas tanpa perlu tahu SHA persis.

**Keputusan yang Dipilih**
Setiap build (branch apa pun) selalu ditandai `<nama-branch>-<sha-pendek>` (presisi, bisa dipakai rollback M8.10). TAMBAHAN tag mengambang sesuai branch: `latest` kalau dibangun dari `main` (production), `staging` kalau dibangun dari `develop` (staging). Branch `staging` (git) sendiri TIDAK mendapat tag mengambang khusus (tidak deploy ke mana pun).

**Alasan**
Kombinasi ini memenuhi keputusan awal user (SHA untuk presisi/rollback) SEKALIGUS memberi M8.10 pegangan sederhana (`:latest`/`:staging`) tanpa perlu tracking SHA manual untuk operasi deploy rutin.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Cuma `latest`+SHA tanpa tag `staging` mengambang** — ditolak, M8.10 akan kesulitan tahu "image staging terbaru yang mana" tanpa query API tambahan.

**Dampak**
`docker/build-push-action` step di kedua job CI baru (Checkpoint 11-12) perlu logic kondisional tag berdasar `github.ref_name`.

---

## Keputusan 9: Kebijakan Trivy — Non-Blocking Dulu, Baseline Direkam

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
Belum ada data nyata soal CVE apa yang akan ditemukan di image `python:3.13-slim`+dependency project ini — memutuskan kebijakan blocking tanpa data risikonya sama dengan M8.1 Keputusan 2 (yang justru menjalankan scan dulu untuk baseline SEBELUM menetapkan kebijakan zero-tolerance).

**Keputusan yang Dipilih**
Trivy dijalankan nyata (kedua image), hasil (CVE per severity) dicatat sebagai baseline di `logs.md`. Job TIDAK gagal karena temuan Trivy (`exit-code: '0'` atau setara).

**Alasan**
Mirror proses M8.1 yang terbukti bekerja baik (baseline dulu, kebijakan diputuskan dengan data di tangan) — dipilih user secara eksplisit di atas opsi blocking langsung.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Blocking CRITICAL+HIGH sejak awal** — ditolak, berisiko memblokir job karena CVE base-image Debian yang belum tentu py fix upstream, tanpa data dulu untuk menilai frekuensinya.

**Dampak**
Kebijakan blocking (kalau nanti diputuskan) jadi keputusan tertunda baru untuk `docs/keputusan-tertunda.md`, dipicu setelah baseline Checkpoint 13 didapat.

---

## Keputusan 10: Endpoint `GET /health` Ditambahkan Sekarang

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
KK M8.7 minta bukti "container menjawab request dasar tanpa error dependency ARM64" — perlu target verifikasi yang tidak bergantung `DATABASE_URL`/`OPENROUTER_API_KEY`/`chatbot_api` (yang tidak tersedia di lingkungan CI/verifikasi image). `/docs`/`/openapi.json` bawaan FastAPI bisa jadi alternatif tanpa endpoint baru, tapi M8.10 (dokumen sumber sendiri) eksplisit menyebut "endpoint health/versi" sebagai salah satu cara memverifikasi deploy sukses.

**Keputusan yang Dipilih**
Tambah `GET /health` di `src/main.py` — respons minimal `{"status": "ok"}`, tanpa dependency eksternal apa pun.

**Alasan**
Nilai gunanya melampaui M8.7 sendiri — langsung relevan untuk M8.9 (target health-check reverse-proxy Caddy) dan M8.10 (KK eksplisit menyebut endpoint health/versi). Biaya implementasi sangat kecil (satu route sederhana).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tunda, pakai `/docs`/`/openapi.json` bawaan untuk verifikasi M8.7 saja** — ditolak user yang memilih menambahkan sekarang mengingat manfaat lintas-milestone.

**Dampak**
`src/main.py` (milik M7.17) mendapat route baru — di-commit `feat` (bukan `fix`, karena ini kapabilitas baru, bukan penyesuaian infrastruktur lama, meski filenya milik milestone lain).

---

## Keputusan 11: `staging` (branch) TIDAK Diberi Branch Protection; `develop`+`main` Diberi

**Sumber Paksaan**
Definisi eksplisit user tentang `staging`: "kerja harian, belum tentu stabil" — forced langsung dari deskripsi fungsinya sendiri (Keputusan 7). Branch protection di titik ini akan bertentangan dengan sifat "boleh belum stabil, commit bebas" yang justru jadi ciri khas `staging`.

**Keputusan yang Diikuti**
Branch protection (required status checks) diaktifkan HANYA di `develop` dan `main` — keduanya jadi gerbang promosi yang wajib lolos CI. `staging` tetap bisa di-push langsung kapan saja.

**Catatan Ketergantungan**
Mirror preseden project sendiri sebelum M8.1 (`main` juga bebas commit langsung tanpa gate apa pun sampai M8.1 menyalakannya) — `staging` sekarang mengambil peran itu untuk lapisan paling awal.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by definisi fungsi `staging` yang sudah dinyatakan eksplisit user sendiri.

---

## Keputusan 12: Addendum Dokumen Sumber Ditulis Sebelum Implementasi Jalan

**Sumber Paksaan**
Prinsip `CLAUDE.md`: dokumen sumber (`rancangan-ci-cd.md`) harus tetap jadi rujukan akurat untuk pekerjaan mendatang (M8.8-8.10) — model 3-branch+dual-environment (Keputusan 7) mengubah asumsi dasar dokumen itu untuk KETIGA milestone tersebut, bukan cuma M8.7.

**Keputusan yang Diikuti**
Checkpoint 2 (sebelum implementasi kode apa pun) menulis addendum eksplisit di `rancangan-ci-cd.md` — peta "branch mana memicu apa", supaya sesi kerja M8.8-8.10 mendatang tidak perlu menelusuri ulang riwayat percakapan ini.

**Catatan Ketergantungan**
Tanpa ini, M8.8 (provisioning VPS) berisiko direncanakan dengan asumsi keliru "1 environment saja" sesuai isi dokumen sumber ASLI (belum di-update).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by prinsip menjaga dokumen sumber tetap akurat.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Dockerfile multi-stage, mirror gaya `custom-exporter/Dockerfile` | B | Checkpoint 9 |
| 2 | Base image `python:3.13-slim` | B | Checkpoint 9 |
| 3 | Build via `uv`, runtime tanpa wrapper `uv run` | B | Checkpoint 9 |
| 4 | `OTLP_ENDPOINT` via env var standar `OTEL_EXPORTER_OTLP_ENDPOINT` | B | Checkpoint 6 |
| 5 | `build-and-push-backend`/`build-and-push-exporter` dua job terpisah | B | Checkpoint 11-12 |
| 6 | Kategori commit `fix` vs `feat` | A | Plan |
| 7 | Evolusi model branch — 3 branch `staging`/`develop`/`main`, kronologi lengkap | A | Plan |
| 8 | Skema tag image — `<branch>-<sha>` + tag mengambang per environment | A | Checkpoint 11-12 |
| 9 | Kebijakan Trivy — non-blocking dulu, baseline direkam | A | Checkpoint 11-12 |
| 10 | Endpoint `GET /health` ditambahkan sekarang | A | Checkpoint 7 |
| 11 | `staging` tanpa branch protection, `develop`+`main` diberi | B | Checkpoint 14 |
| 12 | Addendum dokumen sumber ditulis sebelum implementasi | B | Checkpoint 2 |
