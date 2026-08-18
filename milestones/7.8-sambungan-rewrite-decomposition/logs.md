# Logs — Milestone 7.8: Sambungan 3 (Rewrite → Decomposition)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi sebelum plan ditulis: dikonfirmasi `decompose_question(question: str) -> DecompositionResult` menerima `str` polos (bukan `TurnPayload`/`RewriteResult`); ketiga sub-langkahnya (`klasifikasi_kebutuhan`, `pecah_atomik`, `verifikasi_pemecahan`) dibaca langsung — semua py `try/except APIError` dengan fallback penuh, tidak pernah raise.
- Metodologi pembuktian KK diajukan ke user lewat `AskUserQuestion` (KK M7.8 murni soal konten, beda dari M7.6/M7.7 yang soal span) — user memilih tetap membangun folder `evals/` penuh demi konsistensi struktur Level 2.
- Tulis `decisions.md` — 7 keputusan (1 Jenis A, 6 Jenis B).
- Commit hash: `0d93711`.

## Checkpoint 2 — Implementasi Sambungan

- Extend `src/schemas/orchestration.py::KeadaanTurn` — field `decomposition: DecompositionResult` (non-Optional).
- Extend `src/orchestration/turn_pipeline.py::proses_turn()` — setelah blok `ThreadPoolExecutor` selesai, `decomposition_result = decompose_question(rewrite_result.rewritten_question)` dipanggil sekuensial (thread utama, tanpa propagasi context manual).
- Verifikasi import manual: `KeadaanTurn.model_fields.keys()` menunjukkan `decomposition` sudah masuk.
- Commit hash: `da0f2cf`.

## Checkpoint 3 — Test Deterministik

- Extend `tests/orchestration/test_turn_pipeline.py` — 3 test existing (short-circuit, wiring identity, kegagalan teknis) ditambah mock `decompose_question` supaya tidak memicu panggilan LLM nyata (test kegagalan teknis TIDAK perlu mock karena exception dari Tarik Memory menjalar sebelum baris `decompose_question()` tercapai). 1 test baru: `test_orkestrator_decompose_menerima_rewritten_question_bukan_payload_question` — spy membuktikan `decompose_question` menerima `rewrite_result.rewritten_question`, bukan `payload.question` (payload+rewrite dummy sengaja beda teks total).

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/orchestration/test_turn_pipeline.py -v
test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil PASSED
test_orkestrator_wiring_keadaan_turn_berisi_objek_identik PASSED
test_orkestrator_referensi_terdeteksi_kedua_cabang_terpanggil_argumen_benar PASSED
test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai PASSED
test_orkestrator_decompose_menerima_rewritten_question_bukan_payload_question PASSED
5 passed in 4.30s
```

- Commit hash: `c769e46`.

## Checkpoint 4 — Peta Kejadian

- Tulis `evals/7.8-sambungan-rewrite-decomposition/rancangan.md` — 2 kejadian real-execution (E01 elipsis/koreferensi reuse M1.4 Kelompok A, E02 sudah mandiri reuse M1.4 Kelompok B), verdict berbasis `required_phrases`/`forbidden_phrases` (bukan span, mengikuti sifat KK M7.8).
- Commit hash: `ef15763`.

## Checkpoint 5 — Eksekusi Nyata

- Docker Desktop tidak berjalan di awal sesi ini (`docker ps` gagal terhubung ke daemon) — di-start ulang (`Start-Process Docker Desktop.exe`), ditunggu siap (~10s), lalu `docker compose up -d` di `infra/observability/` (Jaeger+Collector+Prometheus, container sudah ada dari sesi sebelumnya, cuma perlu di-start ulang). Jaeger API dikonfirmasi responsif (`GET /api/services` → 200) sebelum eksekusi.
- Tulis `evals/7.8-.../run_eval.py` (mirror `run_eval.py` M7.6/M7.7: `_TraceIdCapture`, `_query_jaeger_trace` dengan `span_wajib_ada`) — verdict utama berbasis `_cek_phrases()` (required/forbidden pada gabungan `teks_kebutuhan`), span jadi konfirmasi sekunder.
- Dijalankan di background (Decomposition py hingga 3× retry per sub-langkah, lebih lambat dari M7.6/M7.7 yang cuma 1-2 pemanggilan) — selesai exit code 0.

**Hasil run nyata:**
```
Menjalankan E01 (elipsis/koreferensi)...
  trace_id=06c731a65a8103a9dfdbed8fa41373ff
  rewritten_question='Bagaimana tingkat occupancy April 2026 dibandingkan dengan tingkat occupancy April 2025?'
  teks_kebutuhan_gabungan='berapa tingkat occupancy april 2025? | berapa tingkat occupancy april 2026? | bagaimana perbandingan tingkat occupancy april 2026 dengan april 2025?'
  LOLOS KONTEN: False
  jumlah span chat: 5, semua anak invoke_agent: True
Menjalankan E02 (sudah mandiri, baseline)...
  trace_id=d9bf0ba3b5d28c2bff024d7d325b4290
  rewritten_question='Berapa revenue reservasi bulan Maret 2026?'
  teks_kebutuhan_gabungan='berapa revenue reservasi bulan maret 2026?'
  LOLOS KONTEN: True
```

- **Temuan sampingan (dikoreksi di Checkpoint 6, bukan diperbaiki di sini)**: E01 mekanis `LOLOS KONTEN: False` — bukan kegagalan wiring, melainkan `forbidden_phrases=["2026"]` di `rancangan.md` adalah asumsi keliru (kalimat mandiri hasil PERBANDINGAN secara linguistik wajib menyebut kedua sisi yang dibandingkan, termasuk 2026). `decomposition.klasifikasi=majemuk_bergantung`, 3 atomic_intents dengan relasi ketergantungan benar — Decomposition genuinely bekerja benar mengikuti kalimat mandiri, bukan kalimat asli ("satu tahun sebelumnya" genuinely tidak pernah muncul). Detail koreksi ada di `audit.md` "Temuan Metodologi" — `rancangan.md` TIDAK diedit retroaktif, koreksi penilaian didokumentasikan eksplisit di `audit.md`.
- Commit hash: `5317bad`.

## Checkpoint 6 — Audit

- Tulis `evals/7.8-.../audit.md` — 2/2 kejadian membuktikan KK terpenuhi setelah koreksi penilaian E01 (verdict substantif vs teks KK, bukan proxy mekanis yang salah rancang), termasuk section "Temuan Metodologi" untuk pelajaran milestone Sambungan berikutnya (forbidden_phrases harus dari frasa rujukan mentah, bukan entitas/nilai yang bisa legitimately relevan tergantung struktur kalimat).
- Commit hash: `f38e0e6`.
