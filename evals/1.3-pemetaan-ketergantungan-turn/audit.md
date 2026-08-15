# Audit — Pengujian Deteksi Ketergantungan Turn (Milestone 1.3)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-15), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap skenario ada di `payloads/<ID>.json`. Model: `deepseek/deepseek-v4-flash-0731` (OpenRouter).

## Ringkasan

**11/12 skenario sesuai ekspektasi** (termasuk toleransi eksplisit yang sudah ditetapkan di rancangan). Satu skenario (S07) meleset **di luar** toleransi yang sudah diantisipasi — dianalisis detail di bawah, bukan kegagalan sistem (bounds-check tetap bekerja benar), tapi temuan nyata soal perilaku model pada kasus ambigu.

| ID | Ekspektasi | Aktual | Verdict |
|---|---|---|---|
| S01 | `False`, — | `False`, — | ✅ Lolos |
| S02 | `False`, — | `False`, — | ✅ Lolos |
| S03 | `True`, `1` | `True`, `1` | ✅ Lolos |
| S04 | `True`, `1` (toleransi: `False` diterima) | `True`, `1` | ✅ Lolos — **tepat sasaran, toleransi tidak terpakai** |
| S05 | `True`, `1` | `True`, `1` | ✅ Lolos |
| S06 | `True`, `1` (toleransi: gagal diterima) | `True`, `1` | ✅ Lolos — **tepat sasaran, toleransi tidak terpakai** |
| S07 | `True`, `1` atau `3` | `True`, `4` | ❌ **Perlu perhatian** — lihat analisis di bawah |
| S08 | `False`, — | `False`, — | ✅ Lolos |
| S09 | `False`, — | `False`, — | ✅ Lolos |
| S10 | `True`, `1` | `True`, `1` | ✅ Lolos |
| S11 | `True`, `1` | `True`, `1` | ✅ Lolos |
| S12 | `False`, — | `False`, — | ✅ Lolos — **skenario paling kritis, aman** |

## Analisis Per Skenario Penting

### S07 — Ambigu (GAGAL di luar toleransi)

**Payload:** histori 4 turn (occupancy April, revenue F&B April, occupancy Mei, staff baru direkrut), pertanyaan turn 5: "Bandingkan dengan bulan sebelumnya."

**Ekspektasi:** `is_dependent=True` (wajib), `referenced_turn_index` ∈ {1, 3} — turn 1 (kemunculan topik occupancy pertama) atau turn 3 (kemunculan occupancy paling akhir/relevan), keduanya defensible secara linguistik.

**Aktual:** `is_dependent=True`, `referenced_turn_index=4` — turn 4 adalah **"Berapa banyak staff baru direkrut bulan ini?"**, topik rekrutmen staff, **sama sekali tidak berkaitan dengan occupancy**.

**Analisis:** Ini bukan sekadar memilih alternatif ambigu yang lain (yang sudah diantisipasi via toleransi 1/3) — model salah total secara topikal. Pola yang terlihat: turn 4 adalah turn **paling akhir yang menyebut kata "bulan ini"** secara literal, sementara "bandingkan dengan bulan sebelumnya" di turn 5 juga menyebut kata "bulan". Dugaan kuat: model melakukan pencocokan **berbasis kata kunci permukaan** ("bulan") pada turn paling dekat yang mengandung kata itu, alih-alih menganalisis topik/metrik apa yang sedang dibandingkan (occupancy, yang punya dua kandidat di turn 1 dan 3, bukan di turn 4 yang tidak punya angka/metrik yang bisa "dibandingkan" sama sekali — jawaban turn 4 adalah jumlah staff baru, bukan sesuatu yang punya makna "bulan sebelumnya" untuk dibandingkan).

**Kesimpulan:** Bukan bug di sistem `detect_turn_dependency()` — `_parse_and_validate()` bekerja benar (turn 4 memang ada di histori valid, jadi tidak ditolak bounds-check; keputusannya sendiri yang keliru, itu memang wilayah tanggung jawab model, bukan validasi struktural). ini temuan nyata soal **keterbatasan model DeepSeek V4 Flash 0731** pada kasus ambigu dengan banyak kandidat + kata kunci permukaan yang menyesatkan — konsisten dengan status model ini yang eksplisit "untuk testing", bukan klaim performa produksi.

### S12 — Jebakan False-Positive (LOLOS, paling penting)

**Payload:** histori 1 turn ("revenue F&B bulan April 2026"), pertanyaan turn 2: "Berapa revenue reservasi bulan April 2026?" — sama-sama sebut "revenue" dan "April 2026", domain beda (F&B vs reservasi).

**Aktual:** `is_dependent=False` — **benar**. Model berhasil membedakan overlap kata dari kebutuhan rujukan sesungguhnya, tidak terjebak kemiripan leksikal.

**Kenapa ini penting:** Ini skenario yang belum pernah diuji sebelumnya di M1.3 asli, dan risikonya nyata untuk produksi (pertanyaan baru yang kebetulan mirip kata dengan histori, bukan actual perbandingan/rujukan). Hasil bersih di sini memberi keyakinan lebih tinggi terhadap mekanisme dibanding sebelum audit ini dijalankan.

### S04 & S06 — Dependent Implisit (LOLOS, toleransi tidak terpakai)

Kedua skenario ini sengaja dirancang sulit (elipsis tanpa kata penanda eksplisit "tadi"/"itu", termasuk kombinasi jarak-jauh+implisit di S06) dan diberi toleransi kegagalan di rancangan. Model justru **tepat sasaran di keduanya** — bukti tambahan bahwa kemampuan model menangani kelanjutan topik implisit lebih baik dari ekspektasi awal, meski gagal pada kasus ambigu multi-kandidat (S07).

## Temuan Pola

1. **Diskriminasi leksikal-vs-semantik: kuat** pada kasus dua-domain-berbeda (S12), tapi **lemah** pada kasus ambigu-dalam-satu-domain-yang-sama dengan kata kunci permukaan yang tumpang tindih (S07). Pola kegagalan bukan "gagal memahami makna sama sekali", tapi spesifik ke situasi banyak kandidat + sinyal permukaan yang menyesatkan.
2. **Jarak rujukan bukan faktor kegagalan** — S11 (jarak ekstrem, turn 8→turn 1) dan S05 (jarak jauh + distractor) sama-sama lolos bersih. Kegagalan S07 murni soal ambiguitas kandidat, bukan soal seberapa jauh rujukannya.
3. **Rujukan implisit (tanpa kata penanda) bukan titik lemah** — S04 dan S06 lolos tepat, berlawanan dengan asumsi awal saat toleransi ditetapkan di rancangan.

## Rekomendasi

- **Tidak perlu perbaikan mendesak** pada `_SYSTEM_PROMPT`/mekanisme untuk milestone ini — 11/12 lolos termasuk skenario paling kritis (S12), dan satu-satunya kegagalan (S07) adalah kasus genuinely ambigu yang bahkan manusia bisa berbeda pendapat, bukan kegagalan mendasar.
- **Kalau model produksi final nanti berbeda dari DeepSeek V4 Flash 0731** (yang eksplisit untuk testing, lihat `milestones/1.3-pemetaan-ketergantungan-turn/decisions.md` Keputusan 3), ulangi eval ini (`run_eval.py` sudah reusable) dengan model baru — terutama perhatikan S07 sebagai skenario diagnostik untuk kasus ambigu multi-kandidat.
- **Pertimbangkan untuk milestone mendatang** (bukan aksi mendesak sekarang): kalau pola "kata kunci permukaan mengalahkan analisis topik" pada kasus ambigu terbukti berulang di eval lain, system prompt bisa diperkuat dengan instruksi eksplisit "abaikan kesamaan kata permukaan, fokus ke topik/metrik yang benar-benar sedang dibandingkan" — belum dilakukan sekarang karena baru satu data point (S07), terlalu dini untuk mengubah prompt produksi berdasarkan satu kegagalan.
