# Decisions — Milestone 4.3: Membangun Penyimpanan Paket ke Session Memory

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 4.3 — konsumen langsung `HasilEksekusiAtomicIntent` (M4.2, selesai), yang menyusun paket lengkap sesuai skema `SessionMemoryPackage` (M1.5) dan menyimpannya lewat `store_session_memory()`.

---

## Keputusan 1: Pembungkusan `nilai_hasil` List-Shaped ke Field `dict` — `{"rows": [...]}`

**Status:** Diputuskan sebelum implementasi (diskusi + `AskUserQuestion` dengan user).

**Latar Belakang**
`SessionMemoryPackage.nilai_hasil: dict` dikunci M1.5 dari arsitektur §7 (`object` longgar di dokumen arsitektur, diinterpretasikan `dict` oleh M1.5). Data nyata dari `chatbot_api` (dibuktikan M4.1) selalu berbentuk list-of-row (array objek), bukan dict tunggal. M4.3 adalah produsen PERTAMA field ini dengan data nyata (M1.5/M1.7 sebelumnya hanya menyimpan/mengambil data sintetik test) — genuinely terbuka, tidak ada preseden konvensi pembungkusan sebelumnya.

**Keputusan yang Dipilih**
`nilai_hasil` list dibungkus `{"rows": [<row1>, <row2>, ...]}` sebelum masuk `SessionMemoryPackage.nilai_hasil`. Tanpa hasil (status gagal_teknis) dibungkus `{"rows": []}`.

**Alasan**
Key generik netral (`rows`) tidak terikat konteks bisnis spesifik, konsisten dipakai untuk SEMUA `label_bentuk_jawaban` (nilai_tunggal/tren/perbandingan/peringkat/komposisi) — konsumen berikutnya (M4.4 Narasi, M1.7 Pencocokan) bisa membaca `package.nilai_hasil["rows"]` secara seragam tanpa percabangan logic per label.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`{"data": [...]}`** — sama-sama valid secara mekanis, ditawarkan sebagai alternatif eksplisit ke user, tidak dipilih (kurang deskriptif soal bentuk data dibanding "rows").

**Dampak**
M4.4 (Narasi) dan M1.7 (Pencocokan, sudah selesai — perlu dicek ulang saat M4.4 dikerjakan apakah asumsi bentuk `nilai_hasil` di M1.7 konsisten) perlu tahu konvensi `{"rows": [...]}` ini saat membaca `nilai_hasil` dari paket yang ditulis M4.3.

---

## Keputusan 2: Katalog Nullable-Bermakna — Subset Representatif, Bukan Transkripsi Penuh 67 View

**Status:** Diputuskan sebelum implementasi (diskusi + `AskUserQuestion` dengan user).

**Latar Belakang**
`catatan_interpretasi` butuh "pengetahuan yang ditempel" dari pola nullable-bermakna di `katalog-data-chatbot.md` — didokumentasikan sebagai prosa markdown bebas per baris kolom (1000+ baris, 67 view), tidak ada ekstraksi programatik yang bisa diandalkan menangkap MAKNA bisnisnya. Genuinely terbuka: transkripsi penuh vs subset representatif dulu.

**Keputusan yang Dipilih**
Katalog dibangun sebagai subset representatif (2-3 pasang view+kolom), bukan transkripsi penuh 67 view. Dicatat eksplisit provisional di `docs/keterbatasan-diterima.md` (entri baru, Checkpoint 1 Task 3).

**Alasan**
Mirror preseden `docs/keterbatasan-diterima.md` #9 (M2.3: 9 dari sekian view kategori performa-individu, ilustratif bukan daftar tertutup). Transkripsi 1000+ baris prosa bebas di depan tanpa bukti kolom mana yang genuinely sering ditanyakan user berisiko investasi besar bernilai rendah — kolom yang tidak pernah muncul di kebutuhan nyata tidak butuh catatan siap pakai.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Transkripsi PENUH 67 view sekarang** — ditawarkan eksplisit ke user, tidak dipilih: biaya data-entry besar dengan risiko salah transkripsi tinggi untuk kolom yang mungkin tidak pernah relevan.

**Dampak**
Kolom nullable-bermakna yang TIDAK terdaftar katalog akan disimpan TANPA `catatan_interpretasi` — bukan false-positive (salah label), tapi false-negative jujur (tidak tahu, bukan menyamarkan tahu). Dicatat sebagai keterbatasan diterima dengan pemicu peninjauan ulang eksplisit.

---

## Keputusan 3: Fungsi Penyusun Paket Menerima `status`/`nilai_hasil` Eksplisit, Bukan Tipe `HasilEksekusiAtomicIntent` M4.2

**Sumber Paksaan**
Diagram arsitektur (`arsitektur-ai-chatbot-rbac.md` §5) menunjukkan "Simpan paket ke Session Memory" sebagai SATU langkah tunggal yang membungkus SELURUH Fase 2 (Domain Gate reject → Retriever → Query Engine → Verification Gate → Execution) — bukan spesifik Execution/M4.2 saja. Kalau fungsi penyusun paket M4.3 terikat ketat ke tipe `HasilEksekusiAtomicIntent`, pemanggil lain (mis. Domain Gate yang menolak domain, status `ditolak_otorisasi`) tidak akan bisa memakainya tanpa membungkus paksa jadi `HasilEksekusiAtomicIntent` palsu.

**Keputusan yang Diikuti**
`susun_dan_simpan_paket(atomic_intent, session_id, turn_index, status, view_name=None, nilai_hasil=None)` — parameter eksplisit generik, bukan `hasil_eksekusi: HasilEksekusiAtomicIntent`. Testing M4.3 SENDIRI tetap fokus jalur konsumsi M4.2 (sesuai Lingkup literal "menerima hasil terklasifikasi dari Milestone 4.2") — desain generik murni soal ergonomi signature, BUKAN membangun wiring nyata ke Domain Gate/Decomposition (itu di luar cakupan milestone ini).

**Catatan Ketergantungan**
Kalau nanti ada milestone yang secara eksplisit mengonsumsi jalur ditolak_otorisasi/terblokir_ketergantungan, tinggal panggil fungsi yang sama tanpa perlu redesain ulang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fungsi terikat ketat tipe `HasilEksekusiAtomicIntent`** — ditolak: tidak konsisten dengan diagram arsitektur yang menunjukkan satu langkah penyimpanan untuk seluruh Fase 2, bukan spesifik Execution.

---

## Keputusan 4: Lokasi Kode — `src/layers/execution/penyimpanan_paket.py`

**Sumber Paksaan**
`milestones/4.1-membangun-pemanggilan-chatbot-api/decisions.md` Keputusan 6 — subpackage `src/layers/execution/` sengaja dicakupkan untuk M4.1-4.3 sekaligus (preseden struktur `CLAUDE.md`: layer yang mencakup >1 milestone jadi satu subpackage).

**Keputusan yang Diikuti**
File baru `src/layers/execution/penyimpanan_paket.py` di subpackage yang sudah ada (bukan subpackage baru) — tidak perlu update tabel "Struktur Repository" `CLAUDE.md` (file individual baru di subpackage yang sudah tercatat tidak memicu update tabel itu).

**Catatan Ketergantungan**
Tidak ada — murni penempatan file konsisten preseden yang sudah ditetapkan M4.1.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden eksplisit.

---

## Keputusan 5: Span `memory.store` Ditambahkan Langsung di `store_session_memory()` (File M1.5)

**Sumber Paksaan**
Preseden co-location span dengan fungsinya — `retrieve_session_memory()` sudah membuka span `memory.retrieve` LANGSUNG di dalam dirinya sendiri, di file yang sama (`session_memory.py`). M1.5 Keputusan 6 eksplisit menyatakan span "store" BUKAN kontrak yang diwariskan, sengaja ditunda ke "milestone pemanggil produksi" — yang sekarang terkonfirmasi M4.3 (lihat Keputusan 6 di bawah soal koreksi nomor).

**Keputusan yang Diikuti**
`store_session_memory()` (`src/layers/context_resolution/session_memory.py`, file M1.5) dimodifikasi LANGSUNG menambah span `memory.store` (tracer `context_resolution.session_memory`, SAMA dengan `memory.retrieve` — bukan tracer baru), bukan dibungkus dari luar via wrapper di `penyimpanan_paket.py`.

**Catatan Ketergantungan**
Kalau span dibungkus dari luar (bukan di dalam `store_session_memory()`), pemanggil LAIN (non-M4.3, kalau ada di masa depan) yang memanggil `store_session_memory()` langsung tidak akan terinstrumentasi — inkonsisten dengan `retrieve_session_memory()` yang instrumentasinya inherent ke fungsi itu sendiri, bukan tanggung jawab pemanggil.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Span dibuka di `penyimpanan_paket.py` (M4.3), membungkus `store_session_memory()` dari luar** — ditolak: tidak konsisten pola `memory.retrieve` yang instrumentasinya co-located dengan fungsinya sendiri, berisiko pemanggil lain di masa depan lupa membungkus span.

---

## Keputusan 6: Koreksi Referensi "Milestone 4.5" → "Milestone 4.3" di Dokumentasi M1.5

**Status:** Ditemukan di tengah implementasi, Checkpoint 1 (riset sebelum plan ditulis).

**Latar Belakang**
`milestones/1.5-tarik-session-memory/decisions.md` (Keputusan 6, 7) dan `report.md` (Bagian 5, 6) serta docstring `session_memory.py` menyebut "Milestone 4.5 (Execution, pemanggil produksi store)" sebagai milestone yang akan menulis Session Memory produksi. Pada saat M1.5 ditulis (2026-08-15), breakdown resmi PIC 4 (`rancangan-execution-interpretation.md`) mungkin belum sepenuhnya stabil di angka final — faktanya sekarang, dokumen itu eksplisit menamai milestone penyimpanan Session Memory sebagai **4.3** ("Membangun Penyimpanan Paket ke Session Memory"), bukan 4.5 (4.5 adalah "Verifikasi Kesetiaan Data dan Penyusunan Visualisasi", pekerjaan yang sama sekali berbeda).

**Keputusan yang Dipilih**
- `milestones/1.5-tarik-session-memory/decisions.md` dan `report.md`: TIDAK dihapus/ditulis ulang (prinsip "jangan menghapus jejak sejarah", `CLAUDE.md`) — ditambah catatan anotasi eksplisit di tempat referensi basi itu muncul, menyatakan koreksi nomor milestone.
- `src/layers/context_resolution/session_memory.py` (docstring, BUKAN dokumen historis): dikoreksi langsung jadi "Execution, M4.3" — docstring kode boleh diperbaiki langsung karena bukan catatan kronologis keputusan, cukup deskripsi akurat kondisi saat ini.

**Alasan**
Docstring kode yang salah nomor bisa menyesatkan pembaca berikutnya (mis. mencari "M4.5" untuk konteks yang sebenarnya M4.3) — beda dari `decisions.md`/`report.md` yang FUNGSINYA memang mencatat apa yang benar-benar ditulis/dipikirkan saat itu (termasuk kalau ternyata keliru), jadi perlu dipertahankan apa adanya plus anotasi, bukan disunting seolah tidak pernah salah.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menulis ulang `decisions.md`/`report.md` M1.5 seolah selalu benar menyebut "4.3"** — ditolak, melanggar prinsip kejujuran jejak sejarah `CLAUDE.md` eksplisit ("jangan menghapus atau menyembunyikan sejarah error/perubahan arah").

**Dampak**
Pembaca `milestones/1.5-.../decisions.md` dan `report.md` di masa depan akan melihat anotasi koreksi persis di titik referensi basi, tidak perlu menebak-nebak.

---

## Keputusan 7: `store_session_memory()` Tetap `-> None`/Raise-on-Failure, Instrumentasi Murni Tambahan

**Sumber Paksaan**
Tidak ada kontrak baru yang meminta perubahan signature — KK2 M4.3 hanya minta `error.type` tercatat span saat gagal, tidak minta bentuk return value baru. Mengubah signature berisiko memutus pemanggil M1.5/M1.7 yang sudah ada (mengasumsikan `-> None`/exception).

**Keputusan yang Diikuti**
`store_session_memory()` dibungkus `try/except Exception` DI DALAM span: tangkap, set `span.set_attribute("error.type", "gagal_teknis")`, lalu `raise` ulang exception yang sama (bukan exception baru, bukan ditelan). Signature tetap `(package: SessionMemoryPackage) -> None`.

**Catatan Ketergantungan**
Kalau exception ditelan (tidak di-raise ulang), pemanggil (`penyimpanan_paket.py`, M4.3) tidak akan tahu penyimpanan gagal — bertentangan dengan prinsip kejujuran kegagalan teknis `CLAUDE.md`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Return value baru (mis. `bool`/hasil status)** — ditolak, mengubah kontrak M1.5 yang sudah dipakai pemanggil existing tanpa kebutuhan nyata untuk itu.

---

## Keputusan 8: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
`CLAUDE.md` Workflow Wajib, preseden konsisten seluruh milestone sebelumnya.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit `CLAUDE.md`.

---

## Keputusan 9: Revisit — Catatan Kualitas Data (`flagged`/Stale/Tidak Diketahui) Digabung ke `catatan_interpretasi`

**Status:** Ditemukan pasca-milestone (2026-08-17) — turunan langsung dari `milestones/4.2-.../decisions.md` Keputusan 11 (endpoint `_meta` tim database aktif, `SEBAGIAN` diaktifkan di M4.2).

**Sumber Paksaan**
Forced pemisahan tanggung jawab yang sudah dipegang konsisten sejak Checkpoint 3 M4.3 (asli): M4.2 murni menentukan STATUS (`berhasil`/`sebagian`/`gagal_teknis`), teks manusiawi untuk `catatan_interpretasi` adalah domain M4.3 — persis pola nullable-bermakna yang sudah ada. `data_quality_status`/`last_refreshed_at` (diteruskan `HasilEksekusiAtomicIntent` M4.2, Keputusan 11 di sana) genuinely butuh diterjemahkan jadi teks sebelum masuk `catatan_interpretasi`, sama seperti kolom nullable butuh diterjemahkan dari nama kolom mentah.

**Keputusan yang Diikuti**
`susun_dan_simpan_paket()` menerima `data_quality_status`/`last_refreshed_at` opsional. `_catatan_kualitas_data()` (baru) menghasilkan teks BERBEDA NADA untuk 3 kasus: `SEBAGIAN` karena `flagged` (menyebut eksplisit ditandai tim database), `SEBAGIAN` karena stale (menyebut timestamp konkret + ambang yang dipakai), `berhasil` dengan kualitas tidak diketahui (frasa netral "belum diketahui", TIDAK menyiratkan masalah). Hasilnya DIGABUNG (bukan menimpa) dengan catatan nullable-bermakna yang sudah ada — `catatan_interpretasi` tetap satu list.

**Catatan Ketergantungan**
Kalau nada/isi teks salah satu dari 3 kasus disamakan (mis. "tidak diketahui" ditulis dengan nada yang sama alarming-nya dengan "flagged"), itu bertentangan langsung dengan alasan M4.2 Keputusan 11 memisahkan `SEBAGIAN` dari `berhasil+catatan` — kejujuran soal SEBERAPA yakin sistem terhadap suatu sinyal jadi hilang kalau teksnya tidak konsisten dengan status di baliknya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden pemisahan tanggung jawab M4.2/M4.3 yang sudah ada.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Pembungkusan nilai_hasil: {"rows": [...]} | A | Plan |
| 2 | Katalog nullable-bermakna: subset representatif | A | Checkpoint 3 |
| 3 | Fungsi penyusun paket generik, bukan tipe M4.2 ketat | B | Checkpoint 4 |
| 4 | Lokasi kode: src/layers/execution/penyimpanan_paket.py | B | Checkpoint 4 |
| 5 | Span memory.store di dalam store_session_memory() | B | Checkpoint 2 |
| 6 | Koreksi referensi Milestone 4.5 -> 4.3 di dokumentasi M1.5 | A | Checkpoint 1 |
| 7 | store_session_memory() tetap -> None, raise-on-failure | B | Checkpoint 2 |
| 8 | decisions.md Task pertama | B | Plan |
| 9 | Revisit: catatan kualitas data digabung catatan_interpretasi | B | Revisit Checkpoint 1 |
