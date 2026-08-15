# Logs — Milestone 1.7: Membangun Pencocokan Atomic Intent terhadap Data Session Memory

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `2dd65ca` | `docs(milestone-1.7): decisions` |
| 2 | `c690e00` | `feat(milestone-1.7): skema data pencocokan` |
| 3 | `dc0d2ac` | `chore(milestone-1.7): konstanta model pencocokan` |
| 4 | `024ff2b` | `feat(milestone-1.7): mekanisme pencocokan atomic intent` |
| 5 | `6d7abfc` | `feat(milestone-1.7): arsip ulang paket tercocok` |
| 6 | `e59cdd5` | `feat(milestone-1.7): orkestrator match_and_archive` |
| 7 | `bdf0988` | `test(milestone-1.7): skenario uji pencocokan dan verifikasi span nyata` |
| 8 | `c2e40db`, `bb4c27f`, `7f4cff8` | `docs(evals): rancangan` + `test(evals): eksekusi + payload` + `docs(evals): audit` |
| 9 | *(commit ini)* | `docs(milestone-1.7): logs, report` + `docs: perbarui status project` |

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama, sebelum diskusi mendalam dengan user soal pemahaman sistem (sebelum plan disetujui) dan hasil `AskUserQuestion` (mekanisme, pola verifikasi, model).

**Apa yang dilakukan**
13 entri keputusan: 3 Jenis A eksplisit dari `AskUserQuestion` (mekanisme LLM semantik, pola verifikasi satu panggilan + fallback aman, model Qwen3-32B reuse), 3 Jenis A dari diskusi pemahaman sistem yang dikonfirmasi user (filter status=berhasil, satu panggilan per atomic intent, tanpa eksklusivitas), 7 Jenis B forced/preseden (termasuk kebijakan arsip ulang yang di-forced langsung oleh komentar desain M1.5 di `src/db/models.py`).

**Commit:** `2dd65ca`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 2 — `src/schemas/matching.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`MatchStatus` (Enum 2 nilai), `AtomicIntentMatch` dengan validator konsistensi `status`↔`paket`.

**Hasil Verifikasi**
Instansiasi manual: 2 skenario valid (selesai+paket, perlu_eksekusi tanpa paket) berhasil; 2 skenario invalid (selesai tanpa paket, perlu_eksekusi dengan paket) ditolak validator dengan pesan jelas.

**Commit:** `c690e00`

---

## Checkpoint 3 — Konstanta Model

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 3 — `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`OPENROUTER_MODEL_MATCHING` (Qwen3-32B, reuse M1.4/M1.6).

**Commit:** `dc0d2ac`

---

## Checkpoint 4 — Mekanisme Pencocokan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 4 — `match_atomic_intents()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Filter kandidat ke `status=berhasil`, jalur pintas deterministik kalau hasil filter kosong (nol panggilan LLM), satu panggilan LLM konservatif per atomic intent dengan bounds-check deterministik pada `candidate_index`, fallback aman ke `perlu_eksekusi` pada kegagalan apa pun. Span `matching.evaluate` (agregat) membungkus span `chat` per panggilan nyata.

**Hasil Verifikasi**
Smoke test 3 skenario nyata — (a) kandidat kosong → semua `perlu_eksekusi`, 0 panggilan LLM; (b) atomic intent jelas cocok → `selesai` dengan paket benar (29.7s); (c) atomic intent jelas baru → `perlu_eksekusi` (24.1s). Span dicek nyata lewat Jaeger API (`matching.evaluate` + `chat` bersarang, atribut `candidate.pool_size`/`intent.matched_count`/`intent.unmatched_count`/`gen_ai.request.model`/`matching.result` terisi benar).

**Commit:** `024ff2b`

---

## Checkpoint 5 — Arsip Ulang

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 5 — `archive_matched_packages()`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu koreksi signifikan ditemukan SELAMA smoke test (dicatat di Temuan).

**Apa yang dilakukan**
Untuk tiap match `selesai`, bangun `SessionMemoryPackage` baru: `atomic_intent_id`/field lain disalin dari paket lama, `turn_index` diganti ke turn saat ini, panggil `store_session_memory()` (reuse M1.5).

**Temuan**
Desain awal `sumber` disalin VERBATIM dari paket lama — smoke test langsung menemukan ini SALAH: kalau paket lama `sumber="eksekusi_baru"` (eksekusi asli), menyalin verbatim membuat baris arsip juga `"eksekusi_baru"`, padahal seharusnya jadi `"session_memory (turn N)"` (N = turn asal) supaya rantai KK3 tercermin di data. Diperbaiki dengan `_sumber_arsip()`: bangun ulang jadi `session_memory (turn N)` HANYA kalau paket lama masih `"eksekusi_baru"`; kalau paket lama SUDAH `"session_memory (turn N)"` (kasus rantai transitif), pertahankan verbatim. `decisions.md` Keputusan 7 diperbarui menjelaskan koreksi ini sebelum commit.

**Hasil Verifikasi**
Smoke test: seed paket turn 3, match+arsip untuk turn 5, `retrieve_session_memory(sid, 5)` mengembalikan baris dengan `atomic_intent_id` SAMA seperti turn 3 dan `sumber="session_memory (turn 3)"` (setelah koreksi).

**Commit:** `6d7abfc`

---

## Checkpoint 6 — Orkestrator

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 6 — `match_and_archive()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Gabungkan `match_atomic_intents()` + `archive_matched_packages()` jadi satu titik masuk.

**Hasil Verifikasi**
Smoke test rantai NYATA turn 3→5→7 (dua pemanggilan `match_and_archive()` berurutan, bukan fixture ganda) — membuktikan KK3 sebelum masuk test suite formal. Baris arsip turn 7 punya `atomic_intent_id` sama dengan paket turn 3 asli, `sumber` tetap `"session_memory (turn 3)"` (tidak putus di turn 5/arsip perantara).

**Commit:** `e59cdd5`

---

## Checkpoint 7 — Test Suite Formal (Kriteria Keberhasilan)

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 7-9 — Skenario, `test_matching.py`, jalankan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
3 fungsi test sesuai 3 KK sumber: (a) intent sudah tersimpan → cocok, tidak dieksekusi ulang; (b) intent baru → tidak pernah cocok keliru; (c) rantai turn 7→5→3 lewat 2 pemanggilan `match_and_archive()` nyata berantai. Data seed manual via `store_session_memory()` (mirror preseden M1.5), teardown eksplisit per session_id.

**Hasil Verifikasi**
`uv run pytest tests/layers/context_resolution/test_matching.py -v` → 3/3 passed (119.38s).

**Commit:** `bdf0988`

---

## Checkpoint 8 — Eval Mendalam

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 10 — `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan. 10 skenario awal (S01-S10), jumlah tidak dipatok.

**Commit:** `c2e40db`

### Task 11 — `run_eval.py` + eksekusi

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penambahan skenario di tengah proses (dicatat di Temuan).

**Apa yang dilakukan**
Reuse `match_atomic_intents()` produksi langsung. Kandidat dikonstruksi IN-MEMORY (bukan lewat `store_session_memory()`) — dimensi yang diuji murni kualitas keputusan LLM, tidak perlu DB. Dijalankan DUA kali.

**Temuan**
Run pertama (10 skenario): 9/10 lolos, S07 (non-eksklusivitas) REVIEW — payload menunjukkan ini karena item kedua skenario ("bulan April kemarin") genuinely ambigu secara temporal, bukan paraphrase bersih. Ditambahkan S11 (retest dengan paraphrase eksplisit tidak ambigu) ke `run_eval.py`/`rancangan.md`, lalu SELURUH 11 skenario dijalankan ulang. Run kedua: 9/11 lolos — S07 tetap REVIEW (konsisten, mengonfirmasi analisis ambiguitas), S11 LOLOS penuh (mengonfirmasi Keputusan 6 genuinely bekerja). S09 (recency bias) yang LOLOS di run pertama berubah jadi REVIEW di run kedua meski prompt+kandidat identik persis (`temperature=0`) — ditemukan `temperature=0` TIDAK menjamin determinisme penuh untuk model ini via OpenRouter; payload S09 run kedua menunjukkan mode kegagalan "distractor confusion" (gagal cocok sama sekali ke kandidat manapun) BUKAN recency bias klasik (salah pilih kandidat di posisi akhir) — tetap gagal ke arah aman (`perlu_eksekusi`, bukan false-positive).

**Hasil Verifikasi**
11/11 skenario selesai dieksekusi. 9/11 check otomatis lolos di run final.

**Commit:** `bb4c27f`

### Task 12 — `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Analisis mendalam S07 (diklasifikasi ulang jadi artefak desain skenario, dikonfirmasi lewat S11) dan S09 (temuan nyata: distractor confusion + non-determinisme `temperature=0`, berkorelasi dengan `docs/keterbatasan-diterima.md` #3 recency bias).

**Commit:** `7f4cff8`

---

## Checkpoint 9 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 13-15 — `logs.md`, `report.md`, `CLAUDE.md`/`AGENT.md`

Entri Checkpoint 1-8 ditulis sebagai bagian Task 13. Lihat `report.md` dan `CLAUDE.md`/`AGENT.md` untuk Task 14-15. Temuan eval (distractor confusion/recency bias, non-determinisme `temperature=0`) dipromosikan jadi tambahan `docs/keterbatasan-diterima.md` #3 sebagai bagian Task 14.

**Commit:** *(lihat commit gabungan di bawah)*

## Task/Checkpoint di Luar Plan (jika ada)

Satu penambahan di luar plan awal: skenario S11 (Checkpoint 8, Task 11) — ditambahkan setelah run pertama menemukan S07 tidak benar-benar menguji apa yang dimaksud. Konsisten prinsip "jumlah skenario tidak dipatok" (Keputusan 13 M1.6, diwarisi M1.7) — bukan penyimpangan dari plan, melainkan penerapan langsung prinsip itu saat kebutuhan nyata muncul di tengah eksekusi.
