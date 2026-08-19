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

## Checkpoint 4 — Sambungan Wave Loop ke `proses_turn()`

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

**Catatan operasional:** komputer sempat restart di tengah checkpoint ini (setelah Task 7-8 ditulis, sebelum diverifikasi) — background process `chatbot_api` (Checkpoint 1) ikut mati. Working tree (perubahan belum di-commit) tetap utuh setelah restart, dikonfirmasi `git status` menunjukkan persis 2 file termodifikasi yang diharapkan (`turn_pipeline.py`, `orchestration.py`), tidak ada kerja hilang.

### Task 7-8 — Extend `KeadaanTurn` + restrukturisasi wave loop

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah field `execution: list[HasilEksekusiAtomicIntent]` di `KeadaanTurn` (field TERAKHIR, 13 field total) — import `HasilEksekusiAtomicIntent` dari `src.schemas.execution`. Di `turn_pipeline.py`: import `eksekusi_atomic_intent_semua` + `kelompokkan_wave`, restrukturisasi bagian setelah `query_engine_result` — SEBELUMNYA satu panggilan flat `verifikasi_gate_semua(query_engine_result, ...)`, SEKARANG: `kelompokkan_wave(query_engine_result)` menghasilkan `waves`, loop `for wave_index, wave in enumerate(waves, start=1)` — tiap iterasi buka span `orchestration.wave` (`wave.index`, `wave.intent_count`), panggil `verifikasi_gate_semua(wave, retriever_result, cakupan_individu_result, payload.employee_id)` (retriever/cakupan_individu TETAP full-set, bukan di-slice), `extend()` hasilnya ke akumulator `verification_gate_result`, lalu `eksekusi_atomic_intent_semua(hasil_vg_wave, cakupan_individu_result, payload.role_title, payload.employee_id)`, `extend()` ke `execution_result`. Kedua akumulator diisi ke `KeadaanTurn(...)` di akhir.

**Temuan**
Tidak ada temuan tak terduga — restrukturisasi murni mekanis begitu `kelompokkan_wave()` (Checkpoint 2) dan `eksekusi_atomic_intent_semua()` (Checkpoint 3) sudah tersedia dan teruji standalone.

**Error/Kegagalan (jika ada)**
Tidak ada error kode. Satu insiden operasional (restart komputer, lihat Catatan di atas) — tidak menyebabkan kehilangan kerja.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`KeadaanTurn.model_fields` mengandung `execution`, urutan 13 field sesuai rencana (dikonfirmasi `uv run python -c "..."`). Sanity-check `proses_turn()` dengan `kelompokkan_wave`/`verifikasi_gate_semua`/`eksekusi_atomic_intent_semua` di-mock: (a) kasus wave kosong — kedua fungsi tidak terpanggil, field `execution`/`verification_gate` kosong; (b) kasus 2 wave — `verifikasi_gate_semua` menerima `wave1` LALU `wave2` (urutan terbukti benar, dicek lewat rekaman argumen panggilan), `eksekusi_atomic_intent_semua` terpanggil sekali per wave tepat setelah `verifikasi_gate_semua` wave itu.

**Commit:** `940ed42` (feat) + `c9c3881` (docs)

---

## Checkpoint 5 — Test Deterministik Sambungan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 9-10 — Extend test existing + test connectivity baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca ulang `tests/orchestration/test_turn_pipeline.py` (14 test, seluruhnya mock LLM/DB) untuk memahami pola existing. Temuan penting SEBELUM edit: 12 dari 13 test menggunakan `_QUERY_ENGINE_DUMMY = []` (list kosong) sebagai hasil Query Engine — karena `kelompokkan_wave([])` mengembalikan `[]` (tanpa wave), loop wave TIDAK PERNAH jalan untuk test-test ini, jadi `verifikasi_gate_semua`/`eksekusi_atomic_intent_semua` otomatis tidak pernah terpanggil TANPA perlu mock tambahan — 11 dari 13 test existing lolos TANPA perubahan.

Dua perubahan genuinely dibutuhkan:
1. **Test short-circuit** (`test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil`): tambah 2 guard baru (`kelompokkan_wave`, `eksekusi_atomic_intent_semua` — assert TIDAK terpanggil saat validasi gagal), mirror pola guard existing.
2. **Test koneksi M7.13** (`test_orkestrator_verification_gate_menerima_query_engine_retriever_cakupan_individu_employee_id_persis`): **BUTUH PERBAIKAN SUBSTANTIF** — versi asli memakai `query_engine_asli = []`, yang SEKARANG (pasca M7.14) menyebabkan `verifikasi_gate_semua` TIDAK PERNAH terpanggil sama sekali (kelompokkan_wave([]) -> 0 wave) — test akan GAGAL kalau tidak diperbaiki. Diubah jadi `query_engine_asli` berisi 1 item nyata (`HasilPenyusunanRequest`+`HasilVerifikasiBentukRequest`, `relasi=independen`). Konsekuensi arsitektural yang didokumentasikan eksplisit di docstring test: `verifikasi_gate_semua` sekarang menerima WAVE-SLICE (list baru hasil `kelompokkan_wave()`), BUKAN `query_engine_asli` itu sendiri secara identity container — assertion diubah dari `is` (identity list) jadi `==` (value equality) + `[0] is` (identity elemen di dalamnya). Test ini SEKALIGUS diperluas mencakup `eksekusi_atomic_intent_semua` (belum pernah diuji sebelumnya, genuinely baru M7.14).

Test connectivity BARU (Task 10): `test_orkestrator_wave_kedua_menunggu_wave_pertama_selesai` — skenario 2 atomic intent (ai-a independen, ai-b bergantung pada ai-a, mirror KK sumber "bandingkan X dengan Y yang butuh Y dulu"), `verifikasi_gate_semua`/`eksekusi_atomic_intent_semua` di-mock merekam urutan panggilan ke list bersama (bukan Jaeger — murni mock/deterministik). Assert urutan PERSIS: `verifikasi_gate:ai-a` -> `eksekusi:ai-a` -> `verifikasi_gate:ai-b` -> `eksekusi:ai-b` — membuktikan wave 2 genuinely menunggu wave 1 SELESAI KEDUANYA (bukan cuma verifikasi-nya) sebelum diproses.

**Temuan**
Analisis awal (sebelum edit) yang mengidentifikasi 11/13 test TIDAK butuh perubahan terbukti akurat setelah dijalankan — hemat waktu signifikan dibanding mengedit seluruh 13 test secara membabi buta.

**Error/Kegagalan (jika ada)**
Tidak ada — seluruh 14 test (13 existing + 1 baru) lolos percobaan PERTAMA setelah edit.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_turn_pipeline.py -v` — 14/14 PASSED, 4.18s, tanpa panggilan LLM/DB/HTTP nyata. Regresi lebih luas `uv run pytest tests/orchestration/ tests/layers/execution/ tests/layers/verification_gate/ tests/layers/query_engine/ -q` — 209 passed, 1 skipped, 31.75s.

**Commit:** *(dicatat di commit berikutnya)*

---
