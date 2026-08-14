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

**Commit:** `22d9d3a` — `chore(milestone-1.2): skeleton src/, dependency fastapi/uvicorn/pyyaml, reposisi genai_semconv.py`

---

### Task 2 — Skeleton `src/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`mkdir -p src/layers src/schemas src/observability src/config` + `__init__.py` kosong di tiap folder (termasuk `src/__init__.py`).

**Error/Kegagalan** Tidak ada.

**Commit:** `22d9d3a` — `chore(milestone-1.2): skeleton src/, dependency fastapi/uvicorn/pyyaml, reposisi genai_semconv.py`

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

**Commit:** `22d9d3a` — `chore(milestone-1.2): skeleton src/, dependency fastapi/uvicorn/pyyaml, reposisi genai_semconv.py`

---

### Task 4 — Tulis `src/observability/tracing.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`setup_tracing(service_name: str) -> TracerProvider` + `get_tracer(name: str) -> Tracer`, pola diadaptasi langsung dari `send_dummy_span_secondary.py` Milestone 1.1 (parameterisasi `service_name`, dipisah jadi fungsi setup sekali + get_tracer per pemanggilan).

**Error/Kegagalan** Tidak ada (belum diverifikasi end-to-end di checkpoint ini — akan dipakai nyata di Checkpoint 3 saat `src/main.py` ditulis).

**Commit:** `22d9d3a` — `chore(milestone-1.2): skeleton src/, dependency fastapi/uvicorn/pyyaml, reposisi genai_semconv.py`

---

### Task 5 — Perbaiki referensi "19 role" → "20 role"

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dua kemunculan di `docs/02-implementation-plan/rancangan-rbac-authorization.md` (baris 9 tabel header "Dokumen rujukan kebutuhan", baris 59 teks Lingkup Milestone 2.2) diubah dari "19 role × 10 domain" menjadi "20 role × 10 domain".

**Hasil Verifikasi:** `grep -n "19 role" docs/02-implementation-plan/rancangan-rbac-authorization.md` tidak lagi menemukan hasil.

**Commit:** `fb3c255` — `docs: perbaiki referensi jumlah role dan inisialisasi keputusan-tertunda`

---

### Task 6 — Tulis `roles.yaml` + loader

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/config/roles.yaml`: 20 role dari tabel §2 `rancangan-rbac-ai-chatbot.md`, komentar header menyebut sumber, alasan tidak bisa auto-sync, dan tanggal konfirmasi. `src/config/roles.py`: `load_valid_roles() -> frozenset[str]`, dibaca dari file YAML relatif ke lokasi modul (`Path(__file__).parent`), di-cache pakai `functools.lru_cache(maxsize=1)`.

**Temuan** `frozenset` dipilih (bukan `set`) supaya hasil `lru_cache` tidak bisa diam-diam dimutasi pemanggil — sengaja immutable karena ini data konfigurasi yang dibaca banyak tempat.

**Hasil Verifikasi**
`uv run python -c "from src.config.roles import load_valid_roles; roles = load_valid_roles(); assert len(roles) == 20; print(sorted(roles))"` → tepat 20 role tercetak, cocok persis dengan tabel §2 sumber (dicek manual satu-satu).

**Commit:** `22d9d3a` — `chore(milestone-1.2): skeleton src/, dependency fastapi/uvicorn/pyyaml, reposisi genai_semconv.py`

---

### Task 7 — Inisialisasi `docs/keputusan-tertunda.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
File pertama untuk backlog keputusan tertunda project-wide (belum ada sebelumnya di repo). Satu entri: keputusan database utuh untuk proyek (dipakai Session Memory, berpotensi juga migrasi daftar role) ditunda ke Milestone 1.5, dengan konteks kemunculan dan pemicu peninjauan eksplisit.

**Commit:** `fb3c255` — `docs: perbaiki referensi jumlah role dan inisialisasi keputusan-tertunda`

---

### Task 7a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 1 di atas ditulis. File di-stage dalam 2 commit terpisah per kategori (kode vs dokumen), sesuai rencana Commit di plan.

**Hasil Verifikasi**
`git status --short` dicek sebelum staging — dipastikan `.gitignore`/`docs/CLAUDE.md` (pre-existing, di luar cakupan) dan `AGENT.md` (sengaja tidak di-track) tidak ikut ter-stage.

**Commit:** `1640a53` — `docs(milestone-1.2): catat logs checkpoint 1`

---

## Checkpoint 2 — Skema Payload + Logic Validasi Murni

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 8 — Tulis `src/schemas/turn_payload.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`PreviousTurn` (question/answer, keduanya `min_length=1`) dan `TurnPayload` (`session_id`/`role_title`/`employee_id`/`question` non-empty, `turn_index` `ge=1`, `previous_turn: PreviousTurn | None = None`). Validasi `role_title` lewat `field_validator` yang cek keanggotaan ke `load_valid_roles()` (bukan `Literal[...]` — sumbernya benar-benar dari `roles.yaml`, bukan hardcode ulang di Pydantic). Validasi `previous_turn` wajib-jika-`turn_index>1` lewat `model_validator(mode="after")`.

**Temuan** Tidak ada. **Error/Kegagalan** Tidak ada.

**Hasil Verifikasi:** *(digabung dengan Task 9)*

**Commit:** `4e37e9f` — `feat(milestone-1.2): skema payload dan logic validasi input layer`

---

### Task 9 — Tulis `src/layers/input_layer.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`validate_turn_payload(raw: dict) -> TurnPayload`: membungkus `TurnPayload.model_validate(raw)` dalam span `input.validate` (`get_tracer` dari `src/observability/tracing.py`), mengisi atribut `session.id`/`turn.index` best-effort dari raw payload sebelum validasi (supaya tetap terekam meski validasi gagal total). Exception (`pydantic.ValidationError`) dibiarkan menjalar apa adanya — OTel SDK otomatis merekam exception & status ERROR pada span lewat context manager `start_as_current_span`, tidak perlu kode tambahan.

**Temuan**
Saat menguji manual, disadari `get_tracer()` di titik ini memakai `TracerProvider` default OTel (no-op) karena `setup_tracing()` belum pernah dipanggil di checkpoint ini — itu memang baru terjadi di `src/main.py` (Checkpoint 3) saat aplikasi startup. Span call jadi no-op diam-diam (tidak error, tidak terkirim kemana pun) — perilaku yang diharapkan untuk pengujian murni fungsi di checkpoint ini, verifikasi span nyata baru dilakukan di Checkpoint 4.

**Error/Kegagalan** Tidak ada.

**Hasil Verifikasi**
Diuji manual lewat `uv run python -c "..."` dengan 5 skenario: (1) `turn_index=1` tanpa histori → sukses; (2) `turn_index=2` dengan `previous_turn` → sukses; (3) `role_title` tidak dikenal (`"Bukan Role Asli"`) → `ValidationError` pesan `"role_title tidak dikenal: 'Bukan Role Asli'"`; (4) `turn_index=2` tanpa `previous_turn` → `ValidationError` pesan `"previous_turn wajib diisi kalau turn_index > 1"`; (5) field `session_id` dihilangkan → `ValidationError` dengan `loc=('session_id',)`, pesan `"Field required"` — menyebut field spesifik, bukan pesan generik. Kelima skenario lolos sesuai ekspektasi.

**Commit:** `4e37e9f` — `feat(milestone-1.2): skema payload dan logic validasi input layer`

---

### Task 9a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 2 di atas ditulis. File di-stage: `src/schemas/turn_payload.py`, `src/layers/input_layer.py`, `milestones/1.2-input-layer/logs.md`.

**Commit:** `4e37e9f` — `feat(milestone-1.2): skema payload dan logic validasi input layer`

---

## Checkpoint 3 — Endpoint FastAPI

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 10 — Tulis `src/main.py`

**Kesesuaian dengan plan:** Menyimpang dari plan di satu detail teknis — lihat Temuan.

**Apa yang dilakukan**
`FastAPI(lifespan=...)` dengan `setup_tracing(SERVICE_NAME)` dipanggil sekali saat startup (pola `lifespan` async context manager, bukan `@app.on_event("startup")` yang sudah deprecated). Endpoint `POST /v1/turns` menerima body sebagai `dict` (FastAPI parse JSON mentah, bukan lewat parameter bertipe `TurnPayload`), memanggil `validate_turn_payload()`, mengembalikan `payload.model_dump()` (echo) dengan status `200` kalau sukses.

**Temuan**
Plan menyatakan "FastAPI otomatis mengembalikan `422`... dimanfaatkan langsung (bukan custom exception handler)" — ini **keliru** dan dikoreksi saat implementasi. FastAPI hanya otomatis menangani `RequestValidationError` miliknya sendiri (dipicu saat parameter endpoint bertipe model Pydantic divalidasi FastAPI sendiri sebelum handler jalan). Karena desain checkpoint ini sengaja memanggil `TurnPayload.model_validate()` secara manual di dalam `validate_turn_payload()` (supaya fungsi itu tetap murni & bisa diuji lepas dari HTTP, sesuai Checkpoint 2), exception yang dilempar adalah `pydantic.ValidationError` biasa — yang TIDAK ditangani otomatis oleh FastAPI dan akan jadi `500` kalau dibiarkan. Diperbaiki dengan mendaftarkan `@app.exception_handler(ValidationError)` yang mengonversinya jadi `422` dengan detail per-field (`exc.errors()`) — pola resmi yang didokumentasikan FastAPI untuk kasus validasi manual di luar parameter endpoint.

**Error/Kegagalan (jika ada)**
Percobaan pertama (sebelum exception handler ditambahkan) mengembalikan `500 Internal Server Error` untuk payload tidak valid, bukan `422` — diketahui lewat pengujian `curl` manual sebelum ditulis ke Task ini, langsung diperbaiki.

**Diagnosis dan Perbaikan**
Lihat Temuan di atas.

**Hasil Verifikasi:** *(digabung Task 10a — server dijalankan & diuji `curl` nyata)*

**Commit:** *(lihat Task 10a)*

---

### Task 10a — Verifikasi curl nyata, catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan (setelah perbaikan Task 10 di atas).

**Apa yang dilakukan**
`uv run uvicorn src.main:app --port 8000` dijalankan di background, dikonfirmasi `startup complete` dari log dan `GET /docs` → `200`. Empat request `curl` dikirim ke `POST /v1/turns`.

**Hasil Verifikasi**
- Payload valid `turn_index=1` → `200`, body echo payload tervalidasi (`previous_turn: null`).
- Payload valid `turn_index=2` + `previous_turn` → `200`, body echo lengkap termasuk `previous_turn`.
- Payload tanpa `role_title` → `422`, `detail[0].loc=["role_title"]`, `msg="Field required"`.
- Payload `role_title="Bukan Role"` (tidak dikenal) → `422`, `detail[0].loc=["role_title"]`, `msg="Value error, role_title tidak dikenal: 'Bukan Role'"`.

Keempatnya sesuai ekspektasi persis. Server dihentikan setelah verifikasi (`kill` proses background).

**Commit:** *(diisi setelah commit dieksekusi)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Update `infra/observability/README.md` (referensi path `genai_semconv.py`) di Task 3 — bukan task baru, perluasan kecil dari file list Task 3 yang sudah direncanakan, dicatat eksplisit di atas. Perbaikan exception handler `ValidationError` di Task 10 juga bukan task baru — koreksi kesalahan asumsi teknis di deskripsi plan sendiri, dicatat eksplisit di Task 10 alih-alih diam-diam diubah.
