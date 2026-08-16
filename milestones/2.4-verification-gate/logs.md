# Logs — Milestone 2.4: Membangun Verification Gate

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `75e546a` | `docs(milestone-2.4): decisions` |
| 2 | `17422cf`, `e41b26b` | `feat(milestone-2.4): skema data verification gate` + `test(milestone-2.4): validator HasilVerifikasiGate` |
| 3 | `d2231fc`, `571775b` | `feat(milestone-2.4): katalog 67 view per domain` + `test(milestone-2.4): verifikasi katalog 67 view` |
| 4 | `300406e`, `136a7a1` | `feat(milestone-2.4): tabel employees` + `chore(milestone-2.4): seed tabel employees` |
| 5 | `29fb044`, `14d7dd9` | `feat(milestone-2.4): cek 1 bentuk request statis` + `test(milestone-2.4): verifikasi cek 1 bentuk request statis` |
| 6 | `02527e7`, `f802d3b` | `feat(milestone-2.4): cek 2 kepatuhan sumber` + `test(milestone-2.4): verifikasi KK2 kepatuhan sumber` |
| 7 | `fed65fe`, `820349f` | `feat(milestone-2.4): cek 3-4 penegakan constraint + kelengkapan` + `test(milestone-2.4): verifikasi KK1 penegakan constraint` |
| 8 | `3982b7e`, `ff3c5bf`, `d3dafef` | `feat(milestone-2.4): loader tabel employees` + `feat(milestone-2.4): orkestrator verifikasi_gate + observability` + `test(milestone-2.4): verifikasi KK1-3 end-to-end` |
| 9 | *(menyusul)* | `docs(milestone-2.4): verifikasi span nyata` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan. Dua keputusan genuinely terbuka (konvensi filter employee_id, tabel employees) dikonfirmasi lewat DUA putaran `AskUserQuestion` SEBELUM plan ditulis (putaran pertama mengajukan gap kontrak, putaran kedua setelah user meminta klarifikasi dan memberikan `employees_deduped.csv` nyata) — `decisions.md` di sini mendokumentasikan hasil konfirmasi itu.

**Apa yang dilakukan**
9 entri keputusan: 2 Jenis A genuinely terbuka (konvensi employee_id sebagai filter cakupan-individu — eksplisit ditandai PROVISIONAL/belum dikonfirmasi tim database engineering; tabel employees Supabase khusus fixture test), 7 Jenis B forced/preseden (subpackage verification_gate/ terpisah dari domain_gate/, params tetap dict opaque, error.type=gagal_teknis, verification.check_name 4 nilai, tidak ada folder evals/, hire_date str polos karena inkonsistensi data nyata, decisions.md sebagai task pertama).

**Temuan**
Riset kontrak sebelum plan (agent Explore) mengonfirmasi gap arsitektur nyata: `api-chatbot.md` tidak mendokumentasikan parameter apa pun untuk filter level-individu — `staff_id=self` di dokumen arsitektur (baris 187) murni ilustrasi, bukan parameter terkontrak. Ini BUKAN kegagalan riset, melainkan keterbatasan nyata dokumen sumber yang harus ditangani sebagai keputusan provisional, bukan diasumsikan pasti benar.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `75e546a`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 2 — `src/schemas/verification_gate.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`QueryEngineRequest` (`domain`, `view_name`, `params: dict[str, Any]`), `HasilVerifikasiGate` (`request_final`/`lolos`/`terkoreksi`/`alasan_penolakan` + validator konsistensi).

**Temuan**
`tests/layers/verification_gate/__init__.py` dan `src/layers/verification_gate/__init__.py` belum ada (subpackage baru) — `ModuleNotFoundError: No module named 'src'` saat collect test pertama kali, diperbaiki dengan menambah kedua file `__init__.py` kosong (mirror struktur `domain_gate/`).

**Commit:** `17422cf`

### Task 3 — Test validator `HasilVerifikasiGate`

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/test_verification_gate.py` — 6/6 PASSED.

**Error/Kegagalan (jika ada)**
Tidak ada (di luar `__init__.py` yang hilang, sudah diperbaiki di Task 2).

**Commit:** `e41b26b`

---

## Checkpoint 3 — Katalog 67 View

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 4 — `katalog_view.py` + test

**Kesesuaian dengan plan:** Sesuai plan.

**Temuan**
Dua dari 67 view TIDAK mengikuti konvensi awalan `v_`: `guests_contact_view` (domain `guests_pii`) dan `guests_profile_view` (domain `guests_profile`) — pengecualian nyata di `katalog-data-chatbot.md` baris 971/983, dipertahankan persis sesuai dokumen sumber (bukan "dikoreksi" ke `v_guests_*` yang tidak ada).

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/test_katalog_view.py` — 5/5 PASSED: total 67, seluruh 10 domain tercakup, count per domain cocok PERSIS tabel `api-chatbot.md` (ekspektasi ditranskripsi independen), tidak ada duplikat lintas domain, pengecualian penamaan guests eksplisit diuji.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `d2231fc` (kode), `571775b` (test)

---

## Checkpoint 4 — Tabel `employees` + Seed

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 5 — `EmployeeRow` di `src/db/models.py`

**Apa yang dilakukan**
`EmployeeRow` (SQLModel `table=True`) dengan docstring eksplisit menegaskan tabel ini HANYA fixture test.

**Commit:** `300406e`

### Task 6 — Salin CSV + `seed_employees.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`employees_deduped.csv` disalin dari `nirwana-web` (repo sibling, sumber asli, TIDAK dimodifikasi) ke `milestones/2.4-verification-gate/`. `seed_employees.py` membaca CSV, `.strip()` tiap field, insert 84 `EmployeeRow`.

**Hasil Verifikasi**
Dijalankan nyata: `84 baris karyawan di-seed ke tabel employees.` Query langsung Supabase: `SELECT COUNT(*) FROM employees` = 84, sample row `E0013` (Kamila Pranowo, F&B Manager, P01) cocok persis isi CSV.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `136a7a1`

---

## Checkpoint 5 — Cek 1: Bentuk Request Statis

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 7-8 — `verifikasi_bentuk_request_statis()` + test

**Kesesuaian dengan plan:** Sesuai plan. Domain validity tidak diperiksa terpisah - dijamin otomatis oleh tipe `Domain` Pydantic saat `QueryEngineRequest` dikonstruksi (tidak bisa membuat instance dengan domain invalid sama sekali).

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/test_verifikasi_gate.py` — 6/6 PASSED (valid, view_name tidak ada, view_name di domain lain, limit melebihi/persis 1000, tanpa limit).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `29fb044` (kode), `14d7dd9` (test)

---

## Checkpoint 6 — Cek 2: Kepatuhan Sumber (KK2)

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 9-10 — `verifikasi_kepatuhan_sumber()` + test KK2

**Kesesuaian dengan plan:** Sesuai plan.

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/test_verifikasi_gate.py` — 8/8 PASSED. KK2 terbukti langsung: `view_name` sengaja dibuat tidak cocok dengan yang divalidasi Retriever → ditolak, `alasan_penolakan` menyebut KEDUA nilai (request dan Retriever) secara eksplisit.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `02527e7` (kode), `f802d3b` (test)

---

## Checkpoint 7 — Cek 3+4: Penegakan Constraint + Verifikasi Kelengkapan (KK1)

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 11-12 — `tegakkan_constraint_cakupan_individu()`/`verifikasi_kelengkapan_penegakan()` + test KK1

**Kesesuaian dengan plan:** Sesuai plan.

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/test_verifikasi_gate.py` — 11/11 PASSED. KK1 terbukti langsung: `params={}` + `constraint.terdeteksi=True` → `terkoreksi=True`, `params["employee_id"]` diisi persis `employee_id` caller (BUKAN ditolak). Kasus `params` sudah benar → tidak dikoreksi ulang (`terkoreksi=False`). Kasus `constraint.terdeteksi=False` → `params` sama sekali tidak berubah (dicek `==` penuh terhadap input asli).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `fed65fe` (kode), `820349f` (test)

---

## Checkpoint 8 — Orkestrator + Observability + KK1-3 End-to-End

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 13 — `load_employees()` + `verifikasi_gate()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/config/employees.py` (`load_employees()` `@lru_cache`, HANYA dipakai test). `verifikasi_gate()` orkestrator: cek1→cek2 early-exit tolak (`error.type=gagal_teknis`), cek3→cek4 kalau lolos keduanya. Span `verification_gate.check` per cek (`verification.check_name`) + span pembungkus `verification_gate.verifikasi_gate`.

**Commit:** `3982b7e` (loader), `ff3c5bf` (orkestrator)

### Task 14 — Test KK1-3 end-to-end

**Apa yang dilakukan**
3 test pakai fixture employee NYATA (`Housekeeping Staff`, `Maintenance Staff`, `HR Staff`) dari tabel `employees` (Checkpoint 4).

**Hasil Verifikasi**
`uv run pytest tests/layers/verification_gate/test_verifikasi_gate.py` — **14/14 PASSED**. KK1: `terkoreksi=True`, `params["employee_id"]` diisi persis employee nyata. KK2: `view_name` request vs Retriever sengaja tidak cocok → ditolak, alasan menyebut KEDUA nilai. KK3: request sudah benar sepenuhnya → `lolos=True`, `terkoreksi=False`, `params` IDENTIK dengan input (`==` penuh).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `d3dafef`

---

## Checkpoint 9 — Verifikasi Span Nyata

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 15 — Jalankan end-to-end + query Jaeger

**Kesesuaian dengan plan:** Sesuai plan. Docker/Jaeger masih berjalan dari Milestone 2.3 (tidak perlu restart).

**Apa yang dilakukan**
Skrip verifikasi one-off (scratchpad, TIDAK di-commit) memanggil `setup_tracing()` + `verifikasi_gate()` nyata untuk skenario KK1 (`Housekeeping Staff` E0002, domain `facility`, constraint terdeteksi), dibungkus span `invoke_agent`. Trace di-query langsung lewat Jaeger API.

**Temuan**
Trace `60fa05fa279e8af1736aa27097cbc9a6` berisi 6 span dengan hierarki benar: `invoke_agent` (root) → `verification_gate.verifikasi_gate` (`verification_gate.lolos=true`, `verification_gate.terkoreksi=true`) → 4× `verification_gate.check` dengan `verification.check_name` benar per cek (`bentuk_request_statis`, `kepatuhan_sumber`, `constraint_cakupan_individu` dengan `verification.terkoreksi=true`, `kelengkapan_penegakan`). Seluruh atribut sesuai kontrak observability dan desain Checkpoint 8.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(commit ini, docs saja)*
