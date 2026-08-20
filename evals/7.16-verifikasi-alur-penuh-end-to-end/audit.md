# Audit — Sambungan 11: Verifikasi Alur Penuh End-to-End (Milestone 7.16)

Ditulis **setelah** eksekusi `run_eval.py`+`retry_e03.py` (2026-08-20), membandingkan hasil aktual terhadap ekspektasi `rancangan.md`. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Sesi kerja dijeda di tengah percobaan pertama E03 (permintaan user untuk istirahat), `chatbot_api`+Docker/Jaeger mati total selama jeda dan dinyalakan ulang saat dilanjutkan — trace E01/E02 (dari sebelum jeda) tidak bisa di-query ulang dari Jaeger setelah restart (in-memory, tanpa volume persisten), tapi `cakupan_span` sudah tersimpan di payload SEBELUM restart, jadi tidak ada bukti yang hilang.

## Ringkasan

**Kedua Kriteria Keberhasilan M7.16 TERPENUHI PENUH untuk KETIGA skenario**, setelah satu koreksi kecil pada skrip verifikasi (bukan kode produksi — lihat "Temuan Metodologi"):

1. **"Berhasil dijalankan penuh dari ujung ke ujung tanpa pemanggilan manual antar-layer"** — E01/E02/E03 seluruhnya selesai lewat SATU pemanggilan `proses_turn(raw)` tanpa intervensi manual apa pun, menghasilkan `KeadaanTurn` 15 field lengkap termasuk narasi akhir yang jujur (E01/E02 melaporkan `gagal_teknis` apa adanya, E03 melaporkan `sebagian` dengan angka nyata + catatan data parsial).
2. **"Span `invoke_agent` membungkus seluruh span dari kesembilan layer... untuk setiap skenario"** — dikonfirmasi lewat `_analisis_cakupan_span()` (setelah koreksi): seluruh span unik per layer (Input Layer, Domain Gate ×3, Retriever, Query Engine, Verification Gate, Execution ×2, orchestration) hadir di ketiga trace, ditambah bukti window-waktu untuk span "chat" ambigu (Context Resolution+Decomposition sebelum `domain_gate.identifikasi_semua`, Interpretation setelah `orchestration.susun_paket_narasi`).

| ID | Fokus KK | Jumlah atomic intent | Wave | Hasil Execution nyata | `lengkap` (terkoreksi) |
|---|---|---|---|---|---|
| E01 | Tunggal sederhana | 1 | 1 | `gagal_teknis` ×1 (revisi_exhausted) | ✅ `True` |
| E02 | Dengan wave | 3 | 2 | `gagal_teknis` ×1 (revisi_exhausted); 2 lain gap sintetis (tersaring sebelum Execution) | ✅ `True` |
| E03 | Rujukan lintas-turn | 2 | 2 | `sebagian` ×2 (data nyata dari `chatbot_api`) | ✅ `True` |

## Analisis Per Kejadian

### E01 — Kebutuhan tunggal sederhana (LOLOS PENUH)

`trace_id=f8f5ed90aa1b7dca2169ca6fd7856203`. Payload identik `evals/7.9-.../E01.json` (General Manager, occupancy Juni 2026), `session_id` baru. Decomposition: 1 atomic intent (`tunggal`). Mengalir bersih: Domain Gate → `reservation` (berhasil) → Otorisasi lolos → Retriever → `v_reservation_room_type_daily` → Query Engine → Verification Gate `lolos=True` → **Execution nyata**: `status=gagal_teknis`, `kegagalan_alasan=revisi_exhausted` (chatbot_api menolak params hasil LLM, 2 revisi tidak berhasil memperbaiki — pola SAMA seperti M7.14, bukan temuan baru). `paket_narasi` 1 item, narasi akhir melaporkan kendala teknis secara jujur ("data kosong... kami sedang memeriksa masalah ini").

**Span 9 layer**: seluruh span unik hadir. `chat_count_sebelum_domain_gate=5` (1 ketergantungan + 1 rewrite + 3 decomposition — konsisten jumlah minimum tanpa retry). `chat_count_setelah_paket_narasi=2` (narasi + verifikasi kesetiaan Interpretation). `memory_retrieve_ada=False` (BENAR — fast-path M7.7, tidak ada referensi terdeteksi, kontrol negatif yang membuktikan Context Resolution tetap memilih jalur pendek yang benar di dalam pipeline PENUH). `matching_evaluate_ada=False` (lihat Temuan Metodologi).

**Kesimpulan**: rentang layer yang SEBELUMNYA (M7.9) hanya teruji sampai `matches`, sekarang genuinely terbukti mengalir bersih sampai Interpretation.

### E02 — Kebutuhan dengan wave (LOLOS PENUH — replikasi M7.14 + bukti tambahan mekanisme gap M7.15)

`trace_id=10c6cb22892e62c71fd128c6de9c1bac`. Payload identik `evals/7.14-.../E01.json` (Front Office Staff, gop_margin), `session_id` baru. Decomposition kali ini menghasilkan struktur SEDIKIT berbeda dari run M7.14 asli (non-determinisme dikenal, `docs/keterbatasan-diterima.md` #3): 3 atomic intent — **A** "GOP Margin bulan ini" (independen), **B** "deviasi harga bulan ini" (independen), **C** "pengaruh deviasi harga terhadap GOP margin" (**bergantung** pada A+B).

Rantai penyaringan nyata: **A** ditolak di Retriever (`view_name_final=None`, tidak ada view cukup — di-skip di Query Engine per M7.12 Keputusan). **B** dan **C** masuk `query_engine_result` (count=2). `kelompokkan_wave()` mengelompokkan B→wave 1, C→wave 2 (dependensi C ke A dianggap terpenuhi otomatis karena A hilang dari daftar, forced M7.14 Keputusan). **Span `orchestration.wave` MUNCUL 2× — bukti KK "kebutuhan dengan wave" TERPENUHI**, meski secara substansi:
- Wave 1: **B** lolos M3.5 (`lolos=True`) → Verification Gate → **Execution nyata**: `status=gagal_teknis`, `revisi_exhausted` (pola sama E01).
- Wave 2: **C** DITOLAK di M3.5 sendiri (`lolos=False`, item majemuk-bergantung/komparatif — pola konsisten M7.14 E01) → di-skip SEBELUM Verification Gate (Keputusan 2 M7.13) → span wave 2 tetap terbuka+tertutup normal, TAPI TANPA item nyata mencapai Execution di dalamnya (0 item, bukan crash).

**Bukti tambahan genuinely baru (belum pernah terlihat di M7.14, karena M7.14 mendahului M7.15)**: `paket_narasi` berisi 3 item — SEMUA berstatus `gagal_teknis`, TAPI lewat 2 jalur BERBEDA yang sekarang bisa dibedakan: **B** via Execution nyata (revisi_exhausted, presisi), **A** dan **C** via paket sintetis gap (M7.15 — tersaring SEBELUM Execution, klasifikasi teknis generik). Narasi akhir menggabungkan ketiganya secara koheren tanpa membocorkan istilah internal ("sistem mengalami kendala teknis... kedua data tersebut belum tersedia karena proses eksekusi terganggu").

**Span 9 layer**: seluruh span unik hadir (`retriever.proses_semua` dst.), `chat_count_sebelum_domain_gate=7` (3 atomic intent × Decomposition-sequence lebih panjang), `chat_count_setelah_paket_narasi=2`, `memory_retrieve_ada=False`, `wave_count=2` (KK terpenuhi eksplisit).

### E03 — Turn dengan rujukan lintas-turn (LOLOS PENUH setelah 3 percobaan — Execution nyata BERHASIL SEBAGIAN)

`trace_id=64ded97e477e36d5f4af62c912441aa4` (percobaan 3, `session_id=eval-7.16-e03c`; percobaan 1-2 hang, lihat "Insiden Operasional"). Payload: `history` fiktif 1 turn (mirror `evals/7.7-.../E01.json`). `ketergantungan.is_dependent=True`, `referenced_turn_index=1` — terdeteksi PERSIS dari `history` payload seperti diprediksi. `rewrite` menghasilkan pertanyaan mandiri membandingkan Februari vs Maret. **`memory.retrieve` span MUNCUL** (Tarik Memory genuinely terpanggil), `session_memory=[]` (dipanggil, kosong — sesuai desain, BUKAN `None`, karena `session_id` ini baru).

Decomposition menghasilkan 2 atomic intent (`majemuk_bergantung`): "revenue reservasi Februari 2026" (independen) dan "bandingkan Maret vs Februari" (bergantung pada yang pertama) — `wave_count=2`. **Kedua item mencapai Execution NYATA dan BERHASIL SEBAGIAN** (`status=sebagian` ×2, bukan `gagal_teknis`) — chatbot_api mengembalikan data asli (`nilai_hasil` berisi angka transaksi nyata), status `SEBAGIAN` murni karena staleness (`docs/keterbatasan-diterima.md` #15), BUKAN kegagalan teknis. Narasi akhir jujur menyebut angka nyata ("Rp127.95 juta") DAN keterbatasan datanya ("data ini bersifat parsial... terakhir diperbarui...").

Sesuai `decisions.md` Keputusan 3: `matches` KEDUANYA `perlu_eksekusi` (tidak ada kandidat "selesai" — `session_memory` kosong, sesuai desain, BUKAN gap yang perlu ditutup M7.16).

**Span 9 layer**: seluruh span unik hadir, `chat_count_sebelum_domain_gate=5`, `chat_count_setelah_paket_narasi=2`, `memory_retrieve_ada=True` (KK khusus E03 terpenuhi), `wave_count=2`.

## Insiden Operasional

**Jeda istirahat user di tengah percobaan pertama E03** — seluruh proses background (eval + monitor) dihentikan bersih atas permintaan eksplisit user. Saat dilanjutkan, `chatbot_api`+Docker/Jaeger ditemukan mati total (bukan hang — genuinely tidak reachable, `000`) — dinyalakan ulang, dikonfirmasi `/health`+`/api/services` 200 sebelum lanjut. Efek samping: restart Docker menghapus trace Jaeger E01/E02 (in-memory) — tidak menghalangi audit karena `cakupan_span` sudah tersimpan sebelumnya.

**E03 hang 2× berturut-turut, tanpa exception** — persis pola `docs/keterbatasan-diterima.md` #7 (I/O-bound blocking, CPU proses nyaris nol/flat selama beberapa menit, tidak ada request OpenRouter baru — dilaporkan langsung oleh user dari dashboard OpenRouter, dikonfirmasi independen lewat inspeksi trace Jaeger + `Get-Process` CPU delta). Percobaan 1 macet di ~offset 236s (23 span, sekitar Retriever). Percobaan 2 (session_id baru, dipantau aktif via `Monitor` polling Jaeger tiap 60s) maju LEBIH JAUH (38 span, offset ~676s, akhir Retriever/awal Query Engine) sebelum macet lagi (5 tick tanpa span baru). Percobaan 3 (session_id baru lagi) berhasil PENUH, dipantau sampai selesai TANPA stale-tick berkepanjangan.

**Analisis pola**: hang 2× berturut-turut HANYA pada E03 (E01/E02 sukses percobaan pertama) — E03 punya rantai LLM lebih panjang dari E01 (Rewrite+Tarik Memory paralel, Decomposition komparatif menghasilkan 2 atomic intent, Retriever kecukupan per-item ×2) tapi TIDAK lebih panjang dari E02 (3 atomic intent, sukses langsung) — jadi bukan murni soal volume panggilan. Kemungkinan besar ini genuinely acak (root cause `docs/keterbatasan-diterima.md` #7 sendiri belum pernah teridentifikasi penuh), diperkuat oleh 3 percobaan E03 yang PERSIS sama payload-nya menghasilkan 2 hang + 1 sukses — tidak ada pola input yang bisa disalahkan. Dicatat sebagai recurrence baru entri #7 (lihat `report.md`).

## Temuan Metodologi

**Bug di skrip verifikasi (BUKAN kode produksi)**: `_analisis_cakupan_span()` (`run_eval.py`) awalnya mewajibkan span `matching.evaluate` sebagai bukti Context Resolution/Pencocokan berjalan — ternyata `match_atomic_intents()` (M1.7 Keputusan 4) mengambil **fast-path NOL panggilan LLM** kalau tidak ada kandidat `session_memory` berstatus `BERHASIL`, kondisi yang SELALU benar untuk ketiga skenario M7.16 (tidak satu pun py histori "selesai" nyata — sengaja, `decisions.md` Keputusan 2-3). Ini SEHARUSNYA sudah diantisipasi saat menulis `decisions.md` Keputusan 5 (peta span) — bukti langsung sudah ada di `evals/7.9-.../E01.json` (`jumlah_matching_evaluate: 0`) sebelum plan M7.16 ditulis, tapi luput saat menyusun tabel. Diperbaiki di `run_eval.py` (span dikeluarkan dari `UNIQUE_LAYER_SPANS`, dilacak terpisah sebagai `matching_evaluate_ada` informasional) SEBELUM audit ini ditulis — ketiga payload `E01.json`/`E02.json`/`E03.json` TETAP menyimpan nilai `lengkap=False` ASLI (dari skrip SEBELUM diperbaiki, konsisten prinsip log tidak menyembunyikan sejarah) — verdict terkoreksi (`True` untuk ketiganya) didokumentasikan di audit ini, dihitung ulang manual dari field `cakupan_unik`/`chat_count_*`/`memory_retrieve_ada`/`narasi_non_kosong` yang SUDAH tersimpan benar di payload (hanya field agregat `lengkap` yang salah, bukan data mentahnya).

**Pencocokan (M1.7) tetap TERBUKTI bekerja benar di ketiga skenario** meski lewat cabang deterministiknya, bukan cabang LLM — dibuktikan `hasil.matches` terisi sesuai jumlah atomic intent (E01:1, E02:3, E03:2), seluruhnya `perlu_eksekusi` (benar, tidak ada kandidat untuk dicocokkan).
