# Logs — Milestone 7.1: Audit Kontrak Antar-Layer yang Sudah Terimplementasi

## Checkpoint 1 — Persiapan & Keputusan

- Commit `docs/02-implementation-plan/rancangan-orkestrasi-api.md` (sudah ditulis sebelumnya, untracked) — dokumen sumber lengkap grup 7.x (Level 1 M7.2-7.5, Level 2 M7.6-7.16, M7.17 endpoint, M7.18 Database Percakapan).
- Tambah item 9 "Dokumen Sumber Kebenaran" di `CLAUDE.md`/`AGENT.md` (rujukan ke dokumen di atas), renumber item domain-source lama (9→10) dan milestones (10→11). Kedua file gitignored, tidak masuk commit git (sesuai konvensi project).
- Tulis `decisions.md` — 7 keputusan (5 forced/preseden + 2 genuinely-terbuka yang sudah dijawab user lewat `AskUserQuestion` di Plan Mode).
- Commit hash: `cc42857` (docs: rancangan-orkestrasi-api.md), `fd0df15` (docs: decisions.md).

## Checkpoint 2 — Audit PIC 1 (Input Layer, Context Resolution, Decomposition)

**Task 3 — Audit source.** Dibaca langsung (bukan mengandalkan ringkasan sesi planning): `src/schemas/turn_payload.py`, `src/layers/context_resolution/turn_dependency.py`, `src/layers/context_resolution/rewrite.py`, `src/layers/context_resolution/session_memory.py`, `src/layers/context_resolution/matching.py`, `src/layers/decomposition/decompose.py`, `src/schemas/decomposition.py`.

Temuan kunci yang dikonfirmasi langsung dari kode (bukan asumsi):
- `decompose_question()` (M1.6): `_MAX_ATTEMPTS = 3`, loop `while True` dengan `attempt` mulai 1, break kalau `verifikasi.valid` atau `attempt >= 3`. Klasifikasi 1x di luar loop + Pemecahan/Verifikasi hingga 3x di dalam loop = **hingga 7 pemanggilan LLM total** dalam kasus terburuk. Dicatat sebagai penyimpangan dari framing "3 pemanggilan LLM berurutan" di `rancangan-orkestrasi-api.md` — lihat `audit-kontrak-antar-layer.md` bagian M1.6.
- `matching.py::_sumber_arsip()` (M1.7): mekanisme penjagaan rantai turn-asal lintas pengarsipan berulang — detail yang tidak sepenuhnya tertangkap ringkasan awal, ditambahkan ke audit.
- `src/main.py` dikonfirmasi ulang murni echo `POST /v1/turns`, nol layer lain terpanggil.

Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 1".

**Task 4 — Panggilan nyata minimal per unit** (env `OPENROUTER_API_KEY`/`DATABASE_URL` aktif otomatis lewat `load_dotenv()` di `src/config/llm.py`/`database.py`):

| Unit | Test dijalankan | Hasil | Durasi |
|---|---|---|---|
| M1.2 Input Layer | `tests/layers/test_input_layer.py` (seluruh file, 12 test — real `TestClient`, tanpa biaya eksternal) | 12 passed | 6.08s |
| M1.3 Turn Dependency | `test_turn_dependency.py::test_kelompok_a_rujukan_eksplisit_ke_turn_sebelumnya` | 1 passed | 11.47s |
| M1.4 Rewrite | `test_rewrite.py::test_kelompok_a_elipsis_diresolusi_jadi_eksplisit` | 1 passed | 8.57s |
| M1.5 Session Memory | `test_session_memory.py::test_kelompok_a_simpan_lalu_ambil_kembali_identik` (real Supabase round-trip) | 1 passed | 2.50s |
| M1.6 Decomposition | `test_decompose.py::test_kelompok_a_majemuk_bergantung_relasi_benar` (rantai penuh klasifikasi→pemecahan→verifikasi) | 1 passed | 42.86s (konsisten ≥3 LLM call berurutan) |
| M1.7 Matching | `test_matching.py::test_kelompok_c_rantai_arsip_ulang_turn_tujuh_lima_tiga` (skenario rantai arsip, LLM+DB) | 1 passed | 28.61s |

Seluruh 6 unit PIC 1 lolos panggilan nyata — tidak ada skip/mock terdeteksi (durasi tiap test konsisten dengan pemanggilan API/DB sungguhan, bukan instan seperti mock).
