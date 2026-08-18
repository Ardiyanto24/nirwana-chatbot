# Report — Milestone 7.8: Sambungan 3 (Rewrite → Decomposition)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai penuh, dengan satu koreksi penilaian di tengah audit (bukan penyimpangan checkpoint).

Milestone 7.8 (Sambungan 3 Level 2 PIC 7) menyambungkan output Rewrite (M1.4, kalimat mandiri) sebagai input Decomposition (M1.6, sudah tersambung internal sejak M7.2) — titik pertama hasil Level 1 sungguhan dipakai di Level 2. `proses_turn()` sekarang memanggil `decompose_question(rewrite_result.rewritten_question)` sekuensial setelah blok `ThreadPoolExecutor` (M7.7) selesai — TIDAK butuh paralelisme baru (beda dari M7.7) karena Decomposition murni bergantung data pada hasil Rewrite, bukan Tarik Memory.

Metodologi pembuktian KK diajukan ke user (KK M7.8 murni soal KONTEN, beda dari M7.6/M7.7 yang soal struktur span) — user memilih tetap membangun folder `evals/` penuh demi konsistensi struktur pengujian Level 2, dengan verdict utama berbasis kecocokan `required_phrases`/`forbidden_phrases` (bukan `parent_span_id`), bukti span jadi konfirmasi sekunder.

Eksekusi nyata (E01 kasus elipsis/koreferensi, E02 baseline kontras) membuktikan KK terpenuhi — dengan satu temuan metodologi: verdict mekanis E01 sempat `False` karena `forbidden_phrases` di `rancangan.md` salah asumsi (menandai "2026" terlarang, padahal legitimately muncul di kalimat perbandingan yang benar). Dikoreksi eksplisit di `audit.md` berdasar teks KK sesungguhnya — bukan disembunyikan atau `rancangan.md` diedit retroaktif.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Kalimat hasil Rewrite dari kasus elipsis/koreferensi (skenario uji Milestone 1.4) mengalir ke Decomposition dan menghasilkan pemecahan atomik yang konsisten dengan makna kalimat mandiri itu, bukan makna kalimat asli sebelum di-rewrite." | Kejadian E01 (`evals/7.8-.../audit.md`) — `rewritten_question="Bagaimana tingkat occupancy April 2026 dibandingkan dengan tingkat occupancy April 2025?"`, Decomposition menghasilkan 3 atomic_intents (`majemuk_bergantung`) yang PERSIS mencerminkan perbandingan itu (April 2025, April 2026, perbandingan keduanya dengan relasi ketergantungan benar). Teks ambigu asli "satu tahun sebelumnya" genuinely TIDAK PERNAH muncul di hasil Decomposition manapun — dikonfirmasi lewat query langsung `teks_kebutuhan_gabungan`, bukan asumsi. Test deterministik `test_orkestrator_decompose_menerima_rewritten_question_bukan_payload_question` (spy, mocked) memperkuat dengan bukti argumen persis di titik sambung. | **Ya, penuh** (setelah koreksi verdict mekanis — lihat Bagian 4). |

Tambahan di luar KK literal sumber (nilai tambah milestone ini): E02 (baseline kontras) membuktikan Decomposition tetap setia pada kalimat mandiri sederhana (`tunggal`, satu atomic_intent) — bukan pola tetap yang sama di semua kasus, memperkuat kredibilitas verdict E01.

## Bagian 3 — Cara Kerja dan Arsitektur

`proses_turn()` setelah blok `ThreadPoolExecutor` (M7.7) selesai dan `rewrite_result` final: `decomposition_result = decompose_question(rewrite_result.rewritten_question)` dipanggil sekuensial di thread utama — TIDAK butuh `otel_context.attach()`/`detach()` manual (itu hanya perlu untuk kerja lintas-thread `ThreadPoolExecutor`, bukan kode sekuensial biasa), span `chat` dari ketiga sub-langkah Decomposition otomatis jadi anak `invoke_agent` karena tetap berjalan di span context yang sama.

`KeadaanTurn` bertambah `decomposition: DecompositionResult` (selalu terisi — `decompose_question()` py fallback `APIError` penuh di tiap sub-langkah, tidak pernah raise, mirror pola `rewrite`). Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

- Tidak ada penyimpangan checkpoint-vs-eksekusi pada struktur plan — seluruh 7 checkpoint dikerjakan sesuai rencana yang disetujui.
- **Satu koreksi penilaian ditemukan saat eksekusi Checkpoint 5-6 (dicatat detail di `logs.md`/`audit.md`)**: `rancangan.md` E01 menetapkan `forbidden_phrases=["satu tahun sebelumnya", "2026"]` dengan asumsi keliru bahwa kalimat mandiri hasil resolusi hanya menyebut tahun tujuan. Karena skenario E01 adalah PERBANDINGAN ("Bandingkan dengan..."), kalimat mandiri yang benar wajib menyebut KEDUA sisi (April 2026 dan April 2025) — LLM Rewrite dan Decomposition sama-sama benar melakukan ini, verdict mekanis `lolos_konten=False` adalah false negative dari desain `forbidden_phrases` yang salah, bukan kegagalan kode. Dikoreksi eksplisit di `audit.md` (verdict substantif: LOLOS) tanpa mengedit `rancangan.md` retroaktif — konsisten prinsip "ekspektasi ditetapkan sebelum eksekusi, dinilai objektif", di mana "dinilai objektif" mencakup mengoreksi proxy pengujian yang keliru saat ditemukan, bukan memaksakan proxy yang salah sebagai kebenaran akhir.

## Bagian 5 — Keterbatasan dan Item Provisional

- **Temuan metodologi untuk milestone Sambungan berikutnya**: `forbidden_phrases` pada verdict berbasis konten harus dipetakan dari frasa rujukan mentah yang SECARA LINGUISTIK mustahil muncul di kalimat mandiri (mis. "itu", "tadi", "satu tahun sebelumnya"), BUKAN dari entitas/nilai spesifik (seperti tahun) yang bisa legitimately relevan tergantung struktur kalimat (perbandingan vs pernyataan tunggal). Dicatat di `audit.md` "Temuan Metodologi" — bukan keterbatasan sistem, murni pelajaran desain pengujian.
- Docker Desktop tidak berjalan di awal sesi kerja ini — perlu di-start manual sebelum Checkpoint 5. Bukan keterbatasan proyek (di luar kendali kode), dicatat sebagai observasi operasional saja.

## Bagian 6 — Follow-up

- **3/11 Sambungan Level 2 selesai** — M7.9 ("Sambungan 4: (Decomposition + Tarik Memory) → Pencocokan") adalah milestone berikutnya, WAJIB berurutan. M7.9 adalah titik pertemuan pertama (dua jalur independen — Decomposition dari M7.8, Tarik Memory dari M7.7 — sama-sama jadi input Pencocokan M1.7).
- **Preseden metodologi baru**: Keputusan 1 M7.8 menetapkan folder `evals/` sebagai default struktur pengujian Level 2 terlepas dari sifat KK (konten vs span) — berlaku untuk M7.9-7.16 kecuali user memutuskan lain untuk milestone tertentu.
- Follow-up M7.4 (potensi deduplikasi `_revisi_request()` M4.2), M7.6 (Struktur Repository `src/orchestration/`), dan Temuan Pola M7.7 (retry Jaeger `span_wajib_ada`, sudah dipakai ulang di sini) masih berlaku, tidak terkait langsung M7.8.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
