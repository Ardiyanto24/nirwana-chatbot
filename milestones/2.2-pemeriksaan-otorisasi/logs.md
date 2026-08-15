# Logs — Milestone 2.2: Membangun Pemeriksaan Otorisasi

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `e6e2170` | `docs(milestone-2.2): decisions` |
| 2 | `12e2c67` | `feat(milestone-2.2): skema data otorisasi` |
| 3 | `5321e33`, `a164fe2` | `feat(milestone-2.2): tabel role_permissions` + `chore(milestone-2.2): seed matriks role_permissions` |
| 4 | `b1cf77a`, `b654f03` | `feat(milestone-2.2): mekanisme lookup otorisasi` + `test(milestone-2.2): verifikasi exhaustive 200 kombinasi role-domain` |
| 5 | *(commit ini)* | `feat(milestone-2.2): orkestrator periksa otorisasi + observability` + `test(milestone-2.2): skenario multi-domain campuran` |

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

**Commit:** `5321e33`, `a164fe2`

---

## Checkpoint 4 — Mekanisme Lookup + Verifikasi Exhaustive (KK1)

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 5 — `src/config/role_permissions.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`load_role_permissions() -> dict[str, frozenset[Domain]]` (`@lru_cache`), mirror pola `load_valid_roles()` M1.5.

### Task 6 — `src/layers/domain_gate/otorisasi.py` (`periksa_domain`)

**Kesesuaian dengan plan:** Sesuai plan — file ditulis DUA TAHAP secara sengaja (bukan langsung penuh seperti draft awal): `periksa_domain()` dulu (Checkpoint 4 murni), orkestrator (`periksa_otorisasi_atomic_intent`/`periksa_otorisasi_semua`) ditunda ke Checkpoint 5 - supaya tiap checkpoint benar-benar diverifikasi+commit terpisah sebelum lanjut (draft awal sempat menulis semuanya sekaligus, dikembalikan ke cakupan Checkpoint 4 saja sebelum commit pertama).

**Apa yang dilakukan**
`periksa_domain(domain, role_title) -> DomainAuthorization` — murni fungsi tanpa span (span di level orkestrator, Checkpoint 5).

### Task 7 — Unit Test Exhaustive (KK1)

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`tests/layers/domain_gate/test_otorisasi.py` — ekspektasi `_EXPECTED_GRANTED_ROLES` ditranskripsi ULANG independen dari `seed_role_permissions.py`, dengan struktur SENGAJA dibalik (domain-per-domain, bukan role-per-role seperti skrip seed) untuk memaksa pass transkripsi yang genuinely berbeda, bukan copy-paste. Parametrized test 20 role × 10 domain = 200 kasus + 1 sanity check total (74).

**Temuan**
Dua transkripsi INDEPENDEN (role-per-role di `seed_role_permissions.py` Checkpoint 3, domain-per-domain di test ini) menghasilkan total identik (74) DAN seluruh 200 kombinasi cocok persis — bukti kuat transkripsi matriks bebas dari kesalahan (dua metode berbeda, hasil sama, kecil kemungkinan keduanya salah dengan cara yang sama persis).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_otorisasi.py -v` — **201/201 PASSED** (200 kombinasi role×domain + 1 sanity check total baris) dalam 4.06s. **KK1 terbukti langsung**: "Seluruh kombinasi role × domain yang tercatat di `role_permissions` diuji sistematis (bukan sampel), dan hasil izin/tolaknya cocok persis dengan tabel rujukan."

**Commit:** `b1cf77a`, `b654f03`

---

## Checkpoint 5 — Orkestrator + Observability

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 8 — `periksa_otorisasi_atomic_intent()`/`periksa_otorisasi_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`periksa_otorisasi_atomic_intent()` — span `authorization.check` PER domain (atribut `rbac.domain`, `rbac.decision`, `error.type=ditolak_otorisasi` bila ditolak). `periksa_otorisasi_semua()` — filter lewati `GAGAL_TEKNIS`, span pembungkus agregat `domain_gate.periksa_otorisasi_semua` (`intent.count`, `authorization.ditolak_count`).

### Task 9 — Unit Test KK2

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`test_kk2_multi_domain_sebagian_diizinkan_sebagian_ditolak` (Front Office Staff: `reservation` diizinkan, `financial` ditolak, dalam SATU pemanggilan) dan `test_periksa_otorisasi_semua_melewati_gagal_teknis` (entri `GAGAL_TEKNIS` tidak menghasilkan `AtomicIntentAuthorization`).

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/ -v -k "not kelompok"` — **218/218 PASSED** (200 exhaustive + 1 sanity + 2 test baru Checkpoint 5 dari `test_otorisasi.py`, + 15 test pure-function M2.1 tanpa regresi) dalam 6.23s. **KK2 terbukti langsung**: hasil `domain_decisions` benar per domain (`reservation`=diizinkan, `financial`=ditolak) dalam satu `AtomicIntentAuthorization`, bukan keputusan tunggal yang menyamaratakan.

**Commit:** `d74729a`, `df8913a`

---

## Checkpoint 6 — Verifikasi Span Nyata

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 10 — Verifikasi span di Jaeger

**Kesesuaian dengan plan:** Sesuai plan. Docker/Jaeger dari Milestone 2.1 masih berjalan (tidak perlu restart).

**Apa yang dilakukan**
Skrip verifikasi one-off (scratchpad, TIDAK di-commit) memanggil `setup_tracing()` + `periksa_otorisasi_semua()` nyata untuk skenario campuran (Front Office Staff: `reservation`+`financial`, hanya `reservation` yang diizinkan), dibungkus span `invoke_agent`. Trace di-query langsung lewat Jaeger API.

**Temuan**
Span pertama (`authorization.check` untuk `reservation`) memakan ~1.09 detik — jauh lebih lama dari span kedua (`financial`, 452 mikrodetik). Ini bukan anomali, melainkan `load_role_permissions()` (`@lru_cache`) melakukan query DB nyata pertama kali dipanggil (cold start), setelahnya seluruh pemanggilan berikutnya murni in-memory — perilaku sesuai desain.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Trace (`trace_id=450aefbb4416a3bd7ae9d47eafb237b0`) — span `invoke_agent` (session.id, turn.index) → `domain_gate.periksa_otorisasi_semua` (`intent.count=1`, `authorization.ditolak_count=1`) → 2× span `authorization.check`: (1) `rbac.domain=reservation`, `rbac.decision=allow`, tanpa `error.type`; (2) `rbac.domain=financial`, `rbac.decision=deny`, `error.type=ditolak_otorisasi`. Seluruh atribut terkonfirmasi ADA dan benar sesuai kontrak Bagian 2 `rancangan-observability-ai-chatbot.md` baris 38.

**Commit:** *(pending — commit setelah entri ini ditulis, hanya logs.md - tidak ada file kode baru sesuai plan)*

---
