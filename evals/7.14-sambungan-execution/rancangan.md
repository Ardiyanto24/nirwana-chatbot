# Rancangan Pengujian — Sambungan 9: Verification Gate → Execution, termasuk uji wave berulang (Milestone 7.14)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Struktur mirror `evals/7.13-.../rancangan.md`.

**Beda mendasar dari SELURUH eval M7.6-7.13**: ini adalah **kejadian pertama proses_turn() genuinely memanggil `chatbot_api` sungguhan** — Checkpoint 1 sudah membuktikan `panggil_chatbot_api()`/`panggil_meta_chatbot_api()`/`eksekusi_atomic_intent()` bekerja benar SECARA TERPISAH (dipanggil manual), tapi belum pernah lewat `proses_turn()` end-to-end. Eval ini membuktikan pipeline OTOMATIS PENUH — Input Layer sampai Execution — genuinely mengalirkan data ke server nyata, bukan cuma potongan fungsi yang diuji manual.

**Pelajaran metodologi dari `evals/7.9-.../audit.md` s.d. `evals/7.13-.../audit.md`**: jumlah/komposisi `atomic_intent` hasil Decomposition TIDAK BOLEH diasumsikan tetap (non-determinisme `temperature=0` nyata, `docs/keterbatasan-diterima.md` #3) — ekspektasi ditulis sebagai invarian mekanisme, `session_id` BARU per kejadian (`eval-7.14-eXX`).

**Catatan tambahan (data nyata, BUKAN bug)**: Checkpoint 1 menemukan data `v_lookup_daily_occupancy` sudah 8 hari lebih tua dari `EXECUTION_DATA_STALENESS_THRESHOLD_JAM` (48 jam), menghasilkan `SEBAGIAN` bukan `BERHASIL` untuk view itu. View LAIN (`v_reservation_gop_impact_monthly`, `v_hr_employee_performance_semester`, `v_maintenance_technician_daily`) belum pernah dicek staleness-nya — `status=SEBAGIAN` untuk view manapun di eval ini TIDAK dianggap kegagalan, selama `nilai_hasil` genuinely terisi data nyata (bukan `GAGAL_TEKNIS`).

## Yang Diuji

`proses_turn()` — segmen baru M7.14: `kelompokkan_wave(query_engine_result)` mempartisi atomic intent ke wave, loop tiap wave memanggil `verifikasi_gate_semua()` (M7.13, sekarang per-wave) lalu `eksekusi_atomic_intent_semua()` (baru) — Execution (M4.1-4.2) benar-benar memanggil `chatbot_api` lokal (`http://127.0.0.1:8000`, `scripts/chatbot_api/`, HARUS `up` selama eksekusi).

**Invarian mekanisme yang wajib benar di SEMUA kejadian:**

1. Untuk tiap item yang mencapai Execution (`HasilVerifikasiGate.lolos=True` di wave manapun): `HasilEksekusiAtomicIntent.status` WAJIB salah satu dari `BERHASIL`/`SEBAGIAN`/`GAGAL_TEKNIS` (kontrak skema M4.2), dan kalau `BERHASIL`/`SEBAGIAN`, `nilai_hasil` WAJIB berisi data JSON nyata dari `chatbot_api` (bukan `None`/kosong buatan).
2. **Kalau atomic intent dengan `relasi=bergantung` (wave >= 2) genuinely muncul**: span `orchestration.wave` untuk wave itu WAJIB dimulai (start time) SETELAH span `execute_tool` TERAKHIR di wave sebelumnya SELESAI (end time) — dibuktikan lewat timestamp span nyata di Jaeger, bukan cuma urutan array dalam trace JSON.
3. Span `orchestration.wave` WAJIB membawa atribut `wave.index` (mulai 1, berurutan tanpa lompat) dan `wave.intent_count` sesuai jumlah item wave itu SEBELUM filter `lolos=False` di Verification Gate.
4. `403`/`404` dari `chatbot_api` (kalau genuinely terjadi) WAJIB tercatat sebagai `bug_prioritas_tinggi=True` di `HasilEksekusiAtomicIntent` — sinyal kebocoran Domain Gate/Retriever, bukan alur gagal normal (`CLAUDE.md` Prinsip Arsitektur).

## Kejadian

### E01 — Kebutuhan majemuk-bergantung, uji wave berulang nyata (KK literal utama, reuse skenario `gop_margin` M7.9-7.13)

**Payload:** turn 1, `session_id="eval-7.14-e01"`, `role_title="Front Office Staff"`, `question="Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"` — teks IDENTIK M7.9-7.13, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.9-7.13: 2-3 atomic intent, 1-2 `independen` + 1 `bergantung` — kebutuhan "perbandingan" yang bergantung pada kedua intent independen, `view_name_final=v_reservation_gop_impact_monthly` konsisten untuk yang lolos sampai Query Engine):**
- Retriever/Query Engine/Verification Gate kemungkinan besar meloloskan minimal 1 item wave 1 (independen) DAN 1 item wave 2 (bergantung pada wave 1) — REPLIKASI KONDISI YANG SUDAH TERBUKTI M7.9-7.13, kali ini sampai genuinely mengenai `chatbot_api`.
- **Bukti KK literal M7.14**: item wave 2 (bergantung) HARUS menunjukkan span `orchestration.wave` (wave.index=2) yang dimulai SETELAH span `execute_tool` terakhir wave 1 selesai — dikonfirmasi lewat timestamp span nyata Jaeger, DAN lewat urutan panggilan `verifikasi_gate_semua`/`eksekusi_atomic_intent_semua` (span `verification_gate.check`/`execute_tool` per item).
- `HasilEksekusiAtomicIntent.status` untuk seluruh item yang mencapai Execution WAJIB terisi data nyata (bukan simulasi) — dicatat apa adanya (`BERHASIL`/`SEBAGIAN`/`GAGAL_TEKNIS`), tidak dipaksa harus `BERHASIL`.
- Kalau ternyata Decomposition HANYA menghasilkan 1 wave (semua independen, non-determinisme dikenal) — dicatat transparan di `audit.md`, TIDAK di-retry paksa; E01 murni target UTAMA untuk 2-wave, bukan jaminan mutlak (mirror preseden non-determinisme M7.9-7.13).

---

### E02 — Baseline 1 wave, koreksi paksa `employee_id` sampai ke `chatbot_api` nyata (reuse skenario `evals/2.3-.../S01`/M7.11 E04/M7.12 E03/M7.13 E01, HR Staff)

**Payload:** turn 1, `session_id="eval-7.14-e02"`, `role_title="HR Staff"`, `question="Bagaimana hasil review kinerja Budi semester ini?"` — teks IDENTIK M7.13 E01, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.13 E01: 1 atomic intent, `view_name_final=v_hr_employee_performance_semester`, `cakupan_individu.terdeteksi=True`, `terkoreksi=True`, `request_final.params={"full_name": "Budi", "review_period": "...", "employee_id": "emp-eval"}`):**
- 1 atomic intent, SELURUHNYA wave 1 (independen) — baseline TANPA wave berulang, kontrol untuk memastikan kasus 1-wave tetap bekerja normal pasca-restrukturisasi M7.14.
- **Titik nyata baru dibanding M7.13**: `request_final` (dengan `employee_id` yang ditimpa paksa DAN `full_name="Budi"` tetap ada) SEKARANG benar-benar dikirim ke `chatbot_api`. Belum pernah diketahui bagaimana server nyata merespons kombinasi filter nama + `employee_id` sekaligus — dicatat APA ADANYA di `audit.md` (mis. kalau `chatbot_api` mengembalikan 0 baris karena kombinasi filter yang tidak match, itu `BERHASIL` dengan `nilai_hasil` kosong, BUKAN `GAGAL_TEKNIS` — beda semantik yang wajib dibedakan eksplisit).
- Span `orchestration.wave` HANYA 1 kali (`wave.index=1`) — tidak ada wave 2 untuk kejadian ini.

---

### E03 — Bukti kedua independen, domain berbeda (reuse skenario `evals/2.3-.../S02`/M7.13 E03, Maintenance Staff)

**Payload:** turn 1, `session_id="eval-7.14-e03"`, `role_title="Maintenance Staff"`, `question="Berapa banyak tiket yang ditangani teknisi Andi bulan ini?"` — teks IDENTIK M7.13 E03, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.13 E03: 1 atomic intent, `view_name_final=v_maintenance_technician_daily`, `terkoreksi=True`):**
- 1 atomic intent, wave 1 saja — kontrol domain `facility` (beda dari `reservation`/`hr` di E01/E02), memperkuat generalisasi klaim "Execution nyata bekerja lintas domain", bukan kebetulan satu domain saja.
- `HasilEksekusiAtomicIntent.status` dicatat apa adanya dari respons nyata `chatbot_api` untuk view ini (belum pernah diuji sebelumnya sampai lapisan HTTP nyata).

## Catatan Non-Determinisme

Reuse teks pertanyaan yang PERSIS sama dengan milestone sebelumnya TIDAK menjamin Decomposition/Domain Gate/Query Engine/Verification Gate menghasilkan jumlah/komposisi/status yang SAMA PERSIS di run M7.14 ini (pola berulang sejak M7.9). Verifikasi KK literal M7.14 (Checkpoint 7) SELALU membandingkan urutan span/status terhadap hasil RUN M7.14 itu sendiri. Kalau E01 kebetulan hanya menghasilkan 1 wave (bukan 2), itu dicatat transparan — KK literal tetap dianggap terpenuhi selama SETIDAKNYA satu kejadian di run ini (E01 atau replikasi ulang) genuinely menunjukkan 2 wave berurutan; kalau seluruh 3 kejadian gagal menghasilkan >1 wave pada percobaan pertama, dipertimbangkan menjalankan kejadian tambahan (E04) dengan skenario majemuk-bergantung lain sebelum audit ditulis, dicatat sebagai penyesuaian eksplisit di `audit.md`.

## Ringkasan Ekspektasi

| ID | `role_title` | Domain | Wave diharapkan | Fokus utama |
|---|---|---|---|---|
| E01 | Front Office Staff | reservation | 1-2 (target 2) | KK literal — urutan wave berurutan nyata |
| E02 | HR Staff | hr | 1 | Koreksi paksa employee_id sampai chatbot_api nyata |
| E03 | Maintenance Staff | facility | 1 | Bukti kedua independen domain berbeda |
