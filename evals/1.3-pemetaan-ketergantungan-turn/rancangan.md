# Rancangan Pengujian — Pemetaan Ketergantungan Turn (Milestone 1.3)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada, bukan kriteria yang disesuaikan setelah lihat hasil.

## Yang Diuji

`detect_turn_dependency()` (`src/layers/context_resolution/turn_dependency.py`) — Milestone 1.3 sudah lolos 3 skenario minimal dari Kriteria Keberhasilan sumber. Pengujian ini lebih menyeluruh, menutup dimensi yang belum diuji sebelumnya:

| Dimensi | Sudah diuji M1.3 asli? | Skenario di sini |
|---|---|---|
| Independen tanpa histori | Ya (Kelompok B) | S01 |
| Independen meski histori ada (tidak relevan) | Tidak | S02 |
| Dependent eksplisit, turn N-1 | Ya (Kelompok A) | S03 |
| Dependent **implisit** (tanpa kata penanda), turn N-1 | Tidak | S04 |
| Dependent eksplisit, turn jauh + distractor | Ya (Kelompok C) | S05 |
| Dependent **implisit**, turn jauh + distractor | Tidak | S06 |
| Rujukan **ambigu** (topik sama 2×) | Tidak | S07 |
| **Negasi** eksplisit | Tidak | S08 |
| Sesi **panjang** (10+ turn), tanpa dependency | Tidak | S09 |
| Rujukan **pronoun/deiksis** ("itu") | Tidak | S10 |
| Rujukan ke turn **paling awal** dari sesi sangat panjang (jarak ekstrem) | Tidak | S11 |
| **Jebakan false-positive**: overlap leksikal, domain beda | Tidak | S12 |

## Cara Baca Skenario

Tiap skenario: payload persis yang dikirim (`history` + `question` turn terakhir), ekspektasi (`is_dependent`, `referenced_turn_index`), dan kriteria keberhasilan konkret. Skenario yang genuinely ambigu (S04, S06, S07) diberi catatan toleransi eksplisit — bukan dilonggarkan setelah lihat hasil.

---

### S01 — Baseline: independen tanpa histori sama sekali

**Tujuan:** kasus paling sederhana, titik awal.

**Payload:** `turn_index=1`, `history=[]`, `question`: "Berapa occupancy rate properti kita bulan Juni 2026?"

**Ekspektasi:** `is_dependent=False`, `referenced_turn_index=None`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi.

---

### S02 — Independen meski histori ada tapi tidak relevan

**Tujuan:** pastikan model tidak menandai dependent hanya karena histori ada (anti false-positive dasar).

**Payload:** `turn_index=2`, `history=[{1, "Berapa jumlah staff aktif di departemen HR?", "Departemen HR memiliki 8 staff aktif."}]`, `question`: "Apa saja fasilitas yang tersedia di area spa?"

**Ekspektasi:** `False`, `None`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi.

---

### S03 — Dependent eksplisit, turn N-1

**Tujuan:** kasus dasar rujukan eksplisit ke turn tepat sebelumnya.

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Bandingkan dengan bulan sebelumnya."

**Ekspektasi:** `True`, `1`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi.

---

### S04 — Dependent implisit (tanpa penanda eksplisit), turn N-1

**Tujuan:** model harus menangkap kelanjutan topik lewat elipsis, bukan hanya kata kunci literal seperti "tadi"/"itu"/"bandingkan".

**Payload:** `turn_index=2`, `history=[{1, "Berapa rating kepuasan tamu untuk Front Office bulan ini?", "Rating kepuasan tamu Front Office bulan ini 4.6 dari 5."}]`, `question`: "Kalau untuk Housekeeping?"

**Ekspektasi:** `True`, `1`.

**Kriteria Keberhasilan:** idealnya persis sesuai ekspektasi. **Toleransi eksplisit:** kalau model menjawab `False` (gagal menangkap elipsis implisit), ini dicatat sebagai **temuan keterbatasan model**, bukan kegagalan sistem — `_parse_and_validate()` tetap bekerja benar selama tidak ada `referenced_turn_index` yang mengarang di luar histori.

---

### S05 — Dependent eksplisit, turn jauh + distractor

**Tujuan:** replikasi kelas skenario tersulit M1.3 asli (turn jauh, ada distractor topik lain di antaranya) dengan konten baru — memperluas bukti, bukan mengulang.

**Payload:** `turn_index=6`, `question`: "Balik lagi ke soal komplain Front Office tadi, sudah ada tindak lanjutnya?"

`history`:
1. "Berapa jumlah komplain yang diterima Front Office bulan ini?" → "Front Office menerima 7 komplain bulan ini, mayoritas soal waktu check-in."
2. "Bagaimana kondisi kolam renang?" → "Kolam renang beroperasi normal, terakhir dibersihkan kemarin."
3. "Berapa revenue spa minggu ini?" → "Revenue spa minggu ini Rp 32 juta."
4. "Siapa yang bertugas shift malam hari ini?" → "Shift malam dipegang oleh 3 staff Front Office dan 2 staff Housekeeping."
5. "Berapa kamar yang sedang dalam maintenance?" → "5 kamar sedang dalam maintenance, estimasi selesai 3 hari."

**Ekspektasi:** `True`, `1` (bukan turn 5 yang paling dekat tapi topiknya tidak nyambung).

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi (ini kelas skenario yang sudah terbukti bisa dipenuhi model di M1.3 asli).

---

### S06 — Dependent implisit, turn jauh + distractor

**Tujuan:** kombinasi tersulit — rujukan jauh DAN tanpa penanda eksplisit.

**Payload:** `turn_index=4`, `question`: "Naik atau turun dibanding minggu sebelumnya?"

`history`:
1. "Berapa booking spa yang masuk minggu ini?" → "Spa menerima 45 booking minggu ini."
2. "Bagaimana revenue F&B bulan ini?" → "Revenue F&B bulan ini Rp 450 juta."
3. "Berapa unit AC yang rusak di lantai 3?" → "3 unit AC di lantai 3 sedang dalam perbaikan."

**Ekspektasi:** `True`, `1`.

**Kriteria Keberhasilan:** idealnya persis sesuai ekspektasi. **Toleransi eksplisit:** skenario ini sengaja didesain sulit (implisit + tidak langsung sebelumnya) — kalau model gagal (`False`, atau `True` dengan `referenced_turn_index` salah), dicatat sebagai keterbatasan model testing, BUKAN bug — tapi kalau `referenced_turn_index` yang dihasilkan berada di luar `{1,2,3}` sama sekali, itu tetap harus ditangkap `_parse_and_validate()` (bounds-check tidak boleh gagal, itu bukan toleransi).

---

### S07 — Ambigu: topik sama muncul di 2 turn berbeda

**Tujuan:** uji tie-breaking model saat ada lebih dari satu kandidat turn yang relevan.

**Payload:** `turn_index=5`, `question`: "Bandingkan dengan bulan sebelumnya."

`history`:
1. "Berapa occupancy rate bulan April 2026?" → "Occupancy April 2026 mencapai 78%."
2. "Bagaimana dengan revenue F&B bulan yang sama?" → "Revenue F&B April 2026 Rp 450 juta."
3. "Berapa occupancy rate bulan Mei 2026?" → "Occupancy Mei 2026 mencapai 82%."
4. "Berapa banyak staff baru direkrut bulan ini?" → "5 staff baru direkrut bulan ini."

**Ekspektasi utama:** `True`, `3` (occupancy Mei — kemunculan topik occupancy paling akhir/relevan, "bulan sebelumnya" dari Mei secara alami merujuk balik ke pembahasan occupancy terakhir).

**Kriteria Keberhasilan:** `is_dependent=True` **wajib** (tidak ada toleransi di bagian ini — jelas ada topik occupancy yang bisa dirujuk). `referenced_turn_index` **diterima kalau bernilai `1` ATAU `3`** — keduanya defensible (turn 1 = kemunculan topik pertama, turn 3 = kemunculan paling akhir). Audit mencatat mana yang dipilih model beserta penilaian mana yang lebih masuk akal secara linguistik.

---

### S08 — Negasi eksplisit

**Tujuan:** rujukan verbal eksplisit bahwa pertanyaan ini BARU, tidak terkait histori — walau ada histori yang tersedia.

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Ini pertanyaan baru, tidak ada hubungannya dengan tadi: berapa staff maintenance yang aktif sekarang?"

**Ekspektasi:** `False`, `None`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi (petunjuk negasi eksplisit sangat jelas dalam teks).

---

### S09 — Sesi panjang (10 turn histori), tanpa dependency

**Tujuan:** robustness terhadap volume histori besar — pastikan tidak "kebanjiran" dan salah menandai dependent karena banyaknya konteks.

**Payload:** `turn_index=11`, `question`: "Berapa jumlah kamar tipe suite yang tersedia?" (topik benar-benar baru).

`history` (10 entri, topik berbeda-beda — occupancy, F&B, housekeeping, maintenance, spa, staff performa, HR, finance, komplain tamu, reservasi):
1. "Berapa occupancy rate April 2026?" → "78%."
2. "Revenue F&B bulan ini?" → "Rp 450 juta."
3. "Komplain housekeeping bulan ini?" → "12 komplain."
4. "Kondisi maintenance AC lantai 3?" → "3 unit diperbaiki."
5. "Booking spa minggu ini?" → "45 booking."
6. "Staff terbaik bulan ini?" → "Sari dari Front Office."
7. "Staff HR aktif?" → "8 staff."
8. "Revenue financial Q1 2026?" → "Rp 2.1 miliar."
9. "Ada komplain tamu VIP?" → "1 komplain, sudah ditangani GM."
10. "Revenue reservasi bulan lalu?" → "Rp 800 juta."

**Ekspektasi:** `False`, `None`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi (topik kamar suite sama sekali tidak disinggung di 10 turn manapun).

---

### S10 — Rujukan pronoun/deiksis ("itu") tanpa penyebutan ulang topik

**Tujuan:** model harus resolve rujukan bare pronoun, bukan cuma cocokkan kata kunci literal.

**Payload:** `turn_index=2`, `history=[{1, "Berapa banyak komplain yang diterima housekeeping bulan ini?", "Housekeeping menerima 12 komplain bulan ini, mayoritas soal kebersihan kamar."}]`, `question`: "Itu sudah ditindaklanjuti belum?"

**Ekspektasi:** `True`, `1`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi.

---

### S11 — Rujukan ke turn paling awal dari sesi sangat panjang (jarak ekstrem)

**Tujuan:** uji jarak rujukan paling ekstrem yang pernah diuji (turn 8 → turn 1) — melampaui skenario tersulit M1.3 asli (turn 7 → turn 3).

**Payload:** `turn_index=8`, `question`: "Balik lagi ke soal occupancy di awal tadi, apakah ada proyeksi untuk bulan depan?"

`history`:
1. "Berapa occupancy rate bulan April 2026?" → "Occupancy April 2026 mencapai 78%."
2. "Bagaimana revenue F&B?" → "Revenue F&B Rp 450 juta."
3. "Berapa komplain housekeeping?" → "12 komplain, mayoritas kebersihan kamar."
4. "Kondisi maintenance AC lantai 3?" → "3 unit sedang diperbaiki."
5. "Booking spa minggu ini?" → "45 booking."
6. "Siapa staff terbaik bulan ini?" → "Sari dari Front Office."
7. "Berapa staff HR aktif?" → "8 staff aktif."

**Ekspektasi:** `True`, `1`.

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — tidak ada toleransi (rujukan eksplisit "di awal tadi" + topik occupancy hanya muncul di turn 1).

---

### S12 — Jebakan false-positive: overlap leksikal, domain berbeda

**Tujuan:** skenario **paling penting** dalam rancangan ini — belum pernah diuji sama sekali sebelumnya. Menguji apakah model membedakan kemiripan kata (leksikal) dari kebutuhan rujukan sesungguhnya (semantik).

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue F&B bulan April 2026?", "Revenue F&B April 2026 sebesar Rp 450 juta."}]`, `question`: "Berapa revenue reservasi bulan April 2026?"

**Ekspektasi:** `False`, `None` — ini pertanyaan baru yang genuinely independen (domain F&B vs reservasi berbeda total), meski sama-sama menyebut kata "revenue" dan "April 2026".

**Kriteria Keberhasilan:** harus persis sesuai ekspektasi — **tidak ada toleransi**. Kalau model menjawab `True`, ini temuan signifikan (bukan sekadar keterbatasan minor) — dicatat sebagai temuan utama di `audit.md`, karena mengindikasikan model mengandalkan kecocokan kata alih-alih pemahaman makna, dengan konsekuensi nyata: risiko false-positive di produksi untuk pertanyaan yang kebetulan mirip kata tapi beda maksud.

---

## Ringkasan Ekspektasi

| ID | `is_dependent` | `referenced_turn_index` | Toleransi |
|---|---|---|---|
| S01 | False | — | Tidak |
| S02 | False | — | Tidak |
| S03 | True | 1 | Tidak |
| S04 | True | 1 | Ya (implisit dekat) |
| S05 | True | 1 | Tidak |
| S06 | True | 1 | Ya (implisit jauh) |
| S07 | True | 1 atau 3 | Ya (ambigu, keduanya defensible) |
| S08 | False | — | Tidak |
| S09 | False | — | Tidak |
| S10 | True | 1 | Tidak |
| S11 | True | 1 | Tidak |
| S12 | False | — | **Tidak — paling kritis** |
