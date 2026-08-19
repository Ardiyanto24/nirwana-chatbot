# Logs — Milestone 7.11: Sambungan 6 (Domain Gate → Retriever)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (Plan Mode) menemukan dua gap wiring yang tidak tercakup Lingkup tertulis M7.11 asli (`rancangan-orkestrasi-api.md`): M2.2 (Pemeriksaan Otorisasi) dan M2.3 (Deteksi Cakupan Individu) belum pernah disambungkan `proses_turn()`, meski KK M7.11 sendiri butuh M2.2 dan M7.13 (masa depan) mengasumsikan M2.3 sudah direkam Sambungan 6. Kedua gap diajukan ke user lewat `AskUserQuestion` beserta alternatif dan rekomendasi — user memilih menutup KEDUANYA di dalam M7.11 sendiri (bukan patch M7.10, bukan ditunda ke M7.13). Lokasi kode fungsi batch Retriever baru (`proses_retrieval_semua()`) juga dikonfirmasi: di dalam `src/layers/retriever/kecukupan_struktural.py`, mirror preseden 3x konsisten (`domain_gate.py`/`otorisasi.py`/`cakupan_individu.py`). Menulis `milestones/7.11-sambungan-retriever/decisions.md` — 9 keputusan (3 Jenis A dari hasil `AskUserQuestion`, 6 Jenis B forced by kontrak/preseden).

**Temuan**
Rantai tipe data (`AtomicIntentDomains` → `AtomicIntentAuthorization` → `AtomicIntentConstraint`) sudah dirancang menyatu sejak M2.3 dibangun — docstring `src/schemas/cakupan_individu.py` eksplisit menyebut `domain_decisions` "diteruskan dari M2.2, dibutuhkan Retriever/Query Engine", mengonfirmasi Retriever memang dimaksudkan mengonsumsi output M2.3 (bukan M2.2 langsung).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap dengan 9 entri + Daftar Isi Keputusan, tiap entri Jenis A/B memuat Opsi yang Dipertimbangkan tapi Ditolak sesuai format template resmi.

**Commit:** *(dicatat setelah commit checkpoint ini dibuat)*

---
