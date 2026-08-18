# Logs — Milestone 7.10: Sambungan 5 (Pencocokan (jalur "perlu eksekusi") → Domain Gate)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi sebelum plan ditulis: `identifikasi_domain_semua(matches: list[AtomicIntentMatch]) -> list[AtomicIntentDomains]` (M2.1, `src/layers/domain_gate/domain_gate.py`) SUDAH mengimplementasikan filter `status=PERLU_EKSEKUSI` sejak awal — docstring modul eksplisit menyatakan ini, sudah diuji nyata (real LLM) di `tests/layers/domain_gate/test_domain_gate.py`. TAPI `proses_turn()` sendiri belum pernah memanggilnya — M7.10 karena itu HYBRID: filter logic reuse penuh, wiring orkestrator genuinely baru (mirip pola M7.6-M7.9).
- Ditemukan: span `domain_gate.identifikasi_semua` sudah mencatat atribut `intent.count` langsung di kode M2.1 — verifikasi KK bisa lewat cek atribut span langsung, lebih sederhana dari teknik hitung child-span M7.9.
- Ditemukan: skenario KK literal ("campuran dua status") sudah pernah tereproduksi nyata di `evals/7.9-.../E06` — dipakai ulang sebagai basis E01 (dengan `session_id` baru).
- Tulis `decisions.md` — 7 keputusan (semua Jenis B, forced).
- Commit hash: `0ac277e`.

## Checkpoint 2 — Implementasi Sambungan

- Extend `src/schemas/orchestration.py::KeadaanTurn` — field `domain_gate: list[AtomicIntentDomains]` (non-Optional).
- Extend `src/orchestration/turn_pipeline.py::proses_turn()` — setelah `matches` didapat, `domain_gate_result = identifikasi_domain_semua(matches)` (tanpa filter tambahan oleh orkestrator).
- Verifikasi import manual: `KeadaanTurn.model_fields.keys()` menunjukkan `domain_gate` sudah masuk.
- Commit hash: `84c45c5`.

## Checkpoint 3 — Test Deterministik

- Extend 3 test existing (short-circuit, wiring identity, kegagalan teknis dilewati karena exception menjalar sebelum tercapai) + 2 test M7.9 (E01/E02) — tambah mock `identifikasi_domain_semua`.
- 1 test baru: `test_orkestrator_domain_gate_menerima_matches_apa_adanya_tanpa_filter` — spy membuktikan `identifikasi_domain_semua` menerima `matches` PERSIS (identity check) hasil `match_and_archive()`, bukan direkonstruksi/difilter ulang oleh orkestrator.

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/orchestration/test_turn_pipeline.py -v
test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil PASSED
test_orkestrator_wiring_keadaan_turn_berisi_objek_identik PASSED
test_orkestrator_referensi_terdeteksi_kedua_cabang_terpanggil_argumen_benar PASSED
test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai PASSED
test_orkestrator_decompose_menerima_rewritten_question_bukan_payload_question PASSED
test_orkestrator_match_menerima_list_kosong_saat_session_memory_none PASSED
test_orkestrator_match_menerima_list_kosong_saat_session_memory_kosong PASSED
test_orkestrator_domain_gate_menerima_matches_apa_adanya_tanpa_filter PASSED
8 passed in 11.25s
```

- Tidak ada temuan teknis baru di checkpoint ini (pola mock sudah dikenal dari M7.9, diterapkan bersih sejak awal).
- Commit hash: `7517709`.

## Checkpoint 4 — Peta Kejadian

- Tulis `evals/7.10-sambungan-domain-gate/rancangan.md` — 3 kejadian (E01 campuran reuse M7.9 E06, E02 semua perlu_eksekusi, E03 semua selesai reuse payload M7.9 E03), verdict primer berbasis atribut span `intent.count` langsung.
- Commit hash: `0e6f37c`.

## Checkpoint 5 — Eksekusi Nyata

- Docker (Jaeger+Collector+Prometheus) sudah hidup dari sesi sebelumnya — dikonfirmasi `docker ps` + `GET /api/services` → 200.
- Tulis `evals/7.10-.../run_eval.py` — helper `_cari_intent_count()` mengambil atribut `intent.count` langsung dari span `domain_gate.identifikasi_semua` via query Jaeger API.
- Dijalankan di background (3 kejadian × pipeline penuh).

**Hasil run nyata:**
```
Menjalankan E01... jumlah_matches=3, jumlah_domain_gate=2, intent.count=2
Menjalankan E02... jumlah_matches=3, jumlah_domain_gate=3, intent.count=3
Menjalankan E03... jumlah_matches=3, jumlah_domain_gate=2, intent.count=2
```

- **E01 PERSIS sesuai prediksi** (3 matches, 2 domain_gate, intent.count=2) — bukti KK literal utama.
- **Temuan (dikoreksi di Checkpoint 6, bukan diperbaiki di sini)**: E02 dan E03 TIDAK mereproduksi jumlah atomic_intent yang diprediksi `rancangan.md` (diprediksi tunggal/1 intent untuk keduanya, aktual majemuk_bergantung/3 intent) — non-determinisme Decomposition nyata, bahkan untuk E03 yang payload-nya IDENTIK PERSIS dengan `evals/7.9-.../E03` (yang sebelumnya menghasilkan tunggal). Verdict MEKANISME (filter benar, `intent.count` = panjang `domain_gate`) tetap terbukti di ketiga kejadian. Tidak dilakukan retry berulang untuk memaksa hasil "sesuai prediksi" — itu sendiri bentuk bias metodologi. Detail lengkap di `audit.md`.
- Commit hash: `c12465a`.

## Checkpoint 6 — Audit

- Tulis `evals/7.10-.../audit.md` — 3/3 kejadian membuktikan mekanisme filter benar, dengan koreksi transparan E02/E03 (jumlah meleset dari rencana, tapi mekanisme dan bahkan bukti KK literal kedua tetap tervalidasi). Klaim "span tetap terbuka saat `intent.count=0`" divalidasi lewat inspeksi kode (bukan eksekusi nyata) karena tidak ada kejadian yang mereproduksi `domain_gate=[]` — dijelaskan eksplisit alasannya, bukan diklaim sebagai bukti eksekusi yang sebenarnya tidak ada.
- Commit hash: `78bc9de`.
