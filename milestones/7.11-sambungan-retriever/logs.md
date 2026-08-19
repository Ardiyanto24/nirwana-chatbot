# Logs — Milestone 7.11: Sambungan 6 (Domain Gate → Retriever)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (Plan Mode) menemukan dua gap wiring yang tidak tercakup Lingkup tertulis M7.11 asli (`rancangan-orkestrasi-api.md`): M2.2 (Pemeriksaan Otorisasi) dan M2.3 (Deteksi Cakupan Individu) belum pernah disambungkan `proses_turn()`, meski KK M7.11 sendiri butuh M2.2 dan M7.13 (masa depan) mengasumsikan M2.3 sudah direkam Sambungan 6. Kedua gap diajukan ke user lewat `AskUserQuestion` beserta alternatif dan rekomendasi — user memilih menutup KEDUANYA di dalam M7.11 sendiri (bukan patch M7.10, bukan ditunda ke M7.13). Lokasi kode fungsi batch Retriever baru (`proses_retrieval_semua()`) juga dikonfirmasi: di dalam `src/layers/retriever/kecukupan_struktural.py`, mirror preseden 3x konsisten (`domain_gate.py`/`otorisasi.py`/`cakupan_individu.py`). Menulis `milestones/7.11-sambungan-retriever/decisions.md` — 9 keputusan (3 Jenis A dari hasil `AskUserQuestion`, 6 Jenis B forced by kontrak/preseden).

**Temuan**
Rantai tipe data (`AtomicIntentDomains` → `AtomicIntentAuthorization` → `AtomicIntentConstraint`) sudah dirancang menyatu sejak M2.3 dibangun — docstring `src/schemas/cakupan_individu.py` eksplisit menyebut `domain_decisions` "diteruskan dari M2.2, dibutuhkan Retriever/Query Engine", mengonfirmasi Retriever memang dimaksudkan mengonsumsi output M2.3 (bukan M2.2 langsung).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap dengan 9 entri + Daftar Isi Keputusan, tiap entri Jenis A/B memuat Opsi yang Dipertimbangkan tapi Ditolak sesuai format template resmi.

**Commit:** `7b8a974` — `docs(milestone-7.11): keputusan sambungan otorisasi, cakupan individu, retriever`

---

## Checkpoint 2 — Sambungan Otorisasi (M2.2): Implementasi

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 2-3 — Extend `KeadaanTurn` + wiring `periksa_otorisasi_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah field `otorisasi: list[AtomicIntentAuthorization]` di `KeadaanTurn` (`src/schemas/orchestration.py`), import `AtomicIntentAuthorization` dari `src.schemas.authorization`, extend docstring modul dengan paragraf M7.11 (mencatat rantai pemanggilan lengkap M2.1->M2.2->M2.3->Retriever untuk konteks pembaca, meski field `cakupan_individu`/`retriever` sendiri belum ditambahkan di checkpoint ini). Di `src/orchestration/turn_pipeline.py`: import `periksa_otorisasi_semua`, tambah pemanggilan `periksa_otorisasi_semua(domain_gate_result, payload.role_title)` sekuensial setelah `domain_gate_result` final, isi field `otorisasi` di return `KeadaanTurn`.

**Temuan**
Catatan koreksi diri: draf pertama edit `orchestration.py` sempat menambahkan SEMUA 3 field baru (`otorisasi`, `cakupan_individu`, `retriever`) sekaligus dalam satu edit — menyimpang dari plan yang eksplisit memisahkan Checkpoint 2/4/7 supaya tiap unit wiring independen secara rollback. Dikoreksi SEBELUM sanity-check dijalankan: edit direvisi ulang untuk hanya menambahkan field `otorisasi` di checkpoint ini, field lain ditunda ke Checkpoint 4/7 sesuai plan.

**Error/Kegagalan (jika ada)**
Sanity-check pertama (`python -c "from src.schemas.orchestration import KeadaanTurn"`) gagal `ModuleNotFoundError: No module named 'sqlmodel'` — python sistem dipanggil tanpa venv proyek.

**Diagnosis dan Perbaikan (jika ada error)**
Proyek pakai `uv` (terkonfirmasi `pyproject.toml`+`uv.lock`+`.venv/` di root repo) — perintah diulang dengan `uv run python -c ...`, berhasil.

**Hasil Verifikasi**
`uv run python -c "..."` mengonfirmasi `'otorisasi' in KeadaanTurn.model_fields` -> `True`, dan `turn_pipeline` module berhasil di-import dengan `periksa_otorisasi_semua` tersedia di namespace-nya (tidak ada `ImportError`/`TypeError`).

**Commit:** `3ad75f9` — `feat(milestone-7.11): sambungkan pemeriksaan otorisasi ke proses_turn`

---

## Checkpoint 3 — Sambungan Otorisasi (M2.2): Test Deterministik

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 4-5 — Extend test existing + test connectivity baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`tests/orchestration/test_turn_pipeline.py`: tambah konstanta `_OTORISASI_DUMMY = []`. Extend 7 dari 8 test existing dengan `monkeypatch.setattr(turn_pipeline_module, "periksa_otorisasi_semua", ...)` — test kegagalan cabang paralel (`test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai`) TIDAK perlu diubah karena exception-nya menjalar sebelum `periksa_otorisasi_semua` sempat terpanggil (sama seperti tidak butuh mock `decompose_question`/`match_and_archive`/`identifikasi_domain_semua`). Test short-circuit ditambah assertion "tidak boleh terpanggil" mirror pola 4 fungsi lain. Tulis test baru `test_orkestrator_otorisasi_menerima_domain_gate_result_dan_role_title_benar` — spy merekam `domain_gate_result` (identity check) dan `role_title`, memverifikasi keduanya persis berasal dari `identifikasi_domain_semua()` dan `payload.role_title` ("CEO" dari `_RAW_VALID_TURN1`), bukan kebetulan cocok. Tambah import `AtomicIntentDomains`, `Domain` dari `src.schemas.domain_gate`.

**Temuan**
Tidak ada temuan tak terduga — pola mock 1:1 mengikuti preseden M7.10 Keputusan 7 persis, tanpa penyesuaian tambahan.

**Error/Kegagalan (jika ada)**
Draf pertama test baru sempat memakai nama tipe fiktif `StatusEksekusiDomainGate` (asumsi keliru ada enum status terpisah untuk Domain Gate) — dikoreksi SEBELUM run pertama (dicek ulang terhadap laporan riset: `AtomicIntentDomains.status` memakai `StatusEksekusi` yang SAMA dari `src.schemas.session_memory`, sudah ter-import di file test untuk `_paket_dummy`).

**Diagnosis dan Perbaikan (jika ada error)**
Diperbaiki jadi `StatusEksekusi.BERHASIL` sebelum test dijalankan sama sekali — tidak sempat menyebabkan kegagalan run nyata.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_turn_pipeline.py -v` — 9/9 test PASSED (8 existing + 1 baru), 4.30s, tanpa panggilan LLM/DB nyata.

**Commit:** `e99ac3c` — `test(milestone-7.11): test deterministik sambungan otorisasi`

---

## Checkpoint 4 — Sambungan Cakupan Individu (M2.3): Implementasi

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 6-7 — Extend `KeadaanTurn` + wiring `deteksi_constraint_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah field `cakupan_individu: list[AtomicIntentConstraint]` di `KeadaanTurn`, import `AtomicIntentConstraint` dari `src.schemas.cakupan_individu`. Di `turn_pipeline.py`: import `deteksi_constraint_semua`, tambah pemanggilan `deteksi_constraint_semua(otorisasi_result, payload.role_title)` sekuensial setelah `otorisasi_result` final, isi field `cakupan_individu` di return `KeadaanTurn`.

**Temuan**
Tidak ada — pola identik Checkpoint 2, kali ini berhasil dijaga hanya menambah SATU field (pelajaran dari koreksi diri Checkpoint 2 diterapkan konsisten).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run python -c "..."` mengonfirmasi `'cakupan_individu' in KeadaanTurn.model_fields` -> `True`, `turn_pipeline` module berhasil di-import dengan `deteksi_constraint_semua` tersedia.

**Commit:** `5081212` — `feat(milestone-7.11): sambungkan deteksi cakupan individu ke proses_turn`

---

## Checkpoint 5 — Sambungan Cakupan Individu (M2.3): Test Deterministik

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 8-9 — Extend test existing + test connectivity baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah konstanta `_CAKUPAN_INDIVIDU_DUMMY = []`. Extend 8 dari 9 test existing (termasuk test connectivity Otorisasi yang baru ditambah Checkpoint 3) dengan mock `deteksi_constraint_semua` — test kegagalan cabang paralel tetap tidak perlu diubah (exception menjalar sebelum titik ini). Tulis test baru `test_orkestrator_cakupan_individu_menerima_otorisasi_result_dan_role_title_benar` — spy merekam `otorisasi_result` (identity check terhadap `AtomicIntentAuthorization` buatan tangan) dan `role_title`, mirror persis pola test Otorisasi Checkpoint 3. Tambah import `AtomicIntentAuthorization`, `DomainAuthorization` dari `src.schemas.authorization`.

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_turn_pipeline.py -v` — 10/10 test PASSED (9 existing + 1 baru), 4.63s, tanpa panggilan LLM/DB nyata.

**Commit:** *(dicatat di commit berikutnya)*

---
