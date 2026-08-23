# Decisions — Milestone 8.6: Remote + CI untuk `dashboard/`

Dokumen ini mencatat setiap keputusan desain untuk Milestone 8.6, ditentukan sebelum implementasi dimulai lewat Plan Mode (satu putaran `AskUserQuestion`, 4 pertanyaan).

---

## Keputusan 1: Tiga Job CI Persis Sesuai Dokumen Sumber, Tanpa Job Tambahan

**Sumber Paksaan**
`docs/02-implementation-plan/rancangan-ci-cd.md`, Milestone 8.6 Lingkup: "membangun `.github/workflows/ci.yml` di repo itu (eslint + vitest + `next build` sebagai gate PR — ketiga script sudah tersedia di `package.json`, tinggal disambungkan ke CI)". Juga forced oleh prinsip `CLAUDE.md` "Batas Implementasi Saat Ini": "Jangan membangun kapabilitas di luar cakupan delapan dokumen sumber kebenaran... kecuali pengguna memperluas cakupan."

**Keputusan yang Diikuti**
`dashboard/.github/workflows/ci.yml` hanya berisi 3 job (`lint`, `test`, `build`) — TIDAK ditambah `gitleaks`/`dependency-scan`/job lain meski `ci.yml` `nirwana-chatbot` (M8.1-8.5) py 4+ job dengan pola serupa.

**Catatan Ketergantungan**
Menambah job di luar 3 yang diminta dokumen sumber akan jadi scope creep sepihak tanpa konfirmasi user — kalau nanti dibutuhkan (mis. secret scan), itu keputusan terpisah yang perlu diajukan eksplisit.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menambah `gitleaks` untuk paritas dengan `nirwana-chatbot`** — dipertimbangkan karena repo baru ini juga akan public (Keputusan 11), tapi ditolak karena dokumen sumber M8.6 eksplisit tidak memintanya, dan riwayat git `dashboard/` sudah diverifikasi bersih dari kredensial (lihat Keputusan 5 plan/Context Temuan #5).

---

## Keputusan 2: Gaya Workflow Mengikuti Preseden `ci.yml` `nirwana-chatbot`

**Sumber Paksaan**
Preseden `ci.yml` `nirwana-chatbot` (M8.1-8.5) — konvensi project untuk seluruh workflow GitHub Actions: nama job deskriptif, `actions/checkout@v4`, trigger `push`+`pull_request` ke `main`, versi tool terbaru yang konsisten dipakai (Node 22 di job `prompt-eval` M8.4).

**Keputusan yang Diikuti**
`dashboard/.github/workflows/ci.yml` memakai `actions/checkout@v4` + `actions/setup-node@v4` (`node-version: "22"`, `cache: npm`), trigger `on: push/pull_request: branches: [main]`. Tidak memakai path-filtering/job aggregator `if: always()` (`dorny/paths-filter`, pola `test-gate`/`prompt-eval-gate`) karena ketiga job dashboard selalu jalan tiap push/PR — tidak ada kondisi skip yang perlu diatasi.

**Catatan Ketergantungan**
Konsistensi gaya lintas seluruh workflow project — job/step yang menyimpang gaya akan lebih sulit dibaca silang oleh siapa pun yang sudah familiar dengan `ci.yml` utama.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden gaya yang sudah konsisten dipakai 5 milestone CI sebelumnya (M8.1-8.5).

---

## Keputusan 3: Job `build` Tidak Diberi `DATABASE_URL`

**Sumber Paksaan**
Perbaikan Checkpoint 2 (lihat Keputusan 9) — setelah `dashboard/src/app/page.tsx` diberi `export const dynamic = "force-dynamic"`, tidak ada page yang dieksekusi Next.js saat `next build` (semua page jadi dynamic-rendered saat request, bukan build-time), sehingga `db.ts` (yang connect ke Postgres di level modul saat `NODE_ENV=production`) tidak pernah ter-trigger selama build.

**Keputusan yang Diikuti**
Step `npm run build` di job `build` `ci.yml` TIDAK diberi env `DATABASE_URL` sama sekali.

**Catatan Ketergantungan**
Kalau di masa depan ada page baru yang genuinely butuh static rendering (mis. halaman marketing statis tanpa data dinamis), keputusan ini tidak perlu diubah — hanya berlaku untuk page yang mengonsumsi `db.ts`. Kalau ada page baru yang mengonsumsi `db.ts` TANPA `export const dynamic`, gap yang sama (Keputusan 9) akan muncul lagi dan perlu fix serupa.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Beri `DATABASE_URL` sebagai GitHub secret supaya build tetap bisa prerender apa adanya** — ditolak lewat `AskUserQuestion` (lihat Keputusan 9), karena menambah kredensial DB yang sebenarnya tidak perlu di CI dan tidak menutup bug staleness produksi.

---

## Keputusan 4: Job `test` Tidak Butuh Secret Apa Pun

**Sumber Paksaan**
Isi nyata `dashboard/src/lib/trace-tree.test.ts` dan `dashboard/src/lib/format.test.ts` — keduanya menguji fungsi pure (`buildSpanTree()`/`computeWaterfallRows()`, `humanizeDuration()`/`formatPercent()`) tanpa dependensi DB, sesuai preseden M5.2/M5.3 ("`buildSpanTree()` dipisah file supaya testable tanpa `DATABASE_URL`").

**Keputusan yang Diikuti**
Step `npm test` (`vitest run`) di job `test` `ci.yml` tidak diberi env apa pun.

**Catatan Ketergantungan**
Kalau ada test baru di masa depan yang butuh koneksi DB nyata (integration test), keputusan ini perlu ditinjau ulang untuk test tersebut spesifik — bukan mengubah keseluruhan job.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by isi nyata kedua file test yang sudah ada.

---

## Keputusan 5: Repo `dashboard/` Tetap Terpisah dari `nirwana-chatbot`

**Sumber Paksaan**
`milestones/5.2-skema-data-koneksi-nextjs-supabase/decisions.md` Keputusan 1 — repo Git terpisah, gitignored dari `nirwana-chatbot`, mirror pola `nirwana-database/web`.

**Keputusan yang Diikuti**
Milestone 8.6 memberi `dashboard/` remote+CI+Vercel SENDIRI, tanpa menggabungkannya jadi monorepo dengan `nirwana-chatbot`.

**Catatan Ketergantungan**
Mengubah ini di M8.6 akan membatalkan keputusan M5.2 yang sudah final tanpa alasan baru yang kuat.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by keputusan M5.2 yang tidak direvisi di sini.

---

## Keputusan 6: Perbaikan `page.tsx` Dicatat sebagai Addendum di `decisions.md` Milik M5.4

**Sumber Paksaan**
Preseden konsisten project: gap yang ditemukan di satu milestone tapi berasal dari kode milestone lain diperbaiki di file pemilik + didokumentasikan sebagai addendum di `decisions.md` milik milestone tersebut, bukan di `decisions.md` milestone yang menemukannya (M7.6 Keputusan 12 di `milestones/1.3-.../decisions.md`; M7.7 Keputusan 14 di `milestones/1.5-.../decisions.md`; M6.1 addendum role_title di `milestones/7.6-.../decisions.md` dan `milestones/7.18-.../decisions.md`).

**Keputusan yang Diikuti**
Perbaikan bug staleness/build-time-DB (Checkpoint 2) dicatat sebagai addendum baru di `milestones/5.4-panel-agregat-metrik-ringkasan/decisions.md`, bukan sebagai entri baru di sini.

**Catatan Ketergantungan**
Menjaga jejak "siapa pemilik keputusan apa" tetap koheren — pembaca yang membuka `decisions.md` M5.4 di masa depan akan menemukan riwayat lengkap perilaku `page.tsx`, termasuk perbaikan yang terjadi belakangan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden yang sudah dipakai konsisten 3x sebelumnya di project ini.

---

## Keputusan 7: Branch Protection `main` Mewajibkan 3 Status Check

**Sumber Paksaan**
KK M8.6 sendiri (`rancangan-ci-cd.md`): "PR percobaan yang sengaja melanggar eslint ATAU membuat test vitest gagal terbukti diblokir CI" — pernyataan ini mustahil benar tanpa required status checks aktif (CI merah semata tidak mengunci tombol merge tanpa branch protection). Mengikuti pola `milestones/8.1-fondasi-ci/decisions.md` Keputusan 3.

**Keputusan yang Diikuti**
Branch protection rule diaktifkan di `main` repo `nirwana-observability-dashboard`, mewajibkan status check `lint`, `test`, `build` lolos sebelum merge — dieksekusi di Checkpoint 6 dengan konfirmasi eksplisit terpisah (perubahan setting GitHub, bukan file kode).

**Catatan Ketergantungan**
Tanpa ini, Checkpoint 7-8 (PR percobaan) tidak bisa membuktikan KK "terbukti diblokir" secara literal.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by kalimat KK sumber sendiri.

---

## Keputusan 8: Uji Blocking untuk Kedua Pelanggaran (ESLint DAN Vitest)

**Sumber Paksaan**
Preseden thoroughness project — M8.1 menguji lint DAN secret scan terpisah, M8.2 menguji fast-tier DAN llm-tier terpisah, M8.3 menguji unit test DAN PR percobaan kode produksi. Dokumen sumber M8.6 memakai kata "ATAU" (minimum satu skenario cukup).

**Keputusan yang Diikuti**
Checkpoint 7 (PR percobaan ESLint) dan Checkpoint 8 (PR percobaan Vitest) keduanya dieksekusi nyata, melebihi minimum literal dokumen sumber.

**Catatan Ketergantungan**
Tidak ada — murni memperkuat bukti, tidak mengubah bentuk deliverable.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hanya uji salah satu (sesuai kata "ATAU" literal)** — dipertimbangkan sebagai jalan lebih cepat, tapi ditolak untuk konsistensi dengan preseden thoroughness M8.1-8.3.

---

## Keputusan 9: Bug Staleness Halaman Ringkasan Diperbaiki Sekarang (`force-dynamic`)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Riset Plan Mode menemukan `dashboard/src/app/page.tsx` tidak memakai dynamic API apa pun (`searchParams`/`cookies`/`headers`) dan tanpa `export const dynamic` eksplisit — kandidat static rendering default Next.js App Router. `dashboard/src/lib/db.ts` baris 35-38 membuat koneksi Postgres di level modul TOP-LEVEL saat `NODE_ENV === "production"` (throw kalau `DATABASE_URL` kosong). Kombinasi keduanya: `next build` akan mengeksekusi `getSummaryMetrics()` sekali saat build (genuinely connect DB), lalu MEMBEKUKAN datanya sampai deploy berikutnya — bertentangan dengan prinsip arsitektur "Dashboard publik wajib identik isinya dengan dashboard privat (Grafana)" dan komentar `page.tsx` sendiri yang mengimplikasikan real-time. Ini juga membuat job CI `build` (KK M8.6) gagal tanpa `DATABASE_URL` nyata sebagai secret. Bug ini genuinely berasal dari M5.4 (Checkpoint pembuatan halaman Ringkasan), bukan diperkenalkan M8.6 — baru bermanifestasi sekarang karena M8.6 adalah pertama kalinya `next build`+deploy produksi sungguhan dijalankan end-to-end (M5.1-5.4 sebelumnya hanya diverifikasi lewat `next dev`, yang selalu dynamic, tidak pernah menjalankan mode production build).

**Keputusan yang Dipilih**
Perbaiki sekarang: tambahkan `export const dynamic = "force-dynamic";` di `dashboard/src/app/page.tsx`, dieksekusi sebagai Checkpoint 2 milestone ini, didokumentasikan sebagai addendum di `milestones/5.4-.../decisions.md` (lihat Keputusan 6).

**Alasan**
User memilih opsi ini secara eksplisit dari 3 alternatif yang diajukan. Efek ganda yang menguntungkan: (1) menutup bug staleness produksi sesuai prinsip arsitektur real-time, (2) job CI `build` jadi tidak perlu `DATABASE_URL` sama sekali (Keputusan 3) — lebih aman (tidak expose kredensial DB ke CI runner) tanpa trade-off nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Beri `DATABASE_URL` ke CI sebagai secret, kode tidak diubah** — ditolak: menambah kredensial DB yang sebenarnya tidak perlu di CI runner, dan TIDAK menutup bug staleness di produksi Vercel (data tetap beku sampai deploy berikutnya).
- **Tunda, catat sebagai keterbatasan diterima** — ditolak: perbaikannya sederhana (satu baris `export const dynamic`) dan berdampak langsung ke KK M8.6 sendiri, tidak proporsional untuk ditunda.

**Dampak**
`milestones/5.4-panel-agregat-metrik-ringkasan/decisions.md` mendapat addendum baru. Job CI `build` M8.6 (Keputusan 3) tidak butuh `DATABASE_URL`.

---

## Keputusan 10: Nama Repo GitHub Baru — `nirwana-observability-dashboard`

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
`dashboard/` belum pernah py remote GitHub. Tidak ada preseden eksplisit untuk nama repo spesifik ini — sibling `nirwana-database/web` py nama sendiri (`nirwana-monitoring-web`) untuk project berbeda.

**Keputusan yang Dipilih**
`Ardiyanto24/nirwana-observability-dashboard`.

**Alasan**
User memilih nama yang deskriptif fungsi (observability publik PIC 5) daripada nama yang terikat eksplisit ke `nirwana-chatbot` sebagai backend spesifik.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`nirwana-chatbot-dashboard`** — dipertimbangkan karena relasi eksplisit ke backend, tapi tidak dipilih user yang lebih memilih nama deskriptif fungsi.

**Dampak**
Seluruh referensi remote (`git remote add origin`, `gh repo create`, dokumentasi) memakai nama ini.

---

## Keputusan 11: Visibilitas Repo — Public

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Repo baru butuh keputusan visibilitas eksplisit — tidak ada default yang aman diasumsikan sepihak untuk repo yang berisi kode observability dashboard (meski tidak berisi data sensitif itu sendiri, hanya kode aksesnya).

**Keputusan yang Dipilih**
Public.

**Alasan**
Konsisten dengan `nirwana-chatbot` (public sejak M8.1) dan tujuan project ini sebagai portofolio AI/ML Engineer. Riwayat git `dashboard/` sudah diverifikasi bersih dari kredensial asli (Context Temuan #5 plan) sebelum keputusan ini diambil.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Private** — dipertimbangkan sebagai default lebih konservatif, tapi tidak dipilih user yang memilih konsistensi dengan repo utama + tujuan portofolio.

**Dampak**
Tidak ada blocker teknis untuk Vercel (free tier mendukung repo public/private sama-sama). Tidak menambah kebutuhan job `gitleaks` (Keputusan 1) karena riwayat sudah diverifikasi bersih di luar mekanisme otomatis.

---

## Keputusan 12: Eksekusi Koneksi Vercel via CLI (Bukan Web UI Manual)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Menyambungkan repo ke Vercel butuh otorisasi akun (OAuth/login) yang tidak boleh dilakukan agent atas nama user (larangan keamanan). Pertanyaan diajukan untuk menentukan siapa yang mengeksekusi langkah ini.

**Keputusan yang Dipilih**
User sudah memasang Vercel CLI di mesinnya — koneksi dieksekusi lewat `vercel` CLI: agent menjalankan perintah non-kredensial (`vercel link`, `vercel git connect`, dst.), sementara user sendiri menjalankan `vercel login` (kalau belum terautentikasi) dan `vercel env add DATABASE_URL` (karena berisi password, larangan keamanan agent memasukkan kredensial).

**Alasan**
User secara eksplisit menyatakan sudah memasang Vercel CLI, mengindikasikan preferensi jalur CLI dibanding klik manual di web UI Vercel yang semula diajukan sebagai salah satu opsi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **User melakukan seluruhnya manual lewat web UI Vercel** — opsi yang diajukan semula ("Saya lakukan sendiri"), tidak dipilih karena user sudah py Vercel CLI terpasang dan lebih memilih jalur itu.
- **Agent mencoba lewat browser tool (Claude in Chrome)** — opsi lain yang diajukan, tidak dipilih; CLI yang sudah terautentikasi user adalah jalur yang lebih langsung dan tidak butuh sesi browser dengan kredensial user.

**Dampak**
Checkpoint 9 (koneksi Vercel) dan Checkpoint 10 (env var) dieksekusi lewat kombinasi command CLI (agent) + langkah interaktif kredensial (user).

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Tiga job CI persis sesuai dokumen sumber, tanpa job tambahan | B | Plan |
| 2 | Gaya workflow mengikuti preseden `ci.yml` `nirwana-chatbot` | B | Plan |
| 3 | Job `build` tidak diberi `DATABASE_URL` | B | Plan |
| 4 | Job `test` tidak butuh secret apa pun | B | Plan |
| 5 | Repo `dashboard/` tetap terpisah dari `nirwana-chatbot` | B | Plan |
| 6 | Perbaikan `page.tsx` dicatat sebagai addendum milik M5.4 | B | Checkpoint 2 |
| 7 | Branch protection `main` mewajibkan 3 status check | B | Checkpoint 6 |
| 8 | Uji blocking untuk kedua pelanggaran (ESLint dan Vitest) | B | Checkpoint 7-8 |
| 9 | Bug staleness halaman Ringkasan diperbaiki sekarang (`force-dynamic`) | A | Checkpoint 2 |
| 10 | Nama repo GitHub baru — `nirwana-observability-dashboard` | A | Checkpoint 4 |
| 11 | Visibilitas repo — Public | A | Checkpoint 4 |
| 12 | Eksekusi koneksi Vercel via CLI | A | Checkpoint 9-10 |
