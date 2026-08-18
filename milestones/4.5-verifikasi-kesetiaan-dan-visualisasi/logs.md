# Logs — Milestone 4.5: Membangun Verifikasi Kesetiaan Data dan Penyusunan Visualisasi

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan, dengan satu tambahan wajar: menulis entri baru `docs/keputusan-tertunda.md` #4 (skema `DataVisualisasi` provisional) sesuai isi Keputusan 9 itu sendiri ("Dicatat eksplisit di `docs/keputusan-tertunda.md`") — bukan penyimpangan, murni menjalankan apa yang keputusan itu sendiri mewajibkan.

**Apa yang dilakukan**
Menulis `milestones/4.5-verifikasi-kesetiaan-dan-visualisasi/decisions.md` berisi 14 keputusan (seluruhnya Jenis B — forced/preseden, TIDAK ada Jenis A karena plan menyimpulkan tidak ada keputusan genuinely terbuka untuk milestone ini). Menambah entri #4 `docs/keputusan-tertunda.md` untuk skema `DataVisualisasi` provisional (Keputusan 9).

**Temuan**
Tidak ada temuan baru di luar yang sudah tercatat di plan.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual: seluruh 14 entri menyebut sumber paksaan eksplisit. Entri baru `docs/keputusan-tertunda.md` #4 konsisten format 3 entri sebelumnya (status, muncul di, konteks kemunculan, kenapa belum ditutup permanen, pemicu peninjauan ulang).

**Commit:** `808e835` — `docs(milestone-4.5): keputusan desain verifikasi kesetiaan dan visualisasi`

---

## Checkpoint 2 — Skema dan Konstanta Model

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 2 — Skema `HasilVerifikasiNarasi` + `DataVisualisasi`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambah `HasilVerifikasiNarasi` (mirror persis `HasilVerifikasiBentukRequest` M3.5, validator status↔lolos↔alasan) dan `DataVisualisasi` (`nilai_tunggal`/`deret`, validator memaksa tepat satu terisi sesuai label) ke `src/schemas/interpretation.py`.

**Temuan**
Tidak ada.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Pemanggilan manual: 3 kasus valid `HasilVerifikasiNarasi` (lolos=True, lolos=False+alasan, gagal_teknis) berhasil; 2 kasus valid `DataVisualisasi` (nilai_tunggal, tren/deret) berhasil; 2 kasus invalid (nilai_tunggal label tapi deret terisi; lolos=False tanpa alasan) benar-benar `raise pydantic.ValidationError`.

**Commit:** `a78ebff` — `feat(milestone-4.5): skema HasilVerifikasiNarasi + DataVisualisasi + konstanta model`

---

### Task 3 — `OPENROUTER_MODEL_VERIFIKASI_KESETIAAN`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menambah `OPENROUTER_MODEL_VERIFIKASI_KESETIAAN = "deepseek/deepseek-v4-pro"` + entri docstring ke `src/config/llm.py`.

**Temuan**
Tidak ada.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Import + validasi digabung dengan Task 2 dalam satu pemanggilan manual — semua berhasil.

**Commit:** `a78ebff` — `feat(milestone-4.5): skema HasilVerifikasiNarasi + DataVisualisasi + konstanta model`

---

## Checkpoint 3 — System Prompt Verifikasi Kesetiaan

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 4 — Tulis `src/prompts/interpretation/verifikasi_kesetiaan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis frontmatter (`id: interpretation.verifikasi_kesetiaan`, `version: 1`, `milestone: "4.5"`, `model_compat: ["deepseek/deepseek-v4-pro"]`) + body: penjelasan peran (menilai independen, tidak melihat proses generate), 5 kriteria bernomor persis dari Lingkup sumber (data hilang, status non-normal jujur, larangan klaim sebab-akibat, angka sesuai data asli, status terblokir spesifik), format output JSON `{"lolos": bool, "alasan": str|null}` mirror pola `verifikasi_bentuk_request.md` (M3.5).

**Temuan**
Tidak ada temuan tak terduga — isi prompt murni menerjemahkan 5 kriteria Lingkup M4.5 sumber ke instruksi eksplisit bernomor, mengikuti format JSON preseden verifier lain.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`load_prompt("interpretation.verifikasi_kesetiaan").render()` berhasil parse tanpa error. Checklist manual: kelima kriteria tersurat sebagai butir bernomor terpisah, format JSON output eksplisit dicontohkan.

**Commit:** `8efed77` — `feat(milestone-4.5): system prompt verifikasi kesetiaan`

---

## Checkpoint 4 — Implementasi `verifikasi_kesetiaan_narasi()`

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 5 — Implementasi `src/layers/interpretation/verifikasi_kesetiaan.py`

**Kesesuaian dengan plan:** Sesuai plan. Penyimpangan urutan operasional (bukan desain): implementasi module ini mengimpor `susun_data_visualisasi_semua()` dari `visualisasi.py` (Checkpoint 5) karena orkestrator `verifikasi_dan_susun_visualisasi()` (Task 7, Checkpoint 6) ditulis SEKALIGUS di file yang sama saat Checkpoint 4 — Checkpoint 5 (`visualisasi.py`) dikerjakan LEBIH DULU dari urutan plan supaya import tidak pecah, verifikasi ketiganya (Task 5-7) digabung dalam satu putaran pengujian nyata. Tidak mengubah bentuk akhir kode, murni urutan penulisan.

**Apa yang dilakukan**
Implementasi `_build_user_prompt()` (reuse `narasi._build_user_prompt()`, Keputusan 5), `_call_llm()` (`response_format=json_object`, `temperature=0`, `reasoning=high`), `_parse_response()` (mirror persis `_parse_response()` M3.5), `verifikasi_kesetiaan_narasi()` (span `chat`, `APIError`/`empty_choices`/`parse_error` semuanya→`GAGAL_TEKNIS` sebagai fallback aman — BEDA dari `susun_narasi()` M4.4 yang tidak punya fallback aman).

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Tiga panggilan LLM NYATA: (1) narasi dengan klaim sebab-akibat eksplisit ("MENYEBABKAN") terhadap dua data deskriptif independen → `lolos=False`, `alasan` mengutip persis "Kriteria 3" dan menyebut kata "MENYEBABKAN" dari narasi — tepat memenuhi KK sumber paling kritis. (2) Narasi jujur (tanpa klaim kausal) dengan data sama → `lolos=True`. (3) `APIError` disimulasikan (monkeypatch `_call_llm`) → `status=GAGAL_TEKNIS`, `lolos=None`, `alasan=None` — fallback aman, BUKAN exception diteruskan (beda `susun_narasi()` M4.4, sesuai desain karena verifier di sini PUNYA nilai fallback aman yang valid).

**Commit:** `46fbac0` — `feat(milestone-4.5): implementasi verifikasi_kesetiaan_narasi() + penyusunan visualisasi + orkestrator`

---

## Checkpoint 5 — Implementasi Penyusunan Data Visualisasi

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 6 — Implementasi `src/layers/interpretation/visualisasi.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan SATU koreksi skema yang ditemukan saat implementasi (dicatat eksplisit, bukan disembunyikan): validator `DataVisualisasi` versi awal (Checkpoint 2) terlalu ketat — memaksa label `nilai_tunggal` SELALU mengisi field `nilai_tunggal` (tidak boleh `deret`), padahal desain fallback-ambigu (sudah dicatat di plan Risiko & Mitigasi SEBELUM implementasi) butuh `deret` sebagai fallback untuk label `nilai_tunggal` juga saat ekstraksi ambigu. Validator diperbaiki: tepat satu dari `nilai_tunggal`/`deret` wajib terisi (independen dari label), TAPI 4 label selain `nilai_tunggal` tetap wajib `deret` (tidak ada fallback untuk itu, karena list selalu valid apa adanya).

**Apa yang dilakukan**
Implementasi `susun_data_visualisasi(package)` — label `nilai_tunggal` dengan `rows` PERSIS 1 baris 1 kolom → ekstrak scalar; kasus ambigu (>1 baris atau >1 kolom) → fallback `deret` (TIDAK menebak kolom mana "nilai"-nya); 4 label lain → `deret = rows` apa adanya (termasuk `rows=[]` → `deret=[]`, bukan error). `susun_data_visualisasi_semua()` batch wrapper.

**Temuan**
Bug skema ditemukan SEBELUM commit (lihat "Kesesuaian dengan plan" di atas) — validator Checkpoint 2 tidak mengakomodasi fallback ambigu yang SUDAH direncanakan eksplisit di plan Risiko & Mitigasi. Diperbaiki di `src/schemas/interpretation.py` sebagai bagian checkpoint ini (bukan checkpoint terpisah, karena murni koreksi implementasi terhadap desain yang SUDAH disetujui, bukan keputusan baru).

**Error/Kegagalan (jika ada)**
Percobaan pertama `susun_data_visualisasi()` dengan kasus ambigu (2 kolom) gagal `pydantic.ValidationError` karena validator Checkpoint 2 belum mengakomodasi fallback.

**Diagnosis dan Perbaikan (jika ada error)**
Validator `DataVisualisasi.bentuk_sesuai_label()` diperbaiki (lihat "Kesesuaian dengan plan").

**Hasil Verifikasi**
Pemanggilan manual 5 kasus: (1) `nilai_tunggal` 1 baris 1 kolom → scalar `0.82` benar; (2) `nilai_tunggal` ambigu (2 kolom) → fallback `deret` benar (bukan crash/tebak); (3) `tren` 3 baris → `deret` panjang 3; (4) `komposisi` `rows=[]` → `deret=[]`; (5) batch 2 item → 2 hasil. Seluruhnya sesuai ekspektasi.

**Commit:** `46fbac0` — `feat(milestone-4.5): implementasi verifikasi_kesetiaan_narasi() + penyusunan visualisasi + orkestrator`

---

## Checkpoint 6 — Orkestrator Gabungan

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 7 — `verifikasi_dan_susun_visualisasi()`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Implementasi `verifikasi_dan_susun_visualisasi()` di `verifikasi_kesetiaan.py` — panggil `verifikasi_kesetiaan_narasi()`, kalau `lolos is True` lanjut `susun_data_visualisasi_semua(packages)`, selain itu (`False`/`None`) kembalikan `visualisasi=None`. Return `tuple[HasilVerifikasiNarasi, list[DataVisualisasi] | None]` (diputuskan tuple, bukan schema baru `HasilInterpretasiAkhir` — dua nilai selalu dipakai bersamaan tapi tidak butuh validator silang, tuple cukup dan lebih sederhana, konsisten prinsip "jangan tambah abstraksi tanpa kebutuhan jelas").

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Panggilan nyata end-to-end DUA kali: (1) narasi lolos → `visualisasi` terisi 2 `DataVisualisasi` (satu per atomic intent), nilai scalar benar (`10`, `8`); (2) narasi TIDAK lolos (skenario klaim sebab-akibat) → `visualisasi=None`, dikonfirmasi TIDAK ada pemanggilan `susun_data_visualisasi_semua()` (return langsung setelah cek `lolos`).

**Commit:** `46fbac0` — `feat(milestone-4.5): implementasi verifikasi_kesetiaan_narasi() + penyusunan visualisasi + orkestrator`

---

## Checkpoint 7 — Unit Test

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 8-10 — Unit test verifikasi kesetiaan + visualisasi + orkestrator

**Kesesuaian dengan plan:** Sesuai plan, dengan penggabungan Task 10 (test orkestrator) ke `test_verifikasi_kesetiaan.py` alih-alih file terpisah — plan sendiri mencatat ini sebagai opsi eksplisit ("atau ditambahkan ke test_verifikasi_kesetiaan.py"), bukan penyimpangan.

**Apa yang dilakukan**
`test_verifikasi_kesetiaan.py` (13 test): `lolos=true`, `lolos=false`+alasan, `lolos=false` tanpa alasan dari LLM (fallback generik), `APIError`→`GAGAL_TEKNIS`, JSON rusak→`GAGAL_TEKNIS`, `empty_choices`→`GAGAL_TEKNIS`, atribut span lengkap, orkestrator (`lolos=True`→visualisasi terisi; `lolos=False`→visualisasi `None` DAN `susun_data_visualisasi_semua()` dikonfirmasi TIDAK dipanggil via spy; `GAGAL_TEKNIS`→visualisasi `None`; narasi disalin utuh ke hasil, parametrized 2 kasus). `test_visualisasi.py` (10 test): seluruh 5 label, kasus ambigu (multi-kolom, multi-baris), `rows=[]`, `atomic_intent_id` diteruskan, batch.

**Temuan**
Tidak ada temuan tak terduga — pola mock `_call_llm`+`_TracerRekam` dari `test_narasi.py`/`test_verifikasi_bentuk_request.py` (M3.5, tidak dibaca langsung tapi pola sudah dikenal dari M4.4) langsung applicable.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`.venv/Scripts/python.exe -m pytest tests/layers/interpretation/ -v` — 30/30 PASSED (8 dari M4.4 + 22 baru M4.5).

**Commit:** `f6d9dbe` — `test(milestone-4.5): unit test verifikasi kesetiaan + visualisasi`

---

## Checkpoint 8 — Rancangan dan Eksekusi Eval

**Mulai:** 2026-08-18 · **Selesai:** 2026-08-18

### Task 11 — Tulis `evals/4.5-verifikasi-kesetiaan-dan-visualisasi/rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan (10 skenario, sesuai target "~10-12" plan). Cakupan LEBIH SEMPIT dari M4.4 karena `susun_data_visualisasi()` deterministik sudah tuntas via unit test (Checkpoint 7) — eval di sini murni untuk `verifikasi_kesetiaan_narasi()`.

**Apa yang dilakukan**
Menulis 10 skenario (S01-S10): S01/S02 klaim sebab-akibat (KK paling kritis, + kontrol negatif), S03 data hilang, S04 angka dikarang, S05/S06 status sebagian disamarkan vs jujur, S07/S08 status terblokir digeneralisasi vs spesifik, S09 ditolak_otorisasi disamarkan gagal_teknis, S10 stress test kompleks 4-status seluruhnya jujur (kontrol over-triggering).

**Temuan**
Tidak ada temuan tak terduga — struktur pasangan uji/kontrol (mis. S05 uji vs S06 kontrol) dipilih supaya setiap pelanggaran yang diuji punya versi jujur berdampingan sebagai pembanding langsung, mempertajam interpretasi hasil.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Tidak ada eksekusi di checkpoint ini (murni dokumen desain). Review manual: KK1 sumber (klaim sebab-akibat) punya 2 skenario eksplisit (S01+S02); kelima kriteria prompt masing-masing punya minimal 1 skenario uji.

**Commit:** `0aa5f78` — `docs(milestone-4.5): rancangan eval verifikasi kesetiaan`

---

### Task 12 — `run_eval.py` + Eksekusi Nyata

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `evals/4.5-verifikasi-kesetiaan-dan-visualisasi/run_eval.py` — 10 skenario (S01-S10) sesuai `rancangan.md`, reuse `verifikasi_kesetiaan_narasi()` produksi langsung. Dijalankan nyata DUA KALI: run 1 (prompt v1) menemukan 1 REVIEW nyata (S06, bukan false-negative alat ukur); prompt diperbaiki v1→v2 (lihat Task 13); run 2 (prompt v2) — 10/10 sesuai ekspektasi.

**Temuan**
**S06 (run 1) adalah temuan nyata, bukan artefak skenario**: narasi kontrol yang meniru PERSIS pola kalimat sah yang diinstruksikan `narasi.md` M4.4 sendiri ("data ditandai perlu perhatian, sehingga mungkin belum akurat") ditolak verifier v1 karena Kriteria 3 (larangan klaim sebab-akibat) memicu pada kata "sehingga" tanpa membedakan konteks (klaim antar-data vs penjelasan keterbatasan satu hasil). Ditangani sebagai perbaikan prompt di tengah checkpoint (Task 13), bukan ditunda.

**Error/Kegagalan (jika ada)**
Run 1: S06 `match=False` (`lolos=False`, ekspektasi `True`) — dianalisis Task 13.

**Diagnosis dan Perbaikan (jika ada error)**
Lihat Task 13.

**Hasil Verifikasi**
Run 2 (final, prompt v2): 10/10 skenario sesuai ekspektasi. Payload run 2 (final) tersimpan `payloads/S01.json`..`S10.json` — payload run 1 TIDAK disimpan terpisah (ditimpa run 2, konsisten pola project "payload final apa adanya", perbedaan run 1 vs run 2 didokumentasikan naratif di `audit.md` alih-alih menyimpan dua set file).

**Commit:** `70cfb28` — `test(milestone-4.5): eksekusi eval + audit verifikasi kesetiaan (termasuk temuan+perbaikan prompt v2)`

---

### Task 13 — Tulis `audit.md`

**Kesesuaian dengan plan:** Sesuai plan, dengan SATU langkah tambahan di tengah (bukan penyimpangan cakupan): perbaikan prompt `verifikasi_kesetiaan.md` v1→v2 (`fix(milestone-4.5)`, commit terpisah dari eval) dilakukan SEBELUM `audit.md` final ditulis, supaya audit mencerminkan hasil akhir yang benar-benar terverifikasi — bukan mendokumentasikan kegagalan yang sudah diperbaiki seolah masih berlaku.

**Apa yang dilakukan**
Menulis `audit.md`: tabel ringkasan run 1 vs run 2, analisis mendalam 5 skenario penting (S01/S02 pasangan positif-negatif KK inti; **S06 sebagai temuan nyata utama** — akar masalah, perbaikan, verifikasi ulang terpisah sebelum re-run penuh; S07/S08 status terblokir; S09 dimensi di luar 5 kriteria literal; S10 stress test kompleks), "Temuan Pola" (4 poin) dan "Rekomendasi" (3 poin, termasuk kewajiban Checkpoint 9 memakai prompt v2).

**Temuan**
Tidak ditemukan satu pun false-negative (kasus pelanggaran nyata yang lolos keliru) di seluruh 10 skenario × 2 run — bias verifier (sebelum diperbaiki) condong ke arah OVER-KETAT, bukan under-ketat, arah yang lebih aman untuk sistem yang wajib jujur ke user meski tetap butuh perbaikan presisi.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`audit.md` selesai, KK sumber M4.5 (klaim sebab-akibat) terbukti lolos S01+S02 (pasangan positif-negatif pada data identik) di kedua run.

**Commit:** `70cfb28` — `test(milestone-4.5): eksekusi eval + audit verifikasi kesetiaan (termasuk temuan+perbaikan prompt v2)`

---
