# Logs — Milestone 7.6: Sambungan 1 (Input Layer → Pemetaan Ketergantungan Turn)

## Checkpoint 1 — Persiapan & Keputusan

- Investigasi sebelum plan ditulis: dikonfirmasi TIDAK ADA kode lintas-layer di `src/` untuk cakupan ini; ditemukan `detect_turn_dependency()` (M1.3) tanpa `try/except APIError` sama sekali (beda dari semua layer LLM lain kecuali `narasi.py` M4.4 yang sengaja).
- Draf plan pertama (fixture pytest `InMemorySpanExporter` untuk bukti span) DITOLAK user secara eksplisit — diarahkan meniru workflow `evals/` dengan unit "kejadian struktural", bukan variasi bahasa. Plan direvisi total: metodologi bukti span diganti ke live Jaeger (preseden `milestones/2.1-.../logs.md` Checkpoint 8), pengujian kejadian mengikuti struktur `evals/<id>-<slug>/{rancangan.md,run_eval.py,payloads/,audit.md}`.
- Dua keputusan genuinely terbuka diajukan lewat `AskUserQuestion`: lokasi orkestrator (`src/orchestration/`, `main.py` tidak disentuh sampai M7.17) dan bentuk state (`KeadaanTurn` akumulator, bukan tuple membesar) — keduanya dijawab Opsi A (rekomendasi).
- Tulis `decisions.md` — 9 keputusan (2 Jenis A, 7 Jenis B).
- Commit hash: `d6bbc56`.

## Checkpoint 2 — Skema dan Orkestrator

- Implementasi `src/schemas/orchestration.py::KeadaanTurn` + `src/orchestration/{__init__.py,turn_pipeline.py}::proses_turn()` — package baru, span `invoke_agent` dibuka pertama kali di `src/` produksi.
- Verifikasi import manual: `from src.orchestration.turn_pipeline import proses_turn` berhasil tanpa error.
- Tabel Struktur Repository `CLAUDE.md`/`AGENT.md` diperbarui (baris baru `src/orchestration/`) sebagai bagian checkpoint ini, sesuai aturan eksplisit CLAUDE.md.
- Commit hash: `94d62a1`.

## Checkpoint 3 — Test Deterministik

- Tulis `tests/orchestration/{__init__.py,test_turn_pipeline.py}` — 2 test mocked: short-circuit (kejadian E03, payload gagal validasi → `detect_turn_dependency` tidak pernah terpanggil) + wiring identity (KeadaanTurn berisi objek persis dari kedua langkah).

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe -m pytest tests/orchestration/test_turn_pipeline.py -v
tests/orchestration/test_turn_pipeline.py::test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil PASSED
tests/orchestration/test_turn_pipeline.py::test_orkestrator_wiring_keadaan_turn_berisi_objek_identik PASSED
2 passed in 5.97s
```

- Commit hash: `7811403`.

## Checkpoint 4 — Peta Kejadian

- Tulis `evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/rancangan.md` — 4 kejadian (E01-E04) dengan Kriteria Keberhasilan eksplisit + kolom "Dibuktikan lewat" (pytest vs `run_eval.py`+Jaeger), ditulis SEBELUM eksekusi.
- Commit hash: `7c7c00a`.

## Checkpoint 5 — Eksekusi Nyata (Jaeger Live)

- `docker version`/`docker info` dicek dulu — Docker Desktop 4.63.0 berjalan.
- `docker compose up -d` di `infra/observability/` — 3 container (`nirwana-jaeger`, `nirwana-otel-collector`, `nirwana-prometheus`) sehat, dikonfirmasi `docker ps`.
- Tulis `evals/7.6-.../run_eval.py` — memanggil `setup_tracing()` + `SpanProcessor` custom (`_TraceIdCapture`) untuk merekam `trace_id` span `invoke_agent`, query Jaeger API nyata (`urllib.request`, retry dengan jeda untuk `BatchSpanProcessor` async).

**Hasil run nyata:**
```
$ .venv/Scripts/python.exe evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/run_eval.py
Menjalankan E01 (turn pertama, tanpa histori)...
  trace_id=73ebea2fc98331410d5f5379d149d8e6
Menjalankan E02 (turn kedua, histori - skenario KK literal M7.6)...
  trace_id=7fd067cab445721fd302defa26329a39
  is_dependent=True, referenced_turn_index=1
  span invoke_agent ditemukan=True, input.validate=True, chat=True
Menjalankan E04 (kegagalan teknis LLM dipaksa)...
  APIError menjalar tanpa ditangkap: True
```

- E02 dikonfirmasi: `payloads/E02.json` field `span_structure_jaeger` menunjukkan `input.validate` (`spanID=aa7d5eed1978631c`) dan `chat` (`spanID=083562ee523b8269`) SAMA-SAMA `parentSpanID=291b010645607d11` (span `invoke_agent`) — bukti nesting nyata, diquery langsung dari Jaeger API, bukan asumsi kode.
- Commit hash: `3492b56`.

## Checkpoint 6 — Audit dan Keterbatasan Diterima

- Tulis `evals/7.6-.../audit.md` — 4/4 kejadian sesuai ekspektasi, E02 dikutip lengkap sebagai bukti KK literal M7.6 (trace_id + tabel span parent-child).
- Tambah entri #14 `docs/keterbatasan-diterima.md` — celah `detect_turn_dependency()` tanpa `try/except APIError`, dikonfirmasi nyata via E04 (`menjalar_tanpa_ditangkap=true`), pemicu peninjauan ulang sebelum M7.17.
- Commit hash: `0610607`.
