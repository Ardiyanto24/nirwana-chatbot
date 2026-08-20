# Decisions — Milestone 5.3: Membangun Tampilan Waterfall Trace dan Daftar Turn

Dokumen ini mencatat keputusan desain yang diambil untuk Milestone 5.3, seluruhnya ditentukan sebelum implementasi dimulai (dari Plan Mode, riset 2 agent Explore + 1 agent Plan, diverifikasi ulang baca langsung file kunci). Seluruh entri Jenis B (Preseden/Forced/Beralasan) — tidak ada keputusan genuinely-terbuka yang butuh `AskUserQuestion` di milestone ini.

---

## Keputusan 1: Rendering Waterfall — Plain CSS Grid + Tailwind, Tanpa Library Chart

**Sumber Paksaan**
Precedent zero-chart-dependency ganda: `dashboard/package.json` (belum ada d3/recharts/visx/chart.js) DAN `nirwana-database/web/package.json` (satu-satunya preseden Next.js lain di ekosistem project ini, juga nol dependency chart). Sifat visual yang diminta (Lingkup M5.3: "batang horizontal proporsional durasi") murni tata letak geometris, bukan chart matematis (bar/line/pie agregat).

**Keputusan yang Diikuti**
Waterfall dirender `<div>` + Tailwind utility class biasa — posisi (`offsetPct`) dan lebar (`widthPct`) bar dihitung sebagai fungsi murni dari data `TraceDetail`, diterapkan lewat inline `style` (persentase tidak bisa diekspresikan lewat utility class Tailwind statis karena nilainya dinamis per-span).

**Catatan Ketergantungan**
Kalau kelak dibutuhkan interaktivitas kompleks (zoom, pan, brush-select rentang waktu) yang di luar cakupan KK1/KK2 M5.3, revisit kebutuhan library saat itu — jangan diantisipasi sekarang tanpa bukti kebutuhan nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Library chart umum (recharts/visx/d3)** — ditolak: menambah dependency signifikan untuk kebutuhan yang genuinely sederhana (tata letak proporsional, bukan agregasi/statistik), tidak konsisten precedent zero-dependency project ini.
- **Library Gantt-chart khusus** (mis. `react-gantt-chart`) — ditolak: dependency niche tambahan untuk use-case yang cukup dilayani ~100 baris kode custom, dan kontrol penuh atas markup lebih penting untuk penanda visual KK2 (3-sinyal, lihat Keputusan 4) daripada kenyamanan API library pihak ketiga.

---

## Keputusan 2: Kalkulasi Posisi — Timeline Absolut, Bukan Relatif per-Parent

**Sumber Paksaan**
KK1 literal: "hubungan induk-anak yang benar" menuntut span di kedalaman berbeda tetap bisa dibandingkan visual secara valid — timeline relatif-per-parent akan membuat skala berbeda-beda antar level kedalaman, merusak perbandingan itu.

**Keputusan yang Diikuti**
`t0` = `trace.started_at`, `totalMs` = `max(trace.ended_at, max(span.started_at + span.duration_ms))` − `t0` (fallback kalau `ended_at` null, field ini `string | null` di kontrak `Trace`). `offsetPct`/`widthPct` tiap span dihitung terhadap `t0`/`totalMs` yang SAMA untuk seluruh trace, bukan dihitung ulang relatif terhadap `started_at` parent masing-masing.

**Catatan Ketergantungan**
Guard `Math.max(totalMs, 1)` untuk mencegah pembagian oleh nol pada trace dengan durasi ~0.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Skala relatif per-parent** (tiap subtree punya skala 0-100% sendiri) — ditolak: merusak validitas perbandingan visual lintas-kedalaman, bertentangan langsung KK1.

---

## Keputusan 3: `computeWaterfallRows()` sebagai Ekstensi `trace-tree.ts`

**Sumber Paksaan**
`trace-tree.ts` (M5.2) sudah eksplisit didesain sebagai rumah "fungsi MURNI (tanpa I/O)... supaya bisa diuji terisolasi" (komentar file itu sendiri) — `computeWaterfallRows()` punya sifat identik (murni, tanpa I/O), forced masuk file yang sama, bukan file baru.

**Keputusan yang Diikuti**
Tambah `computeWaterfallRows(detail: TraceDetail): WaterfallRow[]` ke `dashboard/src/lib/trace-tree.ts` — DFS pre-order atas `detail.tree` (bukan flat sort ulang, karena `buildSpanTree()` sudah menjamin urutan anak per node mengikuti `started_at`), kembalikan flat list `{span, depth, offsetPct, widthPct}` siap dirender baris demi baris. Kasus uji baru ditambah ke `trace-tree.test.ts` (mirror pola `buildSpanTree()`: multi-wave sibling, `error_type` terisi, `duration_ms=null`).

**Catatan Ketergantungan**
Tidak ada — konsisten pola existing 100%.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Rekursi langsung di JSX komponen React** — ditolak: sulit diuji terisolasi (butuh render React untuk test), melanggar prinsip pemisahan pure-function-vs-I/O yang sudah ditetapkan M5.2.

---

## Keputusan 4: Penanda Span Gagal — 3 Sinyal Independen

**Sumber Paksaan**
KK2 literal: "penanda visual yang jelas berbeda" — prinsip aksesibilitas dasar (tidak boleh cuma warna, colorblind-safe) dianggap bagian dari "jelas berbeda" yang genuine, bukan sekadar estetika.

**Keputusan yang Diikuti**
Span dengan `error_type !== null` ditandai lewat TIGA sinyal bersamaan: (1) warna bar merah vs netral untuk berhasil; (2) `border-dashed` (bentuk berbeda, bukan cuma hue) untuk bar gagal vs solid untuk berhasil; (3) teks `error_type` eksplisit ditampilkan sebagai badge kecil di label span (bukan cuma ikon) — supaya JENIS kegagalan (`ditolak_otorisasi` vs `gagal_teknis`) juga terlihat, bukan cuma "ada kegagalan".

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Warna saja** — ditolak: gagal aksesibilitas dasar (red-green colorblindness), dan tidak membedakan JENIS kegagalan.
- **Ikon saja tanpa teks** — ditolak: ikon generik ("ada masalah") tidak menyampaikan jenis kegagalan spesifik yang relevan untuk debugging (tujuan inti dashboard observability).

---

## Keputusan 5: `listTraces(filters?)` — Filter di Sisi SQL

**Sumber Paksaan**
Preseden `decisions.md` M5.2 Keputusan 5 ("push logic ke DB, bukan JS") — filosofi sama berlaku untuk daftar trace. `postgres` (library existing) native mendukung fragment `sql\`\`` bersarang untuk WHERE dinamis aman-injection (dikonfirmasi baca `dashboard/node_modules/postgres/README.md` langsung).

**Keputusan yang Diikuti**
`listTraces(filters?: {status?, role_title?, session_id?}): Promise<Trace[]>` ditambah ke `dashboard/src/lib/traces.ts` — filter diterapkan lewat fragment SQL dinamis (`WHERE` kondisional per filter yang diisi), `ORDER BY started_at DESC`, bukan fetch-semua-lalu-`.filter()` di JavaScript.

**Catatan Ketergantungan**
`session_id` sudah terindeks eksplisit di `TraceRow` (`Field(index=True)`, M5.2); `status`/`role_title` belum — untuk skala data sample saat ini (belasan baris) tidak masalah, dicatat sebagai kandidat index tambahan kalau volume nyata (data PIC 6) nanti membuktikan itu jadi bottleneck — TIDAK dioptimasi prematur tanpa bukti.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fetch semua trace, filter di JS** — ditolak: tidak konsisten preseden M5.2, tidak scalable untuk M5.4/data asli PIC 6 volume lebih besar.

---

## Keputusan 6: Filter UI — `<form method="GET">` Native + `searchParams`

**Sumber Paksaan**
Dokumentasi resmi Next.js App Router (`dashboard/node_modules/next/dist/docs/`, dibaca langsung) — `searchParams: Promise<{...}>` pada `page.tsx` adalah pola idiomatic untuk filter, otomatis membuat halaman dynamic-rendered per-request. Konsisten pola `params: Promise<{traceId: string}>` yang sudah dipakai `debug/trace/[traceId]/page.tsx` (M5.2).

**Keputusan yang Diikuti**
`dashboard/src/app/traces/page.tsx` membaca `searchParams` (Server Component, `await listTraces(await searchParams)`), form filter native `<form method="GET">` (submit browser mengubah query string URL, trigger refetch Server Component) — nol client-side state/JavaScript tambahan.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`useSearchParams()`+`router.push()` client-side** — ditolak: kompleksitas tambahan (butuh `"use client"`, state management) yang tidak diperlukan untuk kebutuhan filter sederhana ini.

---

## Keputusan 7: Route Baru `/traces` + `/traces/[traceId]`, Hapus Route Debug Lama

**Sumber Paksaan**
Komentar kode M5.2 sendiri (`debug/trace/[traceId]/page.tsx`, `decisions.md` M5.2 Keputusan 8) eksplisit menjanjikan: "bersifat SEMENTARA, akan digantikan begitu M5.3 membangun tampilan sungguhan".

**Keputusan yang Diikuti**
Halaman daftar trace di `/traces`, halaman detail di `/traces/[traceId]` (URL lebih natural untuk dashboard publik dibanding `/debug/trace/[traceId]`). `dashboard/src/app/api/debug/route.ts` dan `dashboard/src/app/debug/` DIHAPUS sepenuhnya (Checkpoint 6) setelah penggantinya (Checkpoint 4-5) terverifikasi bekerja — bukan dipertahankan sebagai endpoint tambahan.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mempertahankan `/debug/trace/[traceId]` sebagai endpoint developer terpisah** — ditolak: bertentangan langsung janji eksplisit komentar kode M5.2, dan dashboard publik tidak butuh endpoint "developer-only" tambahan yang tidak terhubung navigasi.

---

## Keputusan 8: Shell Aplikasi Dasar — Nav + Fixed Dark Theme

**Sumber Paksaan**
Konvensi (bukan kode) `nirwana-database/web` — satu-satunya preseden dashboard monitoring lain di ekosistem project ini, dengan alasan eksplisit di kode mereka sendiri: "monitoring dashboard, always dark by design, not dependent on OS preference". Prinsip project ini sendiri: dashboard publik wajib identik isinya dengan Grafana (default gelap).

**Keputusan yang Diikuti**
`dashboard/src/app/globals.css` diubah jadi fixed dark theme (hapus `@media (prefers-color-scheme: dark)`, `--background`/`--foreground` gelap permanen). `dashboard/src/components/Nav.tsx` (baru) — link ke `/` dan `/traces`. `layout.tsx`/`page.tsx` diganti dari boilerplate `create-next-app` jadi shell aplikasi nyata (`lang="id"`, metadata layak, Nav terpasang).

**Catatan Ketergantungan**
Ini konvensi VISUAL yang ditiru (warna, struktur layout), BUKAN kode yang disalin lintas repo — `nirwana-database/web` tetap repo terpisah, tidak ada dependency/import lintas repo.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Ikut `prefers-color-scheme` (default `create-next-app`)** — ditolak: tidak konsisten precedent dashboard monitoring sejenis di ekosistem ini, dan prinsip "identik dengan Grafana" (yang defaultnya gelap) lebih dekat dipenuhi tema gelap tetap.

---

## Keputusan 9: Data Sample Tambahan — Script Baru, Tidak Mengubah Data M5.2

**Sumber Paksaan**
Kebutuhan teknis nyata: data sample M5.2 (`sample-6d7f5cea8dfd`) tidak representasikan KK1 (hanya 1 span `orchestration.wave`, tidak ada "wave berbeda" ganda) maupun KK2 (semua `error_type=null`). Preseden lokasi seed script one-off: `milestones/<id>-<slug>/seed_*.py` (M5.2, M2.2, M2.4).

**Keputusan yang Diikuti**
`milestones/5.3-.../seed_kk_scenarios.py` (baru) — insert DUA trace tambahan (multi-wave untuk KK1, berstatus gagal untuk KK2), TIDAK menghapus/mengubah trace `sample-6d7f5cea8dfd` (M5.2) yang tetap valid untuk regresi (uji "1 trace lama + 2 trace baru semua tampil" di Checkpoint 4).

**Catatan Ketergantungan**
Atribut span (`wave.index`/`wave.intent_count`, `rbac.decision`, dst.) dikonfirmasi persis dari kode nyata (`src/orchestration/turn_pipeline.py`, `src/layers/domain_gate/otorisasi.py`), bukan dikarang bebas — supaya data sample representatif kasus produksi sungguhan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Modifikasi trace `sample-6d7f5cea8dfd` existing jadi multi-wave+gagal** — ditolak: merusak nilai regresi (trace itu sudah jadi bukti KK1/KK2 M5.1-nyata-mirip di M5.2, mengubahnya menghilangkan continuity); lebih aman menambah trace baru.

---

## Keputusan 10: Verifikasi UI Wajib Lewat Tool Browser, Bukan `curl`

**Sumber Paksaan**
Insiden nyata sesi sebelumnya (M5.2 lanjutan) — user tidak bisa akses `localhost:3000` di browser meski `curl` dari dalam tool berhasil, root cause dev server bind ke `::` (wildcard IPv6) yang bermasalah dari sisi browser user (Windows), teratasi dengan bind eksplisit `127.0.0.1`.

**Keputusan yang Diikuti**
Tiap checkpoint UI (Checkpoint 3, 4, 5, 6) diverifikasi lewat tool Browser (`preview_start`/`navigate`/`computer` screenshot/`read_page`/`get_page_text`/`read_console_messages`) — bukan `curl`/HTTP status code saja. Dev server dijalankan bind eksplisit `127.0.0.1` (bukan default wildcard) berdasar pelajaran insiden tersebut.

**Catatan Ketergantungan**
Tidak ada — murni penerapan pelajaran operasional dari insiden nyata.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced langsung oleh insiden nyata yang baru terjadi.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Rendering Waterfall — Plain CSS Grid + Tailwind, Tanpa Library Chart | B | Checkpoint 5 |
| 2 | Kalkulasi Posisi — Timeline Absolut, Bukan Relatif per-Parent | B | Checkpoint 5 |
| 3 | `computeWaterfallRows()` sebagai Ekstensi `trace-tree.ts` | B | Checkpoint 5 |
| 4 | Penanda Span Gagal — 3 Sinyal Independen | B | Checkpoint 5 |
| 5 | `listTraces(filters?)` — Filter di Sisi SQL | B | Checkpoint 4 |
| 6 | Filter UI — `<form method="GET">` Native + `searchParams` | B | Checkpoint 4 |
| 7 | Route Baru `/traces` + `/traces/[traceId]`, Hapus Route Debug Lama | B | Checkpoint 5, 6 |
| 8 | Shell Aplikasi Dasar — Nav + Fixed Dark Theme | B | Checkpoint 3 |
| 9 | Data Sample Tambahan — Script Baru, Tidak Mengubah Data M5.2 | B | Checkpoint 2 |
| 10 | Verifikasi UI Wajib Lewat Tool Browser, Bukan `curl` | B | Checkpoint 3, 4, 5, 6 |
