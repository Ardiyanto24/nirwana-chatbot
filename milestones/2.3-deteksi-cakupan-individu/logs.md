# Logs — Milestone 2.3: Membangun Deteksi Constraint Cakupan-Individu

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `e54ae24` | `docs(milestone-2.3): decisions` |
| 2 | `47a8585`, `3c134d5` | `feat(milestone-2.3): skema data constraint cakupan-individu` + `test(milestone-2.3): validator constraint cakupan-individu` |
| 3 | `5ce242b`, `3af6b73` | `feat(milestone-2.3): konstanta model + konteks grounding 9 view` + `test(milestone-2.3): verifikasi konteks grounding 9 view` |
| 4 | `582ef9b`, `3d4dadd`, `db3e93d` | `feat(milestone-2.3): prompt deteksi awal cakupan-individu` + `feat(milestone-2.3): langkah 1 deteksi awal cakupan-individu` + `test(milestone-2.3): verifikasi deteksi awal cakupan-individu` |
| 5 | `3821933`, `880d046`, `8f8c91c` | `feat(milestone-2.3): prompt verifikasi titik buta cakupan-individu` + `feat(milestone-2.3): langkah 2 verifikasi titik buta cakupan-individu` + `test(milestone-2.3): verifikasi titik buta cakupan-individu` |
| 6 | `3895fed`, `497a00f` | `feat(milestone-2.3): orkestrator deteksi constraint + observability` + `test(milestone-2.3): pre-filter role dan domain cakupan-individu` |
| 7 | `cbf616a` | `test(milestone-2.3): verifikasi KK1-3 real LLM` |
| 8 | `3864cdc` | `docs(milestone-2.3): verifikasi span nyata` |
| 9 | `404affa`, `f723f99` | `test(evals): skenario deteksi cakupan-individu` + `docs(evals): audit hasil deteksi cakupan-individu` |
| 10 | `822a0fc`, `4f055e1` | `chore(prompt-reliability): config deteksi+verifikasi cakupan-individu` + `docs(prompt-reliability): perbarui README - config M2.3 + status akurat` |
| 11 | `294bb85`, *(status project)* | `docs(milestone-2.3): report` + `docs: perbarui status project` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama, sebelum kode apa pun, setelah plan disetujui user lewat Plan Mode. Dua keputusan genuinely terbuka (daftar 9 view, mekanisme LLM) dikonfirmasi lewat `AskUserQuestion` SEBELUM plan ditulis (bukan saat Checkpoint 1), sesuai instruksi `CLAUDE.md` — `decisions.md` di sini mendokumentasikan hasil konfirmasi itu, bukan tempat pertama kali keputusan diambil.

**Apa yang dilakukan**
12 entri keputusan: 2 Jenis A genuinely terbuka dari `AskUserQuestion` (daftar eksplisit 9 view kategori performa individu hasil tinjauan langsung ke `katalog-data-chatbot.md`; mekanisme LLM generate-verify dual-call union aditif, pola M2.1), 10 Jenis B forced/preseden (transkripsi tier "Staff" sebagai frozenset, pre-filter role sebelum LLM, pre-filter domain facility/hr sebelum LLM, skema output rata bukan nesting, fail-closed saat kegagalan teknis, model constants terisolasi, subpackage domain_gate/ yang sama, folder evals/ dibuat, prompt-file-first + Promptfoo natif sejak awal karena kontrak Manajemen Prompt sudah mengikat, decisions.md sebagai task pertama).

**Temuan**
Tinjauan langsung ke `docs/03-domain-source/katalog-data-chatbot.md` mengonfirmasi hanya 2 dari 10 domain (`facility`, `hr`) yang ditandai eksplisit py sensitivitas performa individu di Ringkasan 10 Domain (baris 47, 49) — bukan hasil tebakan, melainkan penandaan tersurat di dokumen sumber sendiri.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `e54ae24`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 2 — `src/schemas/cakupan_individu.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ConstraintCakupanIndividu` (`terdeteksi: bool`, `alasan: str | None` + validator konsistensi), `AtomicIntentConstraint` (flat: `atomic_intent`, `domain_decisions: list[DomainAuthorization]`, `constraint`), `DeteksiCakupanIndividuResult`/`VerifikasiCakupanIndividuResult` (hasil antara Langkah 1/2, mirror `IdentifikasiDomainResult`/`VerifikasiTitikButaResult` M2.1).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `47a8585`

### Task 3 — Test validator `ConstraintCakupanIndividu`

**Kesesuaian dengan plan:** Sesuai plan — dibuat langsung sebagai task sendiri (bukan didefer), file `test_cakupan_individu.py` mulai diisi di sini, akan ditambah bertahap CP6-7.

**Apa yang dilakukan**
4 test: `terdeteksi=True`+`alasan=None` ditolak, `terdeteksi=False`+`alasan` terisi ditolak, kedua kombinasi valid diterima.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_cakupan_individu.py` — 4/4 PASSED.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `3c134d5`

---

## Checkpoint 3 — Konfigurasi & Konteks Grounding

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 4 — 2 konstanta model di `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI` (Qwen3-32B, reuse nilai) dan `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI` (DeepSeek V4 Pro, reuse nilai) + entri docstring.

**Commit:** `5ce242b`

### Task 5 — `konteks_cakupan_individu.py` + test

**Kesesuaian dengan plan:** Sesuai plan. Deviasi kecil murni administratif: commit Task 4 di atas HANYA berisi `llm.py` (pesan commit menyebut "konteks grounding" tapi filenya menyusul di commit Task 5 bersama test-nya) — pemisahan kode-vs-test sesuai kategori tetap terjaga, hanya urutan file dalam 2 commit itu tidak persis seperti draft rencana awal. Tidak mengubah bentuk kode akhir.

**Apa yang dilakukan**
`ViewCakupanIndividu` (dataclass: nama, domain, kolom_identitas, deskripsi), `DAFTAR_VIEW_CAKUPAN_INDIVIDU` (9 entri: 4 facility + 5 hr, dari Keputusan 1), `CATATAN_INDIVIDU_VS_AGREGAT` (penjelasan kriteria individu vs agregat + jebakan kata kunci, dipakai kedua prompt CP4-5).

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_konteks_cakupan_individu.py` — 6/6 PASSED (jumlah=9, domain hanya facility/hr, 4+5 per domain, nama persis sesuai Keputusan 1, tidak ada view agregat yang lolos, tiap entri punya kolom_identitas+deskripsi).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `3af6b73`

---

## Checkpoint 4 — Langkah 1: Deteksi Awal

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 6 — Prompt `deteksi_cakupan_individu.md`

**Kesesuaian dengan plan:** Sesuai plan — prompt-file-first sejak awal (Keputusan 11), bukan hardcode dulu.

**Apa yang dilakukan**
System prompt dengan grounding 9 view (loop Jinja2, sama pola `identifikasi.md`) + `CATATAN_INDIVIDU_VS_AGREGAT`, minta output JSON `{"terdeteksi": true/false}`.

**Commit:** `582ef9b`

### Task 7 — `deteksi_cakupan_individu.py` + test real-LLM

**Kesesuaian dengan plan:** Sesuai plan — mirror struktur `identifikasi.py` persis.

**Apa yang dilakukan**
`deteksi_cakupan_individu(atomic_intent) -> DeteksiCakupanIndividuResult`, `_call_llm`/`_parse_and_decide` dipisah, span `chat` dengan `prompt.id`/`prompt.version`, guard `response.choices` kosong. `_DAFTAR_VIEW_RENDER` mengonversi `Domain` enum ke `.value` string eksplisit sebelum masuk context Jinja2 (konsisten pola `_DAFTAR_DOMAIN` M2.1 — hindari ambiguitas `str(Enum)`).

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_deteksi_cakupan_individu.py` — 8/8 PASSED (3 pure-function + 5 real-LLM: performa staf tertentu, ranking staf tercepat, jumlah staf hadir hari ini, rata-rata skor departemen, di luar domain facility/hr). Real-LLM run nyata (107.57s total), `OPENROUTER_API_KEY` tersedia di environment.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `3d4dadd` (kode), `db3e93d` (test)

---

## Checkpoint 5 — Langkah 2: Verifikasi Titik Buta

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 8 — Prompt `verifikasi_cakupan_individu.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
System prompt verifier independen (mirror `verifikasi_titik_buta.md`), user prompt membawa kesimpulan Langkah 1 sebagai konteks tapi instruksi eksplisit menilai independen.

**Commit:** `3821933`

### Task 9 — `verifikasi_cakupan_individu.py` + test real-LLM

**Kesesuaian dengan plan:** Sesuai plan — mirror `verifikasi_titik_buta.py` persis, model DeepSeek V4 Pro `reasoning="high"`. Reuse `_DAFTAR_VIEW_RENDER` dari `deteksi_cakupan_individu.py` (bukan duplikasi konversi `Domain.value`) supaya kedua prompt tidak drift.

**Apa yang dilakukan**
`verifikasi_cakupan_individu(atomic_intent, terdeteksi_awal) -> VerifikasiCakupanIndividuResult`.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_verifikasi_cakupan_individu.py` — 5/5 PASSED (3 pure-function + 2 real-LLM). Skenario titik-buta terkontrol (`terdeteksi_awal=False` sengaja diset untuk "Siapa staf tercepat bulan ini?") berhasil ditangkap Langkah 2 (`terdeteksi_tambahan=True`); guard anti-false-positive untuk kebutuhan genuinely agregat lolos (`terdeteksi_tambahan=False`).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `880d046` (kode), `8f8c91c` (test)

---

## Checkpoint 6 — Orkestrator + Observability

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 10 — `cakupan_individu.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`ROLE_STAFF_TIER` (frozenset 7 role, Keputusan 3) + `_domain_diizinkan_relevan()` (cek `Domain.FACILITY`/`Domain.HR` dengan `diizinkan=True`) sebagai dua pre-filter deterministik. `deteksi_constraint_atomic_intent()` — pre-filter dulu (return `terdeteksi=False` langsung tanpa panggilan LLM kalau gagal salah satu), baru Langkah 1+2, OR-merge, fail-closed (`terdeteksi=True`, alasan eksplisit) kalau KEDUA langkah gagal teknis. `deteksi_constraint_semua()` — span pembungkus agregat.

**Commit:** `3895fed`

### Task 11 — Test pre-filter (LLM TIDAK dipanggil)

**Kesesuaian dengan plan:** Sesuai plan — inilah pemeriksaan paling kritis di milestone ini.

**Apa yang dilakukan**
3 test dengan `monkeypatch` yang membuat `deteksi_cakupan_individu`/`verifikasi_cakupan_individu` melempar `AssertionError` kalau terpanggil (bukan mock hasil): (1) role non-Staff dengan domain facility diizinkan tetap `terdeteksi=False` tanpa panggilan LLM, (2) role Staff-tier tapi domain diizinkan tidak menyentuh facility/hr, (3) domain facility ADA di `domain_decisions` tapi `diizinkan=False` (ditolak M2.2) tetap dianggap tidak relevan.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_cakupan_individu.py` — 7/7 PASSED (4 validator CP2 + 3 pre-filter CP6, tidak ada `AssertionError` dari fungsi LLM manapun).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `497a00f`

---

## Checkpoint 7 — Verifikasi KK1-3 (Real LLM)

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 12 — Test KK1-3

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
KK1: "Siapa staf tercepat bulan ini?" + `Housekeeping Staff` -> `terdeteksi=True`, `alasan` terisi. KK2: kebutuhan SAMA + `Housekeeping Manager` -> `terdeteksi=False` lewat pre-filter (bukan kebetulan LLM). KK3: "Berapa jumlah kamar yang sedang out-of-order hari ini?" (domain facility relevan, lolos pre-filter) + `Housekeeping Staff` -> `terdeteksi=False` dibuktikan lewat LLM nyata (bukan pre-filter), membuktikan mekanisme tidak asal-menempel constraint ke seluruh kebutuhan domain facility/hr.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_cakupan_individu.py` — 10/10 PASSED (4 validator + 3 pre-filter + 3 KK, real LLM, 49.93s).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `cbf616a`

---

## Checkpoint 8 — Verifikasi Span Nyata

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 13 — Jalankan end-to-end + query Jaeger

**Kesesuaian dengan plan:** Sesuai plan. Docker Desktop tidak berjalan di awal checkpoint ini - dinyalakan, container `nirwana-jaeger`/`nirwana-otel-collector`/`nirwana-prometheus` (sudah ada dari M1.1-2.2, exited) di-start ulang lewat `docker compose up -d` di `infra/observability/`.

**Apa yang dilakukan**
Skrip verifikasi one-off (scratchpad, TIDAK di-commit) memanggil `setup_tracing()` + `deteksi_constraint_semua()` nyata untuk skenario KK1 ("Siapa staf tercepat bulan ini?", `Housekeeping Staff`, domain `facility` diizinkan), dibungkus span `invoke_agent`. Trace di-query langsung lewat Jaeger API (`curl http://localhost:16686/api/traces/<trace_id>`).

**Temuan**
Trace `b97a12808ac5d23186a61cb53fbd220a` berisi 5 span dengan hierarki benar: `invoke_agent` (root) -> `domain_gate.deteksi_constraint_semua` (`intent.count=1`, `constraint.terdeteksi_count=1`) -> `domain_gate.cakupan_individu.check` (`rbac.individual_scope_constraint=true`) -> 2 span `chat` (Langkah 1: model `qwen/qwen3-32b`, `domain_gate.deteksi_cakupan_individu.terdeteksi=true`, `prompt.id=domain_gate.deteksi_cakupan_individu`, `prompt.version=1`; Langkah 2: model `deepseek/deepseek-v4-pro`, `domain_gate.verifikasi_cakupan_individu.terdeteksi_tambahan=true`, `prompt.id=domain_gate.verifikasi_cakupan_individu`, `prompt.version=1`). Seluruh atribut sesuai kontrak observability dan desain Checkpoint 6.

**Error/Kegagalan (jika ada)**
Tidak ada (di luar Docker Desktop yang perlu dinyalakan manual sebelum verifikasi, bukan bug kode).

**Commit:** `3864cdc`

---

## Checkpoint 9 — Eval Milestone

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 14 — Skenario eval (10 skenario)

**Kesesuaian dengan plan:** Sesuai plan — dieksekusi satu per satu (`run_eval.py <ID>`) mengikuti mitigasi hang M2.1 Checkpoint 10, meski kali ini tidak ada hang yang terjadi.

**Apa yang dilakukan**
`rancangan.md` (10 skenario menutup dimensi belum tercakup `tests/`: 4 view baru, distractor 2 arah, generalisasi role-differentiation, titik-buta phrasing baru, retest over-triggering), `run_eval.py` (reuse `deteksi_constraint_atomic_intent()`/`verifikasi_cakupan_individu()` produksi langsung).

**Hasil Verifikasi**
Seluruh 10 skenario dijalankan nyata satu per satu — **10/10 LOLOS**, payload lengkap di `payloads/`.

**Commit:** `404affa`

### Task 15 — Jalankan nyata + `audit.md`

**Apa yang dilakukan**
Analisis per skenario di `audit.md`. Temuan utama: S05 (ranking individu tanpa kata kunci "staf") lolos — bukti prompt mengajarkan pemahaman makna, bukan cocok kata literal. S10 (distractor over-triggering mirip pola M2.1 keterbatasan #6) TIDAK over-trigger kali ini — dicatat sebagai observasi untuk pemantauan berkelanjutan (Checkpoint 10), BUKAN entri baru `docs/keterbatasan-diterima.md` (satu temuan positif belum cukup bukti pola, beda dari kriteria M2.1 yang butuh konsistensi berulang sebelum dicatat).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `f723f99`

---

## Checkpoint 10 — Reliability Testing (Promptfoo, Natif)

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 16 — Config Promptfoo

**Kesesuaian dengan plan:** Sesuai plan — dibangun natif di dalam milestone ini (Keputusan 11), bukan retrofit terpisah seperti pola M1.3-M2.1.

**Apa yang dilakukan**
`deteksi_cakupan_individu.promptfooconfig.yaml` + `verifikasi_cakupan_individu.promptfooconfig.yaml` (`prompt_reliability/domain_gate/`), reuse `provider.py` generik yang sudah ada, reuse seluruh 10 skenario `evals/2.3-.../rancangan.md` (RBAC-sensitif -> seluruh skenario, bukan subset, sesuai kontrak Bagian 5).

**Commit:** `822a0fc`

### Task 17 — Jalankan nyata + push ke `prompt_eval_runs`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu temuan operasional baru (dicatat di bawah).

**Temuan**
`npx promptfoo eval` awalnya gagal 10/10 dengan `ModuleNotFoundError: No module named 'opentelemetry.exporter.otlp.proto.grpc'` — Promptfoo menjalankan provider Python lewat interpreter Python SISTEM (`C:\Users\LENOVO\...\Python313\python.exe`), bukan virtualenv `uv` (`.venv/`) tempat dependency proyek benar-benar terpasang. Diperbaiki dengan set `PROMPTFOO_PYTHON` mengarah ke `.venv/Scripts/python.exe` sebelum menjalankan eval. Dicatat di `prompt_reliability/README.md` supaya tidak perlu didiagnosis ulang untuk config berikutnya.

**Apa yang dilakukan**
`npx promptfoo eval` dijalankan nyata untuk kedua config (dengan `PROMPTFOO_PYTHON` benar) — **20/20 lolos** (10 `deteksi_cakupan_individu` + 10 `verifikasi_cakupan_individu`), termasuk S10 (distractor over-triggering) tetap tidak over-trigger di KEDUA config, mengonfirmasi temuan `evals/2.3-.../audit.md`. Hasil di-push ke `prompt_eval_runs` lewat `push_results.py` (reuse, tanpa modifikasi) — 10+10=20 baris.

**Hasil Verifikasi**
Query Supabase langsung (`SELECT` `PromptEvalRunRow` filter `prompt_id` kedua prompt M2.3) — 20 baris terkonfirmasi, seluruhnya `verdict=lolos`.

**Error/Kegagalan (jika ada)**
Lihat Temuan di atas — resolved, bukan bug kode produksi (murni konfigurasi environment Promptfoo lokal).

**Commit:** `822a0fc` (config), `4f055e1` (README)

---

## Checkpoint 11 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 18 — `report.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Bagian 1-6 lengkap: ringkasan hasil, KK1-3 vs bukti nyata (tabel dengan Task pembuktinya), cara kerja + diagram Mermaid, satu deviasi administratif kecil (Checkpoint 3), keterbatasan (termasuk entri baru `docs/keterbatasan-diterima.md` #9), follow-up ke M2.4/M3.x.

**Commit:** `294bb85`

### Task 19 — Perbarui `CLAUDE.md`/`AGENT.md`

**Kesesuaian dengan plan:** Sesuai plan, dengan temuan tambahan: `AGENT.md` ternyata SUDAH tertinggal dari `CLAUDE.md` sejak SEBELUM sesi ini dimulai (pembaruan Manajemen Prompt Fase 1-2 tidak pernah diterapkan ke `AGENT.md`) — bukan hanya butuh update M2.3, tapi juga perlu disinkronkan ulang dari kondisi drift yang sudah ada.

**Apa yang dilakukan**
Struktur Repository (baris `docs/keterbatasan-diterima.md`, `milestones/`, `src/`, `src/prompts/`, `tests/`, `evals/`, `prompt_reliability/` — seluruhnya diperbarui dengan file/hasil M2.3), Status Saat Ini (entri M2.3 baru, urutan pengerjaan diarahkan ke M2.4, area terbuka dikurangi jadi hanya fallback PIC 6, jumlah keterbatasan 8→9, model routing M2.3 ditambahkan). `AGENT.md` ditulis ulang penuh menyalin `CLAUDE.md` (bukan cuma diff M2.3) untuk memperbaiki drift pra-sesi sekaligus.

**Hasil Verifikasi**
`diff CLAUDE.md AGENT.md` — IDENTICAL. Kedua file TIDAK di-track git (preseden M1.1), tidak ada commit untuk perubahan ini.

**Error/Kegagalan (jika ada)**
Tidak ada — drift `AGENT.md` yang ditemukan bukan kegagalan pekerjaan ini, melainkan utang dari inisiatif Manajemen Prompt sebelumnya yang tidak eksplisit menyebut pembaruan `AGENT.md`.

**Commit:** Tidak ada (file tidak di-track git). `report.md`/`decisions.md` M2.3 dan pembaruan `docs/keterbatasan-diterima.md` sudah dicommit; sisa working tree (`docs/CLAUDE.md` yang terhapus sejak sebelum sesi ini, dan 7 file `milestones/1.x-*/report.md` yang termodifikasi sebelum sesi ini) TIDAK disentuh — di luar cakupan M2.3.
