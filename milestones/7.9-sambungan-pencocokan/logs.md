# Logs — Milestone 7.9: Sambungan 4 ((Decomposition + Tarik Memory) → Pencocokan)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi sebelum plan ditulis: `match_and_archive(atomic_intents, candidates, session_id, turn_index)` (M1.7) menerima `candidates: list[SessionMemoryPackage]`, BUKAN `Optional` — forced konversi `session_memory_result or []`. `archive_matched_packages()` memanggil `store_session_memory()` yang genuinely raise pada kegagalan DB — beda dari `rewrite`/`decomposition` yang full-fallback.
- Instruksi eksplisit user: real-execution eval WAJIB mencakup seluruh kombinasi kejadian, tidak dibatasi 2 — dianalisis jadi 6 kejadian (E01-E06) berdasar 2 dimensi (state Tarik Memory × bentuk Decomposition), tanpa duplikasi/celah.
- Tulis `decisions.md` — 7 keputusan (semua Jenis B, forced — satu-satunya area genuinely terbuka sudah dijawab langsung oleh instruksi eksplisit user).
- Commit hash: `ec42638`.

## Checkpoint 2 — Implementasi Sambungan

- Extend `src/schemas/orchestration.py::KeadaanTurn` — field `matches: list[AtomicIntentMatch]` (non-Optional).
- Extend `src/orchestration/turn_pipeline.py::proses_turn()` — setelah `decomposition_result` didapat, `matches = match_and_archive(decomposition_result.atomic_intents, session_memory_result or [], payload.session_id, payload.turn_index)`.
- Verifikasi import manual: `KeadaanTurn.model_fields.keys()` menunjukkan `matches` sudah masuk.
- Commit hash: `4ff94e7`.

## Checkpoint 3 — Test Deterministik

- Extend 3 test existing (short-circuit, wiring identity, kegagalan teknis) — tambah mock `match_and_archive`.
- 2 test baru: `test_orkestrator_match_menerima_list_kosong_saat_session_memory_none` (E01) dan `test_orkestrator_match_menerima_list_kosong_saat_session_memory_kosong` (E02) — spy membuktikan `candidates=[]` diterima `match_and_archive()` di KEDUA origin (`None` maupun `[]` eksplisit).

**Temuan teknis (ditemukan+diperbaiki sebelum commit):**
1. Identity check `hasil.matches is _MATCHES_DUMMY` gagal untuk list KOSONG (`[] is []` → `False`) — Pydantic v2 merekonstruksi container `list[...]` bahkan untuk list kosong, mirror temuan M7.7 Checkpoint 4 (tapi kali ini bahkan tanpa elemen di dalamnya). Diperbaiki: ganti `is` jadi `==` (value equality) di seluruh assertion `_MATCHES_DUMMY`.
2. Run pertama 2 test baru (E01/E02) memakan **47.66s** — jauh lebih lambat dari test lain di file yang sama (~5s total) — diagnosis: lupa mock `validate_turn_payload`/`detect_turn_dependency`/`rewrite_to_standalone`, sehingga test genuinely memanggil LLM nyata (terlihat dari `rewritten_question` yang diparafrase, bukan identik `payload.question`) — melanggar docstring cakupan file sendiri ("TIDAK butuh LLM nyata"). Diperbaiki: tambah mock lengkap ke kedua test baru.

**Hasil run nyata (setelah kedua perbaikan):**
```
$ .venv/Scripts/python.exe -m pytest tests/orchestration/test_turn_pipeline.py -v
test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil PASSED
test_orkestrator_wiring_keadaan_turn_berisi_objek_identik PASSED
test_orkestrator_referensi_terdeteksi_kedua_cabang_terpanggil_argumen_benar PASSED
test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai PASSED
test_orkestrator_decompose_menerima_rewritten_question_bukan_payload_question PASSED
test_orkestrator_match_menerima_list_kosong_saat_session_memory_none PASSED
test_orkestrator_match_menerima_list_kosong_saat_session_memory_kosong PASSED
7 passed in 4.90s
```

- Commit hash: `9032473`.

## Checkpoint 4 — Peta Kejadian

- Tulis `evals/7.9-sambungan-pencocokan/rancangan.md` — 6 kejadian (E01-E06), verdict berbasis STATUS match aktual (bukan required/forbidden phrases, bukan parent_span_id — KK M7.9 soal closed-space status). Span Pencocokan diidentifikasi lewat relasi PARENT (`chat` yang parent-nya persis `matching.evaluate`), bukan nama tracer.
- Commit hash: `bd0a6e7`.

## Checkpoint 5 — Eksekusi Nyata

- Docker (Jaeger+Collector+Prometheus) sudah hidup dari sesi sebelumnya — dikonfirmasi `docker ps` + `GET /api/services` → 200, tidak perlu restart.
- Tulis `evals/7.9-.../run_eval.py` — helper `_seed_turn_sebelumnya()` (mirror pola M1.7) dipakai E03-E06, helper `_hitung_span_matching()` mengidentifikasi span Pencocokan lewat relasi parent.
- Dijalankan di background (6 kejadian × pipeline penuh — Decomposition hingga 3 retry, Pencocokan hingga 1 LLM call per kandidat).

**Hasil run nyata:**
```
Menjalankan E01... status_per_intent=[perlu_eksekusi], span matching.evaluate=0, chat(matching)=0
Menjalankan E02... status_per_intent=[perlu_eksekusi, perlu_eksekusi, perlu_eksekusi], span matching.evaluate=0, chat(matching)=0
Menjalankan E03... status_per_intent=[selesai], span matching.evaluate=1, chat(matching)=1
Menjalankan E04... status_per_intent=[perlu_eksekusi], span matching.evaluate=1, chat(matching)=1
Menjalankan E05... status_per_intent=[perlu_eksekusi], span matching.evaluate=0, chat(matching)=0
Menjalankan E06... status_per_intent=[perlu_eksekusi, selesai, perlu_eksekusi], span matching.evaluate=1, chat(matching)=3
  arsip turn2 jumlah baris=1
```

- **6/6 kejadian lolos verdict pada percobaan PERTAMA** — tidak ada race Jaeger/bug seperti M7.7 (pola `span_wajib_ada` dari Temuan Pola M7.7 sudah diterapkan sejak awal, terbukti efektif mencegah race berulang).
- **Temuan (dikoreksi di Checkpoint 6, bukan diperbaiki di sini)**: E02 menghasilkan 3 atomic_intent (majemuk_bergantung), bukan 1 (tunggal) seperti diprediksi `rancangan.md` — payload E02 (diwariskan dari skenario M7.6/M7.7) ternyata berupa pertanyaan komparatif, pola yang sama seperti M7.8 E01/M7.9 E06. Verdict inti (fast-path, semua `perlu_eksekusi`, 0 span Pencocokan) TETAP sesuai prediksi. Detail koreksi di `audit.md`.
- Commit hash: `7f5ecc1`.

## Checkpoint 6 — Audit

- Tulis `evals/7.9-.../audit.md` — 6/6 kejadian lolos verdict, termasuk koreksi eksplisit E02 (jumlah atomic_intent), konfirmasi arsip ulang E06 lewat query DB langsung (`retrieve_session_memory()`, bukan asumsi kode).
- Commit hash: `eb7542e`.
