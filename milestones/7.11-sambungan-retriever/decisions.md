# Decisions — Milestone 7.11: Sambungan 6 (Domain Gate → Retriever)

Dokumen ini mencatat keputusan desain untuk Milestone 7.11, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Gap M2.2 (Pemeriksaan Otorisasi belum tersambung) ditutup di dalam M7.11 sendiri

**Status:** Diputuskan sebelum implementasi (dari plan)

**Latar Belakang**
Riset plan menemukan `periksa_otorisasi_semua()` (M2.2, `src/layers/domain_gate/otorisasi.py`) — kode sudah ada dan teruji sejak milestone aslinya — belum pernah dipanggil `proses_turn()`. Lingkup M7.11 sendiri (`rancangan-orkestrasi-api.md` baris 120-122) berasumsi "hasil Domain Gate Sambungan 5" (M7.10) sudah berupa "daftar domain yang lolos otorisasi", padahal M7.10 hanya menyambungkan `identifikasi_domain_semua()` (M2.1, identifikasi semantik murni, tanpa otorisasi). Ditelusuri ke seluruh 11 Sambungan Level 2 (M7.6-7.16) — tidak ada satu pun yang punya M2.2 sebagai tugas eksplisitnya. Ini genuinely terbuka: tidak ada dokumen yang secara eksplisit menyatakan siapa yang menyambungkan M2.2, dan pilihan penempatan (di M7.11 vs patch M7.10) berdampak material pada di mana kode+jejak keputusan hidup.

**Keputusan yang Dipilih**
M7.11 menyambungkan `periksa_otorisasi_semua()` sebagai bagian dari checkpoint-nya sendiri (Checkpoint 2-3), sebelum checkpoint Retriever. M7.10 tidak dibuka kembali.

**Alasan**
M7.11 adalah satu-satunya milestone yang genuinely butuh "domain yang lolos otorisasi" untuk KK-nya sendiri bisa dibuktikan — kalau bukan M7.11, tidak ada milestone lain yang akan menyambungkannya (kode `periksa_otorisasi_semua()` akan tetap jadi kode mati selamanya). Ini juga bukan bug internal M2.2 yang perlu di-patch di folder pemiliknya (beda dari preseden M1.3/M1.5 yang diperbaiki M7.6/M7.7 karena itu memang bug logic internal layer) — ini murni koneksi yang memang belum pernah dibangun, dan menyambungkan koneksi yang belum ada persis tugas milestone Level 2.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Patch M7.10 dulu (reopen `milestones/7.10-.../decisions.md` dengan addendum), baru mulai M7.11** — ditolak: M7.10 sudah closed dan ter-commit dengan Lingkup/KK sendiri yang scope-nya secara eksplisit hanya soal filter status (`perlu_eksekusi` vs `selesai`), bukan soal otorisasi — memaksakan otorisasi masuk ke M7.10 secara retroaktif tidak konsisten dengan Lingkup asli milestone itu sendiri, dan preseden M7.6/M7.7 (perbaikan bug internal di folder pemilik) tidak cocok diterapkan di sini karena sifat masalahnya beda (koneksi belum ada, bukan bug logic).

**Dampak**
`proses_turn()` dan `KeadaanTurn` bertambah 1 langkah baru (field `otorisasi`). `report.md` M7.11 wajib mencatat eksplisit bahwa milestone ini menutup gap di luar Lingkup tertulis aslinya, supaya tidak menyamarkan penyimpangan dari dokumen sumber.

---

### Keputusan 2: Gap M2.3 (Deteksi Cakupan Individu belum tersambung) juga ditutup sekarang di M7.11, tidak ditunda ke M7.13

**Status:** Diputuskan sebelum implementasi (dari plan)

**Latar Belakang**
Pola yang sama seperti Keputusan 1 ditemukan untuk unit berbeda: `deteksi_constraint_semua()` (M2.3, `src/layers/domain_gate/cakupan_individu.py`) juga belum pernah tersambung. Bedanya, kali ini ditemukan **bukti tekstual dari milestone masa depan**: M7.13 (Sambungan 8: Query Engine → Verification Gate, baris 134) menyebut *"constraint cakupan-individu yang **dicatat Domain Gate (Sambungan 6)**"* — mengasumsikan M2.3 sudah direkam M7.11, padahal Lingkup/KK M7.11 sendiri (baris 120-124) tidak menyebut cakupan-individu sama sekali. Genuinely terbuka: menyambungkan sekarang (scope-creep M7.11 dari 2 jadi 3 unit wiring) vs menunda eksplisit ke M7.13 (risiko M7.13 nanti menemukan gap yang sama, mengulang proses investigasi ini).

**Keputusan yang Dipilih**
M7.11 SEKALIAN menyambungkan `deteksi_constraint_semua()` (Checkpoint 4-5), bukan ditunda sebagai follow-up eksplisit untuk M7.13.

**Alasan**
Dipilih user secara sadar setelah trade-off dijelaskan: mencegah M7.13 nanti mengulang proses gap-discovery yang sama (audit kode + telusur seluruh milestone Level 2) untuk unit yang berbeda tapi pola identik. Konsekuensinya diterima secara sadar: M7.11 kini mencakup 3 unit wiring, bukan 1 — dimitigasi lewat checkpoint granular (lihat `plan` Checkpoint 4-5 terpisah dari 2-3 dan 7-8).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Biarkan untuk M7.13 menangani sendiri saat gilirannya tiba** — sempat direkomendasikan (M7.11 tetap ketat sesuai Lingkup/KK tertulisnya sendiri, gap dicatat eksplisit di `report.md` sebagai follow-up) tapi ditolak user demi mencegah pengulangan gap-discovery yang sama.

**Dampak**
`KeadaanTurn` bertambah field `cakupan_individu`. `report.md` M7.11 dan M7.13 (nanti) wajib saling merujuk — M7.13 tidak perlu lagi audit ulang keberadaan M2.3 di titik ini, cukup mengonsumsi `KeadaanTurn.cakupan_individu` yang sudah tersedia.

---

### Keputusan 3: Fungsi batch baru Retriever (`proses_retrieval_semua()`) ditempatkan di `src/layers/retriever/kecukupan_struktural.py`, bukan inline di `turn_pipeline.py`

**Status:** Diputuskan sebelum implementasi (dari plan)

**Latar Belakang**
Layer Retriever (M3.1-3.3) tidak punya fungsi batch level-list — hanya `proses_retrieval_atomic_intent()` per-item. Genuinely terbuka: menambah fungsi baru di dalam package layer Retriever sendiri (mirror pola `identifikasi_domain_semua()`/`periksa_otorisasi_semua()`/`deteksi_constraint_semua()`, yang semuanya hidup di layer masing-masing) vs menulis loop pemanggilan langsung inline di `turn_pipeline.py` tanpa fungsi baru bernama di layer Retriever.

**Keputusan yang Dipilih**
Fungsi baru `proses_retrieval_semua(daftar_constraint: list[AtomicIntentConstraint]) -> list[HasilKecukupanStruktural]` ditambahkan di `src/layers/retriever/kecukupan_struktural.py`.

**Alasan**
Preseden 3x konsisten dan independen (domain_gate.py M2.1, otorisasi.py M2.2, cakupan_individu.py M2.3 — tiga milestone berbeda yang masing-masing sampai pada pola desain yang sama) cukup kuat untuk dianggap konvensi arsitektur de facto proyek ini: tiap layer memiliki wrapper batch-nya sendiri, `turn_pipeline.py` tetap murni wiring tipis (memanggil fungsi "_semua()" yang sudah ada, bukan mengandung logic batching sendiri). Menyimpang dari pola ini di Retriever tanpa alasan kuat akan membuat satu layer terlihat inkonsisten dari tiga layer lain yang sudah established.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Inline langsung sebagai loop di `turn_pipeline.py`** — dipertimbangkan dengan alasan "tidak menambah kode baru ke package layer yang sudah 'selesai' (M3.1-3.5)", tapi ditolak karena menyimpang dari preseden konsisten 3x tanpa alasan teknis kuat, dan akan membuat `turn_pipeline.py` mengandung logic derive `domain_diizinkan` dari `domain_decisions` yang lebih pas hidup di layer Retriever sendiri (dekat dengan tipe data yang dikonsumsinya).

**Dampak**
`src/layers/retriever/kecukupan_struktural.py` bertambah satu fungsi publik baru. Tidak ada dampak lintas-pekerjaan lain — murni penambahan kapabilitas, bukan perubahan pada fungsi existing manapun di layer ini.

---

### Keputusan 4: Rantai pemanggilan sekuensial `identifikasi_domain_semua()` → `periksa_otorisasi_semua()` → `deteksi_constraint_semua()` → `proses_retrieval_semua()`

**Sumber Paksaan**
Signature masing-masing fungsi: `periksa_otorisasi_semua(atomic_intent_domains_list: list[AtomicIntentDomains], role_title: str)` menerima persis tipe output `identifikasi_domain_semua()`; `deteksi_constraint_semua(atomic_intent_authorization_list: list[AtomicIntentAuthorization], role_title: str)` menerima persis tipe output `periksa_otorisasi_semua()`. Docstring `src/schemas/cakupan_individu.py` baris 10-13 eksplisit menyebut `AtomicIntentConstraint.domain_decisions` "diteruskan dari M2.2, dibutuhkan Retriever/Query Engine" — mengonfirmasi rantai ini memang dirancang menyatu sejak M2.3 dibangun.

**Keputusan yang Diikuti**
Empat pemanggilan dieksekusi sekuensial (bukan paralel) di `proses_turn()`, tiap langkah menerima output langkah sebelumnya sebagai argumen pertamanya.

**Catatan Ketergantungan**
Tidak ada paralelisme yang mungkin secara logis di sini — tiap langkah genuinely butuh OUTPUT langkah sebelumnya sebagai argumen (data dependency searah murni), sama seperti preseden M7.8/M7.9/M7.10.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced oleh data dependency struktural + signature fungsi yang sudah final.

---

### Keputusan 5: `role_title` diambil dari `payload.role_title`, tidak ada field payload baru

**Sumber Paksaan**
`TurnPayload.role_title` (`src/schemas/turn_payload.py` baris 30) sudah tervalidasi (`field_validator role_title_must_be_known`) sejak Input Layer (M1.2). `periksa_otorisasi_semua()` dan `deteksi_constraint_semua()` sama-sama butuh parameter `role_title: str`.

**Keputusan yang Diikuti**
`payload.role_title` diteruskan langsung ke `periksa_otorisasi_semua(otorisasi_input, payload.role_title)` dan `deteksi_constraint_semua(cakupan_input, payload.role_title)`.

**Catatan Ketergantungan**
Tidak ada sumber `role_title` lain yang valid di titik ini — `payload` adalah satu-satunya tempat data pemanggil (role, employee_id) tersedia di seluruh alur `proses_turn()`.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kontrak `TurnPayload` yang sudah final sejak M1.2.

---

### Keputusan 6: `KeadaanTurn` bertambah 3 field baru (`otorisasi`, `cakupan_individu`, `retriever`), seluruhnya non-Optional

**Sumber Paksaan**
Preseden konsisten M7.6-7.10: tiap unit yang disambungkan dapat field sendiri di `KeadaanTurn`, dipertahankan untuk observability/downstream (bukan dihilangkan setelah dikonsumsi langkah berikutnya). Dibaca langsung kode: `periksa_otorisasi_semua()`/`deteksi_constraint_semua()` murni deterministik tanpa jalur gagal-total (tidak pernah raise — lookup role_permissions/pre-filter role-domain, bukan panggilan LLM yang bisa gagal teknis di level fungsi ini). `proses_retrieval_atomic_intent()` per item juga "tidak pernah gagal teknis di level kebutuhan-atomik" (`kecukupan_struktural.py` baris 306, docstring eksplisit "status selalu BERHASIL").

**Keputusan yang Diikuti**
`otorisasi: list[AtomicIntentAuthorization]`, `cakupan_individu: list[AtomicIntentConstraint]`, `retriever: list[HasilKecukupanStruktural]` — ketiganya wajib tanpa default, mirror pola `domain_gate`/`matches`/`decomposition` (bukan pola `session_memory` yang `| None` karena genuinely kondisional dipanggil).

**Catatan Ketergantungan**
Panjang ketiga list ini bisa mengecil secara bertahap sepanjang rantai (`otorisasi`/`cakupan_individu` melewati entri `GAGAL_TEKNIS` M2.1 yang sudah difilter `periksa_otorisasi_semua()` secara internal) — bukan indikasi kegagalan wiring, murni desain filter yang sudah ada di masing-masing fungsi sejak milestone aslinya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M7.6-7.10 + bukti langsung kode ketiga fungsi yang dipanggil.

---

### Keputusan 7: Tidak ada filter/skip tambahan oleh orkestrator di titik manapun dalam rantai baru ini

**Sumber Paksaan**
Preseden Keputusan 1 M7.10 (menolak opsi "orkestrator memfilter duluan" karena duplikasi logic yang sudah ada di fungsi layer). Dikonfirmasi lewat pembacaan kode `_kumpulkan_kandidat()`/`evaluasi_kecukupan_struktural_atomic_intent()`: item dengan `domain_diizinkan=[]` (seluruh domain ditolak otorisasi untuk satu atomic intent) mengalir natural ke `cari_bm25(teks, [])` → 0 kandidat → `evaluasi_kecukupan_struktural_atomic_intent()` dengan `kandidat_dievaluasi=[]` → `view_name_final=None` (dari `_pilih_view_name_final([])`), `status=BERHASIL` — tidak crash, tidak butuh percabangan khusus.

**Keputusan yang Diikuti**
`proses_retrieval_semua()` (baru) memproses SELURUH item `list[AtomicIntentConstraint]` yang diterimanya apa adanya, termasuk yang `domain_diizinkan` hasil derive-nya kosong — dibiarkan mengalir ke `proses_retrieval_atomic_intent(atomic_intent, [])` tanpa pengecualian.

**Catatan Ketergantungan**
Memfilter/skip di level orkestrator akan menduplikasi logic yang seharusnya jadi tanggung jawab Retriever sendiri memutuskan (apakah domain kosong berarti "tidak ada yang bisa dicari" — itu keputusan Retriever, bukan orkestrator) — juga berisiko KK M7.11 sendiri ("tidak ada kandidat dari domain yang ditolak muncul") jadi trivial-dibuktikan-dengan-cara-salah (dibuktikan lewat skip, bukan lewat mekanisme filter domain yang sesungguhnya di `_kumpulkan_kandidat()`).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Orkestrator skip pemanggilan Retriever untuk item dengan `domain_diizinkan=[]`** — ditolak: `proses_retrieval_atomic_intent()` sudah terbukti aman menangani domain kosong (tidak crash, hasil jujur `view_name_final=None`), skip di level orkestrator hanya menambah percabangan tanpa manfaat, dan berisiko duplikasi logic (preseden Keputusan 1 M7.10).

---

### Keputusan 8: `cakupan_individu.terdeteksi` tidak memengaruhi apakah Retriever dipanggil

**Sumber Paksaan**
`rancangan-rbac-authorization.md` baris 76: constraint cakupan-individu murni "dicatat" (bukan ditegakkan) di titik M2.3 — penegakan sesungguhnya (termasuk kemungkinan menahan/mengoreksi request) terjadi belakangan di Verification Gate (M2.4, disambungkan M7.13). Retriever (M3.1-3.3) tidak pernah didesain untuk menerima/memproses sinyal constraint cakupan-individu di dokumen manapun.

**Keputusan yang Diikuti**
`proses_retrieval_semua()` memproses seluruh item `list[AtomicIntentConstraint]` tanpa membaca field `constraint` sama sekali — hanya `atomic_intent` dan `domain_decisions` yang dipakai.

**Catatan Ketergantungan**
Mencoba menegakkan constraint cakupan-individu di titik ini (mis. menahan Retriever untuk item `terdeteksi=True`) akan mendahului tanggung jawab Verification Gate (M2.4) yang belum tersambung (M7.13) — melanggar pemisahan deteksi/penegakan yang eksplisit didesain dokumen sumber.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by pemisahan deteksi/penegakan yang eksplisit di `rancangan-rbac-authorization.md`.

---

### Keputusan 9: `proses_retrieval_semua()` membuka span pembungkus dengan atribut `intent.count`, tracer sama dengan `proses_retrieval_atomic_intent()`

**Sumber Paksaan**
Pola konsisten pada SELURUH fungsi `_semua()` existing di proyek ini: `domain_gate.identifikasi_semua` (M2.1), `domain_gate.periksa_otorisasi_semua` (M2.2), `domain_gate.deteksi_constraint_semua` (M2.3) — ketiganya membuka span pembungkus dengan atribut `intent.count` sebelum memproses list. `nilai_kecocokan_makna_semua()` (M3.2) juga dikonfirmasi "mirror struktur domain_gate.identifikasi_domain_semua()" lewat docstringnya sendiri.

**Keputusan yang Diikuti**
`proses_retrieval_semua()` membuka span baru (nama mengikuti pola `retriever.proses_semua`) di tracer `retriever.retriever` (`_RETRIEVER_TRACER_NAME`, sama dengan yang dipakai `proses_retrieval_atomic_intent()`), set atribut `intent.count` sebelum loop pemanggilan per-item.

**Catatan Ketergantungan**
Tidak ada atribut lain yang perlu ditambahkan di span pembungkus ini — kontrak observability Retriever (`retrieval.candidates_count`, `retrieval.selected_view`) sudah terpenuhi di span anak (`retriever.cari_kandidat_view`) yang dibuka `proses_retrieval_atomic_intent()` per item.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by pola konsisten 4x preseden (M2.1, M2.2, M2.3, M3.2).

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Gap M2.2 ditutup di dalam M7.11 sendiri | A | Plan |
| 2 | Gap M2.3 juga ditutup sekarang di M7.11 | A | Plan |
| 3 | Fungsi batch Retriever baru di `kecukupan_struktural.py` | A | Plan |
| 4 | Rantai pemanggilan sekuensial M2.1→M2.2→M2.3→Retriever | B | Plan |
| 5 | `role_title` dari `payload.role_title` | B | Plan |
| 6 | 3 field baru `KeadaanTurn`, non-Optional | B | Plan |
| 7 | Tidak ada filter/skip tambahan orkestrator | B | Plan |
| 8 | `cakupan_individu.terdeteksi` tidak memengaruhi panggilan Retriever | B | Plan |
| 9 | Span pembungkus `proses_retrieval_semua()`, atribut `intent.count` | B | Plan |
