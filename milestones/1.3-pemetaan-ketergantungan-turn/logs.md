# Logs — Milestone 1.3: Membangun Pemetaan Ketergantungan Turn

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `049a8d5`, `832078f` (+ `a81052f` fix hash) | `docs: revisi kontrak payload turn...` + `feat(milestone-1.3): revisi payload...` |
| 2 | `beee282` (+ `7f5b4bc` fix hash) | `chore(milestone-1.3): fondasi provider llm openrouter` |
| 3 | `ec6c21a` (+ `62df336` fix hash) | `feat(milestone-1.3): deteksi ketergantungan turn via llm, span chat` |
| 4 | `9a6f204` (+ `949be00` fix hash) | `test(milestone-1.3): skenario uji dependency turn dan verifikasi span nyata` |
| 5 | `95c1587` | `docs(milestone-1.3): decisions, logs, report` (`CLAUDE.md`/`AGENT.md` sengaja tidak di-commit, lihat Task 22) |

---

## Checkpoint 1 — Revisi Kontrak Payload M1.2 (Prasyarat): Histori Penuh

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 1 — Revisi `arsitektur-ai-chatbot-rbac.md` §4

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baris 93-95 (kontrak payload) diubah dari "teks & jawaban turn sebelumnya" (tunggal) jadi "seluruh histori turn-turn sebelumnya dalam sesi — turn 1 s.d. turn_index-1, masing-masing dengan turn_index, teks pertanyaan & jawabannya". Ditambahkan catatan inline (bracket) menjelaskan kapan/kenapa direvisi, merujuk balik ke `decisions.md` milestone ini.

**Temuan/Error** Tidak ada. **Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

### Task 2 — Grep referensi payload lama di seluruh `docs/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`grep` pola "teks & jawaban turn sebelumnya", "previous_turn", "turn sebelumnya" ke seluruh `docs/`. Ditemukan satu referensi relevan lain: Lingkup Milestone 1.2 sendiri di `rancangan-context-decomposition.md` baris 46 ("teks beserta jawaban dari turn sebelumnya") — diperbarui konsisten. Referensi lain yang ditemukan (di `template-plan-milestone-lengkap.md`, `rancangan-execution-interpretation.md`, bagian lain `rancangan-context-decomposition.md`) dicek satu per satu: sebagian besar tidak terkait langsung (membahas milestone/mekanisme lain), dan satu (`template-plan-milestone-lengkap.md` baris 184, "konteks turn-turn sebelumnya") justru **sudah konsisten** dengan revisi ini (frasa jamak yang sebelumnya jadi temuan inkonsistensi di riset pra-plan, sekarang otomatis sinkron) — tidak perlu diubah.

**Hasil Verifikasi:** `grep` ulang setelah revisi tidak menemukan sisa referensi bentuk tunggal yang belum diperbarui di lokasi relevan.

**Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

### Task 3 — Revisi `src/schemas/turn_payload.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`PreviousTurn` → `HistoryTurn` (tambah field `turn_index: int = Field(ge=1)`). `TurnPayload.previous_turn: PreviousTurn | None` → `history: list[HistoryTurn] = Field(default_factory=list)`. Validator `previous_turn_required_when_not_first_turn` → `history_matches_turn_index`: bandingkan `{h.turn_index for h in history}` dengan `set(range(1, turn_index))` — satu pengecekan menangkap hilang, duplikat, dan gap sekaligus, pesan error menyebut daftar yang diharapkan vs ditemukan.

**Temuan/Error** Tidak ada.

**Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

### Task 4 — Cek `input_layer.py`/`main.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`grep "previous_turn"` ke `src/` — nihil. Dikonfirmasi (bukan diasumsikan) span attribute yang direkam `validate_turn_payload()` cuma `session.id`/`turn.index`, tidak menyentuh isi `previous_turn`/`history` sama sekali — tidak ada perubahan diperlukan di kedua file ini.

**Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

### Task 5 — Revisi `tests/layers/test_input_layer.py`

**Kesesuaian dengan plan:** Sesuai plan, diperluas sedikit dari deskripsi task (lihat Temuan).

**Apa yang dilakukan**
`VALID_PAYLOAD_TURN2` pakai `history: [...]` 1 entri. Ditambah `VALID_PAYLOAD_TURN3` (histori 2 entri, turn_index=3) untuk skenario multi-turn. Test baru: `test_turn_index_3_with_full_multi_turn_history_accepted`, `test_turn_index_3_with_gap_in_history_rejected`, `test_turn_index_3_with_duplicate_history_turn_index_rejected`. Total 12 test (dari 9 sebelumnya).

**Temuan**
Plan menyebut "duplikat turn_index" dan "histori kurang lengkap" sebagai skenario tambahan — ditambahkan skenario ketiga (`turn_index_3_with_full_multi_turn_history_accepted`, kasus sukses 2-entri) yang tidak eksplisit disebut di plan tapi relevan langsung untuk membuktikan validator menangani histori >1 entri dengan benar, bukan cuma 0 atau 1 entri.

**Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

### Task 6 — Jalankan pytest + verifikasi `curl`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv run pytest tests/layers/test_input_layer.py -v` — 12/12 lolos. Server dijalankan (`uv run uvicorn src.main:app --port 8000`), dua request `curl` dikirim: payload `turn_index=3` dengan histori 2-entri lengkap, dan payload sama dengan histori gap (cuma turn_index=1, hilang turn_index=2).

**Hasil Verifikasi**
- Payload histori lengkap → `200`, echo benar termasuk kedua entri histori dengan `turn_index` masing-masing.
- Payload histori gap → `422`, pesan: `"history harus berisi tepat turn_index [1, 2] ..., ditemukan [1]"` — menyebut selisih persis, bukan pesan generik.

**Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

### Task 6a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 1 di atas ditulis. File di-stage dalam 2 commit terpisah (dokumen vs kode), sesuai rencana Commit di plan.

**Commit:** `049a8d5` (dokumen) / `832078f` (kode)

---

## Checkpoint 2 — Fondasi Provider LLM (OpenRouter)

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 7 — Tambah dependency

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv add openai python-dotenv`.

**Temuan**
`openai==3.0.0` ter-install — versi major 3.x, lebih baru dari yang mungkin diasumsikan generik. Dicek langsung: `chat.completions.create` (API lama, kompatibel OpenRouter) masih tersedia di versi ini, begitu juga `responses.create` (API baru OpenAI, belum tentu kompatibel proxy OpenRouter) — diputuskan tetap pakai `chat.completions.create` untuk Checkpoint 3, sesuai dokumentasi kompatibilitas resmi OpenRouter.

**Commit:** `beee282` — `chore(milestone-1.3): fondasi provider llm openrouter`

---

### Task 8 — Tulis `.env.example`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Template `OPENROUTER_API_KEY=` (nilai kosong) di root, komentar menjelaskan cara pakai dan larangan commit nilai asli. Dikonfirmasi `.env` sudah gitignored sejak baris 1 `.gitignore` awal repo (tidak perlu ditambah lagi).

**Commit:** `beee282` — `chore(milestone-1.3): fondasi provider llm openrouter`

---

### Task 9 — Tulis `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Konstanta `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL="deepseek/deepseek-v4-flash-0731"`, fungsi `get_openrouter_client()` yang baca `OPENROUTER_API_KEY` (via `load_dotenv()` + `os.environ.get`), lempar `RuntimeError` jelas kalau tidak diset.

**Temuan**
Saat verifikasi, ditemukan `OPENROUTER_API_KEY` **sudah ter-set di environment shell** (dikonfirmasi lewat `env | grep OPENROUTER_API_KEY` — hasilnya ada, format `sk-or-v1-...` sesuai pola key OpenRouter) meskipun `.env` belum dibuat user. Kemungkinan sudah ada di environment sistem/profil pengguna dari luar sesi ini. Nilai asli tidak dicatat/ditampilkan ulang di log ini atau di manapun. Karena sudah tersedia di environment, `get_openrouter_client()` langsung berhasil tanpa perlu menunggu `.env` dibuat.

**Hasil Verifikasi**
`uv run python -c "from src.config.llm import get_openrouter_client; print(get_openrouter_client())"` berhasil, mengembalikan objek `OpenAI` tanpa error.

**Commit:** `beee282` — `chore(milestone-1.3): fondasi provider llm openrouter`

---

### Task 10 — Skeleton `src/layers/context_resolution/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/layers/context_resolution/__init__.py` (kosong, subpackage baru untuk 4 milestone Context Resolution — M1.3 mengisi modul pertamanya di Checkpoint 3).

**Commit:** `beee282` — `chore(milestone-1.3): fondasi provider llm openrouter`

---

### Task 10a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 2 di atas ditulis. File di-stage: `pyproject.toml`, `uv.lock`, `.env.example`, `src/config/llm.py`, `src/layers/context_resolution/__init__.py`, `milestones/1.3-pemetaan-ketergantungan-turn/logs.md`.

**Commit:** `beee282` — `chore(milestone-1.3): fondasi provider llm openrouter`

---

## Checkpoint 3 — Prompt, Pemanggilan LLM, Span `chat`

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 11 — Tulis `src/schemas/turn_dependency.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`TurnDependencyResult(is_dependent: bool, referenced_turn_index: int | None = None)`. `session_id` sengaja tidak diminta dari LLM (ditempel kode setelah hasil diterima, di layer pemanggil nanti) — mengurangi risiko halusinasi.

**Commit:** `ec6c21a` — `feat(milestone-1.3): deteksi ketergantungan turn via llm, span chat`

---

### Task 12 — Tulis `src/layers/context_resolution/turn_dependency.py`

**Kesesuaian dengan plan:** Sesuai plan, satu penyesuaian teknis kecil — lihat Temuan.

**Apa yang dilakukan**
`detect_turn_dependency(payload) -> TurnDependencyResult`: system+user prompt (histori dilabeli per `turn_index`, urut), panggilan `client.chat.completions.create` dengan `response_format={"type": "json_object"}`, span `chat` (atribut `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens` dari `response.usage`). Bounds-check deterministik: `referenced_turn_index` di luar himpunan `turn_index` histori yang tersedia → dipaksa `is_dependent=False`, dicatat sebagai span attribute `dependency.forced_independent_reason`. Kegagalan parse JSON total juga dipaksa `is_dependent=False` dengan alasan serupa.

**Temuan**
Plan menyebut "response_format JSON schema (structured output)" — diputuskan pakai `{"type": "json_object"}` (mode JSON umum) alih-alih `json_schema` strict mode, karena dukungan `json_schema` strict bervariasi antar model/provider di OpenRouter (dikonfirmasi lewat riset sebelum plan: "JSON Schema response formats on compatible models" — tidak semua model). `json_object` lebih universal, dikombinasikan dengan instruksi bentuk JSON persis di system prompt + validasi Pydantic defensif (try/except) di sisi kode — hasil akhirnya sama-sama robust tanpa bergantung pada fitur yang belum tentu didukung penuh model spesifik ini.

**Error/Kegagalan** Tidak ada.

**Commit:** `ec6c21a` — `feat(milestone-1.3): deteksi ketergantungan turn via llm, span chat`

---

### Task 12a-b — Smoke Test Manual (2 skenario)

**Kesesuaian dengan plan:** Sesuai plan (Task 12a), ditambah satu smoke test kedua di luar deskripsi literal Task 12a untuk keyakinan lebih (lihat Temuan).

**Apa yang dilakukan**
Skenario 1 (persis sesuai plan): `turn_index=1`, `history=[]`, pertanyaan berdiri sendiri — memanggil `detect_turn_dependency()` langsung (bukan mock), API call nyata ke OpenRouter. Skenario 2 (tambahan): `turn_index=2` dengan 1 entri histori, pertanyaan eksplisit merujuk ("Bandingkan dengan bulan lalu").

**Temuan**
Slug model `deepseek/deepseek-v4-flash-0731` **valid** — API call sukses tanpa error model-not-found, mengonfirmasi riset web sebelum plan sudah benar (tidak perlu koreksi, berbeda dari risiko yang diantisipasi di plan).

**Hasil Verifikasi**
- Skenario 1: `TurnDependencyResult(is_dependent=False, referenced_turn_index=None)` — benar, pertanyaan berdiri sendiri.
- Skenario 2: `TurnDependencyResult(is_dependent=True, referenced_turn_index=1)` — benar, rujukan ke turn 1 terdeteksi tepat.

**Commit:** `ec6c21a` — `feat(milestone-1.3): deteksi ketergantungan turn via llm, span chat`

---

### Task 12c — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan (penomoran Task 12a/12b di plan digabung jadi satu entri smoke test di atas; Task 12c menggantikan "Task 12b — catat logs" di plan untuk menghindari tabrakan penomoran).

**Apa yang dilakukan**
Entri Checkpoint 3 di atas ditulis. File di-stage: `src/schemas/turn_dependency.py`, `src/layers/context_resolution/turn_dependency.py`, `milestones/1.3-pemetaan-ketergantungan-turn/logs.md`.

**Commit:** `ec6c21a` — `feat(milestone-1.3): deteksi ketergantungan turn via llm, span chat`

---

## Checkpoint 4 — Test Suite (3 Skenario) + Verifikasi Span Nyata

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 13 — Susun 3 kelompok skenario uji

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Kelompok A (rujukan eksplisit): turn 2 "Bandingkan dengan bulan sebelumnya" merujuk turn 1 (revenue reservasi Maret). Kelompok B (berdiri sendiri): turn 2 soal fasilitas spa, histori turn 1 soal staff HR — topik tidak nyambung sama sekali. Kelompok C (rujukan turn jauh): skenario 7-turn domain hospitality penuh (occupancy→F&B→**komplain housekeeping**→maintenance AC→spa→performa staff→"balik lagi ke soal komplain housekeeping tadi") — turn 7 harus merujuk turn 3, bukan turn 6 (topik terdekat, staff performance, sama sekali tidak nyambung ke komplain housekeeping).

**Commit:** `9a6f204` — `test(milestone-1.3): skenario uji dependency turn dan verifikasi span nyata`

---

### Task 14 — Tulis `tests/layers/context_resolution/test_turn_dependency.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
3 fungsi test (satu per kelompok), `pytestmark` skip otomatis kalau `OPENROUTER_API_KEY` tidak diset. Panggilan `detect_turn_dependency()` sungguhan (bukan mock).

**Commit:** `9a6f204` — `test(milestone-1.3): skenario uji dependency turn dan verifikasi span nyata`

---

### Task 15 — Jalankan test suite

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv run pytest tests/layers/context_resolution/ -v`.

**Hasil Verifikasi**
Ketiga test **lolos** (3 passed in 17.72s), termasuk Kelompok C — bukti langsung bahwa gap yang memicu revisi payload di Checkpoint 1 sekarang genuinely terselesaikan: LLM benar mengarahkan `referenced_turn_index=3` untuk turn 7, bukan salah tangkap ke turn 6 (topik terdekat tapi tidak relevan).

**Commit:** `9a6f204` — `test(milestone-1.3): skenario uji dependency turn dan verifikasi span nyata`

---

### Task 16 — Verifikasi span nyata di Jaeger

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Disadari sebelum verifikasi: pemanggilan `detect_turn_dependency()` langsung (baik di smoke test Checkpoint 3 maupun test suite Task 15) **tidak pernah memanggil `setup_tracing()`** — beda dari jalur HTTP (`src.main`) yang memanggilnya otomatis lewat `lifespan`. Tanpa itu, span dipakai `TracerProvider` no-op default, tidak benar-benar terkirim ke Collector. Diperbaiki untuk verifikasi ini: panggil `setup_tracing('nirwana-chatbot-context-resolution')` eksplisit dulu, baru `detect_turn_dependency()`, lalu `force_flush()` + `sleep(2)` sebelum query — pola persis sama seperti skrip smoke-test Milestone 1.1.

**Hasil Verifikasi**
Query `GET /api/traces?service=nirwana-chatbot-context-resolution` mengembalikan trace `063e9af0cced951dc696009003e08afc`: span `chat`, atribut `gen_ai.operation.name=chat`, `gen_ai.request.model=deepseek/deepseek-v4-flash-0731`, `gen_ai.usage.input_tokens=418`, `gen_ai.usage.output_tokens=366` (angka nyata dari respons API, bukan 0/kosong), `dependency.referenced_turn_index=1`. Seluruhnya sesuai kontrak Bagian 2 dokumen observability.

**Commit:** `9a6f204` — `test(milestone-1.3): skenario uji dependency turn dan verifikasi span nyata`

---

### Task 16b — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan (menggantikan penomoran "Task 16a" di plan untuk konsistensi dengan pola 16a=temuan setup_tracing yang digabung ke Task 16 di atas).

**Apa yang dilakukan**
Entri Checkpoint 4 di atas ditulis. File di-stage: `tests/layers/context_resolution/__init__.py`, `tests/layers/context_resolution/test_turn_dependency.py`, `milestones/1.3-pemetaan-ketergantungan-turn/logs.md`.

**Commit:** `9a6f204` — `test(milestone-1.3): skenario uji dependency turn dan verifikasi span nyata`

---

## Checkpoint 5 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-14 · **Selesai:** 2026-08-14

### Task 17 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
11 entri keputusan: 5 Jenis A (genuinely terbuka dari `AskUserQuestion` — payload histori penuh, provider, model, plus 2 ditemukan saat implementasi: `response_format`, `setup_tracing`) dan 6 Jenis B (forced/preseden), seluruhnya dengan "Opsi yang Dipertimbangkan tapi Ditolak".

**Commit:** *(lihat commit gabungan di bawah)*

---

### Task 18 — Lengkapi `logs.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tabel ringkasan commit per checkpoint ditambahkan. Entri Checkpoint 5 ini sendiri ditulis sebagai penuntas.

**Commit:** *(lihat commit gabungan di bawah)*

---

### Task 19 — Tulis `report.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ketiga Kriteria Keberhasilan sumber dipetakan ke bukti nyata (Bagian 2), cara kerja+diagram Mermaid ditulis (Bagian 3, termasuk alur bounds-check/fallback), dikonfirmasi tidak ada "Catatan Serah Terima" eksplisit untuk M1.3 tapi "Kenapa Terpisah" M1.3 sendiri menyebut M1.4/M1.5 sebagai penerima langsung (Bagian 3, Integrasi). 4 perubahan-dari-plan didaftar (Bagian 4), 4 keterbatasan didaftar (Bagian 5), 3 follow-up didaftar (Bagian 6).

**Commit:** *(lihat commit gabungan di bawah)*

---

### Task 20 — Entri baru `docs/keterbatasan-diterima.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri #2: payload histori penuh bisa membesar untuk sesi sangat panjang. Sekalian diperbaiki referensi path `genai_semconv.py` yang stale di entri #1 (masih menyebut `infra/observability/`, padahal sudah pindah ke `src/observability/` sejak M1.2) — perluasan kecil housekeeping, dicatat di sini.

**Commit:** *(lihat commit gabungan di bawah)*

---

### Task 21 — Addendum `milestones/1.2-input-layer/report.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Satu paragraf addendum ditambahkan di akhir Bagian 5 (Keterbatasan) M1.2, mencatat revisi kontrak `previous_turn`→`history`. Entri asli di atasnya (termasuk yang menyebut `previous_turn`) **tidak diubah** — prinsip "jangan menghaluskan sejarah" dipertahankan.

**Commit:** *(lihat commit gabungan di bawah)*

---

### Task 22 — Perbarui `CLAUDE.md`/`AGENT.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tabel "Struktur Repository": baris `src/` (catat subpackage `context_resolution/` untuk layer multi-milestone), `tests/`, `docs/keterbatasan-diterima.md` diperbarui. "Status Saat Ini": M1.3 SELESAI dicatat, catatan eksplisit bahwa skema payload M1.2 sudah bukan bentuk final lagi (rujuk M1.3), provider/model LLM dicatat sudah ditentukan (untuk M1.3, dengan catatan status "testing" bukan otomatis final seluruh proyek). `AGENT.md` disinkronkan ulang (`cp` + `diff` kosong).

**Hasil Verifikasi**
Konsisten preseden M1.1/M1.2: `CLAUDE.md`/`AGENT.md` **tidak** ikut di-`git add`/commit (dikonfirmasi `git status --short` tidak menampilkan keduanya, gitignored).

**Commit:** Tidak ada commit untuk Task ini (disengaja, konsisten preseden).

---

### Task Gabungan (17, 19-21) — Commit checkpoint

**Apa yang dilakukan**
File Task 17, 19-21 di-stage bersama: `docs/keterbatasan-diterima.md`, `milestones/1.2-input-layer/report.md`, `milestones/1.3-pemetaan-ketergantungan-turn/{decisions.md,report.md}`. `CLAUDE.md`/`AGENT.md` tidak ikut (Task 22, disengaja).

**Commit:** `95c1587` — `docs(milestone-1.3): decisions, logs, report`

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada checkpoint baru di luar plan. Penyimpangan task (semuanya koreksi/penyesuaian di dalam task yang sudah direncanakan, dicatat eksplisit di masing-masing entri): skenario sukses tambahan Task 5; smoke test kedua Task 12a-b; pilihan `json_object` alih-alih `json_schema` Task 12; kebutuhan `setup_tracing()` eksplisit Task 16; perbaikan path stale `genai_semconv.py` di Task 20.
