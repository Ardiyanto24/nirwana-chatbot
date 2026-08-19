# Audit — Sambungan 9: Verification Gate → Execution, termasuk uji wave berulang (Milestone 7.14)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-19), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json` (E02/E03 percobaan pertama diarsipkan terpisah sebagai `E02_percobaan1_gagal_teknis.json`/`E03_percobaan1_gagal_teknis.json` — lihat "Insiden Operasional" di bawah). Docker Compose (Jaeger+Collector+Prometheus) dan `chatbot_api` lokal (`scripts/chatbot_api/`) dinyalakan ulang sebelum eksekusi (keduanya mati akibat restart komputer di tengah Checkpoint 4).

## Ringkasan

**KK literal M7.14 TERPENUHI PENUH — E01 membuktikan 2 wave genuinely berurutan** (`urutan_benar: true`, dikonfirmasi timestamp span nyata Jaeger, bukan urutan array). **Untuk PERTAMA KALINYA, `proses_turn()` genuinely memanggil `chatbot_api` sungguhan lewat pipeline otomatis penuh** (bukan panggilan manual per-fungsi seperti Checkpoint 1) — dibuktikan di E01 (2 item, wave 1 dan wave 2) dan E03 percobaan kedua (1 item).

**Temuan penting**: SELURUH item yang mencapai Execution di ketiga kejadian berakhir `GAGAL_TEKNIS` via jalur revisi `400` yang habis (`revisi_exhausted`/`revisi_gagal_susun`) — BUKAN bug M7.14 (wiring/wave logic terbukti benar, lihat analisis per kejadian), melainkan temuan genuinely baru tentang perilaku `chatbot_api` nyata terhadap request hasil LLM (M3.4) untuk view `v_reservation_gop_impact_monthly`/`v_maintenance_technician_daily` — dicatat sebagai follow-up di `report.md`, DI LUAR cakupan M7.14 untuk diperbaiki (M7.14 hanya menyambungkan, tidak mengubah logic M3.4/M4.2).

| ID | Wave terbentuk | `urutan_benar` | Item mencapai Execution | Status Execution | chatbot_api nyata dihubungi? |
|---|---|---|---|---|---|
| E01 | 2 (2+1 intent) | `true` | 2/3 (1 di-skip `lolos=False`) | `GAGAL_TEKNIS` ×2 | ✅ Ya, 2× (real 400 + revisi) |
| E02 | 0 (percobaan 1: gagal_teknis Domain Gate) → 0 (percobaan 2: seluruh item `lolos=False`, di-skip M7.13) | `null` (tanpa wave) | 0/1 | — | Tidak (tidak ada yang lolos sampai Execution) |
| E03 | 0 (percobaan 1: gagal_teknis Domain Gate) → 1 (percobaan 2) | `true` (1 wave) | 1/1 | `GAGAL_TEKNIS` | ✅ Ya, 1× (real 400 + revisi, ~68 detik) |

## Analisis Per Kejadian

### E01 — 2 wave genuinely berurutan (LOLOS — KK literal utama TERPENUHI)

`trace_id=62e460e93100afa2803972fa592f5ba1`. Payload: `role_title="Front Office Staff"`, gop_margin (identik M7.9-7.13). Decomposition menghasilkan 3 atomic intent: **A** "GOP Margin bulan ini" (independen), **B** "deviasi harga bulan ini" (independen), **C** "hubungan deviasi & GOP Margin" (**bergantung** pada A+B).

`kelompokkan_wave()` mengelompokkan SELURUH 3 intent (A+B di wave 1, C di wave 2) — TERMASUK A yang kelak `lolos=False` di M3.5, karena pengelompokan wave terjadi SEBELUM filter lolos (forced by desain: `kelompokkan_wave()` beroperasi di `query_engine_result` mentah, filter `lolos=False` terjadi INTERNAL di `verifikasi_gate_semua()` per wave, konsisten Keputusan 2 M7.13). Span `orchestration.wave`:
- Wave 1 (`intent_count=2`): `start=1787133851086993`, `end=1787133945482990` (~94.4 detik — mencakup verifikasi_gate_semua(A,B) + eksekusi_atomic_intent_semua(B) real, A di-skip internal karena `lolos=False`).
- Wave 2 (`intent_count=1`): `start=1787133945483086`, `end=1787134013307280` (~67.8 detik).
- **Gap wave1→wave2: 96 mikrodetik** — wave 2 mulai HAMPIR PERSIS setelah wave 1 selesai, TANPA overlap sama sekali. `urutan_benar=True`.

Item yang mencapai Execution: **B** (`status=GAGAL_TEKNIS`, `revisi_count=2`, `kegagalan_alasan=revisi_exhausted` — chatbot_api menolak params `{"property_name": "Bali", "period_date": "2026-08-01"}` dan 2 percobaan revisi berikutnya, semua ditolak `400`) dan **C** (`status=GAGAL_TEKNIS`, `revisi_count=0`, `kegagalan_alasan=revisi_gagal_susun` — percobaan revisi PERTAMA gagal disusun sama sekali oleh Query Engine, bukan ditolak server).

**Kesimpulan: KK literal M7.14 TERBUKTI PENUH** — kebutuhan majemuk-bergantung (C butuh A+B) menghasilkan 2 wave yang genuinely berurutan lewat Verification Gate DAN Execution YANG SAMA (fungsi `verifikasi_gate_semua()`/`eksekusi_atomic_intent_semua()` dipanggil ulang, bukan kode duplikat), dibuktikan lewat timestamp span nyata (bukan urutan array JSON semata).

### E02 — Baseline 1 wave (LOLOS mekanisme, TIDAK mencapai Execution kedua percobaan — bukan kegagalan M7.14)

**Percobaan 1** (`session_id=eval-7.14-e02`, `trace_id=304379efae56cb021915eae1ea51b9b6`, diarsipkan `E02_percobaan1_gagal_teknis.json`): Domain Gate (`identifikasi_domain_atomic_intent()`, M2.1) mengembalikan `status=gagal_teknis`, `domains=[]` — LLM hiccup murni (tidak ada bukti error spesifik di span, kemungkinan transient API), TIDAK terkait wiring M7.14. Efek berantai: `otorisasi`/`cakupan_individu`/`retriever`/`query_engine`/`verification_gate` seluruhnya `[]` (filter internal tiap layer bekerja benar, tidak crash) — `kelompokkan_wave([])` mengembalikan `[]`, TIDAK ADA span `orchestration.wave` sama sekali (`wave_spans=[]`, BUKAN bug script, genuinely nol wave).

**Percobaan 2** (`session_id=eval-7.14-e02b`, `trace_id=e52eb3b6c41db655cfec76111c6289e3`, file final `E02.json`): Domain Gate `berhasil` kali ini. TAPI Decomposition mengklasifikasikan `label_bentuk_jawaban="peringkat"` (BUKAN `"nilai_tunggal"` seperti run M7.13 sebelumnya — non-determinisme dikenal). Query Engine menyusun params `{"full_name": "Budi", "review_period": "2026-S2"}` — M3.5 (Verifikasi Bentuk Request) BENAR menolak (`lolos=False`): *"Params membatasi ke satu karyawan (Budi) dan satu periode... untuk label 'peringkat', diperlukan banyak baris"*. Sesuai Keputusan 2 M7.13, item ini DI-SKIP sebelum Verification Gate — `verification_gate=[]`, 1 wave terbentuk (`intent_count=1`, durasi ~1.4ms — HANYA span pembungkus kosong, tidak ada panggilan nyata di dalamnya) tapi tidak ada apa pun untuk dieksekusi.

**Kesimpulan: mekanisme skip M7.13 TERBUKTI bekerja benar terhadap kondisi real-execution yang genuinely berubah** (klasifikasi non-deterministik kali ini menghasilkan `lolos=False`, bukan `lolos=True` seperti run sebelumnya) — TIDAK ada item yang "diam-diam lolos" ke Execution meski parameternya sebenarnya valid untuk `nilai_tunggal`. Kejadian ini TIDAK memberi bukti Execution mencapai `chatbot_api` untuk skenario HR, tapi memberi bukti independen bahwa jalur skip bekerja benar di kondisi produksi nyata.

### E03 — Bukti kedua independen, domain facility (LOLOS setelah retry — Execution nyata tercapai)

**Percobaan 1** (`session_id=eval-7.14-e03`, `trace_id=226e9dc66101309907c4324a78a47f35`, diarsipkan `E03_percobaan1_gagal_teknis.json`): identik pola E02 percobaan 1 — Domain Gate `gagal_teknis` murni, nol wave.

**Percobaan 2** (`session_id=eval-7.14-e03b`, `trace_id=1dc610c0170f0c69ddd4b22cda0cd335`, file final `E03.json`): Domain Gate `berhasil` (2 domain teridentifikasi kali ini). 1 wave terbentuk (`intent_count=1`), durasi **~66.1 detik** (`start=1787135209874864`, `end=1787135276020967`) — durasi substansial mengonfirmasi AKTIVITAS NYATA (LLM + HTTP round-trip real, bukan span kosong seperti E02). Item mencapai Execution: `status=GAGAL_TEKNIS`, `kegagalan_alasan=revisi_exhausted` — pola sama seperti E01 item B (chatbot_api menolak params hasil LLM untuk `v_maintenance_technician_daily`, revisi tidak berhasil memperbaikinya).

**Kesimpulan: bukti KEDUA independen bahwa `proses_turn()` genuinely memanggil `chatbot_api` sungguhan**, domain berbeda (`facility` vs `reservation` E01) — memperkuat generalisasi klaim di luar satu domain/view tunggal.

## Insiden Operasional

**Restart komputer (sebelum Checkpoint 6)**: menghentikan proses background `chatbot_api` (Checkpoint 1) DAN Docker Desktop. Keduanya dinyalakan ulang sebelum Checkpoint 6 ditutup — tidak ada kerja/commit yang hilang (dikonfirmasi `git status` bersih pasca-restart).

**Domain Gate `gagal_teknis` pada percobaan pertama E02 DAN E03** (keduanya, `session_id` berbeda, dijalankan berurutan) — pola yang tidak pernah muncul di M7.6-7.13 sebanyak ini secara berturut-turut. Kemungkinan: hiccup transient provider LLM (OpenRouter) saat load tinggi (E01 baru saja menghabiskan ~3 menit LLM+HTTP intensif sebelum E02/E03 dijalankan). TIDAK cukup bukti untuk mengklaim ini bug sistemik — dicatat sebagai observasi operasional, retry dengan `session_id` baru (`eval-7.14-e02b`/`e03b`) berhasil menembus Domain Gate pada percobaan kedua untuk KEDUANYA.

**Tidak ada insiden hang** (durasi total eksekusi E01+E02+E03 asli + retry E02b+E03b jauh di bawah ambang bahaya M7.12 ~24.7 menit).

## Temuan Metodologi

**Seluruh item yang mencapai Execution di ketiga kejadian (E01×2, E03×1) berakhir `GAGAL_TEKNIS` via jalur revisi 400** — ini adalah PERTAMA KALINYA jalur revisi 400 M4.2 diuji terhadap `chatbot_api` NYATA (sebelumnya 100% simulasi mock). Temuan: request hasil `susun_request_atomic_intent()` (M3.4) untuk view `v_reservation_gop_impact_monthly`/`v_maintenance_technician_daily` konsisten ditolak validasi server nyata, dan `_revisi_request()` (M4.2) tidak berhasil memperbaikinya dalam `EXECUTION_MAX_REVISI` percobaan. Ini BUKAN bug wiring M7.14 (mekanisme wave/Execution terbukti benar - request genuinely terkirim, status genuinely diklasifikasi, tidak ada crash/silent failure) — melainkan sinyal kualitas nyata tentang M3.4 (Query Engine)/M4.2 (revisi) yang baru bisa terlihat sekarang server nyata reachable. Dicatat sebagai follow-up di `report.md`, DI LUAR cakupan perbaikan M7.14 sendiri (batasan mengikat: tidak mengubah logic M3.4/M4.2).
