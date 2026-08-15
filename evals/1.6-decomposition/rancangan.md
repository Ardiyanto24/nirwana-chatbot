# Rancangan Pengujian — Decomposition (Milestone 1.6)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/1.3-.../rancangan.md` dan `evals/1.4-.../rancangan.md`, tapi **jumlah skenario TIDAK dipatok ke 12** — prioritasnya mencakup ruang kegagalan yang genuinely relevan untuk mekanisme 3-langkah+retry+2-model ini (lihat `decisions.md` Keputusan 13, koreksi eksplisit user saat review plan).

## Yang Diuji

`decompose_question()` (`src/layers/decomposition/decompose.py`) dan komponennya (`klasifikasi_kebutuhan`, `pecah_atomik`, `verifikasi_pemecahan`) — Milestone 1.6 sudah lolos 2 skenario minimal dari Kriteria Keberhasilan sumber (`tests/layers/decomposition/test_decompose.py`). Pengujian ini lebih menyeluruh, menutup dimensi yang belum diuji:

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Tunggal murni | Tidak | S01 |
| Majemuk independen murni (anti false-positive relasi) | Tidak | S02 |
| Majemuk bergantung, 2 kebutuhan | Ya (kelompok a) | S03 (domain beda, konfirmasi ulang) |
| Majemuk bergantung berlapis (3+ kebutuhan dasar) | Tidak | S04 |
| Kalimat ambigu (tunggal vs majemuk implisit) | Tidak | S05 |
| Retry benar-benar terpicu (bukan cuma diasumsikan) | Tidak | S06 |
| Label `tren` | Tidak | S07 |
| Label `peringkat` | Tidak | S08 |
| Label `komposisi` | Tidak | S09 |
| Jebakan overlap leksikal (paling kritis - domain beda, kata mirip) | Tidak | S10 |
| Verifikasi menangkap kesalahan SUBTIL (bukan cuma kebutuhan hilang) | Ya (kelompok b, kasus kasar) | S11 (kasus halus: label/relasi salah, bukan hilang total) |
| Stress test volume (4+ kebutuhan independen) | Tidak | S12 |
| Retry exhausted (usaha replikasi terkontrol) | Tidak | S13 |
| Klasifikasi anti false-positive (kalimat panjang tapi sebenarnya tunggal) | Tidak | S14 |

## Cara Baca Skenario

Tiap skenario: payload (pertanyaan, atau untuk S11 payload `PemecahanResult` yang disuntik manual), ekspektasi terhadap `DecompositionResult` (atau `VerifikasiResult` untuk S11), dan status toleransi. Karena output `DecompositionResult` jauh lebih kaya dari M1.3/M1.4 (bukan sekadar boolean/string), ekspektasi dicek terhadap beberapa aspek: `klasifikasi`, jumlah `atomic_intents`, pola relasi (independen/bergantung + validitas rujukan `bergantung_pada`), kehadiran `label_bentuk_jawaban` tertentu, dan `verifikasi_valid`.

---

### S01 — Tunggal murni

**Payload:** "Berapa occupancy rate bulan Juni 2026?"

**Ekspektasi:** `klasifikasi=tunggal`, 1 atomic intent, `relasi=independen`, `label_bentuk_jawaban=nilai_tunggal`, `verifikasi_valid=True`.

**Toleransi:** Tidak ada.

---

### S02 — Majemuk independen murni (anti false-positive relasi)

**Payload:** "Berapa revenue F&B bulan ini dan berapa jumlah staff Housekeeping yang aktif?"

**Ekspektasi:** `klasifikasi=majemuk_independen`, 2 atomic intent, KEDUANYA `relasi=independen` (topik benar-benar tidak terkait), `verifikasi_valid=True`.

**Toleransi:** Tidak ada — dua topik ini genuinely tidak berhubungan, model TIDAK boleh memaksakan relasi bergantung.

---

### S03 — Majemuk bergantung, 2 kebutuhan (domain beda dari `tests/`)

**Payload:** "Bandingkan occupancy rate April 2026 dengan Maret 2026."

**Ekspektasi:** `klasifikasi=majemuk_bergantung`, ≥2 atomic intent, minimal 1 `relasi=bergantung` dengan `bergantung_pada` merujuk ke atomic intent independen yang benar-benar ada, `label_bentuk_jawaban=perbandingan` hadir, `verifikasi_valid=True`.

**Toleransi:** Tidak ada.

---

### S04 — Majemuk bergantung berlapis (3 kebutuhan dasar + 1 gabungan)

**Payload:** "Bandingkan revenue reservasi Januari, Februari, dan Maret 2026."

**Ekspektasi:** `klasifikasi=majemuk_bergantung`, ≥4 atomic intent (3 nilai bulanan independen + 1 perbandingan yang bergantung pada ketiganya), `label_bentuk_jawaban=perbandingan` hadir, `verifikasi_valid=True`.

**Toleransi:** Struktur pemecahan detail (mis. apakah perbandingan dipecah jadi 1 atau beberapa pasangan) boleh bervariasi — yang wajib: SEMUA 3 nilai bulanan independen ada, DAN minimal 1 kebutuhan bergantung yang merujuk ke ≥2 di antaranya.

---

### S05 — Kalimat ambigu (tunggal vs majemuk implisit)

**Payload:** "Bagaimana performa Front Office bulan ini?"

**Ekspektasi:** Tidak ada jawaban benar tunggal — bisa `tunggal` (satu kebutuhan umum "performa") atau `majemuk_independen`/`majemuk_bergantung` (implisit: rating kepuasan, jumlah komplain, dll pecah terpisah).

**Toleransi eksplisit:** SEMUA klasifikasi diterima selama `verifikasi_valid=True` (hasil pemecahan konsisten secara internal dengan klasifikasi yang dipilih). Audit mencatat mana yang dipilih model + penilaian apakah itu defensible.

---

### S06 — Retry Benar-Benar Terpicu

**Payload:** "Bandingkan rata-rata rating kepuasan tamu Front Office dengan rata-rata rating kepuasan tamu Housekeeping untuk periode yang sama, dengan tren 3 bulan terakhir masing-masing."

**Tujuan:** Kalimat sengaja kompleks (2 metrik dibandingkan, tiap metrik juga butuh tren 3 bulan) — kandidat kuat memicu kesalahan struktural di percobaan pertama Pemecahan (mis. lupa label `tren`, relasi keliru).

**Ekspektasi:** `verifikasi_valid=True` pada akhirnya (setelah retry kalau perlu), SEMUA kebutuhan (2 rating + tren masing-masing + 1 perbandingan) tercakup.

**Toleransi eksplisit:** `retry_count` BOLEH 0 (kalau model langsung benar) — itu bukan kegagalan, cuma berarti skenario ini tidak berhasil memancing retry. Dicatat di audit sebagai temuan (retry benar-benar terpicu atau tidak), bukan pass/fail.

---

### S07 — Label `tren`

**Payload:** "Bagaimana tren occupancy rate 6 bulan terakhir?"

**Ekspektasi:** 1 atomic intent, `label_bentuk_jawaban=tren`, `relasi=independen`.

**Toleransi:** Tidak ada.

---

### S08 — Label `peringkat`

**Payload:** "Siapa 5 staff dengan rating kepuasan tamu tertinggi bulan ini?"

**Ekspektasi:** 1 atomic intent, `label_bentuk_jawaban=peringkat`.

**Toleransi:** Tidak ada.

---

### S09 — Label `komposisi`

**Payload:** "Bagaimana breakdown revenue bulan ini per departemen?"

**Ekspektasi:** 1 atomic intent, `label_bentuk_jawaban=komposisi`.

**Toleransi:** Tidak ada.

---

### S10 — Jebakan Overlap Leksikal (PALING KRITIS)

**Payload:** "Berapa revenue F&B bulan ini, dan berapa revenue reservasi bulan ini?"

**Tujuan:** Dua metrik revenue, domain sama sekali beda (F&B vs reservasi), kata "revenue"+"bulan ini" muncul di keduanya — TIDAK ada hubungan perbandingan yang genuinely diminta (user tidak bilang "bandingkan").

**Ekspektasi:** `klasifikasi=majemuk_independen` (BUKAN `majemuk_bergantung`), 2 atomic intent, KEDUANYA `relasi=independen`.

**Toleransi:** **Tidak ada — paling kritis.** Kalau model memaksakan relasi bergantung/perbandingan hanya karena kemiripan kata, ini temuan signifikan (indikasi model mengandalkan kecocokan permukaan, bukan pemahaman maksud sesungguhnya) — dicatat sebagai temuan utama di `audit.md`.

---

### S11 — Verifikasi Menangkap Kesalahan Subtil (Relasi/Label Keliru, Bukan Hilang Total)

**Tujuan:** Kriteria Keberhasilan formal (`tests/`) sudah membuktikan verifikasi menangkap kasus KASAR (kebutuhan hilang total). Skenario ini menguji kasus lebih HALUS — semua kebutuhan ADA, tapi salah satu atributnya keliru.

**Payload:** `PemecahanResult` disuntik manual untuk pertanyaan "Bandingkan revenue reservasi Maret 2026 dengan Februari 2026" — 3 atomic intent LENGKAP (Maret, Februari, perbandingan), TAPI kebutuhan perbandingan sengaja dilabel `label_bentuk_jawaban=nilai_tunggal` (seharusnya `perbandingan`) DAN `relasi=independen` (seharusnya `bergantung`). Dipanggil langsung ke `verifikasi_pemecahan()`.

**Ekspektasi:** `valid=False`, `alasan` menyebut ketidaksesuaian label dan/atau relasi.

**Toleransi:** Tidak ada — ini inti kemampuan verifikasi menilai KUALITAS pemecahan, bukan cuma kelengkapan.

---

### S12 — Stress Test Volume (4+ Kebutuhan Independen)

**Payload:** "Berapa occupancy rate, revenue F&B, jumlah komplain housekeeping, dan jumlah staff aktif bulan ini?"

**Ekspektasi:** `klasifikasi=majemuk_independen`, 4 atomic intent, SEMUA `relasi=independen`, `verifikasi_valid=True`.

**Toleransi:** Tidak ada pada jumlah (harus tepat 4, satu per kebutuhan yang disebut eksplisit) — toleransi hanya pada urutan/detail teks kebutuhan.

---

### S13 — Retry Exhausted (Usaha Replikasi Terkontrol)

**Payload:** Kalimat yang sangat rumit dan berpotensi genuinely ambigu secara struktural — "Bandingkan performa keseluruhan Front Office, Housekeeping, dan F&B bulan ini berdasarkan rating kepuasan tamu, jumlah komplain, dan kontribusi revenue masing-masing, lalu urutkan dari yang terbaik."

**Tujuan:** Kombinasi perbandingan+peringkat+banyak dimensi — kandidat terbaik yang tersedia untuk memancing verifikasi gagal berulang.

**Ekspektasi:** Tidak ditentukan di depan (genuinely eksploratif) — dicatat apa adanya: `retry_count` yang terjadi, apakah exhausted (`retry_count=2` dan `verifikasi_valid=False` di akhir) atau berhasil konvergen.

**Toleransi:** **Skenario ini BOLEH gagal direplikasi** (LLM mungkin lebih baik dari perkiraan meski kompleks) — kalau begitu, dicatat sebagai keterbatasan eval di `audit.md` ("belum berhasil mereplikasi retry-exhausted secara terkontrol"), BUKAN dipaksakan/direkayasa jadi test palsu.

---

### S14 — Klasifikasi Anti False-Positive (Kalimat Panjang tapi Sebenarnya Tunggal)

**Payload:** "Berapa total revenue seluruh departemen (F&B, Housekeeping, Spa, dan Reservasi) yang digabung jadi satu angka bulan ini?"

**Tujuan:** Kalimat menyebut banyak departemen (kata kunci berulang) TAPI sebenarnya SATU kebutuhan (total gabungan) — anti false-positive terhadap "banyak kata benda = majemuk".

**Ekspektasi:** Idealnya `klasifikasi=tunggal`, 1 atomic intent, `label_bentuk_jawaban=nilai_tunggal` (atau `komposisi` kalau breakdown per departemen ikut diharapkan, meski pertanyaan eksplisit minta "digabung jadi satu angka" yang mengarah ke `nilai_tunggal`).

**Toleransi eksplisit:** Genuinely ambigu antara `nilai_tunggal` (angka gabungan) vs `komposisi` (breakdown, meski tidak diminta eksplisit) — audit mencatat mana yang dipilih dan penilaian kewajaran. Yang TIDAK ditoleransi: `klasifikasi` selain `tunggal` (kalimat ini genuinely satu kebutuhan, bukan majemuk apa pun bentuknya) — kalau model salah tangkap jadi majemuk karena banyak kata benda, itu temuan nyata (mirip semangat S10, tapi untuk Langkah 4).

---

## Ringkasan Ekspektasi

| ID | Klasifikasi | Jumlah Intent | Relasi Kunci | Label Kunci | Verifikasi | Toleransi |
|---|---|---|---|---|---|---|
| S01 | tunggal | 1 | independen | nilai_tunggal | True | Tidak |
| S02 | majemuk_independen | 2 | independen×2 | — | True | Tidak |
| S03 | majemuk_bergantung | ≥2 | ≥1 bergantung valid | perbandingan | True | Tidak |
| S04 | majemuk_bergantung | ≥4 | ≥1 bergantung ke ≥2 | perbandingan | True | Struktur detail |
| S05 | bebas | — | — | — | True | Ya (klasifikasi bebas) |
| S06 | majemuk_bergantung | — | — | tren+perbandingan | True (akhir) | Ya (retry_count) |
| S07 | tunggal | 1 | independen | tren | True | Tidak |
| S08 | tunggal | 1 | independen | peringkat | True | Tidak |
| S09 | tunggal | 1 | independen | komposisi | True | Tidak |
| S10 | majemuk_independen | 2 | independen×2 | — | True | **Tidak — kritis** |
| S11 | — (VerifikasiResult) | — | — | — | False | Tidak |
| S12 | majemuk_independen | 4 | independen×4 | — | True | Tidak |
| S13 | eksploratif | — | — | — | eksploratif | Ya (boleh gagal replikasi) |
| S14 | tunggal | 1 | independen | nilai_tunggal/komposisi | True | Ya (label spesifik) |
