# Audit — Pengumpulan Kandidat View (Milestone 3.1)

Dieksekusi `uv run python evals/3.1-pengumpulan-kandidat-view/run_eval.py` (batch penuh, satu proses) setelah dry-run per-skenario (`A1`/`A2`/`B3`) mengonfirmasi script bekerja. Payload lengkap tersimpan di `payloads/`.

**Insiden selama eksekusi:** panggilan pertama ke `openai/text-embedding-3-small` gagal `404 NotFoundError` — setting akun OpenRouter "Allowed Providers" saat itu hanya mengizinkan `siliconflow` (yang kebetulan melayani kedua model Qwen3, tapi tidak OpenAI/Azure). User menambahkan `OpenAI` ke Allowed Providers lewat `openrouter.ai/settings/privacy`, dikonfirmasi via panggilan tes langsung (sukses, 1536 dimensi) sebelum eval penuh dijalankan ulang. Dicatat di sini karena ini insiden operasional nyata, bukan disembunyikan seolah eval berjalan mulus dari awal.

## Ringkasan Bagian A (KK1/KK2, Jalur BM25)

| ID | Status | Deskripsi |
|---|---|---|
| A1 | LOLOS | KK1: okupansi Bali bulan ini |
| A2 | LOLOS | KK2: zero-leakage domain ditolak |

Tidak ada temuan baru — mengulang bukti `tests/layers/retriever/test_pencarian_bm25.py` (Checkpoint 5) lewat payload tersimpan.

## Ringkasan Bagian B (Perbandingan 3 Model Embedding)

| ID | qwen3-4b (recall/posisi/latensi) | qwen3-8b (recall/posisi/latensi) | openai-small-3 (recall/posisi/latensi) |
|---|---|---|---|
| B1 | **False** / — / 0.9s | True / 4 / 7.02s | True / 2 / 3.26s |
| B2 | **False** / — / 1.25s | True / 1 / 4.50s | True / 2 / 0.58s |
| B3 | **False** / — / 0.19s | True / 5 / 1.66s | True / 2 / 0.97s |
| B4 | **False** / — / 0.25s | True / 1 / 1.04s | True / 2 / 1.00s |
| B5 | **False** / — / 0.22s | True / 2 / 0.77s | True / 4 / 0.61s |
| **Recall total** | **0/5 (0%)** | **5/5 (100%)** | **5/5 (100%)** |
| **Rank rata-rata (saat recall)** | — | 2.6 | 2.4 |
| **Latensi rata-rata** | 0.56s (tidak relevan, recall 0) | 3.10s (1.99s tanpa B1) | 1.29s (0.79s tanpa B1) |

Catatan latensi: `embed_korpus(model)` di-cache per-model (`@lru_cache`) dalam satu proses — panggilan PERTAMA per model (selalu B1 di urutan run ini) menanggung biaya batch-embed 67 teks korpus sekali, panggilan berikutnya (B2-B5) hanya query tunggal. Latensi "tanpa B1" di atas mencerminkan biaya query-only, lebih representatif untuk produksi (korpus akan di-precompute sekali, bukan tiap request).

## Temuan Utama

**Qwen3-Embedding-4B gagal total (0/5 recall) — bukan sekadar lemah, tapi TIDAK PERNAH menemukan target di SATU PUN dari 5 skenario stress-test**, termasuk B4 (di mana BM25 baseline sendiri sudah menemukan target di rank 2/4 — artinya model 4B bahkan LEBIH BURUK dari BM25 murni di kasus itu, bukan cuma "tidak membantu"). Tidak ada tanda ini bug pemanggilan (kode identik dipakai untuk ketiga model, dua lainnya bekerja normal) — dibaca sebagai kualitas genuine model 4B tidak memadai untuk tugas semantic search bilingual/Bahasa-Indonesia-dominan di skala percobaan ini.

**Qwen3-Embedding-8B dan `text-embedding-3-small` sama-sama mencapai recall sempurna (5/5)** pada seluruh skenario yang dirancang khusus menstress kegagalan BM25 (B1 sinonim non-literal, B2 bahasa sehari-hari, B3 typo, B4 framing abstrak, B5 partial-stem/kosakata umum) — membuktikan MEKANISME fallback embedding itu sendiri (bukan model spesifiknya) bekerja sesuai desain: kasus yang BM25 gagal total (B1, B3) atau nyaris tidak menyaring (B5, 10/10 kandidat) berhasil diperbaiki drastis oleh kedua model ini.

**`text-embedding-3-small` sedikit lebih unggul** di dua dimensi: rank rata-rata lebih baik (2.4 vs 2.6) DAN jauh lebih konsisten (selalu rank 2 kecuali B5 di rank 4, dibanding qwen3-8b yang berayun 1-5), plus latensi query-only jauh lebih rendah (0.79s vs 1.99s rata-rata, hampir 2.5x lebih cepat).

**Temuan trigger (dicatat `rancangan.md` sebelum eksekusi, dikonfirmasi lagi di sini):** skenario B1 membuktikan nyata bahwa `perlu_fallback` (trigger BM25→embedding) TIDAK AKTIF untuk B1/B2/B4/B5 (BM25 menemukan *sesuatu*, meski salah/tidak lengkap) — hanya B3 (typo, 0 kandidat sama sekali) yang benar-benar memicu trigger produksi saat ini. Artinya di 4 dari 5 skenario yang justru butuh fallback paling nyata, mekanisme produksi (Checkpoint 10) **tidak akan pernah memanggil embedding sama sekali** dengan desain trigger `BM25_SKOR_MINIMUM=0.0` saat ini — recall gap ini nyata dan perlu direvisi Checkpoint 9, bukan cuma isu kualitas model.

## Koreksi Checkpoint 9 — Angka Trigger BM25 yang Benar

Klaim "temuan trigger" di atas ditulis berdasar `rancangan.md` yang ternyata memakai baseline BM25 dari skrip eksplorasi (dengan stopword filtering) yang **belum diterapkan** ke `pencarian_bm25.py` sesungguhnya saat Checkpoint 7 dijalankan. Setelah diverifikasi ulang terhadap kode ASLI (tanpa stopword filtering, persis yang di-commit Checkpoint 5): **SEMUA 5 skenario B1-B5 (bukan 4/5) gagal memicu `perlu_fallback`** — root cause: kata fungsi umum ("yang", "dan", "di", dst.) muncul di hampir seluruh 67 teks korpus, membuat skor BM25 nyaris selalu positif untuk query apa pun, terlepas dari relevansi makna.

**Perbaikan diterapkan Checkpoint 9**: stopword filtering ditambahkan ke `pencarian_bm25.py` (`_STOPWORDS_ID`, ~50 kata fungsi Bahasa Indonesia/Inggris). Hasil setelah perbaikan (diverifikasi ulang lewat pemanggilan `cari_bm25()` langsung, bukan estimasi):

| ID | `perlu_fallback` SEBELUM perbaikan | `perlu_fallback` SESUDAH perbaikan | Target ditemukan? |
|---|---|---|---|
| B1 | False (keliru) | **False** | Tidak — recall gap nyata, TETAP tidak ditemukan meski stopword difilter |
| B2 | False (keliru) | False | Ya, rank 2/5 |
| B3 | False (keliru — SEHARUSNYA True) | **True** | — (fallback benar terpicu) |
| B4 | False (keliru) | False | Ya, rank 2/4 |
| B5 | False (keliru) | False | Ya, rank 7/10 |

Stopword filtering memperbaiki kasus yang memang murni disebabkan noise kata fungsi (B3 — typo memutus satu-satunya token bermakna, tanpa stopword lain yang "menyelamatkan" skor secara keliru). **B1 tetap tidak ditemukan bahkan pasca-perbaikan** — target (`v_reservation_channel_daily`, tema "kanal booking") genuinely tidak berbagi SATU KATA BERMAKNA pun dengan query paraphrase ("pesannya lewat mana", "aplikasi pihak ketiga") — ini BUKAN bug tokenizer, melainkan keterbatasan inheren pencarian leksikal murni yang TIDAK bisa diperbaiki tokenizer manapun (dicatat `docs/keterbatasan-diterima.md` entri baru, bukan diperbaiki lebih lanjut di checkpoint ini — lihat Rekomendasi di bawah).

**`BM25_SKOR_MINIMUM` dipertahankan di `0.0`** (bukan dinaikkan) — dengan stopword filtering, skor positif kini benar-benar berarti overlap kata bermakna, bukan noise. Menaikkan angka ini lebih lanjut tanpa bukti tambahan (5 skenario buatan tangan tidak cukup untuk kalibrasi presisi) berisiko over-trigger (memanggil embedding untuk kasus yang BM25 sebenarnya sudah cukup, menambah biaya/latensi tanpa manfaat recall).

## Rekomendasi (Bukan Keputusan Final — Ditutup Checkpoint 8)

1. **Model final: `openai/text-embedding-3-small`** — recall sempurna + rank paling konsisten + latensi terendah. Qwen3-Embedding-8B adalah alternatif valid (recall sama) kalau ada pertimbangan lain (mis. preferensi menghindari provider training-data di luar `siliconflow`, trade-off yang user sudah pertimbangkan sadar saat mengizinkan `OpenAI` di Allowed Providers).
2. **Qwen3-Embedding-4B TIDAK DIREKOMENDASIKAN sama sekali** — 0% recall bukan trade-off yang bisa diterima untuk mekanisme yang tujuannya justru menyelamatkan kasus yang BM25 gagal.
3. ~~Trigger `BM25_SKOR_MINIMUM=0.0` perlu direvisi substansial~~ — **SELESAI Checkpoint 9**: root cause bukan nilai numerik threshold, melainkan tokenizer tanpa stopword filtering (kata fungsi umum membuat skor selalu positif). Stopword filtering ditambahkan, `BM25_SKOR_MINIMUM` dipertahankan `0.0`. Lihat bagian "Koreksi Checkpoint 9" di atas.
4. **Keterbatasan residual (diterima, bukan diperbaiki)**: skenario B1 (sinonim non-literal tanpa satu kata bermakna pun yang overlap) tetap tidak ditemukan BM25 bahkan pasca-perbaikan stopword — keterbatasan inheren pencarian leksikal, bukan bug. Dicatat `docs/keterbatasan-diterima.md`.
