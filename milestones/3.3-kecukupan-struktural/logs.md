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
