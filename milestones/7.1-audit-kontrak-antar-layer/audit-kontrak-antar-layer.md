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
