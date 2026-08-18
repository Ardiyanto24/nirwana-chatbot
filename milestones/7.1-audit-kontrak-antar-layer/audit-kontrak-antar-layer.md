# Audit Kontrak Antar-Layer — Milestone 7.1

Dokumen ini adalah rujukan tunggal kontrak aktual (dari kode nyata, bukan dokumen `rancangan-*.md`) untuk seluruh unit kerja di 9 layer (Milestone 1.2-4.5) yang dipakai Milestone 7.2-7.18. Setiap entri diverifikasi lewat pembacaan langsung source file (Checkpoint 2-6, Task 3/5/7/9/11) dan minimal satu panggilan nyata (Checkpoint 2-6, Task 4/6/8/10/11-12).

> Ringkasan Kontrak (tabel lintas-unit) dan section Penyimpangan Ditemukan disusun di Checkpoint 7 (Task 13), setelah seluruh PIC selesai diaudit.

---

## PIC 1 — Input Layer, Context Resolution, Decomposition (Milestone 1.2-1.7)

### M1.2 — Input Layer

- **File:** `src/layers/input_layer.py`, `src/main.py`, `src/schemas/turn_payload.py`.
- **Fungsi:** `validate_turn_payload(raw: dict) -> TurnPayload` (validasi Pydantic murni, span `input.validate`). `src/main.py::submit_turn(payload: dict) -> dict` — handler `POST /v1/turns`, memanggil `validate_turn_payload()` lalu **echo** `validated.model_dump()` — dikonfirmasi TIDAK memanggil layer lain mana pun.
- **Skema:** `TurnPayload {session_id: str, turn_index: int(>=1), role_title: str (divalidasi thd load_valid_roles()), employee_id: str, question: str, history: list[HistoryTurn]}`; `HistoryTurn {turn_index, question, answer}`. Validator: `history` wajib berisi tepat turn `1..turn_index-1`, tanpa gap/duplikat (model_validator `history_matches_turn_index`).
- **LLM call:** 0.
- **Bukti nyata:** Checkpoint 2, Task 4.
- **Penyimpangan:** tidak ada — perilaku echo-only sesuai docstring modul sendiri, konsisten `CLAUDE.md`.

### M1.3 — Pemetaan Ketergantungan Turn

- **File:** `src/layers/context_resolution/turn_dependency.py`, `src/schemas/turn_dependency.py`.
- **Fungsi:** `detect_turn_dependency(payload: TurnPayload) -> TurnDependencyResult`. Helper: `_call_llm(payload)` (dipakai ulang `evals/`), `_build_user_prompt(payload)`, `_parse_and_validate(raw_content, valid_turn_indices)`.
- **LLM call:** 1 — model `OPENROUTER_MODEL` (`deepseek/deepseek-v4-flash-0731`), `response_format=json_object`, `temperature=0`.
- **Verifikasi internal:** murni deterministik — bounds-check `referenced_turn_index` terhadap `valid_turn_indices` (himpunan `turn_index` di `payload.history`). Gagal parse/di luar bounds → dipaksa `is_dependent=False` (fallback aman, direkam sbg `dependency.forced_independent_reason` di span).
- **Skema:** `TurnDependencyResult {is_dependent: bool, referenced_turn_index: int|None}`. `session_id` sengaja tidak pernah diminta ke LLM — dilekatkan kode, bukan model (mencegah halusinasi ID).
- **Bukti nyata:** Checkpoint 2, Task 4.
- **Penyimpangan:** tidak ada.

### M1.4 — Rewrite Mandiri

- **File:** `src/layers/context_resolution/rewrite.py`, `src/schemas/rewrite.py`.
- **Fungsi:** `rewrite_to_standalone(payload: TurnPayload) -> RewriteResult`.
- **LLM call:** 1 — model `OPENROUTER_MODEL_REWRITE` (`qwen/qwen3-32b`), TANPA `response_format` (free text), `temperature=0`.
- **Fallback:** pada `APIError`/`response.choices` kosong/konten kosong → `RewriteResult(rewritten_question=payload.question)` (echo pertanyaan asli, TIDAK raise exception) — satu-satunya jalur fallback silent di seluruh PIC1.
- **Verifikasi internal:** `_detect_residual_reference()` — scan daftar tetap frasa penanda rujukan sisa (bukan kata tunggal ambigu seperti "itu"/"nya"). Murni flag observability (`rewrite.residual_reference_detected`), TIDAK memaksa fallback tambahan.
- **Skema:** `RewriteResult {rewritten_question: str}`.
- **Bukti nyata:** Checkpoint 2, Task 4.
- **Penyimpangan:** tidak ada — dikonfirmasi eksplisit TIDAK mengonsumsi `TurnDependencyResult` (M1.3), berjalan independen (keputusan desain M1.4, bukan gap).

### M1.5 — Tarik Session Memory

- **File:** `src/layers/context_resolution/session_memory.py`, `src/schemas/session_memory.py`.
- **Fungsi:** `retrieve_session_memory(session_id: str, turn_index: int) -> list[SessionMemoryPackage]` (span `memory.retrieve`, list kosong kalau tidak ada data — TIDAK exception). `store_session_memory(package: SessionMemoryPackage) -> None` (span `memory.store`; kegagalan DB di-set `error.type=gagal_teknis` pada span LALU **di-raise ulang apa adanya** — raise-on-failure dipertahankan, bukan silent).
- **LLM call:** 0.
- **Skema:** `SessionMemoryPackage {atomic_intent_id, session_id, turn_index, teks_kebutuhan, label_bentuk_jawaban: LabelBentukJawaban(enum 5 nilai), nilai_hasil: dict, catatan_interpretasi: list[str], status: StatusEksekusi(enum 5 nilai), sumber: str}` — kontrak bersama PIC1+PIC4 (dipakai ulang, TIDAK didefinisikan ulang di layer lain).
- **Bukti nyata:** Checkpoint 2, Task 4.
- **Penyimpangan:** tidak ada — `store_session_memory()` didokumentasikan eksplisit sebagai utilitas pendukung (peran resmi M1.5 hanya "retrieve"); pemanggil produksi sisi store adalah M4.3 (datang belakangan, bukan gap).

### M1.6 — Decomposition (Klasifikasi → Pemecahan → Verifikasi, dengan retry)

- **File:** `src/layers/decomposition/{decompose,klasifikasi,pemecahan,verifikasi}.py`, `src/schemas/decomposition.py`.
- **Orkestrator:** `decompose.py::decompose_question(question: str) -> DecompositionResult`. **Dikonfirmasi langsung dari kode** (`_MAX_ATTEMPTS = 3`, loop `while True` dengan `attempt` mulai 1, break kalau `verifikasi.valid` atau `attempt >= 3`): `klasifikasi_kebutuhan()` dipanggil **sekali** di luar loop, lalu `pecah_atomik()` + `verifikasi_pemecahan()` diulang hingga 3 kali total (1 percobaan awal + maks 2 retry, feedback = `verifikasi.alasan` percobaan sebelumnya).
- **⚠️ PENYIMPANGAN DITEMUKAN:** dokumen `rancangan-orkestrasi-api.md` (M7.2) membingkai unit ini sebagai "3 pemanggilan LLM berurutan" — framing itu benar untuk **jumlah mekanisme berbeda** (Klasifikasi/Pemecahan/Verifikasi = 3), TAPI jumlah **panggilan LLM aktual** per eksekusi `decompose_question()` adalah **1 + (hingga 3 × 2) = hingga 7 panggilan** dalam kasus terburuk (retry penuh). M7.2 (Level 1, penyambungan internal Decomposition) wajib memperhitungkan retry loop ini, bukan mengasumsikan pipa linear 3-langkah sederhana.
- **Sub-unit:**
  - `klasifikasi.py::klasifikasi_kebutuhan(question: str) -> KlasifikasiKebutuhan` — 1 LLM call, model `OPENROUTER_MODEL_DECOMPOSITION` (`qwen/qwen3-32b`), output plain-text di-parse ke enum; fallback API-error/unparseable = `MAJEMUK_BERGANTUNG`.
  - `pemecahan.py::pecah_atomik(question, klasifikasi, feedback=None) -> PemecahanResult` — 1 LLM call, model sama, `response_format=json_object`. `atomic_intent_id` di-generate UUID4 oleh kode setelah respons (LLM tidak pernah diminta ID).
  - `verifikasi.py::verifikasi_pemecahan(question, hasil) -> VerifikasiResult` — 1 LLM call, model `OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI` (`deepseek/deepseek-v4-pro`, `reasoning: high`), `response_format=json_object`. Verifier independen (model beda dari Klasifikasi/Pemecahan).
- **Skema:** `AtomicIntent {atomic_intent_id, teks_kebutuhan, label_bentuk_jawaban: LabelBentukJawaban (reuse dari session_memory.py), relasi: RelasiKebutuhan(independen|bergantung), bergantung_pada: list[str]|None}` — validator: `bergantung_pada` wajib non-kosong iff `relasi=bergantung`. `DecompositionResult {klasifikasi, atomic_intents, verifikasi_valid, verifikasi_alasan, retry_count}`. Kalau percobaan ke-3 masih invalid, `verifikasi_valid=False` dikembalikan apa adanya (TIDAK disamarkan jadi True).
- **Bukti nyata:** Checkpoint 2, Task 4.

### M1.7 — Pencocokan Atomic Intent

- **File:** `src/layers/context_resolution/matching.py`, `src/schemas/matching.py`.
- **Fungsi:** `match_atomic_intents(atomic_intents, candidates) -> list[AtomicIntentMatch]` — filter `candidates` ke `status==BERHASIL` dulu; kalau hasil filter kosong, jalur pintas deterministik (semua `PERLU_EKSEKUSI`, **0 LLM call**); kalau tidak, **1 LLM call per atomic_intent** (tidak dibatch). `archive_matched_packages(matches, session_id, turn_index) -> None` — re-simpan paket yang `status==SELESAI` sbg baris arsip baru via `store_session_memory()` (M1.5). `match_and_archive(...)` — orkestrator tipis menggabungkan keduanya; **dikonfirmasi langsung dari docstring kode**: "titik masuk tunggal yang nanti dipanggil pipeline penuh (`src/main.py`, **belum dirangkai**)".
- **Temuan tambahan (dari pembacaan langsung, lebih detail dari ringkasan awal):** `archive_matched_packages()` memakai helper `_sumber_arsip(paket_lama)` yang menjaga **rantai turn asal** lintas pengarsipan berulang — kalau paket lama `sumber=="eksekusi_baru"`, arsip baru diberi `sumber=f"session_memory (turn {paket_lama.turn_index})"`; kalau paket lama SUDAH berupa arsip (`sumber` sudah berbentuk `"session_memory (turn N)"`, kasus rantai transitif), nilainya dipertahankan UTUH TANPA PERUBAHAN — N tetap merujuk turn PALING ASAL, bukan turn arsip perantara. Detail ini penting untuk M7.9 (Sambungan 4, titik pertemuan Decomposition+Tarik Memory→Pencocokan) karena caller wajib paham `candidates` diterima sebagai parameter polos (`match_atomic_intents` TIDAK memanggil `retrieve_session_memory()` sendiri — komposisi longgar, caller yang menyediakan).
- **LLM call:** 1 per atomic_intent (kondisional), model `OPENROUTER_MODEL_MATCHING` (`qwen/qwen3-32b`), `response_format=json_object`. TANPA verifier independen kedua (beda dari pola M1.6). Fallback pada kegagalan apa pun (API error/parse error/dangling index) = `PERLU_EKSEKUSI`.
- **Skema:** `AtomicIntentMatch {atomic_intent, status: MatchStatus(selesai|perlu_eksekusi), paket: SessionMemoryPackage|None}` — validator: `paket` wajib ada iff `status==selesai`.
- **Bukti nyata:** Checkpoint 2, Task 4.
- **Penyimpangan:** tidak ada bug — hanya konfirmasi eksplisit bahwa `match_and_archive()` belum dirangkai ke `src/main.py` (sesuai ekspektasi status project, bukan gap baru).

---

## PIC 2 — Domain Gate, Verification Gate (Milestone 2.1-2.4)

### M2.1 — Domain Gate: Identifikasi Domain + Verifikasi Titik Buta

- **File:** `src/layers/domain_gate/{domain_gate,identifikasi,verifikasi_titik_buta}.py`, `src/schemas/domain_gate.py`.
- **Orkestrator:** `domain_gate.py::identifikasi_domain_atomic_intent(atomic_intent) -> AtomicIntentDomains` — Langkah 2 (verifikasi titik buta) **TIDAK dipanggil** kalau Langkah 1 gagal total (tidak ada `domain_awal` untuk diverifikasi) → langsung `status=GAGAL_TEKNIS`, `domains=[]`. `identifikasi_domain_semua(matches: list[AtomicIntentMatch]) -> list[AtomicIntentDomains]` — filter ke `status==PERLU_EKSEKUSI` (hasil M1.7) saja, proses satu per satu (bukan batch).
- **Penggabungan hasil:** `domains_gabungan = list(dict.fromkeys(hasil_awal.domains + hasil_verifikasi.domain_tambahan))` — **union aditif** (dedup via dict, urutan dipertahankan), BUKAN replace. `status = SEBAGIAN` kalau `hasil_verifikasi.gagal`, else `BERHASIL`.
- **LLM call:** 2 berurutan — `identifikasi.py::identifikasi_domain()` (model `OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI`, qwen3-32b) lalu `verifikasi_titik_buta.py::verifikasi_titik_buta()` (model `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA`, deepseek-v4-pro reasoning=high) — dikonfirmasi tepat 2 (tidak ada retry loop di sini, beda dari M1.6).
- **Skema:** `Domain` (enum 10 nilai); `AtomicIntentDomains {atomic_intent, domains: list[Domain], status}` — validator: `GAGAL_TEKNIS ⟺ domains kosong`.
- **Bukti nyata:** Checkpoint 3, Task 6.
- **Penyimpangan:** tidak ada.

### M2.2 — Pemeriksaan Otorisasi

- **File:** `src/layers/domain_gate/otorisasi.py`, `src/schemas/authorization.py`.
- **Fungsi:** `periksa_domain(domain, role_title) -> DomainAuthorization` (murni, tanpa span). `periksa_otorisasi_atomic_intent(atomic_intent_domains, role_title) -> AtomicIntentAuthorization` — span `authorization.check` PER domain (atribut `rbac.domain`/`rbac.decision`, `error.type=ditolak_otorisasi` bila ditolak). `periksa_otorisasi_semua(atomic_intent_domains_list, role_title) -> list[AtomicIntentAuthorization]` — melewati entri `status==GAGAL_TEKNIS` (M2.1).
- **LLM call:** 0 — murni lookup `role_permissions` (`load_role_permissions()`), ruang kesalahan tertutup (20 role × 10 domain).
- **Skema:** `DomainAuthorization {domain, diizinkan: bool, alasan: str|None}` — validator: `alasan` wajib ada iff `diizinkan=False`. Output granular PER domain (bukan satu keputusan per atomic intent).
- **Bukti nyata:** Checkpoint 3, Task 6.
- **Penyimpangan:** tidak ada.

### M2.3 — Deteksi Cakupan Individu

- **File:** `src/layers/domain_gate/{cakupan_individu,deteksi_cakupan_individu,verifikasi_cakupan_individu}.py`, `src/schemas/cakupan_individu.py`.
- **Orkestrator:** `cakupan_individu.py::deteksi_constraint_atomic_intent(atomic_intent_authorization, role_title) -> AtomicIntentConstraint`. **Dua pre-filter deterministik SEBELUM panggilan LLM apa pun** (dikonfirmasi langsung dari kode): (1) `role_title not in ROLE_STAFF_TIER` (frozenset 7 role persis: Front Office/F&B/Housekeeping/Maintenance/Spa & Event/HR/Finance Staff) → `terdeteksi=False`, 0 LLM call; (2) `_domain_diizinkan_relevan()` — tidak ada domain `{FACILITY, HR}` yang diizinkan → `terdeteksi=False`, 0 LLM call. `deteksi_constraint_semua(...) -> list[AtomicIntentConstraint]` — proses satu per satu.
- **LLM call:** 0 (kalau salah satu pre-filter gagal) atau 2 berurutan (kalau lolos keduanya) — `deteksi_cakupan_individu.py` (model `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI`, qwen3-32b) lalu `verifikasi_cakupan_individu.py` (model `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI`, deepseek-v4-pro reasoning=high).
- **Penggabungan hasil:** union aditif (OR-merge) — `terdeteksi = hasil_awal.terdeteksi or hasil_verifikasi.terdeteksi_tambahan`. **Fail-closed**: kalau KEDUA langkah LLM gagal teknis, `terdeteksi=True` dipaksa (`forced_fallback_reason="gagal_teknis_kedua_langkah_fail_closed"`) — arah fail-safe berlawanan dari M1.7 (yang fail ke `PERLU_EKSEKUSI`, bukan fail ke "constraint terdeteksi").
- **Skema:** `ConstraintCakupanIndividu {terdeteksi: bool, alasan: str|None}`; `AtomicIntentConstraint {atomic_intent, domain_decisions: list[DomainAuthorization], constraint}`.
- **Bukti nyata:** Checkpoint 3, Task 6.
- **Penyimpangan:** tidak ada.

### M2.4 — Verification Gate

- **File:** `src/layers/verification_gate/verifikasi_gate.py`, `src/schemas/verification_gate.py`.
- **Fungsi:** `verifikasi_gate(request: QueryEngineRequest, constraint, employee_id, view_name_tervalidasi_retriever) -> HasilVerifikasiGate` — 4 cek berlapis, **early-exit tolak** kalau Cek 1 atau Cek 2 gagal (Cek 3-4 tidak dijalankan), lanjut Cek 3→4 kalau keduanya lolos.
  - Cek 1 `verifikasi_bentuk_request_statis()`: `view_name` terdaftar di `DAFTAR_VIEW_PER_DOMAIN[domain]`; `params["limit"]` (kalau ada) ≤ `LIMIT_MAKSIMUM=1000`.
  - Cek 2 `verifikasi_kepatuhan_sumber()`: `request.view_name` == `view_name_tervalidasi_retriever` (parameter, BUKAN query M3.x langsung).
  - Cek 3 `tegakkan_constraint_cakupan_individu()`: kalau `constraint.terdeteksi=True` dan `params["employee_id"] != employee_id` → **timpa paksa** (bukan tolak), kembalikan `(request_terkoreksi, terkoreksi=True)`.
  - Cek 4 `verifikasi_kelengkapan_penegakan()`: re-cek Cek 3 benar-benar diterapkan (defensif, menangkap bug internal Cek 3 sendiri).
- **LLM call:** 0 — sepenuhnya deterministik, ruang kesalahan tertutup. Span `verification_gate.check` per cek (`verification.check_name`, `error.type=gagal_teknis` bila gagal) di dalam span pembungkus `verification_gate.verifikasi_gate`.
- **Skema:** `QueryEngineRequest {domain: Domain, view_name: str, params: dict}`; `HasilVerifikasiGate {request_final: QueryEngineRequest|None, lolos: bool, terkoreksi: bool, alasan_penolakan: str|None}` — validator dua arah: `lolos ⟺ request_final ada, alasan_penolakan tidak ada`.
- **Bukti nyata:** Checkpoint 3, Task 6.
- **Penyimpangan:** tidak ada — konvensi `employee_id` di `params` masih PROVISIONAL (dicatat `decisions.md` M2.4 Keputusan 1, konsisten `docs/keputusan-tertunda.md`), bukan penyimpangan baru dari audit ini.

---

## PIC 3 — Retriever, Query Engine (Milestone 3.1-3.5)

### M3.1-3.3 — Retriever (Pengumpulan Kandidat → Kecocokan Makna → Kecukupan Struktural)

- **File:** `src/layers/retriever/{retriever,pencarian_bm25,pencarian_embedding,kecocokan_makna,kecukupan_struktural,definisi_view,grain_view}.py`, `src/schemas/retriever.py`.
- **Orkestrator penutup pipeline (produksi):** `kecukupan_struktural.py::proses_retrieval_atomic_intent(atomic_intent, domain_diizinkan) -> HasilKecukupanStruktural` — **dikonfirmasi langsung dari kode**: membuka SATU span pembungkus `retriever.cari_kandidat_view` (nama SAMA dengan wrapper standalone M3.1) yang membungkus `_kumpulkan_kandidat()` (M3.1, tanpa span sendiri) → `nilai_kecocokan_makna_atomic_intent()` (M3.2, span `chat` anak) → `evaluasi_kecukupan_struktural_atomic_intent()` (M3.3, span `chat` anak kondisional) sekaligus, lalu mengisi atribut `retrieval.selected_view` sebelum span ditutup. `cari_kandidat_view()` (wrapper standalone M3.1, dipakai test/pemanggil terisolasi) TIDAK berubah perilaku — refactor Checkpoint 9 M3.3 murni ekstraksi logic ke `_kumpulkan_kandidat()`, dikonfirmasi lewat regresi test tanpa perubahan assertion.
- **M3.1 (`_kumpulkan_kandidat`):** `cari_bm25(teks_kebutuhan, domain_diizinkan) -> tuple[list[KandidatView], bool]` jalur utama (**0 LLM**); `cari_embedding(teks_kebutuhan, domain_diizinkan, model)` fallback **kondisional** (hanya kalau BM25 `perlu_fallback=True`) — **1 panggilan embedding** (model `OPENROUTER_MODEL_RETRIEVER_EMBEDDING` = `openai/text-embedding-3-small`). Union BM25+embedding via `_union_kandidat()`: dedup by `view_name`, BM25 diprioritaskan kalau sama, TIDAK diurutkan ulang lintas skor gabungan (skala BM25 vs cosine similarity tidak sepadan).
- **M3.2 (`kecocokan_makna.py::nilai_kecocokan_makna_atomic_intent`):** jalur pintas kandidat kosong = `BERHASIL` + `kecocokan=[]`, **0 LLM**. Kalau ada kandidat: **2 LLM call berurutan** — Langkah 1 generate (model `OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE`, qwen3-32b, batch seluruh kandidat sekaligus) → Langkah 2 verifikasi (model `OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI`, deepseek-v4-pro reasoning=high) — hasil Langkah 2 **MENGGANTIKAN** Langkah 1 sepenuhnya (koreksi dua arah, BUKAN union aditif seperti M2.1/M2.3). Fallback: Langkah 1 gagal total → `GAGAL_TEKNIS`+kosong; Langkah 2 gagal (Langkah 1 sukses) → `SEBAGIAN`+hasil Langkah 1 dipertahankan utuh. Jaminan struktural: setiap kandidat input WAJIB muncul di output (tidak pernah di-drop diam-diam), default aman `SEBAGIAN` untuk anomali.
- **M3.3 (`kecukupan_struktural.py::evaluasi_kecukupan_struktural_atomic_intent`):** filter kandidat label `ditemukan`/`sebagian` (exclude `tidak_ditemukan`); rule table deterministik `_evaluasi_deterministik()` per kandidat (**0 LLM** untuk kasus pasti) — `nilai_tunggal` selalu cukup; `tren` bergantung `punya_time_series`; `perbandingan`/`peringkat`/`komposisi` bergantung `punya_dimensi_pembanding`; label tak dikenal → fail-safe `tidak_pasti`. Kandidat `tidak_pasti` dikumpulkan lalu **1 panggilan LLM batch konservatif** (model `OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL`, qwen3-32b) — SATU panggilan per kebutuhan atomik untuk SELURUH kandidat ambigu sekaligus, bukan generate-verify penuh. Tie-break `_pilih_view_name_final()`: prioritaskan label M3.2 `ditemukan` atas `sebagian`, lalu skor `KandidatView` (M3.1) tertinggi.
- **Skema:** `KandidatView {view_name, domain, skor, sumber: SumberPencarian}`; `HasilPencarianKandidat {atomic_intent, domain_diizinkan, kandidat, fallback_terpicu, status}`; `HasilKecocokanMakna {atomic_intent, kecocokan: list[KecocokanKandidat], status}`; `HasilKecukupanStruktural {atomic_intent, kecukupan: list[KecukupanKandidat], view_name_final: str|None, status}` — `status` SELALU `BERHASIL` (mekanisme M3.3 tidak pernah gagal teknis di level kebutuhan-atomik, kegagalan LLM fallback ditangani via default aman internal, bukan propagasi status).
- **LLM call total per kebutuhan atomik (kasus terburuk):** M3.1 1 (embedding, kondisional) + M3.2 2 (generate+verifikasi) + M3.3 1 (fallback batch, kondisional) = **hingga 4 panggilan**.
- **Bukti nyata:** Checkpoint 4, Task 8.
- **Penyimpangan:** tidak ada bug — konfirmasi bahwa `proses_retrieval_atomic_intent()` (bukan `cari_kandidat_view()` standalone) adalah entry point produksi yang wajib dipakai M7.11/M7.12 (Sambungan 6-7), penting untuk Level 2 supaya tidak salah memanggil wrapper standalone yang span-nya tidak membungkus M3.2/M3.3.

### M3.4-3.5 — Query Engine (Penyusunan Request → Verifikasi Bentuk Request)

- **File:** `src/layers/query_engine/{penyusunan_request,verifikasi_bentuk_request,param_whitelist}.py`, `src/schemas/query_engine.py`.
- **M3.4 (`penyusunan_request.py::susun_request_atomic_intent`):** `(atomic_intent, view_name, tanggal_referensi: date|None=None, feedback: str|None=None) -> HasilPenyusunanRequest` — **1 LLM call** (model `OPENROUTER_MODEL_PENYUSUNAN_REQUEST`, qwen3-32b), tanpa retry internal, tanpa verifier independen (M3.5 terpisah). `domain` **diturunkan kode** via `view_ke_domain()[view_name]`, TIDAK diminta LLM. `params` disaring deterministik pasca-LLM terhadap `PARAM_WHITELIST_VIEW[view_name]` (exact key match); `employee_id`/`role_title`/`domain`/`view_name` di-strip paksa dari `params` kapan pun muncul di respons LLM. **Parameter `feedback` (ditambahkan M4.2)** dipakai saat dipanggil ulang dari orkestrator Execution (`klasifikasi_respons.py`) pada jalur revisi `400` — fungsi ini SENDIRI tetap tanpa retry internal, loop revisi sepenuhnya tanggung jawab pemanggil.
- **M3.5 (`verifikasi_bentuk_request.py::verifikasi_bentuk_request_atomic_intent`):** hybrid — Kriteria 1 `_view_name_sesuai_retriever()` pre-check DETERMINISTIK (perbandingan string), short-circuit TANPA membuka span `chat`/memanggil LLM kalau gagal. Kriteria 2 (kecukupan semantik `params` vs `label_bentuk_jawaban`) **1 LLM call** (model `OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST`, deepseek-v4-pro reasoning=high), tanpa retry, tanpa verifier kedua. `request` pada output SELALU utuh (tidak pernah di-null-kan) — beda `verifikasi_gate()` (M2.4) yang menolak dengan me-null-kan; M3.5 mendiagnosis, bukan merevisi/menolak.
- **Redundansi terdokumentasi:** `_view_name_sesuai_retriever()` (M3.5) **sengaja** duplikat `verifikasi_kepatuhan_sumber()` (M2.4) — perbandingan string yang sama, di lapisan pipeline berbeda; kedua docstring saling merujuk eksplisit, bukan dead code.
- **LLM call total (kasus Kriteria 1 lolos):** M3.4 1 + M3.5 1 = **2 berurutan**, sesuai framing dokumen orkestrasi.
- **Skema:** `HasilPenyusunanRequest {atomic_intent, request: QueryEngineRequest|None, status}`; `HasilVerifikasiBentukRequest {atomic_intent, request: QueryEngineRequest (selalu ada), status, lolos: bool|None, alasan: str|None}`.
- **Bukti nyata:** Checkpoint 4, Task 8.
- **Penyimpangan:** tidak ada.

---

## PIC 4 — Execution, Interpretation (Milestone 4.1-4.5)

### M4.1 — Membangun Pemanggilan chatbot_api

- **File:** `src/layers/execution/pemanggilan_chatbot_api.py`, `src/schemas/execution.py`.
- **Fungsi:** `_panggil_chatbot_api_raw(request, role_title, employee_id) -> HasilPemanggilanChatbotAPI` (logic murni, TANPA span sendiri — **dikonfirmasi langsung dari kode ini yang dipanggil M4.2**, bukan wrapper publik). `panggil_chatbot_api(...)` — wrapper standalone tipis di atas raw (membuka span `execute_tool` sendiri, perilaku IDENTIK, dipakai untuk pemanggilan berdiri sendiri mis. test). `panggil_meta_chatbot_api(request, role_title, employee_id) -> HasilMetaChatbotAPI` — endpoint `_meta` tim database, SATU percobaan tanpa retry, non-200/kegagalan transport apa pun diperlakukan seragam sebagai "tidak diketahui" (TIDAK PERNAH crash).
- **LLM call:** 0 — murni HTTP via `httpx.Client`. URL dibentuk `{base_url}/chatbot/{domain}/{slug}` (slug dari `VIEW_NAME_KE_SLUG_CHATBOT_API`); `query_params` = `request.params` (nilai `None` di-filter) + `role_title`+`employee_id` disisipkan eksplisit.
- **Skema:** `HasilPemanggilanChatbotAPI {status_code: int|None, body: Any, kegagalan_transport: str|None}` (validator XOR: `status_code` ada ⟺ `kegagalan_transport` tidak ada). `HasilMetaChatbotAPI {status_code, data_quality_status, last_refreshed_at, kegagalan_transport}`.
- **Bukti nyata:** dikutip dari Milestone 4.1 Checkpoint 5 (2026-08-17, `milestones/4.1-membangun-pemanggilan-chatbot-api/report.md`) — KK1 (200) `role_title="Front Office Staff"`, `v_lookup_daily_occupancy` → data 8-kolom nyata, `trace_id=7f79c0a8fe748539cf184cac940baace`; KK2 (403) role sama vs domain `fnb` → `{"detail": "role ... not permitted for domain 'fnb'"}`, `trace_id=2a3c8338023749851de6017592459739`. **Fresh call Checkpoint 6 GAGAL** (`chatbot_api` tidak reachable hari ini, lihat entri M4.2 di bawah).
  - **⚠️ Koreksi temuan (`git log` dicek ulang, klaim awal keliru):** file `pemanggilan_chatbot_api.py` **DIUBAH DUA KALI** setelah commit awal M4.1 (`6e2d71f`, 2026-08-17 19:11) — refactor pemisahan `_panggil_chatbot_api_raw()` (`bc9c855`, 2026-08-17 21:29, docstring-nya sendiri menyatakan "regresi test dijalankan penuh tanpa perubahan assertion", jadi bukti KK1/KK2 di atas tetap dianggap sah untuk `_panggil_chatbot_api_raw()`), dan penambahan `panggil_meta_chatbot_api()` (`3329ff9`, **2026-08-18**, sehari setelah tanggal laporan M4.1). **Konsekuensi:** `panggil_meta_chatbot_api()` — fungsi yang sekarang jadi bagian jalur `200` M4.2 (lihat entri M4.2 di bawah) — **belum pernah dibuktikan panggilan nyata sama sekali**, terlepas dari status M4.1. Ini bagian dari celah yang sama dicatat `docs/keterbatasan-diterima.md` #13 (bukan celah terpisah, karena `panggil_meta_chatbot_api()` hanya dipanggil dari `eksekusi_atomic_intent()` produksi).
  - Bukti KK1/KK2 di atas HANYA membuktikan 2 dari 67 view + jalur 200/403 untuk `_panggil_chatbot_api_raw()`/`panggil_chatbot_api()` (bukan 400/404/5xx/timeout, bukan `panggil_meta_chatbot_api()`).
- **Penyimpangan:** caveat "2/67 view" sudah tercatat di `milestones/4.1-.../report.md` baris 72 (bukan baru); **celah `panggil_meta_chatbot_api()` tanpa bukti nyata ADALAH temuan baru audit ini** (ditemukan lewat pengecekan `git log` yang semula diabaikan, dikoreksi di tempat sebelum menyesatkan konsolidasi Checkpoint 7).

### M4.2 — Klasifikasi Respons & Penanganan Kegagalan

- **File:** `src/layers/execution/klasifikasi_respons.py`.
- **Fungsi:** `eksekusi_atomic_intent(atomic_intent, view_name, request, constraint, role_title, employee_id) -> HasilEksekusiAtomicIntent` — orkestrator penuh, SATU span `execute_tool` (tracer `execution.klasifikasi_respons`) membungkus SATU ATAU LEBIH percobaan (retry infra + revisi 400) sekaligus. Memanggil `_panggil_chatbot_api_raw()` (BUKAN `panggil_chatbot_api()` publik) langsung, dikonfirmasi dari import statement.
- **Pemetaan status (dikonfirmasi langsung dari kode, urutan pengecekan persis):**
  1. Kegagalan infra (`5xx`/timeout/connection_error) → retry sampai `EXECUTION_MAX_RETRY_INFRA`, lalu `GAGAL_TEKNIS`.
  2. `200` → panggil `panggil_meta_chatbot_api()` SEKALI (tanpa retry) → `_tentukan_kualitas_data()`: `flagged` ATAU stale (`_data_basi()` vs `EXECUTION_DATA_STALENESS_THRESHOLD_JAM`) → `SEBAGIAN`; `null`/gagal `_meta` → TETAP `BERHASIL`.
  3. `403`/`404` → `GAGAL_TEKNIS` + `bug_prioritas_tinggi=True`, **eskalasi langsung TANPA retry sama sekali**.
  4. `400` → **⚠️ CROSS-LAYER CALL-BACK dikonfirmasi langsung dari kode**: `_revisi_request()` memanggil ULANG `susun_request_atomic_intent()` (M3.4, dengan `feedback` hasil `_ekstrak_alasan_400()`) → `verifikasi_bentuk_request_atomic_intent()` (M3.5) → `verifikasi_gate()` (M2.4) berurutan, APA ADANYA tanpa modifikasi. Gagal di titik mana pun → `GAGAL_TEKNIS` dengan alasan spesifik (`revisi_gagal_susun`/`revisi_gagal_verifikasi_bentuk`/`revisi_gagal_verification_gate`). Maks `EXECUTION_MAX_REVISI - 1` retry; tiap percobaan revisi py jatah retry infra sendiri (independen).
  5. Status lain (mis. `401`) → `GAGAL_TEKNIS` fallback aman, `status_tak_dikenal_{code}` — bukan bagian ruang kesalahan tertutup KK sumber, TIDAK PERNAH crash/disamarkan berhasil.
- **LLM call langsung di modul ini:** 0. **LLM call tidak langsung (jalur revisi 400):** hingga `(EXECUTION_MAX_REVISI - 1) × 2` (M3.4 + M3.5 per percobaan revisi) — relevan untuk M7.14 (Sambungan 9, Level 2) yang menyambungkan unit ini, wajib memperhitungkan call-back ini sebagai bagian span `execute_tool`, bukan span `chat` terpisah tanpa konteks.
- **Skema:** `HasilEksekusiAtomicIntent {atomic_intent, status, nilai_hasil, bug_prioritas_tinggi, retry_count_infra, revisi_count, kegagalan_alasan, data_quality_status, last_refreshed_at}`.
- **Bukti nyata:** ⚠️ **CELAH DITEMUKAN — TIDAK ADA bukti nyata sama sekali.** Dikonfirmasi: seluruh test (`tests/layers/execution/test_klasifikasi_respons.py` dan file terkait, 200+ test Checkpoint 1-6 + revisit `_meta`) memakai `monkeypatch` untuk `_panggil_chatbot_api_raw()`/`panggil_meta_chatbot_api()` — TIDAK ADA satu pun test/eval yang memanggil `chatbot_api` sungguhan lewat `eksekusi_atomic_intent()`, bahkan untuk jalur `200` sekalipun. Percobaan Checkpoint 6 (2026-08-18) menutup celah ini GAGAL — `chatbot_api` tidak reachable (`ConnectError`, lihat `logs.md`). **Didokumentasikan sebagai keterbatasan diterima baru** (`docs/keterbatasan-diterima.md` #13), sesuai Keputusan 7 `decisions.md` milestone ini — trigger revisit: begitu `chatbot_api` reachable, sebelum Milestone 7.14 dimulai.
- **Penyimpangan:** gap bukti nyata di atas ADALAH temuan utama audit ini untuk unit ini — dicatat eksplisit, tidak didiamkan, sesuai KK2 sumber M7.1.

### M4.3 — Penyimpanan Paket ke Session Memory

- **File:** `src/layers/execution/penyimpanan_paket.py` (reuse skema `SessionMemoryPackage` dari M1.5, tanpa file skema baru).
- **Fungsi:** `susun_dan_simpan_paket(atomic_intent, session_id, turn_index, status, view_name=None, nilai_hasil=None, data_quality_status=None, last_refreshed_at=None) -> SessionMemoryPackage` — `status`/`nilai_hasil` diterima sebagai parameter eksplisit (bukan langsung mengonsumsi `HasilEksekusiAtomicIntent` M4.2), forced diagram arsitektur §5.
- **LLM call:** 0 — murni deterministik: `_bungkus_nilai_hasil()` (list-of-row → `{"rows": [...]}`), `_catatan_interpretasi_untuk_hasil()` (dict lookup `CATATAN_NULLABLE_BERMAKNA`, HANYA kolom yang benar-benar `None` DAN terdaftar katalog), `_catatan_kualitas_data()` (Revisit 2026-08-17: nada teks beda untuk `SEBAGIAN` terkonfirmasi vs `BERHASIL` kualitas-tidak-diketahui). `sumber` SELALU `"eksekusi_baru"` (hardcode). Memanggil `store_session_memory()` (M1.5) — exception diteruskan apa adanya, TIDAK ditelan.
- **Bukti nyata:** Checkpoint 5, Task 10.
- **Penyimpangan:** tidak ada — Revisit `_catatan_kualitas_data()` (2026-08-17) sudah terdokumentasi eksplisit di kode+`decisions.md` M4.3 Keputusan 9, dikonfirmasi ulang di sini, bukan temuan baru.

### M4.4 — Penyusunan Narasi

- **File:** `src/layers/interpretation/narasi.py`, `src/schemas/interpretation.py`.
- **Fungsi:** `susun_narasi(atomic_intents, packages, session_id, turn_index) -> HasilNarasi`.
- **LLM call:** 1 — model `OPENROUTER_MODEL_NARASI` (qwen3-32b), TANPA `response_format` (output teks bebas — SATU-SATUNYA layer LLM di seluruh project dengan output non-JSON), TANPA retry/parameter `feedback` internal.
- **Fallback:** **TIDAK ADA** — `APIError` ditandai `error.type=gagal_teknis` pada span LALU **di-raise ulang** (satu-satunya pemanggilan LLM di seluruh codebase tanpa jalur fallback aman).
- **Kontrak input ketat:** `_build_user_prompt()` menegakkan 1:1 `atomic_intent`↔`package` (by `atomic_intent_id`) — melempar `ValueError` eksplisit (bukan diam-diam skip) kalau ada `atomic_intent` tanpa `package` pasangan.
- **⚠️ PENYIMPANGAN DITEMUKAN (dokumentasi basi, bukan bug fungsional):** docstring modul baris 6 **masih tertulis** "Dipisah dari verifikasinya (Milestone 4.5, **belum dibangun**)" — **dikonfirmasi langsung dari kode saat ini**, M4.5 (`verifikasi_kesetiaan.py`) SUDAH dibangun dan selesai (lihat entri M4.5 di bawah). Tidak berdampak fungsional (tidak ada logic yang bergantung pada docstring), tapi berisiko menyesatkan pembaca kode berikutnya (termasuk milestone 7.5 yang menyambungkan M4.4→M4.5) kalau tidak dikoreksi.
- **Skema:** `HasilNarasi {narasi: str}`.
- **Bukti nyata:** Checkpoint 5, Task 10.

### M4.5 — Verifikasi Kesetiaan Data + Visualisasi

- **File:** `src/layers/interpretation/{verifikasi_kesetiaan,visualisasi}.py`.
- **Fungsi verifikasi:** `verifikasi_kesetiaan_narasi(narasi, atomic_intents, packages, session_id, turn_index) -> HasilVerifikasiNarasi` — **1 LLM call**, model `OPENROUTER_MODEL_VERIFIKASI_KESETIAAN` (deepseek-v4-pro, reasoning=high), `response_format=json_object`. `_build_user_prompt()` **reuse langsung** `narasi.py::_build_user_prompt()` (impor sebagai `_build_user_prompt_narasi`) — verifier menerima konteks ground-truth PERSIS sama dengan yang dipakai menyusun narasi. TANPA retry balik ke `susun_narasi()` (mirror pola M3.5). Fallback pada API error/parse gagal → `GAGAL_TEKNIS` (BEDA dari M4.4 yang tidak punya fallback sama sekali).
- **Orkestrator gabungan:** `verifikasi_dan_susun_visualisasi(narasi, atomic_intents, packages, session_id, turn_index) -> tuple[HasilVerifikasiNarasi, list[DataVisualisasi]|None]` — visualisasi **HANYA** dipanggil kalau `hasil_verifikasi.lolos is True` (perbandingan eksplisit dengan `is True`, bukan truthy check — `lolos=None` dari `GAGAL_TEKNIS` juga menghasilkan `None` visualisasi, bukan error).
- **Fungsi visualisasi:** `visualisasi.py::susun_data_visualisasi(package) -> DataVisualisasi` + `susun_data_visualisasi_semua(packages) -> list[DataVisualisasi]` — **0 LLM**, transformasi struktur murni dari `nilai_hasil["rows"]`. Untuk `label_bentuk_jawaban=NILAI_TUNGGAL`: ekstrak scalar HANYA kalau tepat 1 baris × 1 kolom (tidak ambigu); kasus lain (termasuk 4 label non-`nilai_tunggal`) fallback ke `deret=rows` apa adanya.
- **Skema:** `HasilVerifikasiNarasi {narasi, status, lolos: bool|None, alasan: str|None}`; `DataVisualisasi {atomic_intent_id, label_bentuk_jawaban, nilai_tunggal: ...|None, deret: list[dict]|None}` — validator: tepat satu dari `nilai_tunggal`/`deret` terisi. Skema `deret` untuk 3 label selain `tren` masih PROVISIONAL (`docs/keputusan-tertunda.md` #4, dikonfirmasi masih terbuka, menunggu PIC 5).
- **LLM call total M4.4+M4.5:** 2 berurutan, sesuai framing dokumen orkestrasi. `susun_data_visualisasi_semua()` (0 LLM) berjalan kondisional setelahnya.
- **Bukti nyata:** Checkpoint 5, Task 10.
- **Penyimpangan:** tidak ada baru — status PROVISIONAL skema `deret` sudah tercatat di `docs/keputusan-tertunda.md`, dikonfirmasi ulang bukan ditemukan baru.

---
