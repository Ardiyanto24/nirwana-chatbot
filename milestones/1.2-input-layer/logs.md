# Logs — Milestone 1.2: Membangun Input Layer

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

---

## Checkpoint 1 — Fondasi: Dependency, Skeleton `src/`, Reposisi Modul Observability

**Mulai:** 2026-08-14 (lanjutan sesi) · **Selesai:** 2026-08-14

### Task 1 — Tambah dependency

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv add fastapi "uvicorn[standard]" pyyaml` (runtime, 18 paket termasuk transitive seperti `pydantic`/`starlette`), lalu `uv add --dev pytest httpx` (8 paket).

**Temuan** Tidak ada kejutan — resolve & install berjalan mulus, tidak ada konflik versi dengan dependency Milestone 1.1 (`opentelemetry-*`).

**Error/Kegagalan** Tidak ada.

**Hasil Verifikasi:** Output `uv add` menunjukkan seluruh paket ter-install tanpa error, `uv.lock` ter-update.

**Commit:** *(lihat Task 7a)*

---

### Task 2 — Skeleton `src/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`mkdir -p src/layers src/schemas src/observability src/config` + `__init__.py` kosong di tiap folder (termasuk `src/__init__.py`).

**Error/Kegagalan** Tidak ada.

**Commit:** *(lihat Task 7a)*

---

### Task 3 — Reposisi `genai_semconv.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`git mv infra/observability/genai_semconv.py src/observability/genai_semconv.py` — git mendeteksi sebagai rename murni (status `R`), histori file terjaga. Import di `infra/observability/smoke_test/send_dummy_span.py` diperbarui: sebelumnya `sys.path.insert(0, parent.parent)` + `import genai_semconv`, sekarang `sys.path.insert(0, parents[3])` (root repo) + `from src.observability import genai_semconv as semconv` — karena `src/` sekarang paket Python sungguhan (ada `__init__.py`), bukan lagi folder lepas.

**Temuan**
`infra/observability/README.md` juga merujuk `genai_semconv.py` di path lama — diperbarui juga (di luar daftar Files eksplisit plan Task 3, tapi konsisten dengan semangat "reposisi" itu sendiri; kalau dibiarkan akan jadi dokumentasi usang begitu Milestone ini di-commit).

**Error/Kegagalan** Tidak ada.

**Hasil Verifikasi**
`uv run python -c "from src.observability.genai_semconv import GEN_AI_OPERATION_NAME; print(GEN_AI_OPERATION_NAME)"` → `gen_ai.operation.name`, tanpa error. Stack Docker Milestone 1.1 sempat berhenti (kemungkinan karena sesi/mesin idle sejak commit terakhir) — dinyalakan ulang (`docker compose up -d` di `infra/observability/`) sebelum verifikasi lanjutan. `uv run python infra/observability/smoke_test/send_dummy_span.py` (dengan import baru) berhasil, mencetak `trace_id=4ec57dbe2d8641285ad3d16eb7258bed` tanpa exception — membuktikan reposisi tidak merusak skrip lama.

**Commit:** *(lihat Task 7a)*

---

### Task 4 — Tulis `src/observability/tracing.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`setup_tracing(service_name: str) -> TracerProvider` + `get_tracer(name: str) -> Tracer`, pola diadaptasi langsung dari `send_dummy_span_secondary.py` Milestone 1.1 (parameterisasi `service_name`, dipisah jadi fungsi setup sekali + get_tracer per pemanggilan).

**Error/Kegagalan** Tidak ada (belum diverifikasi end-to-end di checkpoint ini — akan dipakai nyata di Checkpoint 3 saat `src/main.py` ditulis).

**Commit:** *(lihat Task 7a)*

---

### Task 5 — Perbaiki referensi "19 role" → "20 role"

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dua kemunculan di `docs/02-implementation-plan/rancangan-rbac-authorization.md` (baris 9 tabel header "Dokumen rujukan kebutuhan", baris 59 teks Lingkup Milestone 2.2) diubah dari "19 role × 10 domain" menjadi "20 role × 10 domain".

**Hasil Verifikasi:** `grep -n "19 role" docs/02-implementation-plan/rancangan-rbac-authorization.md` tidak lagi menemukan hasil.

**Commit:** *(lihat Task 7a)*

---

### Task 6 — Tulis `roles.yaml` + loader

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/config/roles.yaml`: 20 role dari tabel §2 `rancangan-rbac-ai-chatbot.md`, komentar header menyebut sumber, alasan tidak bisa auto-sync, dan tanggal konfirmasi. `src/config/roles.py`: `load_valid_roles() -> frozenset[str]`, dibaca dari file YAML relatif ke lokasi modul (`Path(__file__).parent`), di-cache pakai `functools.lru_cache(maxsize=1)`.

**Temuan** `frozenset` dipilih (bukan `set`) supaya hasil `lru_cache` tidak bisa diam-diam dimutasi pemanggil — sengaja immutable karena ini data konfigurasi yang dibaca banyak tempat.

**Hasil Verifikasi**
`uv run python -c "from src.config.roles import load_valid_roles; roles = load_valid_roles(); assert len(roles) == 20; print(sorted(roles))"` → tepat 20 role tercetak, cocok persis dengan tabel §2 sumber (dicek manual satu-satu).

**Commit:** *(lihat Task 7a)*

---

### Task 7 — Inisialisasi `docs/keputusan-tertunda.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
File pertama untuk backlog keputusan tertunda project-wide (belum ada sebelumnya di repo). Satu entri: keputusan database utuh untuk proyek (dipakai Session Memory, berpotensi juga migrasi daftar role) ditunda ke Milestone 1.5, dengan konteks kemunculan dan pemicu peninjauan eksplisit.

**Commit:** *(lihat Task 7a)*

---

### Task 7a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 1 di atas ditulis. File di-stage dalam 2 commit terpisah per kategori (kode vs dokumen), sesuai rencana Commit di plan.

**Hasil Verifikasi**
`git status --short` dicek sebelum staging — dipastikan `.gitignore`/`docs/CLAUDE.md` (pre-existing, di luar cakupan) dan `AGENT.md` (sengaja tidak di-track) tidak ikut ter-stage.

**Commit:** *(diisi setelah commit dieksekusi)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Update `infra/observability/README.md` (referensi path `genai_semconv.py`) di Task 3 — bukan task baru, perluasan kecil dari file list Task 3 yang sudah direncanakan, dicatat eksplisit di atas.
