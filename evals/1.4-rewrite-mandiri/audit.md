# Audit — Pengujian Penulisan Ulang Pertanyaan Jadi Mandiri (Milestone 1.4)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-15), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap skenario ada di `payloads/<ID>.json`. Model: `qwen/qwen3-32b` (OpenRouter).

## Ringkasan

**10/12 skenario lolos secara ketat lewat pencocokan `required_phrases`/`forbidden_phrases`.** Setelah audit manual, **11/12 sebenarnya benar secara makna** — satu (S01) adalah kegagalan alat ukur (paraphrase Indonesia yang sah, bukan kegagalan model), dianalisis di bawah. Satu (S07) adalah temuan nyata soal keterbatasan model pada kasus ambigu — konsisten pola yang sama ditemukan di `evals/1.3-.../audit.md` S07 (DeepSeek), kali ini terulang pada Qwen3-32B dengan tugas berbeda (rewrite, bukan deteksi ketergantungan).

| ID | Ekspektasi (required/forbidden) | Hasil Rewrite | Verdict Harness | Verdict Manual |
|---|---|---|---|---|
| S01 | juni, 2026, occupancy / — | "Berapa tingkat keterisian properti kita pada bulan Juni tahun 2026?" | ❌ REVIEW (kata "occupancy" tak muncul) | ✅ **Benar** — "tingkat keterisian" adalah terjemahan sah "occupancy rate", Juni+2026 eksplisit |
| S02 | spa, fasilitas / hr, 8 staff | "Apa saja fasilitas yang tersedia di area spa?" | ✅ Lolos | ✅ Benar |
| S03 | februari, 2026, reservasi / — | "Berapa revenue reservasi bulan Maret 2026 dibandingkan dengan bulan Februari 2026?" | ✅ Lolos | ✅ Benar |
| S04 | housekeeping, rating, kepuasan / — (toleransi) | "Berapa rating kepuasan tamu untuk Housekeeping bulan ini?" | ✅ Lolos | ✅ Benar — **tepat sasaran, toleransi tidak terpakai** |
| S05 | front office, komplain / kolam renang, maintenance, shift malam | "Apa sudah ada tindak lanjut terhadap 7 komplain Front Office bulan ini yang mayoritas soal waktu check-in?" | ✅ Lolos | ✅ Benar — bahkan menyertakan detail "7 komplain"/"check-in" (bonus, bukan syarat wajib) |
| S06 | spa / f&b, ac, lantai 3 (toleransi kelengkapan) | "Booking spa minggu ini naik atau turun dibanding jumlah booking spa minggu sebelumnya?" | ✅ Lolos | ✅ Benar — **tepat sasaran, toleransi tidak terpakai** (bahkan menyebut "booking" eksplisit) |
| S07 | occupancy / staff baru, f&b (toleransi bulan spesifik) | "Berapa banyak staff baru direkrut di bulan Mei 2026 dibandingkan dengan bulan April 2026?" | ❌ REVIEW | ❌ **Salah** — lihat analisis di bawah, di luar toleransi yang diantisipasi |
| S08 | staff, maintenance / reservasi, maret, 800 juta | "Berapa jumlah staff maintenance yang aktif saat ini?" | ✅ Lolos | ✅ Benar — negasi eksplisit berhasil dipatuhi |
| S09 | suite, kamar / 7 topik lain | "Berapa jumlah kamar tipe suite yang tersedia?" | ✅ Lolos | ✅ Benar — tahan terhadap 10 turn histori tak relevan |
| S10 | housekeeping, komplain / — | "Apakah 12 komplain yang diterima housekeeping bulan ini sudah ditindaklanjuti?" | ✅ Lolos | ✅ Benar — bahkan menyertakan angka "12" (bonus) |
| S11 | februari, 2026, front office, staff / — | "Bandingkan revenue reservasi Maret 2026 dengan Februari 2026, dan berapa jumlah staff Front Office yang aktif saat ini?" | ✅ Lolos | ✅ Benar — kedua klausa majemuk terjaga, tidak ada yang hilang |
| S12 | reservasi, april, 2026 / f&b, 450 | "Berapa revenue reservasi bulan April 2026?" | ✅ Lolos | ✅ Benar — **skenario paling kritis, aman**: tidak tercemar nilai/domain F&B dari histori |

## Analisis Per Skenario Penting

### S01 — Kegagalan Alat Ukur, Bukan Kegagalan Model

**Payload:** tanpa histori, "Berapa occupancy rate properti kita bulan Juni 2026?"

**Hasil:** "Berapa tingkat keterisian properti kita pada bulan Juni tahun 2026?"

**Analisis:** Model menerjemahkan "occupancy rate" jadi padanan Bahasa Indonesia "tingkat keterisian" — terjemahan yang sah dan setara makna, bukan distorsi. Entitas kunci (Juni, 2026) tetap eksplisit. `required_phrases` di `rancangan.md` secara keliru mengasumsikan istilah Inggris "occupancy" akan dipertahankan verbatim — asumsi yang tidak berdasar untuk tugas generatif berbahasa Indonesia (beda dari M1.3 yang outputnya JSON terstruktur dengan nilai pasti, bukan parafrasa bebas).

**Kesimpulan:** Bukan bug sistem maupun keterbatasan model — ini **keterbatasan metodologi eval** (pencocokan substring kaku tidak menangkap sinonim/parafrasa sah). Dicatat sebagai temuan metodologi di bagian Rekomendasi, bukan kegagalan `rewrite_to_standalone()`.

### S07 — Ambigu (GAGAL di luar toleransi, temuan nyata)

**Payload:** histori 4 turn (occupancy April, revenue F&B April, occupancy Mei, staff baru direkrut "bulan ini"), pertanyaan turn 5: "Bandingkan dengan bulan sebelumnya."

**Ekspektasi:** tetap soal occupancy (required wajib), boleh merujuk April atau Maret sebagai bulan pembanding (toleransi eksplisit pada bagian ini saja).

**Hasil:** "Berapa banyak staff baru direkrut di bulan Mei 2026 dibandingkan dengan bulan April 2026?" — model melanjutkan topik turn 4 (staff baru direkrut), BUKAN topik occupancy sama sekali. `required_phrases=["occupancy"]` tidak terpenuhi, `forbidden_phrases` "staff baru" justru muncul.

**Analisis:** Model tampak berpegang pada **turn paling akhir sebelum pertanyaan saat ini** (recency bias) alih-alih menimbang topik mana yang punya struktur "bisa dibandingkan antar-bulan" secara wajar (occupancy, yang punya dua data point eksplisit di turn 1 dan 3). Turn 4 sendiri cuma py satu data point ("5 staff baru bulan ini", tanpa bulan sebelumnya untuk dibandingkan) — secara logis kurang koheren untuk "dibandingkan dengan bulan sebelumnya", tapi model tetap memilihnya. **Pola ini identik dengan temuan S07 di `evals/1.3-.../audit.md`** (DeepSeek V4 Flash 0731 pada tugas deteksi ketergantungan) — di sana pun model salah tangkap ke turn paling akhir yang py kata kunci permukaan mirip ("bulan ini"), bukan turn yang topiknya benar-benar koheren untuk dibandingkan. Temuan ini sekarang terkonfirmasi berulang lintas model (Qwen3-32B) DAN lintas tugas (rewrite, bukan cuma deteksi) — mengindikasikan pola kegagalan pada kasus ambigu-multi-kandidat mungkin lebih fundamental (karakteristik umum LLM pada tugas resolusi rujukan ambigu), bukan spesifik satu model.

**Kesimpulan:** Bukan bug `rewrite_to_standalone()` — mekanisme bekerja benar (menghasilkan kalimat mandiri yang valid gramatikal, tidak error/kosong). Ini keterbatasan model pada kasus genuinely ambigu dengan distraktor topikal yang recency-nya lebih tinggi, konsisten status Qwen3-32B yang belum diklaim final produksi.

## Temuan Tambahan (di Luar Cakupan `rancangan.md`)

### Bug Ditemukan Saat Eksekusi Pertama: `response.choices` Kosong (Transient)

Eksekusi pertama `run_eval.py` crash di S02 dengan `TypeError: 'NoneType' object is not subscriptable` — `response.choices` kosong meski API call sukses (200 OK, bukan exception). Diverifikasi lewat pemanggilan ulang manual (3× retry payload identik) bahwa ini **transient**, tidak reproducible dengan payload yang sama — kemungkinan hiccup provider (`SiliconFlow`, provider backend Qwen3-32B di OpenRouter) di bawah beban 12 pemanggilan berurutan cepat.

**Perbaikan diterapkan** (di luar scope asli `rancangan.md`, tapi perlu dicatat karena mengubah kode produksi):
- `src/layers/context_resolution/rewrite.py`: `rewrite_to_standalone()` sekarang cek `response.choices` kosong sebelum indexing, fallback ke `payload.question` asli + span attribute `rewrite.forced_fallback_reason="no_choices_in_response"` — melengkapi Keputusan 8 `decisions.md` yang sudah menyebut "respons kosong" sebagai pemicu fallback, tapi implementasi awal belum menutup celah ini secara spesifik.
- `evals/1.4-rewrite-mandiri/run_eval.py`: `_call_with_retry()` — retry sampai 3× kalau `choices` kosong. Sengaja terpisah dari fallback produksi (yang fail-fast ke teks asli tanpa retry) karena skrip eval bertujuan mengumpulkan data kualitas model, bukan melayani request pengguna nyata.

Eksekusi ulang setelah perbaikan (data di tabel Ringkasan di atas) berjalan mulus tanpa error di 12/12 skenario.

### Qwen3-32B Beroperasi dalam Mode Reasoning/Thinking

Saat debugging bug di atas, ditemukan setiap respons Qwen3-32B menyertakan field `reasoning` (chain-of-thought internal) yang cukup panjang sebelum jawaban akhir — utilisasi token output jauh lebih tinggi dari perkiraan awal untuk tugas "ringan" ini (output token per skenario berkisar 117-636, lihat `payloads/*.json` field `usage`). Ini TIDAK terlihat di riset harga awal (Keputusan 1 `decisions.md`) karena harga per-token OpenRouter yang dikutip tidak membedakan token reasoning vs token jawaban akhir — biaya efektif per-request lebih tinggi dari yang tersirat murni dari angka $0.08/$0.28 per 1M token kalau dihitung dari jumlah kata jawaban akhir saja.

**Dampak:** Tidak mengubah kelolosan fungsional (seluruh skenario tetap dalam rentang latensi wajar untuk testing), tapi relevan untuk estimasi biaya produksi kalau model ini dipakai pada volume tinggi.

### Heuristic Verifikasi Deterministik (`_detect_residual_reference`) Tidak Pernah Terpicu

Di seluruh 12 skenario (termasuk yang punya histori dan seharusnya perlu resolusi), `residual_reference_phrases` selalu kosong (lihat kolom `residual` di data mentah) — heuristic ruang-tertutup (Keputusan 2 `decisions.md`) tidak pernah mendeteksi frasa penanda rujukan sisa, karena model konsisten berhasil meresolusi rujukan (bahkan pada S07 yang salah topik, hasilnya tetap kalimat yang sepenuhnya "mandiri" secara linguistik — cuma salah target, bukan gagal menulis ulang). Belum ada bukti positif ATAUPUN negatif soal kegunaan heuristic ini dari data sejauh ini — perlu data lebih banyak (mis. model yang lebih lemah, atau skenario yang sengaja memancing model gagal total) sebelum bisa dinilai efektivitasnya.

## Temuan Pola

1. **Kualitas resolusi eksplisit: sangat kuat** — 10/11 skenario yang genuinely butuh resolusi (S03-S06, S08, S10-S12; S09 tidak butuh resolusi) berhasil sempurna, termasuk kasus tersulit yang sengaja diberi toleransi (S04, S06) yang justru tepat sasaran tanpa perlu toleransi.
2. **Diskriminasi leksikal-vs-semantik: kuat** pada kasus dua-domain-berbeda dengan overlap kata (S12, paling kritis, aman) dan negasi eksplisit (S08).
3. **Kelemahan konsisten pada kasus ambigu-multi-kandidat dengan distraktor topikal yang lebih baru (recency bias)** — S07 di sini mereplikasi persis pola kegagalan S07 M1.3, lintas model dan lintas tugas. Ini pola paling signifikan dari seluruh eval M1.3+M1.4 sejauh ini.
4. **Volume histori besar (S09) bukan faktor kegagalan** — konsisten temuan S09/S11 M1.3.

## Rekomendasi

- **Tidak perlu perbaikan mendesak** pada `_SYSTEM_PROMPT`/mekanisme rewrite untuk milestone ini — 11/12 benar secara makna (setelah koreksi metodologi S01), termasuk skenario paling kritis (S12) dan kasus implisit tersulit (S04, S06).
- **Perbaikan metodologi eval untuk milestone LLM generatif berikutnya:** pencocokan `required_phrases`/`forbidden_phrases` berbasis substring literal punya batas nyata untuk tugas yang outputnya bebas berbahasa alami (beda dari M1.3 yang outputnya JSON terstruktur) — S01 murni false-negative alat ukur. Pertimbangkan menambah daftar sinonim yang diterima per skenario (mis. `required_phrases_any=[["occupancy", "tingkat keterisian", "keterisian"]]`) untuk milestone rewrite/generatif berikutnya (M1.7 dst kalau relevan).
- **Pola recency bias pada kasus ambigu (temuan #3) muncul dua kali berturut-turut lintas model/tugas** — cukup kuat untuk dipertimbangkan sebagai perhatian desain di Milestone 1.6/1.7 (Decomposition, Pencocokan) yang juga akan berurusan dengan resolusi rujukan/pencocokan. Belum aksi mendesak sekarang (baru 2 data point total lintas kedua milestone), tapi layak jadi skenario uji eksplisit kalau milestone tersebut nanti menyentuh kasus serupa.
- **Kalau model produksi final nanti berbeda dari Qwen3-32B** (eksplisit untuk testing, lihat `decisions.md` Keputusan 1), ulangi eval ini (`run_eval.py` sudah reusable) dengan model baru — terutama perhatikan S07 sebagai skenario diagnostik ambigu, dan pantau apakah pola reasoning-token-tinggi juga muncul di model lain.
