# Rancangan Pengujian — Penulisan Ulang Pertanyaan Jadi Mandiri (Milestone 1.4)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada, bukan kriteria yang disesuaikan setelah lihat hasil. Struktur mirror `evals/1.3-pemetaan-ketergantungan-turn/rancangan.md`.

## Yang Diuji

`rewrite_to_standalone()` (`src/layers/context_resolution/rewrite.py`) — Milestone 1.4 sudah lolos 2 skenario minimal dari Kriteria Keberhasilan sumber (`tests/layers/context_resolution/test_rewrite.py`). Pengujian ini lebih menyeluruh, menutup dimensi yang belum diuji sebelumnya:

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Sudah mandiri, tanpa histori sama sekali | Tidak (tests/ langsung pakai kasus dengan histori kosong tapi tanpa distraktor) | S01 |
| Sudah mandiri meski histori ada tapi tidak relevan (anti false-positive dasar) | Tidak | S02 |
| Elipsis eksplisit, turn N-1 | Ya (kelompok a) | S03 |
| Elipsis **implisit** (tanpa kata penanda), turn N-1 | Tidak | S04 |
| Elipsis eksplisit, turn jauh + distractor | Tidak | S05 |
| Elipsis **implisit**, turn jauh + distractor | Tidak | S06 |
| Rujukan **ganda ambigu** (topik sama muncul 2×) | Tidak | S07 |
| **Negasi** eksplisit (pertanyaan baru disangkal terkait histori) | Tidak | S08 |
| Sesi **panjang** (10+ turn), tanpa elipsis apa pun | Tidak | S09 |
| Rujukan **pronoun/deiksis** ("itu") tanpa penyebutan ulang topik | Tidak | S10 |
| Kalimat **majemuk campuran** elipsis + non-elipsis | Tidak | S11 |
| **Jebakan overlap leksikal**: entitas mirip kata, domain berbeda | Tidak | S12 |

## Cara Baca Skenario

Tiap skenario: payload persis yang dikirim (`history` + `question` turn terakhir), `required_phrases` (semua harus muncul, case-insensitive, di `rewritten_question`) dan `forbidden_phrases` (tidak boleh muncul sama sekali — sinyal model menyisipkan entitas yang tidak relevan/salah tangkap). Skenario yang genuinely sulit (S04, S06, S07) diberi catatan toleransi eksplisit pada bagian yang memang sulit — bukan dilonggarkan setelah lihat hasil. Cek `forbidden_phrases` TIDAK PERNAH ditoleransi, bahkan pada skenario bertoleransi — itu batas keamanan dasar (anti-halusinasi/anti-salah-tangkap), beda dari kelengkapan resolusi yang boleh ditoleransi.

---

### S01 — Baseline: sudah mandiri, tanpa histori sama sekali

**Tujuan:** kasus paling sederhana, titik awal.

**Payload:** `turn_index=1`, `history=[]`, `question`: "Berapa occupancy rate properti kita bulan Juni 2026?"

**Ekspektasi:** `rewritten_question` mempertahankan entitas kunci tanpa distorsi.

**Kriteria Keberhasilan:** `required_phrases=["juni", "2026", "occupancy"]`, `forbidden_phrases=[]`. Tidak ada toleransi.

---

### S02 — Sudah mandiri meski histori ada tapi tidak relevan

**Tujuan:** pastikan model tidak menyisipkan entitas dari histori hanya karena histori ada (anti false-positive dasar).

**Payload:** `turn_index=2`, `history=[{1, "Berapa jumlah staff aktif di departemen HR?", "Departemen HR memiliki 8 staff aktif."}]`, `question`: "Apa saja fasilitas yang tersedia di area spa?"

**Ekspektasi:** `rewritten_question` tetap soal fasilitas spa, tidak menyisipkan entitas HR yang tidak relevan.

**Kriteria Keberhasilan:** `required_phrases=["spa", "fasilitas"]`, `forbidden_phrases=["hr", "8 staff"]`. Tidak ada toleransi.

---

### S03 — Elipsis eksplisit, turn N-1

**Tujuan:** kasus dasar resolusi komparatif eksplisit ke turn tepat sebelumnya.

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Bandingkan dengan bulan sebelumnya."

**Ekspektasi:** "bulan sebelumnya" dari Maret 2026 diresolusi jadi Februari 2026 eksplisit.

**Kriteria Keberhasilan:** `required_phrases=["februari", "2026", "reservasi"]`, `forbidden_phrases=[]`. Tidak ada toleransi.

---

### S04 — Elipsis implisit (tanpa penanda eksplisit), turn N-1

**Tujuan:** model harus menangkap kelanjutan topik lewat elipsis, bukan hanya kata kunci literal seperti "tadi"/"itu"/"bandingkan".

**Payload:** `turn_index=2`, `history=[{1, "Berapa rating kepuasan tamu untuk Front Office bulan ini?", "Rating kepuasan tamu Front Office bulan ini 4.6 dari 5."}]`, `question`: "Kalau untuk Housekeeping?"

**Ekspektasi:** idealnya "Berapa rating kepuasan tamu untuk Housekeeping bulan ini?".

**Kriteria Keberhasilan:** `required_phrases=["housekeeping", "rating", "kepuasan"]`, `forbidden_phrases=[]`. **Toleransi eksplisit:** kalau model gagal menangkap elipsis implisit (hasil rewrite tidak menyebut "rating"/"kepuasan" sama sekali), dicatat sebagai **temuan keterbatasan model**, bukan kegagalan sistem — selama kalimat hasil tetap valid gramatikal (bukan error/kosong).

---

### S05 — Elipsis eksplisit, turn jauh + distractor

**Tujuan:** replikasi kelas skenario tersulit M1.3 (turn jauh, ada distractor topik lain di antaranya) untuk tugas rewrite.

**Payload:** `turn_index=6`, `question`: "Balik lagi ke komplain yang di awal tadi, apa sudah ada tindak lanjutnya?"

`history`:
1. "Berapa jumlah komplain yang diterima Front Office bulan ini?" → "Front Office menerima 7 komplain bulan ini, mayoritas soal waktu check-in."
2. "Bagaimana kondisi kolam renang?" → "Kolam renang beroperasi normal, terakhir dibersihkan kemarin."
3. "Berapa revenue spa minggu ini?" → "Revenue spa minggu ini Rp 32 juta."
4. "Siapa yang bertugas shift malam hari ini?" → "Shift malam dipegang oleh 3 staff Front Office dan 2 staff Housekeeping."
5. "Berapa kamar yang sedang dalam maintenance?" → "5 kamar sedang dalam maintenance, estimasi selesai 3 hari."

**Ekspektasi:** "komplain yang di awal tadi" diresolusi ke komplain Front Office (turn 1), bukan topik turn 5 (maintenance, paling dekat tapi tidak nyambung).

**Kriteria Keberhasilan:** `required_phrases=["front office", "komplain"]`, `forbidden_phrases=["kolam renang", "maintenance", "shift malam"]` (sinyal salah tangkap ke turn distractor). Tidak ada toleransi pada bagian forbidden; penyebutan detail tambahan ("check-in", "7 komplain") dicatat di audit sebagai bukti kualitas resolusi tapi bukan syarat wajib lolos.

---

### S06 — Elipsis implisit, turn jauh + distractor

**Tujuan:** kombinasi tersulit — rujukan jauh DAN tanpa penanda eksplisit.

**Payload:** `turn_index=4`, `question`: "Naik atau turun dibanding minggu sebelumnya?"

`history`:
1. "Berapa booking spa yang masuk minggu ini?" → "Spa menerima 45 booking minggu ini."
2. "Bagaimana revenue F&B bulan ini?" → "Revenue F&B bulan ini Rp 450 juta."
3. "Berapa unit AC yang rusak di lantai 3?" → "3 unit AC di lantai 3 sedang dalam perbaikan."

**Ekspektasi:** idealnya "Naik atau turun booking spa dibanding minggu sebelumnya?" (turn 1 — satu-satunya topik mingguan/"minggu ini").

**Kriteria Keberhasilan:** `required_phrases=["spa"]`, `forbidden_phrases=["f&b", "ac", "lantai 3"]` (anti salah-tangkap ke turn 2/3 — WAJIB, tidak ditoleransi). **Toleransi eksplisit** hanya untuk kelengkapan resolusi: kalau model tidak menyebut kata "booking" secara eksplisit, itu masih diterima selama tetap menyebut "spa" dan tidak menyalahtangkap ke topik lain.

---

### S07 — Ambigu: topik sama muncul di 2 turn berbeda

**Tujuan:** uji perilaku model saat ada lebih dari satu kandidat turn yang relevan untuk diresolusi.

**Payload:** `turn_index=5`, `question`: "Bandingkan dengan bulan sebelumnya."

`history`:
1. "Berapa occupancy rate bulan April 2026?" → "Occupancy April 2026 mencapai 78%."
2. "Bagaimana dengan revenue F&B bulan yang sama?" → "Revenue F&B April 2026 Rp 450 juta."
3. "Berapa occupancy rate bulan Mei 2026?" → "Occupancy Mei 2026 mencapai 82%."
4. "Berapa banyak staff baru direkrut bulan ini?" → "5 staff baru direkrut bulan ini."

**Ekspektasi utama:** tetap soal occupancy, merujuk salah satu dari April (turn 1) atau Maret (bulan sebelum Mei, turn 3) — keduanya defensible secara linguistik.

**Kriteria Keberhasilan:** `required_phrases=["occupancy"]` **wajib** (tidak ada toleransi di bagian ini — jelas ada topik occupancy yang bisa dirujuk), `forbidden_phrases=["staff baru", "f&b"]` (anti salah tangkap ke topik non-occupancy). **Toleransi eksplisit:** bulan spesifik yang disebut (April/Maret/lainnya) tidak dipaksa satu jawaban benar — audit mencatat mana yang dipilih model beserta penilaian mana yang lebih masuk akal secara linguistik, mirror pola M1.3 S07.

---

### S08 — Negasi eksplisit

**Tujuan:** rujukan verbal eksplisit bahwa pertanyaan ini BARU, tidak terkait histori — walau ada histori yang tersedia dan memuat kata "tadi".

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Ini pertanyaan baru, tidak ada hubungannya dengan tadi: berapa staff maintenance yang aktif sekarang?"

**Ekspektasi:** `rewritten_question` soal staff maintenance, TIDAK mengimpor entitas revenue/reservasi/Maret dari histori meski kata "tadi" muncul literal di teks.

**Kriteria Keberhasilan:** `required_phrases=["staff", "maintenance"]`, `forbidden_phrases=["reservasi", "maret", "800 juta"]`. Tidak ada toleransi.

---

### S09 — Sesi panjang (10 turn histori), tanpa elipsis apa pun

**Tujuan:** robustness terhadap volume histori besar — pastikan tidak "kebanjiran" dan salah menyisipkan entitas dari histori yang tidak diminta.

**Payload:** `turn_index=11`, `question`: "Berapa jumlah kamar tipe suite yang tersedia?" (topik benar-benar baru, sudah mandiri).

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

**Ekspektasi:** `rewritten_question` tetap murni soal kamar suite, tanpa entitas dari 10 turn manapun tersisip.

**Kriteria Keberhasilan:** `required_phrases=["suite", "kamar"]`, `forbidden_phrases=["occupancy", "f&b", "housekeeping", "spa", "hr", "vip", "reservasi"]`. Tidak ada toleransi.

---

### S10 — Rujukan pronoun/deiksis ("itu") tanpa penyebutan ulang topik

**Tujuan:** model harus resolve rujukan bare pronoun jadi entitas eksplisit, bukan cuma menghapus kata "itu" tanpa mengisi konteks.

**Payload:** `turn_index=2`, `history=[{1, "Berapa banyak komplain yang diterima housekeeping bulan ini?", "Housekeeping menerima 12 komplain bulan ini, mayoritas soal kebersihan kamar."}]`, `question`: "Itu sudah ditindaklanjuti belum?"

**Ekspektasi:** idealnya "Apakah komplain housekeeping sudah ditindaklanjuti?" atau setara.

**Kriteria Keberhasilan:** `required_phrases=["housekeeping", "komplain"]`, `forbidden_phrases=[]`. Tidak ada toleransi (pronoun tunggal dengan histori 1-turn — kasus relatif sederhana, beda dari S04 yang implisit tanpa pronoun eksplisit sama sekali).

---

### S11 — Kalimat majemuk campuran elipsis + non-elipsis

**Tujuan:** uji apakah model membedakan bagian kalimat yang butuh resolusi dari bagian yang sudah mandiri dalam SATU kalimat majemuk — tidak boleh salah satunya terdistorsi atau hilang.

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue reservasi bulan Maret 2026?", "Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Bandingkan dengan bulan sebelumnya, dan juga berapa jumlah staff Front Office yang aktif sekarang?"

**Ekspektasi:** klausa pertama diresolusi ("bulan sebelumnya" → Februari 2026), klausa kedua (soal staff Front Office, sudah mandiri) tetap utuh — tidak ada yang hilang.

**Kriteria Keberhasilan:** `required_phrases=["februari", "2026", "front office", "staff"]`, `forbidden_phrases=[]`. Tidak ada toleransi.

---

### S12 — Jebakan overlap leksikal: entitas mirip kata, domain berbeda

**Tujuan:** skenario **paling penting** dalam rancangan ini — menguji apakah model membedakan kemiripan kata (leksikal) dari kebutuhan resolusi sesungguhnya. Pertanyaan ini SUDAH mandiri sejak awal (menyebut domain dan periode eksplisit), histori hanya kebetulan berbagi kata "revenue" dan "April 2026".

**Payload:** `turn_index=2`, `history=[{1, "Berapa revenue F&B bulan April 2026?", "Revenue F&B April 2026 sebesar Rp 450 juta."}]`, `question`: "Berapa revenue reservasi bulan April 2026 tahun ini?"

**Ekspektasi:** diteruskan pada dasarnya tanpa perubahan makna (domain reservasi tetap, TIDAK diganti/dicampur dengan nilai F&B Rp 450 juta).

**Kriteria Keberhasilan:** `required_phrases=["reservasi", "april", "2026"]`, `forbidden_phrases=["f&b", "450"]` — **tidak ada toleransi**. Kalau model menyisipkan nilai/domain F&B, ini temuan signifikan (bukan sekadar keterbatasan minor) — dicatat sebagai temuan utama di `audit.md`, indikasi model mengandalkan kecocokan kata alih-alih pemahaman makna, dengan konsekuensi nyata: risiko mencemari pertanyaan yang sebenarnya independen di produksi.

---

## Ringkasan Ekspektasi

| ID | `required_phrases` | `forbidden_phrases` | Toleransi |
|---|---|---|---|
| S01 | juni, 2026, occupancy | — | Tidak |
| S02 | spa, fasilitas | hr, 8 staff | Tidak |
| S03 | februari, 2026, reservasi | — | Tidak |
| S04 | housekeeping, rating, kepuasan | — | Ya (implisit dekat) |
| S05 | front office, komplain | kolam renang, maintenance, shift malam | Tidak (forbidden wajib) |
| S06 | spa | f&b, ac, lantai 3 | Ya (kelengkapan "booking"), forbidden tetap wajib |
| S07 | occupancy | staff baru, f&b | Ya (bulan spesifik, ambigu) |
| S08 | staff, maintenance | reservasi, maret, 800 juta | Tidak |
| S09 | suite, kamar | occupancy, f&b, housekeeping, spa, hr, vip, reservasi | Tidak |
| S10 | housekeeping, komplain | — | Tidak |
| S11 | februari, 2026, front office, staff | — | Tidak |
| S12 | reservasi, april, 2026 | f&b, 450 | **Tidak — paling kritis** |
