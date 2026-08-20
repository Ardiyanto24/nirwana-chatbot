# Rancangan Pengujian — Sambungan 11: Verifikasi Alur Penuh End-to-End (Milestone 7.16)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Struktur mirror `evals/7.14-.../rancangan.md`, dengan fokus verifikasi yang berbeda: bukan urutan wave (sudah dibuktikan M7.14), melainkan **cakupan span 9 layer per skenario**.

**Beda mendasar dari SELURUH eval M7.6-7.15**: ini adalah kejadian PERTAMA `proses_turn()` dijalankan sebagai **satu sistem utuh 9 layer** (Input Layer sampai Interpretation) untuk skenario yang representatif KK asli Level 2 — sebelumnya tiap Sambungan hanya membuktikan SATU pasang layer per milestone. Tidak ada kode baru di milestone ini (`decisions.md` Keputusan 1) — murni eksekusi + pembuktian.

**Klarifikasi mengikat (instruksi eksplisit user, `decisions.md` Keputusan 2)**: ketiga skenario TIDAK mensyaratkan `BERHASIL` — `SEBAGIAN`/`GAGAL_TEKNIS` yang dilaporkan jujur oleh narasi tetap dianggap bukti KK terpenuhi, karena `docs/keterbatasan-diterima.md` #15 membuat `BERHASIL` genuinely mustahil terjadi di lingkungan `chatbot_api` lokal saat ini.

**Pelajaran metodologi (M7.9-7.15)**: jumlah/komposisi `atomic_intent` hasil Decomposition TIDAK BOLEH diasumsikan tetap (non-determinisme `temperature=0`, `docs/keterbatasan-diterima.md` #3) — ekspektasi ditulis sebagai invarian mekanisme, `session_id` BARU per kejadian (`eval-7.16-eXX`).

## Yang Diuji

`proses_turn()` dijalankan APA ADANYA (tanpa mock/intervensi manual apa pun) untuk 3 skenario yang merepresentasikan KK M7.16: kebutuhan tunggal sederhana (E01), kebutuhan dengan wave (E02), turn dengan rujukan lintas-turn (E03). `chatbot_api` lokal (`http://127.0.0.1:8000`) DAN Jaeger (`docker compose`, `infra/observability/`) HARUS `up` selama eksekusi.

**Invarian yang wajib benar di SEMUA kejadian:**

1. `proses_turn()` mengembalikan `KeadaanTurn` lengkap 15 field TANPA exception tak tertangani menjalar keluar (kecuali `APIError` dari `susun_dan_verifikasi_narasi()`, satu-satunya jalur yang SENGAJA tanpa fallback sejak M7.5 — tidak diharapkan terjadi di 3 skenario ini, tapi kalau terjadi, dicatat sebagai temuan bukan kegagalan verifikasi).
2. `hasil.interpretation[0].narasi` (teks narasi akhir) WAJIB berisi teks non-kosong yang mencerminkan status aktual (bukan mengarang `BERHASIL` yang tidak terjadi) — kejujuran terhadap keterbatasan.
3. Untuk SETIAP skenario, span berikut WAJIB muncul sebagai descendant `invoke_agent` dalam SATU trace yang sama (peta lengkap di `decisions.md` Keputusan 5): `input.validate`; minimal satu `chat` dari Context Resolution + `matching.evaluate`; `chat` Decomposition; `domain_gate.identifikasi_semua`, `domain_gate.periksa_otorisasi_semua`, `domain_gate.deteksi_constraint_semua`; `retriever.proses_semua`; `query_engine.susun_dan_verifikasi_request_semua`; `verification_gate.verifikasi_gate_semua`; `execution.eksekusi_atomic_intent_semua`, `execution.susun_dan_simpan_paket_semua`; `orchestration.susun_paket_narasi`; `chat` Interpretation (narasi + verifikasi kesetiaan).
4. Untuk E03 khusus: span `memory.retrieve` WAJIB muncul (Tarik Memory genuinely terpanggil karena `history` fiktif memicu `is_dependent=True`).
5. Untuk E02 khusus: span `orchestration.wave` WAJIB muncul lebih dari sekali kalau Decomposition menghasilkan kebutuhan bergantung (replikasi M7.14 E01).

## Kejadian

### E01 — Kebutuhan tunggal sederhana (reuse `evals/7.9-sambungan-pencocokan/payloads/E01.json`)

**Payload:** turn 1, `session_id="eval-7.16-e01"`, `role_title="General Manager"`, `question="Berapa occupancy rate properti kita bulan Juni 2026?"` — teks IDENTIK M7.9 E01, `session_id` BARU, TANPA `history`.

**Ekspektasi (mengacu hasil nyata M7.9 E01: 1 atomic intent `nilai_tunggal`, tanpa ketergantungan, `session_memory=null` karena Tarik Memory tidak dipanggil):**
- `ketergantungan.is_dependent=False`, span `memory.retrieve` TIDAK ADA (fast-path M7.7) — ini kontrol negatif yang MEMBUKTIKAN Context Resolution tetap benar memilih jalur pendek di dalam pipeline PENUH, bukan cuma di potongan M7.7/M7.9 yang sudah pernah diuji terisolasi.
- 1 atomic intent mengalir genuinely sampai Retriever/Query Engine/Verification Gate/Execution — domain `General Manager` diharapkan lolos otorisasi penuh (role tertinggi di katalog role), sehingga TIDAK ada titik di rantai yang menerima 0 item (mencegah risiko span kosong yang tercantum di plan Bagian Risiko).
- `HasilEksekusiAtomicIntent.status` dicatat apa adanya (`BERHASIL`/`SEBAGIAN`/`GAGAL_TEKNIS`) — skenario ini sebelumnya (M7.9) HANYA teruji sampai `matches`, jadi ini pertama kali payload ini genuinely mencapai Execution+Interpretation.
- `hasil.interpretation[0].narasi` diperiksa menyebutkan angka/status occupancy secara jujur (bukan mengarang jika `SEBAGIAN`).

---

### E02 — Kebutuhan dengan wave (reuse `evals/7.14-sambungan-execution/payloads/E01.json`)

**Payload:** turn 1, `session_id="eval-7.16-e02"`, `role_title="Front Office Staff"`, `question="Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"` — teks IDENTIK M7.9-7.14, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.14 E01: 3 atomic intent, 2 `independen`+1 `bergantung`, 2 wave, kedua item yang lolos Verification Gate berakhir `GAGAL_TEKNIS` via jalur revisi 400 M4.2 — BUKAN kegagalan M7.16, sudah tercatat sebagai temuan follow-up M3.4 di `milestones/7.14-.../report.md`):**
- Kalau Decomposition kembali menghasilkan struktur bergantung serupa: span `orchestration.wave` WAJIB muncul ≥2 kali, wave kedua dimulai setelah wave pertama selesai (mekanisme SUDAH dibuktikan M7.14 — TIDAK diuji ulang urutannya di sini, fokus M7.16 murni cakupan span 9 layer + kelanjutan sampai Interpretation).
- **Titik nyata baru dibanding M7.14**: `paket_narasi`/`interpretation` sekarang genuinely terisi untuk skenario ini — M7.14 berhenti di `execution` (field `paket_narasi`/`interpretation` belum ada saat itu). Kalau kedua sub-kebutuhan berakhir `GAGAL_TEKNIS` (seperti run M7.14), verifikasi bahwa `susun_paket_narasi()` tetap menghasilkan paket via jalur EKSEKUSI (bukan jalur gap sintetis — item ini SAMPAI ke Execution dan Execution SENDIRI yang melaporkan gagal, beda dari item yang tersaring SEBELUM Execution) dan narasi akhir melaporkan kegagalan teknis secara jujur.
- Non-determinisme diterima: kalau kali ini Decomposition HANYA menghasilkan struktur independen (1 wave), dicatat transparan di `audit.md` — E02 tetap sah sebagai bukti "kebutuhan dengan wave" SELAMA riwayat run M7.9-7.14 sudah cukup kuat menunjukkan payload ini SECARA KARAKTERISTIK menghasilkan struktur bergantung (4 dari 5 run sebelumnya).

---

### E03 — Turn dengan rujukan lintas-turn (payload baru, `history` fiktif mirror `evals/7.7-.../E01.json`)

**Payload:** turn 2, `session_id="eval-7.16-e03"` (BARU, belum pernah dipakai), `role_title="Corporate Revenue Director"`, `question="Bandingkan dengan bulan sebelumnya."`, `history=[{"turn_index": 1, "question": "Berapa revenue reservasi bulan Maret 2026?", "answer": "Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]` — payload IDENTIK `evals/7.7-.../E01.json` (sudah terbukti `is_dependent=True`/`referenced_turn_index=1` di M7.7), `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.7 E01: `ketergantungan.is_dependent=True`, `rewrite.rewritten_question` menyisipkan bulan sebelumnya (Februari), span `chat`(Rewrite)+`memory.retrieve`(Tarik Memory) sama-sama child `invoke_agent`):**
- `ketergantungan.is_dependent=True`, `referenced_turn_index=1` — terdeteksi murni dari `history` payload (bukan Session Memory DB, `decisions.md` Keputusan 3).
- Span `memory.retrieve` WAJIB muncul — Tarik Memory genuinely terpanggil. Karena `session_id` ini BARU (belum pernah ada turn 1 sungguhan tersimpan), `retrieve_session_memory()` diharapkan mengembalikan `[]` (list kosong, BUKAN error) — `session_memory=[]` di `KeadaanTurn`, bukan `None`.
- `matches` untuk atomic intent hasil Decomposition (kemungkinan besar "Berapa revenue reservasi bulan Februari 2026?" dibanding Maret) diharapkan SELURUHNYA `perlu_eksekusi` (tidak ada kandidat "selesai" karena `session_memory=[]`) — mengalir genuinely sampai Execution+Interpretation seperti E01.
- **TIDAK diharapkan** dan TIDAK dianggap kegagalan: paket "selesai" hasil re-key `sumber_arsip()` (M7.15) — cabang itu SENGAJA tidak dicakup skenario ini (`decisions.md` Keputusan 3, dampak eksplisit).
- Narasi akhir diperiksa menyebutkan perbandingan bulan (Februari vs Maret) secara jujur sesuai apa pun status Execution-nya.

## Catatan Non-Determinisme

Sama seperti M7.9-7.15: reuse teks pertanyaan yang PERSIS sama TIDAK menjamin Decomposition/Domain Gate/Query Engine/Verification Gate menghasilkan komposisi identik run sebelumnya. Verifikasi KK M7.16 (cakupan span 9 layer + narasi jujur) dibandingkan terhadap hasil RUN M7.16 itu sendiri, bukan ekspektasi kaku dari run milestone lain — kolom "Ekspektasi" di atas adalah PANDUAN berbasis riwayat, bukan syarat lolos/gagal mutlak. Kalau salah satu skenario menyimpang jauh dari ekspektasi (mis. E02 ternyata 0 wave, atau domain yang biasanya lolos kali ini ditolak seluruhnya sehingga ada layer menerima 0 item), dicatat transparan di `audit.md`; kalau itu membuat cakupan span 9 layer TIDAK bisa dibuktikan penuh untuk skenario itu, dipertimbangkan menjalankan kejadian tambahan (E04) sebelum audit ditulis.

## Ringkasan Ekspektasi

| ID | `role_title` | Fokus KK | Span pembeda utama |
|---|---|---|---|
| E01 | General Manager | Kebutuhan tunggal sederhana | Fast-path (TANPA `memory.retrieve`) sampai Interpretation |
| E02 | Front Office Staff | Kebutuhan dengan wave | `orchestration.wave` ≥2× (kalau bergantung terulang) |
| E03 | Corporate Revenue Director | Rujukan lintas-turn | `memory.retrieve` ADA, `session_memory=[]` |
