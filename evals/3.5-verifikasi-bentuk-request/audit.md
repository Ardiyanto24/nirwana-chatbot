# Audit — Verifikasi Bentuk Request (Milestone 3.5)

Eksekusi nyata `verifikasi_bentuk_request_atomic_intent()` (bukan mock) untuk 5 skenario `rancangan.md`. **5/5 skenario lolos check otomatis** (run pertama, tanpa perlu revisi prompt). Payload lengkap: `payloads/S01.json` s.d. `S05.json`.

## Ringkasan Hasil

| ID | Status | Match | Catatan |
|---|---|---|---|
| S01 | LOLOS | ✓ | `lolos=false`, `alasan` PERSIS string deterministik dari `_view_name_sesuai_retriever()` — bukti langsung pre-check menangkap tanpa LLM |
| S02 | LOLOS | ✓ | `lolos=false`, alasan eksplisit menyebut rentang satu hari tidak cukup untuk tren |
| S03 | LOLOS | ✓ | `lolos=true`, rentang 3 bulan diterima untuk label tren |
| S04 | LOLOS | ✓ | `lolos=true`, request nilai_tunggal valid diterima |
| S05 | LOLOS | ✓ | `lolos=false` — replikasi temuan M3.4 berhasil ditangkap, DENGAN alasan yang LEBIH DALAM dari ekspektasi (lihat Temuan 1) |

## Temuan 1 — S01: Pre-Check Terbukti Menangkap Tanpa Panggilan LLM

`alasan` pada hasil S01 (`"view_name request ('v_reservation_channel_daily') tidak sesuai dengan view_name yang divalidasi Retriever ('v_reservation_room_type_daily')"`) PERSIS SAMA dengan string yang di-hardcode di `_view_name_sesuai_retriever()`/`verifikasi_bentuk_request_atomic_intent()` (bukan gaya bahasa LLM) — bukti langsung bahwa pre-check deterministik yang menangani kasus ini, bukan LLM. Konsisten `decisions.md` Keputusan 1 dan 3.

## Temuan 2 — S05: Reasoning LLM Lebih Dalam dari Ekspektasi Rancangan

Ekspektasi awal S05 (`rancangan.md`) memperkirakan model akan menyebut `occupancy_rate: "nilai_tunggal"` sebagai nilai nonsensikal. Hasil nyata: model justru menangkap masalah yang LEBIH FUNDAMENTAL — `v_reservation_room_type_daily` grain-nya properti × tipe kamar × tanggal, dan `params` (`property_name` + rentang tanggal SATU BULAN, tanpa filter `room_type` atau agregasi) akan menghasilkan BANYAK baris (4 tipe kamar × 31 hari), bukan satu angka `nilai_tunggal` yang diminta — alasan yang secara substansi LEBIH BENAR daripada sekadar mengomentari satu nilai string aneh. **Ini bukan kegagalan** — `lolos=false` tetap tercapai sesuai ekspektasi, hanya rutenya berbeda (grain-mismatch, bukan value-nonsense) — dicatat transparan sebagai bukti model benar-benar melakukan penalaran grain-vs-label yang diminta prompt, bukan sekadar pattern-matching ke satu nilai aneh.

## Temuan 3 — Ketidakkonsistenan Nyata: S04 vs S05 Punya Gap Struktural Serupa, Verdict Berbeda

S04 (`params={"property_id": "P01", "period_date_from": "2026-07-01", "period_date_to": "2026-07-31"}`, view sama `v_reservation_room_type_daily`) SECARA STRUKTURAL punya gap yang mirip S05 — TIDAK ADA filter `room_type` atau agregasi eksplisit, padahal grain view sama-sama mencakup dimensi tipe kamar. Namun S04 diberi `lolos=true` (alasan LLM S05 tentang "tanpa filter room_type, hasil akan banyak baris" TIDAK diterapkan konsisten ke S04 yang punya struktur params serupa). Kemungkinan penyebab: (a) genuinely inkonsisten — model tidak menerapkan kriteria grain-mismatch secara seragam antar dua kasus yang mirip; (b) non-determinisme `temperature=0` yang sudah tercatat sebagai pola berulang proyek ini (`docs/keterbatasan-diterima.md` #3 addendum, M1.7) — kemungkinan turut berperan di sini meski model beda (DeepSeek V4 Pro, bukan Qwen3-32B yang jadi subjek entri #3 sebelumnya). **Dampak langsung RENDAH** untuk KEDUA skenario (keduanya tetap match ekspektasi check otomatis yang dirancang independen, bukan saling membandingkan) — tapi pola ini relevan untuk transparansi kualitas keputusan lolos/tidak-lolos yang genuinely dibuat model, bukan aturan tertutup. **Belum cukup 1 titik data untuk entri formal `docs/keterbatasan-diterima.md`** (baru satu pasang perbandingan, bukan pola berulang lintas banyak skenario) — dicatat di sini sebagai observasi jujur untuk pemicu peninjauan kalau pola serupa muncul lagi di Milestone 3.5 lanjutan (Promptfoo, Checkpoint 6) atau produksi nyata.

## Kesimpulan

Kedua Kriteria Keberhasilan sumber M3.5 terbukti:
- **KK1** (kepatuhan sumber `view_name`): S01 lolos bersih, pre-check terbukti aktif tanpa LLM (Temuan 1).
- **KK2** (kecukupan bentuk jawaban, khusus contoh sumber "tren dengan rentang satu hari"): S02 lolos bersih, alasan spesifik dan benar.

Bonus temuan: S05 membuktikan mekanisme menangkap SECARA SUBSTANTIF apa yang M3.4 sengaja lewatkan (Temuan 2) — validasi langsung nilai arsitektur generate-verify Milestone 3.4+3.5. Satu observasi ketidakkonsistenan (Temuan 3) dicatat transparan, tidak memicu revisi prompt segera (baru 1 titik data, dampak rendah, tidak melanggar KK sumber manapun).
