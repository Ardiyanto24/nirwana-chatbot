# Decisions — Milestone 7.7: Sambungan 2 (Pemetaan Ketergantungan → Percabangan Paralel: Rewrite + Tarik Memory)

Dokumen ini mencatat keputusan desain untuk Milestone 7.7, Sambungan kedua Level 2 PIC 7, ditentukan sebelum implementasi dimulai (Plan Mode). M7.7 memperkenalkan mekanisme konkurensi PERTAMA di seluruh codebase — tidak ada preseden apa pun untuk ditarik, sehingga satu keputusan genuinely terbuka diajukan ke user lewat `AskUserQuestion` (dengan penjelasan detail trade-off atas permintaan user).

---

### Keputusan 1: Mekanisme paralel — `concurrent.futures.ThreadPoolExecutor`

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion` — user meminta penjelasan detail trade-off sebelum menjawab).

**Latar Belakang**
M7.7 butuh menjalankan Rewrite (M1.4, pemanggilan LLM blocking) dan Tarik Session Memory (M1.5, query DB blocking) secara BENAR-BENAR bersamaan — bukan berurutan seolah paralel. Grep menyeluruh `src/` untuk `asyncio|threading|concurrent.futures|async def|ThreadPoolExecutor` hanya menghasilkan boilerplate FastAPI di `src/main.py` (tidak pernah dipakai substantif) — genuinely tidak ada preseden konkurensi di project ini. Keputusan ini kemungkinan jadi pola yang dipakai ulang milestone Sambungan berikutnya yang juga butuh percabangan paralel.

**Keputusan yang Dipilih**
`concurrent.futures.ThreadPoolExecutor(max_workers=2)` — `proses_turn()` tetap fungsi sinkron biasa, kedua fungsi blocking (`rewrite_to_standalone`, `retrieve_session_memory`) di-submit ke thread pool, ditunggu lewat `.result()`.

**Alasan**
Dijelaskan detail ke user (cara kerja, kelebihan, kekurangan) sebelum jawaban final: kedua kandidat (Opsi A `ThreadPoolExecutor`, Opsi B `asyncio.gather`+`asyncio.to_thread`) sama-sama memakai thread di baliknya — baik `openai.OpenAI` (client Rewrite) maupun SQLAlchemy `Engine` (client Tarik Memory) bukan versi async-native (tidak ada `AsyncOpenAI`/`asyncpg` di project), jadi Opsi B tetap butuh `asyncio.to_thread()` untuk membungkus keduanya — mekanisme dasarnya identik, cuma lewat API `asyncio` yang lebih rumit. Opsi A tidak memaksa `proses_turn()` (dan kemungkinan besar 9 milestone Sambungan berikutnya yang terus memperluas fungsi yang sama) berubah jadi `async def` tanpa manfaat nyata — `src/main.py` sendiri belum disambungkan ke `proses_turn()` (sengaja ditunda M7.17), jadi tidak ada forcing function untuk async sekarang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`asyncio.gather` + `asyncio.to_thread`** — ditolak user setelah penjelasan detail: manfaat nyata untuk kasus M7.7 spesifik tidak ada (mekanisme dasar sama-sama thread), tapi memaksa perubahan bentuk `proses_turn()` jadi async yang berpotensi menular ke seluruh milestone Sambungan berikutnya tanpa forcing function yang jelas saat ini.

**Dampak**
Menentukan pola konkurensi yang kemungkinan dipakai ulang milestone Sambungan lain yang butuh percabangan paralel di masa depan.

---

### Keputusan 2: Propagasi context OTel manual via `opentelemetry.context.attach()`/`detach()`

**Sumber Paksaan**
Konsekuensi teknis langsung dari Keputusan 1 (`ThreadPoolExecutor`): `contextvars.ContextVar` yang dipakai OTel Python untuk propagasi span TIDAK otomatis diwariskan ke thread baru. **Diverifikasi NYATA** (bukan cuma teori) terhadap Jaeger live yang sedang berjalan sebelum keputusan ini dikunci: skrip percobaan membuka span induk lalu dua span anak di dua worker thread — TANPA propagasi context, kedua span anak menjadi trace_id yang SAMA SEKALI TERPISAH dari span induk (root baru masing-masing); DENGAN `context.attach()`/`detach()` (context ditangkap di thread utama SEBELUM `executor.submit()`, di-attach di awal tiap fungsi worker), query Jaeger API mengonfirmasi kedua span anak sama-sama `parentSpanID` = span induk yang sama persis.

**Keputusan yang Diikuti**
```python
ctx = otel_context.get_current()  # ditangkap DI DALAM with tracer.start_as_current_span("invoke_agent")
with ThreadPoolExecutor(max_workers=2) as executor:
    rewrite_future = executor.submit(_jalankan_rewrite, ctx, payload)
    memory_future = executor.submit(_jalankan_tarik_memory, ctx, session_id, turn_index) if harus_tarik_memory else None
```
Tiap fungsi worker (`_jalankan_rewrite`, `_jalankan_tarik_memory`) memanggil `otel_context.attach(ctx)` di awal, `otel_context.detach(token)` di `finally`, membungkus pemanggilan fungsi asli (`rewrite_to_standalone`/`retrieve_session_memory`) apa adanya.

**Catatan Ketergantungan**
`ctx` WAJIB ditangkap DI DALAM blok `with tracer.start_as_current_span("invoke_agent")` — kalau ditangkap di luar blok itu (mis. sebelum span dibuka), context yang tertangkap tidak akan membawa `invoke_agent` sebagai parent, dan seluruh bukti span M7.7 gagal tanpa pesan error yang jelas (span tetap tercatat di Jaeger, cuma sebagai trace terpisah — kegagalan diam-diam, bukan crash).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — satu-satunya cara yang terverifikasi bekerja untuk `ThreadPoolExecutor` dengan OTel Python SDK versi yang dipakai project ini.

---

### Keputusan 3: `KeadaanTurn` bertambah `rewrite: RewriteResult` dan `session_memory: list[SessionMemoryPackage] | None`

**Sumber Paksaan**
`rewrite_to_standalone()` (M1.4) punya fallback penuh (tidak pernah raise) — selalu menghasilkan `RewriteResult`, forced field non-Optional. KK M7.7 sendiri eksplisit membedakan "Tarik Memory tidak terpanggil sama sekali" dari "terpanggil lalu menghasilkan kosong" — `None` (tidak dipanggil) vs `[]` (dipanggil, genuinely kosong) adalah satu-satunya representasi Python yang menangkap kedua kondisi berbeda ini tanpa ambigu.

**Keputusan yang Diikuti**
```python
class KeadaanTurn(BaseModel):
    payload: TurnPayload
    ketergantungan: TurnDependencyResult
    rewrite: RewriteResult
    session_memory: list[SessionMemoryPackage] | None
```
Kedua field baru WAJIB diisi eksplisit (tanpa default) — konsisten disiplin dua field M7.6 yang sudah ada. Nama field `rewrite`/`session_memory` mengikuti konvensi loanword Inggris yang sudah konsisten dipakai modul terkait (`rewrite.py`, `RewriteResult`, `session_memory.py`), bukan diterjemahkan paksa.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang — bentuk ini satu-satunya yang konsisten dengan kontrak kedua fungsi + KK M7.7.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`session_memory: list[SessionMemoryPackage]` dengan default `[]` untuk kedua kondisi** — ditolak, melanggar eksplisit teks KK M7.7 ("bukan terpanggil lalu menghasilkan kosong") yang menuntut kedua kondisi bisa dibedakan.

---

### Keputusan 4: Kondisi pemicu Tarik Memory — `ketergantungan.is_dependent and ketergantungan.referenced_turn_index is not None`

**Sumber Paksaan**
KK M7.7 sendiri ("jika ada referensi terdeteksi"). Ditambah kebutuhan type-narrowing: `retrieve_session_memory(session_id: str, turn_index: int)` butuh `int` murni, sementara `TurnDependencyResult.referenced_turn_index` bertipe `int | None` di level skema — meski `_parse_and_validate()` (M1.3) selalu menjaga invariant "`is_dependent=True` implies `referenced_turn_index` bukan `None`" di praktik, skema sendiri tidak menegakkannya, sehingga pengecekan eksplisit tetap wajib untuk kebenaran tipe.

**Keputusan yang Diikuti**
`harus_tarik_memory = ketergantungan.is_dependent and ketergantungan.referenced_turn_index is not None` — dicek sebelum `executor.submit()` untuk cabang Tarik Memory.

**Catatan Ketergantungan**
Tidak ada ruang dipertimbangkan ulang.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced ganda oleh KK sumber + kebenaran tipe.

---

### Keputusan 5: Kegagalan ganda (kedua cabang gagal bersamaan) TIDAK ditangani secara khusus

**Sumber Paksaan**
Genuinely terbuka tapi diputuskan langsung (bukan diajukan `AskUserQuestion`) karena skenarionya sangat sempit dan tidak diminta KK sumber sama sekali — `rewrite_to_standalone()` punya fallback penuh sendiri (nyaris tidak pernah raise), sehingga kegagalan ganda butuh KEDUA hal terjadi bersamaan: bug non-`APIError` di Rewrite DAN kegagalan DB di Tarik Memory pada saat yang sama.

**Keputusan yang Diikuti**
`.result()` dipanggil berurutan (Rewrite dulu, baru Memory) — exception pertama yang ditemukan yang menjalar ke pemanggil `proses_turn()`. Kalau keduanya gagal, exception cabang kedua hilang tanpa peringatan (`concurrent.futures` tidak punya mekanisme "unretrieved exception warning" seperti `asyncio`).

**Catatan Ketergantungan**
Membangun penanganan lebih defensif (`concurrent.futures.wait()` + inspeksi kedua exception, gabung jadi satu pesan, dst) tidak sepadan untuk skenario yang probabilitasnya sangat rendah dan tidak diminta sumber manapun — kompleksitas tambahan tanpa kebutuhan nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`concurrent.futures.wait()` + inspeksi kedua exception secara eksplisit** — ditolak, kompleksitas tidak sepadan untuk skenario tepi yang sangat sempit dan tidak diminta KK sumber.

---

### Keputusan 6: Celah `retrieve_session_memory()` (M1.5) diperbaiki di sini, didokumentasikan di M1.5 — TANPA entri `keterbatasan-diterima.md`

**Sumber Paksaan**
Investigasi M7.7 menemukan `retrieve_session_memory()` (M1.5) TIDAK punya `try/except` di sekitar query DB-nya — beda dari fungsi kembarnya di file yang sama, `store_session_memory()`, yang sudah menangkap exception, menandai `error.type=gagal_teknis` di span, baru raise ulang. Preseden penanganan celah serupa (`detect_turn_dependency()` M1.3, ditemukan+diperbaiki sesi kerja sebelumnya): kode diperbaiki, dokumentasi masuk milestone PEMILIK layer (bukan milestone penyambung yang menemukannya), karena logic internal layer tetap tanggung jawab pemiliknya.

**Keputusan yang Diikuti**
`retrieve_session_memory()` diperbaiki: `try/except Exception: span.set_attribute("error.type", "gagal_teknis"); raise`, mirror persis `store_session_memory()`. Test baru masuk `tests/layers/context_resolution/test_session_memory_kegagalan.py` (file SUDAH ADA, docstring-nya sendiri sudah menyebut "mirror pola `memory.retrieve`" — mengantisipasi celah ini). Dokumentasi fix: Addendum di `milestones/1.5-tarik-session-memory/{decisions.md,logs.md,report.md}` — BUKAN di M7.7. Catatan silang singkat di `decisions.md` M7.7 ini (bagian ini sendiri) menjelaskan kenapa `session_memory.py` ikut berubah di bawah commit ber-tag M7.7.

**Alasan**
**Beda dari preseden M1.3**: celah M1.3 sempat "diterima" dulu sebagai keterbatasan (`docs/keterbatasan-diterima.md` #14) sebelum diperbaiki belakangan atas instruksi eksplisit user — ada jeda waktu nyata di mana ia berstatus "diterima, tidak diperbaiki". Celah M1.5 ini ditemukan DAN diperbaiki SEBELUM M7.7 sendiri selesai/di-commit — tidak pernah benar-benar berstatus "diterima sebagai keterbatasan" barang sesaat pun, sehingga entri `docs/keterbatasan-diterima.md` tidak diperlukan sama sekali (backlog itu untuk hal yang genuinely diterima, bukan diperbaiki — celah ini langsung ditutup).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunda perbaikan, catat sebagai keterbatasan diterima dulu (mirror M1.3 persis)** — ditolak, tidak ada alasan menunda ketika perbaikannya sudah jelas dan sempit (mirror pola yang sudah ada di file yang sama), berbeda dari M1.3 yang ditemukan di tengah milestone lain yang sedang berjalan dan sengaja tidak disentuh saat itu.
- **Perbaikan didokumentasikan di M7.7 sendiri** — ditolak, forced by prinsip "layer pemilik yang mendokumentasikan perbaikan logic internalnya sendiri" yang sudah established preseden M1.3.

---

### Keputusan 7: Test kejadian kegagalan teknis masuk `tests/orchestration/`, bukan `evals/`

**Sumber Paksaan**
Klaim inti kejadian ini (exception dari satu cabang menjalar keluar `proses_turn()`, cabang lain tetap selesai lewat `ThreadPoolExecutor.__exit__`'s `shutdown(wait=True)`) sepenuhnya bisa dibuktikan deterministik lewat mock — tidak butuh LLM/DB/Jaeger nyata sama sekali, beda dari kejadian E01/E02 (butuh koneksi nyata + bukti span).

**Keputusan yang Diikuti**
Kejadian kegagalan teknis satu cabang diuji di `tests/orchestration/test_turn_pipeline.py` (Checkpoint 4), bukan dieksekusi ulang lewat `evals/7.7-.../run_eval.py`.

**Catatan Ketergantungan**
Beda dari M7.6 (yang menaruh kejadian kegagalan teknisnya di `evals/` E04) — perbedaan ini disengaja: M7.6 memilih `evals/` untuk kelengkapan naratif peta kejadian meski secara teknis bisa juga mocked-only; M7.7 secara eksplisit memilih `tests/` untuk kejadian setipe supaya lebih cepat/tidak butuh infra tambahan, mengingat cakupan real-execution M7.7 (E01/E02) sudah cukup padat.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Duplikasi kejadian kegagalan teknis ke `evals/` juga (mirror M7.6 persis)** — ditolak, tidak menambah bukti baru (mekanismenya generik, tidak spesifik LLM/DB tertentu), murni duplikasi kerja.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Mekanisme paralel: `ThreadPoolExecutor` | A | Plan |
| 2 | Propagasi context OTel manual (attach/detach) | B | Plan |
| 3 | `KeadaanTurn` field baru: `rewrite`, `session_memory` | B | Plan |
| 4 | Kondisi pemicu Tarik Memory | B | Plan |
| 5 | Kegagalan ganda tidak ditangani khusus | B | Plan |
| 6 | Fix `retrieve_session_memory()` di M1.5, bukan `keterbatasan-diterima.md` | B | Checkpoint 2 |
| 7 | Test kegagalan teknis di `tests/`, bukan `evals/` | B | Checkpoint 4 |
