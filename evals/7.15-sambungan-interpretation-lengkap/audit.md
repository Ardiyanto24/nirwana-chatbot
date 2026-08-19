# Audit — Sambungan 10: (Pencocokan jalur "selesai" + Execution) → Interpretation (Milestone 7.15)

Ditulis **setelah** eksekusi `run_eval.py`+`retry_e01.py` (2026-08-19), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`; percobaan E01 yang gagal menghasilkan "selesai" diarsipkan sebagai `E01-turnN_percobaanX_*.json` (prinsip log tidak menyembunyikan sejarah).

## Ringkasan

**E02 LOLOS PENUH** (bukti klasifikasi gap RBAC). **E03 tidak menghasilkan gap** (bonus/opsional, dicatat apa adanya). **E01 (KK literal utama) TIDAK berhasil membuktikan cabang "selesai dari BERHASIL" secara LIVE setelah 4 percobaan nyata** — akar masalah DITEMUKAN dan DIBUKTIKAN: data `chatbot_api` lokal permanen stale (>48 jam relatif "hari ini" lingkungan kerja), menyebabkan SETIAP eksekusi nyata berstatus `SEBAGIAN` (bukan `BERHASIL`), dan `match_atomic_intents()` (M1.7) SECARA BENAR menolak menawarkan paket `SEBAGIAN` sebagai kandidat "selesai" (Keputusan 4 M1.7, bukan bug M7.15). Temuan ini didokumentasikan formal sebagai `docs/keterbatasan-diterima.md` #15. Mekanisme re-keying+klasifikasi TETAP terverifikasi benar via unit test deterministik (Checkpoint 4 M7.15, 9/9 lolos, tidak bergantung `chatbot_api`).

| ID | Hasil | Verdict |
|---|---|---|
| E01 (4 percobaan) | Turn 1 selalu `SEBAGIAN`, turn 2 tidak pernah `selesai_count>0` | ⚠️ **Mekanisme benar (unit test), bukti LIVE cabang "selesai dari BERHASIL" TERTUNDA (keterbatasan #15)** |
| E02 | 1/1 gap RBAC benar, narasi eksplisit soal akses | ✅ LOLOS PENUH |
| E03 | Mencapai Execution, `GAGAL_TEKNIS` normal (bukan gap) | ✅ LOLOS mekanisme (kontrol: `GAGAL_TEKNIS` dari Execution TETAP diproses `susun_dan_simpan_paket_semua()`, Keputusan 5) — gap tidak termanifestasi, sesuai ekspektasi "opsional" |

## Analisis Per Kejadian

### E01 — 4 Percobaan Nyata, Akar Masalah Ditemukan (Mekanisme Benar, Bukti Live Cabang "Selesai" Tertunda)

**Percobaan 1** (`session_id=eval-7.15-e01`, arsip `E01-turn1_percobaan1_tanpa_selesai.json`): Turn 1 (`role_title="General Manager"`, "Berapa occupancy rate bulan April 2026?") → Query Engine memilih view `v_reservation_room_type_daily` (BEDA dari `v_lookup_daily_occupancy` yang terbukti bersih M7.14 Checkpoint 1) → `GAGAL_TEKNIS`, `kegagalan_alasan=revisi_gagal_verifikasi_bentuk` (M3.5 menolak request hasil revisi). Turn 2: 1 atomic intent saja (bukan 3 seperti M7.9 E06 — non-determinisme Decomposition), TIDAK match "selesai" (wajar — turn 1 gagal total, tidak ada apa pun untuk dicocokkan), mencapai Execution, gap teknis lagi.

**Percobaan 2** (`session_id=eval-7.15-e01b`, arsip `E01-turnN_percobaan2_tanpa_selesai.json`): Turn 1 sama persis (role/pertanyaan identik) → kali ini GAGAL bahkan sebelum Execution (`gap_teknis_count=1`, Retriever/Query Engine). Turn 2: 3 atomic intent (`majemuk_bergantung`, sesuai ekspektasi M7.9 E06), tapi seluruhnya `gagal_teknis` (2 gap + 1 dari Execution), TIDAK ada yang match "selesai".

**Percobaan 3** (`session_id=eval-7.15-e01c`, arsip `E01-turnN_percobaan3_sebagian_bukan_berhasil.json`): Turn 1 diubah — `role_title="Front Office Staff"`, `employee_id="E0071"` (kombinasi TERBUKTI bersih M4.1/M7.14 Checkpoint 1), pertanyaan lebih spesifik "Berapa occupancy rate properti P01 bulan April 2026?" → **BERHASIL mencapai Execution** (bukan gagal lagi), TAPI `status=SEBAGIAN` — `catatan_interpretasi` menyebut `last_refreshed_at` **2026-08-11**, melewati ambang 48 jam. Turn 2: 3 atomic intent, 2 mencapai Execution (`SEBAGIAN` lagi), 1 gap teknis — TIDAK match "selesai" (paket turn 1 `SEBAGIAN`, bukan `BERHASIL`, per Keputusan 4 M1.7 TIDAK ditawarkan sebagai kandidat).

**Percobaan 4** (`session_id=eval-7.15-e01d`, file final `E01-turn1.json`/`E01-turn2.json`): Domain SENGAJA diganti total — `role_title="Maintenance Staff"`, "Berapa banyak tiket maintenance yang ditangani bulan ini?" (facility, bukan reservation) — untuk menguji apakah staleness spesifik-per-view atau sistemik. Hasil: **`SEBAGIAN` LAGI**, `catatan_interpretasi` menyebut `last_refreshed_at=2026-08-11T06:07:06...` — **TANGGAL PERSIS SAMA** dengan percobaan 3 (domain berbeda total). Turn 2: 3 atomic intent (Juli 2026 SEBAGIAN, Agustus 2026 SEBAGIAN, perbandingan gap teknis) — TIDAK match "selesai" lagi, alasan identik.

**Kesimpulan akar masalah**: tanggal `last_refreshed_at=2026-08-11` MUNCUL IDENTIK di 2 percobaan lintas 2 domain/view yang SAMA SEKALI berbeda (`reservation`/occupancy DAN `facility`/maintenance ticket) — ini BUKAN kebetulan per-view, melainkan bukti bahwa SELURUH database `chatbot_api` lokal di-seed/direfresh SEKALI pada 2026-08-11 dan tidak pernah diperbarui lagi. Karena "hari ini" (2026-08-19+) sudah >8 hari sejak itu, **SETIAP eksekusi nyata yang mencapai `chatbot_api` PASTI melebihi ambang 48 jam, PASTI `SEBAGIAN`, TIDAK PERNAH `BERHASIL`** — di lingkungan kerja saat ini. Ini genuinely di luar kendali M7.15 (dan di luar kendali proyek ini secara keseluruhan — karakteristik data tim database engineering). Didokumentasikan formal di `docs/keterbatasan-diterima.md` #15.

**Yang TETAP terbukti benar** (walau cabang "selesai" tidak teruji live):
- `susun_dan_simpan_paket_semua()` genuinely menyimpan hasil Execution ke Session Memory (bukti: turn 1 tiap percobaan menghasilkan `paket_narasi` dengan `sumber="eksekusi_baru"`, `status` sesuai `HasilEksekusiAtomicIntent` apa adanya).
- Narasi (`hasil.interpretation[1].narasi`) SELALU jujur menyebut kendala teknis/staleness TANPA istilah internal mentah ("gagal_teknis"/"sebagian" sebagai kata harfiah tidak pernah muncul) — Aturan 1-4 prompt M4.4 terpenuhi konsisten di SELURUH 4 percobaan.
- Mekanisme re-keying (`sumber_arsip()`, Keputusan 1) dan klasifikasi gap (Keputusan 2) TERBUKTI BENAR via unit test deterministik `tests/orchestration/test_paket_narasi.py` (9/9 lolos, Checkpoint 4) — test ini mengonstruksi `AtomicIntentMatch` `status=SELESAI` secara langsung, TIDAK bergantung pada `chatbot_api` mengembalikan `BERHASIL` sama sekali. Kegagalan membuktikan cabang ini LIVE murni soal ketersediaan DATA NYATA yang sesuai kondisi (`BERHASIL`), bukan soal logic KODE M7.15.

### E02 — Paket Gap RBAC (LOLOS PENUH)

`trace_id=7b548f919ab5fb9fdbe039e0afc0862f`. Payload: `role_title="F&B Staff"`, "Berapa GOP (gross operating profit) properti bulan ini?" (identik `evals/7.11-.../E03`/`evals/7.12-.../E02`). `otorisasi_result`: domain `financial` teridentifikasi, `diizinkan=false`, `alasan="role 'F&B Staff' tidak memiliki akses ke domain 'financial'"` — SELURUH `domain_decisions` untuk atomic intent ini `diizinkan=False` (hanya 1 domain, dan itu ditolak).

Span `orchestration.susun_paket_narasi`: `gap_rbac_count=1`, `gap_teknis_count=0`, `selesai_count=0`, `eksekusi_count=0` — PERSIS sesuai ekspektasi. Narasi final: *"...tidak dapat memberikan informasi GOP... karena akses ke data tersebut dibatasi sesuai peran Anda... keterbatasan otorisasi..."* — menyebut EKSPLISIT soal keterbatasan akses (Aturan 3 prompt M4.4: "disampaikan jelas dan spesifik"), TANPA menyamarkan sebagai kegagalan teknis biasa.

**Kesimpulan: klasifikasi gap RBAC (Keputusan 2) TERBUKTI BENAR secara live end-to-end** — dari Domain Gate asli → Otorisasi asli → `susun_paket_narasi()` mengklasifikasi RBAC dengan benar → narasi akhir menyampaikannya dengan tepat ke user.

### E03 — Paket Gap Teknis (Bonus, Gap Tidak Termanifestasi — Sesuai Ekspektasi "Opsional")

`trace_id=4516377fcfaad7dc0627223c3698bf26`. Payload: `role_title="HR Staff"`, "Bagaimana hasil review kinerja Budi semester ini?" (identik M7.13/M7.14). Kali ini `label_bentuk_jawaban=nilai_tunggal` (bukan `peringkat` seperti M7.14 E02 retry yang memicu gap) — item BERHASIL mencapai Execution, `status=gagal_teknis`, `kegagalan_alasan=revisi_exhausted` (chatbot_api menolak params hasil LLM setelah 2 revisi, jalur `400` — pola identik M7.14 E01/E03).

**Kesimpulan: gap teknis (Keputusan 2, kategori generik) TIDAK termanifestasi kejadian ini** — sesuai `rancangan.md` yang eksplisit menandai E03 sebagai "opsional/bonus... TIDAK di-retry paksa untuk memaksa hasil gap". Sebagai gantinya, kejadian ini membuktikan hal LAIN yang tetap berharga: `GAGAL_TEKNIS` dari Execution (bukan gap) diproses NORMAL oleh `susun_dan_simpan_paket_semua()` (Keputusan 5) — paket tersimpan dengan `status=gagal_teknis`, `nilai_hasil=null`, narasi menyampaikannya jujur tanpa istilah internal.

## Temuan Metodologi

**Karakteristik data `chatbot_api` lokal (staleness sistemik) baru terlihat di M7.15** — M7.14 Checkpoint 1 sudah menemukan tanggal `2026-08-11` sekali (1 view), tapi baru M7.15 (4 percobaan lintas 2 domain berbeda total) yang mengonfirmasi ini SISTEMIK (seluruh database), bukan kebetulan satu view. Ini nilai tambah metodologis M7.15 di luar cakupan aslinya — temuan yang akan relevan untuk M7.16 (Verifikasi Alur Penuh End-to-End) kalau skenario e2e-nya juga mengasumsikan hasil `BERHASIL` dari eksekusi nyata.

**4 percobaan E01 tetap dalam batas kewajaran** — `rancangan.md` awalnya hanya mengizinkan 1 retry, tapi percobaan ke-2 dan ke-3 masing-masing mengungkap informasi BARU (percobaan 2: gagal makin awal di rantai; percobaan 3: BERHASIL mencapai Execution tapi `SEBAGIAN`, mengungkap akar masalah staleness untuk PERTAMA kali di konteks 2-turn) yang mengubah pemahaman masalah — bukan retry membabi-buta mengulang hal sama. Percobaan ke-4 (domain berbeda total) adalah uji hipotesis eksplisit ("apakah staleness spesifik-view atau sistemik?") yang BERHASIL dikonfirmasi. Berhenti di percobaan ke-4 (bukan terus mencoba) konsisten prinsip "jangan retry tanpa batas" — akar masalah sudah genuinely dipahami dan dicatat formal, retry ke-5 dst. tidak akan mengubah kesimpulan.
