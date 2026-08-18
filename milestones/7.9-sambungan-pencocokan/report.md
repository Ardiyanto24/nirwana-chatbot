# Report — Milestone 7.9: Sambungan 4 ((Decomposition + Tarik Memory) → Pencocokan)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai penuh. Titik pertemuan pertama Level 2 PIC 7 berhasil dibangun dan dibuktikan nyata dengan cakupan kombinasi kejadian PENUH (6 kejadian, bukan 2) sesuai instruksi eksplisit user.

Milestone 7.9 (Sambungan 4 Level 2 PIC 7) menyambungkan KEDUA jalur independen (Decomposition dari M7.8, Tarik Memory dari M7.7) sebagai input Pencocokan (M1.7, `match_and_archive()`). `proses_turn()` sekarang memanggil `match_and_archive(decomposition_result.atomic_intents, session_memory_result or [], payload.session_id, payload.turn_index)` sekuensial setelah Decomposition selesai — konversi `or []` forced oleh signature `match_and_archive()` yang menerima `list`, bukan `Optional`, sementara `KeadaanTurn.session_memory` (M7.7) bisa `None`.

Berbeda dari preseden M7.6-M7.8 (2 kejadian real-execution), milestone ini membuktikan **6 kejadian** yang mencakup seluruh kombinasi state bermakna di titik pertemuan ini: Tarik Memory tidak dipanggil (E01), dipanggil-kosong (E02), match nyata (E03), anti false-positive (E04), kandidat terfilter status (E05), dan majemuk campuran granularitas per-intent (E06, reuse pola M7.8 E01) — seluruhnya lolos verdict pada percobaan PERTAMA, tanpa race Jaeger (pola `span_wajib_ada` dari Temuan Pola M7.7 diterapkan sejak awal). Satu koreksi kecil ditemukan+didokumentasikan (jumlah atomic_intent E02 meleset dari prediksi, verdict inti tidak terpengaruh).

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Skenario uji Milestone 1.7 (atomic intent yang jelas merujuk hasil turn sebelumnya) berhasil dicocokkan dengan benar saat kedua jalur benar-benar berasal dari Sambungan 2 dan 3 sungguhan, bukan data buatan yang disusun manual menyerupai output kedua jalur itu." | Kejadian E03 (`evals/7.9-.../audit.md`) — `status=selesai`, `paket` merujuk PERSIS baris tersimpan, dari `decompose_question()` DAN `retrieve_session_memory()` nyata (bukan `AtomicIntent`/`SessionMemoryPackage` buatan tangan langsung dipassing ke `match_and_archive()`). Diperkuat E06 (granularitas per-intent dalam SATU turn majemuk, arsip ulang dikonfirmasi query DB langsung) dan E04 (anti false-positive, kandidat tersedia periode SAMA tapi domain beda tetap TIDAK match). | **Ya, penuh** — dibuktikan lebih kuat dari sekadar 2 kejadian minimal, mencakup seluruh kombinasi state bermakna. |
| "bukan salah satu jalur diuji sendirian seolah jalur lainnya tidak ada" (Lingkup M7.9) | Seluruh 6 kejadian menjalankan `proses_turn()` PENUH (Rewrite+Decomposition+Tarik Memory+Pencocokan nyata) — TIDAK ada kejadian yang memanggil `match_and_archive()` langsung dengan salah satu argumen hand-crafted. | **Ya, penuh**. |

## Bagian 3 — Cara Kerja dan Arsitektur

`proses_turn()` setelah `decomposition_result` final: `matches = match_and_archive(decomposition_result.atomic_intents, session_memory_result or [], payload.session_id, payload.turn_index)` dipanggil sekuensial di thread utama — Pencocokan genuinely butuh OUTPUT Decomposition sebagai argumen, tidak mungkin paralel dengan langkah manapun sebelumnya.

`KeadaanTurn` bertambah `matches: list[AtomicIntentMatch]` — selalu terisi KALAU `proses_turn()` selesai tanpa exception, TAPI panggilan `match_and_archive()` sendiri BISA raise (arsip ulang via `store_session_memory()` genuinely raise pada kegagalan DB) — TIDAK dibungkus try/except baru, exception dibiarkan menjalar apa adanya (konsisten preseden M7.7). Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

- Tidak ada penyimpangan checkpoint-vs-eksekusi pada struktur plan — seluruh 7 checkpoint dikerjakan sesuai rencana yang disetujui, termasuk cakupan 6 kejadian (bukan 2) sesuai instruksi eksplisit user.
- **Dua temuan teknis ditemukan DAN diperbaiki di Checkpoint 3** (dicatat detail di `logs.md`): (1) identity check Pydantic gagal untuk list KOSONG (`[] is []` → `False`, bukan hanya list berisi elemen seperti temuan M7.7) — diperbaiki jadi value equality; (2) dua test baru sempat lupa mock 3 langkah upstream, memicu panggilan LLM nyata tanpa disadari (47.66s, melanggar docstring cakupan file) — diperbaiki dengan mock lengkap.
- **Satu koreksi prediksi ditemukan saat audit Checkpoint 6**: `rancangan.md` E02 memprediksi Decomposition `tunggal`, aktualnya `majemuk_bergantung` (payload E02 diwariskan dari skenario M7.6/M7.7 yang ternyata berupa pertanyaan komparatif) — verdict inti (fast-path, semua `perlu_eksekusi`) TIDAK terpengaruh, dikoreksi eksplisit di `audit.md` tanpa mengedit `rancangan.md` retroaktif.

## Bagian 5 — Keterbatasan dan Item Provisional

- **Verifikasi memakai data seed manual untuk turn sebelumnya** (E03-E06) — Execution (M4.x) belum disambungkan ke `proses_turn()` (ditunda M7.1x), `session_memory_packages` tidak terisi organik. Ini BUKAN keterbatasan baru — mewarisi persis kondisi yang sudah diterima eksplisit di M1.7 (`milestones/1.7-.../report.md` Bagian 5). Data yang diuji SENDIRI (atomic_intents/candidates turn yang sedang diuji) tetap 100% dari pipeline nyata.
- **Pelajaran metodologi untuk milestone Sambungan berikutnya**: payload eval yang mengandung kata "bandingkan"/kalimat komparatif berisiko menghasilkan Decomposition majemuk secara tidak terduga — perlu diantisipasi eksplisit di `rancangan.md` (lihat `audit.md` "Temuan Metodologi"), bukan diasumsikan tunggal secara default.

## Bagian 6 — Follow-up

- **4/11 Sambungan Level 2 selesai** — M7.10 ("Sambungan 5: Pencocokan (jalur 'perlu eksekusi') → Domain Gate") adalah milestone berikutnya, WAJIB berurutan.
- **Preseden desain kejadian pembanding**: E03/E05 (payload turn 2 IDENTIK, hanya `status` kandidat diseed yang berbeda) mengisolasi satu variabel dengan bersih — direkomendasikan sebagai pola untuk kejadian pembanding di milestone Sambungan berikutnya yang butuh membuktikan efek satu faktor spesifik.
- **Identifikasi span lewat relasi parent** (bukan nama tracer) — teknik baru `_hitung_span_matching()` (cari span `matching.evaluate` unik, hitung `chat` yang parent-nya persis span itu) berguna untuk milestone Sambungan berikutnya yang juga perlu menghitung span spesifik dari satu layer di tengah trace yang lebih ramai (nama span `chat` dipakai berulang oleh banyak layer berbeda).
- Follow-up M7.7 (Temuan Pola `span_wajib_ada`) dan M7.8 (forbidden_phrases untuk kalimat komparatif) masih berlaku, sudah diterapkan langsung di milestone ini.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
