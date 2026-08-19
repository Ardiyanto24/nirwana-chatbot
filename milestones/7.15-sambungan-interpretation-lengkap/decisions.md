# Decisions — Milestone 7.15: Sambungan 10 ((Pencocokan jalur "selesai" + Execution) → Interpretation)

Dokumen ini mencatat keputusan desain untuk Milestone 7.15, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Fix identitas paket "selesai" — ekspos `sumber_arsip()` (M1.7) jadi publik, dipakai M7.15 untuk re-key paket

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user via diskusi chat setelah penjelasan konkret, bukan `AskUserQuestion` formal — user minta klarifikasi dulu soal maksud "paket selesai")

**Latar Belakang**
Riset plan menemukan `AtomicIntentMatch.paket` (M1.7, ditahan sejak M7.9 di `KeadaanTurn.matches`) masih membawa `atomic_intent_id` dari TURN ASAL (kapan pertama kali dihitung/dieksekusi) — BUKAN `atomic_intent_id` kebutuhan turn INI (yang dibuat baru setiap kali Decomposition berjalan, walau teks kebutuhannya identik). Interpretation (`susun_narasi()`, M4.4, `narasi.py`) mencocokkan `atomic_intent` ↔ `package` secara KETAT via `atomic_intent_id` (validator internal `_build_user_prompt()` — `ValueError` kalau tidak ketemu pasangannya, "SETIAP atomic_intent sudah punya TEPAT SATU SessionMemoryPackage pasangan"). Kalau `match.paket` dipakai apa adanya, pencocokan akan GAGAL (ValueError) — genuinely terbuka: bagaimana memperbaikinya tanpa mengubah `narasi.py` (di luar batas PIC 7).

**Keputusan yang Dipilih**
`_sumber_arsip()` (private, `src/layers/context_resolution/matching.py`, M1.7) — fungsi 4 baris yang SUDAH menghitung transformasi `sumber` yang benar untuk arsip berantai (Keputusan 7 M1.7: kalau paket lama `sumber="eksekusi_baru"`, arsip baru jadi `"session_memory (turn N)"` dengan N=turn_index paket lama; kalau paket lama SUDAH berupa arsip, nilai dipertahankan utuh) — diganti nama jadi publik `sumber_arsip()` (hapus underscore, TIDAK mengubah isi/logic sama sekali). M7.15 memakainya untuk membangun `SessionMemoryPackage` BARU per match "selesai": `atomic_intent_id`/`session_id`/`turn_index` = turn INI (bukan turn asal), field lain (`teks_kebutuhan`/`label_bentuk_jawaban`/`nilai_hasil`/`catatan_interpretasi`/`status`) disalin utuh dari `match.paket` lama, `sumber` dihitung `sumber_arsip(match.paket)`.

**Alasan**
Ini adalah PERUBAHAN PALING MINIMAL yang mungkin — murni membuka akses ke logic yang SUDAH ada dan SUDAH benar (dibuktikan dipakai `archive_matched_packages()` sejak M1.7), tanpa mengubah perilaku apa pun yang sudah berjalan. Menghindari duplikasi logic (opsi alternatif) yang berisiko drift kalau logic aslinya berubah di masa depan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Duplikasi logic transformasi `sumber` langsung di kode baru M7.15, tanpa sentuh `matching.py`** — dipertimbangkan untuk menjaga batas kepemilikan PIC lebih ketat (M7.15 tidak menyentuh file M1.7 sama sekali), tapi ditolak user: risiko duplikasi kecil (drift kalau logic asli berubah) dinilai lebih besar daripada risiko perubahan penamaan murni yang tidak mengubah perilaku.
- **Ubah `archive_matched_packages()` supaya me-return `list[SessionMemoryPackage]` (arsip yang sudah dibangun) alih-alih `None`** — dipertimbangkan sebagai alternatif tanpa perlu logic terpisah, tapi TIDAK dipilih: `archive_matched_packages()` dipanggil dari `match_and_archive()` (M1.7 orkestrator, sudah tersambung sejak M7.9) yang returnnya `list[AtomicIntentMatch]` — mengubah return value `archive_matched_packages()` tidak otomatis mengalir ke caller M7.15 tanpa JUGA mengubah `match_and_archive()`'s call site di `turn_pipeline.py` M7.9, riak yang lebih besar dan berisiko.

**Dampak**
`milestones/1.7-pencocokan-atomic-intent/decisions.md` mendapat addendum mencatat perubahan ini (mirror preseden M7.6 memperbaiki celah M1.3 di file kepemilikan aslinya, bukan di file M7.6).

---

### Keputusan 2: Item yang tersaring di rantai M7.10-7.14 disurfacekan sebagai paket sintetis, klasifikasi 2 tingkat (RBAC vs teknis generik)

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user via `AskUserQuestion` — user memberi arahan eksplisit untuk kasus RBAC, lalu menyetujui sintesis 2 tingkat untuk sisanya)

**Latar Belakang**
Atomic intent berstatus `perlu_eksekusi` yang tersaring di TENGAH rantai M7.10-7.14 (ditolak SELURUH domain di Domain Gate/Otorisasi, ATAU gagal di Retriever/Query Engine/Verification Gate) TIDAK PERNAH muncul lagi di field `KeadaanTurn` manapun setelah titik penyaringannya. Kalau M7.15 hanya menggabung `matches(status=selesai)` + hasil Execution, item-item ini hilang TOTAL dari narasi turn ini — melanggar prinsip "Kejujuran terhadap keterbatasan" (`CLAUDE.md`, Prinsip Arsitektur: "status non-normal, hasil parsial, penolakan, kegagalan teknis harus selalu tersurat ke user, tidak pernah disamarkan"). Genuinely terbuka: KK M7.15 literal hanya menyebut 2 sumber (selesai + Execution), tidak eksplisit meminta penanganan item tersaring — apakah tetap perlu ditangani sekarang atau didokumentasikan sebagai follow-up terpisah?

**Keputusan yang Dipilih**
M7.15 MENANGANI ini sekarang, dengan klasifikasi 2 tingkat:
1. **Ditolak RBAC**: atomic intent yang di `otorisasi_result`-nya py `domain_decisions` non-kosong DAN SELURUHNYA `diizinkan=False` → paket sintetis `status=DITOLAK_OTORISASI`, `catatan_interpretasi=["Anda tidak memiliki akses untuk data ini sesuai peran Anda."]`.
2. **Kegagalan lain** (Retriever tidak temukan view, Query Engine gagal menyusun/verifikasi, Verification Gate menolak struktural, ATAU Domain Gate sendiri gagal teknis `domain_decisions=[]`/tidak ada entry) → paket sintetis `status=GAGAL_TEKNIS`, `catatan_interpretasi=["Sistem tidak berhasil memproses kebutuhan ini karena kendala teknis."]` — GENERIK, TANPA melacak alasan presisi per-layer.

**Alasan**
Membedakan RBAC dari kegagalan teknis dikonfirmasi eksplisit oleh user ("kalau atomic intent ditolak karena gate/otorisasi maka ini tetap harus diberitahukan ke user 'anda tidak diperkenankan mengakses data ini'"). Klasifikasi generik untuk sisanya menjaga cakupan M7.15 tetap terkendali — melacak alasan presisi butuh menelusuri hingga 5 layer berbeda (Retriever/Query Engine/Verification Gate masing-masing py alasan penolakan sendiri dalam bentuk berbeda), biaya yang tidak sepadan untuk KK yang tidak secara eksplisit memintanya. **Verifikasi menguntungkan yang mengonfirmasi keputusan ini aman diimplementasikan**: `src/prompts/interpretation/narasi.md` (M4.4) SUDAH dirancang generik untuk kelima nilai `StatusEksekusi` sejak awal (Aturan 3 eksplisit soal `ditolak_otorisasi` — "disampaikan jelas dan spesifik", Aturan 4 soal `gagal_teknis` — "jujur TANPA detail teknis internal") — TIDAK perlu mengubah prompt sama sekali; Execution (M4.2) sendiri hanya PERNAH menghasilkan 3 dari 5 nilai (`BERHASIL`/`SEBAGIAN`/`GAGAL_TEKNIS`), M7.15 murni mengisi jalur yang sudah didukung skema+prompt tapi belum pernah dipakai.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tidak menangani sekarang, cukup 2 sumber literal sesuai teks KK** — ditolak user: bertentangan langsung dengan prinsip "Kejujuran terhadap keterbatasan" yang sudah ditegaskan berulang di seluruh project (M4.5, M7.13 report Bagian 6), dan M7.15 adalah titik pertemuan paling natural untuk menutup gap ini (satu-satunya tempat SELURUH nasib atomic intent sebuah turn berkumpul kembali).
- **Klasifikasi generik tunggal untuk SEMUA kegagalan (tanpa membedakan RBAC)** — usulan awal, ditolak user: RBAC butuh pesan SPESIFIK ("tidak memiliki akses"), bukan pesan generik "kendala teknis" yang menyamarkan bahwa ini soal kewenangan, bukan bug sistem.
- **Melacak alasan presisi per-layer untuk kategori "kegagalan lain"** — dipertimbangkan untuk kejujuran maksimal, tapi TIDAK dipilih (untuk sekarang): menambah kompleksitas signifikan (5 sumber alasan berbeda format) tanpa didukung KK eksplisit; `catatan_interpretasi` generik tetap jujur (mengakui kegagalan, tidak menyamarkan sebagai berhasil) walau tidak presisi.

**Dampak**
Paket sintetis TIDAK disimpan ke Session Memory (lihat Keputusan 3) — murni untuk narasi turn ini. `susun_paket_narasi()` (Checkpoint 4) butuh akses ke `otorisasi_result` untuk klasifikasi.

---

### Keputusan 3: Paket sintetis (gap) TIDAK disimpan ke Session Memory

**Sumber Paksaan**
Tidak murni forced — keputusan scope minimal turunan dari Keputusan 2, tapi py alasan struktural kuat: `match_atomic_intents()` (M1.7) memfilter kandidat ke `status=StatusEksekusi.BERHASIL` SAJA sebelum ditawarkan sebagai kandidat cocok (Keputusan 4 M1.7) — walaupun paket gap (`DITOLAK_OTORISASI`/`GAGAL_TEKNIS`) disimpan, ia TIDAK AKAN PERNAH muncul sebagai kandidat match di turn masa depan.

**Keputusan yang Diikuti**
`susun_paket_narasi()` membangun paket sintetis murni in-memory, TIDAK memanggil `store_session_memory()` untuknya.

**Catatan Ketergantungan**
Kalau nanti ada kebutuhan audit historis "kebutuhan apa saja yang pernah gagal", ini perlu direvisit — TIDAK ada bukti kebutuhan ini sekarang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Simpan juga ke Session Memory untuk keperluan audit** — dipertimbangkan, ditolak: tidak ada manfaat fungsional (filter M1.7 membuatnya tidak pernah relevan untuk matching), menambah risiko tanpa keuntungan jelas.

---

### Keputusan 4: `susun_dan_simpan_paket_semua()` (baru) di `src/layers/execution/penyimpanan_paket.py` — PERTAMA KALINYA M4.3 disambungkan ke `proses_turn()`

**Sumber Paksaan**
Preseden lokasi: fungsi batch baru hidup di layer package sendiri (M7.11-7.14, dikonfirmasi konsisten). Kebutuhan wiring: M4.3 (Penyimpanan Paket ke Session Memory) genuinely BELUM PERNAH dipanggil `proses_turn()` sejak M7.6 — gap sejenis dengan M2.2/M2.3 yang ditemukan M7.11 (layer yang sudah matang tapi belum tersambung orkestrator).

**Keputusan yang Diikuti**
`susun_dan_simpan_paket_semua(execution_result, verification_gate_result, session_id, turn_index) -> list[SessionMemoryPackage]` — loop memanggil `susun_dan_simpan_paket()` (M4.3, existing, TIDAK diubah) per item `HasilEksekusiAtomicIntent`, `view_name` dilookup dari `verification_gate_result` (`hasil_vg.request_final.view_name`) via `atomic_intent_id` (mirror pola lookup dict M7.13 Keputusan 7/M7.14 Keputusan 6).

**Catatan Ketergantungan**
Ini adalah PANGGILAN PERTAMA `susun_dan_simpan_paket()` dari orkestrator — sebelumnya hanya diuji standalone (mocked `store_session_memory()`). Efek samping NYATA (tulis DB) sekarang genuinely terjadi tiap kali Execution menghasilkan item.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden lokasi + kebutuhan wiring yang genuinely belum ada.

---

### Keputusan 5: `susun_dan_simpan_paket_semua()` memproses SEMUA status termasuk `GAGAL_TEKNIS` (bukan hanya `BERHASIL`/`SEBAGIAN`)

**Sumber Paksaan**
`HasilEksekusiAtomicIntent` (M4.2) py validator yang mengizinkan `GAGAL_TEKNIS` dengan `nilai_hasil=None` sebagai kondisi VALID (bukan error) — `susun_dan_simpan_paket()` (M4.3) menerima `nilai_hasil: Any = None` sebagai parameter opsional, tidak ada penolakan status tertentu di signature-nya.

**Keputusan yang Diikuti**
Item `GAGAL_TEKNIS` dari Execution TETAP diproses `susun_dan_simpan_paket_semua()` (disimpan ke Session Memory dengan `status=GAGAL_TEKNIS`, `nilai_hasil=None`) — bukan di-skip.

**Catatan Ketergantungan**
Kalau item `GAGAL_TEKNIS` di-skip di sini, hasilnya SAMA seperti item yang tersaring di layer sebelumnya (Keputusan 2 gap) — TAPI `GAGAL_TEKNIS` dari Execution py `kegagalan_alasan` yang lebih presisi (jalur revisi 400/403/404/5xx spesifik M4.2) dibanding gap generik. Menyimpannya via jalur normal (bukan sintetis) mempertahankan presisi ini untuk narasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Skip `GAGAL_TEKNIS` dari Execution, treat sebagai gap seperti Keputusan 2** — ditolak: kehilangan presisi `kegagalan_alasan` M4.2 tanpa alasan kuat, dan `susun_dan_simpan_paket()` sudah dirancang menerima status apa pun tanpa masalah.

---

### Keputusan 6: `susun_paket_narasi()` (baru) di `src/orchestration/paket_narasi.py`

**Sumber Paksaan**
Preseden `src/orchestration/wave.py` (M7.14) — logic yang genuinely lintas-sumber (bukan tanggung jawab satu layer manapun), cukup kompleks (3 kategori penggabungan + klasifikasi gap) untuk butuh test standalone sendiri.

**Keputusan yang Diikuti**
File baru `src/orchestration/paket_narasi.py`, dalam subpackage `src/orchestration/` yang sudah tercatat `CLAUDE.md` — tidak butuh update tabel Struktur Repository.

**Catatan Ketergantungan**
Tidak ada alasan menyimpang dari preseden yang baru dikonfirmasi M7.14.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden.

---

### Keputusan 7: `KeadaanTurn` bertambah `paket_narasi` dan `interpretation`, TANPA skema baru

**Sumber Paksaan**
Preseden M7.6-7.14 (field flat per unit tersambung). `susun_dan_verifikasi_narasi()` (M7.5) sudah mengembalikan tuple 3-elemen TANPA skema baru — mempertahankan bentuk ini konsisten preferensi M7.12-14.

**Keputusan yang Diikuti**
`paket_narasi: list[SessionMemoryPackage]` (hasil gabungan final `susun_paket_narasi()`) dan `interpretation: tuple[HasilNarasi, HasilVerifikasiNarasi, list[DataVisualisasi] | None]` (return `susun_dan_verifikasi_narasi()` apa adanya) — 15 field total, keduanya non-Optional.

**Catatan Ketergantungan**
`atomic_intents` (list kedua yang dikembalikan `susun_paket_narasi()`, dipasangkan 1:1 dengan `paket_narasi`) TIDAK disimpan sebagai field terpisah — bisa didapat ulang via `paket_narasi[i].atomic_intent_id` dicocokkan ke `matches`/`execution`, tidak membawa informasi baru yang perlu diekspos independen.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambah skema baru untuk membungkus hasil `susun_paket_narasi()`** — ditolak: tidak ada kebutuhan, tuple/list polos sudah cukup, konsisten preferensi nol-skema-baru M7.12-14.

---

### Keputusan 8: Span baru `orchestration.susun_paket_narasi` dan `execution.susun_dan_simpan_paket_semua`

**Sumber Paksaan**
Preseden konsisten 7-8x di seluruh project — tiap fungsi `_semua()`/batch baru membuka span pembungkus dengan atribut count.

**Keputusan yang Diikuti**
`execution.susun_dan_simpan_paket_semua`: atribut `intent.count`. `orchestration.susun_paket_narasi`: atribut `paket_narasi.selesai_count`, `paket_narasi.eksekusi_count`, `paket_narasi.gap_rbac_count`, `paket_narasi.gap_teknis_count` — granularitas lebih tinggi dari sekadar `intent.count` karena span ini SENDIRI adalah bukti utama KK M7.15 (butuh terlihat berapa banyak dari tiap kategori).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden + kebutuhan observability KK.

---

### Keputusan 9: `APIError` dari `susun_dan_verifikasi_narasi()` dibiarkan menjalar, tidak dibungkus try/except baru

**Sumber Paksaan**
Preseden M7.5 Keputusan 4-5 — `susun_dan_verifikasi_narasi()` (M4.4/M4.5) SENGAJA tanpa fallback aman, keputusan desain M4.4 sendiri yang sudah final.

**Keputusan yang Diikuti**
`turn_pipeline.py` memanggil `susun_dan_verifikasi_narasi()` apa adanya, tanpa try/except tambahan di M7.15.

**Catatan Ketergantungan**
Konsisten seluruh pola `proses_turn()` — short-circuit alami via exception yang menjalar, bukan ditangkap diam-diam.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by keputusan M7.5 yang sudah final.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Fix re-keying via `sumber_arsip()` publik | A | Plan |
| 2 | Klasifikasi 2 tingkat item tersaring (RBAC vs teknis) | A | Plan |
| 3 | Paket sintetis tidak disimpan DB | B | Plan |
| 4 | `susun_dan_simpan_paket_semua()` di `penyimpanan_paket.py`, pertama kali M4.3 tersambung | B | Plan |
| 5 | Proses semua status termasuk GAGAL_TEKNIS | B | Plan |
| 6 | `susun_paket_narasi()` di `src/orchestration/paket_narasi.py` | B | Plan |
| 7 | Field `paket_narasi`+`interpretation`, tanpa skema baru | B | Plan |
| 8 | Span baru dengan atribut granular | B | Plan |
| 9 | `APIError` menjalar, tidak ditangkap baru | B | Plan |
