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

## Keputusan 10: `DATABASE_URL` Disediakan Juga ke `test-python-fast` — Hanya `OPENROUTER_API_KEY` yang Genuinely Path-Filtered

**Status:** Ditemukan di tengah implementasi pada Checkpoint 3.

**Latar Belakang**
Saat memverifikasi job `test-python-fast` (rencana awal: TANPA kredensial apa pun), `pytest tests/` tanpa `DATABASE_URL` menghasilkan **27 test GAGAL** (bukan skip bersih) di `tests/layers/test_input_layer.py`+`tests/orchestration/test_turn_pipeline.py`, PLUS 1 collection ERROR di `tests/test_main.py` yang menghentikan seluruh proses collection. Investigasi: `src/config/roles.py::load_valid_roles()` (migrasi ke database sejak M1.5) dipanggil dari validasi `role_title` di `TurnPayload` — dampaknya jauh lebih luas dari 8 grup yang sudah dipetakan (Keputusan 4), mencakup Input Layer, Orchestration (via `TestClient`/`proses_turn()`), dan `test_main.py` — bukan sekadar "8 unit yang py test bergerbang eksplisit".

**Keputusan yang Dipilih**
`test-python-fast` (baseline, SELALU jalan) diberi `DATABASE_URL` sebagai secret, TAPI TETAP TANPA `OPENROUTER_API_KEY`. Diverifikasi lokal (`OPENROUTER_API_KEY="" uv run pytest tests/`, `DATABASE_URL` asli dari `.env`): **670 passed, 35 skipped, 17.33 detik** — nol kegagalan, jauh lebih cepat dari full suite (400-500 detik saat LLM ikut jalan).

**Alasan**
`DATABASE_URL` (Postgres/Supabase) CEPAT dan TIDAK terbukti flaky — beda kualitatif dari `OPENROUTER_API_KEY` yang sudah 3x terbukti tidak stabil sepanjang M8.1 (`docs/keterbatasan-diterima.md` #7). Path-filtering seharusnya menyasar sumber biaya/waktu/flakiness yang GENUINE (panggilan LLM), bukan seluruh kredensial secara membabi buta. Menyediakan `DATABASE_URL` ke baseline juga menutup 27+1 test yang SEBELUMNYA akan salah dilaporkan gagal (bukan "tidak relevan dengan perubahan", tapi genuinely butuh DB untuk validasi role yang sudah jadi bagian arsitektur sejak M1.5).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tetap TANPA kredensial apa pun di `test-python-fast` (rencana asli)** — ditolak setelah bukti nyata: menghasilkan 27 test gagal + 1 collection error yang akan membuat gate SELALU merah untuk PR manapun, termasuk yang tidak menyentuh Input Layer/Orchestration sama sekali — bukan sinyal kualitas kode, murni artefak kredensial hilang.
- **Perlakukan Input Layer/Orchestration/`test_main.py` sebagai grup path-filter baru (mirip 8 grup lain)** — dipertimbangkan, ditolak karena `DATABASE_URL` sendiri genuinely tidak mahal/flaky (beda `OPENROUTER_API_KEY`) — filtering hanya bernilai untuk yang benar-benar constrained (biaya API, waktu, keandalan).

**Dampak**
Checkpoint 6 (user menambahkan secret) TETAP menambahkan KEDUA secret bersamaan (tidak berubah urutan), tapi job assignment berubah: `test-python-fast` sekarang butuh `DATABASE_URL` (bukan genuinely "tanpa kredensial" seperti draf plan awal). Daftar SKIP presisi (`pytest tests/ -v -rs` dengan `DATABASE_URL` asli, `OPENROUTER_API_KEY=""`) dikonfirmasi **35 test**, TAPI tersebar hanya **5 grup** (bukan 8 seperti tabel plan awal) — `verification_gate` (`test_verifikasi_gate.py`) dan `orchestration` (`test_riwayat_percakapan.py`) TIDAK py sisa test bergerbang sama sekali (murni DB-gated, sekarang tercakup baseline); `execution` (`test_penyimpanan_paket_integrasi.py`) py 1 skip TAPI alasannya BUKAN kredensial ("kegagalan DB nyata sengaja tidak disimulasikan otomatis di sini" — skip permanen sengaja, tidak relevan untuk path-filter). Tabel pemetaan Checkpoint 4 direvisi jadi 5 grup: `context_resolution`(8), `decomposition`(4), `domain_gate`(19), `query_engine`(1), `interpretation`(2) = 34 test genuinely `OPENROUTER_API_KEY`-gated.

---

## Keputusan 11: Bug Nyata Ditemukan+Diperbaiki — `test_400_lalu_200_di_revisi_kedua_berhasil` Lupa Mock `panggil_meta_chatbot_api`

**Status:** Ditemukan di tengah implementasi pada Checkpoint 7 (run CI nyata pertama).

**Latar Belakang**
Run CI nyata pertama (`32558796535`) menunjukkan `test-python-fast` GAGAL — 1 test (`tests/layers/execution/test_klasifikasi_respons_revisi.py::test_400_lalu_200_di_revisi_kedua_berhasil`) genuinely memanggil `get_chatbot_api_base_url()` NYATA (bukan mock), meledak `RuntimeError: CHATBOT_API_BASE_URL tidak diset`. Ini kredensial KETIGA (di luar `OPENROUTER_API_KEY`/`DATABASE_URL` yang sudah dipetakan) yang genuinely tidak mungkin disediakan di CI cloud — `chatbot_api` adalah instance LOKAL milik user (`localhost`), tidak bisa dijangkau runner GitHub Actions.

**Investigasi:** File ini (`test_klasifikasi_respons_revisi.py`) py docstring eksplisit "modul ini TIDAK menyentuh LLM/HTTP sama sekali" — tapi test yang gagal genuinely mencapai `StatusEksekusi.BERHASIL`, yang membuat `eksekusi_atomic_intent()` lanjut memanggil `panggil_meta_chatbot_api()` (fitur `_meta` M4.2 revisit, 2026-08-17). File SAUDARA (`test_klasifikasi_respons.py`) sudah py helper `_patch_meta_tidak_diketahui()` yang di-mock default untuk SETIAP test yang mencapai BERHASIL — tapi `test_klasifikasi_respons_revisi.py` py `_patch_raw()` SENDIRI (duplikat, bukan reuse) yang TIDAK PERNAH diperbarui mengikuti revisit yang sama. Gap maintenance murni: revisit M4.2 hanya menyentuh satu dari dua helper duplikat.

**Keputusan yang Dipilih**
Perbaiki di tempat: tambah `_patch_meta_tidak_diketahui()` (mirror persis `test_klasifikasi_respons.py`) ke `test_klasifikasi_respons_revisi.py`, panggil di SATU-SATUNYA test yang genuinely mencapai `BERHASIL` (`test_400_lalu_200_di_revisi_kedua_berhasil` — 4 test lain di file yang sama pakai `StatusEksekusi.BERHASIL` cuma sebagai NILAI MOCK ANTARA, bukan hasil akhir, sehingga tidak pernah memanggil `panggil_meta_chatbot_api()`).

**Alasan**
Ini genuinely bug pre-existing (gap maintenance dari M4.2 revisit), bukan sesuatu yang M8.2 "ciptakan" — Keputusan 5 (path-filter tidak menyentuh kode test) tentang TIDAK me-refactor mekanisme skipif existing, BUKAN larangan memperbaiki bug nyata yang ditemukan lewat eksekusi CI sungguhan (persis filosofi M8.1: perbaiki di file pemilik begitu genuinely terbukti, bukan borongan preventif).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambah `skipif` untuk `CHATBOT_API_BASE_URL` di test ini** — ditolak; itu akan menyembunyikan bug asli (test SEHARUSNYA lolos penuh mocked, sesuai janji docstring file-nya sendiri) di balik skip permanen, bukan memperbaiki akar masalah.

**Dampak**
`test-python-fast` sekarang genuinely 670/705 passed tanpa gagal sama sekali (diverifikasi lokal meniru kondisi CI persis: `OPENROUTER_API_KEY=""`+`CHATBOT_API_BASE_URL=""`+`DATABASE_URL` asli → 670 passed, 35 skipped, 18.53s). Push perbaikan + re-run CI menyusul.

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
| 10 | `DATABASE_URL` Disediakan Juga ke `test-python-fast` | A | Checkpoint 3 |
| 11 | Bug Nyata: `test_400_lalu_200_di_revisi_kedua_berhasil` Lupa Mock `panggil_meta_chatbot_api` | A | Checkpoint 7 |
