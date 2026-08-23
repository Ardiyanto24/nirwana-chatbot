# Logs — Milestone 8.6: Remote + CI untuk `dashboard/`

Dokumen ini mencatat peristiwa nyata sepanjang Milestone 8.6 dikerjakan (2026-08-23), dikelompokkan per checkpoint sesuai plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/8.6-remote-ci-dashboard/decisions.md` berisi 12 keputusan (8 forced, 4 hasil `AskUserQuestion`) sebelum menyentuh kode apa pun.

**Temuan**
Tidak ada.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Review manual isi dokumen mencakup seluruh keputusan dari plan.

**Commit:** `b0be082` — `docs(milestone-8.6): decisions`

---

## Checkpoint 2 — Perbaikan Bug Staleness Homepage (Addendum M5.4)

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 2 — Tambahkan `export const dynamic = "force-dynamic"` di `page.tsx`

**Kesesuaian dengan plan:** Menyimpang dari plan — lihat "Task/Checkpoint di Luar Plan" untuk detail penuh koreksi dua babak.

**Apa yang dilakukan**
Menambahkan `export const dynamic = "force-dynamic";` di `dashboard/src/app/page.tsx`.

**Temuan**
Perbaikan ini SENDIRI tidak cukup — lihat Task di luar plan di bawah untuk kronologi lengkap penemuan dan koreksinya.

**Error/Kegagalan (jika ada)**
Klaim awal (dari plan) bahwa perbaikan ini menghilangkan kebutuhan `DATABASE_URL` saat `next build` TERBUKTI SALAH lewat verifikasi empiris (lihat Task di luar plan). Akar masalah sesungguhnya ada di `db.ts`, bukan `page.tsx`.

**Diagnosis dan Perbaikan (jika ada error)**
Lihat Task di luar plan ("Refactor `db.ts` jadi Lazy").

**Hasil Verifikasi**
`force-dynamic` tetap valid untuk tujuan aslinya (mencegah halaman Ringkasan dibekukan datanya) — dikonfirmasi lewat route table `next build` yang menunjukkan `/` sebagai `ƒ Dynamic` (bukan `○ Static`).

**Commit:** `b31640e` — `fix(dashboard): cegah static render dan koneksi DB saat build`

### Task 3 — Tulis addendum di `milestones/5.4-.../decisions.md`

**Kesesuaian dengan plan:** Sesuai plan (isi addendum diperluas mengikuti Task di luar plan, tapi keberadaan task-nya sendiri sesuai rencana).

**Apa yang dilakukan**
Menulis Keputusan 14 (Addendum) di `milestones/5.4-panel-agregat-metrik-ringkasan/decisions.md`, mendokumentasikan kedua babak (force-dynamic saja → terbukti tidak cukup → refactor `db.ts` lazy).

**Hasil Verifikasi**
Review manual isi addendum mencakup latar belakang, koreksi empiris, keputusan final, opsi ditolak, dan dampak.

**Commit:** `c7bf458` — `docs(milestone-5.4,milestone-8.6): addendum + koreksi bug build-time DB`

---

## Task/Checkpoint di Luar Plan (Checkpoint 2 — Refactor `db.ts` jadi Lazy)

**Kenapa ini tidak masuk plan sejak awal:** Plan (Plan Mode) menduga `export const dynamic = "force-dynamic"` di `page.tsx` SAJA sudah cukup menghilangkan kebutuhan `DATABASE_URL` saat `next build` — dugaan ini didasarkan pemahaman bahwa halaman yang di-set dynamic tidak akan dieksekusi Next.js saat build. Ini adalah **kesalahan analisis teknis di fase riset Plan Mode**, bukan temuan baru yang genuinely muncul di tengah eksekusi tanpa bisa diantisipasi — dicatat jujur di sini karena berdampak nyata ke bentuk pekerjaan Checkpoint 2.

### Task — Verifikasi Empiris yang Mematahkan Asumsi Plan

**Apa yang dilakukan**
Setelah Task 2 diterapkan, dijalankan verifikasi nyata: `dashboard/.env.local` dipindah sementara (`mv .env.local .env.local.bak-verify`), `.next` dihapus, `npm run build` dijalankan.

**Temuan**
Build GAGAL di fase "Collecting page data" untuk `/` MAUPUN `/traces` dengan error persis `DATABASE_URL tidak diset` dari `db.ts`. Investigasi lanjutan mengonfirmasi akar masalah: Next.js App Router meng-*import* modul SETIAP route (dynamic maupun static) di fase itu untuk mengumpulkan konfigurasi route — `export const dynamic` memengaruhi kapan konten *di-render*, bukan kapan modul *di-import*. `db.ts` versi eager (`export const sql = ... createClient()` di level modul) karena itu tetap ter-trigger.

**Error/Kegagalan**
```
Error: Failed to collect configuration for /traces
  [cause]: Error: DATABASE_URL tidak diset. ...
      at <unknown> (src\lib\db.ts:27:11)
      at module evaluation (src\lib\db.ts:33:1)
      at module evaluation (src\lib\traces.ts:2:1)
      at module evaluation (src\app\traces\page.tsx:2:1)
```
(Error identik juga muncul untuk `/`.)

**Diagnosis dan Perbaikan**
Temuan dibawa balik ke user lewat `AskUserQuestion` (transparan mengoreksi klaim sebelumnya yang keliru) — 3 opsi diajukan: refactor `db.ts` jadi lazy / beri `DATABASE_URL` ke CI / kombinasi keduanya. User memilih **refactor lazy**. Diimplementasikan: `db.ts` diubah dari `export const sql = <eager createClient()>` jadi `export const sql = new Proxy(placeholder, { apply, get })` — trap `apply` menangani pemanggilan tagged-template `sql\`...\``, trap `get` menangani akses method (`.begin`, dst.), keduanya memanggil `getClient()` yang baru membuat/cache client saat itu juga (bukan saat modul di-*import*). `traces.ts`/`summary.ts` TIDAK diubah sama sekali (Proxy transparan terhadap pemanggil).

**Hasil Verifikasi**
- `.env.local` dipindah sementara lagi, `npm run build` SUKSES penuh (route table: `/`, `/traces`, `/traces/[traceId]` seluruhnya `ƒ Dynamic`).
- `npm run lint`: 0 error, 0 warning (setelah juga menghapus 1 directive `eslint-disable` basi yang ditemukan saat proses ini — lihat task terpisah di bawah).
- `npm test`: 16/16 lolos.
- Smoke test fungsional: `.env.local` dikembalikan, `npm run start -p 3411` dijalankan, `curl http://localhost:3411/` dan `/traces` mengembalikan HTTP 200 dengan konten nyata ("Jumlah Query", "Daftar Trace") — mengonfirmasi Proxy tidak merusak fungsi query nyata ke Supabase.

**Commit:** `b31640e` (sama dengan Task 2 — kedua perbaikan `page.tsx`+`db.ts` satu commit `fix` karena satu root cause yang sama ditemukan+diperbaiki dalam satu sesi kerja berkelanjutan).

### Task — Perbaikan Tambahan yang Ditemukan Bersamaan (Bukan Bagian Rencana)

Dua defect kecil TIDAK TERKAIT langsung dengan bug staleness/build-DB, ditemukan selagi memverifikasi build/lint, diperbaiki di commit yang sama karena trivial dan langsung menghalangi verifikasi checkpoint ini:

1. **`trace-tree.test.ts` — TS2783 (key `span_id` duplikat).** `next build` gagal type-check dengan error `'span_id' is specified more than once, so this usage will be overwritten` di `makeSpan()` (helper test M5.2) — `span_id: overrides.span_id` eksplisit lalu `...overrides` di baris berikutnya menimpa key yang sama. Diperbaiki dengan menghapus baris eksplisit yang redundan (tipe tetap valid karena `overrides` sudah dijamin `Pick<Span, "span_id">`). Murni penghapusan dead code, tidak ada keputusan desain — tidak didokumentasikan sebagai entri `decisions.md` terpisah, hanya dicatat di sini.
2. **`db.ts` — directive `eslint-disable-next-line no-var` basi.** `npm run lint` melaporkan warning "Unused eslint-disable directive" untuk komentar yang mengawal `declare global { var ... }`. Dihapus karena rule `no-var` ternyata tidak lagi menyasar `var` di ambient `declare global` context pada versi eslint-config-next yang dipakai project ini.

**Commit:** `b31640e` (sama).

---

## Checkpoint 3 — Workflow CI `dashboard/`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 4 — Buat `dashboard/.github/workflows/ci.yml`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `dashboard/.github/workflows/ci.yml` dengan 3 job (`lint`, `test`, `build`), masing-masing `actions/checkout@v4` + `actions/setup-node@v4` (node 22, cache npm) + `npm ci`, lalu command sesuai job. Trigger `push`+`pull_request` ke `main`.

**Hasil Verifikasi**
`npm ci` (clean install dari lockfile) lalu `npm run lint`/`npm test`/`npm run build` seluruhnya sukses secara lokal — `lint`: 0 masalah; `test`: 16/16 lolos; `build`: sukses, route table `ƒ Dynamic` untuk seluruh 3 halaman.

**Commit:** `5d0cdf0` — `ci(dashboard): workflow lint+test+build`

---

## Checkpoint 4 — Repo GitHub Baru + Push Pertama

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 5 — Buat repo GitHub baru

**Kesesuaian dengan plan:** Sesuai plan. Konfirmasi eksplisit diminta lewat `AskUserQuestion` sebelum eksekusi (sesuai catatan "butuh konfirmasi terpisah" di plan) — user menjawab "Ya, lanjutkan".

**Apa yang dilakukan**
`gh repo create Ardiyanto24/nirwana-observability-dashboard --public` berhasil, menghasilkan `https://github.com/Ardiyanto24/nirwana-observability-dashboard`.

### Task 6 — Tambah remote + push

**Apa yang dilakukan**
Re-verifikasi riwayat commit bersih dari kredensial (`git log --all --diff-filter=A --name-only`, hanya `.env.local.example` yang muncul — placeholder, aman). `git remote add origin ...` + `git push -u origin main` (8 commit).

**Hasil Verifikasi**
`gh repo view` mengonfirmasi `visibility: PUBLIC`, `defaultBranchRef: main`. `gh api repos/.../commits` menunjukkan commit `5d0cdf0`/`b31640e` (2 commit terbaru sesi ini) benar-benar ada di remote, sha cocok persis dengan `git log` lokal.

**Commit:** — (aksi git/infra, tidak ada commit kode baru di checkpoint ini).

---

## Checkpoint 5 — Verifikasi CI Nyata (Baseline)

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 7 — Konfirmasi run CI pertama

**Kesesuaian dengan plan:** Sesuai plan.

**Hasil Verifikasi**
`gh run list` menunjukkan 1 run (`32638914544`, trigger `push`), status `completed success`. `gh run view` merinci ketiga job: `lint (eslint)` ✓ 23s, `build (next build)` ✓ 26s, `test (vitest)` ✓ 23s — seluruhnya hijau di GitHub Actions sungguhan (bukan asumsi dari isi file).

---

## Checkpoint 6 — Branch Protection `main`

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 8 — Aktifkan branch protection

**Kesesuaian dengan plan:** Sesuai plan. Konfirmasi eksplisit diminta lewat `AskUserQuestion` sebelum eksekusi — user menjawab "Ya, lanjutkan".

**Apa yang dilakukan**
Nama context status check dikonfirmasi persis dulu (`gh api repos/.../commits/main/check-runs --jq '.check_runs[].name'` → `"lint (eslint)"`, `"test (vitest)"`, `"build (next build)"`) sebelum mengaktifkan protection, supaya string context tidak salah ketik. Percobaan pertama via `gh api -f` gagal (`strict` dikirim sebagai string "false", bukan boolean — API menolak dengan 422). Diperbaiki dengan mengirim body JSON eksplisit lewat `--input -` (heredoc), memastikan tipe boolean benar.

**Error/Kegagalan (jika ada)**
```
{"message":"Invalid request.\n\nNo subschema in \"anyOf\" matched.\nFor 'properties/strict', \"false\" is not a boolean...","status":"422"}
```

**Diagnosis dan Perbaikan**
Ganti pendekatan dari `-f key=value` (selalu string) ke `--input -` dengan body JSON literal (`"strict": false` sebagai boolean asli). Berhasil di percobaan kedua.

**Hasil Verifikasi**
`gh api repos/.../branches/main/protection --jq '.required_status_checks.contexts'` mengembalikan `["lint (eslint)","test (vitest)","build (next build)"]`.

---

## Checkpoint 7 — PR Percobaan: Pelanggaran ESLint

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 9 — PR percobaan eslint

**Kesesuaian dengan plan:** Menyimpang sedikit dari plan — plan menyebut contoh pelanggaran "variabel tidak terpakai", tapi percobaan pertama dengan itu (`@typescript-eslint/no-unused-vars`) TERNYATA cuma **warning** (severity 1) di config `eslint-config-next` project ini, bukan error — exit code `npm run lint` tetap 0, tidak akan menggagalkan CI. Diganti pelanggaran `react-hooks/rules-of-hooks` (severity 2/error) — hook dipanggil kondisional di fungsi trial `TrialBadHookUsage`.

**Apa yang dilakukan**
Branch `test/eslint-violation`, tambah kode pelanggaran hooks sengaja di `src/lib/format.ts`, diverifikasi lokal (`npm run lint` → exit 1, error nyata), commit+push, buka PR #1.

**Temuan**
`@typescript-eslint/no-unused-vars` = warning (severity 1) di config project ini, bukan error — dicek via `npx eslint --print-config`. `react-hooks/rules-of-hooks` = error (severity 2).

**Hasil Verifikasi**
`gh pr checks 1 --watch`: job `lint` FAIL, `build` FAIL (Next.js `next build` juga menjalankan eslint internal, jadi ikut gagal — konsisten, bukan bug), `test` PASS (tidak terkait). `gh pr view --json mergeable,mergeStateStatus` → `mergeStateStatus: BLOCKED`, `mergeable: MERGEABLE` (artinya tidak ada conflict, tapi diblokir status check).

PR ditutup tanpa merge (`gh pr close 1 --delete-branch`), branch lokal dihapus.

**Commit:** `2d6fcbb` (di branch percobaan, dihapus setelah verifikasi — tidak masuk `main`).

---

## Checkpoint 8 — PR Percobaan: Assertion Vitest Gagal

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 10 — PR percobaan vitest

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Branch `test/vitest-failure`, ubah 1 assertion di `format.test.ts` (`formatPercent(1)` diharapkan `"999.9%"`, padahal hasil sebenarnya `"100.0%"`), diverifikasi lokal (vitest melaporkan "1 failed | 15 passed"), commit+push, buka PR #2.

**Hasil Verifikasi**
`gh pr checks 2 --watch`: job `lint` PASS, `build` PASS, `test` FAIL — kali ini terisolasi bersih (hanya job yang relevan yang gagal, membuktikan job independen satu sama lain). `mergeStateStatus: BLOCKED`.

PR ditutup tanpa merge, branch dihapus (remote+lokal).

**Commit:** `c6fa12e` (di branch percobaan, dihapus).

---

## Checkpoint 9 — Koneksi Vercel (Git Integration)

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 11 — Cek autentikasi CLI

**Kesesuaian dengan plan:** Sesuai plan.

**Hasil Verifikasi**
`vercel whoami` → sudah terautentikasi sebagai `ardiyanto24042002-7951`. Tidak perlu PAUSE untuk login.

### Task 12 — `vercel link` + sambungkan git

**Kesesuaian dengan plan:** Sesuai plan, tapi lebih sederhana dari dugaan — `vercel link --yes` TERNYATA membuat project baru DAN menyambungkan repo GitHub SEKALIGUS dalam satu command (bukan dua langkah terpisah seperti diduga plan). Konfirmasi eksplisit diminta lewat `AskUserQuestion` sebelum eksekusi — user menjawab "Ya, lanjutkan".

**Apa yang dilakukan**
`vercel link --yes` dari folder `dashboard/`. Output CLI: `✓ Created ardiyanto-s-projects/dashboard`, `> Connecting GitHub repository: https://github.com/Ardiyanto24/nirwana-observability-dashboard`, `> Connected`.

**Temuan**
CLI juga menambahkan `.vercel`+`.env*` DUPLIKAT ke `.gitignore` (baris sudah ada dari `create-next-app` scaffold sebelumnya) — dibersihkan langsung (dikembalikan ke isi identik versi ter-commit, jadi tidak perlu commit baru).

**Hasil Verifikasi**
`vercel project ls` menunjukkan project baru `dashboard` di bawah `ardiyanto-s-projects`. `.vercel/project.json` berisi `projectId`/`orgId` valid. Bukti konklusif koneksi git baru didapat lebih kuat di Checkpoint 11 (deploy preview nyata muncul otomatis dari PR).

**Commit:** — (tidak ada perubahan bersih untuk di-commit — `.gitignore` dikembalikan ke isi identik).

---

## Checkpoint 10 — Env Var `DATABASE_URL` di Vercel

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 13 — User menjalankan `vercel env add`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Agent memberi instruksi persis (3 command `vercel env add DATABASE_URL <environment>` untuk production/preview/development, nilai disalin user dari `.env.local` mereka sendiri) tanpa pernah melihat/memasukkan value. User menjalankan sendiri, sempat bertanya soal prompt "Git branch?" saat mengisi environment `preview` — dijawab: kosongkan (Enter) supaya berlaku untuk seluruh branch Preview, bukan dibatasi satu branch spesifik (PR percobaan Checkpoint 11 memakai branch baru yang belum ada saat itu).

**Hasil Verifikasi**
`vercel env ls` menunjukkan `DATABASE_URL` terdaftar `Encrypted` untuk ketiga environment (Development/Preview/Production) — value tidak pernah ditampilkan/dilihat agent.

**Commit:** — (aksi konfigurasi eksternal, bukan file kode).

---

## Checkpoint 11 — Verifikasi Deploy Preview Nyata (KK M8.6 butir 3)

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 14 — PR valid + verifikasi preview

**Kesesuaian dengan plan:** Sesuai plan — perubahan valid yang dipilih adalah menulis ulang `README.md` (masih boilerplate `create-next-app` sejak M5.2, belum pernah disesuaikan project ini).

**Apa yang dilakukan**
Branch `docs/readme-vercel-note`, `README.md` ditulis ulang (deskripsi project, cara jalan lokal, struktur, catatan CI/CD), commit+push, buka PR #3.

**Hasil Verifikasi**
`gh pr checks 3 --watch`: job `lint`/`test`/`build` PASS, PLUS check `Vercel` (deployment) PASS dengan pesan "Deployment has completed", dan check `Vercel Preview Comments` PASS. Komentar bot Vercel di PR memuat URL preview nyata: `https://dashboard-blush-gamma-47.vercel.app`.

Dikunjungi via browser tool (bukan asumsi dari komentar semata): `/` menampilkan "Observability — Dashboard Publik" dengan data nyata (Jumlah Query=12, Tingkat Keberhasilan=16.7%, tabel distribusi status/latency per layer/frekuensi error.type terisi data sungguhan dari Supabase). `/traces` menampilkan "Daftar Trace" dengan 12 baris trace nyata (termasuk trace verifikasi M5.2/M5.3/M6.1/M6.2 sebelumnya).

**Commit:** `d841433` (di branch PR, dimerge di Checkpoint 12).

---

## Checkpoint 12 — Verifikasi Production Deploy

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 15 — Merge + verifikasi production

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
PR #3 di-merge (`gh pr merge 3 --squash --delete-branch`) menghasilkan commit `742b47c` di `main`. Local `main` disinkronkan (`git pull --ff-only`).

**Temuan**
`vercel ls` menunjukkan deployment Production baru (`dashboard-kbsr4kdtj-...`, status Ready, 12s duration) muncul otomatis dalam hitungan detik setelah merge — TANPA campur tangan manual (murni git integration). `vercel inspect` pada deployment itu menunjukkan `target: production` dan daftar alias termasuk `dashboard-blush-gamma-47.vercel.app` (sama seperti preview sebelumnya, kini dialihkan ke production) dan `dashboard-ardiyanto-s-projects.vercel.app`.

**Penemuan tak terduga (dicatat jujur, bukan blocker):** alias `dashboard-ardiyanto-s-projects.vercel.app` (nama proyek) mengarahkan ke halaman login Vercel (deployment protection tim/akun default) saat dikunjungi browser — TIDAK bisa diakses publik tanpa autentikasi Vercel. Alias `dashboard-blush-gamma-47.vercel.app` (nama acak bawaan deploy pertama) sebaliknya publik tanpa hambatan. Ini bukan bug kode — murni setting default Vercel untuk project di bawah scope tim (`ardiyanto-s-projects`). Dicatat sebagai temuan di Bagian 5 `report.md`, BUKAN diperbaiki sepihak di milestone ini (mengubah Deployment Protection adalah setting akun Vercel, di luar cakupan literal KK M8.6 yang hanya minta "URL production nyata... dibuktikan konten sesuai commit terbaru" — terpenuhi lewat alias yang publik).

**Hasil Verifikasi**
`https://dashboard-blush-gamma-47.vercel.app` dikunjungi ulang setelah merge — konten identik dengan sebelumnya (data live Supabase, README yang baru di-merge tidak dirender di UI karena memang dokumentasi murni, tidak memengaruhi tampilan aplikasi).

---

## Checkpoint 13 — Dokumentasi dan Penutupan

**Mulai:** 2026-08-23 · **Selesai:** 2026-08-23

### Task 16-18

Lihat `report.md` dan pembaruan `CLAUDE.md`/`AGENT.md` di commit terkait.
