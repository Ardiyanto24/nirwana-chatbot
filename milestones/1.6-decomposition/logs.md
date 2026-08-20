# Logs — Milestone 1.6: Membangun Decomposition (Klasifikasi, Pemecahan, Verifikasi)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `580fe9b` | `docs(milestone-1.6): decisions` |
| 2 | `013e2e3` | `feat(milestone-1.6): skema data decomposition` |
| 3 | `0a8d945` | `chore(milestone-1.6): konstanta model klasifikasi/pemecahan/verifikasi` |
| 4 | `a51b03d` | `feat(milestone-1.6): langkah klasifikasi kebutuhan` |
| 5 | `6601c2d` | `feat(milestone-1.6): langkah pemecahan atomik` |
| 6 | `e342b47` | `feat(milestone-1.6): langkah verifikasi pemecahan` |
| 7 | `33a53cf` | `feat(milestone-1.6): orkestrator decompose_question + kebijakan retry` |
| 8 | `dd2670d` | `test(milestone-1.6): skenario uji decomposition dan verifikasi span nyata` |
| 9 | `12e842f`, `630d32b`, `cb72d56` | `docs(evals): rancangan` + `test(evals): eksekusi + payload` + `docs(evals): audit` |
| 10 | *(commit ini)* | `docs(milestone-1.6): logs, report` + `docs: perbarui status project` |

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama.

**Apa yang dilakukan**
14 entri keputusan awal: 3 Jenis A (Qwen3-32B untuk Langkah 4-5, DeepSeek V4 Pro untuk Langkah 6, kebijakan retry maks 3 kali) dan 11 Jenis B (forced/preseden).

**Commit:** `580fe9b`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 2 — `src/schemas/decomposition.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`KlasifikasiKebutuhan`, `RelasiKebutuhan`, `AtomicIntent` (dengan validator konsistensi `relasi`↔`bergantung_pada`), `PemecahanResult`, `VerifikasiResult`, `DecompositionResult`. `LabelBentukJawaban` diimpor dari `session_memory.py` (M1.5), tidak didefinisikan ulang.

**Hasil Verifikasi**
Instansiasi manual: skenario valid (bergantung dengan `bergantung_pada` terisi) berhasil; skenario invalid (bergantung tanpa `bergantung_pada`) ditolak validator dengan pesan jelas.

**Commit:** `013e2e3`

---

## Checkpoint 3 — Konstanta Model

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 3 — `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`OPENROUTER_MODEL_DECOMPOSITION` (Qwen3-32B) dan `OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI` (DeepSeek V4 Pro).

**Commit:** `0a8d945`

---

## Checkpoint 4 — Langkah 4: Klasifikasi Kebutuhan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 4 — `klasifikasi_kebutuhan()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Satu pemanggilan LLM (teks polos, bukan JSON — cuma 1 nilai enum), fallback aman (`majemuk_bergantung`, paling konservatif) untuk kegagalan API/parse.

**Hasil Verifikasi**
Smoke test 3 skenario nyata (satu per nilai enum) — semuanya benar. Span `chat` terverifikasi di Jaeger dengan `decomposition.classification` terisi untuk ketiganya.

**Commit:** `a51b03d`

---

## Checkpoint 5 — Langkah 5: Pemecahan Atomik

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 5 — `pecah_atomik()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
LLM merespons pakai index lokal untuk relasi; kode generate `atomic_intent_id` (UUID4) + bounds-check index lokal (dangling → drop + flag anomali). Parameter `feedback` opsional untuk retry.

**Hasil Verifikasi**
Smoke test skenario "bandingkan Maret dengan Februari" → 3 atomic intent benar (2 independen + 1 bergantung dengan referensi UUID tepat). Span `chat` terverifikasi di Jaeger: `intent.count=3`, `intent.relation_type=["bergantung","independen"]`.

**Commit:** `6601c2d`

---

## Checkpoint 6 — Langkah 6: Verifikasi Pemecahan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 6 — `verifikasi_pemecahan()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
LLM independen kedua (DeepSeek V4 Pro, `reasoning.effort="high"` via `extra_body`), input hanya kalimat asli + hasil struktural Langkah 5 (tanpa reasoning Langkah 5). Parse gagal → `valid=False` (memaksa retry, bukan diam-diam meloloskan).

**Hasil Verifikasi**
Smoke test generate-lalu-verify PENUH pertama di proyek: (a) hasil benar → `valid=True`; (b) hasil sengaja dibuat keliru (kebutuhan perbandingan dihilangkan) → `valid=False` dengan alasan akurat ("Pemecahan tidak mencakup kebutuhan untuk membandingkan..."). Kedua span terverifikasi di Jaeger dengan `model=deepseek/deepseek-v4-pro`.

**Commit:** `e342b47`

---

## Checkpoint 7 — Orkestrator + Kebijakan Retry

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 7 — `decompose_question()`

**Kesesuaian dengan plan:** Sesuai plan, satu penyederhanaan (dicatat di Temuan).

**Apa yang dilakukan**
Alur Klasifikasi (sekali) → Pemecahan → Verifikasi → retry maksimal 3 kali total kalau invalid (feedback disisipkan). `retry_count`/`verifikasi_valid` dikembalikan apa adanya di `DecompositionResult`, tidak disamarkan kalau exhausted.

**Temuan**
Plan menyebut `decomposition.retry_count`/`decomposition.verification_exhausted` sebagai span attribute Langkah 6 — disederhanakan: cukup lewat `DecompositionResult` yang dikembalikan, TIDAK diretrofit ke span (akan butuh ubah signature `verifikasi_pemecahan()` yang sudah teruji). Kontrak observability sendiri cuma mewajibkan `intent.count`/`intent.relation_type`, bukan retry-specific.

**Hasil Verifikasi**
Smoke test end-to-end: skenario "bandingkan Maret dengan Februari" langsung valid di percobaan pertama (`retry_count=0`), 3 span `chat` berurutan terverifikasi di Jaeger.

**Commit:** `33a53cf`

---

## Checkpoint 8 — Test Suite Formal (Kriteria Keberhasilan)

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 8-10 — Skenario, `test_decompose.py`, jalankan

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dua fungsi test: (a) "bandingkan X dengan Y" lewat `decompose_question()` end-to-end, cek relasi bergantung benar-benar merujuk ke kebutuhan independen yang ada; (b) hasil pemecahan sengaja dibuat keliru dipanggil langsung ke `verifikasi_pemecahan()`.

**Hasil Verifikasi**
`uv run pytest tests/layers/decomposition/test_decompose.py -v` → 2/2 passed (117.22s — lambat karena DeepSeek V4 Pro reasoning="high" + kemungkinan retry).

**Commit:** `dd2670d`

---

## Checkpoint 9 — Eval Mendalam

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 11 — `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan. 14 skenario (S01-S14), jumlah tidak dipatok ke angka tertentu sesuai koreksi eksplisit user saat review plan.

**Commit:** `12e842f`

### Task 12 — `run_eval.py` + eksekusi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Reuse `decompose_question()`/`verifikasi_pemecahan()` produksi langsung. Eksekusi 14 skenario berurutan — durasi signifikan (beberapa menit) karena tiap skenario 2-3+ pemanggilan LLM berurutan (hingga 6-9 kalau retry kepicu), DeepSeek V4 Pro reasoning="high" lambat. User sempat menanyakan progres di tengah eksekusi — dijawab dengan mengecek file `payloads/*.json` yang sudah tertulis (bukan cuma menunggu output console ter-buffer) untuk konfirmasi proses berjalan normal, bukan macet.

**Hasil Verifikasi**
14/14 skenario selesai (13 lewat `decompose_question()` + S11 langsung ke `verifikasi_pemecahan()`). 8/13 check otomatis lolos (S13 eksploratif tanpa check).

**Commit:** `630d32b`

### Task 13 — `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Analisis mendalam 5 skenario REVIEW (S05-S08, S14) — dikonfirmasi SEMUANYA temuan nyata (bukan false-negative alat ukur seperti pola M1.3/M1.4). Temuan paling signifikan: `retry_count` di seluruh 13 skenario cuma 0 atau 2 (exhausted), tidak pernah membaik di percobaan tengah.

**Commit:** `cb72d56`

---

## Checkpoint 10 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 14-16 — `logs.md`, `report.md`, `CLAUDE.md`/`AGENT.md`

Entri Checkpoint 1-9 ditulis sebagai bagian Task 14. Lihat `report.md` dan `CLAUDE.md`/`AGENT.md` untuk Task 15-16. Temuan eval (taksonomi `label_bentuk_jawaban`, efektivitas retry) dipromosikan jadi entri baru `docs/keterbatasan-diterima.md` sebagai bagian Task 15.

**Commit:** *(lihat commit gabungan di bawah)*

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada checkpoint baru di luar plan. Penyimpangan: penyederhanaan span retry-attribute Checkpoint 7 (dicatat di atas).

---

## Addendum (2026-08-20) — Fix Guard `response.choices` Kosong/`None` di `klasifikasi_kebutuhan()`

**Ditemukan:** Milestone 7.18, Checkpoint 7 (eksekusi nyata `evals/7.18-database-percakapan/run_eval.py`) — endpoint `POST /v1/turns` crash HTTP 500 dua kali berturut-turut (`session_id` `eval-7.18-e01c`/`eval-7.18-e01d`). Traceback ditangkap lewat pemanggilan manual `uv run python -m uvicorn` (stderr tidak dibuang, beda dari skrip eval yang pakai `DEVNULL`), menunjuk `klasifikasi_kebutuhan()` (`src/layers/decomposition/klasifikasi.py:69`) — `response.choices` bernilai `None`, celah yang sudah lebih dulu terdaftar `docs/keterbatasan-diterima.md` #17 ("3 sub-langkah Decomposition M1.6", ditemukan riset M7.17, sengaja diterima tanpa perbaikan karena belum terbukti nyata).

**Apa yang dilakukan:** Sesuai pemicu peninjauan ulang yang sudah tercatat lebih dulu di entri #17 itu sendiri, `klasifikasi.py` diberi guard `if not response.choices:` sebelum baris indexing — reuse mekanisme fallback aman yang sudah ada (`_FALLBACK = KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG` + span attribute `decomposition.forced_fallback_reason`), tanpa mengubah skema. Detail lengkap keputusan (termasuk kenapa cakupan SENGAJA dibatasi hanya `klasifikasi.py`, bukan seluruh 5 titik #17) di `decisions.md` Keputusan 15 (Addendum). Test baru `tests/layers/decomposition/test_klasifikasi_kegagalan.py` (mocked, mirror pola `test_turn_dependency_kegagalan.py` M1.3) membuktikan fallback bekerja untuk `choices=None` DAN `choices=[]`.

**Hasil Verifikasi**
```
$ uv run pytest tests/layers/decomposition/test_klasifikasi_kegagalan.py -v
test_choices_none_fallback_aman_tanpa_exception_menjalar PASSED
test_choices_kosong_list_fallback_aman PASSED
2 passed in 10.08s
```
Diverifikasi ulang nyata via HTTP: request diagnostik yang sebelumnya crash (payload identik) dijalankan ulang setelah fix — hasil dicatat di `milestones/7.18-database-percakapan/logs.md` Checkpoint 7.

**Dampak lintas-dokumen:** `docs/keterbatasan-diterima.md` #17 diperbarui — titik `klasifikasi.py` ditandai DIPERBAIKI (SEBAGIAN, 4 titik lain tetap AKTIF). `milestones/7.18-database-percakapan/logs.md` mencatat temuan ini ditutup di M1.6 (di sini), bukan di M7.18 sendiri — konsisten prinsip perbaikan logic internal layer jadi tanggung jawab milestone pemilik, mirror pola M7.6 Keputusan 12/Addendum M1.3.

**Commit:** lihat commit `fix(milestone-1.6): ...` di root repo.
