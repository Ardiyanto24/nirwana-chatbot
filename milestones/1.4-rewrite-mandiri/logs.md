# Logs — Milestone 1.4: Membangun Penulisan Ulang Pertanyaan Jadi Mandiri

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `69eb468`, `48f2935` | `docs(milestone-1.4): decisions` + `feat(milestone-1.4): implementasi rewrite mandiri Context Resolution` |
| 2 | `11e8d79` | `test(milestone-1.4): skenario uji rewrite mandiri dan verifikasi span nyata` |
| 3 | `4d81627`, `8f966eb`, `d57c69b`, `f65aec8` | `fix(milestone-1.4): tangani response.choices kosong` + 3 commit eval (`docs`/`test`/`docs`) |
| 4 | *(lihat commit gabungan di bawah)* | `docs(milestone-1.4): logs, report` + `docs: perbarui status project` |

---

## Checkpoint 1 — Keputusan Desain + Mekanisme Rewrite Mandiri

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama sebelum kode apa pun, sesuai instruksi eksplisit user untuk milestone ini (revisi dari pola M1.3).

**Apa yang dilakukan**
11 entri keputusan: 2 Jenis A (genuinely terbuka lewat `AskUserQuestion` + riset web — model Qwen3-32B, pendekatan verifikasi deterministik) dan 9 Jenis B (forced/preseden), seluruhnya dengan "Opsi yang Dipertimbangkan tapi Ditolak".

**Commit:** `69eb468` — `docs(milestone-1.4): decisions`

---

### Task 2 — Buat `src/schemas/rewrite.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`RewriteResult(rewritten_question: str)` — satu field, tanpa `response_format=json_object` (beda M1.3, lihat Keputusan 5).

**Commit:** `48f2935` — `feat(milestone-1.4): implementasi rewrite mandiri Context Resolution`

---

### Task 3 — Tambah `OPENROUTER_MODEL_REWRITE` di `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Konstanta baru `OPENROUTER_MODEL_REWRITE = "qwen/qwen3-32b"`, terpisah dari `OPENROUTER_MODEL` (M1.3). Docstring modul diperluas menjelaskan kedua konstanta model per-langkah.

**Commit:** `48f2935` — `feat(milestone-1.4): implementasi rewrite mandiri Context Resolution`

---

### Task 4-6 — Implementasikan `src/layers/context_resolution/rewrite.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`rewrite_to_standalone(payload) -> RewriteResult`: system+user prompt (histori dilabeli per `turn_index`, mirror `_build_user_prompt` M1.3), `_call_llm()` terpisah (reuse pola M1.3 untuk skrip eval), panggilan teks polos (bukan JSON). Span `chat` mencatat atribut `gen_ai.*` standar. Verifikasi deterministik `_detect_residual_reference()` — scan 14 frasa tetap penanda rujukan sisa (hanya jika `payload.history` non-kosong), murni flag span attribute tanpa mengubah hasil. Fallback ke `payload.question` asli untuk `APIError` atau respons kosong, span attribute `rewrite.forced_fallback_reason`.

**Temuan**
Sanity check `_detect_residual_reference()` tanpa panggilan API: frasa bersih (`"Bandingkan revenue reservasi Maret 2026 dengan revenue reservasi Februari 2026."`) → `[]`; frasa dengan penanda sisa (`"Bagaimana hal itu dibanding tadi?"`) → `['dibanding tadi', 'hal itu']`. Sesuai ekspektasi.

**Commit:** `48f2935` — `feat(milestone-1.4): implementasi rewrite mandiri Context Resolution`

---

### Task 7 — Smoke Test + Verifikasi Span Awal

**Kesesuaian dengan plan:** Sesuai plan, dengan satu insiden infrastruktur di luar kode (lihat Temuan).

**Apa yang dilakukan**
Dua skenario nyata (API call sungguhan, bukan mock): (1) elipsis "satu tahun sebelumnya" dari histori occupancy April 2026, (2) kalimat sudah mandiri tanpa histori.

**Temuan/Insiden**
Percobaan pertama menemukan Docker Desktop engine mengembalikan `500 Internal Server Error` pada seluruh API (`docker info`/`docker ps` gagal) — WSL distro `docker-desktop` sempat menunjukkan status `Stopped` meski proses Docker Desktop berjalan. Restart proses + `wsl --shutdown` + relaunch tidak langsung memperbaiki (masih gagal setelah polling ~270 detik total). User memutuskan restart komputer penuh di luar sesi ini; setelah restart, Docker Desktop berjalan normal dan `infra/observability` (Collector+Jaeger+Prometheus) berhasil di-`docker compose up -d` tanpa masalah lebih lanjut.

**Hasil Verifikasi**
- Skenario 1: `"Bandingkan dengan occupancy satu tahun sebelumnya."` (histori: occupancy April 2026 78%) → `"Bagaimana perbandingan occupancy rate bulan April 2026 dengan occupancy rate bulan April 2025?"` (percobaan pra-restart) — resolusi tahun eksplisit benar.
- Skenario 2: kalimat mandiri diteruskan tanpa distorsi.
- Setelah Docker pulih: kedua skenario diulang, span `chat` dikonfirmasi nyata di Jaeger — `gen_ai.request.model=qwen/qwen3-32b`, `gen_ai.usage.input_tokens`/`output_tokens` terisi angka nyata (373/215 dan 343/218 untuk dua trace berbeda), sesuai kontrak Bagian 2 dokumen observability.

**Commit:** `48f2935` — `feat(milestone-1.4): implementasi rewrite mandiri Context Resolution` (span verification tidak menghasilkan perubahan kode, murni bukti verifikasi)

---

### Task 8a — Catat logs, commit checkpoint

**Apa yang dilakukan**
Dua commit terpisah per kategori: `docs(milestone-1.4): decisions` (Task 1) dan `feat(milestone-1.4): implementasi rewrite mandiri Context Resolution` (Task 2-7).

**Commit:** `69eb468`, `48f2935`

---

## Checkpoint 2 — Test Suite (Kriteria Keberhasilan) + Verifikasi Span Nyata

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 7 (plan) — Susun skenario uji minimal

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dua kelompok sesuai dua Kriteria Keberhasilan sumber: (a) elipsis "satu tahun sebelumnya" butuh histori, (b) kalimat sudah mandiri.

**Commit:** `11e8d79`

---

### Task 8 (plan) — Tulis `tests/layers/context_resolution/test_rewrite.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dua fungsi test, `pytestmark` skip otomatis kalau `OPENROUTER_API_KEY` tidak diset (mirror M1.3). Assertion berbasis substring case-insensitive terhadap entitas kunci (bukan exact match, karena output generatif bebas berbahasa alami).

**Commit:** `11e8d79`

---

### Task 9 (plan) — Jalankan test suite

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv run pytest tests/layers/context_resolution/test_rewrite.py -v`.

**Hasil Verifikasi**
Kedua test **lolos** (2 passed in 25.89s) — panggilan API nyata ke Qwen3-32B, bukan mock.

**Commit:** `11e8d79`

---

### Task 10 (plan) — Verifikasi span nyata di Jaeger

**Kesesuaian dengan plan:** Sesuai plan — verifikasi ini reuse hasil smoke test Checkpoint 1 (skenario identik dijalankan ulang setelah Docker Desktop pulih), tidak diulang terpisah karena `pytest` sendiri tidak memanggil `setup_tracing()` (sama seperti temuan Keputusan 5 M1.3 — pemanggilan langsung non-HTTP tidak otomatis setup tracing).

**Hasil Verifikasi**
Query `GET /api/traces?service=nirwana-chatbot-context-resolution&limit=5` mengembalikan 2 trace, masing-masing span `chat` dengan `gen_ai.operation.name=chat`, `gen_ai.request.model=qwen/qwen3-32b`, token usage terisi angka nyata. Tidak ada `rewrite.residual_reference_detected` pada kedua trace (sesuai ekspektasi — kedua skenario diresolusi bersih tanpa sisa penanda rujukan).

**Commit:** `11e8d79`

---

### Task 10a — Catat logs, commit checkpoint

**Apa yang dilakukan**
Entri Checkpoint 2 ditulis, commit tunggal (Task 7-10 plan bersifat satu unit kerja koheren, tidak dipecah kategori karena semuanya test).

**Commit:** `11e8d79` — `test(milestone-1.4): skenario uji rewrite mandiri dan verifikasi span nyata`

---

## Checkpoint 3 — Eval Mendalam: Skenario di Luar Kriteria Keberhasilan Minimal

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 11 (plan) — Tulis `evals/1.4-rewrite-mandiri/rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
12 skenario (S01-S12) menutup 8 dimensi yang belum diuji di `tests/`: sudah-mandiri-tanpa/dengan-histori-tak-relevan, elipsis eksplisit/implisit × dekat/jauh+distractor, ambiguitas, negasi, sesi panjang (10 turn), pronoun/deiksis, kalimat majemuk campuran, jebakan overlap leksikal. Tiap skenario diberi `required_phrases`/`forbidden_phrases` dan toleransi eksplisit di mana relevan — mirror struktur `evals/1.3-.../rancangan.md`.

**Commit:** `8f966eb`

---

### Task 12 (plan) — Tulis dan jalankan `run_eval.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu perbaikan kode di tengah eksekusi (lihat Temuan/Error).

**Apa yang dilakukan**
Skrip meng-import `_call_llm`, `_build_user_prompt`, `_SYSTEM_PROMPT`, `_detect_residual_reference` langsung dari `rewrite.py` produksi (tidak duplikasi logic). Match dinilai lewat `required_phrases`/`forbidden_phrases` case-insensitive.

**Temuan/Error**
Eksekusi pertama **crash** di skenario S02: `TypeError: 'NoneType' object is not subscriptable` — `response.choices` kosong meski API call sukses (200 OK). Investigasi: dipanggil ulang manual 3× dengan payload S02 identik, seluruhnya sukses normal — **transient**, tidak reproducible dengan payload yang sama (kemungkinan hiccup provider `SiliconFlow` di bawah beban 12 pemanggilan berurutan cepat). Ditemukan juga saat debugging: Qwen3-32B beroperasi mode reasoning/thinking (field `reasoning` panjang di tiap respons, token output jauh lebih tinggi dari perkiraan untuk tugas "ringan" — lihat `audit.md` untuk detail).

**Perbaikan diterapkan** (di luar scope task literal, tapi perlu untuk melanjutkan):
1. `src/layers/context_resolution/rewrite.py`: tambah pengecekan `response.choices` kosong sebelum indexing → fallback ke `payload.question` asli, span attribute `rewrite.forced_fallback_reason="no_choices_in_response"`.
2. `evals/1.4-rewrite-mandiri/run_eval.py`: tambah `_call_with_retry()` (retry sampai 3× kalau `choices` kosong) — terpisah dari fallback produksi yang sengaja fail-fast tanpa retry.

**Hasil Verifikasi**
Eksekusi ulang setelah perbaikan: 12/12 skenario berjalan tanpa error, payload lengkap tersimpan di `payloads/*.json`. 10/12 lolos pencocokan otomatis ketat (`required_phrases`/`forbidden_phrases`) — analisis manual di `audit.md` menyimpulkan 11/12 sebenarnya benar secara makna (S01 false-negative alat ukur), 1 (S07) temuan nyata (recency bias pada kasus ambigu).

**Commit:** `4d81627` (fix), `d57c69b` (eksekusi + payload)

---

### Task 13 (plan) — Tulis `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tabel ringkasan match/mismatch (harness vs manual), analisis mendalam S01 (kegagalan alat ukur) dan S07 (temuan nyata, mereplikasi pola S07 M1.3 lintas model dan lintas tugas), bagian "Temuan Tambahan" (bug transient, mode reasoning Qwen3-32B, heuristic tidak pernah terpicu), "Temuan Pola" (4 poin), "Rekomendasi" (4 poin, termasuk saran metodologi eval untuk milestone generatif berikutnya).

**Commit:** `f65aec8`

---

### Task 13a — Catat logs, commit checkpoint

**Apa yang dilakukan**
Entri Checkpoint 3 ditulis (bagian ini).

**Commit:** *(bagian dari commit gabungan Checkpoint 4, lihat di bawah — logs.md untuk Checkpoint 1-3 seluruhnya ditulis dan di-commit bersama sebagai satu file di Task 14)*

---

## Checkpoint 4 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 14 — Tulis `logs.md`

**Kesesuaian dengan plan:** Sesuai plan (isi dokumen ini sendiri).

---

### Task 15 — Tulis `report.md`

**Kesesuaian dengan plan:** Sesuai plan. Lihat `report.md`.

---

### Task 16 — Perbarui `CLAUDE.md`/`AGENT.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tabel "Struktur Repository" (`src/config/llm.py` dan `src/layers/context_resolution/` diperbarui menyebut M1.4). "Status Saat Ini": M1.4 SELESAI dicatat.

**Hasil Verifikasi**
Konsisten preseden M1.1-1.3: `CLAUDE.md`/`AGENT.md` tidak ikut di-`git add`/commit (gitignored).

**Commit:** Tidak ada commit untuk task ini (disengaja, konsisten preseden).

---

### Task Gabungan (14-15) — Commit checkpoint

**Commit:** *(lihat commit di working tree — `docs(milestone-1.4): logs, report`)*

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada checkpoint baru di luar plan. Penyimpangan task (semuanya koreksi/penyesuaian di dalam task yang sudah direncanakan, dicatat eksplisit di masing-masing entri): insiden Docker Desktop Checkpoint 1 (infrastruktur, di luar kode, diselesaikan lewat restart komputer oleh user); bug `response.choices` kosong + perbaikannya di Checkpoint 3 Task 12.
