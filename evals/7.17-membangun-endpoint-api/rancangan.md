# Rancangan Pengujian — Membangun Endpoint API (Milestone 7.17)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Beda mendasar dari SELURUH eval M7.6-7.16: ini adalah **kejadian pertama panggilan HTTP nyata** (bukan pemanggilan `proses_turn()` langsung dari skrip Python) — `httpx` sebagai klien, `uvicorn src.main:app --port 8001` sebagai server sungguhan berjalan terpisah.

**Standar verifikasi KK1 (`decisions.md` Keputusan 7) — WAJIB dibaca sebelum menilai hasil**: "kesamaan hasil" antara panggilan langsung `proses_turn()` dan panggilan lewat HTTP diverifikasi secara STRUKTURAL (status/kategori hasil sama — mis. sama-sama `terverifikasi=True` dengan `narasi` non-kosong, atau sama-sama gap RBAC dengan pesan penolakan), **BUKAN kesamaan teks literal** — dua pemanggilan LLM terpisah (`session_id` beda) TIDAK akan pernah menghasilkan narasi berkata-kata identik, ini bukan tanda kegagalan. Kesetaraan PERSIS (byte-for-byte) sudah dibuktikan terpisah lewat test deterministik (`tests/test_main.py`, Checkpoint 4) dengan `KeadaanTurn` yang sama persis di-mock.

## Yang Diuji

`POST http://127.0.0.1:8001/v1/turns` — endpoint HTTP sungguhan, `chatbot_api` (port 8000) DAN Jaeger HARUS `up` selama eksekusi (dipanggil `proses_turn()` internal).

**Invarian yang wajib benar di SEMUA kejadian:**

1. Response HTTP genuinely diterima (bukan timeout/connection error) dengan status code sesuai ekspektasi kejadian.
2. Body response valid JSON, cocok skema `TurnResponse` (`session_id`, `turn_index`, `narasi`, `terverifikasi`, `catatan_verifikasi`, `visualisasi`).
3. `narasi` WAJIB non-kosong string apa pun statusnya (kejujuran — tidak pernah field kosong tanpa penjelasan).

## Kejadian

### E01 — Kebutuhan tunggal sederhana, KK1 (payload valid via HTTP nyata)

**Payload:** identik `evals/7.16-verifikasi-alur-penuh-end-to-end/payloads/E01.json` raw_payload (General Manager, "Berapa occupancy rate properti kita bulan Juni 2026?"), `session_id` BARU.

**Prosedur:** (a) panggil `proses_turn()` LANGSUNG (Python, tanpa HTTP) dengan `session_id="eval-7.17-e01-direct"` — catat status (`terverifikasi`, ada/tidaknya `narasi`, status `execution`). (b) panggil endpoint HTTP dengan `session_id="eval-7.17-e01-http"` (payload lain SAMA) — catat response HTTP penuh.

**Ekspektasi (mengacu M7.16 E01 — 1 atomic intent, execution mencapai `chatbot_api` nyata, hasil `gagal_teknis`/`sebagian`/`berhasil` apa pun yang genuinely terjadi):**
- Response HTTP 200 (pipeline SELESAI, terlepas status internal per-intent — sesuai `decisions.md` M7.16 Keputusan 2, filosofi yang sama berlaku di sini: sukses = pipeline selesai, bukan hasil data harus sempurna).
- KESETARAAN STRUKTURAL antara (a) dan (b): kalau (a) `hasil.interpretation[1].lolos=True` maka (b) `terverifikasi=True` DAN `narasi` non-kosong DAN `visualisasi` konsisten ada/tidaknya; kalau (a) `lolos=False`/`None` maka (b) `terverifikasi=False` DAN `narasi == _PESAN_NARASI_BELUM_TERVERIFIKASI` (pesan generik, BUKAN teks asli) DAN `catatan_verifikasi` terisi.
- Body response TIDAK memuat traceback/nama exception Python apa pun (sanity check keamanan, seharusnya tidak relevan untuk kasus sukses tapi tetap dicek).

---

### E02 — Penolakan otorisasi Domain Gate, KK2 (reuse skenario `gop_margin`)

**Payload:** identik `evals/7.16-.../E02.json` raw_payload (Front Office Staff, gop_margin — domain `financial` DITOLAK otorisasi, replikasi M7.9-7.16), `session_id` BARU via HTTP saja (tidak perlu panggilan langsung terpisah — fokus KK2 murni soal isi narasi via HTTP).

**Ekspektasi (mengacu M7.9-7.16 — minimal 1 dari beberapa atomic intent domain `financial` ditolak, tersaring jadi gap sintetis `DITOLAK_OTORISASI` via mekanisme M7.15):**
- Response HTTP 200 (BUKAN 403 — penolakan otorisasi adalah bagian dari hasil turn yang SELESAI diproses, bukan kegagalan HTTP-level, sesuai `decisions.md` M7.15 Keputusan 2 + prinsip narasi generik untuk SEMUA `StatusEksekusi`).
- `narasi` (via jalur `terverifikasi` apa pun statusnya — TIDAK terkait suppression Keputusan 1, karena gap RBAC punya narasi TERSENDIRI dari M7.15, bukan hasil verifikasi kesetiaan M4.5 yang gagal) WAJIB menyampaikan penolakan otorisasi secara jujur — dicek mengandung kata kunci semacam "akses"/"tidak memiliki"/"otorisasi", BUKAN istilah internal (`DITOLAK_OTORISASI`, nama enum Python) BOCOR ke teks.
- Kalau verifikasi kesetiaan (M4.5) untuk narasi CAMPURAN (sebagian gap RBAC + sebagian hasil eksekusi/gap teknis lain) kebetulan `lolos=False`/`None` (jarang, tapi mungkin) — dicatat transparan bahwa Keputusan 1 (suppression) akan mengaburkan pesan RBAC juga dalam kasus itu, BUKAN dianggap kegagalan E02 (interaksi 2 desain yang sudah didokumentasikan, bukan bug).

## Catatan Non-Determinisme

Sama seperti M7.9-7.16: hasil aktual (jumlah atomic intent, status execution per item, apakah `terverifikasi=True/False`) TIDAK dijamin identik run-ke-run meski payload sama persis. Verifikasi KK1/KK2 dibandingkan terhadap hasil RUN M7.17 itu sendiri (dan struktur, bukan teks) — kalau salah satu kejadian menyimpang jauh dari ekspektasi (mis. E02 kebetulan tidak menghasilkan gap RBAC sama sekali kali ini), dicatat transparan di `audit.md`, dipertimbangkan menjalankan kejadian tambahan sebelum audit ditulis.

## Ringkasan Ekspektasi

| ID | Fokus KK | `role_title` | Status code diharapkan |
|---|---|---|---|
| E01 | KK1 — kesetaraan struktural HTTP vs langsung | General Manager | 200 |
| E02 | KK2 — penolakan otorisasi disampaikan jujur | Front Office Staff | 200 (bukan 403) |
