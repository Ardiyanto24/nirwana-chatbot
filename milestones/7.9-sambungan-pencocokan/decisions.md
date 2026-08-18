# Decisions — Milestone 7.9: Sambungan 4 ((Decomposition + Tarik Memory) → Pencocokan)

Dokumen ini mencatat keputusan desain untuk Milestone 7.9, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: `match_and_archive()` dipanggil dengan kedua jalur nyata — `session_memory_result or []` untuk kandidat

**Sumber Paksaan**
`match_and_archive(atomic_intents, candidates, session_id, turn_index)` (`src/layers/context_resolution/matching.py`, M1.7) menerima `candidates: list[SessionMemoryPackage]` — BUKAN `Optional`. `KeadaanTurn.session_memory` (M7.7) bertipe `list[...] | None`. Lingkup M7.9 sendiri: "output Decomposition... dan output Tarik Memory... benar-benar keduanya jadi input Pencocokan... bukan salah satu jalur diuji sendirian".

**Keputusan yang Diikuti**
`matches = match_and_archive(decomposition_result.atomic_intents, session_memory_result or [], payload.session_id, payload.turn_index)` di `proses_turn()`.

**Catatan Ketergantungan**
Tanpa konversi `or []`, memanggil `match_and_archive()` dengan `session_memory_result=None` akan TypeError/crash saat Tarik Memory tidak dipanggil — jalur paling umum (turn tanpa referensi).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by signature `match_and_archive()` sendiri.

---

### Keputusan 2: Dipanggil sekuensial setelah Decomposition selesai, bukan paralel baru

**Sumber Paksaan**
Pencocokan genuinely bergantung data pada KEDUA jalur sebelumnya (Decomposition M7.8 DAN Tarik Memory M7.7, yang sudah selesai dari blok `ThreadPoolExecutor`). Lingkup/KK M7.9 tidak menyebut kebutuhan paralelisme baru. Preseden identik M7.8 Keputusan 3 (YAGNI, `CLAUDE.md` "Don't add features... beyond what the task requires").

**Keputusan yang Diikuti**
`match_and_archive()` dipanggil di thread utama, sekuensial, setelah `decomposition_result` final.

**Catatan Ketergantungan**
Memaksakan paralelisme di sini tidak mungkin secara logis (Pencocokan butuh OUTPUT Decomposition sebagai argumen, tidak bisa mulai sebelum Decomposition selesai) — beda dari M7.7 di mana Rewrite dan Tarik Memory genuinely independen satu sama lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced oleh data dependency struktural (Pencocokan butuh hasil Decomposition sebagai parameter).

---

### Keputusan 3: Field `KeadaanTurn.matches: list[AtomicIntentMatch]` non-Optional, TANPA try/except baru di orkestrator

**Sumber Paksaan**
Kalau `proses_turn()` selesai tanpa exception, `match_and_archive()` sudah pasti mengembalikan `list` (`match_atomic_intents()` selalu return list, baik jalur fast-path maupun jalur LLM). TAPI `archive_matched_packages()` (dipanggil di dalam `match_and_archive()`) memanggil `store_session_memory()` (M1.5) yang genuinely raise ulang pada kegagalan DB (`error.type=gagal_teknis` di span, LALU raise apa adanya) — beda dari `rewrite_to_standalone()`/`decompose_question()` (M7.7/M7.8) yang keduanya full-fallback, tidak pernah raise.

**Keputusan yang Diikuti**
`matches: list[AtomicIntentMatch]` (wajib, tanpa default) di `KeadaanTurn`. Panggilan `match_and_archive()` TIDAK dibungkus `try/except` baru di `proses_turn()` — kegagalan DB arsip dibiarkan menjalar apa adanya keluar `proses_turn()`.

**Catatan Ketergantungan**
Preseden identik M7.7: kegagalan cabang paralel (Tarik Memory gagal teknis) dibiarkan menjalar, TIDAK ditangani khusus di level orkestrator — "Kejujuran terhadap keterbatasan" (`CLAUDE.md`) menuntut kegagalan teknis genuinely tersurat, bukan disamarkan lewat fallback yang tidak diminta KK manapun.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Membungkus panggilan `match_and_archive()` dengan `try/except` supaya `matches` selalu terisi meski arsip gagal** — ditolak karena menyembunyikan kegagalan teknis nyata (menyalahi prinsip kejujuran keterbatasan) dan tidak diminta KK M7.9 manapun.

---

### Keputusan 4: Tidak merefactor/mengubah logic internal `match_and_archive()`/sub-fungsinya

**Sumber Paksaan**
"Tidak termasuk" `rancangan-orkestrasi-api.md` — logic internal 9 layer tidak dirombak ulang di M7.x. Preseden identik `milestones/7.2-menyambungkan-decomposition/decisions.md` Keputusan 1, `milestones/7.8-.../decisions.md` Keputusan 5.

**Keputusan yang Diikuti**
`match_and_archive()`, `match_atomic_intents()`, `archive_matched_packages()`, `_match_single()`, `_sumber_arsip()` dipakai apa adanya, tanpa modifikasi.

**Catatan Ketergantungan**
Kode ini sudah diverifikasi bekerja benar dan teruji sejak M1.7 (termasuk rantai arsip ulang turun-temurun) — mengubahnya di M7.9 berisiko meregresi milestone yang sudah closed tanpa alasan bug yang valid.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by batasan dokumen sumber + preseden M7.2/M7.8.

---

### Keputusan 5: Folder `evals/7.9-.../` dengan 6 kejadian (bukan 2) — verdict berbasis status match, bukan required/forbidden phrases

**Sumber Paksaan**
Instruksi eksplisit user untuk milestone ini: real-execution eval WAJIB mencakup seluruh kombinasi kejadian yang mungkin terjadi di titik pertemuan ini, tidak dibatasi 2 seperti preseden M7.6-M7.8. Preseden struktur folder `evals/` sebagai default Level 2 (M7.8 Keputusan 1). KK M7.9 soal STATUS match yang benar (closed-space: `selesai`/`perlu_eksekusi`) — beda dari KK M7.8 yang soal konten teks bebas, sehingga proxy pengujian yang tepat juga berbeda: cek langsung nilai `status`/`paket` per atomic_intent, bukan `required_phrases`/`forbidden_phrases`.

**Keputusan yang Diikuti**
6 kejadian (E01-E06, lihat plan "Peta Kombinasi Kejadian") — dipilih dari analisis ruang kejadian nyata (2 dimensi: state Tarik Memory × bentuk Decomposition), bukan jumlah sembarang. Tiap kejadian diverifikasi lewat nilai `status` aktual hasil `match_and_archive()`, dibandingkan ekspektasi yang ditetapkan di `rancangan.md` sebelum eksekusi.

**Catatan Ketergantungan**
Membatasi ke 2 kejadian (preseden M7.6-M7.8) akan meninggalkan beberapa state penting tidak teruji lewat pipeline nyata (mis. filter internal `status≠berhasil`, anti false-positive, granularitas per-intent pada Decomposition majemuk) — bertentangan langsung dengan instruksi eksplisit user.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **2 kejadian saja (match vs no-match), mirror preseden M7.6-M7.8** — ditolak eksplisit oleh instruksi user ("tidak harus 2").
- **Cartesian product penuh seluruh kombinasi state (termasuk kombinasi yang mekanis identik, mis. "tidak dipanggil + majemuk")** — ditolak karena tidak menambah bukti baru (jumlah atomic_intent tidak mengubah MEKANISME fast-path), sekadar duplikasi kerja tanpa nilai tambah.

---

### Keputusan 6: Seeding data "turn sebelumnya" via `store_session_memory()` manual di `run_eval.py`

**Sumber Paksaan**
Execution (M4.x) belum disambungkan ke `proses_turn()` (ditunda ke M7.1x, belum dikerjakan) — `session_memory_packages` di Supabase tidak terisi secara organik lewat pipeline. Preseden identik M1.7 (`milestones/1.7-pencocokan-atomic-intent/decisions.md` Keputusan 13, `report.md` Bagian 5: "Verifikasi memakai data seed manual... disepakati EKSPLISIT dengan user sebelum plan ditulis").

**Keputusan yang Diikuti**
`run_eval.py` py helper `_seed_turn_sebelumnya()` yang memanggil `store_session_memory()` manual untuk membangun data "turn sebelumnya" (mensimulasikan seolah Execution sudah pernah menghitung dan menyimpannya), dipakai kejadian E03-E06. Data yang diuji SENDIRI (atomic_intents dari Decomposition, kandidat hasil `retrieve_session_memory()` untuk turn SAAT INI) tetap 100% dari pipeline nyata — yang disuntik manual murni prasyarat historis, bukan hasil kedua jalur yang sedang dibuktikan M7.9.

**Catatan Ketergantungan**
Tanpa seeding ini, tidak mungkin membangun kondisi "kandidat status=berhasil tersedia" (E03/E04/E06) atau "kandidat status≠berhasil" (E05) secara nyata — satu-satunya alternatif adalah memanggil `match_and_archive()` langsung dengan `SessionMemoryPackage` buatan tangan, yang justru melanggar KK M7.9 literal ("bukan data buatan yang disusun manual menyerupai output kedua jalur itu").

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Membangun Execution minimal di M7.9 supaya data organik** — ditolak, jauh di luar Lingkup M7.9 (Execution adalah PIC 7 milestone lain jauh ke depan, M7.1x).
- **`SessionMemoryPackage` buatan tangan langsung dipassing ke `match_and_archive()` tanpa lewat `store_session_memory()`+`retrieve_session_memory()`** — ditolak karena melanggar KK M7.9 literal (jalur Tarik Memory HARUS genuinely dari `retrieve_session_memory()` nyata, bukan data yang menyerupai outputnya).

---

### Keputusan 7: 3 test existing di `tests/orchestration/test_turn_pipeline.py` ditambah mock `match_and_archive`

**Sumber Paksaan**
Docstring file itu sendiri: "Cakupan SEMPIT... hanya kejadian yang TIDAK butuh LLM/DB/Jaeger nyata" (preseden M7.6 Keputusan 8, M7.7 Keputusan 7, M7.8 Keputusan 6). Begitu `proses_turn()` memanggil `match_and_archive()` sungguhan (M7.9), ketiga test lama akan memicu panggilan LLM+DB nyata tanpa disadari.

**Keputusan yang Diikuti**
Ketiga test existing ditambah `monkeypatch.setattr(turn_pipeline_module, "match_and_archive", lambda *a, **k: [])`.

**Catatan Ketergantungan**
Tanpa perubahan ini, test suite yang seharusnya cepat/deterministik diam-diam jadi bergantung jaringan+API key+DB, berisiko flaky/lambat tanpa terlihat dari nama test-nya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by docstring cakupan file + preseden M7.7/M7.8.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | `match_and_archive()` dipanggil dengan `session_memory_result or []` | B | Plan |
| 2 | Dipanggil sekuensial, bukan paralel baru | B | Plan |
| 3 | Field `matches` non-Optional, tanpa try/except baru | B | Plan |
| 4 | Tidak merefactor `match_and_archive()` internal | B | Plan |
| 5 | Folder `evals/` dengan 6 kejadian, verdict berbasis status | B | Plan |
| 6 | Seeding turn sebelumnya via `store_session_memory()` manual | B | Plan |
| 7 | 3 test existing ditambah mock `match_and_archive` | B | Plan |
