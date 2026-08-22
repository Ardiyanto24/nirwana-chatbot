# Decisions — Milestone 8.1: Fondasi CI — Kebersihan Kode & Rahasia

Dokumen ini mencatat setiap keputusan desain untuk Milestone 8.1, ditentukan sebelum implementasi dimulai lewat Plan Mode (dua putaran `AskUserQuestion`).

---

## Keputusan 1: Rule `ruff` yang Dinyalakan

**Status:** Diputuskan sebelum implementasi (dari plan).

**Latar Belakang**
Repo `nirwana-chatbot` belum pernah py lint config sepanjang 24 milestone sebelumnya (M1.1-M7.18). Menyalakan rule ruff pertama kali di codebase mature seperti ini genuinely terbuka — tidak ada preseden milestone manapun, dan pilihannya langsung mempengaruhi seberapa besar cleanup Checkpoint 4-15.

**Keputusan yang Dipilih**
Baseline: `select = ["E", "F", "I", "UP", "B", "SIM"]` (pycodestyle+pyflakes error dasar, isort, pyupgrade, bugbear, simplify). Bukan Minimal (`E`,`F` saja) maupun Ketat (+`ANN`,`ARG`,`PTH`,`TCH`, dst.).

**Alasan**
Baseline adalah titik keseimbangan umum industri untuk lint pertama kali di codebase besar — menangkap bug pattern nyata (`B`, mis. mutable default argument) dan konsistensi (`I`,`UP`,`SIM`) tanpa memaksa refactor besar (anotasi tipe di semua fungsi, migrasi `os.path`→`pathlib`) yang bukan tujuan milestone "fondasi".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Minimal (`E`,`F`)** — ditolak karena tidak menangkap pola bug nyata seperti mutable default argument; terlalu longgar untuk fondasi lint pertama kali.
- **Ketat (+`ANN`,`ARG`,`PTH`,`TCH`, dst.)** — ditolak untuk SEKARANG karena realistis butuh cleanup besar (type annotation di semua fungsi, migrasi `os.path`) yang keluar dari cakupan "fondasi" — berisiko jadi pekerjaan tersendiri yang menunda gate CI. User eksplisit minta ini dicatat sebagai keputusan tertunda untuk upgrade di masa depan (lihat Task 22, `docs/keputusan-tertunda.md`).

**Dampak**
Menentukan scope cleanup Checkpoint 4-15 (12 unit). `docs/keputusan-tertunda.md` akan mencatat trigger peninjauan ulang untuk upgrade ke Ketat.

---

## Keputusan 2: Kebijakan CVE Baseline (`pip-audit`+`govulncheck`)

**Status:** Diputuskan sebelum implementasi (dari plan).

**Latar Belakang**
KK3 M8.1 mewajibkan `pip-audit`+`govulncheck` dijalankan nyata sekali untuk mencatat baseline. Tidak ada preseden di project ini soal bagaimana menangani CVE aktif yang genuinely ditemukan — dokumen sumber cuma minta "dicatat", tidak menentukan kebijakan remediasi.

**Keputusan yang Dipilih**
Zero-tolerance: SEMUA CVE yang ditemukan wajib di-fix/upgrade dependency sebelum Checkpoint 16 dianggap selesai, tanpa memandang severity.

**Alasan**
User eksplisit memilih postur keamanan terkuat — project ini publik dan menyangkut RBAC data sensitif (financial/HR/PII), sehingga toleransi nol terhadap CVE aktif dianggap lebih penting daripada kecepatan menutup checkpoint.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Severity-based** (Critical/High wajib fix, Medium/Low boleh diterima+allowlist) — ditolak; user memilih tidak membedakan severity.
- **Putuskan reaktif nanti** — ditolak; user memilih komit kebijakan di depan supaya tidak ada jeda keputusan tambahan di tengah eksekusi Checkpoint 16.

**Dampak**
Checkpoint 16 (Task 16-17) berisiko tidak bisa "bersih" murni kalau CVE ditemukan tanpa patch upstream tersedia — dicatat sebagai risiko di plan, mitigasinya eskalasi ke user case-by-case, bukan melunakkan kebijakan sepihak.

---

## Keputusan 3: Branch Protection `main`

**Status:** Diputuskan sebelum implementasi (dari plan).

**Latar Belakang**
Dokumen sumber menyebut 4 job CI M8.1 sebagai "blocking" tapi tidak eksplisit menyebut mekanisme GitHub branch protection (required status checks) — ambigu apakah "blocking" berarti job tampil merah, atau benar-benar mengunci tombol merge.

**Keputusan yang Dipilih**
Aktifkan branch protection rule di `main` di M8.1 (Checkpoint 19) mewajibkan 4 status check milestone ini (`ruff`, `golangci-lint`, `gitleaks`, `dependency-scan`) lolos sebelum merge. M8.2-8.5 nanti menambah check masing-masing ke daftar wajib yang sama secara incremental.

**Alasan**
Sesuai framing "fondasi" — gate CI mestinya benar-benar mengunci merge sejak awal, bukan cuma informational. Tidak ada branch protection aktif saat ini (dikonfirmasi `gh api` → 404), jadi tidak ada risiko menimpa konfigurasi existing.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tunda sampai akhir Bagian 1 (setelah M8.5)** — ditolak; user memilih menyalakan sekarang untuk konsistensi dengan framing "fondasi", meski konsekuensinya setting repo diubah incremental beberapa kali (M8.1, lalu M8.3, M8.4 dst.) alih-alih sekali di akhir.

**Dampak**
Checkpoint 19 adalah perubahan setting GitHub (bukan file kode) — butuh konfirmasi eksplisit terpisah dari persetujuan plan sebelum dieksekusi (aturan keamanan aksi "Changing account settings"). M8.2-8.5 mewarisi pola ini — setiap milestone yang menambah job baru juga perlu menambah ke required status checks.

---

## Keputusan 4: Granularitas Pembersihan Lint

**Status:** Diputuskan sebelum implementasi (dari plan, ditemukan+diajukan user di tengah sesi perencanaan setelah draf plan pertama).

**Latar Belakang**
Draf plan pertama merencanakan satu checkpoint besar `ruff check --fix`+`format` sekaligus di seluruh `src/`+`tests/`. User meminta pendekatan lebih aman: analisis dulu daftar fitur yang ada, lalu bersihkan fokus satu fitur per satu waktu — supaya kalau ada satu unit yang bermasalah, rollback-nya spesifik ke unit itu saja, bukan menghapus pekerjaan bersih di unit lain yang sudah benar.

**Keputusan yang Dipilih**
Per layer arsitektur — 12 unit independen (9 layer + Orchestration + Support lintas-layer + Go exporter), masing-masing checkpoint sendiri, diverifikasi dengan subset test unit itu sendiri (kecuali Unit 8/Support yang diverifikasi full suite karena dipakai lintas-layer). Lihat tabel 12 unit di plan.

**Alasan**
Match persis batas folder `tests/layers/<nama>/` yang sudah ada — memberi isolasi risiko paling presisi, konsisten prinsip checkpoint kecil-independen yang sudah dipegang project ini sejak M1.5 (lihat `milestones/1.5-.../decisions.md`).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Sekaligus seluruh `src/`+`tests/` (draf awal)** — ditolak user karena satu checkpoint besar menghapus manfaat rollback spesifik-per-unit kalau ada bagian yang bermasalah.
- **Per grup PIC (7 unit, gabung layer semilik PIC)** — dipertimbangkan sebagai jalan tengah (lebih sedikit siklus verifikasi+commit), tapi tidak dipilih user yang lebih memilih presisi maksimal (Per layer arsitektur).

**Dampak**
Checkpoint 3 (draf awal) pecah jadi Checkpoint 3-15 (13 checkpoint: 1 config ruff + 11 unit Python + 1 unit Go). Total checkpoint milestone naik dari 9 (draf awal) jadi 20. ~12 commit `chore`/`fix` terpisah hanya untuk cleanup.

---

## Keputusan 5: Urutan Pengerjaan 12 Unit

**Status:** Diputuskan sebelum implementasi (dari plan).

**Latar Belakang**
Setelah granularitas per-layer disepakati (Keputusan 4), urutan pengerjaan 12 unit itu sendiri genuinely terbuka — tidak ada preseden yang menentukan urutan pembersihan lint lintas-layer.

**Keputusan yang Dipilih**
Ukuran/risiko terkecil dulu — diurutkan objektif berdasar jumlah file (kode+test) per unit, dari Input Layer (3 file) sampai Domain Gate (22 file). Tabel lengkap di plan.

**Alasan**
User memilih pendekatan warm-up: memvalidasi mekanisme checkpoint-per-unit ini sendiri di unit kecil dulu (Input Layer, Verification Gate) sebelum masuk ke unit besar (Retriever 21 file, Domain Gate 22 file) yang risiko cakupan temuannya jauh lebih tinggi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Ikuti alur 9-layer (Input Layer → ... → Interpretation, lalu Orchestration/Support/Go)** — dipertimbangkan karena paling mudah dilacak silang dengan dokumentasi milestone M1-M4 yang sudah ada, tapi tidak dipilih user yang lebih memilih ordering berbasis risiko/ukuran.

**Dampak**
Urutan Checkpoint 4-15 di plan: Input Layer(3) → Verification Gate(4) → Decomposition(7) → Go exporter(8) → Interpretation(9) → Orchestration(10) → Query Engine(11) → Support(11) → Execution(13) → Context Resolution(14) → Retriever(21) → Domain Gate(22).

---

## Keputusan 6: 4 Job CI dan Sifatnya Blocking

**Sumber Paksaan**
`docs/02-implementation-plan/rancangan-ci-cd.md`, Milestone 8.1 Lingkup: "`.github/workflows/ci.yml` dibangun dengan empat job: `ruff` (lint+format, blocking), `golangci-lint` (blocking, mencakup `govet`+`staticcheck`+`gosec`), `gitleaks` (secret scan, blocking), dan `pip-audit`+`govulncheck` (dependency vulnerability scan, blocking)."

**Keputusan yang Diikuti**
Persis 4 job tersebut, seluruhnya blocking, dibangun di Checkpoint 17.

**Catatan Ketergantungan**
M8.2-8.5 menambah job ke workflow yang sama — mengubah jumlah/nama job di M8.1 akan memutus kontrak yang diasumsikan milestone berikutnya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kalimat Lingkup dokumen sumber secara verbatim.

---

## Keputusan 7: Pembersihan Lokal Sebelum Gate Dinyalakan

**Sumber Paksaan**
`rancangan-ci-cd.md`, "Konteks: Kenapa Dokumen Ini Ada", butir keputusan 3: "Strategi lint gate → blocking penuh sejak awal, tapi didahului pembersihan lokal (`ruff --fix`, `golangci-lint run --fix`) di seluruh kode existing SEBELUM gate CI dinyalakan sebagai wajib."

**Keputusan yang Diikuti**
Checkpoint 3-16 (config+cleanup+baseline CVE) seluruhnya terjadi SEBELUM Checkpoint 17 (`ci.yml` dibangun) dan Checkpoint 19 (branch protection dinyalakan).

**Catatan Ketergantungan**
Membalik urutan ini (nyalakan gate dulu, baru bersihkan) akan langsung memblokir seluruh riwayat kerja 24 milestone sebelumnya yang ditulis tanpa lint config — bertentangan langsung dengan alasan keputusan ini ditulis di dokumen sumber.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by keputusan eksplisit user yang sudah dikutip di dokumen sumber sendiri.

---

## Keputusan 8: `gitleaks/gitleaks-action@v2` Resmi (Bukan CLI Manual)

**Sumber Paksaan**
Temuan nyata `gh repo view Ardiyanto24/nirwana-chatbot` → `"isPrivate": false, "visibility": "PUBLIC"`. `gitleaks-action` resmi berbayar untuk repo private, gratis untuk repo public.

**Keputusan yang Diikuti**
Checkpoint 17 memakai `gitleaks/gitleaks-action@v2` di `ci.yml`, bukan CLI manual/docker image sebagai workaround lisensi.

**Catatan Ketergantungan**
Kalau repo ini nanti diubah jadi private, keputusan ini perlu ditinjau ulang (action akan minta lisensi).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by temuan visibility repo — tidak ada kendala lisensi yang perlu dihindari.

---

## Keputusan 9: Lokasi `.golangci.yml` dan Working Directory Go

**Sumber Paksaan**
Temuan nyata `Glob custom-exporter/**/go.{mod,sum}` → `go.mod`/`go.sum` ada di `custom-exporter/supabaseexporter/`, BUKAN `custom-exporter/` root seperti tersirat kalimat Lingkup dokumen sumber ("`golangci-lint run --fix` di `custom-exporter/`").

**Keputusan yang Diikuti**
`.golangci.yml` (Checkpoint 7) dan seluruh command `golangci-lint`/`govulncheck` (Checkpoint 7, 16) dijalankan dengan working directory `custom-exporter/supabaseexporter/`. Job `golangci-lint` di `ci.yml` (Checkpoint 17) memakai `working-directory: custom-exporter/supabaseexporter`.

**Catatan Ketergantungan**
Menjalankan dari `custom-exporter/` root akan gagal (`go.mod` tidak ditemukan) — bukan pilihan yang genuinely tersedia.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by struktur direktori nyata repo.

---

## Keputusan 10: Config Global Ditulis Sekali di Depan

**Sumber Paksaan**
Sifat config `[tool.ruff]`/`.golangci.yml` yang project-wide (satu config berlaku untuk seluruh unit), bukan per-unit.

**Keputusan yang Diikuti**
Checkpoint 3 menulis `[tool.ruff]` SEKALI sebelum unit manapun dibersihkan (Checkpoint 4-15). Go terkecuali — `.golangci.yml` digabung ke Checkpoint 7 (bukan checkpoint config terpisah) karena Go cuma py 1 unit total, tidak ada manfaat memisah config dari fix untuk satu-satunya unit yang memakainya.

**Catatan Ketergantungan**
Menulis config berulang per-unit Python akan jadi kerja duplikat tanpa manfaat (config sama untuk semua unit).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by sifat config itu sendiri.

---

## Keputusan 11: `ruff` sebagai Dev Dependency via `uv add --dev`

**Sumber Paksaan**
Preseden `pytest` yang sudah ada di `[dependency-groups].dev` `pyproject.toml` — pola dev-tool project ini.

**Keputusan yang Diikuti**
`uv add --dev ruff` (Checkpoint 3) — `ruff` jadi bagian dev dependency group, tersedia lokal maupun CI lewat `uv sync`.

**Catatan Ketergantungan**
Konsisten dengan cara `pytest` sudah dikelola — menyimpang dari pola ini (mis. instal `ruff` global tanpa lewat `uv`) akan bikin reproduksibilitas CI vs lokal tidak terjamin.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden pola dev dependency existing.

---

## Keputusan 12: `pip-audit` via `uv run --with pip-audit pip-audit`

**Sumber Paksaan**
Kebutuhan teknis: `pip-audit` perlu mengaudit environment PROJECT (mengikuti `uv.lock`), bukan environment ephemeral kosong. `uvx pip-audit` berdiri sendiri tidak melihat dependency project sama sekali.

**Keputusan yang Diikuti**
Checkpoint 16 dan job `dependency-scan` (Checkpoint 17) memakai `uv run --with pip-audit pip-audit`.

**Catatan Ketergantungan**
Memakai `uvx pip-audit` polos akan menghasilkan hasil scan yang salah (audit environment kosong, bukan `uv.lock` project).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`uv export` → `requirements.txt` → `pip-audit -r`** — dipertimbangkan sebagai alternatif valid, tidak dipilih karena `uv run --with` lebih ringkas (satu command, tidak perlu file perantara).

**Dampak**
Tidak ada dampak lintas-milestone — murni detail eksekusi command.

---

## Keputusan 13: `govulncheck` via `go install`

**Sumber Paksaan**
Preseden toolchain Go native yang sudah dipakai `custom-exporter` sejak M6.1 (`go build`/`go test` langsung, bukan container-only untuk development).

**Keputusan yang Diikuti**
`go install golang.org/x/vuln/cmd/govulncheck@latest` (Checkpoint 16), dijalankan dari `custom-exporter/supabaseexporter/`.

**Catatan Ketergantungan**
Konsisten cara toolchain Go lain (`golangci-lint`) diinstal di Checkpoint 7.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden toolchain Go native project ini.

---

## Keputusan 14: Update Tabel "Struktur Repository" di Checkpoint yang Sama

**Sumber Paksaan**
`CLAUDE.md`/`AGENT.md`, Workflow Wajib butir "Implementasikan per checkpoint" poin 5: "Jika checkpoint ini menghasilkan folder top-level/subpackage BARU yang belum tercatat di 'Struktur Repository', perbarui bagian itu di `CLAUDE.md` dan `AGENT.md` sebagai bagian dari checkpoint ini — bukan ditunda ke penutupan milestone."

**Keputusan yang Diikuti**
Checkpoint 17 (yang membuat folder `.github/` baru lewat `ci.yml`) langsung memperbarui tabel "Struktur Repository" di `CLAUDE.md`+`AGENT.md` sebagai bagian dari checkpoint itu sendiri, bukan ditunda ke Checkpoint 20 (penutupan).

**Catatan Ketergantungan**
Menunda update ini ke penutupan akan melanggar aturan eksplisit yang sudah ditulis di CLAUDE.md.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by aturan eksplisit CLAUDE.md.

---

## Keputusan 15: Commit `ci.yml` Pakai Tipe `ci`

**Sumber Paksaan**
Konvensi Conventional Commits yang mendefinisikan tipe `ci` khusus untuk perubahan konfigurasi CI. `CLAUDE.md` mewajibkan standar Conventional Commits untuk seluruh commit project.

**Keputusan yang Diikuti**
Commit Checkpoint 17 yang menulis `.github/workflows/ci.yml` memakai prefix `ci(milestone-8.1): ...`, bukan `feat`/`chore`.

**Catatan Ketergantungan**
Project belum pernah pakai tipe `ci` di 24 milestone sebelumnya (tidak pernah ada perubahan CI) — ini pemakaian pertama, konsisten memperkenalkan tipe baru sesuai kebutuhan genuinely baru, bukan penyimpangan dari konvensi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`feat`** — ditolak karena `ci.yml` bukan fitur aplikasi, melainkan konfigurasi tooling CI, yang punya tipe khusus sendiri di Conventional Commits.

---

## Keputusan 16: Keluarkan E501 (Line-Too-Long) dari Rule Set

**Status:** Ditemukan di tengah implementasi pada Checkpoint 3.

**Latar Belakang**
Setelah `[tool.ruff]` ditulis (rule Baseline, Keputusan 1), `uv run ruff check src/ tests/` menunjukkan 933 total temuan — 867 di antaranya (93%) `E501` line-too-long. Uji coba `ruff format` di salinan scratch (tidak menyentuh repo) mengurangi jadi 551, tapi analisis distribusi sisa pelanggaran (median 113 char, mean 132, maksimum 515 char) menunjukkan mayoritas genuinely tidak bisa dibereskan formatter — kemungkinan besar komentar/docstring naratif Bahasa Indonesia yang memang gaya dokumentasi project ini. Menaikkan `line-length` ke 100/120 tetap menyisakan 404/236 pelanggaran. Ini genuinely tidak terduga saat rule Baseline dipilih (Keputusan 1) — E501 tidak pernah dibahas eksplisit sebagai risiko dominan saat itu.

**Keputusan yang Dipilih**
Tambah `ignore = ["E501"]` di `[tool.ruff.lint]`, select tetap `E,F,I,UP,B,SIM` (rule lain tidak berubah).

**Alasan**
`ruff format` (Black-compatible) sudah menjamin konsistensi lebar kode untuk ekspresi yang bisa di-reflow; E501 sisa murni menghukum komentar/docstring/string panjang yang memang pilihan gaya dokumentasi, bukan indikator bug/kualitas kode — sejalan dengan alasan awal memilih Baseline (moderate cleanup, bukan refactor besar-besaran). Praktik umum industri saat sudah memakai formatter otomatis. Setelah `ignore` ditambahkan, total temuan turun ke 66 (53 auto-fixable, 13 manual) — proporsional untuk cakupan "fondasi".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Naikkan `line-length` ke 120** — ditolak; data menunjukkan masih menyisakan 236 pelanggaran (43% dari 551), tidak cukup efektif mengurangi noise.
- **Pertahankan E501 apa adanya (88 char, wajib)** — ditolak; akan membengkakkan SETIAP checkpoint pembersihan (Checkpoint 4-15) jadi didominasi kerja wrapping baris komentar/docstring, bertentangan dengan alasan awal memilih Baseline alih-alih Ketat (menghindari cleanup besar yang keluar dari cakupan "fondasi").

**Dampak**
Checkpoint 4-15 sekarang realistis (66 temuan total di seluruh 12 unit, bukan 933) — konsisten skala "moderate cleanup" yang dijanjikan Keputusan 1. `docs/keputusan-tertunda.md` (Task 22) perlu mencatat E501/line-length sebagai bagian pertimbangan saat upgrade ke rule Ketat nanti, bukan cuma `ANN`/`ARG`/`PTH`/`TCH`.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Rule `ruff` yang Dinyalakan | A | Plan |
| 2 | Kebijakan CVE Baseline | A | Plan |
| 3 | Branch Protection `main` | A | Plan |
| 4 | Granularitas Pembersihan Lint | A | Plan |
| 5 | Urutan Pengerjaan 12 Unit | A | Plan |
| 6 | 4 Job CI dan Sifatnya Blocking | B | Plan |
| 7 | Pembersihan Lokal Sebelum Gate Dinyalakan | B | Plan |
| 8 | `gitleaks/gitleaks-action@v2` Resmi | B | Plan |
| 9 | Lokasi `.golangci.yml` dan Working Directory Go | B | Plan |
| 10 | Config Global Ditulis Sekali di Depan | B | Plan |
| 11 | `ruff` sebagai Dev Dependency via `uv add --dev` | B | Plan |
| 12 | `pip-audit` via `uv run --with pip-audit pip-audit` | B | Plan |
| 13 | `govulncheck` via `go install` | B | Plan |
| 14 | Update Tabel "Struktur Repository" di Checkpoint yang Sama | B | Plan |
| 15 | Commit `ci.yml` Pakai Tipe `ci` | B | Plan |
| 16 | Keluarkan E501 (Line-Too-Long) dari Rule Set | A | Checkpoint 3 |
