# Rancangan Pengujian — Pencocokan Atomic Intent × Data Session Memory (Milestone 1.7)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/1.3-.../1.4-.../1.6-.../rancangan.md`. **Jumlah skenario TIDAK dipatok** — 10 skenario di sini murni hasil analisis dimensi yang relevan untuk mekanisme LLM-satu-panggilan-per-item ini (lihat `decisions.md` Keputusan 13, plan Checkpoint 8), bukan konvensi wajib.

## Yang Diuji

`match_atomic_intents()` (`src/layers/context_resolution/matching.py`) — Milestone 1.7 sudah lolos 3 skenario minimal dari Kriteria Keberhasilan sumber (`tests/layers/context_resolution/test_matching.py`, termasuk rantai arsip ulang lewat `match_and_archive()`). Pengujian ini fokus MURNI pada presisi keputusan cocok/tidak-cocok (`match_atomic_intents()`, TANPA sentuh DB — kandidat dikonstruksi langsung sebagai objek `SessionMemoryPackage` in-memory, bukan lewat `store_session_memory()`, karena dimensi yang diuji di sini adalah kualitas keputusan LLM, bukan persistence yang sudah dibuktikan formal):

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Paraphrase kata berbeda makna sama (alasan inti kenapa LLM dipilih) | Tidak | S01 |
| Entitas kunci beda: bulan berbeda (anti false-positive) | Sebagian (kelompok b, topik total beda) | S02 (topik SAMA, cuma bulan beda — lebih ketat) |
| Entitas kunci beda: metrik berbeda, domain sama | Tidak | S03 |
| Filter kandidat status=gagal_teknis, topik identik | Tidak | S04 |
| Filter kandidat status=sebagian, topik identik | Tidak | S05 |
| Mixed match dalam satu turn (sebagian cocok, sebagian tidak) | Tidak | S06 |
| Non-eksklusivitas (2 atomic intent baru cocok ke kandidat sama) | Tidak | S07 |
| Pool kandidat besar, presisi pemilihan index yang benar | Tidak | S08 |
| Recency bias (posisi kandidat vs kebenaran makna) | Tidak (relevan `docs/keterbatasan-diterima.md` #3) | S09 |
| `label_bentuk_jawaban` beda meski topik sama | Tidak | S10 |

## Cara Baca Skenario

Tiap skenario: daftar atomic intent baru (teks_kebutuhan + label_bentuk_jawaban), daftar kandidat (teks_kebutuhan + label_bentuk_jawaban + status, indeks urutan SENGAJA dicatat karena relevan untuk S08/S09), ekspektasi per atomic intent (`selesai` + index kandidat yang benar, atau `perlu_eksekusi`), dan status toleransi.

---

### S01 — Paraphrase Kata Berbeda Makna Sama

**Atomic intent baru:** "pendapatan reservasi bulan Maret 2026" (nilai_tunggal)

**Kandidat:** [1] "revenue reservasi Maret 2026" (nilai_tunggal, berhasil)

**Ekspektasi:** `selesai`, kandidat index 1.

**Toleransi:** Tidak ada — ini alasan inti kenapa mekanisme LLM semantik dipilih (Keputusan 1), bukan deterministik/string-match. Kalau gagal cocok di sini, itu temuan signifikan terhadap keputusan arsitektur itu sendiri.

---

### S02 — Entitas Kunci Beda: Bulan Berbeda (Topik Sama)

**Atomic intent baru:** "occupancy rate Mei 2026" (nilai_tunggal)

**Kandidat:** [1] "occupancy rate bulan April 2026" (nilai_tunggal, berhasil)

**Ekspektasi:** `perlu_eksekusi`.

**Toleransi:** Tidak ada — kritis. Kalau model salah cocok hanya karena topik "occupancy rate" sama (mengabaikan bulan beda), ini indikasi model mengandalkan kemiripan permukaan, bukan kesesuaian makna sesungguhnya (mirror semangat S10 `evals/1.6-.../rancangan.md`).

---

### S03 — Entitas Kunci Beda: Metrik Berbeda, Domain Sama

**Atomic intent baru:** "revenue F&B bulan Maret 2026" (nilai_tunggal)

**Kandidat:** [1] "jumlah komplain tamu F&B bulan Maret 2026" (nilai_tunggal, berhasil)

**Ekspektasi:** `perlu_eksekusi`.

**Toleransi:** Tidak ada — domain (F&B) sama, tapi metrik (revenue vs komplain) genuinely berbeda.

---

### S04 — Filter Kandidat: `status=gagal_teknis`, Topik Identik

**Atomic intent baru:** "occupancy rate bulan April 2026" (nilai_tunggal)

**Kandidat:** [1] "occupancy rate bulan April 2026" (nilai_tunggal, **gagal_teknis** — teks IDENTIK persis, status yang beda)

**Ekspektasi:** `perlu_eksekusi` — kandidat difilter habis SEBELUM sampai ke LLM (Keputusan 4), nol panggilan LLM sungguhan untuk skenario ini.

**Toleransi:** Tidak ada — menguji jalur pintas kandidat-kosong-setelah-filter (Checkpoint 4) bekerja meski teks identik persis.

---

### S05 — Filter Kandidat: `status=sebagian`, Topik Identik

**Atomic intent baru:** "occupancy rate bulan April 2026" (nilai_tunggal)

**Kandidat:** [1] "occupancy rate bulan April 2026" (nilai_tunggal, **sebagian**)

**Ekspektasi:** `perlu_eksekusi`.

**Toleransi:** Tidak ada — sama seperti S04, status non-`berhasil` lain.

---

### S06 — Mixed Match dalam Satu Turn

**Atomic intent baru:** [a] "berapa occupancy April 2026" (nilai_tunggal), [b] "berapa jumlah staff yang resign bulan Juni 2026" (nilai_tunggal)

**Kandidat:** [1] "occupancy rate bulan April 2026" (nilai_tunggal, berhasil)

**Ekspektasi:** [a] `selesai` kandidat index 1, [b] `perlu_eksekusi`.

**Toleransi:** Tidak ada — satu panggilan `match_atomic_intents()` memproses dua atomic intent, hasil harus benar untuk KEDUANYA secara independen.

---

### S07 — Non-Eksklusivitas (Dua Atomic Intent Baru Cocok ke Kandidat Sama)

**Atomic intent baru:** [a] "berapa occupancy April 2026", [b] "occupancy rate bulan April kemarin"

**Kandidat:** [1] "occupancy rate bulan April 2026" (nilai_tunggal, berhasil)

**Ekspektasi:** [a] DAN [b] sama-sama `selesai` kandidat index 1 (Keputusan 6 — tidak dipaksa eksklusif).

**Toleransi:** Tidak ada — kedua atomic intent genuinely merujuk fakta yang sama dengan frasa berbeda, keduanya WAJAR dapat kandidat yang sama.

---

### S08 — Pool Kandidat Besar, Presisi Pemilihan

**Kandidat:** [1] "occupancy rate Januari 2026" [2] "occupancy rate Februari 2026" [3] "occupancy rate Maret 2026" [4] "occupancy rate April 2026" (semua nilai_tunggal, berhasil)

**Atomic intent baru:** "berapa occupancy Maret 2026"

**Ekspektasi:** `selesai`, kandidat index **3** SPESIFIK (bukan index lain meski semuanya bertopik sama).

**Toleransi:** Tidak ada pada index yang dipilih.

---

### S09 — Recency Bias (Posisi Kandidat vs Kebenaran Makna)

**Kandidat (urutan SENGAJA disusun):** [1] "occupancy rate Februari 2026" (BENAR secara makna) [2] "revenue F&B Maret 2026" (topik lain, pengisi) [3] "occupancy rate April 2026" (SALAH bulan, tapi di posisi PALING AKHIR)

**Atomic intent baru:** "berapa occupancy Februari 2026"

**Ekspektasi:** `selesai`, kandidat index **1** (BUKAN index 3 meski di posisi akhir/paling "recent" dalam daftar).

**Toleransi eksplisit:** Kalau model salah pilih index 3, INI BUKAN otomatis dianggap gagal keras seperti S02 — dicatat sebagai temuan pola recency bias yang relevan langsung dengan `docs/keterbatasan-diterima.md` #3 (recency bias sudah teramati lintas M1.3/M1.4, model/tugas berbeda). Tetap dianalisis eksplisit di `audit.md`, bukan diabaikan.

---

### S10 — `label_bentuk_jawaban` Berbeda Meski Topik Sama

**Kandidat:** [1] "occupancy rate bulan Januari 2026" (nilai_tunggal, berhasil — satu angka)

**Atomic intent baru:** "bagaimana tren occupancy rate 6 bulan terakhir" (**tren**)

**Ekspektasi:** `perlu_eksekusi` — kandidat cuma satu nilai tunggal, tidak bisa menjawab kebutuhan bentuk `tren` (deret waktu).

**Toleransi:** Tidak ada — `label_bentuk_jawaban` yang berbeda adalah sinyal kuat bahwa ini kebutuhan yang genuinely berbeda meski topik (occupancy) tumpang tindih.

---

### S11 — Non-Eksklusivitas (Retest, Paraphrase Tidak Ambigu)

**Ditambahkan SETELAH S07 dijalankan** — S07 ternyata tidak benar-benar menguji Keputusan 6, karena item keduanya ("occupancy rate bulan April kemarin") genuinely ambigu (tidak eksplisit tahun 2026, beda dari item 1), sehingga penolakan model adalah perilaku konservatif yang benar (by design), bukan pengujian eksklusivitas yang valid. Lihat `audit.md` untuk analisis lengkap.

**Atomic intent baru:** [a] "berapa occupancy April 2026", [b] "nilai occupancy rate untuk periode April 2026" (paraphrase lain, TIDAK ambigu — eksplisit "April 2026" persis seperti item a)

**Kandidat:** [1] "occupancy rate bulan April 2026" (nilai_tunggal, berhasil)

**Ekspektasi:** [a] DAN [b] sama-sama `selesai` kandidat index 1.

**Toleransi:** Tidak ada — kedua frasa sama-sama eksplisit merujuk fakta identik, tidak ada ambiguitas temporal seperti S07.

---

## Ringkasan Ekspektasi

| ID | Atomic Intent | Ekspektasi | Toleransi |
|---|---|---|---|
| S01 | 1 | selesai → [1] | Tidak |
| S02 | 1 | perlu_eksekusi | Tidak — kritis |
| S03 | 1 | perlu_eksekusi | Tidak |
| S04 | 1 | perlu_eksekusi (filter, 0 panggilan LLM) | Tidak |
| S05 | 1 | perlu_eksekusi (filter, 0 panggilan LLM) | Tidak |
| S06 | 2 | [a]→selesai [1], [b]→perlu_eksekusi | Tidak |
| S07 | 2 | [a]→selesai [1], [b]→selesai [1] | Tidak |
| S08 | 1 | selesai → [3] | Tidak |
| S09 | 1 | selesai → [1] | Ya — dicatat sebagai temuan kalau salah, bukan fail keras |
| S10 | 1 | perlu_eksekusi | Tidak |
| S11 | 2 | [a]→selesai [1], [b]→selesai [1] | Tidak (retest S07 dengan paraphrase tidak ambigu) |
