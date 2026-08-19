# Rancangan Pengujian — Sambungan 8: Query Engine → Verification Gate (Milestone 7.13)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Struktur mirror `evals/7.12-.../rancangan.md`.

**Pelajaran metodologi dari `evals/7.9-.../audit.md` s.d. `evals/7.12-.../audit.md`**: jumlah/komposisi `atomic_intent` hasil Decomposition, dan status `lolos` M3.5 per intent, TIDAK BOLEH diasumsikan tetap bahkan untuk teks pertanyaan identik lintas run (non-determinisme `temperature=0` nyata, `docs/keterbatasan-diterima.md` #3) — ekspektasi di bawah ditulis sebagai **invarian mekanisme**, bukan jumlah absolut, dan `session_id` BARU dipakai per kejadian (`eval-7.13-eXX`, bukan reuse `eval-7.1X-eXX`) mengikuti preseden Keputusan 6 M7.10.

**Temuan tambahan dari inspeksi `evals/7.12-.../payloads/E01.json` (reuse gop_margin, dipakai lagi sebagai E02 di sini)**: pada run M7.12 aktual, dari 3 atomic intent yang mencapai Query Engine, HANYA 1 yang `HasilVerifikasiBentukRequest.lolos=True` (item "perbandingan", params terisi lengkap) — 2 lainnya (`nilai_tunggal` dengan params kosong) `lolos=False`. Ini konsisten dengan Keputusan 2 M7.13: kedua item `lolos=False` itu akan DI-SKIP oleh `verifikasi_gate_semua()`, tidak pernah mencapai Verification Gate sama sekali. E02 di bawah karena itu ditulis sebagai invarian per-item (bukan jumlah tetap 3), sama seperti kejadian lain.

## Yang Diuji

`proses_turn()` — segmen baru M7.13: `verifikasi_gate_semua(query_engine_result, retriever_result, cakupan_individu_result, payload.employee_id)` dipanggil sekuensial setelah Query Engine (M7.12) selesai. Kejadian di sini menjalankan pipeline PENUH dari `proses_turn()` nyata — bukan tiga list buatan tangan langsung dipassing ke fungsi manapun.

**Invarian mekanisme yang wajib benar di SEMUA kejadian:**

1. Untuk tiap `(hasil_susun, hasil_verifikasi)` di `query_engine_result` dengan `hasil_verifikasi is not None and hasil_verifikasi.lolos=True`, item itu WAJIB muncul di `KeadaanTurn.verification_gate` (dicocokkan via `atomic_intent_id`) — dan sebaliknya, item dengan `hasil_verifikasi is None` atau `lolos=False` TIDAK PERNAH muncul di `KeadaanTurn.verification_gate`. Panjang `verification_gate` <= jumlah item `lolos=True` di `query_engine_result`.
2. Untuk tiap item yang lolos ke Verification Gate: `constraint` yang benar-benar dipakai (`ConstraintCakupanIndividu` di balik pemanggilan `verifikasi_gate()`) HARUS PERSIS SAMA (`terdeteksi`, `alasan`) dengan `cakupan_individu_result[i].constraint` milik `atomic_intent_id` yang SAMA pada RUN itu sendiri — bukan dicatat manual/di-hardcode dari kejadian lain.
3. **Koreksi paksa**: kalau `constraint.terdeteksi=True` DAN `request.params.get("employee_id") != payload.employee_id`, maka `HasilVerifikasiGate.terkoreksi=True` dan `request_final.params["employee_id"] == payload.employee_id` (fungsi `tegakkan_constraint_cakupan_individu()`, `verifikasi_gate.py` baris 65-80). Kalau `constraint.terdeteksi=False`, maka `terkoreksi=False` dan `request_final.params` TIDAK berubah dari `request` asli Query Engine.
4. Span pembungkus `verification_gate.verifikasi_gate_semua` (tracer `verification_gate.verifikasi_gate`) SELALU terbuka dengan atribut `intent.count` = panjang `query_engine_result` yang diteruskan (SEBELUM filter `None`/`lolos=False`) — terlepas berapa yang di-skip. Untuk tiap item yang benar-benar diproses, span anak `verification_gate.check` (`verification.check_name="constraint_cakupan_individu"`, atribut `verification.terkoreksi`) WAJIB ter-emit.

## Kejadian

### E01 — Koreksi paksa `employee_id` (bukti KK literal utama, reuse skenario `evals/2.3-.../S01`/M7.11 E04/M7.12 E03, HR Staff)

**Payload:** turn 1, `session_id="eval-7.13-e01"`, `role_title="HR Staff"`, `question="Bagaimana hasil review kinerja Budi semester ini?"` — teks IDENTIK `evals/2.3-.../S01.json`/`evals/7.11-.../E04`/`evals/7.12-.../E03`, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.11 E04/M2.3 S01: 1 atomic intent, domain `hr` diizinkan, `view_name_final=v_hr_employee_performance_semester`, `cakupan_individu.terdeteksi=True` — "kebutuhan menyentuh kategori data performa individu staf"):**
- Retriever kemungkinan besar menghasilkan atomic intent dengan `view_name_final` terisi, dan `cakupan_individu_result` untuk intent itu ber-`terdeteksi=True` (reuse teks yang SUDAH terbukti 2x konsisten sebelumnya).
- Query Engine (M3.4) kemungkinan menyusun `params` yang mengacu nama "Budi" (mis. `employee_name`/filter serupa), BUKAN `employee_id` milik caller — sehingga `request.params.get("employee_id") != payload.employee_id` bernilai True secara alami (caller tidak pernah menyebut ID dirinya sendiri di pertanyaan).
- **Bukti KK literal M7.13**: item ini mencapai Verification Gate, `HasilVerifikasiGate.terkoreksi=True`, `request_final.params["employee_id"] == payload.employee_id` (payload run ini, BUKAN nilai hardcoded) — dikonfirmasi lewat inspeksi langsung return value Python DAN span `verification_gate.check` (`verification.check_name="constraint_cakupan_individu"`, `verification.terkoreksi=True`, dikonfirmasi lewat Jaeger).
- Constraint yang dipakai (`terdeteksi=True`) WAJIB dibuktikan berasal dari `cakupan_individu_result` hasil Domain Gate SUNGGUHAN di run ini — bukan dicatat manual (syarat eksplisit KK sumber M7.13).

---

### E02 — Baseline tanpa constraint (reuse skenario `evals/7.11-.../E01`/`evals/7.12-.../E01`, Front Office Staff, gop_margin)

**Payload:** turn 1, `session_id="eval-7.13-e02"`, `role_title="Front Office Staff"`, `question="Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"` — teks IDENTIK `evals/7.11-.../E01`/`evals/7.12-.../E01`, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.11 E01/M7.12 E01: beberapa atomic intent, domain `financial` ditolak untuk sebagian, `cakupan_individu.terdeteksi=False` untuk SEMUA intent — skenario ini murni tentang otorisasi domain, bukan cakupan-individu):**
- Untuk SETIAP atomic intent yang mencapai Verification Gate di run ini (`lolos=True` di M3.5): `cakupan_individu_result` intent itu ber-`terdeteksi=False` (reuse teks yang SUDAH terbukti 2x `terdeteksi=False` untuk SEMUA intent-nya).
- **Bukti**: `HasilVerifikasiGate.terkoreksi=False` untuk SEMUA item, `request_final.params == request.params` asli Query Engine (TIDAK berubah) — membuktikan Verification Gate TIDAK melakukan koreksi kalau constraint tidak terdeteksi, walau constraint yang dicek genuinely berasal dari Domain Gate run ini (bukan sekadar tidak pernah dipanggil).
- Kemungkinan besar TIDAK SEMUA atomic intent hasil Decomposition mencapai Verification Gate (preseden M7.12 E01: sebagian `lolos=False` di M3.5, di-skip lebih dulu) — ini DIHARAPKAN, bukan kegagalan, sepanjang item yang genuinely diproses memenuhi invarian di atas.

---

### E03 — Bukti kedua independen, domain berbeda (reuse skenario `evals/2.3-.../S02`, Maintenance Staff)

**Payload:** turn 1, `session_id="eval-7.13-e03"`, `role_title="Maintenance Staff"`, `question="Berapa banyak tiket yang ditangani teknisi Andi bulan ini?"` — teks IDENTIK `evals/2.3-.../S02.json`, `session_id` BARU (BELUM PERNAH dipakai di Sambungan Level 2 manapun sebelumnya — bukti independen ketiga di luar rantai gop_margin/Budi yang sudah berulang kali direuse).

**Ekspektasi (mengacu hasil nyata `evals/2.3-.../S02.json`: domain `facility` diizinkan, `cakupan_individu.terdeteksi=True` — "kebutuhan menyentuh kategori data performa individu staf"):**
- Retriever kemungkinan menghasilkan atomic intent dengan `view_name_final` terisi (domain `facility`), `cakupan_individu_result` ber-`terdeteksi=True`.
- Sama seperti E01: `request.params` Query Engine kemungkinan mengacu nama "Andi", bukan `employee_id` caller — `terkoreksi=True` diharapkan, `request_final.params["employee_id"] == payload.employee_id` run ini.
- **Bukti kedua independen** untuk KK literal M7.13 di luar E01 — domain (`facility` vs `hr`) dan `session_id` yang genuinely belum pernah dieksekusi di Sambungan manapun, memperkuat generalitas mekanisme (bukan kebetulan satu domain).

## Catatan Non-Determinisme

Reuse teks pertanyaan yang PERSIS sama dengan milestone sebelumnya TIDAK menjamin Decomposition/Domain Gate/Query Engine menghasilkan jumlah/komposisi/status `lolos` yang SAMA PERSIS di run M7.13 ini (pola sudah teramati berulang sejak M7.9 — bahkan `session_id` baru untuk payload identik pernah menghasilkan `klasifikasi`/status berbeda, lihat `evals/7.12-.../payloads/E01.json` yang mengalami 2/3 item `lolos=False`). Verifikasi KK literal M7.13 (Checkpoint 6) karena itu SELALU membandingkan `constraint`/`terkoreksi`/`request_final.params["employee_id"]` terhadap `cakupan_individu_result`/`payload.employee_id` hasil **RUN M7.13 itu sendiri** — bukan terhadap nilai yang tercatat di `payloads/` milestone lain. Kalau jumlah/komposisi atomic intent yang mencapai Verification Gate meleset dari ekspektasi di atas (mis. E02 ternyata SEMUA `lolos=False`, sehingga `verification_gate` kosong untuk kejadian itu), itu dicatat transparan di `audit.md` (bukan disembunyikan/di-retry), sepanjang invarian mekanisme (bagian "Yang Diuji") tetap terbukti benar untuk SETIAP item yang genuinely mencapai Verification Gate. Kalau E02 kebetulan menghasilkan `verification_gate` kosong, KK literal M7.13 (koreksi paksa) tetap dianggap terbukti selama E01 DAN E03 sama-sama menunjukkan `terkoreksi=True` — E02 murni kontrol negatif (constraint tidak terdeteksi -> tidak ada koreksi), bukan sumber utama bukti KK.

## Ringkasan Ekspektasi

| ID | `role_title` | Reuse dari | `cakupan_individu.terdeteksi` (referensi) | `terkoreksi` diharapkan | `request_final.params["employee_id"]` diharapkan |
|---|---|---|---|---|---|
| E01 | HR Staff | `evals/2.3-.../S01`, M7.11 E04, M7.12 E03 | `True` | `True` | = `payload.employee_id` run ini |
| E02 | Front Office Staff | M7.11 E01, M7.12 E01 | `False` (semua intent) | `False` | tidak berubah dari `request` Query Engine |
| E03 | Maintenance Staff | `evals/2.3-.../S02` | `True` | `True` | = `payload.employee_id` run ini |
