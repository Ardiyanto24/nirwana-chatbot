# Logs — Milestone 2.2: Membangun Pemeriksaan Otorisasi

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `e6e2170` | `docs(milestone-2.2): decisions` |
| 2 | `12e2c67` | `feat(milestone-2.2): skema data otorisasi` |
| 3 | *(commit ini)* | `feat(milestone-2.2): tabel role_permissions` + `chore(milestone-2.2): seed matriks role_permissions` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama, sebelum kode apa pun, setelah plan disetujui user lewat Plan Mode (riset langsung ke `rancangan-rbac-authorization.md` Milestone 2.2, `api-chatbot.md` kredensial `chatbot_authz_reader`, kontrak span, dan kode preseden `seed_roles.py`/`src/db/models.py`/`src/config/roles.py`).

**Apa yang dilakukan**
11 entri keputusan: 10 Jenis B forced/preseden (larangan query produksi langsung, mekanisme deterministik tanpa LLM, output granular per domain, tidak menangani access_scope, tidak ada folder evals/, subpackage domain_gate/ yang sama, file skema terpisah, pola seed di milestones/, entri GAGAL_TEKNIS dilewati, decisions.md sebagai task pertama), 1 Jenis A genuinely terbuka dari `AskUserQuestion` (sumber matriks — tabel Supabase baru, bukan konstanta Python statis).

**Temuan**
Dikonfirmasi lewat `api-chatbot.md` baris 29-30: kredensial `chatbot_authz_reader` untuk query `mart_cleaned.role_permissions` eksklusif milik Milestone 4.4 — M2.2 (Lapis 1) definitif tidak punya jalur akses ke tabel produksi ini, memaksa kebutuhan salinan matriks sendiri.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `e6e2170`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 2 — `src/schemas/authorization.py`

**Kesesuaian dengan plan:** Sesuai plan — unit test dedicated ditunda ke `tests/layers/domain_gate/test_otorisasi.py` (Checkpoint 4-5), sesuai opsi eksplisit yang sudah disebut plan sendiri ("mirror preseden M2.1 Checkpoint 2"). Sanity check manual dijalankan langsung (4 kasus: true/alasan-none valid, false/alasan-terisi valid, false/alasan-none ditolak, true/alasan-terisi ditolak) untuk konfirmasi cepat sebelum lanjut, bukan pengganti unit test formal.

**Apa yang dilakukan**
`DomainAuthorization` (`domain: Domain` reuse M2.1, `diizinkan: bool`, `alasan: str | None`) dengan validator `alasan_konsisten_dengan_diizinkan`, dan `AtomicIntentAuthorization` (`atomic_intent`, `domain_decisions: list[DomainAuthorization]`).

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Sanity check manual (`uv run python -c "..."`) — 4/4 kasus validator berperilaku benar (2 valid diterima, 2 invalid ditolak `ValidationError`).

**Commit:** `12e2c67`

---

## Checkpoint 3 — Tabel Role Permissions + Seed

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 3 — `RolePermissionRow` (`src/db/models.py`)

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`RolePermissionRow` (tabel `role_permissions`, kolom `role_title`+`domain`, satu baris = satu izin granted) ditambahkan ke `src/db/models.py`, docstring eksplisit membedakan dari tabel produksi.

### Task 4 — `seed_role_permissions.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu langkah tambahan yang tidak eksplisit disebut task tapi perlu (forced oleh kondisi nyata): tabel `role_permissions` belum ada secara fisik di Supabase sebelum seed pertama kali dijalankan (`UndefinedTable` error) — dijalankan `SQLModel.metadata.create_all(engine)` sekali (mirror mekanisme migrasi M1.5, idempotent, tidak menyentuh tabel lain yang sudah ada) sebelum retry seed.

**Apa yang dilakukan**
Transkripsi manual 20 role × domain granted dari `rancangan-rbac-ai-chatbot.md` Bagian 2 (baris 45-64) ke `ROLE_PERMISSIONS: dict[str, list[str]]`, di-assert `len == 20` sebelum insert. Dijalankan nyata terhadap Supabase.

**Temuan**
Tidak ada temuan baru (selain kondisi tabel belum ada, sudah dicatat di atas).

**Error/Kegagalan (jika ada)**
`psycopg.errors.UndefinedTable: relation "role_permissions" does not exist` pada percobaan pertama jalankan seed — diselesaikan dengan `create_all(engine)` (lihat Diagnosis).

**Diagnosis dan Perbaikan**
Root cause: tabel baru (`RolePermissionRow`) ditambahkan ke `SQLModel` metadata tapi belum pernah di-`create_all()` di database nyata (beda dari `roles`/`session_memory_packages` yang sudah dibuat saat M1.5). Perbaikan: jalankan `SQLModel.metadata.create_all(get_engine())` sekali — operasi idempotent, HANYA membuat tabel yang belum ada, tidak menyentuh/drop tabel lain (mirror mekanisme migrasi M1.5, `decisions.md` M1.5 Keputusan: "TANPA Alembic, `SQLModel.metadata.create_all()` cukup").

**Hasil Verifikasi**
`74 baris izin di-seed ke tabel role_permissions (20 role)` — cocok persis perhitungan manual sebelum eksekusi (`total rows: 74`, dihitung dari dict `ROLE_PERMISSIONS` sebelum dikirim ke DB). **Cross-check manual lengkap**: query `SELECT * FROM role_permissions ORDER BY role_title` dikelompokkan per role, dibandingkan SATU-PER-SATU terhadap `rancangan-rbac-ai-chatbot.md` Bagian 2 — seluruh 20 role cocok PERSIS (jumlah domain per role DAN domain spesifiknya), termasuk kasus yang mudah salah transkripsi (CEO=10/all, General Manager=8/enam-operasional+2-granular-tanpa-guests, Corporate Revenue Director=5/reservation+financial+properties_ref+guests_pii+guests_profile-tanpa-employees_directory).

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
