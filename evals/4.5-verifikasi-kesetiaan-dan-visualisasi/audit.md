# Audit — Pengujian Verifikasi Kesetiaan Data (Milestone 4.5)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18, dijalankan DUA kali — run pertama menemukan 1 REVIEW nyata, run kedua setelah perbaikan prompt v2), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap skenario ada di `payloads/<ID>.json` (payload final = hasil run kedua, prompt v2). Model: `deepseek/deepseek-v4-pro`, `reasoning="high"`, `temperature=0`.

## Ringkasan

**10/10 skenario LOLOS (run kedua, prompt v2)** — turun dari **9/10 di run pertama (prompt v1)**. SATU temuan nyata (S06) memicu revisi prompt di tengah checkpoint — bukan false-negative alat ukur (beda M4.4 Checkpoint 7), melainkan **genuine over-triggering verifier** yang dikonfirmasi dan diperbaiki sebelum checkpoint ditutup.

| ID | Ekspektasi | Hasil (v1) | Hasil (v2) | Verdict Final |
|---|---|---|---|---|
| S01 | `lolos=False` | `False` ✅ | `False` ✅ | ✅ Lolos |
| S02 | `lolos=True` | `True` ✅ | `True` ✅ | ✅ Lolos |
| S03 | `lolos=False` | `False` ✅ | `False` ✅ | ✅ Lolos |
| S04 | `lolos=False` | `False` ✅ | `False` ✅ | ✅ Lolos |
| S05 | `lolos=False` | `False` ✅ | `False` ✅ | ✅ Lolos |
| S06 | `lolos=True` | `False` ⚠️ **REVIEW** | `True` ✅ | ✅ Lolos (setelah perbaikan) |
| S07 | `lolos=False` | `False` ✅ | `False` ✅ | ✅ Lolos |
| S08 | `lolos=True` | `True` ✅ | `True` ✅ | ✅ Lolos |
| S09 | `lolos=False` | `False` ✅ | `False` ✅ | ✅ Lolos |
| S10 | `lolos=True` | `True` ✅ | `True` ✅ | ✅ Lolos |

## Analisis Skenario Penting

### S01, S02 — Klaim Sebab-Akibat: Kasus Positif dan Negatif (LOLOS, Kritis)

**S01** (occupancy naik 10% "MENYEBABKAN" revenue F&B naik 8%, TANPA dasar di data): `lolos=False`, alasan mengutip persis kata "MENYEBABKAN" dan menyebut "dua hasil deskriptif terpisah... tanpa menyatakan hubungan kausal". **S02** (narasi identik TANPA kata penghubung kausal): `lolos=True`. Pasangan ini membuktikan verifier bisa membedakan PRESENCE vs ABSENCE klaim kausal pada data yang PERSIS sama — bukti kuat KK sumber (paling eksplisit di seluruh Lingkup M4.5) terpenuhi bersih.

### S06 — Temuan Nyata: Over-Triggering Kriteria 3 pada Kalimat Kualitas Data (REVIEW di v1, Diperbaiki di v2)

**Payload v1:** Narasi "...data ini ditandai perlu perhatian tim database **sehingga** mungkin belum akurat sepenuhnya" (persis pola yang DIINSTRUKSIKAN prompt `narasi.md` M4.4 sendiri, instruksi 2: "sampaikan jujur sebagai alasan kenapa hasilnya parsial") ditolak verifier v1 dengan alasan: *"Narasi menggunakan kata 'sehingga' untuk mengaitkan status 'perlu perhatian' dengan kesimpulan 'mungkin belum akurat sepenuhnya'... melanggar kriteria 3."*

**Analisis akar masalah:** Prompt v1 Kriteria 3 mencontohkan kata pemicu ("menyebabkan", "sehingga", "akibatnya") TANPA membedakan dua situasi yang berbeda secara mendasar: (a) klaim kausal ANTARA DUA DATA/METRIK TERPISAH (yang genuinely dilarang, dan itulah maksud KK sumber — mis. S01) vs (b) penjelasan WAJAR tentang keterbatasan SATU hasil berdasarkan catatan kualitas data yang MEMANG ada pada hasil itu sendiri (bukan klaim antar-data, forced oleh instruksi M4.4 sendiri). Model verifier mengikuti daftar kata pemicu secara harfiah, bukan maksud sesungguhnya di balik Kriteria 3 — false-positive yang genuinely berbahaya kalau tidak diperbaiki: narasi yang JUJUR justru akan ditolak berulang.

**Perbaikan:** Prompt `interpretation.verifikasi_kesetiaan` di-bump v1→v2, Kriteria 3 direvisi eksplisit membedakan kedua kasus dengan CONTOH KONKRET pengecualian ("PENGECUALIAN PENTING - JANGAN SALAH TANGKAP"). Diverifikasi ulang SEBELUM re-run penuh: S06 (harus `True`) dan S01 (harus tetap `False`, memastikan perbaikan tidak melonggarkan kasus yang sah ditangkap) dites terpisah dulu — keduanya benar, baru re-run penuh 10 skenario dijalankan (hasil: 10/10).

**Relevansi:** Ini BUKAN kegagalan model verifier terhadap tugasnya (model tetap benar mendeteksi kata pemicu sesuai instruksi persis yang diberikan) — murni gap SPESIFIKASI prompt v1 yang tidak mengantisipasi kasus penjelasan-kualitas-data-tunggal sebagai pengecualian wajar. Ditemukan justru karena skenario kontrol (S06) sengaja disusun meniru persis pola kalimat yang diinstruksikan `narasi.md` M4.4 sendiri (bukan skenario acak) — desain pasangan uji/kontrol di `rancangan.md` terbukti efektif menangkap masalah ini.

### S07, S08 — Status Terblokir: Generalisasi vs Spesifik (LOLOS)

**S07** ("Beberapa data tidak dapat ditampilkan saat ini" — generalisasi tanpa menyebut kebutuhan/relasi spesifik): `lolos=False`. **S08** (menyebut eksplisit revenue Maret gagal DAN perbandingan Februari bergantung padanya): `lolos=True`. Kriteria 5 (KK terkait dependency, mirror instruksi M4.4 ke-6) terbukti bekerja tepat membedakan generalisasi vs spesifik dengan data IDENTIK.

### S09 — Ditolak Otorisasi Disamarkan sebagai Kegagalan Teknis (LOLOS)

Narasi "terjadi kendala teknis" untuk kebutuhan yang SEBENARNYA `ditolak_otorisasi` (bukan `gagal_teknis`) ditangkap `lolos=False` — verifier tidak hanya mengecek kata kunci permukaan ("kendala" muncul di narasi) tapi benar-benar membandingkan STATUS SEBENARNYA di data sumber terhadap NADA yang dipakai narasi. Ini dimensi tambahan di luar 5 kriteria literal prompt (turunan dari Kriteria 2 "status non-normal disampaikan jujur", diperluas ke kasus penyamaran ANTAR jenis status non-normal, bukan cuma disamarkan sebagai normal) — verifier menangkapnya dengan benar meski tidak eksplisit dicontohkan di prompt.

### S10 — Stress Test 4-Status Kompleks (LOLOS, Kontrol Penting)

Narasi jujur menyampaikan 4 status berbeda sekaligus (berhasil, ditolak_otorisasi, gagal_teknis, terblokir_ketergantungan) dalam satu narasi kompleks — `lolos=True` bersih. Membuktikan kompleksitas/panjang narasi TIDAK memicu false-positive tambahan pada verifier v2 (S06 sudah diperbaiki, tidak muncul over-triggering baru pada kombinasi status lain).

## Temuan Pola

1. **Kriteria 3 (larangan klaim sebab-akibat) adalah kriteria PALING RENTAN over-triggering** dari kelima kriteria — satu-satunya yang memicu revisi prompt di checkpoint ini. Kriteria berbasis kata-kunci pemicu (bukan pemahaman kontekstual penuh) berisiko menangkap pola permukaan (kata "sehingga") tanpa membedakan konteks pemakaiannya - relevan untuk revisi prompt manapun di masa depan yang memakai pendekatan serupa (daftar kata pemicu eksplisit).
2. **Desain pasangan uji/kontrol (`rancangan.md`) terbukti efektif** — S06 ditemukan justru karena dirancang meniru PERSIS pola kalimat sah yang diinstruksikan M4.4, bukan skenario acak. Pola ini (skenario "kontrol positif" yang sengaja meniru output nyata konsumen upstream) layak direplikasi di eval milestone LLM berikutnya yang punya hubungan generate-verify serupa.
3. **Verifier menangkap dimensi di luar 5 kriteria literal prompt dengan benar** (S09: perbedaan NADA status non-normal, bukan cuma kata kunci "kendala") — indikasi model benar-benar membandingkan STATUS SEBENARNYA vs NADA narasi, bukan sekadar pattern-matching kata.
4. **Tidak ditemukan SATU PUN false-negative** (kasus yang seharusnya `lolos=False` tapi lolos) di seluruh 10 skenario, di kedua run — bias verifier (kalau ada) condong ke arah OVER-KETAT (S06), bukan ke arah lolos-kan pelanggaran nyata. Ini arah yang lebih aman untuk sistem yang wajib jujur ke user, meski butuh perbaikan presisi (sudah dilakukan).

## Rekomendasi

- **Tidak ada aksi lebih lanjut mendesak** — prompt v2 sudah terbukti 10/10 bersih, termasuk kasus yang sebelumnya gagal (S06) tanpa melonggarkan kasus yang sah ditangkap (S01 tetap benar).
- **Prompt Reliability config (Checkpoint 9) WAJIB memakai isi prompt v2** (bukan v1) — konsisten kontrak `rancangan-manajemen-prompt.md` ("reliability testing wajib dijalankan setiap kali version di-bump, sebelum commit di-push").
- **Kalau M4.5 (atau prompt verifier manapun berikutnya) menemukan pola over-triggering serupa pada kriteria lain**, pertimbangkan audit menyeluruh terhadap SELURUH daftar kata-kunci-pemicu di prompt verifier project (bukan cuma yang ditemukan di sini) - baru 1 data point sekarang, belum cukup untuk perubahan kebijakan lintas-project.
