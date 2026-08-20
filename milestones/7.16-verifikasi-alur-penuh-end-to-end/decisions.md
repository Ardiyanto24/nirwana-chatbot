# Decisions — Milestone 7.16: Sambungan 11 (Verifikasi Alur Penuh End-to-End)

Dokumen ini mencatat keputusan desain untuk Milestone 7.16, ditentukan sebelum implementasi dimulai (Plan Mode). Seluruh entri Jenis B (Preseden/Forced) — tidak ada keputusan genuinely terbuka yang butuh `AskUserQuestion` untuk milestone ini (dikonfirmasi eksplisit di plan, section "Keputusan yang Ditanyakan ke User").

---

### Keputusan 1: Tidak ada kode produksi baru — `proses_turn()` sudah lengkap 9 layer sejak M7.15

**Sumber Paksaan**
State kode nyata: `src/orchestration/turn_pipeline.py::proses_turn()` sudah mengimplementasikan seluruh sembilan layer (Input Layer → Ketergantungan → Rewrite/Tarik Memory paralel → Decomposition → Pencocokan → Domain Gate → Otorisasi → Cakupan Individu → Retriever → Query Engine → wave loop Verification Gate+Execution → Penyimpanan Paket → Penggabungan Narasi → Interpretation) sejak Milestone 7.15 selesai (2026-08-19, dikonfirmasi lewat pembacaan langsung file tersebut sebelum plan ditulis).

**Keputusan yang Diikuti**
M7.16 tidak menambah/mengubah satu baris kode `src/` pun. Cakupan murni: eksekusi nyata 3 skenario + verifikasi span + dokumentasi penutup Level 2. Pola ini sama seperti M7.2/M7.3 ("sudah tersambung sejak milestone asalnya, milestone jadi verifikasi+dokumentasi") — bedanya di sini seluruh SEMBILAN layer sekaligus, bukan satu unit LLM.

**Catatan Ketergantungan**
Kalau riset lebih lanjut (Checkpoint 2-3) genuinely menemukan bug/celah baru (mirror pola M7.6/M7.7 yang menemukan celah `try/except`), itu akan dicatat sebagai entri baru di sini dan didokumentasikan di `docs/keterbatasan-diterima.md` bila diterima, atau diperbaiki di file kepemilikan aslinya (bukan di M7.16) — konsisten preseden.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by state kode nyata.

---

### Keputusan 2: Ketiga skenario toleran terhadap `SEBAGIAN`/`GAGAL_TEKNIS`, tidak mensyaratkan `BERHASIL`

**Sumber Paksaan**
Instruksi eksplisit user saat memulai milestone ini ("tidak perlu ada uji yang membutuhkan data terbaru, karena data memang belum update") + `docs/keterbatasan-diterima.md` #15 (seluruh database `chatbot_api` lokal permanen stale sejak 2026-08-11 — SETIAP eksekusi nyata yang mencapai `chatbot_api` di lingkungan kerja saat ini PASTI `SEBAGIAN`, tidak pernah `BERHASIL`).

**Keputusan yang Diikuti**
KK M7.16 ("berhasil dijalankan penuh dari ujung ke ujung tanpa pemanggilan manual antar-layer") dibaca sebagai kriteria soal ALUR (pipeline selesai tanpa exception tak tertangani/tanpa intervensi manual), BUKAN soal hasil data yang harus `BERHASIL`. `SEBAGIAN`/`GAGAL_TEKNIS` yang dilaporkan jujur ke narasi akhir dianggap bukti KK terpenuhi, sepanjang seluruh 9 layer benar-benar dilalui dan span `invoke_agent` membungkus semuanya.

**Catatan Ketergantungan**
Kalau `docs/keterbatasan-diterima.md` #15 di masa depan direvisi (data direfresh), skenario ini TIDAK perlu diulang untuk M7.16 — keputusan ini murni kriteria evaluasi milestone ini, bukan klaim yang expired begitu data segar tersedia.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by instruksi eksplisit user.

---

### Keputusan 3: Skenario E03 (rujukan lintas-turn) — satu pemanggilan `proses_turn()` dengan `history` fiktif di payload, bukan dua panggilan nyata berurutan

**Sumber Paksaan**
Keputusan 2 di atas (tidak boleh butuh data segar) + preseden `evals/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/payloads/E01.json` (payload `turn_index=2` dengan `history` memuat 1 entri turn 1 fiktif — `detect_turn_dependency()` (M1.3) membaca ketergantungan LANGSUNG dari field `history` di payload, bukan dari Session Memory DB — sudah terbukti valid menghasilkan `is_dependent=True`/`referenced_turn_index=1`).

**Keputusan yang Diikuti**
E03 dirancang sebagai SATU pemanggilan `proses_turn()`: `session_id` baru (belum pernah dipakai), `turn_index=2`, `history=[{turn_index: 1, question: ..., answer: ...}]` fiktif. `retrieve_session_memory()` (Tarik Memory) tetap GENUINELY terpanggil (karena `is_dependent=True` terdeteksi dari `history`), tapi query ke Session Memory DB sungguhan untuk `session_id` baru ini akan mengembalikan `[]` (kosong, bukan error) — pembeda `None` (tidak dipanggil) vs `[]` (dipanggil-kosong) sudah dikonfirmasi valid sejak M7.7.

**Alasan**
Membuktikan mekanisme Percabangan Paralel (M7.7) + Pencocokan (M1.7) tetap aktif benar di dalam pipeline PENUH (belum pernah dibuktikan bersama Interpretation sebelumnya) TANPA bergantung pada data historis nyata yang genuinely stale — cabang "selesai dari BERHASIL" (yang butuh data segar) sudah eksplisit di luar cakupan M7.16 sesuai Keputusan 2, konsisten `docs/keterbatasan-diterima.md` #15 follow-up ("prioritaskan sebelum M7.16 kalau skenario e2e-nya juga butuh kombinasi serupa" — M7.16 SENGAJA dirancang tidak membutuhkannya).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Dua panggilan nyata berurutan (turn 1 genuinely dieksekusi dulu, baru turn 2 memanggil `proses_turn()` lagi dengan `session_id` yang sama)** — ini pola yang dipakai M7.15 E01 (4 percobaan) dan gagal genuinely dibuktikan karena turn 1 selalu berakhir `SEBAGIAN` (staleness), membuat turn 2 tidak pernah mendapat kandidat "selesai" yang valid. Ditolak karena PERSIS bertentangan dengan instruksi eksplisit user hari ini soal tidak butuh data segar — mengulang pola ini di M7.16 hanya akan mereproduksi kegagalan yang sama.

**Dampak**
E03 TIDAK membuktikan cabang "selesai dari BERHASIL turn sebelumnya" — itu tetap gap terbuka milik `docs/keterbatasan-diterima.md` #15, bukan tanggung jawab M7.16 untuk menutupnya (M7.16 KK-nya soal alur 9 layer, bukan soal skenario "selesai" spesifik yang sudah jadi tanggung jawab M7.15).

---

### Keputusan 4: E01 dan E02 reuse payload persis dari eval milestone sebelumnya

**Sumber Paksaan**
Preseden reuse skenario yang konsisten dipakai M7.10-7.15 (payload identik + `session_id` baru, menghindari menyusun skenario baru tanpa alasan kuat saat skenario lama yang sudah teruji sebagian tersedia).

**Keputusan yang Diikuti**
- **E01** (kebutuhan tunggal sederhana): payload persis `evals/7.9-sambungan-pencocokan/payloads/E01.json` (General Manager, "Berapa occupancy rate properti kita bulan Juni 2026?"), `session_id` baru. Skenario ini SEBELUMNYA hanya teruji sampai `matches` (M7.9 belum py Domain Gate dst.) — menjalankannya lewat `proses_turn()` final genuinely menguji rentang yang belum pernah dibuktikan bersama (Retriever→Interpretation).
- **E02** (kebutuhan dengan wave): payload persis `evals/7.14-sambungan-execution/payloads/E01.json` (Front Office Staff, pertanyaan gop_margin majemuk-bergantung 2-wave), `session_id` baru. Skenario ini SEBELUMNYA hanya teruji sampai `execution` (M7.14 mendahului M7.15, belum py `paket_narasi`/`interpretation`) — menjalankannya lagi genuinely menguji apakah wave loop diikuti Penyimpanan Paket+Narasi+Interpretation yang benar.

**Catatan Ketergantungan**
Kedua skenario melibatkan pemanggilan LLM non-deterministik (Decomposition dkk.) — hasil `atomic_intents`/`domains`/dst. bisa sedikit berbeda dari run sebelumnya meski payload identik (preseden `docs/keterbatasan-diterima.md` #3). Ini tidak masalah untuk KK M7.16 (soal alur, bukan hasil persis) — dicatat apa adanya di `audit.md`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menyusun skenario baru dari nol** — ditolak: tidak ada kebutuhan genuinely baru yang tidak bisa dipenuhi payload existing, dan reuse memberi nilai tambah (menguji rentang layer yang belum pernah dibuktikan bersama untuk payload yang sama).

---

### Keputusan 5: Verifikasi cakupan span 9 layer via peta nama span yang dikonfirmasi lewat inspeksi kode langsung

**Sumber Paksaan**
Preseden M7.9 (span diidentifikasi lewat relasi eksplisit dalam trace, bukan asumsi/tebakan nama).

**Keputusan yang Diikuti**
Sebelum eksekusi nyata, seluruh nama span pembungkus tiap layer dikonfirmasi lewat `grep "start_as_current_span("` langsung ke `src/`:

| Layer | Span wajib muncul sebagai descendant `invoke_agent` |
|---|---|
| Input Layer | `input.validate` |
| Context Resolution | `chat` (ketergantungan+rewrite+matching per-item), `matching.evaluate`; `memory.retrieve` HANYA jika ada referensi terdeteksi |
| Decomposition | `chat` × 3 (klasifikasi/pemecahan/verifikasi) |
| Domain Gate | `domain_gate.identifikasi_semua`, `domain_gate.periksa_otorisasi_semua`, `domain_gate.deteksi_constraint_semua` |
| Retriever | `retriever.proses_semua` (+ `retriever.cari_kandidat_view`/`retriever.nilai_kecocokan_makna_semua` per item) |
| Query Engine | `query_engine.susun_dan_verifikasi_request_semua` |
| Verification Gate | `verification_gate.verifikasi_gate_semua` (per wave) |
| Execution | `execution.eksekusi_atomic_intent_semua`, `execution.susun_dan_simpan_paket_semua` |
| Interpretation | `chat` (narasi + verifikasi kesetiaan) |

Ditambah span orkestrasi murni (bukan salah satu 9 layer, tapi wajib ada): `invoke_agent` (root), `orchestration.wave` (per wave, hanya E02), `orchestration.susun_paket_narasi`.

**Catatan Ketergantungan**
Kalau salah satu span di atas TIDAK muncul untuk skenario yang seharusnya melewatinya, itu temuan genuinely baru yang dicatat di `audit.md` — bukan diasumsikan sebagai kesalahan skrip eval.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M7.9 + kebutuhan akurasi verifikasi KK kedua M7.16 ("span `invoke_agent` membungkus seluruh span dari kesembilan layer").

---

### Keputusan 6: `run_eval.py` diadaptasi dari `evals/7.14-sambungan-execution/run_eval.py`, `_serialize_result()` diperluas mencakup `paket_narasi`+`interpretation`

**Sumber Paksaan**
Pola paling dekat: `evals/7.14-.../run_eval.py` sudah py query Jaeger, cek prasyarat `chatbot_api`+Jaeger, dan serialisasi `KeadaanTurn` — tapi ditulis SEBELUM M7.15 menambah 2 field terakhir (`paket_narasi`, `interpretation`).

**Keputusan yang Diikuti**
`_serialize_result()` diperluas 2 key baru mengikuti pola `.model_dump()` yang sama seperti field lain, ditambah `_analisis_cakupan_span()` (fungsi baru khusus M7.16, menggantikan `_analisis_urutan_wave()` M7.14 yang spesifik uji urutan wave — M7.16 butuh cek cakupan 9 layer, bukan urutan).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menulis `run_eval.py` dari nol** — ditolak: struktur `_cek_prasyarat()`/`_query_jaeger_trace()`/`_jalankan_kejadian()` M7.14 sudah terbukti bekerja 2 milestone berturut-turut (M7.14, dan pola serupa M7.15), tidak ada alasan menulis ulang logic yang sama.

---

### Keputusan 7: Tidak ada unit test baru

**Sumber Paksaan**
Keputusan 1 (tidak ada kode produksi baru) — tidak ada yang perlu di-unit-test.

**Keputusan yang Diikuti**
Seluruh test existing (`tests/orchestration/test_turn_pipeline.py`, total 679 test project per regresi M7.15) sudah menjaga regresi kontrak I/O tiap fungsi yang dipanggil `proses_turn()` — cukup dijalankan ulang sebagai sanity check di Checkpoint 5 (bukan ditambah).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by Keputusan 1.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Tidak ada kode produksi baru | B | Plan |
| 2 | Toleran `SEBAGIAN`/`GAGAL_TEKNIS`, tidak mensyaratkan `BERHASIL` | B | Plan |
| 3 | E03 satu-panggilan dengan `history` fiktif | B | Plan |
| 4 | E01/E02 reuse payload persis milestone sebelumnya | B | Plan |
| 5 | Peta nama span 9 layer, dikonfirmasi via grep | B | Plan |
| 6 | `run_eval.py` diadaptasi dari M7.14 | B | Plan |
| 7 | Tidak ada unit test baru | B | Plan |
