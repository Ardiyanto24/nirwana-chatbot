# Logs — Milestone 7.7: Sambungan 2 (Pemetaan Ketergantungan → Percabangan Paralel: Rewrite + Tarik Memory)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi sebelum plan ditulis: dikonfirmasi tidak ada preseden konkurensi sama sekali di project (`asyncio|threading|concurrent.futures|async def` hanya boilerplate FastAPI). `rewrite_to_standalone()` (M1.4) dikonfirmasi sengaja dirancang independen dari `TurnDependencyResult` sejak awal (`decisions.md` M1.4 Keputusan 4). Celah `retrieve_session_memory()` (M1.5, tanpa `try/except`) ditemukan mirror pola celah M1.3.
- Mekanisme paralel (`ThreadPoolExecutor` vs `asyncio`) diajukan ke user lewat `AskUserQuestion` — user meminta penjelasan detail trade-off sebelum menjawab, dijelaskan cara kerja/kelebihan/kekurangan kedua opsi, dijawab Opsi A (`ThreadPoolExecutor`).
- Teknik propagasi context OTel ke thread worker diverifikasi NYATA terhadap Jaeger live (oleh Plan agent) sebelum dikunci sebagai pendekatan — dikonfirmasi bekerja (span anak berbagi `parentSpanID` sama dengan span induk).
- Tulis `decisions.md` — 7 keputusan (1 Jenis A, 6 Jenis B).
- Commit hash: `8ede8a2`.

## Checkpoint 2 — Perbaikan `retrieve_session_memory()` (M1.5)

- `src/layers/context_resolution/session_memory.py::retrieve_session_memory()` dibungkus `try/except Exception: span.set_attribute("error.type", "gagal_teknis"); raise`, mirror persis `store_session_memory()`.
- Extend `tests/layers/context_resolution/test_session_memory_kegagalan.py` — `_SessionExecGagal` baru + test `test_kegagalan_db_saat_retrieve_menghasilkan_error_type_lalu_raise_ulang`.

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/layers/context_resolution/test_session_memory_kegagalan.py -v
test_kegagalan_db_menghasilkan_error_type_lalu_raise_ulang PASSED
test_kegagalan_db_atribut_session_turn_atomic_intent_tetap_tercatat PASSED
test_kegagalan_db_saat_retrieve_menghasilkan_error_type_lalu_raise_ulang PASSED
3 passed in 3.64s
```

- **Temuan sampingan saat regresi**: full suite `tests/layers/context_resolution/` (14 test) menghasilkan 1 kegagalan di `test_matching.py::test_kelompok_c_rantai_arsip_ulang_turn_tujuh_lima_tiga` (M1.7), TIDAK TERKAIT perubahan ini. Diverifikasi 2x terpisah (gagal dengan alasan BERBEDA tiap run: `MatchStatus` salah lalu `assert 2 == 1`/baris duplikat) — dikonfirmasi murni masalah isolasi test M1.7 pra-eksisting (`session_id` hardcoded `"test-m17-kelompok-c"`, data menumpuk di Supabase nyata antar-run, bukan di-randomize per-run seperti fixture test lain). Dicatat sebagai observasi, tidak diperbaiki (di luar Lingkup M7.7/M1.5, kepemilikan test itu ada di M1.7).
- Addendum ditulis di `milestones/1.5-tarik-session-memory/{decisions.md,logs.md,report.md}` (Keputusan 14).
- Commit hash: `2ef5012` (fix), `5be7f0d` (test), `77c9b30` (docs M1.5).

## Checkpoint 3 — Implementasi Orkestrator Paralel

- Extend `src/schemas/orchestration.py::KeadaanTurn` — field `rewrite: RewriteResult`, `session_memory: list[SessionMemoryPackage] | None`.
- Extend `src/orchestration/turn_pipeline.py::proses_turn()` — `ThreadPoolExecutor(max_workers=2)`, helper `_jalankan_rewrite`/`_jalankan_tarik_memory` dengan `otel_context.attach()`/`detach()`.
- Verifikasi import manual berhasil tanpa error.
- Commit hash: `b527f8d`.

## Checkpoint 4 — Test Deterministik

- Extend `tests/orchestration/test_turn_pipeline.py` — 2 test baru (referensi terdeteksi kedua cabang terpanggil argumen benar, kegagalan teknis satu cabang) + perbaikan test wiring M7.6 yang sekarang juga perlu mock `rewrite_to_standalone` (dipanggil selalu, sebelumnya cuma butuh mock `validate_turn_payload`/`detect_turn_dependency`).
- **Temuan teknis**: identity check `is` gagal untuk `hasil.session_memory is paket_asli` (whole-list identity) — Pydantic v2 merekonstruksi container `list[BaseModel]` sebagai objek baru meski elemen di dalamnya tetap instance persis (fast-path revalidasi Pydantic v2 untuk BaseModel yang sudah tervalidasi hanya berlaku per-elemen, bukan container). Diperbaiki: assert `len(...)` + identity elemen (`hasil.session_memory[0] is paket_asli[0]`), bukan identity container penuh.

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/orchestration/test_turn_pipeline.py -v
test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil PASSED
test_orkestrator_wiring_keadaan_turn_berisi_objek_identik PASSED
test_orkestrator_referensi_terdeteksi_kedua_cabang_terpanggil_argumen_benar PASSED
test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai PASSED
4 passed in 3.17s
```

- Commit hash: `c078e1d`.

## Checkpoint 5 — Peta Kejadian

- Tulis `evals/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/rancangan.md` — 2 kejadian real-execution (E01/E02) + 2 kejadian dirujuk ke `tests/orchestration/` (E03/E04).
- Commit hash: `6e7a3cf`.

## Checkpoint 6 — Eksekusi Nyata (Jaeger Live)

- `docker ps` dicek — 3 container (Jaeger+Collector+Prometheus, warisan sesi M7.6) masih hidup, tidak perlu `docker compose up` ulang.
- Tulis `evals/7.7-.../run_eval.py` (mirror `evals/7.6-.../run_eval.py`, dengan pemeriksaan span parent lebih ketat untuk E01).

**Percobaan pertama gagal karena race Jaeger** — `_query_jaeger_trace()` (mirror preseden M7.6, berhenti retry begitu ada data pertama tidak kosong) mendapat trace dengan 3 dari 4 span (span `invoke_agent` sendiri belum terindeks), sehingga `chat_parent_cocok_invoke_agent`/`memory_retrieve_parent_cocok_invoke_agent` keduanya `False` — bukan karena propagasi context gagal (span `chat`+`memory.retrieve` sebenarnya SUDAH sama-sama menunjuk `parentSpanID` yang identik satu sama lain di percobaan pertama, cuma `invoke_agent`-nya sendiri belum muncul di hasil query). Diperbaiki: `_query_jaeger_trace()` diberi parameter `span_wajib_ada`, retry menunggu SET LENGKAP span sebelum diterima, bukan cuma "ada data apa saja".

**Hasil run nyata (setelah perbaikan):**
```
$ .venv/Scripts/python.exe evals/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/run_eval.py
Menjalankan E01 (referensi terdeteksi, kedua jalur paralel)...
  trace_id=1209dcff1ddf138a4a1118239a53dec6
  is_dependent=True, referenced_turn_index=1
  chat parent cocok invoke_agent: True
  memory.retrieve parent cocok invoke_agent: True
  KEDUA SPAN ANAK DARI SPAN YANG SAMA: True
Menjalankan E02 (tanpa referensi, hanya Rewrite)...
  trace_id=be61c3ce528b50dc28a84561952e85da
  session_memory=None
  span chat ditemukan=True, span memory.retrieve ditemukan=False
```

- E01 (`payloads/E01.json`): 5 span dalam trace (`invoke_agent` root, `input.validate`, 2× `chat` [Pemetaan Ketergantungan M7.6 + Rewrite M7.7], `memory.retrieve`) — SEMUA 4 span anak sama-sama `parentSpanID=5f88085f1577dcaf` (invoke_agent).
- E02 (`payloads/E02.json`): 4 span (`invoke_agent`, `input.validate`, 2× `chat`) — TIDAK ADA span `memory.retrieve` sama sekali.
- Commit hash: `cff1734`.

## Checkpoint 7 — Audit

- Tulis `evals/7.7-.../audit.md` — 4/4 kejadian sesuai ekspektasi, E01/E02 dikutip lengkap sebagai bukti KK literal M7.7 (tabel span parent-child E01, konfirmasi ketiadaan span E02).
- Commit hash: `f14e303`.
