# Logs — Milestone 3.4: Penyusunan Request

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.4-penyusunan-request/decisions.md`: 15 keputusan (1 Jenis A hasil `AskUserQuestion` + klarifikasi lanjutan langsung ke user dalam sesi perencanaan — konvensi penamaan parameter nama kolom asli view, ditambah instruksi eksplisit user untuk dokumen kontrak usulan terpisah; 14 Jenis B forced/preseden — reuse `QueryEngineRequest`, domain diturunkan kode, signature menerima `view_name` langsung, `tanggal_referensi` WIB, status biner validator dua arah, `employee_id`/`role_title` tidak pernah diisi, filter defensif, subpackage baru, observability, lokasi dokumen kontrak, entri keputusan-tertunda).

**Temuan**
Tidak ada temuan baru di luar yang sudah tercatat di plan (Context "Temuan Penting").

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh keputusan di plan yang disetujui punya entri `decisions.md` dengan "Opsi yang Dipertimbangkan tapi Ditolak".

**Commit:** `6a945d9` — `docs(milestone-3.4): decisions.md keputusan awal`

---

## Checkpoint 2 — Kontrak Parameter `chatbot_api` Usulan

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 2 — Bangun `param_whitelist.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `src/layers/query_engine/param_whitelist.py` — `_ekstrak_nama_kolom()` parse tabel Markdown "| Kolom | Deskripsi |" per entri `DEFINISI_LENGKAP_VIEW` (HANYA sel pertama tiap baris, supaya backtick di sel Deskripsi seperti nilai enum tidak salah tertangkap sebagai nama kolom), `_whitelist_dari_kolom()` mengklasifikasi kolom bertema tanggal (substring "date") jadi 3 entri (exact + `_from`/`_to`), kolom lain 1 entri exact. `PARAM_WHITELIST_VIEW: dict[str, frozenset[str]]` untuk 67 view, `limit`/`offset` ditambahkan ke semua, `employee_id`/`role_title`/`domain`/`view_name` tidak pernah masuk.

**Temuan**
Dua pola pemisah kolom-ganda-per-baris ditemukan di korpus (koma: "`property_id`, `property_name`, `region`"; garis miring: "`avg_lead_time_days` / `median_lead_time_days`") — keduanya tertangani otomatis oleh regex `_BACKTICK_NAME` yang mencari SEMUA nama berformat backtick di sel, tanpa perlu logic split per separator berbeda.

**Error/Kegagalan**
Tidak ada — sanity check manual (`PARAM_WHITELIST_VIEW['v_reservation_room_type_daily']`, dst.) lolos pada percobaan pertama.

**Hasil Verifikasi**
Lihat Task 3.

**Commit:** `9716096` — `feat(milestone-3.4): whitelist parameter per-view`

---

### Task 3 — Test Whitelist Parameter

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/query_engine/test_param_whitelist.py` — 12 test: bijektif dengan `DAFTAR_VIEW_PER_DOMAIN`, 67-count, nol view gagal parsing (whitelist > sekadar param global), param global selalu ada, param terlarang tidak pernah bocor, spot-check kolom multi-per-baris (koma DAN garis miring), sel Deskripsi tidak ikut terekstrak (`v_maintenance_ticket_daily` — `critical`/`high`/`medium`/`low` dari teks penjelasan `sla_threshold_hours` WAJIB tidak muncul di whitelist), view tanpa `property_id` konsisten katalog (`v_financial_business_line_group_monthly`).

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada — seluruh 12 test lolos pada percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/query_engine/test_param_whitelist.py -v` → 12 passed.

**Commit:** `147b313` — `test(milestone-3.4): verifikasi whitelist parameter`

---

### Task 4 — Dokumen Kontrak Parameter Usulan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Skrip sekali-pakai (`scratchpad/gen_kontrak_parameter.py`, tidak di-commit, mirror pola `korpus_view.py`/`definisi_view.py`) membangkitkan `docs/kontrak-parameter-chatbot-api-usulan.md` dari `PARAM_WHITELIST_VIEW` + `DAFTAR_VIEW_PER_DOMAIN` — pembuka menjelaskan status USULAN (bukan kontrak resmi), aturan derivasi, pemicu peninjauan ulang, lalu tabel 67 baris dikelompokkan per 10 domain (mirror struktur `katalog-data-chatbot.md`).

**Temuan (konsekuensi desain, dicatat untuk `report.md` Bagian 5)**
`PARAM_TERLARANG` (Keputusan 7 `decisions.md`) mengecualikan `employee_id` secara GLOBAL dari seluruh whitelist — termasuk `v_employees_directory`, padahal Fungsi view itu sendiri secara eksplisit "cari nama karyawan dari ID" (lookup by `employee_id` adalah use-case UTAMA-nya, bukan soal cakupan-individu seperti 9 view "performa individu" M2.3 yang jadi alasan awal pengecualian). Konsekuensi: M3.4 kehilangan kapabilitas mengisi filter `employee_id` langsung untuk lookup direktori sederhana pada view ini secara spesifik — trade-off yang sengaja diterima (konsistensi aturan sederhana > pengecualian kasus-per-kasus) tapi didokumentasikan transparan, bukan disembunyikan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Dokumen dibaca ulang manual (143 baris), dicocokkan sampel terhadap `katalog-data-chatbot.md` untuk beberapa view (`v_reservation_room_type_daily`, `v_properties_ref`, `guests_profile_view`) — seluruhnya sesuai.

**Commit:** `dbfe396` — `docs: kontrak parameter chatbot_api usulan`

---

### Task 5 — Entri `keputusan-tertunda.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan entri #3 ke `docs/keputusan-tertunda.md` — konvensi parameter AKTIF dipakai tapi provisional, 3 pemicu peninjauan eksplisit (rekonsiliasi tim `chatbot_api` di akhir proyek, pola kegagalan `400` berulang di M4.x, dokumentasi whitelist resmi tersedia lebih awal).

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Dibaca ulang manual, format konsisten dengan entri #1-2 yang sudah ada.

**Commit:** `09620ea` — `docs: catat keputusan tertunda konvensi parameter chatbot_api`

---

## Checkpoint 3 — Skema `HasilPenyusunanRequest`

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6-7 — Skema + Test

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/schemas/query_engine.py` — `HasilPenyusunanRequest` reuse `QueryEngineRequest` (M2.4), validator dua arah (`status=BERHASIL` <=> `request` terisi). `tests/layers/query_engine/test_query_engine_schema.py` — 7 test mencakup seluruh kombinasi status valid/tidak valid.

**Temuan / Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/query_engine/ -v` → 19 passed (12 whitelist + 7 skema).

**Commit:** `14fa7be` (feat) + `fb9f6b5` (test).

---

## Checkpoint 4 — Prompt + Config Plumbing

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 8-10 — Konstanta Model, Span Attributes, Prompt

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`OPENROUTER_MODEL_PENYUSUNAN_REQUEST` (Qwen3-32B) ditambahkan ke `src/config/llm.py`. `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` ditambahkan ke `genai_semconv.py` (pola sama `PROMPT_ID`/`PROMPT_VERSION`). `src/prompts/query_engine/penyusunan_request.md` ditulis — instruksi resolusi tanggal relatif, daftar parameter valid (bukan tabel kolom mentah), larangan mengisi `employee_id`/`role_title`/`domain`/`view_name`.

**Temuan / Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`load_prompt("query_engine.penyusunan_request")` sukses parse + render. `pytest tests/layers/query_engine/ tests/layers/retriever/ tests/config/ -q` (regresi lintas subpackage) → 146 passed.

**Commit:** `16b7258` (konstanta) + `967a04b` (prompt).

---

## Checkpoint 5 — Fungsi LLM Call + Filter Defensif + Orkestrator

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 11-13 — Implementasi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/layers/query_engine/penyusunan_request.py`: `_call_llm()` (panggilan mentah, dipisah untuk reuse eval), `_parse_response()` (parse `{"params": {...}}`, gagal total kalau JSON rusak/skema salah), `_saring_params_tidak_dikenal()` (exact match terhadap `PARAM_WHITELIST_VIEW[view_name]`, strip paksa `PARAM_TERLARANG`), `susun_request_atomic_intent()` (orkestrator: span `"chat"` dengan `request.domain`/`request.view_name`/`prompt.id`/`prompt.version`, `domain` diturunkan `view_ke_domain()[view_name]`, `tanggal_referensi` default WIB `timezone(timedelta(hours=7))` — dipilih fixed-offset ketimbang `zoneinfo`/`Asia/Jakarta` supaya tidak butuh package `tzdata` tambahan di Windows, ekuivalen persis karena Indonesia tidak menerapkan DST).

**Temuan**
Tidak ada penyimpangan dari plan.

**Error/Kegagalan**
Tidak ada — seluruh 16 test lolos pada percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/query_engine/ -v` → 35 passed (12 whitelist + 7 skema + 16 orkestrator). Regresi lintas subpackage (`tests/layers/query_engine/ tests/layers/retriever/ tests/config/ tests/layers/verification_gate/`) → 182 passed.

**Commit:** `5b70cdf` (feat) + `b0d1ecf` (test).

---

## Checkpoint 6 — Eval Nyata

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 15-17 — Rancangan, Eksekusi Nyata, Audit

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/3.4-penyusunan-request/rancangan.md` (7 skenario: bulan lalu, tiga bulan terakhir, filter kategorikal, resolusi nama properti, kebutuhan minimal, view tanpa tanggal, adversarial param tak-dikenal). `run_eval.py` menjalankan `susun_request_atomic_intent()` NYATA dengan `tanggal_referensi=2026-08-17` tetap. Dieksekusi 3 kali (run 1 awal → 5/7; retry S02 saja mengonfirmasi kegagalan pertama transient → LOLOS; run final penuh pasca-prompt-v2 → 6/7).

**Temuan**
1. S02 (run 1) `status=gagal_teknis` — retry tunggal langsung berhasil, dikonfirmasi transient (pola sama `docs/keterbatasan-diterima.md` #7, bukan bug baru).
2. S04: `property_name="Nirwana Lombok Escape"` dipakai alih-alih `property_id="P05"` — ditinjau ulang BUKAN bug (parameter sama-sama valid, model tidak pernah diberi tabel nama→kode di prompt) - `check()` rancangan terlalu ketat, dikoreksi transparan di `audit.md`.
3. S04: nilai `occupancy_rate: "nilai_tunggal"` (nonsensikal — label bentuk jawaban salah masuk sebagai NILAI filter kolom metrik) — temuan kualitas nyata, SENGAJA tidak diperbaiki M3.4 (filter defensif hanya validasi KEY bukan kewajaran NILAI) - mengonfirmasi peran M3.5 (verifikasi independen, di luar cakupan) untuk menangkap kasus persis ini.
4. S05 (run 1, prompt v1): `params={"property_id": "Nirwana"}` — model salah menafsirkan nama GRUP perusahaan sebagai nama properti spesifik. **Diperbaiki**: prompt dibump ke v2, aturan eksplisit ditambahkan. Diverifikasi ulang: `params={}` benar.

**Error/Kegagalan**
S02 run 1: `status=gagal_teknis` (lihat Temuan 1, transient, tidak direplikasi run berikutnya).

**Hasil Verifikasi**
Run final: `python evals/3.4-penyusunan-request/run_eval.py` → 6/7 LOLOS (S04 REVIEW dikoreksi jadi lolos substansi di `audit.md`, bukan kegagalan mekanisme).

**Commit:** `7a23099` (fix prompt v2) + `f35e62e` (docs eval).

---

## Checkpoint 7 — Reliability Testing Promptfoo (Native)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 18-19 — Config + Run + Iterasi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`prompt_reliability/query_engine/penyusunan_request.promptfooconfig.yaml` — 4 skenario native (user_prompt diambil persis dari `_build_user_prompt()` nyata via skrip verifikasi sekali-pakai, dihapus setelah dipakai). Run 1 (prompt v1): 3/4 lolos — S04 (kebutuhan minimal) gagal, replikasi PERSIS temuan "Nirwana" dari eval Checkpoint 6, mengonfirmasi silang lewat dua jalur independen (eval manual + Promptfoo). Run 2 (prompt v2, setelah perbaikan): **4/4 lolos (100%)**.

**Temuan**
Tidak ada temuan tooling baru (assertion JS ditulis langsung pakai `return` eksplisit sejak awal, belajar dari bug M3.3 Checkpoint 14/7 — tidak terulang).

**Error/Kegagalan**
Run 1 S04 gagal (lihat Temuan Checkpoint 6 #4) — diperbaiki via prompt v2, bukan dianggap kegagalan tersisa.

**Hasil Verifikasi**
Hasil run 2 dipush ke `prompt_eval_runs` (Supabase) — 4 baris terverifikasi (`Berhasil push 4 baris`).

**Commit:** `66bfbc3` (config awal).

---
