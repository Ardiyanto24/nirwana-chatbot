# Logs — Milestone 4.2: Klasifikasi Respons dan Penanganan Kegagalan

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint. Real testing ke `chatbot_api` sungguhan DITUNDA (Keputusan 4) — Checkpoint 1-6 diverifikasi lewat simulasi/mock, konsisten kata Kriteria Keberhasilan sumber sendiri.

---

## Checkpoint 1 — Keputusan dan Dokumentasi Pendukung

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/4.2-klasifikasi-respons-dan-penanganan-kegagalan/decisions.md` berisi 10 keputusan (4 Jenis A genuinely-terbuka, hasil diskusi mendalam dengan user sebelum plan ditulis; 6 Jenis B forced/preseden), mengikuti template resmi.

**Temuan**
Riset mendalam soal "berhasil vs sebagian" (Keputusan 1) mengungkap bahwa `StatusEksekusi.SEBAGIAN` punya makna konsisten di seluruh codebase (proses 2+ langkah, satu gagal teknis) yang tidak pernah eksplisit didokumentasikan sebagai "aturan umum" di satu tempat — hanya tersirat berulang di docstring tiap skema. Ini yang jadi dasar argumen kuat untuk keputusan "selalu berhasil" di M4.2.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
Review manual — 10 entri decisions.md mencakup seluruh keputusan yang muncul sepanjang diskusi plan (berhasil/sebagian, cakupan 400 Opsi B, real testing ditunda, refactor span, batas retry/revisi, skema, M3.5/M2.4 tak berubah, addendum keputusan-tertunda, workflow Task 1).

**Commit:** *(pending — digabung dengan Task 2-3, lihat bawah)*

---

### Task 2 — Addendum docs/keputusan-tertunda.md #3

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan addendum di entri #3 `docs/keputusan-tertunda.md` — draf usulan kontrak `last_refreshed_at`/`data_quality_status` per view/domain ke tim database engineering (dua field, dua opsi bentuk implementasi, pemicu peninjauan ulang eksplisit).

**Temuan**
Tidak ada temuan baru — draf sudah disiapkan penuh saat diskusi plan (sesi percakapan sebelum implementasi dimulai).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — addendum konsisten dengan draf pesan yang disiapkan di percakapan, ditambahkan sebagai perluasan entri #3 (bukan entri baru), sesuai Keputusan 9.

**Commit:** *(pending — digabung dengan Task 1, 3)*

---

### Task 3 — Cross-reference di milestones/3.4-penyusunan-request/report.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan catatan pasca-milestone di Bagian 6 (Follow-up) `report.md` M3.4 — kontrak `susun_request_atomic_intent()` akan diperluas M4.2 dengan parameter `feedback` opsional, cross-reference ke `decisions.md` M4.2 Keputusan 3.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — catatan ditambahkan tanpa mengubah isi historis report.md yang sudah ada (append, bukan rewrite), konsisten prinsip "jangan menghapus/menyembunyikan sejarah" `CLAUDE.md`.

**Commit:** *(pending)*

---

## Checkpoint 2 — Refactor M4.1: Pisahkan Logic Murni dari Span

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — Ekstrak `_panggil_chatbot_api_raw()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/layers/execution/pemanggilan_chatbot_api.py` direfactor: logic HTTP+parsing murni dipindah ke `_panggil_chatbot_api_raw()` (tanpa span). `panggil_chatbot_api()` publik jadi wrapper tipis yang membuka span `execute_tool`, mendelegasikan ke `_panggil_chatbot_api_raw()`, lalu men-set `http.response.status_code` HANYA kalau `status_code is not None` (kegagalan transport tidak punya status_code untuk dicatat) - perilaku ini identik logic lama.

**Temuan**
Test suite awalnya gagal collect via `python` sistem (`ModuleNotFoundError: opentelemetry.exporter.otlp.proto.grpc`) - ternyata bukan bug refactor, melainkan environment: project punya `.venv` sendiri yang harus dipakai eksplisit (`./.venv/Scripts/python.exe`), bukan `python`/`pip` global.

**Error/Kegagalan (jika ada)**
`ModuleNotFoundError` di atas - murni kesalahan environment (python sistem, bukan `.venv` project), bukan error dari kode yang direfactor.

**Diagnosis dan Perbaikan (jika ada error)**
Diperbaiki dengan menjalankan test lewat `.venv` project (`./.venv/Scripts/python.exe -m pytest`), bukan `python` sistem. Tidak ada perubahan kode untuk mengatasi ini.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/execution/test_pemanggilan_chatbot_api.py -v` — **11/11 test lolos TANPA perubahan assertion** (regresi murni terhadap test yang sudah ada sejak M4.1), termasuk `test_span_execute_tool_mencatat_status_code` yang memverifikasi atribut span tidak berubah.

**Commit:** *(pending — digabung dengan Task 5)*

### Task 5 — Konstanta Retry/Revisi

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan `EXECUTION_MAX_RETRY_INFRA = 2`, `EXECUTION_RETRY_DELAY_DETIK = 1.0`, `EXECUTION_MAX_REVISI = 3` ke `src/config/chatbot_api.py`, dengan docstring merujuk `decisions.md` Keputusan 6.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — nilai konsisten dengan Keputusan 6 (mirror `_MAX_ATTEMPTS=3` M1.6).

**Commit:** *(pending)*

---

## Checkpoint 3 — Perluas Kontrak M3.4: Parameter Feedback Revisi

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6 — Tambah Parameter `feedback`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian teknis kecil (dicatat di bawah).

**Apa yang dilakukan**
`_build_user_prompt()`, `_call_llm()`, dan `susun_request_atomic_intent()` (`src/layers/query_engine/penyusunan_request.py`) ditambah parameter `feedback: str | None = None`. Kalau terisi, blok "PERHATIAN: percobaan penyusunan parameter sebelumnya DITOLAK chatbot_api..." disisipkan ke user prompt, mirror persis pola `_build_user_prompt()` di `pecah_atomik.py` (M1.6).

**Temuan**
`_call_llm()` sekarang dipanggil dengan 4 argumen positional (termasuk `feedback`) dari `susun_request_atomic_intent()`, bukan 3 seperti sebelumnya. Ini berarti SELURUH mock `_call_llm` di `tests/layers/query_engine/test_penyusunan_request.py` yang sebelumnya bersignature `(ai, vn, tr)` (5 lokasi: 3 lambda, 2 fungsi `def`) perlu ditambah parameter `fb=None` supaya tetap bisa dipanggil - kalau tidak, seluruh test lama akan gagal dengan `TypeError: takes 3 positional arguments but 4 were given`. Ini PENYESUAIAN MEKANIS pada signature mock (supaya callable), BUKAN perubahan assertion/logic test - tetap konsisten dengan Acceptance Criteria plan ("tanpa perubahan assertion").

**Error/Kegagalan (jika ada)**
Tidak ada error nyata terjadi - penyesuaian mock dilakukan proaktif SEBELUM menjalankan test (diantisipasi dari membaca kode test terlebih dulu), bukan ditemukan lewat kegagalan test.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku (tidak ada error, murni penyesuaian proaktif).

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/query_engine/test_penyusunan_request.py -v` — **20/20 lolos** (16 test lama, assertion tidak berubah + 4 test baru: 2 untuk `_build_user_prompt` dengan/tanpa feedback, 2 untuk `susun_request_atomic_intent` meneruskan feedback ke `_call_llm` dengan benar).

**Commit:** *(pending)*

### Task 7 — Bump Prompt ke Versi 3

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`src/prompts/query_engine/penyusunan_request.md` — frontmatter `version: 2` → `3`, deskripsi diperbarui menyebut revisi berbasis feedback, tambah section "Aturan revisi" (baca alasan penolakan, perbaiki hanya parameter relevan, jangan mengulang parameter yang sudah ditolak).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual isi prompt + span `PROMPT_VERSION` di `susun_request_atomic_intent()` otomatis membaca versi terbaru dari `load_prompt()` (tidak perlu perubahan kode terpisah untuk propagasi versi).

**Commit:** *(pending)*

---

## Checkpoint 4 — Skema Hasil Eksekusi

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 8 — Skema `HasilEksekusiAtomicIntent`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian lokasi file test (dicatat di bawah).

**Apa yang dilakukan**
Menambah `HasilEksekusiAtomicIntent` ke `src/schemas/execution.py`: `status: StatusEksekusi` (invarian: hanya BERHASIL/GAGAL_TEKNIS), `nilai_hasil: Any = None`, `bug_prioritas_tinggi: bool = False`, `retry_count_infra: int = 0`, `revisi_count: int = 0`, `kegagalan_alasan: str | None = None`, dengan `model_validator` menegakkan invarian silang (GAGAL_TEKNIS wajib `kegagalan_alasan` + `nilai_hasil=None`; BERHASIL tidak boleh `kegagalan_alasan`/`bug_prioritas_tinggi=True`; status lain di luar keduanya ditolak).

**Temuan**
Plan menyebut lokasi test `tests/schemas/test_execution_schema.py`, tapi dicek dulu konvensi nyata project: skema `Hasil<X>` lain (`retriever.py`/`query_engine.py`) test-nya di `tests/layers/<layer>/test_<modul>_schema.py`, BUKAN direktori `tests/schemas/` terpisah (direktori itu bahkan tidak ada di project). Disesuaikan ke `tests/layers/execution/test_execution_schema.py`, mirror persis preseden `test_query_engine_schema.py`.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/execution/test_execution_schema.py -v` — **11/11 lolos**: konstruksi valid BERHASIL (dengan `nilai_hasil` terisi maupun list kosong `[]` - membuktikan 0-legitimate tetap sah), konstruksi valid GAGAL_TEKNIS, dan 4 kasus pelanggaran invarian (BERHASIL+kegagalan_alasan, BERHASIL+bug_prioritas_tinggi=True, GAGAL_TEKNIS tanpa kegagalan_alasan, GAGAL_TEKNIS+nilai_hasil terisi) + 3 kasus status terlarang (SEBAGIAN/DITOLAK_OTORISASI/TERBLOKIR_KETERGANTUNGAN) semuanya memicu `ValidationError` sesuai ekspektasi.

**Commit:** *(pending)*

---

## Checkpoint 5 — Klasifikasi Inti: Retry Infrastruktural + Eskalasi 403/404 + Berhasil 200

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 9 — `klasifikasi_respons.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `src/layers/execution/klasifikasi_respons.py`: `_kegagalan_infra()` (helper klasifikasi retryable: `kegagalan_transport` ATAU `status_code>=500`), `_panggil_dengan_retry_infra()` (loop retry maks `EXECUTION_MAX_RETRY_INFRA`, delay `EXECUTION_RETRY_DELAY_DETIK` via `time.sleep`), dan `eksekusi_atomic_intent()` (orkestrator, membungkus SATU span `execute_tool`) yang menangani jalur 200 (berhasil), 403/404 (eskalasi, `bug_prioritas_tinggi=True`, TANPA retry), retry-infra-exhausted (gagal_teknis), dan placeholder 400 (gagal_teknis sementara, disempurnakan Checkpoint 6). Signature menerima `view_name`/`constraint` sekalipun belum dipakai di checkpoint ini - disiapkan sekaligus untuk Checkpoint 6 (dijelaskan eksplisit di docstring fungsi kenapa ini bukan speculative/premature).

**Temuan**
Tidak ada temuan tak terduga - implementasi berjalan sesuai desain yang sudah dipetakan detail di plan (termasuk hitungan retry_count yang presisi: `percobaan` di `_panggil_dengan_retry_infra()` merepresentasikan JUMLAH RETRY, bukan jumlah total panggilan, mirror pola `retry_count=attempt-1` di `decompose.py`).

**Error/Kegagalan (jika ada)**
Tidak ada - seluruh 8 test lolos di percobaan pertama.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/execution/test_klasifikasi_respons.py -v` — **8/8 lolos**: 200 langsung berhasil (`_panggil_chatbot_api_raw` dipanggil 1x); 200 body kosong `[]` tetap berhasil (bukti KK Keputusan 1); 403 DAN 404 eskalasi tanpa retry (`bug_prioritas_tinggi=True`, dipanggil TEPAT 1x, span `error.type=gagal_teknis`+`execution.bug_prioritas_tinggi=True`); 500 berturut habis batas -> gagal_teknis, dipanggil TEPAT 3x (`EXECUTION_MAX_RETRY_INFRA`+1); timeout berturut habis batas -> gagal_teknis serupa; 500 lalu sukses di percobaan ke-2 -> berhasil, `retry_count_infra=1`, span `execution.retry_count_infra=1` DAN `http.response.status_code=200` (bukti status code yang tercatat adalah dari percobaan TERAKHIR, bukan pertama); 400 placeholder -> gagal_teknis (`belum_diimplementasi`), dipanggil TEPAT 1x (bukti 400 tidak ikut retry infra). Span attributes diverifikasi via fake tracer in-process (`_SpanRekam`/`_TracerRekam`, mirror pola M4.1) - TIDAK butuh Jaeger/Docker.

**Commit:** *(pending)*

---

## Checkpoint 6 — Integrasi Jalur Revisi 400

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 10 — `_revisi_request()` dan Integrasi Loop 400

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`klasifikasi_respons.py` dilengkapi: `_ekstrak_alasan_400()` (ambil teks alasan dari body 400 - `body["detail"]` kalau dict berisi key itu, else `str(body)`), `_revisi_request()` (orkestrasi `susun_request_atomic_intent(feedback=...)` M3.4 -> `verifikasi_bentuk_request_atomic_intent()` M3.5 -> `verifikasi_gate()` M2.4, APA ADANYA tanpa modifikasi kedua fungsi terakhir, mengembalikan `(request_final, None)` atau `(None, alasan_spesifik)`). `eksekusi_atomic_intent()` direstrukturisasi jadi `while True` loop: 400 memicu `_revisi_request()` (kalau jatah revisi tersisa) lalu lanjut ke `_panggil_dengan_retry_infra()` lagi dengan request baru; batas `EXECUTION_MAX_REVISI` dihormati; `execution.revisi_count`/`execution.retry_count_infra` (kumulatif lintas seluruh percobaan revisi) dicatat di span SATU kali per iterasi loop.

**Temuan**
Tidak ada temuan tak terduga secara teknis. Test lama `test_klasifikasi_respons.py` (Checkpoint 5) sempat punya test placeholder 400 (`test_400_placeholder_gagal_teknis_belum_diimplementasi`) yang perilakunya SEKARANG BERUBAH (400 tidak lagi langsung gagal_teknis, tapi memicu revisi) - test itu DIHAPUS (bukan diubah assertion-nya) karena skenarionya sudah sepenuhnya digantikan test file baru `test_klasifikasi_respons_revisi.py`. Ini penyimpangan kecil dari kata plan "seluruh test lama tetap lolos tanpa perubahan assertion" - tapi test yang dihapus itu SENDIRI adalah test Checkpoint 5 untuk perilaku SEMENTARA yang memang direncanakan diganti Checkpoint 6 (bukan test regresi milestone lain), jadi tidak melanggar semangat acceptance criteria (yang soal test REGRESI M3.4/M3.5/M2.4, bukan soal placeholder internal M4.2 sendiri).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/execution/ tests/layers/query_engine/ tests/layers/verification_gate/ -v` — **120/120 lolos**, mencakup:
- `test_klasifikasi_respons_revisi.py` (5 test baru): 400 lalu 200 di revisi ke-2 -> berhasil, `revisi_count=1`, feedback yang diteruskan ke `susun_request_atomic_intent` persis sama dengan `body["detail"]` respons 400; gagal di M3.4 -> `revisi_gagal_susun`; gagal di M3.5 -> `revisi_gagal_verifikasi_bentuk`; gagal di M2.4 -> `revisi_gagal_verification_gate`; 400 berulang sampai `EXECUTION_MAX_REVISI` habis -> `revisi_exhausted`, `_panggil_chatbot_api_raw` dipanggil TEPAT `EXECUTION_MAX_REVISI` kali dan `susun_request_atomic_intent` TEPAT `EXECUTION_MAX_REVISI-1` kali (bukti tidak berulang tanpa henti), span `execution.revisi_count` tercatat benar di seluruh skenario.
- `test_klasifikasi_respons.py` (7 test Checkpoint 5, setelah penghapusan 1 placeholder) tetap lolos TANPA perubahan assertion.
- SELURUH test regresi M3.4 (`test_penyusunan_request.py`, `test_param_whitelist.py`, `test_query_engine_schema.py`), M3.5 (`test_verifikasi_bentuk_request.py`), M2.4 (`test_verification_gate.py`, `test_verifikasi_gate.py`) — **lolos penuh, TANPA satu pun perubahan** (bukti tidak ada regresi lintas-milestone dari integrasi loop revisi).

**Commit:** *(pending)*

---

*(Checkpoint 7 - verifikasi nyata dan penutupan - DITUNDA sesuai Keputusan 4, lihat plan.)*

---

## Revisit — Integrasi Sinyal Freshness/Kualitas Data (`_meta`)

Dipicu kabar tim database (2026-08-17) endpoint `_meta` aktif — memenuhi pemicu peninjauan ulang Keputusan 1. Plan terpisah ditulis dan disetujui (lihat plan file sesi ini), checkpoint di bawah mengikuti plan itu.

### Checkpoint 1 — Keputusan dan Dokumentasi

**Mulai:** 2026-08-17

**Apa yang dilakukan**
Menambah addendum di Keputusan 1 (revisit) + Keputusan 11 baru (`decisions.md`) menjelaskan pemetaan final `flagged`/stale→`SEBAGIAN`, `null`/gagal→tetap `berhasil`+catatan. Menambah addendum kedua `docs/keputusan-tertunda.md` #3 — mencatat isi lengkap pesan tim database, keputusan ambang batas 48 jam (starting point), DAN draf pesan balasan ke tim database yang wajib dikirim user (item aksi eksplisit).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual — konsisten seluruh diskusi `AskUserQuestion` sesi ini (3 keputusan: pemetaan null/gagal, pemakaian ambang, retry meta call).

**Commit:** *(pending)*

### Checkpoint 2 — Pemanggilan Endpoint `_meta`

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

**Kesesuaian dengan plan:** Sesuai plan, dengan satu konsolidasi (dicatat di bawah).

**Apa yang dilakukan**
`HasilMetaChatbotAPI` ditambah ke `src/schemas/execution.py` (mirror XOR `HasilPemanggilanChatbotAPI`). `panggil_meta_chatbot_api()` ditambah ke `pemanggilan_chatbot_api.py` — GET `.../{slug}/_meta`, SATU percobaan (tanpa retry), TIDAK membuka span sendiri (dibungkus pemanggil M4.2). Non-200/kegagalan apa pun diperlakukan seragam "tidak diketahui" tanpa crash.

**Sekaligus dikerjakan** (konsolidasi dari Checkpoint 3 plan, karena satu file edit yang sama): perluasan validator `HasilEksekusiAtomicIntent` — `SEBAGIAN` sekarang valid (structurally mirip `BERHASIL`), field baru `data_quality_status`/`last_refreshed_at`. Diputuskan digabung karena kedua perubahan skema (M4.2 revisit) secara alami satu unit edit di file yang sama (`src/schemas/execution.py`) — Checkpoint 3 sekarang murni fokus ke `klasifikasi_respons.py` (logic klasifikasi + integrasi panggilan meta), bukan skema lagi.

**Temuan**
Test lama `test_status_di_luar_berhasil_gagal_teknis_ditolak[sebagian]` (parametrize) tadinya lolos untuk alasan SALAH setelah validator diperluas (SEBAGIAN sekarang valid sebagai STATUS, tapi test itu juga set `kegagalan_alasan="x"` yang tetap ditolak validator untuk SEBAGIAN — jadi masih raise ValidationError, tapi bukan karena status-nya lagi). Dikoreksi: parametrize dipersempit ke `DITOLAK_OTORISASI`/`TERBLOKIR_KETERGANTUNGAN` saja, ditambah test baru khusus `SEBAGIAN` (valid construction + 2 invarian: tanpa `kegagalan_alasan`, tanpa `bug_prioritas_tinggi=True`).

**Error/Kegagalan (jika ada)**
Tidak ada error nyata — temuan di atas ditangkap lewat review kode, bukan test yang gagal.

**Hasil Verifikasi**
`./.venv/Scripts/python.exe -m pytest tests/layers/execution/ -v` — **62/62 lolos, 1 skip (sengaja)** — mencakup seluruh regresi M4.1/M4.2/M4.3 (`test_pemanggilan_chatbot_api.py` 19, `test_execution_schema.py` 15, `test_klasifikasi_respons.py` 7, `test_klasifikasi_respons_revisi.py` 5, `test_penyimpanan_paket.py` 13, `test_penyimpanan_paket_integrasi.py` 2+1skip) TANPA satu pun kegagalan.

**Commit:** *(pending)*

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
