# Logs — Milestone 1.3: Membangun Pemetaan Ketergantungan Turn

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

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

**Commit:** *(lihat Task 10a)*

---

### Task 8 — Tulis `.env.example`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Template `OPENROUTER_API_KEY=` (nilai kosong) di root, komentar menjelaskan cara pakai dan larangan commit nilai asli. Dikonfirmasi `.env` sudah gitignored sejak baris 1 `.gitignore` awal repo (tidak perlu ditambah lagi).

**Commit:** *(lihat Task 10a)*

---

### Task 9 — Tulis `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Konstanta `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL="deepseek/deepseek-v4-flash-0731"`, fungsi `get_openrouter_client()` yang baca `OPENROUTER_API_KEY` (via `load_dotenv()` + `os.environ.get`), lempar `RuntimeError` jelas kalau tidak diset.

**Temuan**
Saat verifikasi, ditemukan `OPENROUTER_API_KEY` **sudah ter-set di environment shell** (dikonfirmasi lewat `env | grep OPENROUTER_API_KEY` — hasilnya ada, format `sk-or-v1-...` sesuai pola key OpenRouter) meskipun `.env` belum dibuat user. Kemungkinan sudah ada di environment sistem/profil pengguna dari luar sesi ini. Nilai asli tidak dicatat/ditampilkan ulang di log ini atau di manapun. Karena sudah tersedia di environment, `get_openrouter_client()` langsung berhasil tanpa perlu menunggu `.env` dibuat.

**Hasil Verifikasi**
`uv run python -c "from src.config.llm import get_openrouter_client; print(get_openrouter_client())"` berhasil, mengembalikan objek `OpenAI` tanpa error.

**Commit:** *(lihat Task 10a)*

---

### Task 10 — Skeleton `src/layers/context_resolution/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/layers/context_resolution/__init__.py` (kosong, subpackage baru untuk 4 milestone Context Resolution — M1.3 mengisi modul pertamanya di Checkpoint 3).

**Commit:** *(lihat Task 10a)*

---

### Task 10a — Catat logs, commit checkpoint

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Entri Checkpoint 2 di atas ditulis. File di-stage: `pyproject.toml`, `uv.lock`, `.env.example`, `src/config/llm.py`, `src/layers/context_resolution/__init__.py`, `milestones/1.3-pemetaan-ketergantungan-turn/logs.md`.

**Commit:** *(diisi setelah commit dieksekusi)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — seluruh Task 1-10 berjalan sesuai plan, dengan satu perluasan kecil di Task 5 (skenario sukses tambahan) yang dicatat eksplisit di atas, bukan penyimpangan dari struktur checkpoint.
