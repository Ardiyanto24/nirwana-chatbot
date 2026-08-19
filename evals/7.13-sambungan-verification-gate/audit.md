# Audit — Sambungan 8: Query Engine → Verification Gate (Milestone 7.13)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-19), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) dinyalakan ulang sebelum eksekusi (`docker compose up -d` di `infra/observability/`, stack tidak `up` di awal sesi ini).

**Catatan operasional**: BEDA dari M7.12, eksekusi kali ini LANCAR percobaan pertama — tidak ada hang. Ketiga kejadian selesai dalam satu proses background tunggal tanpa intervensi restart.

## Ringkasan

**3/3 kejadian LOLOS — koreksi paksa `employee_id` terbukti benar di SELURUH item yang mencapai Verification Gate (5 dari 5: E01×1, E02×3, E03×1)**, dan constraint yang dipakai terbukti berasal dari `KeadaanTurn.cakupan_individu` (Domain Gate sungguhan run ini, dicocokkan via `atomic_intent_id`) — bukan dicatat manual. KK literal M7.13 terbukti PALING JELAS di E01 dan E03: keduanya menghasilkan `constraint.terdeteksi=True`, dan `verifikasi_gate_semua()` menimpa paksa `params["employee_id"]` dari nilai yang semula TIDAK ADA (Query Engine hanya menyusun filter nama subjek — `full_name`/`technician_name` — bukan `employee_id` caller) menjadi persis `payload.employee_id` run ini.

**Penyimpangan dari rencana (non-determinisme Decomposition, pola berulang M7.9→M7.12)**: E02 (baseline) menghasilkan 5 atomic intent dari Decomposition (bukan 3 seperti run M7.11/M7.12 asli), 2 di antaranya `view_name_final=None` di Retriever (di-skip sebelum Query Engine), dan SEMUA 3 sisanya `lolos=True` di M3.5 (berbeda dari run M7.12 E01 yang hanya 1/3 `lolos=True`) — sehingga 3 item (bukan 1) mencapai Verification Gate di kejadian ini. Dicatat transparan, TIDAK di-retry untuk memaksa reproduksi persis — komposisi lebih besar ini justru memberi 3 bukti independen sekaligus untuk kontrol negatif (constraint tidak terdeteksi → tidak ada koreksi), bukan melemahkan verdict.

| ID | `role_title` | Item mencapai Verification Gate | `constraint.terdeteksi` | `terkoreksi` | Koreksi benar | Verdict |
|---|---|---|---|---|---|---|
| E01 | HR Staff | 1/1 | `True` | `True` | 1/1 | ✅ **LOLOS — bukti KK literal utama** |
| E02 | Front Office Staff | 3/3 | `False` (semua) | `False` (semua) | 3/3 | ✅ LOLOS — kontrol negatif (3x independen) |
| E03 | Maintenance Staff | 1/1 | `True` | `True` | 1/1 | ✅ LOLOS — bukti kedua independen |

## Analisis Per Kejadian

### E01 — Koreksi paksa `employee_id` untuk "review kinerja Budi" (LOLOS — bukti KK literal utama)

`trace_id=cdec64441824479e4db0e40c1702ce10`. Payload: `role_title="HR Staff"`, pertanyaan "Bagaimana hasil review kinerja Budi semester ini?" (teks identik `evals/2.3-.../S01`/`evals/7.11-.../E04`/`evals/7.12-.../E03`, `session_id` baru `eval-7.13-e01`). Decomposition `tunggal`, 1 atomic_intent — PERSIS sesuai prediksi. Domain `hr`+`employees_directory` diizinkan seluruhnya, `KeadaanTurn.cakupan_individu` untuk intent ini: `constraint.terdeteksi=True`, `alasan="kebutuhan menyentuh kategori data performa individu staf"` (identik alasan `evals/2.3-.../S01.json`). Retriever: `view_name_final=v_hr_employee_performance_semester`. Query Engine menyusun `request.params={"full_name": "Budi", "review_period": "2026-S2"}` — TIDAK menyertakan `employee_id` sama sekali (Query Engine menyusun filter berdasarkan nama subjek pertanyaan, bukan identitas caller), `lolos=True`.

`verifikasi_gate_semua()` mencocokkan `atomic_intent_id` ini terhadap `cakupan_individu_result` (constraint `terdeteksi=True` genuinely dari Domain Gate run ini) dan `retriever_result` (`view_name_final` sama) — memanggil `verifikasi_gate()`. Cek 1-2 lolos (view_name valid, kepatuhan sumber sesuai). Cek 3 (`tegakkan_constraint_cakupan_individu`): `constraint.terdeteksi=True` dan `params.get("employee_id") (None) != employee_id ("emp-eval")` → TIMPA PAKSA, `request_final.params={"full_name": "Budi", "review_period": "2026-S2", "employee_id": "emp-eval"}`, `terkoreksi=True`. Cek 4 (kelengkapan) lolos. Hasil akhir: `HasilVerifikasiGate.lolos=True`, `terkoreksi=True`. Span Jaeger mengonfirmasi: `verification_gate.verifikasi_gate_semua` (`intent.count=1`), span `verification_gate.check` dengan `verification.check_name="constraint_cakupan_individu"` membawa tag `verification.terkoreksi=true`.

**Kesimpulan: Kriteria Keberhasilan literal Milestone 7.13 TERPENUHI PENUH** — constraint cakupan-individu yang mengalir dari Domain Gate asli (M7.11) sampai Verification Gate (M2.4) menghasilkan koreksi paksa yang benar, dibuktikan `constraint` yang dicek genuinely berasal dari `cakupan_individu_result` run ini (dicocokkan via `atomic_intent_id`, bukan dicatat manual), lewat inspeksi return value Python DAN span Jaeger.

### E02 — Baseline tanpa constraint, 3 item independen (LOLOS — kontrol negatif)

`trace_id=091415a735f417afadbf3b8298b6cc6c`. Payload: `role_title="Front Office Staff"`, "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?" (teks identik `evals/7.11-.../E01`/`evals/7.12-.../E01`, `session_id` baru `eval-7.13-e02`). Decomposition menghasilkan 5 atomic_intents (majemuk, `verifikasi_valid=False` — non-determinisme dikenal, bukan kegagalan struktural). Domain `financial` DITOLAK untuk seluruh 5 intent (role Front Office Staff), sehingga `cakupan_individu.terdeteksi=False` untuk SEMUA 5 — skenario ini genuinely tidak pernah menyentuh kategori data performa individu staf, murni soal otorisasi domain.

Retriever: 3 dari 5 intent mendapat `view_name_final=v_reservation_gop_impact_monthly` (2 lainnya `None`, di-skip sebelum Query Engine — mekanisme M7.12). Ketiga intent yang tersisa SEMUANYA `lolos=True` di M3.5 kali ini (berbeda dari run M7.12 asli), sehingga `verifikasi_gate_semua()` menerima `intent.count=3`. Untuk KETIGANYA: constraint yang dicocokkan (`terdeteksi=False`) memicu `tegakkan_constraint_cakupan_individu()` mengembalikan `request` APA ADANYA (`terkoreksi=False`), dikonfirmasi `request_final.params` identik `request.params` asli Query Engine untuk ketiga item. Span Jaeger: 3× `verification_gate.check` (`check_name="constraint_cakupan_individu"`) SEMUA `verification.terkoreksi=false`.

**Kesimpulan: mekanisme "tidak ada koreksi kalau constraint tidak terdeteksi" terbukti bekerja nyata, 3x independen dalam satu kejadian** — melengkapi bukti E01/E03 (constraint terdeteksi → koreksi) dengan kontrol negatif (constraint tidak terdeteksi → tidak ada koreksi), constraint yang dicek tetap genuinely berasal dari Domain Gate run ini (bukan sekadar tidak pernah dipanggil).

### E03 — Bukti kedua independen, domain `facility` (LOLOS)

`trace_id=f49d161a5069f34f345f68f84cfe9ab6`. Payload: `role_title="Maintenance Staff"`, "Berapa banyak tiket yang ditangani teknisi Andi bulan ini?" (teks identik `evals/2.3-.../S02`, `session_id` BARU `eval-7.13-e03` — skenario yang belum pernah dieksekusi di Sambungan Level 2 manapun sebelumnya). Decomposition `tunggal`, 1 atomic_intent — PERSIS sesuai prediksi. Domain `facility` diizinkan, `employees_directory` DITOLAK ("role 'Maintenance Staff' tidak memiliki akses ke domain 'employees_directory'") — tapi `cakupan_individu.terdeteksi=True` tetap terjadi (constraint dideteksi dari domain `facility` yang diizinkan, "kebutuhan menyentuh kategori data performa individu staf", identik alasan `evals/2.3-.../S02.json`). Retriever: `view_name_final=v_maintenance_technician_daily`. Query Engine: `request.params={"technician_name": "Andi", "period_date_from": "2026-08-01", "period_date_to": "2026-08-31"}` — TIDAK menyertakan `employee_id`, `lolos=True`.

`verifikasi_gate_semua()`: Cek 3 menimpa paksa `params["employee_id"]="emp-eval"` (`terkoreksi=True`), `request_final.params` menyimpan `technician_name="Andi"` APA ADANYA plus `employee_id` tertimpa — mengonfirmasi koreksi TIDAK menghapus konteks pertanyaan asli, hanya menambahkan identitas caller sebagai filter mengikat. Span Jaeger mengonfirmasi `verification.terkoreksi=true`.

**Kesimpulan: bukti KEDUA independen untuk KK literal M7.13**, di domain berbeda (`facility` vs `hr` E01), role berbeda, DAN `session_id`/skenario yang genuinely baru (bukan reuse Sambungan sebelumnya) — memperkuat generalisasi klaim "koreksi paksa" melampaui satu domain/skenario tunggal yang sudah berulang kali direuse.

## Temuan Metodologi

**Non-determinisme Decomposition/M3.5 (E02)**: komposisi 5 atomic_intent (bukan 3) dan SEMUA 3 item yang mencapai Query Engine `lolos=True` (bukan 1/3 seperti M7.12 E01) — data point tambahan untuk `docs/keterbatasan-diterima.md` #3, konsisten pola M7.9→M7.12. Tidak memengaruhi verdict KK — E02 murni kontrol negatif pelengkap (dicatat eksplisit di `rancangan.md` sebagai bukan sumber utama bukti KK), dan komposisi lebih besar ini justru memberi 3 bukti independen "tidak ada koreksi" sekaligus.

**Fan-in 3 sumber tanpa bug pencocokan**: seluruh 5 item lintas 3 kejadian menunjukkan `constraint`/`view_name_final` yang dipakai `verifikasi_gate()` PERSIS sesuai `atomic_intent_id` masing-masing (tidak ada indikasi tertukar) — konsisten hasil unit test `test_verifikasi_gate_semua_multi_item_tidak_tertukar` (Checkpoint 2) yang sudah membuktikan ini secara mocked; run nyata ini membuktikannya lagi dengan data real-execution.

**Tidak ada insiden hang** — berbeda dari M7.12, eksekusi lancar dalam satu percobaan (~30 menit total untuk 3 kejadian termasuk waktu antar-kejadian menunggu LLM Decomposition majemuk di E02). Regresi penuh 493 test (`tests/orchestration/`, `tests/layers/{verification_gate,query_engine,retriever,domain_gate}/`, dikecualikan test konektivitas real-LLM) juga lolos 100% sebelum eksekusi eval ini dijalankan.
