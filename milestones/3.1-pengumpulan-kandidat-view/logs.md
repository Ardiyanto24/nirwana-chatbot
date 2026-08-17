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

**Commit:** `edf6ee1` — `docs(milestone-3.1): decisions.md keputusan awal`

---

---

## Checkpoint 2 — Relokasi Katalog View ke `src/config/`

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 2 — Pindahkan `DAFTAR_VIEW_PER_DOMAIN`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `src/config/katalog_view.py` (docstring diperluas menjelaskan alasan relokasi + rujukan `decisions.md` Keputusan 3, data `DAFTAR_VIEW_PER_DOMAIN` byte-identik dengan versi lama), update import di `verifikasi_gate.py` dari `src.layers.verification_gate.katalog_view` ke `src.config.katalog_view`, hapus `src/layers/verification_gate/katalog_view.py`.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`grep -rn "from src\.layers\.verification_gate\.katalog_view"` di seluruh repo — nol hasil, tidak ada import lama tersisa.

**Commit:** *(digabung Task 3, lihat di bawah)*

---

### Task 3 — Pindahkan Test ke `tests/config/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `tests/config/__init__.py` dan `tests/config/test_katalog_view.py` (isi sama persis dengan versi lama, hanya import path diubah ke `src.config.katalog_view`), hapus `tests/layers/verification_gate/test_katalog_view.py`.

**Temuan**
`git add` mendeteksi perpindahan file sebagai rename murni (`R src/layers/verification_gate/katalog_view.py -> src/config/katalog_view.py`, `R tests/layers/verification_gate/test_katalog_view.py -> tests/config/test_katalog_view.py`) — bukti tambahan bahwa perubahan ini murni refactor tanpa modifikasi isi substansial.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/verification_gate/ tests/config/ -v` — 25 test lolos (20 test verification_gate sisa + 5 test config pindahan), tanpa perubahan assertion. `CLAUDE.md`/`AGENT.md` diperbarui (baris `src/config/`, `src/layers/verification_gate/`, `tests/`) mencatat relokasi dan folder baru `tests/config/`, disinkronkan identik (`diff` kosong).

**Commit:** `fc9c342` — `refactor(config): relokasi katalog view ke src/config`

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
