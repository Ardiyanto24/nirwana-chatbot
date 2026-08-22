# Decisions — Milestone 8.2: Test Gate — Unit & Integration

Dokumen ini mencatat setiap keputusan desain untuk Milestone 8.2, ditentukan sebelum implementasi dimulai lewat Plan Mode (satu putaran `AskUserQuestion` + diskusi konseptual lanjutan sebelum plan ditulis).

---

## Keputusan 1: Kredensial LLM/DB di CI — Full, Tapi Path-Filtered per Layer

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
Dari 705 test, ~48 (≈6.8%, 8 dari 12 "unit" M8.1) genuinely butuh `OPENROUTER_API_KEY`/`DATABASE_URL` asli (sudah py mekanisme `skipif` otomatis). Genuinely terbuka: haruskah CI menyediakan kredensial ini sama sekali, dan kalau ya, bagaimana caranya supaya tidak mahal/lambat/flaky (full suite pernah 400-500 detik di M8.1, dengan kegagalan LLM pra-eksisting berulang 3x).

**Keputusan yang Dipilih**
User ingin CI genuinely lengkap (kredensial dipakai nyata, bukan cuma diandalkan skip) TAPI test real-LLM/DB dipecah per-kelompok sesuai layer kode yang berubah — hanya grup yang relevan dengan perubahan yang genuinely dijalankan.

**Alasan**
Menyeimbangkan cakupan penuh (tidak ada test yang "dikorbankan" permanen) dengan biaya/waktu/risiko flaky yang proporsional terhadap perubahan aktual — mirip prinsip M8.4 (LLM Eval Gate) yang memang dirancang path-filtered, diterapkan lebih awal untuk `pytest`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tidak menyediakan kredensial sama sekali (skip otomatis semua 48 test di CI)** — direkomendasikan agent di awal (nol biaya/flaky), TAPI ditolak user yang ingin CI genuinely lengkap, bukan cakupan yang dikorbankan permanen.
- **Menyediakan kredensial, jalankan seluruh 48 test di setiap push tanpa filter** — ditolak; mewarisi biaya+waktu+flaky penuh tanpa mempertimbangkan relevansi perubahan.

**Dampak**
Menentukan seluruh arsitektur Checkpoint 3-5 (job `test-python-fast` vs `test-python-llm` path-filtered vs `test-gate` aggregator).

---

## Keputusan 2: Mekanisme Deteksi Layer Berubah — `dorny/paths-filter`

**Status:** Diputuskan sebelum implementasi (dari plan, diskusi konseptual sebelum `AskUserQuestion`/plan ditulis).

**Latar Belakang**
User eksplisit meminta penjelasan standar industri untuk "menjalankan sebagian test berdasarkan bagian kode yang berubah" sebelum memutuskan — bukan diasumsikan sepihak oleh agent.

**Keputusan yang Dipilih**
`dorny/paths-filter@v3` — step di awal workflow yang membaca diff, menghasilkan flag boolean per grup path yang didefinisikan eksplisit di config YAML.

**Alasan**
Paling umum dipakai untuk kasus "GitHub Actions, satu repo, jalankan job tertentu hanya kalau folder tertentu berubah" — matang, menangani edge case base-ref (push vs PR) yang kalau dibuat sendiri gampang salah, hasilnya eksplisit/bisa diaudit langsung dari config.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`pytest-testmon` (coverage-based)** — otomatis/adaptif (tidak basi kalau ada file baru), tapi ditolak karena kurang transparan ("magic" dari coverage, bukan daftar path eksplisit yang bisa dibaca manusia) dan butuh infra tambahan (database `.testmondata` di-cache antar-run).
- **Native `on: paths:` trigger GitHub Actions** — ditolak; forced tidak cocok, itu memfilter seluruh WORKFLOW (workflow tidak jalan sama sekali), bukan job individual dalam satu `ci.yml` yang harus tetap menjalankan job lain (ruff, golangci-lint, dst).
- **Tooling monorepo besar (Nx, Bazel, dst.)** — ditolak; overkill untuk skala satu repo Python+Go kecil ini, bukan monorepo puluhan package.

**Dampak**
Checkpoint 4 (job `test-python-llm`) dibangun di atas step `dorny/paths-filter@v3`.

---

## Keputusan 3: `go test ./...` Jadi Job CI Terpisah

**Sumber Paksaan**
`docs/02-implementation-plan/rancangan-ci-cd.md`, Milestone 8.2 Lingkup: "Menyambungkan `pytest tests/`... DAN `go test ./...`... sebagai *required check*."

**Keputusan yang Diikuti**
Job `go-test` baru di `ci.yml`, `working-directory: custom-exporter/supabaseexporter` (preseden lokasi persis job `golangci-lint` M8.1).

**Catatan Ketergantungan**
Menggabungkan ke job Python manapun akan mengaburkan sinyal kegagalan (Python vs Go) dan melanggar preseden satu-job-satu-toolchain M8.1.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kalimat KK sumber secara verbatim + preseden struktur job M8.1.

---

## Keputusan 4: Pemetaan Layer→File Test Bergerbang Identik Tabel 12 Unit M8.1

**Sumber Paksaan**
Inventaris nyata (`grep -rn "pytest.mark.skipif" tests/` + `grep -rlE "skipif.*(OPENROUTER_API_KEY|DATABASE_URL)"`) — 8 dari 12 unit M8.1 py file test bergerbang kredensial, batas foldernya identik dengan unit M8.1 (`src/layers/<nama>/`+`src/schemas/<terkait>.py`+`src/config/<terkait>.py`).

**Keputusan yang Diikuti**
Tabel pemetaan (lihat plan) memakai persis 8 grup itu (Context Resolution, Decomposition, Domain Gate, Query Engine, Verification Gate, Interpretation, Execution, Orchestration) + grup `shared` (`llm.py`/`prompts/loader.py`) untuk file cross-cutting.

**Catatan Ketergantungan**
Membuat pemetaan baru dari nol (bukan reuse unit M8.1) berisiko tidak konsisten dengan batas kepemilikan file yang sudah divalidasi nyata sebulan lalu.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by inventaris nyata + preseden struktur M8.1.

---

## Keputusan 5: Path-Filter di Level CI, Tidak Me-refactor Kode Test

**Sumber Paksaan**
Prinsip minimal-invasive change — cakupan milestone ini CI, bukan refactor test.

**Keputusan yang Diikuti**
Path-filter (config `dorny/paths-filter`) dan target file `pytest` di job `test-python-llm` ditulis di `ci.yml` saja. 18 file test yang sudah py `skipif` (module-level `pytestmark`/per-fungsi `@pytestmark_llm`/`@pytestmark_db`) TIDAK disentuh — dipertahankan apa adanya.

**Catatan Ketergantungan**
Me-refactor jadi pytest marker resmi (`@pytest.mark.llm`, didaftarkan `pyproject.toml`) akan menyentuh 18 file production test tanpa manfaat tambahan untuk tujuan milestone ini (path-filter CI-side sudah cukup) — risiko regresi tidak sepadan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Refactor ke pytest marker resmi lintas 18 file** — dipertimbangkan (lebih "pytest-idiomatic"), ditolak karena mengubah lebih banyak kode existing tanpa kebutuhan nyata dari KK sumber milestone ini.

---

## Keputusan 6: File Cross-Cutting (`llm.py`, `prompts/loader.py`) Memicu SEMUA Grup

**Sumber Paksaan**
Preseden "Support" unit M8.1 (Keputusan turunan tabel unit M8.1, verifikasi full-suite untuk perubahan lintas-layer).

**Keputusan yang Diikuti**
Grup `shared` di path-filter — kalau `src/config/llm.py` atau `src/prompts/loader.py` berubah, SEMUA 8 grup LLM dijalankan (union penuh), bukan cuma satu.

**Catatan Ketergantungan**
Perubahan model/provider config atau mekanisme render prompt genuinely bisa mempengaruhi SEMUA layer yang memanggil LLM — melewatkan grup manapun berisiko regresi lolos tanpa terdeteksi.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by sifat cross-cutting file itu sendiri + preseden M8.1.

---

## Keputusan 7: Perubahan `src/prompts/<layer>/**.md` Ikut Memicu Grup Layer yang Sama

**Sumber Paksaan**
Prompt adalah bagian perilaku LLM layer itu sendiri (isi instruksi yang dikirim ke model), bukan sekadar dokumentasi statis.

**Keputusan yang Diikuti**
Tiap grup path-filter menyertakan `src/prompts/<layer>/**` selain `src/layers/<layer>/**`.

**Catatan Ketergantungan**
Mengubah prompt tanpa mengubah kode Python bisa mengubah perilaku LLM signifikan (contoh nyata: revisi prompt narasi M4.4/M4.5) — kalau path-filter cuma memantau `.py`, perubahan prompt murni akan lolos tanpa test real-LLM sama sekali.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by sifat prompt sebagai bagian perilaku, bukan dokumentasi.

---

## Keputusan 8: Job Aggregator `test-gate` untuk Required Status Check

**Sumber Paksaan**
Keterbatasan teknis GitHub Actions: job yang di-skip via kondisi `if:` bisa membuat *required status check* menunggu tanpa pernah resolve (skip tidak selalu dihitung sebagai "success" eksplisit oleh branch protection) — pola aggregator job (`needs:` + `if: always()`) adalah mitigasi yang sudah dikenal luas untuk masalah ini.

**Keputusan yang Diikuti**
Job `test-gate` baru, `needs: [test-python-fast, go-test, test-python-llm]`, `if: always()`, memeriksa `needs.*.result` eksplisit. Job INI yang didaftarkan ke `required_status_checks` (Checkpoint 8), BUKAN `test-python-llm` langsung.

**Catatan Ketergantungan**
Mendaftarkan `test-python-llm` langsung sebagai required check berisiko PR macet permanen kalau job itu genuinely skip (union grup kosong) — kondisi yang justru SERING terjadi by design (PR yang tidak menyentuh layer manapun).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by keterbatasan teknis GitHub Actions itu sendiri.

---

## Keputusan 9: Agent Tidak Menambahkan GitHub Secret — User Menambahkan Sendiri

**Sumber Paksaan**
Aturan keamanan agent: memasukkan API key/kredensial ke sistem apa pun (termasuk GitHub Secrets) ada di daftar aksi terlarang, tanpa pengecualian meski user memberi izin eksplisit.

**Keputusan yang Diikuti**
Checkpoint 6 — Task 6 dikerjakan USER sendiri (`gh secret set OPENROUTER_API_KEY`/`DATABASE_URL`, nilai dari `.env` lokal). Agent hanya memverifikasi KEBERADAAN secret (`gh secret list`, bukan nilainya) sebelum lanjut Checkpoint 7+.

**Catatan Ketergantungan**
Checkpoint 7-10 (yang butuh kredensial genuinely ada untuk verifikasi nyata `test-python-llm`) tidak bisa dimulai sebelum Checkpoint 6 selesai oleh user.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by aturan keamanan agent yang tidak bisa dinegosiasikan.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Kredensial LLM/DB di CI — Full, Tapi Path-Filtered per Layer | A | Plan |
| 2 | Mekanisme Deteksi Layer Berubah — `dorny/paths-filter` | A | Plan |
| 3 | `go test ./...` Jadi Job CI Terpisah | B | Plan |
| 4 | Pemetaan Layer→File Test Bergerbang Identik Tabel 12 Unit M8.1 | B | Plan |
| 5 | Path-Filter di Level CI, Tidak Me-refactor Kode Test | B | Plan |
| 6 | File Cross-Cutting Memicu Semua Grup | B | Plan |
| 7 | Perubahan Prompt Ikut Memicu Grup Layer yang Sama | B | Plan |
| 8 | Job Aggregator `test-gate` untuk Required Status Check | B | Plan |
| 9 | Agent Tidak Menambahkan GitHub Secret | B | Plan |
