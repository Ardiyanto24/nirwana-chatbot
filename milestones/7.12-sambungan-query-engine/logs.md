# Logs — Milestone 7.12: Sambungan 7 (Retriever → Query Engine)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (Plan Mode) menemukan bahwa Query Engine (M3.4-3.5) sudah tersambung internal penuh sejak M7.4 dan tidak py gap tersembunyi seperti M7.11 (M2.2/M2.3) — tapi layer-nya sama sekali tidak py fungsi batch level-list untuk gabungan Langkah 1+2 (`susun_dan_verifikasi_request_atomic_intent()` M7.4 cuma per-item). Satu keputusan genuinely terbuka diajukan ke user lewat `AskUserQuestion`: bentuk field `KeadaanTurn.query_engine` — pertahankan tuple `list[tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]]` apa adanya (dikonfirmasi user, setelah dijelaskan tidak ada blocker teknis) vs bungkus skema baru bernama. Menulis `milestones/7.12-sambungan-query-engine/decisions.md` — 9 keputusan (1 Jenis A dari `AskUserQuestion`, 8 Jenis B forced by kontrak/preseden, termasuk preseden SAMA-FOLDER `verifikasi_bentuk_request_semua()` yang memperkuat pola batch-wrapper M7.11).

**Temuan**
Ditemukan perbedaan prinsip penting dari M7.11: item Retriever dengan `view_name_final=None` WAJIB di-skip (forced by signature `view_name: str` non-Optional `susun_request_atomic_intent()`), BEDA dari M7.11 Keputusan 7 (Retriever sengaja tidak memfilter karena callee-nya terbukti aman menerima input kosong). Dicatat eksplisit sebagai Keputusan 4 supaya tidak disamakan keliru dengan preseden M7.11.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap dengan 9 entri + Daftar Isi Keputusan, format Jenis A/B sesuai template resmi.

**Commit:** *(dicatat di commit berikutnya)*

---
