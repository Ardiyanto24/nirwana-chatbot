# Logs — Milestone 1.5: Membangun Penarikan Data dari Session Memory

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `3adc5a9` | `docs(milestone-1.5): decisions` |
| 2 | `34619bf` | `chore(milestone-1.5): tambah dependency sqlmodel dan psycopg + konfigurasi env` |
| 3 | `9fd8397` | `feat(milestone-1.5): konfigurasi koneksi database supabase` |
| 4 | `d45c4e8` | `feat(milestone-1.5): skema tabel session memory dan roles` |
| 5 | `dcf8d81` (fix), `9061a56` | `fix(milestone-1.5): simpan label_bentuk_jawaban/status sebagai str polos` + `feat(milestone-1.5): mekanisme store session memory` |
| 6 | `4c29a5e` | `feat(milestone-1.5): mekanisme retrieve session memory + span memory.retrieve` |
| 7 | `5f22870` | `test(milestone-1.5): skenario uji session memory dan verifikasi span nyata` |
| 8 | `1ac41eb` | `feat(milestone-1.5): seed tabel roles dari roles.yaml` |
| 9 | `e014cf3` | `feat(milestone-1.5): migrasi load_valid_roles ke database` |
| 10 | `de5d685` | `chore(milestone-1.5): hapus roles.yaml pasca migrasi` (satu commit, bukan dua seperti rencana plan — lihat Task 16-17 di bawah) |
| 11 | *(commit ini)* | `docs(milestone-1.5): logs, report` + `docs: perbarui status project` |

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama sebelum kode apa pun.

**Apa yang dilakukan**
11 entri keputusan awal: 3 Jenis A (genuinely terbuka lewat `AskUserQuestion` — Supabase, SQLModel, migrasi `roles.yaml`) dan 8 Jenis B (forced/preseden). Dua entri lagi (Keputusan 12, 13) ditambahkan belakangan saat temuan mid-implementation muncul (lihat Checkpoint 3 dan 5).

**Commit:** `3adc5a9`

---

## Checkpoint 2 — Dependency & Konfigurasi Environment

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 2-3 — Dependency + `.env.example`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv add sqlmodel "psycopg[binary]"` (menambah `sqlmodel==0.0.39`, `sqlalchemy==2.0.52`, `psycopg==3.3.4`, `psycopg-binary==3.3.4`, `greenlet`, `tzdata`). `.env.example` tambah `DATABASE_URL=`.

**Hasil Verifikasi**
`uv run python -c "import sqlmodel, psycopg"` berhasil tanpa error.

**Commit:** `34619bf`

---

## Checkpoint 3 — Koneksi Database (Supabase)

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 4 — `src/config/database.py`

**Kesesuaian dengan plan:** Sesuai plan, dua temuan mid-implementation diperbaiki di tempat (dicatat `decisions.md` Keputusan 12).

**Apa yang dilakukan**
`get_engine()` — `DATABASE_URL` dari environment, `create_engine()` cached via `@lru_cache`.

**Temuan/Error**
1. Percobaan pertama: `.env` sudah ada tapi `DATABASE_URL` kosong — user diminta mengisi sendiri (kredensial Supabase, tidak diminta ditempel ke chat).
2. Setelah diisi (koneksi "Direct connection"): `ModuleNotFoundError: No module named 'psycopg2'` — SQLAlchemy default me-resolve skema `postgresql://` ke driver `psycopg2` (tidak diinstal, proyek sengaja pakai `psycopg` v3). Diperbaiki: `get_engine()` menormalisasi skema jadi `postgresql+psycopg://` eksplisit.
3. Setelah dialect diperbaiki: `psycopg.OperationalError: failed to resolve host 'db.xxx.supabase.co'`. Investigasi `nslookup` mengonfirmasi hostname *direct connection* Supabase hanya punya alamat IPv6, jaringan lokal tidak mendukung IPv6 — keterbatasan Supabase yang sudah dikenal luas. User diminta ganti ke connection string **Connection Pooler** (Transaction/Session mode, IPv4-compatible).

**Hasil Verifikasi**
Setelah ganti ke pooler: koneksi nyata berhasil (`SELECT 1` → `(1,)`).

**Commit:** `9fd8397`

---

## Checkpoint 4 — Skema Tabel Database

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 5-8 — `src/db/models.py`, `src/schemas/session_memory.py`, buat tabel, update `CLAUDE.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`SessionMemoryPackageRow`/`RoleRow` (SQLModel `table=True`), `SessionMemoryPackage`/`LabelBentukJawaban`/`StatusEksekusi` (Pydantic murni). `SQLModel.metadata.create_all(engine)` dijalankan. `CLAUDE.md`/`AGENT.md` diperbarui (baris `src/`, folder `src/db/` baru).

**Hasil Verifikasi**
Query langsung ke `information_schema.columns` mengonfirmasi kedua tabel (`session_memory_packages` 10 kolom, `roles` 2 kolom) benar-benar ada dengan tipe kolom yang benar (termasuk `USER-DEFINED` untuk enum native Postgres — kemudian direvisi di Checkpoint 5, lihat Temuan di sana).

**Commit:** `d45c4e8`

---

## Checkpoint 5 — Mekanisme Store

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 9 — `store_session_memory()`

**Kesesuaian dengan plan:** Sesuai plan, satu bug ditemukan dan diperbaiki (dicatat `decisions.md` Keputusan 13).

**Apa yang dilakukan**
`store_session_memory(package)` — konversi `SessionMemoryPackage` → `SessionMemoryPackageRow`, insert.

**Temuan/Error**
Smoke test pertama menemukan `label_bentuk_jawaban`/`status` tersimpan sebagai **nama member Python** (`"NILAI_TUNGGAL"`), bukan **value string** yang dikunci arsitektur (`"nilai_tunggal"`) — perilaku default kolom Enum native Postgres SQLAlchemy. Diperbaiki: kolom diubah jadi `str` polos di `src/db/models.py`, `store_session_memory()` pakai `model_dump(mode="json")` supaya `StrEnum` diserialisasi ke `.value` dengan benar.

**Insiden terkait (near-miss, tidak ada kerusakan):** Saat membersihkan tipe ENUM Postgres lama sebelum recreate tabel, dijalankan `SELECT typname FROM pg_type WHERE typtype='e'` **tanpa filter schema** — hasil query ikut menangkap tipe internal Supabase sendiri (`auth.factor_type`, `auth.aal_level`, `storage.buckettype`, `realtime.action`, dst — 11 tipe sistem di luar milik proyek ini). `DROP TYPE IF EXISTS` kemudian dijalankan untuk semua hasil tanpa schema-qualifier. **Diverifikasi ulang segera** lewat query `pg_type` + `pg_namespace`: seluruh 11 tipe sistem tersebut **masih utuh** (schema `auth`/`storage`/`realtime`), hanya 2 tipe milik proyek sendiri (`labelbentukjawaban`, `statuseksekusi`, schema `public`) yang benar-benar terhapus — `search_path` koneksi default `public` membuat `DROP TYPE IF EXISTS` tanpa schema-qualifier terhadap tipe di schema lain jadi no-op aman. Dikonfirmasi lebih lanjut: `information_schema.tables` schema `auth` tetap 23 tabel. **Tidak ada kerusakan nyata**, tapi dicatat eksplisit sebagai insiden yang seharusnya dihindari — user diberi tahu langsung saat kejadian. Pelajaran diterapkan: query administratif ke Supabase sejak ini wajib schema-qualified eksplisit.

**Hasil Verifikasi**
Setelah perbaikan: tabel `session_memory_packages` dibuat ulang, smoke test insert ulang mengonfirmasi `label_bentuk_jawaban='nilai_tunggal'`, `status='berhasil'` (query langsung). Baris smoke test dibersihkan.

**Commit:** `dcf8d81` (fix), `9061a56` (feat)

---

## Checkpoint 6 — Mekanisme Retrieve + Span

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 10 — `retrieve_session_memory()` + span `memory.retrieve`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`retrieve_session_memory(session_id, turn_index)` — query `WHERE session_id=... AND turn_index=...`, span `memory.retrieve` (`session.id`, `turn.index`, `memory.packages_found`).

**Hasil Verifikasi**
Smoke test (`setup_tracing()` eksplisit): (a) simpan paket lalu retrieve dengan key sama → `results[0] == pkg` True; (b) retrieve turn tidak ada (`turn_index=99`) → list kosong. Span dikonfirmasi nyata di Jaeger untuk KEDUA skenario: `memory.packages_found=1`/`session.id=smoke-1.5-retrieve`/`turn.index=1` dan `memory.packages_found=0`/`turn.index=99`. Data smoke test dibersihkan.

**Commit:** `4c29a5e`

---

## Checkpoint 7 — Test Suite Formal (Kriteria Keberhasilan)

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 11-13 — Skenario, `test_session_memory.py`, jalankan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dua fungsi test sesuai dua Kriteria Keberhasilan, `session_id` berprefix `"test-"`, teardown eksplisit (`DELETE ... WHERE session_id=...` di blok `finally`).

**Hasil Verifikasi**
`uv run pytest tests/layers/context_resolution/test_session_memory.py -v` → 2/2 passed (4.38s). Query ulang `SELECT count(*) WHERE session_id LIKE 'test-%'` → 0 (teardown terbukti bersih).

**Commit:** `5f22870`

---

## Checkpoint 8 — Seed Tabel Roles

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 14 — Skrip seed

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`milestones/1.5-tarik-session-memory/seed_roles.py` — baca `roles.yaml`, insert 20 baris ke tabel `roles`.

**Hasil Verifikasi**
Dijalankan: "20 role di-seed ke tabel roles." Perbandingan set eksplisit (`yaml_roles == db_roles`) → `True`, selisih kosong.

**Commit:** `1ac41eb`

---

## Checkpoint 9 — Migrasi Kode `roles.py` ke Database

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 15 — Ubah `load_valid_roles()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Query tabel `roles` alih-alih baca YAML, `@lru_cache(maxsize=1)` dipertahankan.

**Hasil Verifikasi**
`load_valid_roles()` → 20 role, `"CEO"` dan `"Front Office Staff"` terkonfirmasi ada.

**Commit:** `e014cf3`

---

## Checkpoint 10 — Regresi + Hapus `roles.yaml`

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 16 — Regresi `test_input_layer.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Hasil Verifikasi**
`uv run pytest tests/layers/test_input_layer.py -v` → 12/12 passed (3.76s), sumber role sekarang dari DB.

### Task 17 — Verifikasi ulang data sebelum hapus

**Kesesuaian dengan plan:** Sesuai plan.

**Hasil Verifikasi**
Re-cek `yaml_roles == db_roles` → `True` (tepat sebelum penghapusan, terpisah dari cek Checkpoint 8).

### Task 18 — Hapus `roles.yaml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`rm src/config/roles.yaml`. `grep "roles.yaml"` di `src/` → tidak ada hasil (tidak ada referensi tersisa). Test suite dijalankan ulang sekali lagi setelah penghapusan → 12/12 tetap passed.

**Penyimpangan dari plan:** Rencana plan menyebut 2 commit terpisah untuk checkpoint ini (`test(...): verifikasi regresi` + `chore(...): hapus roles.yaml`). Karena Task 16-17 (regresi + verifikasi ulang) tidak mengubah file apa pun (murni menjalankan test/query yang sudah ada), tidak ada diff untuk di-commit sebagai commit "test" terpisah — jadi hanya **satu commit** (`chore`) yang benar-benar terjadi, mencakup hasil kedua verifikasi di badan pesan commit.

**Commit:** `de5d685`

---

## Checkpoint 11 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 19-22 — `logs.md`, `report.md`, `keputusan-tertunda.md`, `CLAUDE.md`/`AGENT.md`

Entri Checkpoint 1-10 di atas ditulis sebagai bagian Task 19. Lihat `report.md`, `docs/keputusan-tertunda.md`, dan `CLAUDE.md`/`AGENT.md` untuk Task 20-22.

**Commit:** *(lihat commit gabungan di bawah)*

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada checkpoint baru di luar plan. Penyimpangan task (semuanya koreksi/penyesuaian di dalam task yang sudah direncanakan, dicatat eksplisit di masing-masing entri): normalisasi dialect + pooler Checkpoint 3; perbaikan penyimpanan enum + insiden near-miss `DROP TYPE` Checkpoint 5; konsolidasi 2 commit rencana jadi 1 commit nyata Checkpoint 10 (tidak ada diff terpisah untuk verifikasi murni).

---

## Addendum (2026-08-18) — Fix `try/except` di `retrieve_session_memory()`

**Ditemukan:** Milestone 7.7 (investigasi sebelum plan, saat memetakan percabangan paralel Rewrite+Tarik Memory) — `retrieve_session_memory()` tidak punya `try/except` sama sekali di sekitar query DB-nya, beda dari `store_session_memory()` di file yang sama (lihat `decisions.md` Keputusan 14 untuk detail lengkap).

**Apa yang dilakukan:** `src/layers/context_resolution/session_memory.py::retrieve_session_memory()` dibungkus `try/except Exception: span.set_attribute("error.type", "gagal_teknis"); raise` — mirror persis pola `store_session_memory()`. Test baru `tests/layers/context_resolution/test_session_memory_kegagalan.py::test_kegagalan_db_saat_retrieve_menghasilkan_error_type_lalu_raise_ulang` (mock `_SessionExecGagal` baru, mirror fixture `_TracerRekam`/`_SpanRekam` yang sudah ada).

**Hasil Verifikasi**
```
$ .venv/Scripts/python.exe -m pytest tests/layers/context_resolution/test_session_memory_kegagalan.py -v
test_kegagalan_db_menghasilkan_error_type_lalu_raise_ulang PASSED
test_kegagalan_db_atribut_session_turn_atomic_intent_tetap_tercatat PASSED
test_kegagalan_db_saat_retrieve_menghasilkan_error_type_lalu_raise_ulang PASSED
3 passed in 3.64s
```
Regresi dicek lewat full suite `tests/layers/context_resolution/` (14 test) — 13 passed, 1 gagal (`test_matching.py::test_kelompok_c_rantai_arsip_ulang_turn_tujuh_lima_tiga`, M1.7 Pencocokan Atomic Intent) TIDAK TERKAIT perubahan ini: perubahan hanya membungkus jalur sukses `retrieve_session_memory()` yang sudah ada dalam `try/except` tanpa mengubah logic/return value sama sekali saat tidak ada exception. Diverifikasi ulang dengan menjalankan test itu sendirian dua kali — gagal dengan alasan BERBEDA tiap kali (`assert 2 == 1`, ternyata menemukan 2 baris duplikat dengan `atomic_intent_id` identik untuk `session_id="test-m17-kelompok-c"` yang di-hardcode, bukan di-randomize per-run seperti fixture test lain) — mengonfirmasi ini murni masalah isolasi test M1.7 pra-eksisting (data menumpuk di Supabase nyata antar-run test karena `session_id` tetap, bukan kegagalan yang disebabkan perubahan `session_memory.py`). Dicatat sebagai observasi, tidak diperbaiki di sini (di luar Lingkup M7.7/addendum M1.5 ini, kepemilikan test itu ada di M1.7).

**Commit:** `2ef5012` (fix), `5be7f0d` (test).
