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

## Checkpoint 3 — Audit PIC 2 (Domain Gate, Verification Gate)

**Task 5 — Audit source.** Dibaca langsung: `src/layers/domain_gate/{domain_gate,identifikasi,verifikasi_titik_buta,otorisasi,cakupan_individu,deteksi_cakupan_individu,verifikasi_cakupan_individu}.py`, `src/layers/verification_gate/verifikasi_gate.py`. Temuan kunci dikonfirmasi langsung dari kode:
- M2.1: penggabungan Langkah 1+2 union aditif via `dict.fromkeys()` (dedup, urutan dipertahankan), status `SEBAGIAN` kalau verifikasi gagal teknis. Langkah 2 di-skip total kalau Langkah 1 gagal (bukan dipanggil dengan domain kosong).
- M2.3: dua pre-filter deterministik persis sesuai ringkasan awal — `ROLE_STAFF_TIER` (7 role) dan domain relevan `{FACILITY, HR}`; fail-closed (`terdeteksi=True`) hanya kalau KEDUA langkah LLM gagal teknis sekaligus (arah fail-safe berlawanan dari M1.7).
- M2.4: 4 cek berlapis dikonfirmasi tepat urutannya (statis→kepatuhan sumber→tegakkan constraint→verifikasi kelengkapan), `LIMIT_MAKSIMUM=1000` eksplisit di kode, early-exit hanya di Cek 1-2 (Cek 3 tidak pernah menolak, hanya mengoreksi paksa).

Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 2".

**Task 6 — Panggilan nyata minimal per unit:**

| Unit | Test dijalankan | Hasil | Durasi |
|---|---|---|---|
| M2.1 Domain Gate | `test_domain_gate.py::test_kelompok_a_union_domain_berhasil` (real LLM, 2 langkah) | 1 passed | 42.26s |
| M2.2 Otorisasi | `test_otorisasi.py::test_kk2_multi_domain_sebagian_diizinkan_sebagian_ditolak` (real DB role_permissions) | 1 passed | 3.26s |
| M2.3 Cakupan Individu | `test_cakupan_individu.py::test_kk1_staff_kebutuhan_individu_menghasilkan_constraint_eksplisit` (real LLM, 2 langkah) | 1 passed | 27.82s |
| M2.4 Verification Gate | `test_verifikasi_gate.py::test_orkestrator_kk1_constraint_terdeteksi_dikoreksi_paksa` (real DB employee fixture) | 1 passed | 2.02s |

Seluruh 4 unit PIC 2 lolos panggilan nyata.
