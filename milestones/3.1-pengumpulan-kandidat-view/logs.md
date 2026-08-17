# Logs — Milestone 3.1: Pengumpulan Kandidat View

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.1-pengumpulan-kandidat-view/decisions.md`: 13 keputusan (2 Jenis A hasil `AskUserQuestion` dalam sesi perencanaan — mekanisme hybrid BM25+fallback embedding, dan proses perbandingan-empiris 3 model embedding dengan penguncian provisional; 11 Jenis B forced/preseden — termasuk relokasi `DAFTAR_VIEW_PER_DOMAIN` ke `src/config/`), format Jenis A/B + "Opsi yang Dipertimbangkan tapi Ditolak" mirror `milestones/2.4-verification-gate/decisions.md`, ditutup tabel Daftar Isi Keputusan.

**Temuan**
Keputusan 2 (model embedding) sempat direvisi user setelah draft plan pertama diajukan lewat `ExitPlanMode` — user menolak (rejection) karena plan awal secara implisit menutup keputusan model secara permanen pasca-eval; user mengoreksi: model performa tertinggi dipakai sekarang tapi WAJIB dicatat sebagai keputusan tertunda (`docs/keputusan-tertunda.md`), bukan ditutup final. Plan direvisi (Checkpoint 9 baru ditambahkan) sebelum `ExitPlanMode` diajukan ulang dan disetujui.

Draft plan kedua juga sempat ditolak user karena tidak mengikuti `docs/00-project-governance/template-plan-milestone-lengkap.md` secara ketat (section "Keputusan yang Ditanyakan ke User" terlewat, penomoran Task tidak berurutan lintas checkpoint) — plan direvisi ulang mengikuti template persis (Context → Keputusan Desain Turunan → Keputusan yang Ditanyakan ke User → Checkpoint & Task Breakdown dengan Task bernomor 1-26 berurutan → Kriteria Keberhasilan → Commit → Risiko & Mitigasi) sebelum disetujui.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh keputusan di plan yang disetujui (Keputusan Desain Turunan + Keputusan yang Ditanyakan ke User) punya entri `decisions.md` yang sesuai, tidak ada yang diam-diam jadi asumsi implisit.

**Commit:** *(dicatat setelah commit dibuat)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
