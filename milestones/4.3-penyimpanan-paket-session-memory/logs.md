# Logs — Milestone 4.3: Membangun Penyimpanan Paket ke Session Memory

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan.

---

## Checkpoint 1 — Keputusan dan Koreksi Dokumentasi

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/4.3-penyimpanan-paket-session-memory/decisions.md` — 8 keputusan (2 Jenis A genuinely-terbuka hasil diskusi+`AskUserQuestion`: wrapping `nilai_hasil`, cakupan katalog nullable-bermakna; 1 Jenis A ditemukan mid-riset: koreksi referensi M4.5->M4.3; 5 Jenis B forced/preseden).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — konsisten seluruh diskusi sesi ini.

**Commit:** *(pending — digabung Task 2-3)*

### Task 2 — Koreksi Referensi "Milestone 4.5" di M1.5

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditambah anotasi koreksi (blockquote `>`) di titik persis referensi basi muncul — `milestones/1.5-tarik-session-memory/decisions.md` Keputusan 6 dan 7 (2 titik), `report.md` bagian Keterbatasan dan Follow-up (2 titik). Isi asli TIDAK dihapus/ditulis ulang. Docstring `session_memory.py` (bukan dokumen historis) dikoreksi langsung jadi "M4.3".

**Temuan**
Referensi basi ternyata muncul di 5 titik total (bukan 3 seperti perkiraan awal riset): `decisions.md` Keputusan 6+7 (2), `report.md` Bagian 5 (Keterbatasan) + Bagian 6 (Follow-up) (2), `session_memory.py` docstring (1) — sedikit lebih banyak dari estimasi awal, tapi masih dalam cakupan Task 2 yang sama.

**Error/Kegagalan (jika ada)**
Percobaan pertama `Edit` pada `decisions.md` Keputusan 6 GAGAL (`String to replace not found`) — old_string yang disusun dari hasil riset agent sebelumnya sedikit meleset dari teks persis file (heading sebenarnya "## Keputusan 6 (Forced): ..." bukan "## Keputusan 6: ...").

**Diagnosis dan Perbaikan (jika ada error)**
Dibaca ulang file langsung (`Read`) untuk mendapat teks PERSIS, baru `Edit` diulang dengan old_string yang sudah dicocokkan - berhasil.

**Hasil Verifikasi**
Review manual seluruh 5 titik — anotasi konsisten, isi asli M1.5 tetap utuh (append-only untuk dokumen historis, koreksi langsung untuk docstring kode).

**Commit:** *(pending)*

### Task 3 — Entri Baru keterbatasan-diterima.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambah entri #12 (melanjutkan #11 M3.1) — katalog nullable-bermakna M4.3 sebagai subset representatif, bukan transkripsi penuh 67 view, mirror struktur entri #9 (M2.3).

**Error/Kegagalan (jika ada)**
Percobaan pertama `Edit` juga sempat meleset satu kata (`"volume pemakaian model embedding ini berubah"` vs teks asli `"volume pemakaian model embedding berubah"` tanpa kata "ini") — dikoreksi sama seperti Task 2, baca ulang file untuk teks persis sebelum edit kedua.

**Hasil Verifikasi**
Review manual — entri #12 mengikuti format 4 bagian (konteks penemuan, kenapa diterima, dampak+mitigasi, pemicu peninjauan ulang) konsisten entri lain.

**Commit:** *(pending)*

---

*(Checkpoint 2-6 akan ditambahkan progresif setelah masing-masing selesai dan terverifikasi.)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
