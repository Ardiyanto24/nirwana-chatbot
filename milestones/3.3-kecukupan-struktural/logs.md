# Logs — Milestone 3.3: Pemeriksaan Kecukupan Struktural

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.3-kecukupan-struktural/decisions.md`: 10 keputusan (2 Jenis A hasil `AskUserQuestion` dalam sesi perencanaan — mekanisme hybrid deterministik+fallback LLM konservatif (user menolak rekomendasi awal deterministik-murni dengan argumen forward-looking soal taksonomi `label_bentuk_jawaban` yang akan bertambah kompleks), dan aturan tie-break `view_name_final` label-dulu-baru-skor; 8 Jenis B forced/preseden — termasuk refactor span M3.1 untuk memenuhi KK3 literal, fail-safe rule table ke LLM untuk label tak dikenal, satu panggilan LLM konservatif tanpa verifier kedua karena asimetri risiko, batching per kebutuhan atomik, status selalu BERHASIL).

**Temuan**
Tidak ada temuan baru di luar yang sudah tercatat di plan (Context "Temuan Penting").

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh keputusan di plan yang disetujui (Keputusan Desain Turunan + Keputusan yang Ditanyakan ke User) punya entri `decisions.md` dengan "Opsi yang Dipertimbangkan tapi Ditolak", tidak ada yang diam-diam jadi asumsi implisit.

**Commit:** `3535026` — `docs(milestone-3.3): decisions.md keputusan awal`

---

## Checkpoint 2 — Taksonomi Grain Terstruktur (67 View)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 2 — Bangun `grain_view.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membaca seluruh 67 baris "Sumber" (grain) di `docs/03-domain-source/katalog-data-chatbot.md` (via `Grep` pola `^#### \`|^\*Sumber:` untuk mengekstrak pasangan view_name+grain sekaligus, menghindari baca manual satu-satu). Mengklasifikasi tiap view ke dua sinyal tri-state (`punya_time_series`, `punya_dimensi_pembanding`) + catatan rasional, ditulis ke `src/layers/retriever/grain_view.py` (`GRAIN_STRUKTURAL_VIEW: dict[str, KarakteristikGrain]`, Pydantic `BaseModel` lokal ke modul ini — beda dari korpus/definisi M3.1/M3.2 yang `dict[str, str]` polos, karena di sini bentuknya struktur bukan teks).

**Temuan**
Klasifikasi row-level (`mart_cleaned`, "1 baris = 1 X") ternyata TIDAK seragam: sebagian py label periode eksplisit di grain-nya sendiri (`v_lookup_payroll` "1 baris = 1 karyawan × 1 bulan", `v_lookup_staff_shifts` "1 baris = 1 karyawan × 1 hari kerja") — ini diklasifikasi `ya`/`ya` (mirror `v_hr_employee_monthly`/`v_hr_attendance_daily`), BUKAN otomatis `tidak_pasti` hanya karena row-level. Sebaliknya, row-level TANPA label periode (`v_lookup_bookings` "1 baris = 1 reservasi", `v_lookup_fnb_transactions`, `v_lookup_housekeeping_log`, `v_lookup_maintenance_tickets`, `v_lookup_spa_bookings`, `v_lookup_event_bookings`) diklasifikasi `tidak_pasti` untuk kedua sinyal — genuinely ambigu apakah cukup untuk tren/perbandingan agregat. 3 tabel referensi murni tanpa metrik bisnis (`v_properties_ref`, `v_employees_directory`, `guests_contact_view`) diklasifikasi `tidak`/`tidak` (bukan ambigu — katalog eksplisit menyatakan isinya cuma nama/kontak, bukan metrik).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Klasifikasi direview ulang sekali (baca kembali seluruh 67 baris grain dari hasil Grep, dicocokkan terhadap tabel akhir) sebelum lanjut ke Task 3.

**Commit:** *(digabung dengan Task 3, lihat di bawah)*

---

### Task 3 — Test Taksonomi Grain

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_grain_view.py` — 10 test: bijektif dengan `DAFTAR_VIEW_PER_DOMAIN`, 67-count, seluruh entri bertipe `KarakteristikGrain` dengan nilai tri-state valid, spot-check kasus jelas (`v_reservation_room_type_daily` ya/ya, `v_facility_room_status_daily`/`v_hr_turnover_snapshot`/`v_hr_headcount_status_daily` snapshot→`tidak`, `v_properties_ref` tidak/tidak, `v_lookup_payroll` row-level-berlabel-periode→ya/ya), dan bukti jalur hybrid genuinely dipicu (minimal satu entri `tidak_pasti` per masing-masing sinyal, termasuk assert eksplisit `v_lookup_bookings` ada di daftar `tidak_pasti`).

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada — seluruh 10 test lolos pada percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_grain_view.py -v` → 10 passed.

**Commit:** *(lihat commit gabungan Task 2-3 di bawah)*

---

## Checkpoint 3 — Skema Kecukupan Struktural

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — Extend `src/schemas/retriever.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan `SumberKeputusanKecukupan` (Enum `DETERMINISTIK`/`LLM`), `KecukupanKandidat`, `HasilKecukupanStruktural` ke `src/schemas/retriever.py` (extend file yang sama, mirror pola M3.1+M3.2 satu file). Validator `status_dan_view_name_final_konsisten`: (a) `status` wajib `StatusEksekusi.BERHASIL`; (b) `view_name_final` (kalau tidak `None`) wajib match salah satu `kecukupan` berlabel `cukup=True`.

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 5 (test skema dijalankan bersamaan).

**Commit:** `fbf5488` — `feat(milestone-3.3): skema kecukupan struktural`

---

### Task 5 — Test Skema

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_kecukupan_struktural_schema.py` (file terpisah dari `test_kecukupan_struktural.py` yang akan berisi test orkestrator Checkpoint 8+, mirror pola `test_kecocokan_makna_schema.py` vs `test_kecocokan_makna.py` M3.2) — 8 test mencakup kedua validator, dua arah gagal (status bukan BERHASIL/GAGAL_TEKNIS; view_name_final tidak match kandidat cukup manapun — dua sub-kasus: kandidat ada tapi cukup=False, dan view_name_final tidak pernah dievaluasi sama sekali) dan arah sukses (view_name_final=None valid untuk dua kasus "tidak ada kandidat cukup"; view_name_final match kandidat cukup valid).

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada — seluruh 8 test lolos pada percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/retriever/ -v` (regresi penuh subpackage, bukan hanya file baru) → 85 passed, termasuk 8 test baru + seluruh test M3.1/M3.2 existing tanpa perubahan assertion.

**Commit:** `fc31a1a` — `test(milestone-3.3): validator skema kecukupan struktural`

---

## Checkpoint 4 — Mekanisme Deterministik (Rule Table)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6 — Bangun `_evaluasi_deterministik()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `src/layers/retriever/kecukupan_struktural.py` (baru) berisi `_evaluasi_deterministik(label_bentuk_jawaban, grain) -> tuple[str, str]`: `nilai_tunggal` selalu `cukup`; `tren` dicek lewat `grain.punya_time_series`; `perbandingan`/`peringkat`/`komposisi` dicek lewat `grain.punya_dimensi_pembanding` (tiga label ini pola rule-nya identik — sama-sama butuh grain yang menghasilkan >1 baris comparable). Label yang tidak dikenal rule table (dibandingkan `==` terhadap seluruh anggota `LabelBentukJawaban` yang eksplisit dicek) jatuh ke cabang terakhir `tidak_pasti`.

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 7.

**Commit:** `23a79d1` — `feat(milestone-3.3): mekanisme deterministik rule table`

---

### Task 7 — Test Matriks Lengkap

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_kecukupan_struktural.py` — 22 test (parametrized) mencakup seluruh kombinasi 5 label x nilai tri-state relevan per label, PLUS satu kasus fail-safe: memanggil `_evaluasi_deterministik()` dengan `label_bentuk_jawaban` berupa plain `str` ("deskriptif_naratif") yang BUKAN anggota Enum `LabelBentukJawaban` saat ini — mensimulasikan taksonomi label masa depan tanpa perlu mengubah Enum, membuktikan perbandingan `==` di rule table jatuh ke cabang fail-safe terakhir alih-alih exception/menebak.

**Temuan**
Tidak ada — hipotesis desain (perbandingan `==` enum vs plain str aman dan predictable di Python) terbukti sesuai ekspektasi pada percobaan pertama.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_kecukupan_struktural.py -v` → 22 passed.

**Commit:** `22c9df6` — `test(milestone-3.3): matriks rule deterministik + fail-safe`

---

## Checkpoint 5 — Prompt LLM Fallback

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 8 — Tulis Prompt

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `src/prompts/retriever/kecukupan_struktural_fallback.md` (id `retriever.kecukupan_struktural_fallback`, mirror struktur `context_resolution/matching.md` M1.7 — satu panggilan konservatif tanpa variabel Jinja2, beda dari `kecocokan_makna_generate.md` M3.2 yang butuh `catatan_lintas_domain`). Instruksi eksplisit menjelaskan konteks per bentuk jawaban (nilai_tunggal/tren/perbandingan-peringkat-komposisi) dan aturan "kalau ragu, cukup=false".

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`load_prompt("retriever.kecukupan_struktural_fallback")` sukses parse frontmatter+body, `.render()` menghasilkan teks tanpa error (tidak ada variabel Jinja2 yang perlu di-supply).

**Commit:** `2dbf085` — `feat(prompts): prompt fallback kecukupan struktural`

---

## Checkpoint 6 — Fungsi LLM Fallback + Observability

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 9 — Implementasikan `_evaluasi_llm_fallback()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan `OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL = "qwen/qwen3-32b"` ke `src/config/llm.py` (+ dokumentasi entri di docstring modul). Menambahkan `_evaluasi_llm_fallback()` ke `kecukupan_struktural.py` — satu panggilan batch (`_call_llm_fallback`, dipisah dari span/parsing untuk reuse skrip eval, mirror pola `kecocokan_makna.py`), span `"chat"` (`gen_ai.operation.name`/`gen_ai.request.model`/`prompt.id`/`prompt.version`) HANYA dibuka kalau `kandidat_tidak_pasti` non-kosong. Reuse `DEFINISI_LENGKAP_VIEW` (corpus M3.2) sebagai sumber teks grain lengkap per kandidat di user prompt — bukan re-derive dari `KarakteristikGrain.catatan` sendiri (yang notabene adalah interpretasi kita, bukan definisi asli katalog). Tiga jalur kegagalan (API error, empty choices, JSON rusak total) sama-sama jatuh ke `_default_aman_semua()` — SELURUH kandidat batch itu `cukup=False`, `sumber_keputusan=LLM`. Kandidat yang hilang dari respons yang SEBAGIAN valid (`_parse_fallback`) diberi default aman individual (bukan menggagalkan seluruh batch).

**Temuan**
Tidak ada penyimpangan dari plan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 10.

**Commit:** `cbb1ad1` — `feat(milestone-3.3): fallback llm konservatif kecukupan struktural`

---

### Task 10 — Test Monkeypatch

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan 6 test ke `tests/layers/retriever/test_kecukupan_struktural.py`: batch kosong (dibuktikan monkeypatch `_call_llm_fallback` raise `AssertionError`, mirror pola pembuktian jalur pintas M2.3/M3.2), sukses normal, API error, empty choices, JSON rusak (tiga terakhir sama-sama menguji `_default_aman_semua`), dan kandidat hilang dari respons sebagian valid (test langsung ke `_parse_fallback`, bukti jaminan struktural "tidak drop diam-diam" mirror M3.2).

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada — seluruh 6 test baru lolos pada percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_kecukupan_struktural.py -v` → 28 passed (22 test Checkpoint 4 + 6 test baru).

**Commit:** `6ebb667` — `test(milestone-3.3): fallback llm monkeypatch`

---

## Checkpoint 7 — Reliability Testing Promptfoo (Native)

**Mulai:** 2026-08-17 · **Selesai:** *(lihat Checkpoint 8 log untuk hasil run — dieksekusi paralel dengan implementasi Checkpoint 8 karena run Promptfoo panggilan API nyata memakan waktu, tidak memblokir kerja lain yang tidak bergantung padanya)*

### Task 11 — Config Promptfoo Native

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `prompt_reliability/retriever/kecukupan_struktural_fallback.promptfooconfig.yaml` — 4 skenario: S01 (row-level `v_lookup_bookings` tanpa label periode, label tren, assert `cukup=false`), S02 (grain jelas time-series `v_reservation_room_type_daily`, label tren, assert `cukup=true`), S03 (snapshot eksplisit `v_facility_room_status_daily`, label tren, assert `cukup=false`), S04 (dua kandidat sekaligus dalam satu batch — bukti WAJIB menilai keduanya, plus assert kandidat grain jelas tetap `cukup=true` di tengah batch campuran). Definisi view di tiap skenario diambil PERSIS dari `DEFINISI_LENGKAP_VIEW` (dibaca via skrip sekali-pakai ke file sementara, dihapus setelah dipakai — menghindari masalah encoding konsol Windows, bukan korupsi data) supaya user_prompt di config identik dengan yang benar-benar dikirim `_build_user_prompt_fallback()` saat runtime.

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada saat penulisan config (hasil eksekusi nyata dicatat terpisah setelah run selesai — lihat Checkpoint 8 log).

**Hasil Verifikasi**
*(menyusul — run Promptfoo lokal dieksekusi di background, hasil + push ke `prompt_eval_runs` dicatat begitu selesai)*

**Commit:** `fa1ac35` — `chore(prompt-reliability): config kecukupan struktural`

---

## Checkpoint 8 — Orkestrator Per Kebutuhan Atomik + Tie-Break

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 12 — Implementasikan Orkestrator

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan `evaluasi_kecukupan_struktural_atomic_intent()` ke `kecukupan_struktural.py`: filter `hasil_kecocokan.kecocokan` ke label `ditemukan`/`sebagian`; loop tiap kandidat lewat `_evaluasi_deterministik()`; kandidat dengan hasil `tidak_pasti` dikumpulkan dan dilempar SEKALI (batch) ke `_evaluasi_llm_fallback()`; gabungkan seluruh `KecukupanKandidat`; `_pilih_view_name_final()` menerapkan tie-break (label M3.2 DITEMUKAN>SEBAGIAN dulu, lalu skor `KandidatView` tertinggi via `min()` dengan key tuple `(urutan_label, -skor)`) untuk memfinalkan `view_name_final` dari kandidat `cukup=True`, atau `None` kalau tidak ada.

**Temuan**
Tidak ada penyimpangan dari plan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 13.

**Commit:** `38eba02` — `feat(milestone-3.3): orkestrator per kebutuhan atomik + tie-break`

---

### Task 13 — Test Skenario Orkestrator

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan 6 test ke `tests/layers/retriever/test_kecukupan_struktural.py`: seluruh kandidat terselesaikan deterministik (`v_reservation_room_type_daily`, `punya_time_series=ya`, dibuktikan monkeypatch `_call_llm_fallback` raise — nol panggilan LLM genuinely nol, bukan cuma tidak diverifikasi); sebagian kandidat butuh fallback LLM (kombinasi `v_reservation_channel_daily` deterministik + `v_lookup_bookings` fallback dalam SATU batch kebutuhan atomik yang sama, membuktikan dua jalur hidup berdampingan); tidak ada kandidat cukup sama sekali (`v_properties_ref`, deterministik pasti tanpa LLM) → `view_name_final=None`; kandidat berlabel `tidak_ditemukan` dikecualikan total dari evaluasi (Keputusan 3); dan dua kasus tie-break (label DITEMUKAN menang meski skor lebih rendah; skor tertinggi menang saat label sama-sama DITEMUKAN).

**Temuan**
Helper `_buat_kandidat()`/`_buat_kecocokan_kandidat()` (ditulis Checkpoint 6) perlu diperluas menerima parameter `skor` opsional untuk mendukung skenario tie-break berbasis skor — perluasan aditif (default value dipertahankan), tidak meregresi test Checkpoint 6 yang sudah ada.

**Error/Kegagalan**
Satu kesalahan penulisan test (bukan bug kode produksi): draft awal `test_orkestrator_seluruh_deterministik_nol_panggilan_llm` sempat memanggil fungsi placeholder yang salah ketik (`SumberKeukupanKecukupan_or_deterministik()`) alih-alih assertion langsung `== SumberKeputusanKecukupan.DETERMINISTIK` — diperbaiki sebelum dijalankan, tidak pernah ter-commit dalam bentuk salah.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_kecukupan_struktural.py -v` → 34 passed (28 test Checkpoint 4+6 + 6 test baru).

**Commit:** `f63786e` — `test(milestone-3.3): skenario orkestrator per-item`

---

## Checkpoint 7 (lanjutan) — Hasil Run Promptfoo Nyata

**Percobaan 1** (4 skenario, `PROMPTFOO_PYTHON` diarahkan ke `.venv/`): **0/4 passed** — SELURUH assertion javascript gagal dengan error `Custom function must return a boolean, number, or GradingResult object. Got type undefined: undefined`. Root cause: replikasi PERSIS bug tooling M3.2 Checkpoint 14 — assertion `javascript` multi-baris Promptfoo TIDAK auto-return ekspresi terakhir (beda dari asumsi awal); body multi-baris dieksekusi APA ADANYA sebagai function body, butuh `return` eksplisit di baris terakhir. Diperbaiki: tambah `return` ke seluruh 6 assertion javascript di config.

**Temuan tambahan (dari respons LLM nyata di percobaan 1, sebelum assertion diperbaiki)**: S03 asli (`v_facility_room_status_daily`, ditandai `(snapshot)` di katalog) dijawab model `cukup=true` dengan alasan "grain kamar x tanggal (snapshot) memungkinkan agregasi status out-of-order per periode, sehingga dapat menghasilkan deret waktu untuk tren" — BERTENTANGAN dengan klasifikasi `grain_view.py` (`punya_time_series=tidak`) hasil Checkpoint 2. Investigasi lanjutan (baca ulang `DEFINISI_LENGKAP_VIEW` penuh untuk `v_facility_room_status_daily`/`v_hr_headcount_status_daily`/`v_hr_turnover_snapshot`) menemukan: klasifikasi awal MENYAMARATAKAN penanda `(snapshot)` di grain sebagai selalu berarti "tidak ada tren", padahal hanya `v_hr_turnover_snapshot` yang teks Fungsi-nya EKSPLISIT menyatakan "snapshot, tidak ada tren historis (data sumber tidak punya tanggal resign)" — `v_facility_room_status_daily` dan `v_hr_headcount_status_daily` TIDAK punya pernyataan serupa, dan `period_date` yang berulang tiap hari (nama `_daily`, sumber `fact_..._daily`) genuinely bisa dibaca sebagai state-per-hari yang membentuk tren, sesuai argumen model. **Diperbaiki**: `grain_view.py` direvisi (`punya_time_series` `tidak` → `tidak_pasti` untuk kedua view tersebut, `v_hr_turnover_snapshot` TETAP `tidak`), `test_grain_view.py` disesuaikan, skenario S03 promptfoo diganti dari `v_facility_room_status_daily` (ternyata genuinely ambigu, bukan trap case yang baik) ke `v_hr_turnover_snapshot` (ground truth tegas dari katalog).

**Percobaan 2** (setelah kedua perbaikan, dijalankan paralel dengan implementasi Checkpoint 8-10): **2/4 passed** — S02 (`v_reservation_room_type_daily`, grain jelas) dan S03 baru (`v_hr_turnover_snapshot`) lolos bersih. S01 (`v_lookup_bookings`, tren) GAGAL: model menjawab `cukup=true` dengan alasan "grain per reservasi memungkinkan agregasi jumlah booking per periode... dengan booking_date/check_in_date sebagai dimensi waktu" — temuan nyata: prompt v1 tidak menjelaskan batasan arsitektur bahwa `chatbot_api` TIDAK melakukan agregasi sisi klien, jadi model bernalar umum ala BI (tabel apa pun dengan kolom tanggal bisa di-trend) alih-alih memakai batasan sistem spesifik proyek ini. S04 tetap ERROR (timeout 300s, direplikasi identik percobaan 1 — diduga terkait `concurrency: 4` membebani worker Python lokal, bukan masalah skenario itu sendiri).

**Perbaikan prompt v2**: ditambah paragraf "Batasan sistem penting" (view diakses row-level tanpa agregasi tambahan, row-level individual TIDAK otomatis cukup untuk tren/perbandingan kecuali grain eksplisit sudah "entitas × periode").

**Percobaan 3** (prompt v2, `-j 2` mengganti concurrency 4→2 untuk mengatasi timeout): timeout S04 HILANG (durasi turun 6m42s→1m20s, mengonfirmasi dugaan resource contention, bukan bug skenario) — tapi **overcorrection baru**: S02 dan S04 (kandidat `v_reservation_room_type_daily`, grain genuinely jelas `properti × tipe kamar × tanggal`) kini GAGAL — model salah menafsirkan klarifikasi v2 sebagai "granularitas grain harus PERSIS cocok dengan kata dalam kebutuhan" (mis. kebutuhan sebut "3 bulan terakhir" → model minta grain sudah agregat BULANAN, menolak grain harian yang genuinely cukup untuk tren pada granularitas apa pun).

**Perbaikan prompt v3**: menambah penegasan eksplisit "granularitas periode BUKAN masalah" — filter rentang tanggal adalah urusan Query Engine (M3.4), bukan kriteria kecukupan grain.

**Percobaan 4** (prompt v3, `-j 2`): **4/4 passed (100%)** — S01 (`v_lookup_bookings` → `cukup=false`, alasan tepat menyebut row-level+tanpa agregasi), S02 (`v_reservation_room_type_daily` → `cukup=true`), S03 (`v_hr_turnover_snapshot` → `cukup=false`, alasan tepat menyebut pernyataan eksplisit katalog), S04 (kedua kandidat batch dinilai benar). Hasil dipush ke `prompt_eval_runs` (Supabase) — 4 baris terverifikasi lewat query langsung.

**Ringkasan siklus iterasi**: 4 percobaan real (bukan simulasi) menemukan DAN memperbaiki 3 masalah berbeda secara berurutan — bug tooling (assertion JS butuh `return` eksplisit, replikasi persis M3.2 Checkpoint 14), gap konten prompt v1 (tidak ada batasan arsitektur "tanpa agregasi klien"), dan overcorrection prompt v2 (granularitas periode disalahartikan sebagai syarat exact-match) — pola pengetatan bertahap yang konsisten budaya eval-driven proyek ini, bukan sekali coba lalu diterima apa adanya.

**Commit (perbaikan):** `936c9e5` — `fix(milestone-3.3): revisi klasifikasi grain snapshot berbasis bukti eval`; `d264aa6` — `fix(prompt-reliability): assertion js promptfoo butuh return eksplisit`; `4989c82` — `fix(prompts): koreksi overkonservatif granularitas periode`.

---

## Checkpoint 9 — Refactor Span M3.1 (Ekstraksi Logic Murni)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 14 — Ekstraksi `_kumpulkan_kandidat()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Mengekstrak logic BM25+fallback embedding murni (TANPA span pembungkus) dari `cari_kandidat_view()` ke `_kumpulkan_kandidat()` baru di `src/layers/retriever/retriever.py` — span anak `retriever.pencarian_embedding_fallback` TETAP dibuka di dalam fungsi ini (masih tanggung jawab M3.1), otomatis jadi anak span apa pun yang aktif di context pemanggil (parent-child OTel via contextvars). Menambahkan `_atribut_span_dari_hasil()` (turunkan `retrieval.candidates_count`/`fallback_terpicu`/`sumber_utama` dari `HasilPencarianKandidat`, satu tempat dipakai baik wrapper standalone maupun orkestrator M3.3). `cari_kandidat_view()` publik jadi wrapper tipis: buka span `retriever.cari_kandidat_view` (nama/atribut identik sebelum refactor), panggil `_kumpulkan_kandidat()`, set atribut dari `_atribut_span_dari_hasil()`, tutup span, return.

**Temuan**
Tidak ada penyimpangan — refactor murni sesuai desain di decisions.md Keputusan 4.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 15.

**Commit:** `73ec621` — `refactor(milestone-3.1): ekstraksi _kumpulkan_kandidat murni dari cari_kandidat_view`

---

### Task 15 — Regresi Penuh

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menjalankan `tests/layers/retriever/test_retriever.py` (5 test existing M3.1) TANPA menyentuh isinya sama sekali.

**Temuan**
`git diff --stat tests/layers/retriever/test_retriever.py` kosong (nol perubahan) — bukti murni refactor internal, bukan cuma klaim.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_retriever.py -v` → 5 passed, assertion identik sebelum/sesudah refactor. `pytest tests/layers/retriever/ tests/config/ -q` (regresi subpackage penuh) → 125 passed.

**Commit:** *(verifikasi tanpa perubahan kode, tidak ada commit terpisah — lihat Task 14)*

---

## Checkpoint 10 — Orkestrator Penutup Pipeline (M3.1→M3.2→M3.3)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 16 — Implementasikan `proses_retrieval_atomic_intent()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan `proses_retrieval_atomic_intent()` ke `kecukupan_struktural.py`: membuka span `retriever.cari_kandidat_view` (tracer `retriever.retriever`, reuse `_TRACER_NAME` dari `retriever.py` via import supaya tidak drift) → panggil `_kumpulkan_kandidat()` (M3.1 pure) → set atribut via `_atribut_span_dari_hasil()` (reuse fungsi Task 14, bukan duplikasi logic) → panggil `nilai_kecocokan_makna_atomic_intent()` (M3.2) → panggil `evaluasi_kecukupan_struktural_atomic_intent()` (M3.3) → `span.set_attribute("retrieval.selected_view", view_name_final or "")` sebelum span ditutup (string kosong sebagai pengganti `None`, OTel span attribute tidak menerima `None`).

**Temuan**
Tidak ada penyimpangan dari plan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 17.

**Commit:** `2f4f4e2` — `feat(milestone-3.3): orkestrator penutup pipeline retriever`

---

### Task 17 — Test Skenario Pipeline

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambahkan 2 test ke `tests/layers/retriever/test_kecukupan_struktural.py`: urutan panggilan M3.1(pure)→M3.2→M3.3 dibuktikan lewat list `urutan_panggilan` yang di-assert persis `["m3.1", "m3.2", "m3.3"]`, plus assertion objek yang diteruskan antar tahap adalah objek fixture YANG SAMA (`is`, bukan `==`) sehingga tidak ada transformasi tersembunyi di antara panggilan; kasus `view_name_final=None` tidak menyebabkan exception saat span attribute diisi.

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada — kedua test lolos pada percobaan pertama.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_kecukupan_struktural.py -v` → 36 passed. `pytest tests/layers/retriever/ tests/config/ -q` (regresi penuh subpackage) → tetap hijau.

**Commit:** `1b56a8b` — `test(milestone-3.3): skenario pipeline end-to-end`

---

## Checkpoint 11 — Verifikasi Jaeger Nyata (KK3)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 18 — Jalankan Pipeline Nyata + Verifikasi Trace

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Skrip verifikasi (`scratchpad/verify_m33_pipeline_spans.py`, tidak di-commit, mirror pola M3.1 Checkpoint 10) menjalankan `proses_retrieval_atomic_intent()` NYATA (Collector lokal aktif, `docker ps` dikonfirmasi `nirwana-otel-collector`/`nirwana-jaeger` `Up`) untuk dua skenario: (A) "tren okupansi Bali per tipe kamar 3 bulan terakhir" (domain `reservation`, jalur M3.3 deterministik penuh); (B) "tren status kamar out-of-order 3 bulan terakhir" (domain `facility`, jalur M3.3 memicu fallback LLM lewat `v_facility_room_status_daily` yang diklasifikasi `tidak_pasti` pasca-revisi Checkpoint 7). Trace diambil langsung dari Jaeger HTTP API (`GET /api/traces?service=nirwana-chatbot-m33-verify`), bukan hanya dibaca dari UI screenshot.

**Temuan (bukti nyata, dua trace_id berbeda)**
- **Trace A** (`8c8d2782bee629068063f9632a8c725d`, scenario `m33_deterministik_saja`): span `retriever.cari_kandidat_view` membawa `retrieval.candidates_count=5`, `retrieval.fallback_terpicu=False`, `retrieval.sumber_utama=bm25`, DAN `retrieval.selected_view=v_reservation_room_type_daily` — SEMUA pada span YANG SAMA. Dua span anak `"chat"` (M3.2 Langkah 1 Qwen3-32B + Langkah 2 DeepSeek V4 Pro) benar terparent ke span itu. TIDAK ada span `"chat"` fallback M3.3 (jalur deterministik murni, sesuai ekspektasi).
- **Trace B** (`c3ef710165a92c51006ee4cf2474bd5f`, scenario `m33_fallback_llm_terpicu`): span `retriever.cari_kandidat_view` yang SAMA membawa `retrieval.candidates_count=7` DAN `retrieval.selected_view=` (string kosong — genuinely tidak ada kandidat cukup, `v_facility_room_status_daily` dinilai `cukup=false` oleh fallback LLM). TIGA span anak `"chat"`: 2 milik M3.2 + 1 milik M3.3 fallback (`prompt.id=retriever.kecukupan_struktural_fallback`, `prompt.version=2` — mengonfirmasi run ini genuinely memakai prompt v2, bukan v1/v3, menyelesaikan ambiguitas timing proses background).

Kedua trace membuktikan KK3 secara LITERAL: `retrieval.selected_view` mengisi span `retriever.cari_kandidat_view` M3.1 yang SAMA (bukan span baru), terlihat konsisten di Jaeger untuk jalur deterministik MAUPUN fallback-terpicu — termasuk kasus `view_name_final=None` yang jujur tercermin sebagai string kosong (bukan disembunyikan).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`curl http://localhost:16686/api/traces?service=nirwana-chatbot-m33-verify` dua trace_id di atas, atribut dicek programatik (Python, bukan baca visual manual) — detail lengkap dicatat di atas.

**Commit:** *(skrip verifikasi murni operasional di scratchpad, tidak di-commit — konsisten preseden M3.1 Checkpoint 10 Task 22)*

---
