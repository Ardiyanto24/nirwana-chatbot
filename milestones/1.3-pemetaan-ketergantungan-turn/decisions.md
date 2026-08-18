# Decisions — Milestone 1.3: Membangun Pemetaan Ketergantungan Turn

## Keputusan 1: Payload Direvisi Membawa Seluruh Histori Sesi (Bukan Window N-Turn)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion` — didahului diskusi mendalam soal gap arsitektur).

**Latar Belakang**
Riset menyeluruh sebelum plan ditulis mengonfirmasi gap nyata di dokumen sumber: kontrak payload M1.2 (`arsitektur-ai-chatbot-rbac.md` §4, sebelum revisi) hanya membawa satu turn sebelumnya, tapi Kriteria Keberhasilan M1.3 menuntut deteksi rujukan ke turn yang jauh lebih lama (skenario uji: turn 7 merujuk turn 3), sementara Langkah 2 di titik ini eksplisit belum boleh membaca session memory. Tidak ada penjelasan mekanisme di dokumen manapun yang menutup gap ini — bahkan contoh plan resmi di `template-plan-milestone-lengkap.md` tidak menyadarinya. User awalnya menandai ini sebagai "dua skenario yang harus dihandle" (satu-turn vs multi-turn) yang belum tercakup M1.2.

**Keputusan yang Dipilih**
Payload direvisi membawa **seluruh histori turn dalam sesi** (turn 1 s.d. turn_index-1, masing-masing dengan `turn_index`, teks pertanyaan, dan jawaban) — bukan window N-turn terbatas.

**Alasan**
Pola umum chatbot API (frontend resend transkrip penuh tiap request). Window N-turn tetap tidak menyelesaikan kasus umum (rujukan ke turn di luar window) — hanya menggeser batas masalah, plus butuh keputusan tambahan (N berapa). Histori penuh memberi LLM akses semantik penuh ke turn manapun dalam sesi, sesuai kebutuhan literal Kriteria Keberhasilan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Window N turn terakhir (mis. 5)** — payload tetap terbatas ukurannya, tapi rujukan ke turn di luar window tetap tidak terdeteksi; hanya menggeser masalah, bukan menghilangkannya.
- **Batasi kemampuan M1.3 ke sinyal eksplisit + revisi Kriteria Keberhasilan sumber** — sempat jadi opsi rekomendasi awal (tidak mengganggu M1.2 yang sudah selesai), tapi user memilih memperluas payload setelah diskusi lebih lanjut mengonfirmasi keduanya (skenario satu-turn dan multi-turn) memang harus tercakup.

**Dampak**
Milestone 1.2 (sudah selesai/ter-commit) dibuka ulang sebagai prasyarat Checkpoint 1 milestone ini: `PreviousTurn`→`HistoryTurn`, `previous_turn`→`history: list`, validator baru, dokumen arsitektur §4 direvisi. Ukuran payload berpotensi membesar untuk sesi panjang — dicatat sebagai keterbatasan diterima baru (lihat Task 20).

---

## Keputusan 2: Provider LLM — OpenRouter

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Milestone 1.3 adalah pemanggilan LLM pertama proyek — provider belum pernah diputuskan (dicatat eksplisit sebagai keputusan tertunda di `CLAUDE.md` "Status Saat Ini").

**Keputusan yang Dipilih**
OpenRouter.

**Alasan**
User memilih fleksibilitas satu API untuk banyak provider model, dan akses ke model non-Claude yang lebih murah untuk tugas klasifikasi ringan seperti ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Anthropic API langsung** — direkomendasikan awal (latensi lebih rendah, tanpa markup router), tapi user memilih OpenRouter untuk fleksibilitas ganti-model dan opsi harga.

**Dampak**
`openai` Python SDK dipakai sebagai client (drop-in compatible, `base_url` diarahkan ke OpenRouter) — lihat Keputusan 6.

---

## Keputusan 3: Model — DeepSeek V4 Flash 0731 (untuk Testing)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Konsekuensi langsung Keputusan 2 — perlu model konkret. Tugas M1.3 ringan (klasifikasi terstruktur, bukan reasoning kompleks) tapi frekuensi tinggi (dipanggil hampir tiap turn bukan-pertama).

**Keputusan yang Dipilih**
`deepseek/deepseek-v4-flash-0731`.

**Alasan**
User eksplisit menyatakan ini **untuk keperluan testing** — bukan klaim final produksi. Dicatat apa adanya, bukan diam-diam diperlakukan sebagai keputusan permanen.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Sonnet 5** — direkomendasikan sebagai alternatif kalau butuh pemahaman bahasa lebih kuat untuk rujukan implisit/ambigu, tapi lebih mahal & lambat; tidak dipilih untuk tahap testing ini.

**Dampak**
Konstanta model diisolasi di `src/config/llm.py` — gampang diganti nanti tanpa menyentuh `turn_dependency.py`. Terverifikasi nyata bekerja (Checkpoint 3-4), termasuk lolos skenario tersulit (turn 7→turn 3).

---

## Keputusan 4: `response_format={"type": "json_object"}`, Bukan `json_schema` Strict Mode

**Status:** Ditemukan di tengah implementasi pada Checkpoint 3, Task 12.

**Latar Belakang**
Riset sebelum plan mengonfirmasi OpenRouter mendukung `json_schema` structured output, tapi "pada model yang kompatibel" — tidak semua model. Model testing yang dipilih (DeepSeek V4 Flash 0731) belum tentu termasuk yang didukung penuh.

**Keputusan yang Dipilih**
`response_format={"type": "json_object"}` (mode JSON umum) + instruksi bentuk JSON persis di system prompt + validasi Pydantic defensif (try/except) di kode, dengan fallback `is_dependent=False` kalau parsing/validasi gagal.

**Alasan**
`json_object` jauh lebih universal didukung across model/provider dibanding `json_schema` strict mode. Kombinasi dengan validasi defensif di kode memberi robustness yang setara tanpa bergantung pada fitur yang belum tentu didukung penuh.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`json_schema` strict mode** — rencana awal plan, berisiko gagal kalau model/provider tidak mendukung penuh; tidak diuji lebih lanjut karena `json_object` + validasi defensif sudah cukup robust dan terbukti bekerja (Checkpoint 3-4 lolos semua skenario).

**Dampak**
Murni internal `turn_dependency.py` — tidak berdampak ke kontrak yang dijanjikan ke milestone lain.

---

## Keputusan 5: `setup_tracing()` Wajib Dipanggil Eksplisit untuk Pemanggilan Langsung (Non-HTTP)

**Status:** Ditemukan di tengah implementasi pada Checkpoint 4, Task 16.

**Latar Belakang**
Verifikasi span nyata awalnya tidak menemukan span apa pun — ternyata pemanggilan `detect_turn_dependency()` langsung (smoke test Checkpoint 3, test suite Checkpoint 4) tidak pernah melewati `src.main`'s `lifespan`, satu-satunya tempat `setup_tracing()` dipanggil sejauh ini (Milestone 1.2). Tanpa itu, span dipakai `TracerProvider` no-op default OTel — tidak error, tapi juga tidak benar-benar terkirim.

**Keputusan yang Dipilih**
Untuk verifikasi manual/smoke-test yang tidak lewat HTTP, panggil `setup_tracing(service_name)` eksplisit dulu sebelum memanggil fungsi layer — pola yang sama seperti skrip smoke-test Milestone 1.1.

**Alasan**
Bukan bug di `turn_dependency.py`/`tracing.py` itu sendiri — ini konsekuensi wajar dari `detect_turn_dependency()` belum wired ke satu entry-point aplikasi manapun (M1.3 sengaja berdiri sendiri, lihat Batasan Mengikat plan). Begitu layer-layer lain dirangkai jadi satu pipeline (milestone mendatang), `setup_tracing()` akan dipanggil sekali di titik masuk aplikasi yang sesungguhnya, bukan berulang di tiap fungsi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Panggil `setup_tracing()` di dalam `detect_turn_dependency()` sendiri** — ditolak karena akan membuat setiap pemanggilan fungsi ini diam-diam membuat `TracerProvider` baru (mahal, dan bisa menimpa provider yang sudah di-setup aplikasi pemanggil kalau nanti sudah wired) — bukan pola yang benar untuk fungsi yang akan dipanggil berulang kali dalam satu proses aplikasi.

**Dampak**
Dicatat sebagai catatan untuk milestone mendatang yang akan mewiring beberapa layer sekaligus: `setup_tracing()` cukup dipanggil sekali di titik masuk aplikasi.

---

## Keputusan 6 (Forced): Output `{session_id, turn_index}`, Tidak Pernah `atomic_intent_id`

**Sumber Paksaan:** `arsitektur-ai-chatbot-rbac.md` baris 111-113 (sebelum nomor baris bergeser akibat revisi Keputusan 1) — LLM di titik ini belum pernah membaca session memory.

**Keputusan yang Diikuti:** `TurnDependencyResult` hanya berisi `is_dependent`+`referenced_turn_index`; `session_id` ditempel kode (bukan diminta dari LLM) karena rujukan selalu dalam sesi yang sama.

**Catatan Ketergantungan:** Memaksa LLM menghasilkan ID granular di titik ini membuka risiko halusinasi rujukan yang sebenarnya tidak ada — kontrak ini eksplisit mencegah itu.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by kontrak eksplisit.

---

## Keputusan 7 (Forced): Satu Pemanggilan LLM Tunggal, Tanpa Verifier Kedua

**Sumber Paksaan:** Output Milestone 1.3 ("satu pemanggilan model AI") + prinsip ruang-kesalahan-tertutup `CLAUDE.md`.

**Keputusan yang Diikuti:** Verifikasi hanya bounds-check deterministik (`referenced_turn_index` dalam rentang histori valid) — bukan LLM kedua.

**Catatan Ketergantungan:** Beda dari Decomposition (M1.6) yang eksplisit 3 langkah termasuk verifikasi independen — di sini penilaian makna itu sendiri sudah didesain sebagai satu keputusan LLM tunggal oleh dokumen sumber, dan yang perlu diverifikasi ulang murni bentuk output (closed error space), bukan makna.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 8 (Forced): Span `chat`, Atribut `gen_ai.*` dari `genai_semconv.py`

**Sumber Paksaan:** `rancangan-observability-ai-chatbot.md` Bagian 2.

**Keputusan yang Diikuti:** Konstanta diimpor dari `src/observability/genai_semconv.py` (Milestone 1.1) — tidak hardcode string baru.

**Catatan Ketergantungan:** Konsistensi lintas-layer untuk dashboard observability (Milestone 5.x).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 9 (Forced): `referenced_turn_index` di Luar Rentang → Dipaksa `is_dependent=False`

**Sumber Paksaan:** Kriteria Keberhasilan M1.3 sendiri ("tanpa memaksakan rujukan yang sebenarnya tidak ada").

**Keputusan yang Diikuti:** Bounds-check + fallback aman, dicatat sebagai span attribute anomali.

**Catatan Ketergantungan:** Lebih aman under-trigger daripada over-trigger dengan rujukan salah.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 10 (Forced): `src/layers/context_resolution/` sebagai Subpackage

**Sumber Paksaan:** 1 layer arsitektur (Context Resolution) = 4 milestone implementasi (1.3/1.4/1.5/1.7).

**Keputusan yang Diikuti:** Subpackage, bukan `context_resolution.py` tunggal — `turn_dependency.py` untuk M1.3.

**Catatan Ketergantungan:** Konsisten konvensi "per-layer" M1.2 tanpa memaksakan 4 milestone masuk 1 file.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif dipertimbangkan — perluasan wajar dari keputusan `src/` M1.2.

---

## Keputusan 11 (Forced): `openai` SDK sebagai Client, API Key via Environment Variable

**Sumber Paksaan:** OpenRouter drop-in compatible dengan OpenAI API (dikonfirmasi riset resmi) + `CLAUDE.md` ("Rahasia tidak boleh di-hardcode atau di-commit").

**Keputusan yang Diikuti:** `openai.OpenAI(base_url=OPENROUTER_BASE_URL)`; `OPENROUTER_API_KEY` dibaca dari environment (`.env`/`.env.example` template, gitignored).

**Catatan Ketergantungan:** Tidak ada SDK OpenRouter terpisah yang perlu dipertimbangkan — ini cara resmi yang didokumentasikan OpenRouter.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 12 (Addendum): `detect_turn_dependency()` Diberi `try/except APIError` — Fallback Aman Sama Seperti Kegagalan Parse/Bounds

**Status:** Ditemukan di Milestone 7.6 (2026-08-18, saat memetakan kejadian struktural untuk menyambungkan Input Layer ke Pemetaan Ketergantungan Turn), diperbaiki di sini atas instruksi eksplisit user — bukan ditutup di M7.6 sendiri, karena perbaikan logic internal M1.3 adalah tanggung jawab milestone pemilik layer ini, bukan milestone penyambung.

**Latar Belakang**
Investigasi M7.6 menemukan `detect_turn_dependency()` TIDAK punya `try/except` sama sekali di sekitar `_call_llm(payload)` — beda dari SEMUA layer LLM lain di project (yang menangkap `openai.APIError` dan mendegradasi ke status gagal teknis), kecuali `susun_narasi()` (M4.4, sengaja tanpa fallback, terdokumentasi eksplisit di `decisions.md`-nya sendiri). Dokumen `decisions.md` M1.3 ini (Keputusan 9 di atas) hanya mendokumentasikan fallback untuk kegagalan PARSE/BOUNDS (JSON rusak atau `referenced_turn_index` di luar histori valid) — TIDAK PERNAH membahas kegagalan API/jaringan teknis. Dibuktikan nyata lewat kejadian E04 M7.6 (`evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/payloads/E04.json`, sebelum fix ini): `_call_llm` dipaksa raise `openai.APIError`, exception menjalar keluar TANPA ditangkap di titik mana pun — dicatat sempat sebagai `docs/keterbatasan-diterima.md` #14 (kini berstatus DIPERBAIKI, lihat file itu).

**Keputusan yang Dipilih**
`_call_llm(payload)` dibungkus `try/except APIError`, mengembalikan `TurnDependencyResult(is_dependent=False)` + mencatat span attribute `dependency.forced_independent_reason=f"api_error: {exc}"` — REUSE persis mekanisme fallback aman yang sudah ada untuk kegagalan parse/bounds (Keputusan 9), bukan menambah field/status baru ke skema `TurnDependencyResult`.

**Alasan**
`TurnDependencyResult` sengaja hanya `{is_dependent, referenced_turn_index}` tanpa field `status` (beda dari skema layer lain yang punya `StatusEksekusi`) — menambah field baru untuk membedakan "gagal teknis" dari "berhasil, independen" berarti mengubah skema yang sudah dipakai `KeadaanTurn` (M7.6, `src/schemas/orchestration.py`) dan berpotensi konsumen lain nanti. `is_dependent=False` sebagai fallback aman sudah konsisten dengan filosofi modul ini sejak awal ("lebih aman under-trigger daripada over-trigger dengan rujukan salah", Keputusan 9) — kegagalan teknis genuinely tidak beda konsekuensinya dari kegagalan parse dari sudut pandang pemanggil: keduanya sama-sama "tidak bisa dipercaya menentukan dependency, aman diasumsikan independen". Span attribute `dependency.forced_independent_reason` tetap membedakan alasan (`api_error: ...` vs alasan parse/bounds) untuk keperluan observability/debugging, tanpa mengubah kontrak tipe.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menambah field `status: StatusEksekusi` ke `TurnDependencyResult`** — ditolak, perubahan skema breaking yang merembet ke `KeadaanTurn` (M7.6) dan konsumen masa depan, tidak sepadan untuk kasus yang sudah bisa direpresentasikan lewat mekanisme fallback yang sudah ada.
- **Membiarkan exception menjalar apa adanya (status quo)** — ditolak eksplisit oleh user: "sekalian saja perbaiki celah tersebut."

**Dampak**
`tests/layers/context_resolution/test_turn_dependency_kegagalan.py` (baru, mocked, mirror pola `test_session_memory_kegagalan.py`) membuktikan fallback ini. `docs/keterbatasan-diterima.md` #14 diperbarui status jadi DIPERBAIKI. `milestones/7.6-.../report.md` diberi catatan silang bahwa temuannya sudah ditutup di sini, bukan lagi "diterima, tidak diperbaiki".

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Payload histori penuh (bukan window N-turn) | A | Plan |
| 2 | Provider LLM: OpenRouter | A | Plan |
| 3 | Model: DeepSeek V4 Flash 0731 (untuk testing) | A | Plan |
| 4 | `response_format json_object` bukan `json_schema` strict | A | Checkpoint 3 |
| 5 | `setup_tracing()` eksplisit untuk pemanggilan non-HTTP | A | Checkpoint 4 |
| 6 | Output `{session_id, turn_index}`, tidak pernah `atomic_intent_id` | B | Plan |
| 7 | Satu pemanggilan LLM tunggal, tanpa verifier kedua | B | Plan |
| 8 | Span `chat`, atribut `gen_ai.*` | B | Plan |
| 9 | Bounds-check `referenced_turn_index` → fallback aman | B | Plan |
| 10 | `src/layers/context_resolution/` subpackage | B | Checkpoint 2 |
| 12 | Addendum M7.6: `try/except APIError`, reuse fallback aman | A | Addendum 2026-08-18 |
| 11 | `openai` SDK + API key via env var | B | Plan |
