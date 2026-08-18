# Audit — Pengujian Penyusunan Narasi (Milestone 4.4)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18, satu kali run, 13/13 skenario berhasil dipanggil tanpa error), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload+narasi lengkap tiap skenario ada di `payloads/<ID>.json`. Model: `qwen/qwen3-32b` (Keputusan 1 `decisions.md`), `temperature=0`.

**Beda mendasar dari audit milestone LLM sebelumnya (M1.6/M1.7/dst.)**: output di sini adalah teks bebas, bukan keputusan terstruktur — verdict akhir tiap skenario adalah hasil **audit manual** (membaca narasi dan menilai apakah memenuhi ekspektasi kualitatif), heuristik otomatis hanya sinyal pendukung (dan terbukti punya false-negative di 2 skenario, lihat Analisis).

## Ringkasan

**13/13 skenario LOLOS audit manual** — seluruh 7 instruksi wajib prompt (`src/prompts/interpretation/narasi.md`) teramati bekerja benar di skenario yang dirancang khusus mengujinya, termasuk kedua skenario paling kritis (S04 — kontras nada berdampingan KK2; S11 — larangan klaim sebab-akibat). Heuristik otomatis 11/13 LOLOS; 2 REVIEW (S05, S10) keduanya **false-negative heuristik**, dikonfirmasi manual sebagai narasi yang BENAR (lihat Analisis) — bukan temuan kegagalan mekanisme.

| ID | Dimensi | Heuristik | Verdict Manual | Kategori |
|---|---|---|---|---|
| S01 | Campuran sumber (KK1) | ✅ Lolos | ✅ Lolos | — |
| S02 | `ditolak_otorisasi` spesifik (KK2a) | ✅ Lolos | ✅ Lolos | — |
| S03 | `gagal_teknis` tanpa detail teknis (KK2b) | ✅ Lolos | ✅ Lolos | Temuan minor (lihat Analisis) |
| S04 | Kontras nada berdampingan (KK2, **kritis**) | N/A | ✅ Lolos — **kritis, bersih** | — |
| S05 | Sebagian, flagged | ⚠️ REVIEW | ✅ Lolos | **False-negative heuristik** |
| S06 | Sebagian, stale | ✅ Lolos | ✅ Lolos | — |
| S07 | Berhasil murni (baseline negatif) | ✅ Lolos | ✅ Lolos | — |
| S08 | Terblokir ketergantungan 1 level | ✅ Lolos | ✅ Lolos | Temuan minor (lihat Analisis) |
| S09 | Terblokir ketergantungan rantai 2 level | N/A | ✅ Lolos — **melampaui ekspektasi minimum** | — |
| S10 | Nullable-bermakna jujur | ⚠️ REVIEW | ✅ Lolos | **False-negative heuristik (negasi)** |
| S11 | Larangan klaim sebab-akibat (**kritis kedua**) | ✅ Lolos | ✅ Lolos — **kritis, bersih** | — |
| S12 | Kejujuran total kegagalan | ✅ Lolos | ✅ Lolos | — |
| S13 | Lintas-turn ganda | N/A (turn_reference deterministik: ✅) | ✅ Lolos | — |

## Analisis Per Skenario Penting

### S04 — Kontras Nada Berdampingan (LOLOS, Paling Kritis)

**Narasi:** "...occupancy rate ... tercatat sebesar 75%, yang merupakan hasil perhitungan baru pada turn ini. Namun, **sistem mengalami kendala teknis** saat mengambil data revenue reservasi, sehingga informasi tersebut tidak dapat disajikan. Selain itu, **akses terhadap data gaji staff bernama Budi tidak dapat diberikan karena keterbatasan kewenangan sistem**."

**Analisis:** Model membedakan SECARA JELAS dua kalimat terpisah dengan pemicu kata berbeda persis sesuai instruksi 3 vs 4 prompt — "kendala teknis" (gagal_teknis, netral, tanpa jargon) vs "keterbatasan kewenangan" (ditolak_otorisasi, eksplisit soal akses). Kebutuhan berhasil (occupancy) tetap disajikan normal di kalimat pertama, TIDAK ikut "tenggelam" oleh dua kegagalan lain. Ini skenario yang paling representasikan kalimat KK2 sumber persis apa adanya ("nada yang berbeda... dalam satu jawaban") — hasil bersih tanpa cela.

### S11 — Larangan Klaim Sebab-Akibat (LOLOS, Kritis Kedua)

**Narasi:** "...tingkat okupansi naik sebesar 10%... Selain itu, pendapatan F&B pada bulan yang sama **juga** mengalami peningkatan sebesar 8%..."

**Analisis:** Model memakai kata penghubung netral ("juga", "selain itu") — TIDAK sekali pun memakai kata kausal ("menyebabkan", "sehingga", "akibat") untuk menghubungkan kedua angka, meski keduanya sama-sama naik di periode yang sama (godaan alami untuk menyimpulkan korelasi/kausasi). Ini instruksi paling rawan dilanggar model generatif (kecenderungan LLM umum "melihat pola" dan menyimpulkan hubungan) — hasil bersih menunjukkan prompt (instruksi 5) efektif menahan kecenderungan itu di kasus yang secara eksplisit dirancang memancingnya.

### S09 — Rantai Ketergantungan 2 Level (LOLOS, Melampaui Ekspektasi Minimum)

**Narasi:** "...occupancy rate April 2026... tidak dapat diperoleh. Kebutuhan perbandingan dengan Maret 2026 **dan** persentase kenaikan **juga** tidak dapat diproses karena bergantung pada data April 2026 yang gagal diambil."

**Analisis:** `rancangan.md` mencatat kemungkinan model HANYA menjelaskan lapisan terdekat (C gagal karena B gagal, tanpa sampai ke akar A) sebagai risiko yang diterima (bukan otomatis gagal keras). Hasil aktual justru LEBIH BAIK dari ekspektasi minimum — model langsung menelusuri KEDUA kebutuhan turunan (B dan C) sampai ke akar penyebab sesungguhnya (A, occupancy April yang gagal_teknis), bukan berhenti di lapisan langsung. Tidak ada tindak lanjut diperlukan.

### S05, S10 — False-Negative Heuristik (Heuristik REVIEW, Narasi Benar)

**S05** (sebagian+flagged): narasi memakai frasa "**belum sepenuhnya memenuhi standar**", "**mungkin belum mencerminkan keadaan akurat atau lengkap**", "**sedang melakukan evaluasi lebih lanjut**" — secara SUBSTANSI ini menyampaikan hasil sebagai parsial dengan tepat, tapi TIDAK memakai kata kunci literal yang dicari heuristik ("parsial"/"sebagian"/dst.). Heuristik kata-kunci-ringan gagal menangkap parafrase yang valid.

**S10** (nullable-bermakna): narasi eksplisit menulis "...**bukan karena data tidak tersedia** atau sistem mengalami kendala." — heuristik `_tidak_mengandung("data tidak tersedia", ...)` mendeteksi SUBSTRING "data tidak tersedia" hadir dan menandainya gagal, PADAHAL frasa itu muncul dalam konteks NEGASI (menyangkal, bukan mengklaim) — justru inilah pemenuhan instruksi paling tepat yang mungkin (secara eksplisit mengklarifikasi BUKAN karena data hilang). Ini keterbatasan struktural heuristik substring-match yang tidak memahami negasi, bukan kegagalan narasi.

**Kesimpulan kedua kasus:** Heuristik kata-kunci di `run_eval.py` terbukti bisa false-negative pada narasi yang justru BENAR — mengonfirmasi keputusan desain `rancangan.md` bahwa heuristik hanya lapis tambahan, verdict akhir wajib audit manual. Tidak ada perbaikan mendesak terhadap `susun_narasi()`/prompt — perbaikan (kalau ada) seharusnya di heuristik `run_eval.py` sendiri, bukan prioritas milestone ini.

### S03, S08 — Temuan Minor: Klaim Tindakan yang Tidak Terverifikasi

**S03:** "...**Tim teknis sedang meninjau masalah ini**, dan kami akan berusaha memberikan data yang diminta pada kesempatan berikutnya."

**S08:** "...**Kami sedang meninjau masalah teknis ini** agar dapat memberikan informasi yang lengkap di masa mendatang."

**Analisis:** Kedua narasi menambahkan klaim tindakan proaktif ("tim sedang meninjau") yang TIDAK ada dasarnya dari data yang diterima (`status`/`catatan_interpretasi` tidak pernah menyatakan ada tim yang sedang menangani). Ini BUKAN pelanggaran instruksi 5 (larangan klaim sebab-akibat dari data deskriptif — beda konteks, ini bukan klaim kausal antar-data) dan BUKAN pelanggaran instruksi 4 (tetap tanpa detail teknis) — tapi tetap sebuah bentuk "mengarang" halus (menyiratkan proses operasional yang sebenarnya tidak diketahui sistem ini). Dicatat sebagai temuan pola untuk pertimbangan revisi prompt versi berikutnya (lihat Rekomendasi), BUKAN kegagalan KK sumber manapun secara langsung.

## Temuan Pola

1. **Ketujuh instruksi wajib prompt (5 arsitektur + rujukan lintas-turn + kontras nada) bekerja sesuai desain di SELURUH 13 skenario** — termasuk kedua skenario paling kritis (S04, S11) yang dirancang khusus memancing pelanggaran. Model `qwen/qwen3-32b` (dipilih tanpa perbandingan empiris baru, `decisions.md` Keputusan 1) terbukti memadai untuk tugas ini pada cakupan skenario yang diuji.
2. **Rantai ketergantungan (S08, S09) dijelaskan model sampai ke akar penyebab**, bukan berhenti di lapisan langsung — melampaui ekspektasi minimum yang dicatat `rancangan.md`.
3. **Heuristik kata-kunci ringan (`run_eval.py`) punya keterbatasan struktural nyata**: tidak menangkap parafrase valid (S05) dan tidak memahami negasi (S10) — dua false-negative, nol false-positive. Konsisten arah aman (heuristik ketat gagal menandai narasi baik sebagai buruk, tapi tidak pernah menandai narasi buruk sebagai baik pada 13 skenario ini).
4. **Kecenderungan model menambahkan klaim tindakan proaktif tidak berdasar** ("tim sedang meninjau") pada narasi kegagalan teknis (S03, S08) — pola berulang 2x dari 3 skenario yang melibatkan `gagal_teknis`, layak dipantau lintas evaluasi berikutnya (M4.5 dan penggunaan produksi nanti) sebelum diputuskan perlu revisi prompt atau tidak.
5. **Tidak ditemukan satu pun kasus** klaim sebab-akibat tak berdasar, penyamaran status non-normal sebagai normal, atau kebocoran istilah teknis internal ke user — tiga risiko paling berbahaya dari 7 instruksi wajib nol-insiden di seluruh 13 skenario.

## Rekomendasi

- **Tidak ada aksi mendesak terhadap `susun_narasi()` atau prompt `narasi.md`** — seluruh dimensi kritis (kontras nada, larangan kausal, rantai ketergantungan, kejujuran status) lolos bersih.
- **Perbaiki heuristik `run_eval.py` kalau file ini dipakai ulang untuk regresi di masa depan** (bukan prioritas sekarang, milestone ini sudah terbukti lewat audit manual): (a) heuristik "parsial" sebaiknya berbasis daftar kata kunci lebih luas atau deteksi semantik ringan, bukan exact substring; (b) heuristik larangan-frasa sebaiknya sadar-negasi (mis. cek apakah frasa terlarang didahului "bukan"/"tidak"/"tanpa" dalam jarak dekat) sebelum menandai gagal.
- **Pantau pola "klaim tindakan proaktif tidak berdasar" (S03, S08) di evaluasi berikutnya** — kalau berulang konsisten pada volume lebih besar (mis. saat M4.5/produksi nanti), pertimbangkan menambah instruksi eksplisit ke prompt: "jangan mengklaim ada tindakan/tim yang sedang menangani kecuali itu benar-benar diketahui dari data". Belum cukup bukti (2 data point) untuk revisi prompt sekarang — dicatat di `report.md` sebagai item pantauan, bukan `docs/keterbatasan-diterima.md` (dampaknya kecil, bukan risiko kejujuran/keamanan).
- **Reuse 13 skenario ini penuh sebagai config Promptfoo** (Checkpoint 8) — seluruhnya representatif untuk reliability testing berkelanjutan tiap kali `narasi.md` direvisi versi berikutnya.
