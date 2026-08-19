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

**Commit:** `0bd95fb` — `test(milestone-7.11): test deterministik sambungan cakupan individu`

---

## Checkpoint 6 — Retriever: Bangun `proses_retrieval_semua()` Baru

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 10-11 — Fungsi batch baru + unit test standalone

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `src/layers/retriever/kecukupan_struktural.py` lengkap + `tests/layers/retriever/test_kecukupan_struktural.py` (khususnya bagian `proses_retrieval_atomic_intent`, baris 416-528) untuk memahami konvensi mock (`monkeypatch.setattr(kecukupan_struktural_module, ...)`) dan helper fixture (`_buat_atomic_intent()`). Juga dicek `tests/layers/domain_gate/test_otorisasi.py` — dikonfirmasi skenario "Front Office Staff: reservation DIIZINKAN, financial DITOLAK" SUDAH ada sebagai test existing (`test_kk2_multi_domain_sebagian_diizinkan_sebagian_ditolak`), menguatkan rencana reuse skenario ini untuk E01 eval Checkpoint 9.

Tambah `proses_retrieval_semua(daftar_constraint: list[AtomicIntentConstraint]) -> list[HasilKecukupanStruktural]` di `kecukupan_struktural.py` — untuk tiap item, derive `domain_diizinkan` dari `item.domain_decisions` (filter `diizinkan=True`), panggil `proses_retrieval_atomic_intent(item.atomic_intent, domain_diizinkan)`; span pembungkus `retriever.proses_semua` (tracer `retriever.retriever`, sama dengan `proses_retrieval_atomic_intent`), atribut `intent.count`. Import baru: `AtomicIntentConstraint` dari `src.schemas.cakupan_individu`.

Tulis 4 unit test baru di `tests/layers/retriever/test_kecukupan_struktural.py` (helper `_buat_constraint()`, `_hasil_kecukupan_dummy()`): (1) filter `diizinkan=True` terbukti benar — domain ditolak tidak ikut diteruskan; (2) domain kosong (seluruh ditolak) TETAP diproses, tidak di-skip; (3) urutan+panjang hasil dipertahankan multi-item; (4) list kosong -> hasil kosong tanpa error.

**Temuan**
Tidak ada temuan tak terduga — struktur file dan konvensi mock persis seperti diperkirakan dari riset plan.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/layers/retriever/ -v` — 125/125 test PASSED (121 existing + 4 baru), 13.08s, regresi nol pada seluruh test retriever existing.

**Commit:** `31f143d` (feat) + `4d7ca40` (test)

---

## Checkpoint 7 — Sambungan Retriever: Implementasi

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 12-13 — Extend `KeadaanTurn` + wiring `proses_retrieval_semua()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah field `retriever: list[HasilKecukupanStruktural]` di `KeadaanTurn` — field TERAKHIR yang ditambahkan M7.11, melengkapi rantai penuh `payload -> ketergantungan -> rewrite -> session_memory -> decomposition -> matches -> domain_gate -> otorisasi -> cakupan_individu -> retriever` (10 field). Di `turn_pipeline.py`: import `proses_retrieval_semua` dari `src.layers.retriever.kecukupan_struktural`, panggil sekuensial setelah `cakupan_individu_result` final, isi field `retriever`. Ini SECARA RESMI Sambungan 6 (Domain Gate -> Retriever) yang jadi judul asli M7.11 — Checkpoint 2-6 sebelumnya adalah prasyarat (M2.2/M2.3 wiring + fungsi batch baru) yang genuinely dibutuhkan sebelum sambungan ini bisa dibuktikan bekerja.

**Temuan**
Tidak ada — pola identik Checkpoint 2/4, disiplin satu-field-per-checkpoint dipertahankan sampai akhir.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run python -c "..."` mengonfirmasi `'retriever' in KeadaanTurn.model_fields` -> `True`, `proses_retrieval_semua` tersedia di `turn_pipeline` module, dan urutan 10 field `KeadaanTurn.model_fields.keys()` sesuai rantai yang direncanakan.

**Commit:** `f1168a4` — `feat(milestone-7.11): sambungkan retriever ke proses_turn`

---

## Checkpoint 8 — Sambungan Retriever: Test Deterministik

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 14-15 — Extend test existing + test connectivity baru

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tambah konstanta `_RETRIEVER_DUMMY = []`. Extend 9 dari 10 test existing dengan mock `proses_retrieval_semua` (kegagalan cabang paralel tetap tidak berubah, alasan identik 3 checkpoint test sebelumnya). Tulis test baru `test_orkestrator_retriever_menerima_cakupan_individu_result_persis` — spy merekam `cakupan_individu_result` (identity check terhadap `AtomicIntentConstraint` buatan tangan), menutup rantai penuh 4 test connectivity M7.11 (Otorisasi Checkpoint 3, Cakupan Individu Checkpoint 5, Retriever Checkpoint 8) yang masing-masing membuktikan SATU sambungan spesifik. Tambah import `AtomicIntentConstraint`, `ConstraintCakupanIndividu` dari `src.schemas.cakupan_individu`.

**Temuan**
Total test file kini 11 test (dari 7 sebelum M7.11 dimulai) — 4 test baru M7.11 (Otorisasi, Cakupan Individu, Retriever connectivity, masing-masing 1) ditambah extend mock di seluruh 9-10 test lama tiap checkpoint. Pola mock berlapis (tiap checkpoint menambah satu `monkeypatch.setattr` baru ke SEMUA test existing) terbukti scalable tapi verbose - dicatat sebagai observasi murni, bukan masalah yang perlu diperbaiki (konsisten preseden M7.6-7.10).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`uv run pytest tests/orchestration/test_turn_pipeline.py -v` — 11/11 test PASSED (10 existing + 1 baru), 3.70s, tanpa panggilan LLM/DB nyata.

**Commit:** `ff3ae12` — `test(milestone-7.11): test deterministik sambungan retriever`

---

## Checkpoint 9 — Peta Kejadian

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 16 — Tulis `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `evals/7.10-sambungan-domain-gate/{rancangan.md,run_eval.py,audit.md}` lengkap untuk mirror struktur+gaya persis (bukan contoh minimal template). Ditelusuri role×domain matrix (`docs/03-domain-source/rancangan-rbac-ai-chatbot.md` Bagian 2) untuk memilih kombinasi role/pertanyaan yang PASTI menghasilkan skenario yang diinginkan tanpa menebak: **Front Office Staff** (hanya `reservation`) untuk E01 (reuse skenario `gop_margin` PERSIS dari M2.1/M7.3 — pertanyaan cross-domain reservation+financial yang sudah terbukti nyata menghasilkan identifikasi 2 domain); **CEO** (semua domain) untuk E02 baseline; **F&B Staff** (hanya `fnb`) ditanya metrik `financial` murni untuk E03 edge case (domain kosong); **HR Staff** dengan pertanyaan PERSIS `evals/2.3-.../S01.json` ("Bagaimana hasil review kinerja Budi semester ini?", sudah terbukti `terdeteksi=True` di M2.3 asli) untuk E04 bukti sambungan Cakupan Individu.

Tulis `evals/7.11-sambungan-retriever/rancangan.md` — 4 kejadian, ekspektasi ditulis sebagai INVARIAN MEKANISME (bukan jumlah atomic_intent absolut) mengikuti pelajaran eksplisit `audit.md` M7.10 Bagian "Temuan Metodologi".

**Temuan**
Seluruh 4 role_title (`Front Office Staff`, `CEO`, `F&B Staff`, `HR Staff`) dikonfirmasi valid via `load_valid_roles()` sebelum ditulis ke `rancangan.md` — mencegah kejadian gagal validasi Input Layer karena typo nama role.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review manual `rancangan.md` — 4 kejadian, tiap kejadian py ekspektasi konkret per-domain (bukan jumlah absolut), tabel ringkasan mencakup kolom `domain_diizinkan ke Retriever` dan `cakupan_individu.terdeteksi` untuk memudahkan verifikasi silang Checkpoint 10.

**Commit:** *(dicatat di commit berikutnya)*

---
