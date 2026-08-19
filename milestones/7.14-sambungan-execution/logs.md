# Logs — Milestone 7.14: Sambungan 9 (Verification Gate → Execution, termasuk uji wave berulang)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan + Prasyarat Reachability `chatbot_api`

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/7.14-sambungan-execution/decisions.md` — 10 entri keputusan (1 Jenis A genuinely terbuka: desain wave, dikonfirmasi user lewat diskusi chat sebelum plan ditulis setelah penjelasan konkret skenario `gop_margin`; 9 Jenis B forced/preseden termasuk koreksi folder `chatbot_api` yang benar).

**Temuan**
Tidak ada temuan baru di luar yang sudah ditemukan sebelum plan ditulis (riset plan sudah menemukan koreksi folder `api/` vs `scripts/chatbot_api/`, signature `eksekusi_atomic_intent()` butuh `constraint`).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap, 10 entri + Daftar Isi Keputusan.

**Commit:** *(dicatat bersama Task 2)*

### Task 2 — Jalankan `chatbot_api` lokal, verifikasi reachability nyata

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Cek dependensi Python global (`fastapi 0.141.1`, `uvicorn 0.52.3`, `psycopg2`) — sudah terpasang, tidak perlu install ulang. Jalankan `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000` dari `nirwana-database/scripts/chatbot_api/` (background). `GET /health` → `200` (dikonfirmasi `curl`).

Tiga panggilan nyata berurutan (reuse skenario M4.1 Checkpoint 5: `role_title="Front Office Staff"`, `employee_id="E0071"`, `view_name="v_lookup_daily_occupancy"`, domain `reservation`, `params={"property_id": "P01"}`):
1. `panggil_chatbot_api()` (M4.1) langsung — `status_code=200`, body data occupancy nyata (8 kolom).
2. `panggil_meta_chatbot_api()` — `status_code=200`, `data_quality_status="ok"`, `last_refreshed_at="2026-08-11T06:03:04.668186+00:00"` — pertama kali fungsi ini tereksekusi terhadap server nyata sama sekali (celah spesifik yang dicatat `docs/keterbatasan-diterima.md` #13).
3. `eksekusi_atomic_intent()` (M4.2, orkestrator penuh, dipanggil langsung dengan `AtomicIntent`+`QueryEngineRequest`+`ConstraintCakupanIndividu(terdeteksi=False)` buatan tangan) — `status=StatusEksekusi.SEBAGIAN` (bukan `BERHASIL`), `retry_count_infra=0`, `revisi_count=0`, `data_quality_status="ok"`, `nilai_hasil` berisi data JSON asli.

Update `docs/keterbatasan-diterima.md` #13 — judul ditambah "DIVERIFIKASI (2026-08-19)", paragraf baru mencatat hasil ketiga panggilan di atas.

**Temuan**
`eksekusi_atomic_intent()` mengembalikan `SEBAGIAN` (bukan `BERHASIL`) untuk data nyata ini — `last_refreshed_at` (2026-08-11) lebih tua ~8 hari dari tanggal eksekusi (2026-08-19), melebihi `EXECUTION_DATA_STALENESS_THRESHOLD_JAM` (48 jam). Ini BUKAN bug — justru bukti POSITIF bahwa logika staleness M4.2 (dibangun murni via simulasi test sebelumnya) bekerja BENAR terhadap kondisi data sungguhan yang genuinely stale. Kekhawatiran risiko di `docs/keterbatasan-diterima.md` #13 ("bentuk respons HTTP nyata mungkin sedikit menyimpang dari simulasi test") TIDAK terwujud — bentuk body JSON konsisten dengan yang disimulasikan test M4.1/M4.2.

**Error/Kegagalan (jika ada)**
Percobaan pertama skrip verifikasi gagal `ModuleNotFoundError: No module named 'src.config.domain'` — import `Domain` salah lokasi.

**Diagnosis dan Perbaikan**
`Domain` enum sebenarnya ada di `src/schemas/domain_gate.py` (dikonfirmasi lewat `Grep` cepat), bukan `src/config/domain.py` yang tidak eksis. Diperbaiki, dijalankan ulang berhasil.

**Hasil Verifikasi**
3 panggilan nyata (`panggil_chatbot_api`, `panggil_meta_chatbot_api`, `eksekusi_atomic_intent`) seluruhnya `status_code=200` di level HTTP, `chatbot_api` server tetap `up` di background untuk checkpoint-checkpoint berikutnya yang butuh koneksi nyata.

**Commit:** `e6ffb66` — `docs(milestone-7.14): keputusan + verifikasi reachability chatbot_api`

---

## Checkpoint 2 — Fungsi Pengelompokan Wave (Baru, Deterministik)

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 3-4 — Bangun `kelompokkan_wave()` + unit test

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `HasilPenyusunanRequest`/`HasilVerifikasiBentukRequest` (`src/schemas/query_engine.py`) dan `AtomicIntent`/`RelasiKebutuhan` (`src/schemas/decomposition.py`) untuk memastikan bentuk tuple `query_engine_result` dan lokasi `relasi`/`bergantung_pada`. Baca pola helper fixture test existing (`tests/layers/verification_gate/test_verifikasi_gate.py::_buat_atomic_intent`/`_buat_query_engine_entry`) untuk konsistensi gaya.

Bangun `src/orchestration/wave.py::kelompokkan_wave()` — algoritma iteratif (bukan rekursif): tiap pass memindahkan item dari `remaining` ke `wave_of` begitu SELURUH dependensinya (yang genuinely ada di `by_id`) sudah py wave; level = `max(wave dependensi) + 1`, atau `1` kalau tidak ada dependensi sisa (baik independen maupun seluruh dependensi hilang). Kalau satu pass penuh TIDAK memindahkan item apa pun (`progressed=False`) — indikasi siklus — sisa item di-force ke wave fallback (`max_wave + 1` atau `1`), loop `break`.

Tulis 8 unit test standalone (`tests/orchestration/test_wave.py`): list kosong, seluruh independen (1 wave), 1 dependensi sederhana (2 wave), multi-dependensi 2 parent beda wave (level = max+1, plus 1 level lagi di bawahnya), dependensi hilang seluruhnya (masuk wave 1), dependensi SEBAGIAN hilang (pakai yang masih ada), siklus buatan 2-node (tidak infinite loop, seluruh item tetap muncul di wave fallback), dan sanity check seluruh item muncul persis sekali tanpa duplikat/hilang.

**Temuan**
Tidak ada temuan tak terduga — algoritma iteratif dengan deteksi "tidak ada progress" terbukti cukup untuk menangani siklus tanpa perlu iterasi maksimum eksplisit terpisah (loop `while remaining` otomatis `break` begitu satu pass penuh gagal memindahkan item).

**Error/Kegagalan (jika ada)**
Tidak ada — seluruh 8 test lolos percobaan pertama.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_wave.py -v` — 8/8 PASSED, 0.70s.

**Commit:** `99caf4c` (feat) + `51fc197` (test) + `5262060` (docs)

---

## Checkpoint 3 — Bangun `eksekusi_atomic_intent_semua()`

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 5-6 — Fungsi batch baru + unit test standalone

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca ulang `src/schemas/execution.py` mengonfirmasi `HasilEksekusiAtomicIntent` SUDAH membawa field `atomic_intent` (beda dari `HasilVerifikasiGate` M2.4) — return type batch function karena itu `list[HasilEksekusiAtomicIntent]` TANPA tuple pembungkus (Keputusan 5). Tambah `eksekusi_atomic_intent_semua(verification_gate_wave, cakupan_individu_result, role_title, employee_id)` di `src/layers/execution/klasifikasi_respons.py` — lookup dict `constraint_by_id` (key `atomic_intent_id`), filter item `hasil_vg.lolos=False`, panggil `eksekusi_atomic_intent(atomic_intent, hasil_vg.request_final.view_name, hasil_vg.request_final, constraint, role_title, employee_id)` per item lolos filter, span pembungkus `execution.eksekusi_atomic_intent_semua` dengan `intent.count`.

Tulis 5 unit test baru di `tests/layers/execution/test_klasifikasi_respons.py` (mocked `eksekusi_atomic_intent`): list kosong; skip `lolos=False`; argumen benar per item (atomic_intent/view_name/request/constraint/role_title/employee_id, identity check untuk `request`/`constraint`); multi-item constraint TIDAK TERTUKAR (urutan `cakupan_individu_result` sengaja dibalik dari urutan wave, mirror pola M7.13); urutan+panjang dipertahankan pada campuran lolos=True/False.

**Temuan**
Sempat ada sisa `)` yatim (artefak proses edit) yang menyebabkan `IndentationError` saat sanity import pertama — langsung terlihat dan diperbaiki sebelum lanjut ke test (lihat Error/Kegagalan).

**Error/Kegagalan (jika ada)**
`IndentationError: unexpected indent` pada baris 348 `klasifikasi_respons.py` saat `uv run python -c "from ... import eksekusi_atomic_intent_semua"` — satu baris `)` berlebih tersisa dari proses edit sebelumnya.

**Diagnosis dan Perbaikan**
Baca ulang file di sekitar baris 336-348, hapus baris `)` yatim. Sanity import berhasil setelah perbaikan.

**Hasil Verifikasi**
`uv run pytest tests/layers/execution/ -v -k "eksekusi_atomic_intent_semua"` — 5/5 PASSED. Regresi penuh `uv run pytest tests/layers/execution/ -q` — 86 passed, 1 skipped (skip pre-existing, tidak terkait perubahan ini), 25.64s.

**Commit:** `49528a7` (feat) + `9fba356` (test)

---
