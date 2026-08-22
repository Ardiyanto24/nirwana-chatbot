# Decisions — Milestone 8.4: LLM Eval Gate (Promptfoo → CI)

Dokumen ini mencatat setiap keputusan desain untuk Milestone 8.4, ditentukan sebelum implementasi dimulai lewat Plan Mode (satu putaran `AskUserQuestion`, didahului riset agent Explore + bacaan langsung `prompt_reliability/`, `rancangan-manajemen-prompt.md`, dan `ci.yml` existing).

---

## Keputusan 1: Filter Path Per-File Presisi (17 Filter Individual)

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
17 config `promptfooconfig.yaml` mapping 1:1 bersih ke 17 file `src/prompts/**/*.md` (dikonfirmasi riset — tidak ada orphan di kedua arah). Genuinely terbuka: filter CI dibangun per-file (presisi, hanya config yang relevan berjalan) atau reuse grup layer M8.2 (`changes` job, 6 grup, lebih kasar — mengubah 1 prompt domain_gate akan menjalankan SEMUA 4 config domain_gate).

**Keputusan yang Dipilih**
Filter per-file — 17 filter individual (satu per pasangan prompt/config), job `changes-prompts` BARU, TIDAK reuse/extend job `changes` M8.2.

**Alasan**
Output KK sumber M8.4 eksplisit menyebut "kontrol biaya" (Promptfoo menghabiskan token LLM sungguhan per skenario, beda dari `pytest` M8.2 yang gratis) — filter presisi meminimalkan config yang tidak relevan ikut jalan. Kutipan contoh KK1 sumber sendiri ("perubahan `identifikasi.md` memicu job ini menjalankan `identifikasi.promptfooconfig.yaml`") juga selaras presisi per-file, bukan per-layer.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse/extend job `changes` M8.2 (grup per-layer)** — ditolak; lebih sederhana (tidak menambah 17 filter key baru) dan konsisten pola M8.2, tapi boros biaya LLM (config yang tidak relevan ikut jalan) dan mencampur granularitas dua konsumen berbeda (unit test layer-level vs eval prompt file-level) dalam satu step filter.

**Dampak**
Checkpoint 3 (`changes-prompts`, 17+1 filter key) dan Checkpoint 4 (`prompt-eval`, `if:` OR 18 output) — job filter dan job eval keduanya BARU, terpisah total dari `changes`/`test-python-llm` M8.2.

---

## Keputusan 2: Gap Retriever M8.2 — Terpenuhi Native, Bukan Perubahan ke Job M8.2

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`), DIKOREKSI oleh riset lanjutan sebelum plan ditulis.

**Latar Belakang**
Riset awal (agent Explore) menduga job `changes`/`test-python-llm` (M8.2) tidak pernah punya grup `retriever` meski layer itu py 3 prompt+config Promptfoo nyata — diajukan ke user sebagai potensi gap untuk "diperbaiki sekarang atau dibiarkan". User memilih "diperbaiki sekarang". Riset LANJUTAN (sebelum plan final ditulis) menemukan premis itu SEBAGIAN keliru: `tests/layers/retriever/` (unit test pytest M8.2) genuinely 100% ter-mock (`monkeypatch _call_llm_generate`/`_call_llm_verifikasi`, dikonfirmasi grep `pytestmark_llm` NIHIL di folder itu, docstring `test_kecocokan_makna.py` baris 8 eksplisit menyatakan "TANPA [real API call]") — artinya `test-python-fast` (baseline, TANPA `OPENROUTER_API_KEY`) SUDAH mencakup 100% test retriever, TIDAK ADA gap nyata di sisi job `test-python-llm` untuk retriever.

**Keputusan yang Dipilih**
TIDAK mengubah job `changes`/`test-python-llm` M8.2 sama sekali. Gap yang REAL (3 config retriever butuh path-filter) diselesaikan native lewat cakupan 17-filter Keputusan 1 di atas (`retriever_kecocokan_makna_generate`, `retriever_kecocokan_makna_verifikasi`, `retriever_kecukupan_struktural_fallback` — 3 dari 17 filter M8.4 sendiri).

**Alasan**
Jawaban user ("perbaiki sekarang") tetap dihormati secara substantif — retriever TIDAK dibiarkan tanpa path-filter — tapi implementasinya menyesuaikan fakta yang ditemukan riset lanjutan, bukan memaksakan perubahan ke job M8.2 yang ternyata tidak py gap nyata. Mengubah job M8.2 tanpa gap nyata untuk diperbaiki akan jadi perubahan tanpa dasar (berlawanan prinsip "jangan mengasumsikan detail teknis yang sengaja terbuka" — di sini malah sebaliknya, mengasumsikan gap yang ternyata tidak ada).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tetap tambah grup `retriever` ke job `changes`/`test-python-llm` M8.2 meski tidak ada gap nyata** — ditolak; akan jadi perubahan kosmetik tanpa manfaat fungsional (tidak ada test yang butuh `OPENROUTER_API_KEY` di folder itu untuk di-path-filter), berisiko menambah kerumitan `ci.yml` tanpa alasan konkret.

**Dampak**
`ci.yml` job `changes`/`test-python-llm` M8.2 TIDAK disentuh sama sekali oleh M8.4. Cakupan retriever sepenuhnya lewat 3 filter di `changes-prompts` (Checkpoint 3).

---

## Keputusan 3: Gate 100% Lolos Wajib (Bukan Threshold Persentase)

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
`rancangan-ci-cd.md` Bagian Output M8.4 menyebut "gate berdasar threshold pass-rate" — tapi riset mengonfirmasi TIDAK ADA satu pun dari 17 config py field `threshold`/`defaultTest` numerik hari ini; assertion Promptfoo murni pass/fail per skenario, "pass rate" yang pernah disebut di `logs.md` historis (mis. "7/8 lolos") murni pelaporan manusia, bukan gate YAML. Genuinely terbuka: implementasikan gate 100% (exit code Promptfoo apa adanya) atau bangun mekanisme threshold persentase baru (mis. lolos kalau ≥90%).

**Keputusan yang Dipilih**
Gate 100% lolos wajib — job gagal kalau ADA satu skenario gagal di config manapun yang dijalankan, memakai exit code `promptfoo eval` apa adanya, TANPA kode parsing/threshold tambahan.

**Alasan**
Konsisten realita config hari ini (tidak ada satu pun yang didesain dengan toleransi kegagalan) — menambah threshold persentase custom akan jadi keputusan arsitektur baru tanpa preseden atau angka yang bisa dipertanggungjawabkan (kenapa 90% dan bukan 80%?). Assertion di tiap config (`is-json`, `javascript`, dll.) sudah dirancang sebagai pemeriksaan biner (benar/salah) sejak M1.3-M3.2, bukan skor bertingkat.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Threshold persentase (mis. lolos kalau ≥90% skenario per config)** — ditolak; butuh menentukan angka toleransi tanpa dasar/preseden, plus kode parsing output JSON tambahan (kompleksitas baru) untuk manfaat yang tidak jelas (config manapun yang punya skenario gagal 1x tetap layak diselidiki, bukan "cukup diabaikan asal masih di atas threshold").

**Dampak**
`prompt_reliability/run_and_push.py` (Checkpoint 2) tidak perlu logic parsing pass-rate — cukup propagate exit code `npx promptfoo eval` apa adanya ke caller.

---

## Keputusan 4: Push Hasil ke Supabase (`prompt_eval_runs`) Masuk Cakupan Sekarang

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
`rancangan-manajemen-prompt.md` Bagian 6 eksplisit menyebut `push_results.py` "dijalankan setelah tiap `promptfoo eval`, baik manual maupun (nanti) dari CI" — menandakan niat arsitektur asli MENCAKUP push otomatis dari CI. Tapi `rancangan-ci-cd.md` (dokumen scope M8.4 sendiri) TIDAK eksplisit mensyaratkan push sebagai bagian Kriteria Keberhasilan — genuinely terbuka apakah realisasi "nanti dari CI" itu masuk cakupan M8.4 atau ditunda.

**Keputusan yang Dipilih**
Masuk cakupan sekarang — `prompt_reliability/run_and_push.py` (Checkpoint 2, BARU) memanggil `push_results.push_results()` langsung (import Python, bukan subprocess CLI kedua) untuk SETIAP config yang dievaluasi CI, apa pun hasilnya (lolos maupun gagal — riwayat gagal justru paling bernilai diaudit di `prompt_eval_runs`).

**Alasan**
Data yang dibutuhkan (`prompt_id`, `model` dari YAML config; `version` dari `src.prompts.loader.load_prompt()`) sudah tersedia programatik TANPA tabel hardcode — biaya implementasi tambahan rendah dibanding manfaat merealisasikan penuh niat arsitektur yang sudah lama tertulis tapi belum pernah dieksekusi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Ditunda — M8.4 murni gate (jalankan+lolos/gagal), tanpa push** — ditolak; KK sumber M8.4 tetap terpenuhi tanpa push (jadi bukan forced), tapi menunda berarti mengabaikan langkah yang murah untuk dikerjakan bersamaan dan meninggalkan `push_results.py` tetap manual-only tanpa alasan kuat.

**Dampak**
Checkpoint 2 membangun wrapper baru (bukan sekadar memanggil `npx promptfoo eval` langsung dari `ci.yml`) — kompleksitas tambahan dibanding gate murni, tapi terbungkus rapi di satu file Python yang bisa diuji lokal sebelum dipakai CI. Butuh `DATABASE_URL` (sudah ada, secret M8.2) di job `prompt-eval`.

---

## Keputusan 5: Job `changes-prompts`/`prompt-eval`/`prompt-eval-gate` — Tiga Job Baru Terpisah dari M8.2/M8.3

**Sumber Paksaan**
KK sumber M8.4 ("Job CI baru") + preseden Keputusan 8 M8.2 (gotcha skip-vs-required-check untuk job yang genuinely bisa skip) + preseden Keputusan 3 M8.3 (pemisahan sinyal kegagalan supaya tidak diaburkan).

**Keputusan yang Diikuti**
Tiga job baru: `changes-prompts` (paths-filter 17+1 key), `prompt-eval` (jalankan config relevan), `prompt-eval-gate` (aggregator skip-tolerant, `if: always()`) — TIDAK memperluas job `changes`/`test-python-llm`/`test-gate` M8.2 maupun `rbac-regression` M8.3.

**Catatan Ketergantungan**
`prompt-eval` genuinely bisa SKIP (union 17 filter kosong — kondisi PALING UMUM, sebagian besar PR tidak menyentuh prompt) sehingga butuh aggregator skip-tolerant persis seperti `test-python-llm`/`test-gate` (M8.2) — tapi tetap job/aggregator TERPISAH dari `test-gate` supaya pesan gagal "unit test Python gagal" tidak tercampur "prompt reliability gagal" (dua kelas kegagalan berbeda makna, mirror alasan `rbac-regression` M8.3 dipisah dari `test-gate`).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Extend aggregator `test-gate` M8.2 (tambah `prompt-eval` ke `needs:`-nya)** — ditolak; nama "test-gate" secara semantik terikat pytest/go test, mencampur eval Promptfoo (tool berbeda total, biaya berbeda total) ke situ mengaburkan makna pesan gagal saat dibaca sekilas dari daftar checks PR.

---

## Keputusan 6: Wrapper `run_and_push.py` — Extract Metadata Programatik, Bukan Tabel Hardcode

**Sumber Paksaan**
Ketersediaan `src.prompts.loader.load_prompt(prompt_id).version` (sudah ada sejak Fase 2 Manajemen Prompt) + prinsip project "hindari duplikasi/state yang bisa drift" (preseden Keputusan 4 M8.3 — matriks `role_permissions` dipanggil nyata, bukan snapshot statis).

**Keputusan yang Diikuti**
`run_and_push.py` menerima 1 path config sebagai argumen, extract `prompt_id`+`model` dari `providers[0].config` YAML config itu sendiri (`yaml.safe_load`), extract `version` via `load_prompt(prompt_id).version` (baca live dari frontmatter `src/prompts/`), TIDAK ada tabel hardcode config→prompt_id/version/model manapun di sisi CI.

**Catatan Ketergantungan**
Tabel hardcode akan basi diam-diam setiap kali prompt di-bump versi (praktik project yang wajib per konvensi `prompt_reliability/README.md`) — sumber kebenaran yang benar adalah file itu sendiri, bukan salinan manual di CI.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by ketersediaan `load_prompt()` yang sudah menyediakan data ini tanpa kerja tambahan.

---

## Keputusan 7: Reuse Secret `OPENROUTER_API_KEY`+`DATABASE_URL`, Node Setup Baru

**Sumber Paksaan**
Preseden M8.2 (kedua secret sudah ada, GitHub secret least-privilege sudah diprovisioning) + fakta `prompt_reliability/` adalah package Node PERTAMA di repo (tidak ada root `package.json`, `node_modules/` gitignored, `package-lock.json` ter-track).

**Keputusan yang Diikuti**
Reuse `secrets.OPENROUTER_API_KEY`+`secrets.DATABASE_URL` apa adanya (tidak ada secret baru). `actions/setup-node@v4` (Node LTS) ditambah PERTAMA KALI ke `ci.yml`, `working-directory: prompt_reliability` + `npm ci` (bukan `npm install`, memakai `package-lock.json` yang sudah ter-commit).

**Catatan Ketergantungan**
Tidak ada dasar untuk secret terpisah — kredensial LLM sama persis dipakai jalur produksi (`src/config/llm.py`), bukan kredensial berbeda untuk testing.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by struktur `prompt_reliability/` yang sudah ada.

---

## Keputusan 8: `timeout-minutes` Eksplisit + `PROMPTFOO_CACHE_PATH` + Concurrency Rendah

**Sumber Paksaan**
`docs/keterbatasan-diterima.md` #7 (LLM hang berkepanjangan tanpa exception, recurrence berulang M5.1/M7.16/M7.17 — pola project yang SUDAH terbukti, bukan risiko hipotetis) + Output KK sumber M8.4 ("dengan caching (`PROMPTFOO_CACHE_PATH`) dan concurrency limit untuk kontrol biaya").

**Keputusan yang Diikuti**
Job `prompt-eval` diberi `timeout-minutes` eksplisit (nilai konkret dikunci Checkpoint 4 berdasar estimasi worst-case 17 config berurutan). `PROMPTFOO_CACHE_PATH` diarahkan ke direktori yang di-restore lewat `actions/cache@v4` (key statis per-OS). Flag concurrency `npx promptfoo eval` diset RENDAH — nama flag persis diverifikasi empiris `--help` di Checkpoint 2 sebelum dikunci (bukan diasumsikan `-j`/`--max-concurrency` tanpa cek).

**Catatan Ketergantungan**
Tanpa `timeout-minutes` eksplisit, job berpotensi menggantung tanpa batas persis seperti insiden #7 yang sudah berulang kali menghambat sesi kerja lain di project ini — pola mitigasi (batas atas eksplisit, bukan usaha "mencegah" hang yang di luar kendali) sudah jadi preseden project sejak `src/config/llm.py` (`timeout=90.0`).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by riwayat insiden nyata #7 yang sudah berulang di 3 milestone berbeda.

---

## Keputusan 9: PR Percobaan Pakai Branch Throwaway (Bukan Bump Version Prompt Produksi Permanen)

**Sumber Paksaan**
Preseden M8.1-8.3 (seluruh PR percobaan pakai branch sementara, ditutup tanpa merge, dihapus).

**Keputusan yang Diikuti**
Checkpoint 9 (bukti presisi filter) dan Checkpoint 10 (bukti sengaja-gagal) sama-sama pakai branch throwaway — perubahan prompt (termasuk bump `version` frontmatter) TIDAK PERNAH mendarat permanen di `main` hanya demi pembuktian CI.

**Catatan Ketergantungan**
Prompt RBAC-sensitif (`domain_gate/identifikasi.md`, dipakai KK2 sumber sebagai contoh) tidak boleh punya riwayat versi yang tercemar perubahan artifisial murni untuk testing — versi prompt production harus mencerminkan perubahan konten yang genuinely dimaksudkan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden konsisten 3 milestone sebelumnya + risiko mencemari riwayat versi prompt produksi.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Filter Path Per-File Presisi (17 Filter) | A | Plan |
| 2 | Gap Retriever M8.2 — Terpenuhi Native | A | Plan |
| 3 | Gate 100% Lolos Wajib | A | Plan |
| 4 | Push Hasil ke Supabase Masuk Cakupan | A | Plan |
| 5 | 3 Job Baru Terpisah dari M8.2/M8.3 | B | Plan |
| 6 | Wrapper Extract Metadata Programatik | B | Plan |
| 7 | Reuse Secret + Node Setup Baru | B | Plan |
| 8 | `timeout-minutes`+Cache+Concurrency | B | Plan |
| 9 | PR Percobaan Branch Throwaway | B | Plan |
