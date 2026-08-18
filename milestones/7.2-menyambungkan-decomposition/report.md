# Report — Milestone 7.2: Menyambungkan Decomposition (Klasifikasi → Pemecahan → Verifikasi)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai dengan penyesuaian signifikan dari plan.

Investigasi sebelum implementasi menemukan bahwa `decompose_question()` (`src/layers/decomposition/decompose.py`) **sudah menyambungkan** ketiga langkah Decomposition (Klasifikasi → Pemecahan → Verifikasi) sejak Milestone 1.6 Checkpoint 7 (2026-08-15) — dibangun dan dibuktikan nyata (real LLM + Jaeger) saat itu. Premis Lingkup M7.2 di `rancangan-orkestrasi-api.md` ("ketiga langkah terbukti bekerja terisolasi") tidak akurat untuk kondisi kode saat ini. Milestone ini karena itu bergeser dari "membangun penyambung" menjadi **memperkuat bukti connectivity** (test boundary-level, bukan cuma hasil akhir) **dan menutup dokumentasi formal** — dua test baru ditambahkan (jalur normal + jalur retry/feedback), keduanya membuktikan hand-off nilai persis antar langkah dengan panggilan LLM sungguhan, lolos nyata.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Satu teks kebutuhan mandiri... dialirkan lewat ketiga langkah menghasilkan output akhir Verifikasi yang konsisten dengan Kriteria Keberhasilan asli Milestone 1.6 — dibuktikan dengan kasus kebutuhan majemuk-bergantung yang benar-benar mengalir melalui ketiga langkah tanpa intervensi manual di antaranya." | `test_konektivitas_klasifikasi_pemecahan_verifikasi_jalur_normal` (Checkpoint 2) — pertanyaan majemuk-bergantung nyata, real LLM, spy membuktikan argumen `klasifikasi` yang diterima `pecah_atomik()` dan argumen `hasil` yang diterima `verifikasi_pemecahan()` adalah objek PERSIS (identity check) dari return langkah sebelumnya, bukan rekonstruksi. Lolos nyata, 58.96s. | **Ya** — dibuktikan lebih kuat dari bukti M1.6/M7.1 yang sudah ada (yang hanya memeriksa hasil akhir). |

Tambahan di luar KK literal sumber (nilai tambah milestone ini): `test_konektivitas_retry_feedback_mengalir_ke_pecah_atomik_berikutnya` (Checkpoint 3) membuktikan jalur retry/feedback (Keputusan 3 M1.6) — sebelumnya tanpa test otomatis sama sekali — lolos nyata, 52.14s.

## Bagian 3 — Cara Kerja dan Arsitektur

Milestone ini tidak mengubah kode produksi apa pun (`decompose_question()` dan sub-langkahnya tetap seperti sebelumnya, sudah bekerja benar) — hanya menambah 2 test baru di `tests/layers/decomposition/test_decompose.py` dan dokumentasi penutupan. Cara kerja `decompose_question()` sendiri (klasifikasi sekali → loop pemecahan+verifikasi hingga 3x dengan feedback) sudah didokumentasikan lengkap di `milestones/1.6-decomposition/report.md` — tidak diulang di sini.

## Bagian 4 — Perubahan dari Plan

- **Penyesuaian besar terhadap ekspektasi awal milestone** (bukan plan Milestone 7.2 sendiri, yang sudah menuliskan temuan ini eksplisit sejak awal): dokumen sumber `rancangan-orkestrasi-api.md` mengasumsikan M7.2 adalah pekerjaan membangun kode penyambung; investigasi sebelum plan ditulis menemukan kode itu sudah ada sejak M1.6. Plan yang disetujui sudah mengantisipasi ini sepenuhnya (lihat `decisions.md` Keputusan 1) — tidak ada penyimpangan checkpoint-vs-eksekusi selama implementasi berjalan.
- Seluruh 2 checkpoint test (Checkpoint 2-3) dikerjakan persis sesuai plan yang disetujui, tanpa penyesuaian di tengah jalan.

## Bagian 5 — Keterbatasan dan Item Provisional

- Tidak ada keterbatasan baru yang perlu dicatat ke `docs/keterbatasan-diterima.md` sebagai akibat milestone ini — kode yang diaudit sudah bekerja benar, hanya kurang bukti test boundary-level (sekarang sudah ditutup).
- Test connectivity baru menambah ~2 menit waktu eksekusi test suite Decomposition (real LLM call) — konsisten dengan seluruh test real-call lain di project (`skipif` tanpa `OPENROUTER_API_KEY`), bukan keterbatasan baru.

## Bagian 6 — Follow-up

- **Milestone 7.3** (Domain Gate) — pola serupa sudah dikonfirmasi sejak investigasi awal (sudah tersambung, hanya butuh test boundary + dokumentasi), dikerjakan langsung setelah milestone ini dalam sesi yang sama.
- **Milestone 7.4** (Query Engine) dan **Milestone 7.5** (Interpretation) — GENUINELY perlu kode orkestrator baru (tidak seperti M7.2/M7.3), dikonfirmasi dari investigasi: tidak ada fungsi mana pun di `src/` yang menyambungkan M3.4→M3.5 atau M4.4→M4.5 untuk jalur utama. Follow-up untuk milestone tersebut, bukan cakupan M7.2.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
