# Decisions — Milestone 5.2: Membangun Skema Data dan Koneksi Next.js ke Supabase

Dokumen ini mencatat keputusan desain yang diambil untuk Milestone 5.2, seluruhnya ditentukan sebelum implementasi dimulai (dari Plan Mode, riset 2 agent Explore + 1 agent Plan, diverifikasi ulang baca langsung file kunci).

---

## Keputusan 1: Lokasi Proyek Next.js — Folder di Repo Ini vs Repo Git Terpisah

**Status:** Diputuskan sebelum implementasi (dari plan), dikonfirmasi user via `AskUserQuestion`.

**Latar Belakang**
`CLAUDE.md` mencatat lokasi folder Next.js untuk PIC 5 sebagai "belum ditentukan, keputusan konkret diajukan ke user saat Milestone 5.2 dimulai". Riset awal salah mengasumsikan preseden satu-satunya di ekosistem ini (`nirwana-database/web/`) adalah subfolder biasa — verifikasi langsung (`git status`/`.gitignore` repo tetangga) menunjukkan itu genuinely repo Git terpisah (`.git` sendiri, remote `nirwana-monitoring-web`, di-gitignore eksplisit oleh repo induk dengan komentar "developed here locally but deployed from their own separate repos"). Genuinely terbuka: dua opsi (folder di `nirwana-chatbot` vs repo terpisah) sama-sama valid secara teknis.

**Keputusan yang Dipilih**
Repo Git **terpisah**, di-nest di filesystem lokal di `nirwana-chatbot/dashboard/` (mirror persis pola `nirwana-database/web`), digitignore oleh repo `nirwana-chatbot`, **tanpa remote/push** untuk saat ini.

**Alasan**
Mengikuti preseden nyata satu-satunya yang ada di ekosistem project ini — bukan preferensi baru. Agent Plan sempat merekomendasikan folder-di-repo-ini (argumen: belum ada milestone deployment, overhead dua `CLAUDE.md`/`AGENT.md`), tapi user memilih mengikuti pola tetangga secara konsisten.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Folder top-level di dalam `nirwana-chatbot`** (mis. `nirwana-chatbot/dashboard/` sebagai bagian repo yang sama) — dipertimbangkan (direkomendasikan agent Plan sebagai opsi lebih sederhana untuk fase dev saat ini), tapi ditolak user demi konsistensi dengan preseden nyata `nirwana-database/web`.

**Dampak**
Riwayat commit sesi ini akan terpecah dua repo (`nirwana-chatbot` untuk file Python/dokumentasi milestone, `dashboard/` untuk kode Next.js) — dicatat eksplisit di `logs.md` commit mana masuk repo mana. Tidak ada dampak ke M5.1 (sudah selesai, jalur Grafana independen total).

---

## Keputusan 2: Library Postgres Client Node — `postgres` vs `pg` vs ORM

**Sumber Paksaan**
Bukan forced murni — keputusan teknis beralasan (dicatat Jenis B karena tidak genuinely terbuka setelah riset: bukti teknis konkret mengarah satu opsi, bukan preferensi berimbang).

**Keputusan yang Diikuti**
Library `postgres` (porsager/postgres) untuk query Postgres langsung dari Next.js — bukan `pg` (node-postgres) atau ORM (Prisma/Drizzle).

**Catatan Ketergantungan**
- TypeScript-native (tanpa `@types/pg` komunitas terpisah), API tagged-template (`` sql`...` ``) memberi parameterisasi aman-injection tanpa placeholder manual — konsisten KK2 ("siap pakai tanpa transformasi rumit").
- ORM ditolak: over-engineering untuk 2 tabel read-only berskema tetap (kontrak Bagian 4 tidak boleh diubah), tidak konsisten pola minimalis Python (SQLModel langsung, tanpa Alembic).
- `pg` tetap valid tapi hasil query default `any`-typed per baris kecuali digenerikkan manual tiap query — boilerplate lebih banyak.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`pg` (node-postgres)** — ditolak: lebih matang tapi butuh generic typing manual tiap query, lebih banyak boilerplate.
- **Prisma/Drizzle (ORM)** — ditolak: skema sudah dikunci mati (Bagian 4), migration tooling ORM tidak dibutuhkan untuk 2 tabel read-only; tidak konsisten pola Python (tanpa Alembic).

---

## Keputusan 3: Connection Pooler dan SSL — Session Pooler (5432) + SSL Eksplisit

**Sumber Paksaan**
Kebutuhan teknis nyata (default SSL berbeda antar bahasa/library) + karakteristik Transaction Pooler Supabase (PgBouncer/Supavisor, prepared statement tidak aman lintas koneksi pooled — didokumentasikan resmi oleh Supabase maupun maintainer `postgres.js`).

**Keputusan yang Diikuti**
`DATABASE_URL` Node (`dashboard/.env.local`) memakai **Session Pooler (port 5432)**, bukan Transaction Pooler (6543) yang dipakai backend Python. SSL eksplisit: `?sslmode=require` di connection string DAN opsi `ssl: 'require'` di kode client — tidak mengandalkan parsing URL implisit.

**Catatan Ketergantungan**
`psycopg3` Python default `sslmode=prefer` (coba TLS, fallback diam-diam ke plaintext kalau ditolak) — makanya `src/config/database.py` jalan tanpa parameter SSL eksplisit. `postgres.js`/`pg` default `ssl:false` TANPA fallback — connection string yang sama persis dari `.env` Python TIDAK menjamin hasil sama kalau di-copy-paste apa adanya ke Node. Kalau nanti perlu Transaction Pooler (mis. kebutuhan serverless skala besar), tambahkan opsi `{ prepare: false }` yang disediakan `postgres.js` khusus untuk itu — ditunda karena tidak relevan untuk dashboard internal low-traffic M5.2.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Pakai Transaction Pooler (6543) sama seperti Python, prepared statement default aktif** — ditolak: berisiko intermittent error prepared-statement di lingkungan pooled tanpa `{ prepare: false }` eksplisit, kompleksitas tambahan yang tidak perlu untuk skala M5.2.

---

## Keputusan 4: Modul Koneksi Singleton (`globalThis`-guarded)

**Sumber Paksaan**
Padanan langsung pola `@lru_cache get_engine()` di `src/config/database.py` (Python) — menjaga simetri arsitektur; mencegah Next.js dev server (Fast Refresh) membuka koneksi baru tiap file disimpan (pola resmi yang direkomendasikan ekosistem Prisma/Next.js untuk masalah serupa).

**Keputusan yang Diikuti**
`dashboard/src/lib/db.ts` cache instance client `postgres` di `globalThis`, dijaga `process.env.NODE_ENV !== 'production'`.

**Catatan Ketergantungan**
Tuning connection-pool khusus lingkungan serverless (`max:1` per instance, hindari Edge Runtime karena butuh raw TCP socket) **DITUNDA** ke milestone deployment — belum ada di M5.1-5.4 manapun, dicatat sebagai follow-up di `report.md`, bukan diabaikan begitu saja.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — pola ini forced by kebutuhan mencegah connection leak saat dev, sudah ada padanan persis di sisi Python yang tinggal ditiru.

---

## Keputusan 5: Dua Query Terpisah (`traces` + `spans`), Bukan Satu JOIN

**Sumber Paksaan**
KK2 M5.2 ("struktur siap pakai tanpa transformasi rumit") + karakteristik data nyata (trace M5.1 punya 28 span).

**Keputusan yang Diikuti**
`getTraceWithSpans()` menjalankan `SELECT * FROM traces WHERE trace_id = $1` dan `SELECT * FROM spans WHERE trace_id = $1 ORDER BY started_at ASC` secara paralel (`Promise.all`), bukan satu query JOIN. Index eksplisit ditambahkan ke `spans.trace_id` saat provisioning (Postgres tidak otomatis mengindeks kolom FK di sisi child).

**Catatan Ketergantungan**
Kalau nanti volume span per trace jadi jauh lebih besar (ratusan+), pertimbangkan ulang strategi query — tapi tidak relevan untuk skala M5.2 (data contoh manual, belasan-puluhan span).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu query JOIN `traces` × `spans`** — ditolak: menduplikasi 6 kolom `traces` di tiap baris span (28× untuk trace M5.1) tanpa manfaat, hasilnya butuh logic pisah-kelompok tambahan di JS sebelum siap dipakai komponen — lebih banyak transformasi, bukan lebih sedikit, bertentangan langsung dengan KK2.

---

## Keputusan 6: Bentuk Output — Flat `spans[]` DAN `tree: SpanNode[]`

**Sumber Paksaan**
KK1 ("tersusun sesuai urutan waktu DAN hubungan induk-anaknya") + KK2 ("siap pakai komponen tanpa transformasi rumit") + kebutuhan tidak menebak detail render M5.3 (di luar cakupan M5.2) secara berlebihan.

**Keputusan yang Diikuti**
`getTraceWithSpans()` mengembalikan `TraceDetail = { trace, spans, tree }` — `spans` flat terurut `started_at`, `tree: SpanNode[]` bersarang by `parent_span_id` (dibangun via `buildSpanTree()` di lapisan query, BUKAN diserahkan ke komponen).

**Catatan Ketergantungan**
M5.3 (waterfall UI, di luar cakupan M5.2) kemungkinan butuh `spans` flat untuk hitung offset horizontal relatif `trace.started_at`, dan `tree` untuk struktur bersarang visual — menyediakan keduanya menghindari M5.2 harus menebak detail kebutuhan render M5.3 lebih jauh dari itu. M5.2 sengaja TIDAK menghitung offset piksel/warna/keputusan visual apa pun — itu wilayah M5.3.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hanya kembalikan `tree` bersarang** — ditolak: M5.3 kemungkinan butuh list rata terurut waktu untuk kalkulasi posisi waterfall, memaksa M5.3 meratakan ulang tree kalau hanya `tree` yang disediakan.
- **Hanya kembalikan `spans` flat, biarkan komponen bangun tree sendiri** — ditolak langsung oleh KK2 ("tidak perlu transformasi tambahan yang rumit di sisi komponen") — mengelompokkan flat list by `parent_span_id` adalah transformasi non-trivial.

---

## Keputusan 7: Lokasi Seed Script — `milestones/5.2-.../`, Bukan `src/`

**Sumber Paksaan**
Preseden persis `milestones/2.2-pemeriksaan-otorisasi/seed_role_permissions.py` dan `milestones/2.4-verification-gate/seed_employees.py` — script provisioning data sekali-jalan hidup di dalam folder milestone-nya sendiri, bukan `src/` (isinya cuma runtime app) atau `scripts/` (folder ini tidak ada di project ini).

**Keputusan yang Diikuti**
`milestones/5.2-skema-data-koneksi-nextjs-supabase/seed_sample_trace.py`, mirror pola `seed_employees.py`: `SQLModel.metadata.create_all(engine)` dipanggil DI DALAM script (bukan langkah manual terpisah), reuse `get_engine()` dari `src/config/database.py`.

**Catatan Ketergantungan**
Model `TraceRow`/`SpanRow` tetap didefinisikan di `src/db/models.py` (konsisten 6 model existing) — hanya SCRIPT eksekusinya yang hidup di folder milestone.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — preseden project ini konsisten di 2 milestone sebelumnya, forced by konvensi yang sudah established.

---

## Keputusan 8: Verifikasi KK Lewat Route Debug JSON Mentah, Bukan Komponen UI

**Sumber Paksaan**
`docs/02-implementation-plan/rancangan-observability-dashboard.md` — Lingkup M5.2 eksplisit hanya "lapisan query dan tipe data", sementara "Membangun Tampilan Waterfall Trace dan Daftar Turn" adalah Milestone 5.3 terpisah.

**Keputusan yang Diikuti**
Route/page debug (`dashboard/src/app/api/debug/route.ts`, `dashboard/src/app/debug/trace/[traceId]/page.tsx`) menampilkan JSON mentah hasil query — bukan komponen visual waterfall jadi. Route ini bersifat SEMENTARA, akan digantikan (bukan dihapus tanpa pengganti) begitu M5.3 membangun tampilan sungguhan.

**Catatan Ketergantungan**
Kalau M5.3 nanti butuh bentuk data berbeda dari `TraceDetail` yang dirancang di sini, itu perlu dikomunikasikan balik — `TraceDetail` bukan kontrak beku, hanya desain awal berdasar KK M5.2.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Membangun komponen UI sederhana (bukan cuma JSON mentah) untuk verifikasi** — ditolak: di luar Lingkup M5.2, berisiko tumpang tindih pekerjaan M5.3.

---

## Keputusan 9: Kredensial Postgres Node Terpisah (Least-Privilege)

**Sumber Paksaan**
`CLAUDE.md` — "Rahasia tidak boleh di-hardcode atau di-commit. Gunakan kredensial least-privilege yang dipisah menurut pola akses (mis. kredensial exporter Supabase terpisah dari kredensial lain)."

**Keputusan yang Diikuti**
Role Postgres baru khusus Next.js (read-only, `GRANT SELECT` saja ke `traces`/`spans`), connection string-nya disimpan di `dashboard/.env.local` (repo terpisah, gitignored) — TERPISAH dari `DATABASE_URL` Python (yang punya akses read-write ke `session_memory_packages`/`roles`/dst.).

**Catatan Ketergantungan**
Kalau di masa depan Next.js butuh menulis data (di luar cakupan M5.2-5.4 manapun, seluruhnya murni baca), role ini perlu direvisi — TIDAK diantisipasi sekarang karena dashboard publik memang murni read-only by design.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse `DATABASE_URL` Python yang sama untuk Next.js** — ditolak eksplisit oleh prinsip arsitektur least-privilege; role Python py akses write ke tabel sensitif (Session Memory, roles) yang tidak relevan sama sekali untuk dashboard publik read-only.

---

## Keputusan 10: Unit Test Vitest untuk `buildSpanTree()`

**Sumber Paksaan**
Bukan forced — keputusan praktik-baik beralasan (Jenis B: biaya rendah, manfaat jelas, bukan preferensi terbuka yang perlu ditanya).

**Keputusan yang Diikuti**
`dashboard/src/lib/traces.test.ts` (Vitest) menguji `buildSpanTree()` dengan kasus span sengaja out-of-order dan bercabang (fungsi murni tanpa I/O, cocok diuji terisolasi tanpa perlu koneksi DB nyata).

**Catatan Ketergantungan**
Test pertama di stack Next.js project ini — set up Vitest (`vitest`, `@vitejs/plugin-react` kalau perlu) jadi bagian Task 8.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tidak ada unit test, andalkan verifikasi manual route debug saja** — ditolak: `buildSpanTree()` adalah logic non-trivial (transformasi flat→tree) yang rawan bug kasus edge (span bercabang, urutan tidak berurutan) yang mungkin tidak tertangkap satu data contoh manual di Checkpoint 2.

---

## Keputusan 11: `.gitignore` `nirwana-chatbot` Ditambah `dashboard/`

**Sumber Paksaan**
Konsekuensi langsung Keputusan 1 (repo terpisah nested) — mirror persis entri `.gitignore` `nirwana-database` untuk `web/`: *"api/ and web/ are developed here locally but deployed from their own separate repos"*.

**Keputusan yang Diikuti**
Tambah baris `dashboard/` ke `.gitignore` repo `nirwana-chatbot`, dengan komentar penjelasan mirror gaya tetangga.

**Catatan Ketergantungan**
Tidak ada — konsekuensi mekanis langsung dari Keputusan 1.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by Keputusan 1.

---

## Keputusan 12: Tidak Ada `git push`/Pembuatan Remote untuk Repo `dashboard/`

**Sumber Paksaan**
Instruksi umum project (`CLAUDE.md` "Git dan Kualitas Perubahan": "Jangan push atau membuat remote tanpa instruksi eksplisit pengguna").

**Keputusan yang Diikuti**
Repo `dashboard/` dibuat dan di-commit LOKAL saja sepanjang M5.2 — tidak ada `git remote add`, tidak ada `git push`, tidak ada pembuatan repo GitHub/GitLab.

**Catatan Ketergantungan**
Kalau user nanti ingin deploy (mis. ke Vercel, mengikuti pola tetangga), itu keputusan terpisah yang perlu instruksi eksplisit — dicatat sebagai follow-up potensial di `report.md`, bukan diasumsikan di sini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by instruksi standar project, tidak ada indikasi user memberi izin membuat remote/push di scope M5.2.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Lokasi Proyek Next.js — Folder di Repo Ini vs Repo Git Terpisah | A | Plan |
| 2 | Library Postgres Client Node — `postgres` vs `pg` vs ORM | B | Plan → Checkpoint 4 |
| 3 | Connection Pooler dan SSL — Session Pooler + SSL Eksplisit | B | Plan → Checkpoint 4 |
| 4 | Modul Koneksi Singleton (`globalThis`-guarded) | B | Checkpoint 4 |
| 5 | Dua Query Terpisah (`traces`+`spans`), Bukan Satu JOIN | B | Checkpoint 5 |
| 6 | Bentuk Output — Flat `spans[]` DAN `tree: SpanNode[]` | B | Checkpoint 5 |
| 7 | Lokasi Seed Script — `milestones/5.2-.../`, Bukan `src/` | B | Checkpoint 2 |
| 8 | Verifikasi KK Lewat Route Debug JSON Mentah | B | Checkpoint 5 |
| 9 | Kredensial Postgres Node Terpisah (Least-Privilege) | B | Checkpoint 2, 4 |
| 10 | Unit Test Vitest untuk `buildSpanTree()` | B | Checkpoint 5 |
| 11 | `.gitignore` `nirwana-chatbot` Ditambah `dashboard/` | B | Checkpoint 3 |
| 12 | Tidak Ada `git push`/Pembuatan Remote untuk Repo `dashboard/` | B | Checkpoint 3 |
