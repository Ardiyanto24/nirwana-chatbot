# Logs — Milestone 4.2: Klasifikasi Respons dan Penanganan Kegagalan

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint. Real testing ke `chatbot_api` sungguhan DITUNDA (Keputusan 4) — Checkpoint 1-6 diverifikasi lewat simulasi/mock, konsisten kata Kriteria Keberhasilan sumber sendiri.

---

## Checkpoint 1 — Keputusan dan Dokumentasi Pendukung

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/4.2-klasifikasi-respons-dan-penanganan-kegagalan/decisions.md` berisi 10 keputusan (4 Jenis A genuinely-terbuka, hasil diskusi mendalam dengan user sebelum plan ditulis; 6 Jenis B forced/preseden), mengikuti template resmi.

**Temuan**
Riset mendalam soal "berhasil vs sebagian" (Keputusan 1) mengungkap bahwa `StatusEksekusi.SEBAGIAN` punya makna konsisten di seluruh codebase (proses 2+ langkah, satu gagal teknis) yang tidak pernah eksplisit didokumentasikan sebagai "aturan umum" di satu tempat — hanya tersirat berulang di docstring tiap skema. Ini yang jadi dasar argumen kuat untuk keputusan "selalu berhasil" di M4.2.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review manual — 10 entri decisions.md mencakup seluruh keputusan yang muncul sepanjang diskusi plan (berhasil/sebagian, cakupan 400 Opsi B, real testing ditunda, refactor span, batas retry/revisi, skema, M3.5/M2.4 tak berubah, addendum keputusan-tertunda, workflow Task 1).

**Commit:** *(pending — digabung dengan Task 2-3, lihat bawah)*

---

### Task 2 — Addendum docs/keputusan-tertunda.md #3

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan addendum di entri #3 `docs/keputusan-tertunda.md` — draf usulan kontrak `last_refreshed_at`/`data_quality_status` per view/domain ke tim database engineering (dua field, dua opsi bentuk implementasi, pemicu peninjauan ulang eksplisit).

**Temuan**
Tidak ada temuan baru — draf sudah disiapkan penuh saat diskusi plan (sesi percakapan sebelum implementasi dimulai).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — addendum konsisten dengan draf pesan yang disiapkan di percakapan, ditambahkan sebagai perluasan entri #3 (bukan entri baru), sesuai Keputusan 9.

**Commit:** *(pending — digabung dengan Task 1, 3)*

---

### Task 3 — Cross-reference di milestones/3.4-penyusunan-request/report.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan catatan pasca-milestone di Bagian 6 (Follow-up) `report.md` M3.4 — kontrak `susun_request_atomic_intent()` akan diperluas M4.2 dengan parameter `feedback` opsional, cross-reference ke `decisions.md` M4.2 Keputusan 3.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — catatan ditambahkan tanpa mengubah isi historis report.md yang sudah ada (append, bukan rewrite), konsisten prinsip "jangan menghapus/menyembunyikan sejarah" `CLAUDE.md`.

**Commit:** *(pending)*

---

## Checkpoint 2 — Refactor M4.1: Pisahkan Logic Murni dari Span

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — Ekstrak `_panggil_chatbot_api_raw()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/layers/execution/pemanggilan_chatbot_api.py` direfactor: logic HTTP+parsing murni dipindah ke `_panggil_chatbot_api_raw()` (tanpa span). `panggil_chatbot_api()` publik jadi wrapper tipis yang membuka span `execute_tool`, mendelegasikan ke `_panggil_chatbot_api_raw()`, lalu men-set `http.response.status_code` HANYA kalau `status_code is not None` (kegagalan transport tidak punya status_code untuk dicatat) - perilaku ini identik logic lama.

**Temuan**
Test suite awalnya gagal collect via `python` sistem (`ModuleNotFoundError: opentelemetry.exporter.otlp.proto.grpc`) - ternyata bukan bug refactor, melainkan environment: project punya `.venv` sendiri yang harus dipakai eksplisit (`./.venv/Scripts/python.exe`), bukan `python`/`pip` global.

**Error/Kegagalan (jika ada)**
`ModuleNotFoundError` di atas - murni kesalahan environment (python sistem, bukan `.venv` project), bukan error dari kode yang direfactor.

**Diagnosis dan Perbaikan (jika ada error)**
Diperbaiki dengan menjalankan test lewat `.venv` project (`./.venv/Scripts/python.exe -m pytest`), bukan `python` sistem. Tidak ada perubahan kode untuk mengatasi ini.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/execution/test_pemanggilan_chatbot_api.py -v` — **11/11 test lolos TANPA perubahan assertion** (regresi murni terhadap test yang sudah ada sejak M4.1), termasuk `test_span_execute_tool_mencatat_status_code` yang memverifikasi atribut span tidak berubah.

**Commit:** *(pending — digabung dengan Task 5)*

### Task 5 — Konstanta Retry/Revisi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan `EXECUTION_MAX_RETRY_INFRA = 2`, `EXECUTION_RETRY_DELAY_DETIK = 1.0`, `EXECUTION_MAX_REVISI = 3` ke `src/config/chatbot_api.py`, dengan docstring merujuk `decisions.md` Keputusan 6.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — nilai konsisten dengan Keputusan 6 (mirror `_MAX_ATTEMPTS=3` M1.6).

**Commit:** *(pending)*

---

*(Checkpoint 3-6 akan ditambahkan progresif setelah masing-masing selesai dan terverifikasi.)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
