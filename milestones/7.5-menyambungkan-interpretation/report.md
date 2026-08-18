# Report — Milestone 7.5: Menyambungkan Interpretation (Narasi → Verifikasi Kesetiaan Data)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai sesuai plan. Satu penyimpangan kecil murni operasional (bukan substantif) dari rencana commit — lihat Bagian 4.

Sama seperti M7.4 (dikerjakan sebelumnya dalam sesi yang sama), investigasi mengonfirmasi Milestone 7.5 genuinely butuh kode baru — tidak ada fungsi mana pun di `src/` yang menyambungkan `susun_narasi()` (M4.4) ke `verifikasi_dan_susun_visualisasi()` (M4.5) untuk jalur utama sebelum milestone ini. Fungsi orkestrator baru `susun_dan_verifikasi_narasi()` (`src/layers/interpretation/interpretation.py`) dibangun, diuji unit (mocked) untuk wiring, dan dibuktikan nyata (LLM sungguhan) lewat dua test connectivity: jalur normal tanpa mock sama sekali, dan skenario klaim sebab-akibat tak berdasar (KK sumber) yang genuinely butuh strategi test non-standar karena prompt narasi secara sengaja dirancang untuk TIDAK menghasilkan klaim semacam itu secara alami.

**Dengan M7.5 tuntas, seluruh 4 milestone Level 1 (M7.2-M7.5) SELESAI SEPENUHNYA — Level 2 (M7.6) boleh dimulai.**

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Narasi yang sengaja dibuat mengandung klaim sebab-akibat tidak berdasar (skenario uji yang sudah dipakai Milestone 4.5) berhasil ditangkap saat mengalir dari Penyusunan Narasi ke Verifikasi secara berurutan nyata." | `test_konektivitas_klaim_sebab_akibat_tertangkap_verifikasi_nyata` (Checkpoint 3) — reuse skenario S01 M4.5 persis (`evals/4.5-verifikasi-kesetiaan-dan-visualisasi/payloads/S01.json`, klaim "Kenaikan ini MENYEBABKAN revenue F&B..."). `susun_narasi()` dipaksa mengembalikan teks S01 (forced by Rule 5 prompt narasi yang melarang LLM mengarang klaim ini secara alami — lihat `decisions.md` Keputusan 7), `verifikasi_dan_susun_visualisasi()` LLM sungguhan penuh tanpa mock. `hasil_verifikasi.lolos is False`, alasan menyebut sebab-akibat/kausal, `visualisasi is None`. Lolos nyata, 15.77s. | **Ya**, dengan strategi test yang didokumentasikan eksplisit (bukan generasi organik penuh — lihat `decisions.md` Keputusan 7 untuk rasional lengkap). |

Tambahan di luar KK literal sumber (nilai tambah milestone ini, mirror pola M7.2): `test_konektivitas_jalur_normal_narasi_verifikasi_nyata` (Checkpoint 3) membuktikan wiring dasar TANPA mock sama sekali (kedua langkah LLM sungguhan) — lolos nyata, 73.12s.

## Bagian 3 — Cara Kerja dan Arsitektur

`susun_dan_verifikasi_narasi(atomic_intents, packages, session_id, turn_index) -> tuple[HasilNarasi, HasilVerifikasiNarasi, list[DataVisualisasi] | None]`:

1. Panggil `susun_narasi()` (M4.4). `APIError` (kalau terjadi) menjalar apa adanya — TIDAK ditangkap, konsisten keputusan sengaja M4.4 (tanpa fallback aman).
2. Panggil `verifikasi_dan_susun_visualisasi()` (M4.5) dengan `hasil_narasi.narasi`, kembalikan ketiganya `(hasil_narasi, hasil_verifikasi, visualisasi)`.

Tidak membuka span baru — kontrak observability §2 Interpretation (2 span `chat`) sudah terpenuhi penuh oleh instrumentasi M4.4/M4.5 masing-masing. Tidak ada skema baru ditambahkan ke `src/schemas/interpretation.py` — konsisten dengan pola desain M7.4 yang dikerjakan sebelumnya dalam sesi yang sama. Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

- Tidak ada penyimpangan substantif checkpoint-vs-eksekusi — seluruh 4 checkpoint dikerjakan sesuai plan yang disetujui, termasuk strategi test klaim sebab-akibat yang sudah diantisipasi plan lewat `AskUserQuestion`.
- **Penyimpangan operasional kecil pada commit Checkpoint 3**: plan mengasumsikan dua commit `test` terpisah (jalur normal, lalu klaim sebab-akibat). Karena kedua test ditulis dalam satu `Edit` (satu diff), keduanya ter-commit bersamaan di commit pertama (`7933905`); commit kedua sempat dibuat kosong (`--allow-empty`) lalu dikoreksi dengan `git reset --soft HEAD~1` (bukan `git commit --amend`, dihindari sesuai aturan Git project) sebelum ada commit lain di atasnya. Tidak mempengaruhi hasil verifikasi — kedua test tetap ada dan lolos nyata, hanya struktur commit yang berbeda dari rencana. Dicatat detail lengkap di `logs.md` Checkpoint 3.

## Bagian 5 — Keterbatasan dan Item Provisional

- **Strategi test klaim sebab-akibat (mock `susun_narasi()` return value) adalah penyimpangan terdokumentasi dari konvensi "tidak pernah mock LLM" M7.2/M7.3** — `decisions.md` Keputusan 7 mencatat rasional lengkap (Rule 5 prompt narasi, preseden M7.2 retry test). Bukan keterbatasan yang butuh perbaikan — pilihan sadar dengan trade-off eksplisit, dikonfirmasi user.
- Tidak ada keterbatasan baru yang perlu dicatat ke `docs/keterbatasan-diterima.md`.

## Bagian 6 — Follow-up

- **Seluruh 4 milestone Level 1 (M7.2-M7.5) SELESAI SEPENUHNYA.** Level 2 (M7.6, sambung antar-layer) boleh dimulai — syarat `rancangan-orkestrasi-api.md` terpenuhi.
- Follow-up M7.4 (potensi deduplikasi `_revisi_request()` M4.2 dengan orkestrator Query Engine baru) masih berlaku, dicatat di `milestones/7.4-menyambungkan-query-engine/report.md` Bagian 6 — tidak diulang di sini, tidak terkait M7.5.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
