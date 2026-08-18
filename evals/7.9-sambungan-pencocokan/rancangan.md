# Rancangan Pengujian — Sambungan 4: (Decomposition + Tarik Memory) → Pencocokan (Milestone 7.9)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — kejadian dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada. Struktur mirror `evals/7.6-.../`, `evals/7.7-.../`, `evals/7.8-.../`, dengan penyesuaian verdict: KK M7.9 soal STATUS match yang benar (closed-space: `selesai`/`perlu_eksekusi` per atomic intent) — verdict tiap kejadian dicek langsung terhadap nilai `status`/`paket` hasil `match_and_archive()`, bukan `required_phrases`/`forbidden_phrases` (pola M7.8, untuk KK berbasis konten teks bebas).

**Instruksi eksplisit user**: cakupan real-execution TIDAK dibatasi 2 kejadian (preseden M7.6-M7.8) — 6 kejadian di bawah mencakup seluruh kombinasi state yang secara struktural berbeda di titik pertemuan Decomposition+Tarik Memory→Pencocokan (lihat `decisions.md` Keputusan 5 untuk analisis ruang kejadian lengkap).

## Yang Diuji

`proses_turn()` — khusus segmen baru M7.9: `match_and_archive(decomposition_result.atomic_intents, session_memory_result or [], payload.session_id, payload.turn_index)` dipanggil sekuensial setelah Decomposition (M7.8) selesai. Kejadian di sini menjalankan pipeline PENUH dari payload mentah — Decomposition dan Tarik Memory (kalau dipicu) benar-benar dari `proses_turn()` nyata, BUKAN `AtomicIntent`/`SessionMemoryPackage` buatan tangan yang langsung di-passing ke `match_and_archive()` (itu akan melanggar KK M7.9 literal).

**Fixture seeding** (E03-E06 saja): karena Execution (M4.x) belum disambungkan ke `proses_turn()` (ditunda M7.1x), data "turn sebelumnya yang sudah pernah dieksekusi" disuntik manual via `store_session_memory()` SEBELUM turn saat ini dijalankan — mensimulasikan seolah Execution sudah pernah menghitung dan menyimpannya (preseden identik M1.7, lihat `decisions.md` Keputusan 6). Data yang diuji SENDIRI (atomic_intents Decomposition turn ini, kandidat hasil `retrieve_session_memory()` turn ini) tetap 100% dari pipeline nyata.

## Kejadian

### E01 — Tarik Memory tidak dipanggil (fast-path, origin: tidak ada referensi)

**Payload:** `session_id="eval-7.9-e01"`, turn 1, tanpa histori, "Berapa occupancy rate properti kita bulan Juni 2026?"

**Ekspektasi:**
- `ketergantungan.is_dependent=False` → `session_memory=None` di `KeadaanTurn`.
- `matches`: 1 `AtomicIntentMatch`, `status=perlu_eksekusi`, `paket=None`.
- **0 span** `matching.evaluate` DAN **0 span** `chat` di tracer `context_resolution.matching` — `match_atomic_intents()` return SEBELUM membuka span apa pun saat `candidates` kosong (jalur fast-path deterministik, lihat `matching.py`).

---

### E02 — Tarik Memory dipanggil, genuinely kosong (fast-path, origin: dipanggil tapi tidak ada data)

**Payload:** `session_id="eval-7.9-e02"`, turn 2, histori turn 1 "Berapa revenue reservasi bulan Maret 2026?" → "Rp 800 juta", pertanyaan turn 2: "Bandingkan dengan bulan sebelumnya." TIDAK ADA seeding `store_session_memory()` untuk sesi ini — `retrieve_session_memory()` genuinely tidak menemukan baris apa pun.

**Ekspektasi:**
- `ketergantungan.is_dependent=True`, `referenced_turn_index=1` → Tarik Memory dipanggil → `session_memory=[]` (bukan `None`) — beda origin dari E01, hasil mekanis sama.
- `matches`: 1 `AtomicIntentMatch`, `status=perlu_eksekusi`, `paket=None`.
- **0 span** `matching.evaluate`/`chat` — sama seperti E01 (candidates kosong setelah filter, meski originnya "dipanggil" bukan "tidak dipanggil").

---

### E03 — Match nyata (bukti KK literal utama)

**Seeding:** `store_session_memory()` untuk `session_id="eval-7.9-e03"`, `turn_index=1`: `teks_kebutuhan="Berapa occupancy rate bulan April 2026?"`, `label_bentuk_jawaban=nilai_tunggal`, `nilai_hasil={"occupancy_rate": 78}`, `status=berhasil`, `sumber="eksekusi_baru"`.

**Payload:** turn 2, histori turn 1 "Berapa occupancy rate bulan April 2026?" → "Occupancy April 2026 mencapai 78%.", pertanyaan turn 2: "Berapa lagi occupancy April 2026 itu?" (jelas merujuk turn 1, tanpa info baru).

**Ekspektasi:**
- `ketergantungan.is_dependent=True`, `referenced_turn_index=1` → Tarik Memory menemukan 1 kandidat (`status=berhasil`, lolos filter).
- Decomposition tunggal, 1 atomic_intent (teks serupa kandidat tersimpan).
- `matches`: 1 `AtomicIntentMatch`, **`status=selesai`**, `paket` merujuk baris yang diseed.
- **1 span** `matching.evaluate` + **1 span** `chat` (satu atomic_intent, satu kandidat).
- **Arsip ulang**: baris baru tersimpan di `session_memory_packages` untuk `turn_index=2`, `sumber="session_memory (turn 1)"` (dicek langsung via `retrieve_session_memory(session_id, 2)` setelah eksekusi).

---

### E04 — Anti false-positive (kandidat tersedia, topik beda → TIDAK match)

**Seeding:** sama seperti E03 tapi `session_id="eval-7.9-e04"` — kandidat occupancy April 2026, `status=berhasil`.

**Payload:** turn 2, histori sama (occupancy April 2026), pertanyaan turn 2: "Sekarang gimana dengan revenue F&B bulan yang sama?" (merujuk periode via "bulan yang sama", TAPI metrik/domain jelas beda — revenue F&B, bukan occupancy).

**Ekspektasi:**
- `ketergantungan.is_dependent=True` (referensi periode terdeteksi) → Tarik Memory menemukan kandidat occupancy yang sama seperti E03.
- Decomposition tunggal: "Berapa revenue F&B bulan April 2026?" (hasil Rewrite).
- `matches`: 1 `AtomicIntentMatch`, **`status=perlu_eksekusi`**, `paket=None` — TIDAK match meski kandidat tersedia (domain berbeda: revenue F&B vs occupancy).
- **1 span** `matching.evaluate` + **1 span** `chat` (kandidat dievaluasi, TAPI hasilnya tidak match — beda dari E01/E02 yang 0 span karena kandidat kosong dari awal).

---

### E05 — Kandidat ada tapi status≠berhasil (filter internal via pipeline nyata)

**Seeding:** `store_session_memory()` untuk `session_id="eval-7.9-e05"`, `turn_index=1`: `teks_kebutuhan="Berapa occupancy rate bulan April 2026?"`, `status=gagal_teknis` (BUKAN `berhasil`), `nilai_hasil={}`.

**Payload:** turn 2, histori sama seperti E03/E04, pertanyaan turn 2: "Berapa lagi occupancy April 2026 itu?" (sama seperti E03, supaya perbedaan HANYA di status kandidat, bukan di pertanyaan).

**Ekspektasi:**
- Tarik Memory menemukan 1 baris (`retrieve_session_memory()` tidak filter status — mengembalikan apa adanya) → `session_memory` di `KeadaanTurn` NON-KOSONG (1 item, status=gagal_teknis).
- TAPI `match_atomic_intents()` memfilter kandidat ke `status=berhasil` saja → filtered kosong → fast-path.
- `matches`: 1 `AtomicIntentMatch`, `status=perlu_eksekusi`, `paket=None`.
- **0 span** `matching.evaluate`/`chat` — MESKI `session_memory` non-kosong di `KeadaanTurn` (beda dari E01/E02 yang `session_memory` kosong/None dari awal) — bukti filter internal bekerja lewat data pipeline nyata, bukan hand-crafted seperti test M1.7 asli.

---

### E06 — Majemuk campuran (granularitas per-intent, reuse pola M7.8 E01)

**Seeding:** `store_session_memory()` untuk `session_id="eval-7.9-e06"`, `turn_index=1`: `teks_kebutuhan="Berapa occupancy rate bulan April 2026?"`, `status=berhasil`, `nilai_hasil={"occupancy_rate": 78}` — HANYA untuk April 2026 (TIDAK ada seeding untuk April 2025).

**Payload:** turn 2, histori turn 1 "Berapa occupancy rate bulan April 2026?" → "Occupancy April 2026 mencapai 78%.", pertanyaan turn 2: "Bandingkan dengan occupancy satu tahun sebelumnya." (persis skenario M7.8 E01).

**Ekspektasi (mengacu hasil nyata M7.8 E01):**
- Rewrite: "...April 2026 dibandingkan dengan...April 2025..." (kedua tahun eksplisit).
- Decomposition `majemuk_bergantung`, 3 atomic_intents: (1) "occupancy April 2025" independen, (2) "occupancy April 2026" independen, (3) perbandingan keduanya, bergantung pada (1)+(2).
- Tarik Memory menemukan 1 kandidat (April 2026 saja).
- `matches`: **HASIL CAMPURAN** — intent (2) "April 2026" → `status=selesai` (match ke kandidat tersimpan); intent (1) "April 2025" → `status=perlu_eksekusi` (tidak ada kandidat); intent (3) perbandingan → `status=perlu_eksekusi` (tidak ada kandidat untuk hasil perbandingan itu sendiri).
- **1 span** `matching.evaluate` + **3 span** `chat` (satu per atomic_intent, kandidat pool tetap sama untuk ketiganya).
- **Arsip ulang**: HANYA 1 baris baru tersimpan (untuk intent yang match), bukan 3.

## Ringkasan Ekspektasi

| ID | Tarik Memory dipanggil? | Kandidat lolos filter | Jumlah atomic_intent | `status` per intent | Span `matching.evaluate`+`chat` |
|---|---|---|---|---|---|
| E01 | Tidak | 0 | 1 | `perlu_eksekusi` | 0+0 |
| E02 | Ya (kosong) | 0 | 1 | `perlu_eksekusi` | 0+0 |
| E03 | Ya | 1 | 1 | `selesai` | 1+1 |
| E04 | Ya | 1 | 1 | `perlu_eksekusi` | 1+1 |
| E05 | Ya | 0 (terfilter status) | 1 | `perlu_eksekusi` | 0+0 |
| E06 | Ya | 1 | 3 | campuran: 1×`selesai`, 2×`perlu_eksekusi` | 1+3 |
