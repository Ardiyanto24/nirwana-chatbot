# Report — Milestone 7.3: Menyambungkan Domain Gate (Identifikasi → Verifikasi Titik Buta)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai dengan penyesuaian signifikan dari plan.

Sama seperti M7.2 (Decomposition), investigasi sebelum implementasi menemukan bahwa `identifikasi_domain_atomic_intent()` (`src/layers/domain_gate/domain_gate.py`) **sudah menyambungkan** kedua langkah Domain Gate (Identifikasi → Verifikasi Titik Buta) sejak Milestone 2.1 Checkpoint 7-8 (2026-08-15) — dibangun dan dibuktikan nyata (real LLM + Jaeger trace) saat itu. Milestone ini bergeser dari "membangun penyambung" menjadi **memperkuat bukti connectivity** (test boundary-level) **dan menutup dokumentasi formal** — satu test baru ditambahkan, memakai skenario `gop_margin` yang eksplisit dirujuk KK sumber, membuktikan hand-off nilai persis antar langkah dengan panggilan LLM sungguhan, lolos nyata.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Kasus domain 'bocor' lewat kolom turunan (skenario uji `gop_margin` yang sudah dipakai Milestone 2.1) berhasil mengalir dari Identifikasi ke Verifikasi dan menghasilkan daftar domain lengkap yang benar, dibuktikan lewat pemanggilan berurutan nyata bukan dua pemanggilan terpisah yang hasilnya digabung manual." | `test_konektivitas_identifikasi_verifikasi_titik_buta_skenario_gop_margin` (Checkpoint 2) — skenario `gop_margin` persis (di-reuse dari `test_kelompok_a_union_domain_berhasil`), real LLM, spy membuktikan argumen `domain_awal` yang diterima `verifikasi_titik_buta()` adalah objek PERSIS (identity check) dari `identifikasi_domain().domains`, bukan digabung manual. Union akhir mencakup `RESERVATION`+`FINANCIAL` (domain yang bocor lewat kolom turunan berhasil ditangkap). Lolos nyata, 54.11s. | **Ya** — dibuktikan lebih kuat dari bukti M2.1/M7.1 yang sudah ada (yang hanya memeriksa hasil akhir union, bukan argumen boundary spesifik). |

## Bagian 3 — Cara Kerja dan Arsitektur

Milestone ini tidak mengubah kode produksi apa pun (`identifikasi_domain_atomic_intent()` dan sub-langkahnya tetap seperti sebelumnya, sudah bekerja benar) — hanya menambah 1 test baru di `tests/layers/domain_gate/test_domain_gate.py` dan dokumentasi penutupan. Cara kerja orkestrator sendiri (identifikasi sekali → verifikasi titik buta sekali → union aditif, tanpa retry) sudah didokumentasikan lengkap di `milestones/2.1-identifikasi-domain/report.md` — tidak diulang di sini.

## Bagian 4 — Perubahan dari Plan

- **Penyesuaian besar terhadap ekspektasi awal milestone** (bukan plan Milestone 7.3 sendiri, yang sudah menuliskan temuan ini eksplisit sejak awal, sama seperti M7.2): dokumen sumber `rancangan-orkestrasi-api.md` mengasumsikan M7.3 adalah pekerjaan membangun kode penyambung; investigasi menemukan kode itu sudah ada sejak M2.1. Plan yang disetujui sudah mengantisipasi ini sepenuhnya — tidak ada penyimpangan checkpoint-vs-eksekusi selama implementasi berjalan.
- **Temuan tambahan positif saat Task 2 dikerjakan**: skenario `gop_margin` yang diwajibkan KK sumber ternyata SUDAH ada persis di test yang sudah ada (`test_kelompok_a_union_domain_berhasil`) — tidak perlu direkonstruksi manual dari `evals/2.1-identifikasi-domain/` seperti diantisipasi risiko di plan (lihat `decisions.md` Keputusan 4, dan Risiko & Mitigasi plan M7.2+7.3). Teks kebutuhan yang sama langsung di-reuse.
- Satu checkpoint test (Checkpoint 2) dikerjakan persis sesuai plan yang disetujui, tanpa penyesuaian di tengah jalan.

## Bagian 5 — Keterbatasan dan Item Provisional

- Tidak ada keterbatasan baru yang perlu dicatat ke `docs/keterbatasan-diterima.md` sebagai akibat milestone ini.
- Docstring `test_domain_gate.py` (baris 8-15) mencatat cabang `GAGAL_TEKNIS`/`SEBAGIAN` di `identifikasi_domain_atomic_intent()` tidak diuji lewat kegagalan API yang dipaksa (project tidak mock panggilan LLM di file ini) — keterbatasan yang sudah ada sejak M2.1, dikonfirmasi ulang masih berlaku, bukan ditemukan baru oleh M7.3.

## Bagian 6 — Follow-up

- **Milestone 7.4** (Query Engine) dan **Milestone 7.5** (Interpretation) — GENUINELY perlu kode orkestrator baru (tidak seperti M7.2/M7.3), dikonfirmasi dari investigasi: tidak ada fungsi mana pun di `src/` yang menyambungkan M3.4→M3.5 atau M4.4→M4.5 untuk jalur utama. Follow-up untuk milestone tersebut, bukan cakupan M7.3.
- Dengan M7.2 dan M7.3 tuntas, Level 1 tersisa: M7.4 dan M7.5 — keduanya boleh dikerjakan urutan bebas (forced dokumen sumber), tapi wajib tuntas sebelum Level 2 (M7.6) dimulai.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
