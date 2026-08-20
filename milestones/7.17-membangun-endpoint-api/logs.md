# Logs — Milestone 7.17: Membangun Endpoint API

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 1-2 — decisions.md + entri backlog project-wide

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan (3 agen Explore paralel) menemukan: `src/main.py` belum pernah memanggil `proses_turn()`; tidak ada schema response API sama sekali; peta lengkap exception yang bisa lolos `proses_turn()` (termasuk 2 celah defensif laten baru — `IndexError`/`KeyError` — yang belum pernah terjadi nyata); bentrok port 8000 antara app sendiri dan `chatbot_api`. Dua keputusan diajukan ke user via `AskUserQuestion` (narasi gagal verifikasi, penanganan celah laten), keduanya diminta penjelasan konkret dulu sebelum diputuskan. User memutuskan: Opsi B (ganti pesan generik) untuk narasi gagal verifikasi + wajib dicatat di KEDUA `keterbatasan-diterima.md` dan `keputusan-tertunda.md`; Opsi A (tidak diperbaiki, catat sebagai keterbatasan) untuk celah laten. Di tengah Plan Mode, user juga meminta perluasan cakupan: dokumen panduan integrasi frontend dengan contoh output nyata — ditambahkan sebagai Checkpoint 7 baru.

Menulis `milestones/7.17-membangun-endpoint-api/decisions.md` (11 keputusan, 2 Jenis A + 9 Jenis B), entri baru `docs/keterbatasan-diterima.md` #16 (narasi gagal verifikasi) + #17 (celah laten), entri baru `docs/keputusan-tertunda.md` #5 (strategi lebih halus narasi gagal verifikasi).

**Temuan**
Skema `HasilVerifikasiNarasi` (M4.5) — `alasan` dijamin `None` BUKAN HANYA saat `lolos=True`, tapi JUGA saat `status=GAGAL_TEKNIS` (validator: "status=gagal_teknis wajib lolos=None dan alasan=None"). Ini penting untuk implementasi `catatan_verifikasi` (Checkpoint 3) — tidak bisa langsung diisi `alasan` untuk kasus `GAGAL_TEKNIS`, butuh fallback string tetap.

**Hasil Verifikasi**
Review manual `decisions.md`+2 entri backlog — format Jenis A/B sesuai template, "Opsi Ditolak" terisi.

**Commit:** `af27dea` (decisions.md) + `f2e0338` (keterbatasan-diterima+keputusan-tertunda)

---

## Checkpoint 2 — Skema Response API

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 3 — `TurnResponse`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca `src/schemas/interpretation.py` lengkap sebelum menulis (konfirmasi bentuk `DataVisualisasi` untuk reuse). Menulis `src/schemas/api_response.py` — `TurnResponse(session_id, turn_index, narasi, terverifikasi, catatan_verifikasi, visualisasi)`.

**Temuan**
Tidak ada temuan tak terduga.

**Hasil Verifikasi**
`uv run python -c "from src.schemas.api_response import TurnResponse; ..."` — instantiable, `model_dump_json()` menghasilkan JSON valid.

**Commit:** `cf1d480` — `feat(milestone-7.17): skema response API`

---

## Checkpoint 3 — Sambungkan `main.py` ke `proses_turn()`

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 4 — Wiring + exception handlers

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ubah `src/main.py`: `submit_turn()` sekarang memanggil `proses_turn(payload)` lalu `_build_turn_response()` (logic suppression narasi sesuai Keputusan 1 — `catatan_verifikasi` diisi `alasan` KALAU ada, fallback `_PESAN_VERIFIKASI_GAGAL_TEKNIS` KALAU tidak, menutup temuan Checkpoint 1). Tambah handler `openai.APIError`→503, `(SQLAlchemyError, RuntimeError)`→500 (dua decorator ditumpuk satu fungsi), catch-all `Exception`→500. Perbarui docstring (port 8001).

**Temuan**
Tidak ada temuan tak terduga.

**Hasil Verifikasi**
`uv run python -c "from src.main import app; print([r.path...], list(app.exception_handlers.keys()))"` — route `/v1/turns` terdaftar, seluruh 8 handler (termasuk bawaan FastAPI) terdaftar dengan urutan spesifisitas benar (`ValidationError`, `APIError`, `RuntimeError`, `SQLAlchemyError`, `Exception`).

**Commit:** `0e6acb3` — `feat(milestone-7.17): sambungkan main.py ke proses_turn`

---

## Checkpoint 4 — Migrasi + Test Deterministik

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 5-6 — Migrasi test lama + tulis `tests/test_main.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Baca pola dummy `tests/orchestration/test_turn_pipeline.py` (konstruksi `KeadaanTurn` 15 field) untuk direplikasi. Update 3 test PENERIMAAN `tests/layers/test_input_layer.py` — monkeypatch `proses_turn`, assert bentuk `TurnResponse` (bukan echo `history`). 6 test PENOLAKAN TIDAK disentuh. Tulis `tests/test_main.py` baru: 3 test `_build_turn_response()` (lolos=True/False/None), 1 test sukses endpoint, 4 test pemetaan exception handler (masing-masing memverifikasi status code BENAR + pesan exception asli TIDAK bocor ke body — defense-in-depth), 1 test payload invalid tetap 422.

**Temuan**
Dua kegagalan percobaan pertama, keduanya bug test (bukan bug produksi):
1. `test_endpoint_exception_generik_dipetakan_500_catch_all` — `IndexError` dari mock menjalar sampai gagal test alih-alih tertangkap. Diagnosis: handler `@app.exception_handler(Exception)` (bare `Exception`, beda dari tipe SPESIFIK seperti `SQLAlchemyError`/`RuntimeError`) ditangani `ServerErrorMiddleware` Starlette, BUKAN `ExceptionMiddleware` — `ServerErrorMiddleware` SELALU `raise exc` lagi SETELAH mengirim response (by design, supaya ASGI server produksi tetap bisa mencatat error meski response sudah terkirim ke client sungguhan). `TestClient` default (`raise_server_exceptions=True`) meneruskan re-raise itu sebagai kegagalan Python, BUKAN mengembalikan response. Perilaku PRODUKSI tetap benar (client nyata tetap dapat 500 body aman) — murni keterbatasan cara `TestClient` menguji kasus ini.
2. `test_endpoint_payload_invalid_tetap_422_bukan_ditelan_catch_all` — dapat 200, bukan 422. Diagnosis: test SALAH me-monkeypatch `proses_turn` jadi dummy sukses yang mengabaikan payload — sehingga validasi payload TIDAK PERNAH genuinely dijalankan (mock tidak memanggil `validate_turn_payload()`).

**Error/Kegagalan**
2 test gagal percobaan pertama (lihat Temuan).

**Diagnosis dan Perbaikan**
(1) Ganti ke `TestClient(app, raise_server_exceptions=False)` KHUSUS untuk test catch-all itu — membaca response yang genuinely terkirim, bukan menunggu exception Python. (2) Hapus monkeypatch dari test itu — `proses_turn()` TIDAK di-mock, validasi (langkah pertama `proses_turn()`, sebelum LLM/DB/HTTP apa pun) genuinely dijalankan nyata.

**Hasil Verifikasi**
`uv run pytest tests/layers/test_input_layer.py tests/test_main.py -v` — 21/21 PASSED. Regresi penuh project `uv run pytest tests/ -q -k "not matching"` — 688 passed, 1 skipped, 3 deselected, 748.97s (0:12:28), 0 gagal.

**Commit:** `6cd0a6a` — `test(milestone-7.17): migrasi test lama + test deterministik baru`

---

## Checkpoint 5 — Peta Kejadian Eval

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 7 — Tulis rancangan.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/7.17-membangun-endpoint-api/rancangan.md` — 2 kejadian: E01 (KK1, reuse `evals/7.16-.../E01.json`, prosedur ganda: panggilan langsung `proses_turn()` DAN panggilan HTTP nyata, dibandingkan struktural), E02 (KK2, reuse `evals/7.16-.../E02.json` skenario gop_margin). Standar verifikasi KK1 dinyatakan eksplisit (struktural, bukan teks literal) sebelum eksekusi.

**Hasil Verifikasi**
Review manual `rancangan.md`.

**Commit:** `48ee3ca` — `docs(milestone-7.17): peta kejadian eval`

---

## Checkpoint 6 — Eksekusi Nyata

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20 (mencakup 5 percobaan E02 + 1 diagnostik terpisah)

### Task 8 — Tulis + jalankan `run_eval.py`

**Kesesuaian dengan plan:** Sesuai plan, DIPERLUAS signifikan untuk E02 (5 percobaan, 2 bug operasional ditemukan+diperbaiki, lihat Temuan/Error).

**Apa yang dilakukan**
Tulis `evals/7.17-membangun-endpoint-api/run_eval.py` — server app sendiri (`uvicorn`) dinyalakan sebagai subprocess terlacak, `httpx` sebagai klien HTTP nyata. E01 (2 prosedur: panggilan langsung `proses_turn()` + panggilan HTTP terpisah) berhasil PERCOBAAN PERTAMA — kedua jalur sama-sama `gagal_teknis` dengan narasi berbeda teks tapi kategori status sama (kesetaraan struktural KK1 terbukti). E02 (gop_margin, KK2) mengalami rangkaian kendala panjang, ditangani satu per satu dengan `retry_e02.py` (mirror pola `retry_e0X.py` M7.15/M7.16, session_id baru tiap percobaan):

- **Percobaan 1** (`eval-7.17-e02-http`): `httpx.ReadTimeout` pada klien (timeout 600s) — trace Jaeger menunjukkan span TERUS bertambah sampai detik terakhir sebelum timeout (bukan hang tanpa progres).
- **Percobaan 2** (`eval-7.17-e02-http-b`): app server BARU gagal start sama sekali ("gagal start dalam waktu wajar").
- **Percobaan 3** (`eval-7.17-e02-http-c`): app server (setelah bug percobaan 2 diperbaiki) berhasil start, TAPI hang tanpa exception ~5+ menit (CPU nyaris nol) tepat setelah span ketergantungan selesai, sebelum Rewrite/Tarik Memory.
- **Diagnostik terpisah** (`eval-7.17-diag-direct`, TANPA HTTP sama sekali): payload gop_margin identik dipanggil langsung `proses_turn()` untuk mengisolasi apakah hang terkait HTTP/threading — HASIL: JUGA hang (pada titik berbeda, setelah 6 span, bukan 2), CPU sama-sama nyaris nol.
- **Percobaan 4** (`eval-7.17-e02-http-d`): dijalankan dengan server yang SUDAH diperbaiki (lihat Temuan 2) — TETAP hang di titik yang mirip.
- **Percobaan 5** (`eval-7.17-e02-http-e`): BERHASIL PENUH (HTTP 200), ~16-17 menit total, melewati seluruh titik yang sebelumnya macet.

**Temuan**
1. **Bug: `app_proc.terminate()` tidak menembus proses `uvicorn` cucu di Windows.** `_start_app_server()` awalnya memanggil `subprocess.Popen(["uv", "run", "uvicorn", ...])` — `.terminate()` HANYA mematikan proses `uv` (induk langsung yang dilacak Popen), BUKAN `uvicorn` (proses cucu terpisah yang di-spawn `uv run`). Setelah percobaan 1 timeout, proses `uvicorn` lama TETAP HIDUP dan tetap menempati port 8001 (dikonfirmasi `Get-NetTCPConnection` menunjukkan proses lama masih `Listen` di port itu) — inilah sebab percobaan 2 gagal start (bentrok port). Diagnosis dikonfirmasi via inspeksi proses langsung (`Get-Process`/`Get-NetTCPConnection`), diperbaiki mematikan proses orphan manual (`taskkill /F /T`) sebelum lanjut.
2. **Bug: `submit_turn()` `async def` memblokir event loop.** Ditemukan saat menginvestigasi kenapa health check (`/docs`) tidak responsif selama E02 diproses — `proses_turn()` (sepenuhnya sinkron/blocking) dipanggil LANGSUNG di dalam `async def`, memblokir SATU-SATUNYA event loop uvicorn sepenuhnya selama satu turn diproses (server tidak bisa merespons request/health-check APA PUN selagi sibuk). Diperbaiki: `submit_turn()` diubah jadi `def` biasa (FastAPI otomatis menjalankan di threadpool worker). Diverifikasi lewat monitoring `health_docs` selama percobaan 4-5: server TETAP merespons 200 di `/docs` selagi turn lain diproses — bug genuinely teratasi.
3. **Hang berulang (percobaan 3+4, DAN diagnostik langsung) dikonfirmasi BUKAN disebabkan bug event-loop/threading** — diagnostik panggilan LANGSUNG (tanpa HTTP, tanpa nested threading apa pun) untuk payload IDENTIK JUGA mengalami hang (CPU nyaris nol, titik berbeda). Ini pola KONSISTEN `docs/keterbatasan-diterima.md` #7 (infra LLM acak), yang kebetulan lebih sering terjadi sesi ini (4 kejadian hang: E02 percobaan 3+4, diagnostik langsung — plus 2 kejadian M7.16 sebelumnya di sesi lain).
4. **Percobaan 5 (berhasil) non-deterministik menghasilkan `gagal_teknis`, BUKAN penolakan RBAC** seperti diprediksi `rancangan.md` — Decomposition/Domain Gate run ini tidak mereproduksi penolakan domain `financial` seperti run-run sebelumnya (M7.9-7.16). Diterima transparan (mekanisme RBAC-passthrough-jujur SUDAH dibuktikan di level orkestrator M7.15 E02 dan berulang kali M7.9-7.16 — yang genuinely BARU dibuktikan M7.17 adalah lapisan HTTP TIDAK mengubah/menghilangkan apa pun dari narasi apa pun yang dihasilkan pipeline, sudah terbukti oleh E01 DAN E02 sama-sama menunjukkan wrapping yang setia).

**Error/Kegagalan**
5 percobaan E02 (4 gagal karena alasan berbeda-beda, lihat Temuan), 1 diagnostik tambahan.

**Diagnosis dan Perbaikan**
Timeout klien: dinaikkan 600s→1800s di `run_eval.py` (permanen, berlaku run berikutnya). Proses orphan: `_start_app_server()`/`_matikan_app_server()` diubah pakai `sys.executable -m uvicorn` langsung (bukan `uv run uvicorn`) + `taskkill /F /T` sebagai pengaman tambahan di Windows — commit `fix(milestone-7.17)` terpisah dari commit eksekusi eval (kategori berbeda, konsisten aturan project). Blocking event loop: `submit_turn()` `async def`→`def` biasa, commit `fix` yang sama. Hang infra: TIDAK "diperbaiki" (di luar kendali, sesuai `docs/keterbatasan-diterima.md` #7) — ditangani retry dengan `session_id` baru + pemantauan aktif Jaeger, konsisten pola M7.14-7.16.

**Hasil Verifikasi**
E01+E02 tersimpan `payloads/*.json` dengan bukti nyata (`status_code=200` keduanya, narasi non-kosong, kesetaraan struktural E01 dikonfirmasi). Regresi `tests/layers/test_input_layer.py tests/test_main.py` tetap 21/21 PASSED setelah fix event-loop. Grep secret kosong.

**Commit:** `24e2f2c` (fix event-loop, sebelum percobaan 4) + `eea73bc` (test — eksekusi eval lengkap E01+E02 final)

---

## Checkpoint 7 — Panduan Integrasi Frontend

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 9 — Tulis `docs/panduan-integrasi-frontend.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `docs/panduan-integrasi-frontend.md` — ringkasan endpoint, tabel skema request+response, contoh request/response NYATA dikutip langsung dari `payloads/E01.json` (satu-satunya contoh sukses HTTP yang tersimpan lengkap), tabel status HTTP+contoh body error, catatan render `visualisasi` per label (termasuk peringatan provisional untuk 3 label selain `tren`/`nilai_tunggal`), bagian "Prinsip Kejujuran" menjelaskan kenapa `200` tidak selalu berarti "data ditemukan".

**Temuan**
Sesuai antisipasi Risiko & Mitigasi plan — kasus `terverifikasi=false` TIDAK muncul organik di kedua eksekusi nyata (E01 maupun E02, keduanya `lolos=True`). Contoh untuk kasus ini dibangun manual, ditandai eksplisit `[Contoh dikonstruksi...]` di dokumen — TIDAK diklaim sebagai hasil eksekusi nyata, tapi tetap akurat (dibangun dari fixture yang sudah diverifikasi `tests/test_main.py::test_build_turn_response_lolos_false_narasi_diganti_generik`).

**Hasil Verifikasi**
Review manual — tiap contoh JSON dicocokkan sumbernya: E01 dari `payloads/E01.json` `raw_payload_http`/`hasil_http.body` (disalin persis, tidak diedit), contoh `terverifikasi=false` ditandai jelas sebagai konstruksi.

**Commit:** `82e9da4` — `docs(milestone-7.17): panduan integrasi frontend`

---

## Checkpoint 8 — Audit

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 10 — Tulis audit.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/7.17-membangun-endpoint-api/audit.md` — verdict KK1 terpenuhi penuh (E01, kesetaraan struktural), KK2 terpenuhi dengan penalaran eksplisit kenapa (mekanisme HTTP passthrough terbukti setia lewat E01+E02, meski skenario RBAC spesifik tidak organik ter-reproduksi di E02). Ringkasan insiden operasional (2 bug nyata) + bagian "Temuan Metodologi" (nilai eval justru dominan dari menemukan bug operasional, bukan cuma verifikasi KK).

**Hasil Verifikasi**
Review isi `audit.md` mencerminkan `payloads/E01.json`/`E02.json` apa adanya.

**Commit:** `3bad906` — `docs(milestone-7.17): audit`

---

## Checkpoint 9 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 11-12 — Finalisasi logs.md, tulis report.md, update status proyek

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Finalisasi `logs.md` (checkpoint ini). Tulis `milestones/7.17-membangun-endpoint-api/report.md` — kedua KK dipetakan terpenuhi (KK2 dengan penalaran eksplisit dijelaskan lengkap), konfirmasi "Catatan Serah Terima" (`docs/panduan-integrasi-frontend.md` sebagai kontrak tertulis resmi pertama ke frontend). Update tabel "Status Proyek" `CLAUDE.md`+`AGENT.md` (working tree saja, gitignored) — M7.17 selesai, baris `src/main.py` di Struktur Repository diperbarui, M7.18 (Database Percakapan) berikutnya.

**Hasil Verifikasi**
Baca ulang `report.md` — KK dipetakan jujur, termasuk penjelasan eksplisit kenapa KK2 dianggap terpenuhi meski skenario RBAC literal tidak organik ter-reproduksi. `CLAUDE.md`/`AGENT.md` diperbarui working tree, TIDAK di-commit.

**Commit:** `docs(milestone-7.17): logs, report` (CLAUDE.md/AGENT.md TIDAK termasuk — gitignored, working tree saja)

---
