# Logs — Milestone 7.18: Membangun Database Percakapan

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (3 agen Explore paralel) menemukan: tidak ada hook/tempat disiapkan untuk penulisan riwayat; "status keseluruhan turn" tidak didefinisikan di mana pun (genuinely perlu dirancang); pola "tangkap-dan-diam" belum pernah ada di project (SELURUH penanganan kegagalan existing konsisten "tangkap-tandai-raise ulang"); `PromptEvalRunRow` preseden model tabel terdekat. Dua keputusan diajukan ke user via `AskUserQuestion`: lokasi kode penulisan (user pilih rekomendasi: `main.py`) dan sumber "status keseluruhan turn" (user minta penjelasan konkret dulu — diberi contoh turn campuran berhasil/gagal yang tetap `terverifikasi=True` — user memutuskan agregasi `paket_narasi`, BUKAN reuse `terverifikasi`). Menulis `milestones/7.18-database-percakapan/decisions.md` (7 keputusan, 2 Jenis A + 5 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template.

**Commit:** `68ea8c5` — `docs(milestone-7.18): keputusan`

---

## Checkpoint 2 — Skema Tabel + Materialisasi

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 2-3 — `ConversationTurnRow` + `create_all()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `src/db/models.py` lengkap (konfirmasi bentuk `PromptEvalRunRow` untuk ditiru). Tambah `ConversationTurnRow` (`__tablename__ = "conversation_turns"`, UUID PK + `created_at` default). Jalankan `SQLModel.metadata.create_all(get_engine())` sekali terhadap Supabase nyata.

**Temuan**
Tidak ada temuan tak terduga.

**Hasil Verifikasi**
Query `SELECT` langsung ke `conversation_turns` (bukan asumsi `create_all()` sukses, preseden kehati-hatian M2.2) — tabel terkonfirmasi ada, 0 baris. `ConversationTurnRow(...)`+`.model_dump()` valid.

**Commit:** `5935f25` — `feat(milestone-7.18): skema tabel conversation_turns`

---

## Checkpoint 3 — Fungsi Agregasi Status + Penyimpanan

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 4-7 — `tentukan_status_keseluruhan_turn()` + `simpan_riwayat_turn()` + test

**Kesesuaian dengan plan:** Sesuai plan, dengan 1 penyesuaian kecil (lihat Temuan).

**Apa yang dilakukan**
Baca `session_memory.py` lengkap untuk mirror pola persis (span, tangkap+tandai+raise). Tulis `src/orchestration/riwayat_percakapan.py` — `tentukan_status_keseluruhan_turn()` (murni, set status unik → seragam/`"campuran"`/`"tidak_ada_kebutuhan"`) dan `simpan_riwayat_turn()` (span `riwayat.simpan`, mirror `store_session_memory()`). Tulis `tests/orchestration/test_riwayat_percakapan.py` (real DB, mirror `test_session_memory.py`) dan `tests/orchestration/test_riwayat_percakapan_kegagalan.py` (mocked, mirror `test_session_memory_kegagalan.py`).

**Temuan**
Penyesuaian dari plan tertulis: test MURNI `tentukan_status_keseluruhan_turn()` (Task 6 menyebutnya di file real-DB) DIPINDAH ke `test_riwayat_percakapan_kegagalan.py` (file tanpa `skipif`) — supaya test yang genuinely tidak butuh DB TIDAK ikut ter-skip kalau `DATABASE_URL` tidak tersedia di lingkungan lain. Verifikasi checkpoint (`pytest tests/orchestration/test_riwayat_percakapan*.py`) tetap tercakup via glob, tidak melanggar maksud plan.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_riwayat_percakapan.py tests/orchestration/test_riwayat_percakapan_kegagalan.py -v` — 9/9 PASSED (real DB tidak ter-skip, `DATABASE_URL` tersedia).

**Commit:** `a2899a0` (feat) + `868ecf7` (test)

---

## Checkpoint 4 — Sambungkan ke `main.py`

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 8 — Wiring + try/except tangkap-dan-diam

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah `_simpan_riwayat_percakapan_aman(keadaan, turn_response)` di `src/main.py` — hitung `status` via `tentukan_status_keseluruhan_turn(keadaan.paket_narasi)`, panggil `simpan_riwayat_turn()` dalam `try/except Exception: pass` (komentar eksplisit menjelaskan pola BARU ini beda dari SELURUH handler lain di file). `submit_turn()` memanggil ini setelah `_build_turn_response()`, sebelum `return`.

**Temuan**
Tidak ada temuan tak terduga.

**Hasil Verifikasi**
`uv run python -c "from src.main import app, _simpan_riwayat_percakapan_aman; ..."` — import berhasil, tidak ada error sintaks/dependensi sirkular.

**Commit:** `500afc1` — `feat(milestone-7.18): sambungkan riwayat percakapan ke main.py`

---

## Checkpoint 5 — Test Deterministik KK2 (Level HTTP)

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 9 — Test HTTP + perbaikan kebocoran test lama

**Kesesuaian dengan plan:** Sesuai plan, DIPERLUAS (lihat Temuan — bug test-hygiene ditemukan+diperbaiki).

**Apa yang dilakukan**
Tambah `test_endpoint_tetap_200_walau_simpan_riwayat_gagal` (KK2 literal — mock `simpan_riwayat_turn` untuk raise, assert response TETAP 200) dan `test_simpan_riwayat_dipanggil_dengan_argumen_benar` (assert argumen `session_id`/`turn_index`/`pertanyaan`/`narasi`/`status` benar) di `tests/test_main.py`.

**Temuan**
Test EXISTING (`test_endpoint_sukses_mengembalikan_turn_response` di `tests/test_main.py`, DAN 3 test penerimaan `tests/layers/test_input_layer.py`) TERNYATA diam-diam mulai menulis baris NYATA ke `conversation_turns` sejak Checkpoint 4 — file-file itu men-mock `proses_turn()` tapi TIDAK `simpan_riwayat_turn()` (fungsi baru), sehingga `submit_turn()` genuinely memanggil DB nyata setiap kali test itu jalan. Dikonfirmasi lewat query langsung: 3 baris `session_id="sess-test"` (`turn_index` 1/2/3) ditemukan di Supabase, tercatat SEBELUM perbaikan ini disadari.

**Error/Kegagalan**
Kebocoran test-hygiene (bukan kegagalan test — seluruh test tetap PASSED, karena `simpan_riwayat_turn()` yang genuinely sukses ke DB nyata TIDAK menyebabkan assertion gagal).

**Diagnosis dan Perbaikan**
Tambah `monkeypatch.setattr(main_module, "simpan_riwayat_turn", lambda **kwargs: None)` ke `test_endpoint_sukses_mengembalikan_turn_response` dan ketiga test penerimaan `test_input_layer.py`. Baris yang sudah terlanjur tersimpan DIHAPUS manual (`DELETE FROM conversation_turns WHERE session_id = 'sess-test'`) SEBELUM commit — dikonfirmasi 0 baris tersisa setelah run ulang.

**Hasil Verifikasi**
`uv run pytest tests/layers/test_input_layer.py tests/test_main.py -v` — 23/23 PASSED. Query `conversation_turns` setelah run — 0 baris (tidak ada kebocoran baru).

**Commit:** `a86ec77` — `test(milestone-7.18): test deterministik KK2 level HTTP`

---

## Checkpoint 6 — Peta Kejadian Eval

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 10 — `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `evals/7.18-database-percakapan/rancangan.md` — 1 kejadian (E01, reuse payload M7.17 E01 General Manager/occupancy), 5 invarian wajib (HTTP 200, tepat 1 baris baru, `pertanyaan`/`narasi` cocok persis, `status` konsisten).

**Commit:** `d4e18e0` — `docs(milestone-7.18): peta kejadian eval`

---

## Checkpoint 7 — Eksekusi Nyata

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 11 — `run_eval.py` + eksekusi

**Kesesuaian dengan plan:** Sesuai plan, dengan diversi signifikan (lihat Temuan — bug produksi genuinely baru ditemukan+diperbaiki, bukan sekadar retry infra seperti M7.14-7.17).

**Apa yang dilakukan**
Tulis `evals/7.18-database-percakapan/run_eval.py` (adaptasi `evals/7.17-.../run_eval.py`, server `uvicorn` port 8001 sendiri via `sys.executable -m uvicorn`, query langsung `conversation_turns` via SQLModel setelah HTTP selesai).

**Temuan**
Percobaan pertama (`session_id="eval-7.18-e01"`) crash tak terduga — chatbot_api DAN app server sama-sama mati bersamaan, tanpa traceback tertangkap (stderr `DEVNULL`). Percobaan kedua (`session_id="eval-7.18-e01b"`, chatbot_api direstart) BERHASIL selesai (exit 0) TAPI hasilnya HTTP **500**, bukan 200 seperti diharapkan `rancangan.md` — `conversation_turns_rows: []` (tidak ada baris tersimpan, sesuai desain: `submit_turn()` gagal sebelum sempat memanggil `_simpan_riwayat_percakapan_aman()`).

**Error/Kegagalan**
HTTP 500 `{"detail": "Terjadi kesalahan internal, silakan coba lagi atau hubungi tim terkait."}` — pesan generik catch-all `main.py`, tidak mengungkap akar masalah dari body response.

**Diagnosis dan Perbaikan**
Server debug manual dijalankan terpisah (port 8002, stderr TIDAK dibuang) untuk menangkap traceback asli — direproduksi 2× identik: `TypeError: 'NoneType' object is not subscriptable` di `src/layers/decomposition/klasifikasi.py:69` (`response.choices[0]`), `response.choices` bernilai `None`. Ini PERSIS titik pertama dari 5 yang sudah terdaftar `docs/keterbatasan-diterima.md` #17 (ditemukan riset M7.17, sengaja diterima tanpa perbaikan sampai terbukti nyata) — pemicu peninjauan ulang entri itu sendiri kini terpenuhi. Diperbaiki DI M1.6 (milestone pemilik layer, BUKAN di M7.18) — guard `if not response.choices:` ditambahkan, reuse fallback aman yang sudah ada, mirror pola perbaikan M7.6/M7.7 (fix di file pemilik, dokumentasi di `decisions.md`/`logs.md` M1.6, BUKAN M7.18). Detail lengkap: `milestones/1.6-decomposition/decisions.md` Keputusan 15 (Addendum), `milestones/1.6-decomposition/logs.md` Addendum 2026-08-20. Cakupan perbaikan SENGAJA dibatasi hanya `klasifikasi.py` — 4 titik lain di entri #17 TIDAK disentuh (belum terbukti crash nyata masing-masing).

Insiden operasional tambahan (tidak terkait bug di atas): chatbot_api sempat mati 2× tanpa traceback selama proses diagnosis (proses `nohup ... &` manual tidak survive antar-tool-call di lingkungan kerja ini) — diselesaikan dengan menjalankan chatbot_api via mekanisme `run_in_background` bawaan tool (lebih stabil), bukan `nohup` manual.

**Hasil Verifikasi**
Setelah fix M1.6 + chatbot_api stabil, `run_eval.py` dijalankan ulang (`session_id="eval-7.18-e01f"`) — **BERHASIL PENUH**:
```
http status=200
baris ditemukan: 1
```
Kelima invarian `rancangan.md` diverifikasi dari `payloads/E01.json`:
1. HTTP 200 ✓
2. Tepat 1 baris baru `conversation_turns`, `turn_index=1` ✓
3. `pertanyaan` tersimpan PERSIS sama dengan payload `question` ✓
4. `narasi` tersimpan PERSIS sama dengan body response HTTP (`"Saat ini, sistem mengalami kendala teknis..."`) ✓
5. `status="gagal_teknis"` — konsisten dengan narasi yang jujur melaporkan kendala teknis (`terverifikasi=true`, bukan fabrikasi) — seragam karena 1 atomic intent, bukan `"campuran"` ✓

**KK1 M7.18 terbukti TERPENUHI PENUH secara nyata** (bukan simulasi/mock).

**Commit:** `49853e7` — `test(milestone-7.18): eksekusi nyata` (kode+payload), `762fbd4` — `docs(milestone-7.18): logs Checkpoint 1-7`

---

## Checkpoint 8 — Audit

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 12 — `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tulis `evals/7.18-database-percakapan/audit.md` — ringkasan KK1 terpenuhi penuh, tabel invarian vs hasil aktual, kronologi 4 percobaan (3 penyebab kegagalan berbeda-beda sebelum sukses), temuan metodologi (eksekusi nyata sekali lagi menemukan bug produksi tak terlihat dari test mocked, konsisten preseden M7.6/M7.7/M7.11/M7.17).

**Commit:** *(lihat commit gabungan di bawah)*

---
