# Rancangan Pengujian — Sambungan 7: Retriever → Query Engine (Milestone 7.12)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Struktur mirror `evals/7.11-.../rancangan.md`.

**Pelajaran metodologi dari `evals/7.10-.../audit.md` dan `evals/7.11-.../audit.md`**: jumlah/komposisi `atomic_intent` hasil Decomposition TIDAK BOLEH diasumsikan tetap bahkan untuk teks pertanyaan identik lintas run (non-determinisme `temperature=0` nyata, `docs/keterbatasan-diterima.md` #3) — ekspektasi di bawah ditulis sebagai **invarian mekanisme**, bukan jumlah absolut, dan `session_id` BARU dipakai per kejadian (`eval-7.12-eXX`, bukan reuse `eval-7.11-eXX`) mengikuti preseden Keputusan 6 M7.10.

## Yang Diuji

`proses_turn()` — segmen baru M7.12: `susun_dan_verifikasi_request_semua(retriever_result)` dipanggil sekuensial setelah Retriever (M7.11) selesai. Kejadian di sini menjalankan pipeline PENUH dari `proses_turn()` nyata — bukan `list[HasilKecukupanStruktural]` buatan tangan langsung dipassing ke fungsi manapun.

**Invarian mekanisme yang wajib benar di SEMUA kejadian:**
1. Untuk tiap atomic intent dengan `view_name_final` terisi, `request.view_name` yang benar-benar dikirim ke Query Engine (`HasilVerifikasiBentukRequest.request.view_name` atau `HasilPenyusunanRequest.request.view_name` bila verifikasi tidak sempat jalan) HARUS PERSIS SAMA dengan `view_name_final` hasil Retriever pada RUN itu sendiri — bukan dicocokkan terhadap nilai literal yang di-hardcode dari run M7.11 sebelumnya.
2. Atomic intent dengan `view_name_final=None` TIDAK PERNAH muncul di `KeadaanTurn.query_engine` — panjang `query_engine` <= panjang `retriever`.
3. Span pembungkus `query_engine.susun_dan_verifikasi_request_semua` (tracer `query_engine.query_engine`) SELALU terbuka dengan atribut `intent.count` = panjang `KeadaanTurn.retriever` yang diteruskan (SEBELUM filter `view_name_final=None`) — terlepas berapa yang di-skip.

## Kejadian

### E01 — `view_name` persis sama dengan hasil Retriever (bukti KK literal utama, reuse skenario `gop_margin` M7.11 E01)

**Payload:** turn 1, `session_id="eval-7.12-e01"`, `role_title="Front Office Staff"`, `question="Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"` — teks IDENTIK `evals/7.11-.../E01`, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.11 E01, sebagai referensi — bukan jaminan reproduksi persis, lihat "Catatan Non-Determinisme" di bawah):**
- Retriever kemungkinan besar menghasilkan minimal satu atomic intent dengan `view_name_final` terisi (M7.11 E01 aktual: 3 atomic intent, 2 di antaranya `view_name_final` terisi — salah satunya `v_reservation_gop_impact_monthly` untuk intent inti gop_margin).
- **Bukti KK literal M7.12**: untuk SETIAP atomic intent dengan `view_name_final` terisi, `request.view_name` yang dikirim ke `susun_request_atomic_intent()` (dan hasil akhirnya) HARUS SAMA PERSIS dengan `view_name_final` intent itu di RUN M7.12 ini sendiri — dibuktikan lewat inspeksi langsung return value Python DAN span `chat` M3.4 (atribut `request.view_name`, dikonfirmasi lewat Jaeger).
- `HasilVerifikasiBentukRequest.lolos` diharapkan `True` untuk Kriteria 1 (kepatuhan sumber `_view_name_sesuai_retriever()`) — karena `view_name`/`view_name_tervalidasi_retriever` sama-sama dari `view_name_final` yang identik (decisions.md Keputusan 5), mismatch KK1 M3.5 SECARA STRUKTURAL tidak mungkin terjadi di titik wiring produksi ini (beda dari skenario test M7.4 sendiri yang sengaja memaksa nilai berbeda).

---

### E02 — Item `view_name_final=None` di-skip dari Query Engine (reuse skenario M7.11 E03, F&B Staff)

**Payload:** turn 1, `session_id="eval-7.12-e02"`, `role_title="F&B Staff"`, `question="Berapa GOP (gross operating profit) properti bulan ini?"` — teks IDENTIK `evals/7.11-.../E03`, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.11 E03: 1 atomic intent, domain `financial` ditolak seluruhnya, `view_name_final=None`):**
- Retriever menghasilkan atomic intent dengan `view_name_final=None` (domain `financial` ditolak otorisasi F&B Staff, `domain_diizinkan=[]`, 0 kandidat).
- **Bukti skip bekerja**: atomic intent ini TIDAK muncul di `KeadaanTurn.query_engine` sama sekali (panjang `query_engine` = panjang `retriever` dikurangi jumlah `view_name_final=None`) — `susun_request_atomic_intent()`/`susun_dan_verifikasi_request_atomic_intent()` TIDAK PERNAH dipanggil untuk intent ini (dikonfirmasi TIDAK ADA span `chat` M3.4/M3.5 tambahan untuk intent ini di trace).
- `proses_turn()` selesai NORMAL tanpa exception (mirror ketahanan mekanisme yang sudah dibuktikan M7.11 E03 satu langkah sebelumnya).

---

### E03 — Bukti kedua independen + kepatuhan sumber (reuse skenario M7.11 E04, HR Staff)

**Payload:** turn 1, `session_id="eval-7.12-e03"`, `role_title="HR Staff"`, `question="Bagaimana hasil review kinerja Budi semester ini?"` — teks IDENTIK `evals/7.11-.../E04`, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.11 E04: 1 atomic intent, domain `hr` diizinkan, `view_name_final=v_hr_employee_performance_semester`):**
- Retriever menghasilkan atomic intent dengan `view_name_final` terisi (kemungkinan `v_hr_employee_performance_semester`, tapi dibandingkan terhadap hasil RUN INI sendiri, bukan literal hardcoded).
- `request.view_name` yang dikirim Query Engine PERSIS sama dengan `view_name_final` — bukti KEDUA independen untuk KK literal M7.12 (di luar E01).
- `HasilVerifikasiBentukRequest.lolos=True` (kepatuhan sumber otomatis terpenuhi by construction).
- `cakupan_individu.terdeteksi=True` untuk intent ini (mewarisi hasil M7.11 E04) — dicatat sebagai konteks, BUKAN bagian KK M7.12 (constraint tidak memengaruhi Query Engine, decisions.md M7.11 Keputusan 8).

## Catatan Non-Determinisme

Reuse teks pertanyaan yang PERSIS sama dengan M7.11 TIDAK menjamin Decomposition/Domain Gate menghasilkan jumlah/komposisi atomic intent yang SAMA PERSIS di run M7.12 ini (pola sudah teramati berulang: M7.9→M7.10, M7.10→M7.11 — bahkan `session_id` baru untuk payload identik pernah menghasilkan `klasifikasi` berbeda). Verifikasi KK literal M7.12 (Checkpoint 6) karena itu SELALU membandingkan `request.view_name` terhadap `view_name_final` hasil Retriever **pada RUN M7.12 itu sendiri** — bukan terhadap nilai yang tercatat di `payloads/` M7.11. Kalau jumlah/komposisi atomic intent meleset dari ekspektasi di atas, itu dicatat transparan di `audit.md` (bukan disembunyikan/di-retry), sepanjang invarian mekanisme (bagian "Yang Diuji") tetap terbukti benar untuk SETIAP atomic intent yang genuinely dihasilkan.

## Ringkasan Ekspektasi

| ID | `role_title` | Reuse dari | `view_name_final` (referensi M7.11) | Diteruskan ke Query Engine? | `request.view_name` diharapkan |
|---|---|---|---|---|---|
| E01 | Front Office Staff | M7.11 E01 | terisi (`v_reservation_gop_impact_monthly`, salah satu intent) | Ya | = `view_name_final` run ini |
| E02 | F&B Staff | M7.11 E03 | `None` | **Tidak (di-skip)** | — |
| E03 | HR Staff | M7.11 E04 | terisi (`v_hr_employee_performance_semester`) | Ya | = `view_name_final` run ini |
