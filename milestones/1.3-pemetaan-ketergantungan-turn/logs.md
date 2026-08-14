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

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — seluruh Task 1-6 berjalan sesuai plan, dengan satu perluasan kecil di Task 5 (skenario sukses tambahan) yang dicatat eksplisit di atas, bukan penyimpangan dari struktur checkpoint.
