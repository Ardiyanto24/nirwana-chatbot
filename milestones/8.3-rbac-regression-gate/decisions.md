# Decisions — Milestone 8.3: RBAC/Authorization Regression Gate

Dokumen ini mencatat setiap keputusan desain untuk Milestone 8.3, ditentukan sebelum implementasi dimulai lewat Plan Mode (satu putaran `AskUserQuestion`, didahului riset agent Explore atas bukti nyata M7.11-M7.14).

---

## Keputusan 1: Klasifikasi LLM Di-Mock/Fix ke Hasil Historis — Fokus Murni Enforcement

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
Kelima skenario zero-leakage (`gop_margin` dkk.) melibatkan langkah Domain Gate (identifikasi domain, deteksi cakupan individu) yang genuinely memanggil LLM. Genuinely terbuka: apakah `rbac-regression` harus memanggil LLM nyata (menguji klasifikasi + enforcement sekaligus) atau cukup fokus ke logika enforcement (otorisasi + koreksi paksa) dengan hasil klasifikasi di-fix ke nilai historis yang sudah terbukti benar.

**Keputusan yang Dipilih**
Hasil klasifikasi Domain Gate (domain teridentifikasi, `cakupan_individu.terdeteksi`) di-fix/mock ke nilai historis per skenario — TIDAK ada panggilan LLM nyata di `rbac-regression`. Fokus murni ke `periksa_otorisasi_semua()` (deterministik, real `DATABASE_URL`) dan koreksi paksa Verification Gate.

**Alasan**
Gate ini secara eksplisit dirancang sebagai "sinyal kebocoran RBAC, prioritas tinggi, dieskalasi langsung" — HARUS selalu bisa diandalkan, tidak boleh merah karena infra LLM (OpenRouter sudah 3x terbukti flaky di M8.1/M8.2). Klasifikasi LLM sendiri sudah tercakup grup `domain_gate` M8.2 (`test-python-llm`) — menggandakannya di sini cuma menambah risiko flakiness tanpa cakupan tambahan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Real LLM call, uji klasifikasi + enforcement sekaligus** — ditolak; lebih menyeluruh (menangkap regresi prompt) tapi mewarisi flakiness yang merusak kepercayaan terhadap sinyal gate ini sendiri — trade-off yang secara eksplisit ditolak user.

**Dampak**
Menentukan seluruh desain Checkpoint 2-8: setiap skenario dibangun dari state HASIL Domain Gate yang sudah di-fix (bukan memanggil `identifikasi_domain`/`deteksi_constraint` sungguhan), lalu memanggil fungsi enforcement deterministik apa adanya.

---

## Keputusan 2: Cakupan Comprehensive — 5 Skenario, Bukan Cuma `gop_margin`

**Status:** Diputuskan sebelum implementasi (dari plan, `AskUserQuestion`).

**Latar Belakang**
KK sumber M8.3 literal cuma minta "minimal skenario `gop_margin`". Riset agent Explore menemukan 4 skenario zero-leakage LAIN yang juga sudah terbukti nyata di M7.11-M7.14 (F&B all-denied, HR Staff "Budi", Maintenance Staff "Andi", CEO baseline) — genuinely terbuka apakah semuanya dikodekan atau cukup minimum literal.

**Keputusan yang Dipilih**
Kodekan seluruh 5 skenario sebagai regression test permanen.

**Alasan**
Skenario+data sudah ada dari eval M7.11-7.14 (bagian tersulit — menemukan+membuktikan skenario nyata — sudah selesai) — biaya inkremental mengodekan ulang jadi test permanen rendah dibanding manfaat cakupan regression yang jauh lebih kuat dari 1 skenario tunggal.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Minimal — cuma `gop_margin`** — ditolak; sesuai KK literal tapi meninggalkan 4 skenario yang sudah terbukti nyata tanpa regression permanen sama sekali, padahal datanya sudah tersedia.

**Dampak**
Checkpoint 3-7 (5 checkpoint terpisah, satu per skenario) alih-alih 1 checkpoint tunggal.

---

## Keputusan 3: Job `rbac-regression` Terpisah dari `test-python-fast`/`test-python-llm`

**Sumber Paksaan**
`docs/02-implementation-plan/rancangan-ci-cd.md`, Milestone 8.3: "Job ini **terpisah** dari Milestone 8.2, bukan digabung ke dalamnya" + "Kenapa Ini Jadi Milestone Terpisah: kegagalan di gate ini bermakna beda dari kegagalan unit test generik... Menggabungkannya ke job test generik akan mengaburkan urgensi itu."

**Keputusan yang Diikuti**
Job `rbac-regression` baru di `ci.yml`, target `pytest tests/rbac_regression/` — TIDAK digabung ke job `test-python-fast`/`test-python-llm` M8.2 meski secara teknis bisa (sama-sama `pytest`).

**Catatan Ketergantungan**
Menggabungkan akan bertentangan langsung dengan alasan eksplisit dokumen sumber kenapa milestone ini dipisah sejak awal.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kalimat KK sumber secara verbatim.

---

## Keputusan 4: Reuse `DATABASE_URL` Secret M8.2 untuk Otorisasi Nyata

**Sumber Paksaan**
Preseden Keputusan 10 M8.2 (`DATABASE_URL` cepat+andal, disediakan ke baseline).

**Keputusan yang Diikuti**
`periksa_otorisasi_semua()` dipanggil NYATA terhadap `DATABASE_URL` (secret sudah ada dari M8.2, tidak perlu ditambah baru) — bukan mock statis matriks `role_permissions`.

**Catatan Ketergantungan**
Mock statis berisiko drift dari matriks izin nyata (kalau tabel `role_permissions` berubah, test tetap hijau padahal enforcement sungguhan sudah beda) — bertentangan dengan tujuan gate ini sebagai sinyal kebocoran nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mock statis matriks role_permissions di kode test** — ditolak; lebih cepat/tanpa dependency DB, tapi berisiko basi diam-diam, kontradiktif dengan tujuan regression gate yang harus mencerminkan keadaan otorisasi SUNGGUHAN.

**Dampak**
Job `rbac-regression` butuh `DATABASE_URL` di `env:`, TIDAK butuh `OPENROUTER_API_KEY` sama sekali (Keputusan 1).

---

## Keputusan 5: `tests/rbac_regression/` — Package Baru, Bukan Menambah ke `tests/layers/domain_gate/`

**Sumber Paksaan**
Tujuan milestone (sinyal terpisah, high-visibility, preseden Keputusan 3) + kebutuhan CI job target `pytest` yang bersih.

**Keputusan yang Diikuti**
Folder baru `tests/rbac_regression/` (bukan `tests/layers/domain_gate/test_rbac_regression.py`) — top-level baru di bawah `tests/`, memicu update tabel "Struktur Repository" `CLAUDE.md`/`AGENT.md` di Checkpoint 2 (forced by aturan eksplisit CLAUDE.md, bukan ditunda ke penutupan).

**Catatan Ketergantungan**
Menaruh di dalam `tests/layers/domain_gate/` akan mengaburkan batas "ini regression gate lintas-layer" vs "ini unit test satu layer" — CI job `pytest tests/rbac_regression/` jadi tidak presisi kalau bercampur dengan test domain_gate biasa.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambahkan ke `tests/layers/domain_gate/`** — ditolak; skenario zero-leakage genuinely lintas-layer (Domain Gate→Otorisasi→Retriever→Verification Gate), bukan milik satu layer, dan mencampur akan mengaburkan target CI job yang presisi.

---

## Keputusan 6: Reuse Builder Fixture dari `test_verifikasi_gate.py`

**Sumber Paksaan**
Preseden pola "state per-layer via `monkeypatch`" yang sudah matang di `tests/layers/verification_gate/test_verifikasi_gate.py` (M2.4) — builder `_buat_hasil_kecukupan()`, `_buat_atomic_intent_constraint()`, `_buat_query_engine_entry()`.

**Keputusan yang Diikuti**
`tests/rbac_regression/test_zero_leakage.py` adaptasi (bukan duplikasi dari nol) builder-builder itu untuk membangun state antar-layer per skenario.

**Catatan Ketergantungan**
Membangun ulang dari nol berisiko pola berbeda dari preseden matang yang sudah teruji, plus kerja duplikat.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden pola yang sudah matang + prinsip hindari duplikasi.

---

## Keputusan 7: Test "Sengaja Dibuat Gagal" — Checkpoint Sendiri

**Sumber Paksaan**
KK2 sumber M8.3 eksplisit membedakan "skenario zero-leakage lolos" dari "skenario sengaja bocor terdeteksi" sebagai DUA bukti terpisah.

**Keputusan yang Diikuti**
Checkpoint 8 (test unit "sengaja gagal") + Checkpoint 11 (verifikasi nyata CI dengan kode produksi dilonggarkan sesaat) — TIDAK digabung ke checkpoint skenario 1-5 manapun.

**Catatan Ketergantungan**
Menggabungkan akan mengaburkan dua jenis bukti yang secara sengaja dibedakan dokumen sumber (gate lolos untuk kasus aman vs gate MERAH untuk kasus bocor buatan).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by struktur KK sumber sendiri.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Klasifikasi LLM Di-Mock/Fix ke Hasil Historis | A | Plan |
| 2 | Cakupan Comprehensive — 5 Skenario | A | Plan |
| 3 | Job `rbac-regression` Terpisah | B | Plan |
| 4 | Reuse `DATABASE_URL` Secret M8.2 | B | Plan |
| 5 | `tests/rbac_regression/` Package Baru | B | Plan |
| 6 | Reuse Builder Fixture `test_verifikasi_gate.py` | B | Plan |
| 7 | Test "Sengaja Dibuat Gagal" — Checkpoint Sendiri | B | Plan |
