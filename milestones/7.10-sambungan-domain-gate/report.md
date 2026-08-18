# Report — Milestone 7.10: Sambungan 5 (Pencocokan (jalur "perlu eksekusi") → Domain Gate)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai penuh. KK literal terpenuhi dengan bukti utama E01 PERSIS sesuai prediksi, diperkuat E03 sebagai bukti literal kedua yang muncul independen (bukan hasil rencana awal).

Milestone 7.10 (Sambungan 5 Level 2 PIC 7) menyambungkan output Pencocokan (M7.9, `matches: list[AtomicIntentMatch]`) sebagai input Domain Gate (`identifikasi_domain_semua()`, sudah ada sejak M2.1). Berbeda dari M7.2/M7.3 (murni verifikasi+dokumentasi, tidak ada kode baru) maupun M7.4/M7.5/M7.6-M7.9 (genuinely butuh orkestrator baru), M7.10 HYBRID: filter logic (`status=PERLU_EKSEKUSI` saja) sudah ada dan teruji sejak M2.1 — TIDAK disentuh — tapi `proses_turn()` sendiri belum pernah memanggilnya, jadi wiring orkestrator genuinely baru, mirror pola M7.6-M7.9.

`proses_turn()` sekarang memanggil `identifikasi_domain_semua(matches)` sekuensial setelah Pencocokan selesai — `matches` diteruskan APA ADANYA tanpa filter tambahan oleh orkestrator (mencegah duplikasi logic). Eksekusi nyata (3 kejadian) membuktikan mekanisme filter bekerja benar di seluruh kasus, dengan satu temuan metodologi jujur: non-determinisme Decomposition membuat 2 dari 3 kejadian tidak mereproduksi jumlah atomic_intent yang direncanakan — TIDAK mengurangi validitas bukti KK, justru E03 secara tak terduga menjadi bukti literal kedua yang independen.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Turn dengan campuran dua status (sebagian 'selesai' dari memory, sebagian 'perlu eksekusi') hanya meneruskan yang 'perlu eksekusi' ke Domain Gate — dibuktikan lewat span yang menunjukkan Domain Gate hanya menerima jumlah atomic intent yang sesuai, bukan seluruhnya." | Kejadian E01 (`evals/7.10-.../audit.md`) — campuran 1 `selesai` + 2 `perlu_eksekusi` dari 3 atomic_intent, `KeadaanTurn.domain_gate` berisi TEPAT 2 item, atribut span `intent.count=2` dikonfirmasi lewat query Jaeger API langsung. Diperkuat E03 (campuran independen kedua, komposisi/topik berbeda total dari E01, `intent.count=2` dari 3 juga) dan test deterministik `test_orkestrator_domain_gate_menerima_matches_apa_adanya_tanpa_filter` (spy, identity check argumen). | **Ya, penuh** — dibuktikan DUA KALI dengan skenario campuran berbeda, bukan satu kejadian tunggal. |

## Bagian 3 — Cara Kerja dan Arsitektur

`proses_turn()` setelah `matches` (M7.9) final: `domain_gate_result = identifikasi_domain_semua(matches)` dipanggil sekuensial — Domain Gate genuinely butuh OUTPUT Pencocokan sebagai argumen, tidak mungkin paralel. `matches` diteruskan utuh; filter ke `status=PERLU_EKSEKUSI` terjadi SEPENUHNYA di dalam `identifikasi_domain_semua()` (M2.1) — orkestrator tidak menduplikasi logic ini.

`KeadaanTurn` bertambah `domain_gate: list[AtomicIntentDomains]` — selalu terisi (fungsi tidak pernah raise, sub-langkahnya full-fallback APIError), panjangnya BISA lebih kecil dari `matches` (entri `selesai` difilter). Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

- Tidak ada penyimpangan checkpoint-vs-eksekusi pada struktur plan — seluruh 7 checkpoint dikerjakan sesuai rencana yang disetujui.
- **Penyimpangan hasil (bukan struktur) ditemukan saat Checkpoint 5-6**: `rancangan.md` E02/E03 memprediksi Decomposition `tunggal` (1 atomic_intent) berdasar preseden run M7.9 sebelumnya — aktual keduanya `majemuk_bergantung` (3 atomic_intent), termasuk E03 yang payload-nya IDENTIK PERSIS dengan `evals/7.9-.../E03`. Ini non-determinisme LLM Decomposition nyata (`temperature=0`, sudah dikenal dari `docs/keterbatasan-diterima.md` #3), BUKAN bug wiring M7.10 — verdict MEKANISME (filter benar, `intent.count` = panjang `domain_gate`) tetap terbukti di seluruh 3 kejadian. Dikoreksi eksplisit di `audit.md`, `rancangan.md` TIDAK diedit retroaktif, TIDAK di-retry berulang untuk memaksa hasil "sesuai rencana" (dijelaskan eksplisit sebagai bentuk bias metodologi yang dihindari).

## Bagian 5 — Keterbatasan dan Item Provisional

- **Klaim "span `domain_gate.identifikasi_semua` tetap terbuka dengan `intent.count=0` saat `domain_gate=[]`" TIDAK dibuktikan lewat eksekusi nyata di milestone ini** — ketiga kejadian yang genuinely tereksekusi tidak menghasilkan kondisi `domain_gate` kosong sepenuhnya (E03 yang direncanakan untuk ini malah menghasilkan campuran, bukan semua-selesai). Divalidasi lewat inspeksi kode langsung (`domain_gate.py`: span dibuka TANPA kondisi apa pun, tidak ada fast-path/early-return seperti `match_atomic_intents()` M1.7) — dicatat eksplisit sebagai validasi via inspeksi kode, bukan diklaim sebagai bukti eksekusi yang sebenarnya tidak ada. Kandidat follow-up kalau milestone Sambungan berikutnya kebetulan menghasilkan kondisi ini secara organik.
- **Non-determinisme Decomposition untuk payload identik lintas run** (E03 M7.10 vs E03 M7.9) — data point baru untuk `docs/keterbatasan-diterima.md` #3, belum ditambahkan sebagai entri formal di milestone ini (di luar Lingkup M7.10 untuk mengubah dokumen limitasi project-wide tanpa instruksi eksplisit) — dicatat sebagai follow-up di Bagian 6.

## Bagian 6 — Follow-up

- **5/11 Sambungan Level 2 selesai** — M7.11 ("Sambungan 6: Domain Gate → Retriever") adalah milestone berikutnya, WAJIB berurutan.
- **Pelajaran metodologi untuk `rancangan.md` milestone Sambungan berikutnya**: ekspektasi jumlah atomic_intent Decomposition TIDAK BOLEH diasumsikan tetap/reproducible bahkan untuk teks pertanyaan identik lintas run — sebaiknya ditulis dalam bentuk invarian mekanisme (mis. "seluruh `perlu_eksekusi` diteruskan, `intent.count` = panjang hasil"), bukan jumlah absolut, kecuali sudah diverifikasi stabil lintas beberapa run.
- **Pertimbangkan menambah data point non-determinisme Decomposition E03 M7.10 vs E03 M7.9 ke `docs/keterbatasan-diterima.md` #3** — belum dilakukan di milestone ini (di luar Lingkup), tapi relevan untuk sesi kerja mendatang yang menyentuh dokumen itu.
- Follow-up M7.9 (preseden desain kejadian pembanding E03/E05, teknik identifikasi span lewat relasi parent) masih berlaku, tidak terkait langsung M7.10 (M7.10 memakai teknik lebih sederhana berkat atribut `intent.count` yang sudah tersedia).
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
