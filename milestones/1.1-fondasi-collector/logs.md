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

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — penyimpangan Task 1 (flag `uv init`) adalah koreksi di dalam task yang sudah direncanakan, bukan task/checkpoint baru di luar plan.
