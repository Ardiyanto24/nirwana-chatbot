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

## Checkpoint 2 — Span `memory.store` + Penanganan Kegagalan

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — Span + try/except di `store_session_memory()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`store_session_memory()` (`session_memory.py`, file M1.5) dimodifikasi: buka span `memory.store` (tracer `context_resolution.session_memory`, sama dengan `memory.retrieve`), set atribut `session.id`/`turn.index`/`atomic_intent_id` SEBELUM percobaan commit (supaya tetap tercatat meski gagal), bungkus `session.add()+commit()` dalam `try/except Exception`, set `error.type=gagal_teknis` lalu `raise` (bukan exception baru, exception ASLI diteruskan).

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/context_resolution/ -v` — **12/12 lolos**, termasuk `test_kelompok_a_simpan_lalu_ambil_kembali_identik` (M1.5, REAL Supabase) yang TETAP lolos tanpa perubahan assertion — bukti konkret modifikasi `store_session_memory()` tidak merusak perilaku produksi nyata (bukan cuma lolos test mocked).

**Commit:** *(pending)*

### Task 5 — Test Skenario Gagal

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian struktural (dicatat di bawah).

**Apa yang dilakukan**
Test baru `tests/layers/context_resolution/test_session_memory_kegagalan.py`: `_SessionGagal` (fake context manager, `commit()` selalu raise), diverifikasi `error.type=gagal_teknis` tercatat span DAN exception ASLI (bukan exception baru) tetap ter-raise ke pemanggil; test kedua memverifikasi atribut identitas (`session.id`/`turn.index`/`atomic_intent_id`) tercatat span WALAUPUN operasinya gagal (penting untuk korelasi trace ke atomic intent yang gagal disimpan).

**Temuan**
Plan menyebut lokasi test di FILE YANG SAMA (`test_session_memory.py`) — disesuaikan jadi FILE TERPISAH (`test_session_memory_kegagalan.py`). Alasan: `test_session_memory.py` punya `pytestmark = pytest.mark.skipif(not DATABASE_URL)` di level MODUL, yang otomatis berlaku ke SELURUH test dalam file itu, termasuk yang murni mocked. Skenario kegagalan Checkpoint 2 sengaja TIDAK butuh `DATABASE_URL` sama sekali (justru dirancang supaya bisa diverifikasi tanpa DB nyata) - kalau ditaruh di file yang sama, test ini akan ikut ter-skip di environment tanpa `DATABASE_URL`, padahal seharusnya selalu bisa jalan. File terpisah menghindari itu.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
2/2 test baru lolos (bagian dari 12/12 total di atas).

**Commit:** *(pending)*

---

## Checkpoint 3 — Katalog Nullable-Bermakna (Subset Representatif)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6 — `catatan_nullable_bermakna.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dibaca langsung `docs/03-domain-source/katalog-data-chatbot.md` di 3 titik (baris ~300-344, ~490-519, ~405-421) untuk transkripsi PERSIS. `src/config/catatan_nullable_bermakna.py` ditulis dengan 3 pasang view+kolom: `v_lookup_fnb_transactions.guest_id` (baris 332), `v_lookup_maintenance_tickets.room_id` (baris 508), `v_maintenance_ticket_daily.avg_exceeds_sla_threshold` (baris 421) — mencakup 2 domain (fnb, facility), termasuk 1 contoh kolom turunan/agregat (bukan cuma kolom mentah).

**Temuan**
Saat menulis test (Task berikutnya), sempat draft awal berisi 5 pasang (3 kolom untuk `v_lookup_maintenance_tickets` saja) — melebihi cakupan "2-3 pasang" yang disepakati Keputusan 2. Dikoreksi jadi 3 pasang final (buang `resolved_date`/`parts_replaced`) supaya konsisten `decisions.md`/`keterbatasan-diterima.md` yang sudah menyebut angka itu eksplisit.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Test baru `tests/config/test_catatan_nullable_bermakna.py` (4 test): view_name terdaftar valid (cross-check `DAFTAR_VIEW_PER_DOMAIN`); cakupan tetap subset (<10 pasang); **frasa kunci tiap catatan (ditulis ULANG independen di test, bukan copy-paste dari file katalog) benar-benar ditemukan di teks sumber `katalog-data-chatbot.md` pada bagian view yang tepat** — bukti transkripsi tidak melenceng, bukan pengujian sirkular.

**Commit:** *(pending)*

---

*(Checkpoint 4-6 akan ditambahkan progresif setelah masing-masing selesai dan terverifikasi.)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
