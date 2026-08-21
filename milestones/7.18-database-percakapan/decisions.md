# Decisions — Milestone 7.18: Membangun Database Percakapan

Dokumen ini mencatat keputusan desain untuk Milestone 7.18, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Kode penulisan riwayat percakapan diletakkan di `src/main.py` (endpoint), BUKAN di dalam `proses_turn()`

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user via `AskUserQuestion`, memilih opsi rekomendasi)

**Latar Belakang**
Riset plan menemukan `proses_turn()` (`turn_pipeline.py`) dan `submit_turn()` (`main.py`) SAMA-SAMA tidak punya hook/reservasi untuk langkah ini — genuinely terbuka di mana kode baru diletakkan. Dua kandidat: dalam `proses_turn()` (orkestrator, dipanggil dari mana pun termasuk eval/test) vs dalam `main.py` (endpoint, hanya dipanggil request HTTP nyata).

**Keputusan yang Dipilih**
Penulisan riwayat diletakkan di `src/main.py::submit_turn()`, SETELAH `_build_turn_response()` menghasilkan `TurnResponse`.

**Alasan**
(a) KK2 M7.18 sendiri secara literal menyebut "sebelum/bersamaan response dikirim LEWAT ENDPOINT" — "mengirim response" adalah konsep level HTTP, bukan konsep orkestrator murni. (b) `proses_turn()` dipanggil TERUS-MENERUS oleh `evals/` sejak M7.6 untuk kebutuhan testing/verifikasi — kalau penulisan riwayat ada di sana, SETIAP eksekusi eval (termasuk yang sudah ada, M7.6-7.17) akan ikut menulis baris riwayat "palsu" (bukan percakapan aplikasi nyata) ke tabel yang seharusnya murni untuk kebutuhan aplikasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Di dalam `proses_turn()`, di akhir orkestrator** — dipertimbangkan (Output KK menyebut "mekanisme penulisan yang terpanggil otomatis di akhir tiap turn yang diproses ORKESTRATOR", bisa dibaca sebagai tanggung jawab orkestrator), TAPI ditolak user — konsekuensinya (evals ikut menulis riwayat palsu) dinilai lebih buruk daripada ambiguitas penafsiran kata "orkestrator" tersebut.

**Dampak**
`KeadaanTurn` TIDAK bertambah field baru (beda dari pola M7.6-7.16) — riwayat dihitung dari `keadaan.paket_narasi` yang SUDAH ada, dikonsumsi langsung di `main.py`, tidak perlu diwariskan lewat skema akumulator.

---

### Keputusan 2: "Status keseluruhan turn" diturunkan dari AGREGASI status tiap item `paket_narasi`, BUKAN reuse `terverifikasi`

**Status:** Diputuskan sebelum implementasi (dikonfirmasi user via `AskUserQuestion` — user minta penjelasan konkret dulu sebelum memutuskan)

**Latar Belakang**
"Status keseluruhan turn" adalah salah satu dari 5 field skema minimal M7.18, TAPI tidak didefinisikan di mana pun (bukan di `KeadaanTurn`, bukan di dokumen manapun) — genuinely perlu dirancang. Dua kandidat sumber: `TurnResponse.terverifikasi` (sudah dihitung M7.17, biner) vs agregasi `KeadaanTurn.paket_narasi` (list per-atomic-intent, masing-masing py `StatusEksekusi` sendiri).

**Keputusan yang Dipilih**
Fungsi baru `tentukan_status_keseluruhan_turn(paket_narasi)` — kalau SELURUH item share `status` yang sama, itu jadi status turn; kalau campuran, hasilnya `"campuran"`.

**Alasan**
Dijelaskan konkret ke user (contoh: turn dengan 3 kebutuhan — 1 berhasil, 2 gagal teknis — tetap menghasilkan narasi JUJUR yang lolos verifikasi kesetiaan, `terverifikasi=True`, PADAHAL turn itu SEBAGIAN BESAR gagal). `terverifikasi` mengukur "apakah narasi tidak mengarang", BUKAN "apakah turn berhasil" — turn yang 100% ditolak RBAC atau 100% gagal teknis tetap bisa `terverifikasi=True` selama narasinya jujur melaporkannya. Kalau dipakai sebagai "status", kolom database akan nyaris SELALU "berhasil" (karena verifikasi kesetiaan jarang gagal), tidak berguna membedakan situasi turn yang genuinely berbeda-beda (sukses penuh vs ditolak vs gagal teknis vs campuran) — persis kegunaan yang disebut "Catatan Serah Terima" dokumen sumber (relevan untuk analitik/audit masa depan).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse `terverifikasi` (biner)** — direkomendasikan awal (sederhana, konsisten dengan yang user lihat di response), TAPI ditolak SETELAH penjelasan konkret di atas — user menilai nilai informasinya terlalu rendah untuk tujuan "status turn".

**Dampak**
`"campuran"` SENGAJA dipilih sebagai nilai BARU (bukan reuse `StatusEksekusi.SEBAGIAN` existing) — mencegah tertukar makna: `SEBAGIAN` di level atomic-intent berarti "data basi" (freshness), sementara "campuran" di level turn berarti "beberapa kebutuhan berbeda nasib". List `paket_narasi` kosong (kemungkinan besar mustahil, Decomposition selalu hasilkan ≥1 intent) ditangani defensif → `"tidak_ada_kebutuhan"`.

---

### Keputusan 3: Skema tabel `ConversationTurnRow` mirror `PromptEvalRunRow` (UUID PK + `created_at`), bukan `SessionMemoryPackageRow`

**Sumber Paksaan**
Preseden `src/db/models.py` — `PromptEvalRunRow` sudah py bentuk PALING dekat kebutuhan M7.18 (identitas unik per-baris + timestamp genuine), sementara `SessionMemoryPackageRow` (int PK sintetis, TANPA timestamp) dirancang untuk kebutuhan berbeda (arsip per atomic-intent, timestamp implisit lewat `turn_index`).

**Keputusan yang Diikuti**
`ConversationTurnRow(SQLModel, table=True)`: `id: uuid.UUID` (PK), `session_id: str` (index), `turn_index: int`, `pertanyaan: str`, `narasi: str`, `status: str`, `created_at: datetime` (default `datetime.now(timezone.utc)`).

**Catatan Ketergantungan**
`narasi` yang disimpan = `TurnResponse.narasi` (versi yang user GENUINELY terima, termasuk kalau sudah diganti pesan generik M7.17), BUKAN `HasilNarasi.narasi` mentah — forced by lingkup M7.18 ("riwayat... untuk kebutuhan APLIKASI", harus mencerminkan yang sungguh dikirim ke user).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mirror `SessionMemoryPackageRow` (int PK sintetis)** — ditolak: tidak py timestamp bawaan (field "waktu" WAJIB di skema minimal M7.18), `PromptEvalRunRow` preseden lebih tepat.

---

### Keputusan 4: Fungsi `simpan_riwayat_turn()` mirror pola raise-on-failure `store_session_memory()`, ditempatkan di `src/orchestration/riwayat_percakapan.py`

**Sumber Paksaan**
Preseden KONSISTEN seluruh project (Session Memory M1.5/M1.7/M4.3, narasi M4.4, verification gate M2.4): tangkap `Exception`, tandai `error.type="gagal_teknis"` di span, `raise` ulang APA ADANYA — caller yang memutuskan nasib kegagalan, bukan fungsi penyimpanan itu sendiri yang menelan. Lokasi `src/orchestration/` — M7.18 adalah concern PIC 7 (sejajar `src/layers/`, BUKAN salah satu 9 layer arsitektur), mirror preseden `wave.py` (M7.14)/`paket_narasi.py` (M7.15).

**Keputusan yang Diikuti**
`simpan_riwayat_turn(session_id, turn_index, pertanyaan, narasi, status) -> None` di `src/orchestration/riwayat_percakapan.py` — span `riwayat.simpan`, `try: ... except Exception: span.set_attribute("error.type", "gagal_teknis"); raise`.

**Catatan Ketergantungan**
Memungkinkan `simpan_riwayat_turn()` diuji STANDALONE dengan pola test kegagalan yang SAMA persis dengan `test_session_memory_kegagalan.py` (`monkeypatch` `Session`/`get_engine`/`get_tracer`, assert `pytest.raises`) — caller (`main.py`) yang baru menerapkan kebijakan "tangkap dan lanjutkan" (Keputusan 5).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fungsi menelan kegagalan sendiri, return `bool`/result object (mirror `HasilPemanggilanChatbotAPI`)** — dipertimbangkan (preseden `pemanggilan_chatbot_api.py`), TAPI ditolak untuk konsistensi dengan preseden Session-Memory-style yang LEBIH dekat secara fungsi (keduanya genuinely "simpan row ke Postgres"), dan supaya bisa diuji standalone dengan pola `pytest.raises` yang sudah familiar di project.

---

### Keputusan 5: `src/main.py` membungkus panggilan `simpan_riwayat_turn()` dalam try/except BARU yang menangkap dan TIDAK re-raise

**Sumber Paksaan**
KK2 M7.18 literal: "kegagalan penulisan riwayat tidak boleh menggagalkan pengiriman response ke user."

**Keputusan yang Diikuti**
Helper baru `_simpan_riwayat_percakapan_aman(keadaan, turn_response)` di `main.py` — hitung `status` via `tentukan_status_keseluruhan_turn()`, panggil `simpan_riwayat_turn()` dalam `try/except Exception: pass` (dengan komentar eksplisit menjelaskan kenapa pola ini BEDA dari SELURUH exception handler lain di file — SATU-SATUNYA titik "tangkap-dan-diam" di seluruh project). `submit_turn()` tetap `return turn_response` apa pun hasilnya.

**Catatan Ketergantungan**
Kegagalan TETAP "sinyal terpisah, bukan disembunyikan" — tercatat di span `riwayat.simpan` (`error.type`+exception event) milik `simpan_riwayat_turn()` sendiri (Keputusan 4), terlihat di Jaeger by service+span name, meski tidak sampai ke response HTTP. **Simplifikasi diterima**: span ini TIDAK ter-nest di bawah `invoke_agent` — `proses_turn()` sudah menutup span-nya SEBELUM `submit_turn()` memanggil fungsi ini (span baru mulai trace terpisah). Memperbaikinya butuh threading context OTel lintas-boundary (function call biasa, bukan lagi dalam scope span aktif) — di luar cakupan KK M7.18, tidak sepadan kompleksitasnya untuk milestone ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced literal oleh KK2 — satu-satunya cara memenuhi "kegagalan tidak boleh menggagalkan response" adalah menangkap di titik terakhir sebelum response dikirim.

---

### Keputusan 6: Tidak ada fungsi/endpoint retrieve riwayat baru

**Sumber Paksaan**
Output KK M7.18 hanya menyebut "mekanisme PENULISAN yang terpanggil otomatis" — tidak menyebut mekanisme baca/API baru untuk frontend.

**Keputusan yang Diikuti**
Verifikasi KK1 ("bisa ditarik kembali") dilakukan lewat query LANGSUNG ke tabel via SQLModel di skrip eval (Checkpoint 7), BUKAN membangun fungsi/endpoint retrieve produksi.

**Catatan Ketergantungan**
Kalau di masa depan frontend butuh menampilkan riwayat percakapan lama, itu perlu milestone/task terpisah (di luar cakupan M7.18) — dicatat sebagai potensi follow-up di `report.md`.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by Output KK yang eksplisit hanya menyebut penulisan.

---

### Keputusan 7: Materialisasi tabel via `SQLModel.metadata.create_all(get_engine())` sekali jalan, tanpa Alembic

**Sumber Paksaan**
Tidak ada Alembic/migration tool di project ini (dikonfirmasi riset: nol hasil `migrations/`/Alembic di seluruh repo) — preseden M1.5 ("Migrasi skema: `SQLModel.metadata.create_all(engine)`, TANPA Alembic") dan M2.2 (mengalami `UndefinedTable` sebelum tabel dimaterialisasi, diperbaiki cara sama).

**Keputusan yang Diikuti**
Checkpoint 2 menjalankan `SQLModel.metadata.create_all(get_engine())` sekali (skrip sekali-pakai) terhadap Supabase nyata, diverifikasi eksplisit tabel ada SEBELUM lanjut Checkpoint 3 — preseden M2.2 menunjukkan asumsi "otomatis berhasil" berisiko.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by tidak adanya migration tool di project ini.

---

### Keputusan 8 (Addendum M6.1): "Simplifikasi diterima" Keputusan 5 (span `riwayat.simpan` tidak ter-nest) DIPERBAIKI

**Status:** Ditemukan+diperbaiki di Milestone 6.1 (PIC 6, Custom Exporter Go) — dicatat di sini karena kepemilikan kode (`main.py::_simpan_riwayat_percakapan_aman()`) tetap M7.18, mengikuti preseden penulisan gap-fix di file pemilik.

**Latar Belakang**
Keputusan 5 di atas eksplisit mencatat "Simplifikasi diterima" bahwa span `riwayat.simpan` TIDAK ter-nest di bawah `invoke_agent` karena "Memperbaikinya butuh threading context OTel lintas-boundary... di luar cakupan KK M7.18". Riset M6.1 menemukan simplifikasi ini bukan sekadar kosmetik — tanpa perbaikan, exporter Go PIC 6 tidak akan PERNAH bisa mengisi `traces.status` untuk trace utama (satu-satunya sumber `riwayat.status` ada di trace `riwayat.simpan` yang terpisah), mematikan fitur distribusi status M5.1-5.4 begitu data asli mengalir. Lihat `milestones/6.1-membangun-exporter-dasar/decisions.md` Keputusan 2.

**Keputusan yang Dipilih**
`_simpan_riwayat_percakapan_aman()` sekarang merekonstruksi `SpanContext`/`NonRecordingSpan` dari `KeadaanTurn.invoke_agent_trace_id`/`invoke_agent_span_id` (M7.6 addendum, lihat `milestones/7.6-.../decisions.md` Keputusan 10), `opentelemetry.context.attach()`/`detach()` membungkus panggilan `simpan_riwayat_turn()` — persis "threading context OTel lintas-boundary" yang sebelumnya dianggap di luar cakupan.

**Alasan**
Threading context ternyata TIDAK sekompleks yang diperkirakan Keputusan 5 — pola `context.attach()`/`detach()` sudah ada presedennya sejak M7.7 (`turn_pipeline.py`), tinggal direkonstruksi dari trace_id/span_id string alih-alih objek `Context` langsung (menghindari `arbitrary_types_allowed` di `KeadaanTurn`).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Korelasi `session_id`+`turn_index` di sisi exporter Go (bukan perbaikan di Python)** — ditolak, lihat alasan lengkap di `milestones/6.1-.../decisions.md` Keputusan 2 (menambah heuristik rapuh, bukan menghilangkan kompleksitas).

**Dampak**
`error.type=gagal_teknis` pada span `riwayat.simpan` (kalau `simpan_riwayat_turn()` gagal) sekarang genuinely terlihat sebagai anak `invoke_agent` di Jaeger/Supabase — pesan asli Keputusan 5 "terlihat di Jaeger by service+span name" masih benar, TAPI sekarang JUGA correctly ternested, bukan sekadar dicari terpisah. Verifikasi nyata: lihat `milestones/6.1-.../logs.md` Checkpoint 2.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Lokasi penulisan di `main.py`, bukan `proses_turn()` | A | Plan |
| 2 | Status keseluruhan turn dari agregasi `paket_narasi` | A | Plan |
| 3 | Skema `ConversationTurnRow` mirror `PromptEvalRunRow` | B | Plan |
| 4 | `simpan_riwayat_turn()` mirror pola raise-on-failure | B | Plan |
| 5 | `main.py` tangkap-dan-diam (pola baru pertama) | B | Plan |
| 6 | Tidak ada fungsi retrieve baru | B | Plan |
| 7 | `create_all()` sekali jalan, tanpa Alembic | B | Plan |
| 8 | Span `riwayat.simpan` di-nest ke `invoke_agent` (Addendum M6.1, perbaikan Keputusan 5) | A | M6.1 Checkpoint 2 |
