# Decisions — Milestone 5.4: Membangun Panel Agregat dan Metrik Ringkasan

Dokumen ini mencatat keputusan desain milestone 5.4 (PIC 5, milestone terakhir — melengkapi dashboard publik dengan panel agregat lintas seluruh trace tersimpan: jumlah query, tingkat keberhasilan, distribusi status, latency per layer, frekuensi error.type).

Seluruh 14 keputusan di bawah adalah **Jenis B (Preseden/Forced)** — tidak ada keputusan Jenis A (Genuinely Terbuka) di milestone ini. Plan awal sempat diajukan lebih tipis, ditolak user untuk digali lebih dalam ("riset lagi milestone 4.5 dengan lebih mendalam" — dikonfirmasi via `AskUserQuestion` sebagai typo untuk milestone 5.4); dua agent Explore terpisah dijalankan (riset makna istilah "query" di seluruh dokumen sumber, dan riset konvensi visual `nirwana-database/web` + tooling `dashboard/`) sebelum plan final ditulis ulang dan disetujui.

---

### Keputusan 1: Homepage `/` diisi jadi Halaman Ringkasan

**Sumber Paksaan**
`dashboard/src/components/Nav.tsx` (dibangun Milestone 5.3) sudah memuat `{ href: "/", label: "Ringkasan" }` di daftar link navigasi — homepage `/` sudah "dipesan" jadi halaman Ringkasan sejak M5.3, meski isinya saat itu masih stub sambutan+CTA ke `/traces`.

**Keputusan yang Diikuti**
Halaman `/` (`dashboard/src/app/page.tsx`) ditulis ulang berisi seluruh panel agregat M5.4, bukan route baru terpisah (mis. `/ringkasan`).

**Catatan Ketergantungan**
Kalau panel agregat ditaruh di route lain, label Nav "Ringkasan" yang mengarah ke `/` akan menyesatkan (link kosong/stub) — inkonsistensi navigasi yang dibangun sendiri di M5.3.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by `Nav.tsx` M5.3.

---

### Keputusan 2: "Jumlah Query" = `COUNT(*) FROM traces`

**Sumber Paksaan**
Istilah "query" tidak pernah didefinisikan formal di dokumen manapun (hanya muncul 3× di `docs/02-implementation-plan/rancangan-observability-dashboard.md`, seluruhnya di dalam Milestone 5.4 sendiri). Tiga bukti tekstual independen mengarah konsisten ke grain trace/turn:
1. Baris 91 (Output M5.4): "metrik agregat **lintas seluruh trace yang tersimpan** — jumlah query, tingkat keberhasilan..." — "jumlah query" berimpit kalimat langsung dengan "lintas seluruh trace".
2. Baris 94 (KK1): diverifikasi "cocok dengan penghitungan manual **terhadap data yang sama di Supabase**" — grain tabel `traces` dikunci `docs/01-architecture/rancangan-observability-ai-chatbot.md:103`: `-- Satu baris per trace (= satu turn user)`.
3. Panel Grafana M5.1 (rujukan eksplisit kesetaraan M5.4) yang paling dekat konsepnya berjudul **"Distribusi Status (per turn)"** — `milestones/5.1-membangun-dashboard-grafana/decisions.md:92` menegaskan eksplisit "level TURN, bukan level atomic-intent" untuk konteks panel agregat sejenis.

**Keputusan yang Diikuti**
Satu "query" = satu trace = satu turn user. "Jumlah Query" dihitung `COUNT(*) FROM traces`.

**Catatan Ketergantungan**
Kalau granularitas ini keliru, dampaknya murni label/angka tampilan satu StatCard — trivial dikoreksi tanpa mengubah struktur kode lain (fungsi `computeOverallStats()` tinggal diberi sumber data berbeda).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Jumlah atomic-intent (hasil Decomposition, M1.6)** — nol bukti tekstual mendukung; Grafana M5.1 sendiri eksplisit MENOLAK granularitas ini untuk panel agregat status sejenis ("Distribusi Status (per turn)", bukan per atomic-intent).
- **Jumlah pemanggilan `chatbot_api` sungguhan (Execution, M4.1/M4.2)** — kata "query" cuma dipakai bahasa sehari-hari satu kali di `docs/01-architecture/arsitektur-ai-chatbot-rbac.md:61` ("sebelum query apa pun jalan"), bukan istilah formal berdefinisi, dan tidak match grain tabel Supabase manapun yang sudah dikunci (`traces`/`spans` sama-sama bukan grain "satu panggilan chatbot_api").

---

### Keputusan 3: Distribusi Status Query Langsung dari `traces.status`

**Sumber Paksaan**
Skema Supabase (`src/db/models.py:161-179`, `TraceRow`) sudah menyediakan kolom `status` level-trace langsung. Panel Grafana M5.1 pembanding ("Distribusi Status (per turn)") terpaksa memproksi via atribut `riwayat.status` pada span `riwayat.simpan` (`infra/observability/grafana/dashboards/observability.json:88-100`, dikonfirmasi `milestones/5.1-membangun-dashboard-grafana/decisions.md:92`) — itu murni workaround keterbatasan Jaeger/Prometheus yang tidak punya konsep "field level-trace", bukan pilihan desain yang perlu ditiru caranya.

**Keputusan yang Diikuti**
`SELECT status, COUNT(*) FROM traces GROUP BY status`.

**Catatan Ketergantungan**
Meniru workaround proksi-span Grafana di sini justru menambah kompleksitas tanpa manfaat — Supabase tidak punya keterbatasan yang memaksanya. Kesetaraan isi (KK2) dipenuhi lewat hasil yang sama, bukan mekanisme teknis yang sama.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mereplikasi proksi span `riwayat.simpan`/`riwayat.status`** — ditolak karena tidak forced di Supabase (kolom trace-level sudah tersedia langsung), hanya menambah query join yang tidak perlu.

---

### Keputusan 4: Latency per Layer Dikelompokkan `layer_name` Saja

**Sumber Paksaan**
`spans.layer_name` (`src/db/models.py:195`, dikonfirmasi nilai nyata di `milestones/5.2-skema-data-koneksi-nextjs-supabase/seed_sample_trace.py`) sudah field nama-layer eksplisit (`"domain_gate"`, `"retriever"`, `"query_engine"`, dst) — BUKAN nama span mentah `operation_name` yang dipakai ulang (mis. `"chat"` dipakai puluhan span lintas layer). Panel Grafana "Latency per Layer (p95)" terpaksa memakai dimensi ganda `(span_name, prompt_id)` (`observability.json:72,79`) justru karena keterbatasan itu — `layer_name` di skema Supabase sudah menyelesaikan masalah itu di level skema.

**Keputusan yang Diikuti**
`GROUP BY layer_name` saja (tanpa dimensi kedua).

**Catatan Ketergantungan**
Menambah dimensi kedua tanpa alasan menambah kompleksitas query dan tampilan tanpa manfaat — `layer_name` sudah cukup disambiguasi.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`GROUP BY (layer_name, operation_name)`** — dipertimbangkan untuk presisi lebih detail, ditolak karena KK sumber minta "latency per layer" (bukan per operasi), dan `layer_name` saja sudah cukup untuk tujuan itu (identifikasi bottleneck per layer, sesuai tujuan panel Grafana aslinya: "agar bottleneck mudah diketahui dari melihat layer mana yang paling lama").

---

### Keputusan 5: Persentil via `PERCENTILE_CONT` (Postgres Native, Eksak)

**Sumber Paksaan**
Postgres native mendukung `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)` — persentil eksak dari baris data asli. Panel Grafana pembanding memakai `histogram_quantile()` (aproksimasi dari bucket histogram `spanmetricsconnector`), yang tercatat py keterbatasan `NaN` untuk span di luar rentang bucket default (`docs/keterbatasan-diterima.md` #18, ditemukan M5.1).

**Keputusan yang Diikuti**
`PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)` per `layer_name` di `spans` (filter `duration_ms IS NOT NULL`).

**Catatan Ketergantungan**
Ini justru LEBIH presisi dari Grafana (bukan sekadar setara) — cocok untuk KK1 yang eksplisit minta "cocok dengan penghitungan manual", dan tidak mewarisi keterbatasan #18 (bucket mismatch → NaN).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mereplikasi histogram bucket + `histogram_quantile()` ala Prometheus** — tidak ada infrastruktur histogram bucket di Supabase (`spans.duration_ms` kolom integer polos), membangunnya di sini hanya untuk meniru cara teknis Grafana adalah kerja tambahan tanpa manfaat, bahkan mewarisi kelemahan (aproksimasi, potensi NaN) yang tidak perlu.

---

### Keputusan 6: `totalTraces`/`successRate` Dihitung dari `statusDistribution`

**Sumber Paksaan**
Prinsip "satu sumber kebenaran" — kalau `totalTraces`/`successRate` dihitung dari query terpisah, ada risiko dua angka saling tidak konsisten (mis. race condition antar-query, atau logic hitung yang diam-diam berbeda). Menghitungnya dari hasil `statusDistribution` yang SAMA menghilangkan kelas masalah itu sepenuhnya.

**Keputusan yang Diikuti**
Fungsi murni baru `computeOverallStats(statusDistribution: StatusCount[])` → `{ totalTraces, successRate }`, dipanggil setelah `getStatusDistribution()` selesai — bukan query SQL count terpisah.

**Catatan Ketergantungan**
Fungsi ini murni (tanpa I/O) — testable via Vitest tanpa `server-only`/DB, mirror pola `computeWaterfallRows()`/`buildSpanTree()` (M5.2/M5.3).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Query `SELECT COUNT(*), COUNT(*) FILTER (WHERE status='berhasil') FROM traces` terpisah** — ditolak: duplikasi logic agregasi status yang sudah dikerjakan `getStatusDistribution()`, menambah satu round-trip query tanpa manfaat.

---

### Keputusan 7: Query Agregat di File Terpisah `summary.ts`

**Sumber Paksaan**
Pemisahan berdasar CONCERN, bukan I/O-boundary (beda dari alasan pemisahan `trace-tree.ts`/`traces.ts` M5.2): `dashboard/src/lib/traces.ts` berisi query PER-TRACE (`getTraceWithSpans`, `listTraces`), sedangkan M5.4 butuh query LINTAS-TRACE (agregat) — concern yang secara semantik berbeda meski sama-sama butuh `server-only`/koneksi DB.

**Keputusan yang Diikuti**
File baru `dashboard/src/lib/summary.ts` (`import "server-only"`, mirror pola `traces.ts`).

**Catatan Ketergantungan**
Menjaga `traces.ts` tetap fokus per-trace, memudahkan penelusuran kalau nanti ada bug — jelas dari nama file query mana yang agregat vs per-trace.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambahkan fungsi agregat langsung ke `traces.ts`** — dipertimbangkan (lebih sedikit file), ditolak karena `traces.ts` akan bercampur dua concern berbeda (per-trace vs lintas-trace) yang masing-masing bisa tumbuh sendiri-sendiri ke depannya.

---

### Keputusan 8: `humanizeDuration()` Diekstrak ke `format.ts`, Gaya Test Mengikuti `trace-tree.test.ts` Persis

**Sumber Paksaan**
`dashboard/src/components/WaterfallRow.tsx` sudah py `humanizeDuration()` lokal (tidak diekspor) yang dibutuhkan lagi untuk menampilkan `avg_ms`/`p95_ms` di panel latency M5.4 — duplikasi logic format kalau tidak diekstrak. Riset tooling (`dashboard/package.json`, tidak py `vitest.config.ts`/`@testing-library`/`jsdom`) mengonfirmasi test project ini murni logic-only, dan `trace-tree.test.ts:2` memakai import RELATIF (`from "./trace-tree"`) bukan alias `@/lib/...` — karena alias TIDAK diresolusi Vitest tanpa config path tambahan yang belum ada.

**Keputusan yang Diikuti**
`humanizeDuration()` DIPINDAH (bukan disalin) ke `dashboard/src/lib/format.ts`, ditambah `formatPercent(ratio: number)` baru. `WaterfallRow.tsx` mengimpor dari sana. Test baru `format.test.ts` pakai `import { describe, expect, it } from "vitest"` + import relatif `from "./format"`, TANPA `vitest.config.ts`/testing-library baru.

**Catatan Ketergantungan**
Kalau memakai alias `@/lib/format` di test, kemungkinan besar test gagal resolve import (Vitest 4 zero-config di project ini tidak baca `tsconfig.json` path mapping tanpa plugin tambahan) — forced ikut pola relatif yang sudah terbukti bekerja.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Duplikasi `humanizeDuration()` di komponen baru panel latency** — ditolak, duplikasi logic yang sama persis di dua tempat.
- **Tambah `vitest.config.ts` + `vite-tsconfig-paths` supaya bisa pakai alias `@/lib/format` di test** — ditolak sebagai scope creep: mengubah konfigurasi tooling project di luar kebutuhan literal milestone ini, dan pola relatif existing sudah terbukti bekerja tanpa masalah.

---

### Keputusan 9: Struktur Visual Hybrid — `StatCard`+`Table` (Sibling) + `StatusBadge`+`humanizeDuration()` (Internal)

**Sumber Paksaan**
Dua preseden bersaing, disintesis:
1. `nirwana-database/web/src/app/warehouse/chatbot-performance/page.tsx` + `src/components/ui.tsx` — kasus pakai HAMPIR IDENTIK (halaman "Performa Query AI Chatbot": p50/p95/p99 latency + jumlah/persentase ditolak). Strukturnya `StatCard` (angka besar bertone) + `Table` generik, **plain Tailwind, no component library** (komentar eksplisit `ui.tsx:1-2`). Riset eksplisit mengonfirmasi TIDAK ADA pola bar-chart/progress-bar apa pun di seluruh sibling project — untuk data kategorikal, konsisten pakai `Table`+`Badge`.
2. Preseden internal `dashboard/` sendiri: `StatusBadge` (`Badge.tsx`, taksonomi 5-nilai persis project ini) dan `humanizeDuration()` (format durasi ms/s, lebih presisi dari `.toFixed(0)+" ms"` polos sibling untuk latency LLM yang bisa >1 detik — bukti nyata seed data M5.2: span `chat` narasi 5600ms). File terpisah per komponen (`Badge.tsx`/`Nav.tsx`/`Waterfall.tsx`/`WaterfallRow.tsx` semua terpisah, bukan satu file `ui.tsx` bundel ala sibling).

**Keputusan yang Diikuti**
- `StatCard.tsx` dan `Table.tsx` baru (file terpisah, mirror STRUKTUR sibling — bukan bar-chart CSS width% yang sempat jadi ide plan awal, dibatalkan setelah riset konfirmasi sibling tidak punya pola itu).
- Kolom kategorikal (Status, error_type) pakai `<StatusBadge>` yang SUDAH ADA apa adanya — `error_type` share vocabulary PERSIS dengan `status` (`ditolak_otorisasi`/`gagal_teknis` sama-sama nilai valid keduanya, dikonfirmasi docstring `TraceRow`+`SpanRow` di `src/db/models.py`), jadi TIDAK perlu tone generik baru maupun export tambahan dari `Badge.tsx`.
- Angka durasi tetap `humanizeDuration()` (Keputusan 8), bukan `.toFixed(0)+" ms"` polos sibling.
- `PageHeader`/`Section`/`EmptyState` sibling TIDAK diadopsi — masing-masing cuma dipakai SEKALI di milestone ini, tidak ada pemakaian berulang yang membenarkan ekstraksi komponen baru (prinsip "no premature abstraction", `CLAUDE.md` "Jangan menambah abstraksi di luar yang dibutuhkan task"). Dirender inline (`<h1>`/`<section>` polos) mengikuti gaya `page.tsx` existing.

**Catatan Ketergantungan**
Sintesis ini menjaga konsistensi ekosistem (struktur `StatCard`/`Table` dikenali user yang familiar `nirwana-database/web`) SEKALIGUS konsistensi internal `dashboard/` (taksonomi status 5-nilai, format durasi presisi, file-per-komponen) — tidak mengorbankan salah satu demi yang lain.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Bar-chart CSS width% (teknik `Waterfall` M5.3) untuk distribusi status/frekuensi error.type** — ide di plan draf pertama, DIBATALKAN setelah riset eksplisit mengonfirmasi sibling project (satu-satunya preseden dashboard lain di ekosistem) tidak punya pola visual ini sama sekali; mengikuti preseden yang benar-benar ada dinilai lebih kuat daripada mempertahankan konsistensi-diri-sendiri semata.
- **Satu file `ui.tsx` bundel meniru sibling persis** — ditolak, tidak konsisten preseden file-per-komponen `dashboard/` sendiri yang sudah berjalan 4 komponen (`Badge`/`Nav`/`Waterfall`/`WaterfallRow`).
- **Export `TONE_BY_STATUS` dari `Badge.tsx` untuk dipakai komponen bar terpisah** — gugur bersamaan dengan dibatalkannya ide bar-chart; `<StatusBadge>` dipakai langsung sebagai komponen utuh, bukan cuma peta warnanya.
- **Tone generik `neutral/good/warn/bad` ala `StatCard`/`Badge` sibling untuk kolom status/error_type** — ditolak, kurang presisi dibanding taksonomi 5-nilai `StatusBadge` yang sudah ada dan sudah battle-tested M5.3.

---

### Keputusan 10: Tone `StatCard` Ringkasan Dibuat Neutral

**Sumber Paksaan**
Sibling project mewarnai `StatCard` "% ditolak" dengan `tone={perf.denied_pct > 10 ? "warn" : "good"}` — sebuah AMBANG BISNIS (10%) yang merupakan keputusan produk mereka sendiri, tidak terdokumentasi sebagai kebijakan resmi project ini. Project AI Chatbot RBAC ini belum punya kebijakan ambang tingkat-keberhasilan yang didokumentasikan formal di dokumen sumber kebenaran manapun.

**Keputusan yang Diikuti**
`StatCard` "Jumlah Query" dan "Tingkat Keberhasilan" memakai `tone="neutral"` — melaporkan angka apa adanya tanpa penilaian baik/buruk yang dikarang sendiri.

**Catatan Ketergantungan**
Mewarnai berdasar ambang karangan sendiri berisiko menyesatkan pembaca dashboard PUBLIK — prinsip arsitektur "Kejujuran terhadap keterbatasan" (`CLAUDE.md`) lebih dekat dipenuhi dengan melaporkan angka netral daripada memberi sinyal baik/buruk tanpa dasar kebijakan yang disepakati.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Meniru ambang sibling (`warn` kalau tingkat keberhasilan < 90%, sebagai contoh)** — ditolak, ambang seperti itu adalah keputusan kebijakan yang perlu disepakati eksplisit (bukan diasumsikan sepihak saat implementasi), konsisten `CLAUDE.md` "Kelola keputusan teknis" soal keputusan yang belum saatnya diambil.

---

### Keputusan 11: Panel Kumulatif Seluruh Data, Tidak Berjendela Waktu

**Sumber Paksaan**
Panel Grafana M5.1 pembanding ("Distribusi Status", "Frekuensi error.type") memakai query PromQL `sum(traces_span_metrics_calls_total{...}) by (...)` dengan `"instant": true` (`observability.json:95,112`) — nilai counter Prometheus MENTAH tanpa `rate()`/`increase()` atas jendela waktu, yang secara efektif adalah nilai KUMULATIF sejak counter mulai terkumpul (bukan windowed). Sibling project (`chatbot-performance/page.tsx`) sebaliknya eksplisit "24 jam terakhir" — kebijakan produk berbeda, tidak relevan untuk kesetaraan KK2 terhadap Grafana M5.1.

**Keputusan yang Diikuti**
Query `summary.ts` TIDAK memfilter rentang waktu apa pun — agregat atas SELURUH baris `traces`/`spans` tersimpan.

**Catatan Ketergantungan**
Konsisten sifat panel Grafana yang jadi rujukan literal kesetaraan KK2 ("...sama-sama terlihat menonjol di dashboard publik ini seperti di Grafana").

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Filter "24 jam terakhir" ala sibling** — ditolak, tidak match sifat panel Grafana M5.1 yang jadi rujukan KESETARAAN eksplisit KK2 (Grafana efektif kumulatif, bukan windowed).

---

### Keputusan 12: Tidak Ada Seed Data Baru

**Sumber Paksaan**
3 trace existing (M5.2: `sample-6d7f5cea8dfd` status=`berhasil`; M5.3: `sample-mw-...` status=`berhasil`, `sample-fail-...` status=`sebagian` dengan `error_type` `ditolak_otorisasi`×2/`gagal_teknis`×1) sudah py keberagaman status (`berhasil`/`sebagian`) DAN error_type (`ditolak_otorisasi`/`gagal_teknis`) yang cukup untuk membuktikan kedua KK M5.4. Dokumen sumber (`rancangan-observability-dashboard.md:91`) minta agregat "lintas seluruh trace yang tersimpan" — bukan skenario data baru.

**Keputusan yang Diikuti**
Tidak ada script seed baru di milestone ini.

**Catatan Ketergantungan**
Kalau nanti ternyata data tidak cukup representatif saat verifikasi nyata Checkpoint 3/4, keputusan ini akan direvisi eksplisit (dicatat di `logs.md`), bukan diam-diam ditambah data tanpa jejak.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Seed trace tambahan untuk memperkaya variasi layer_name/status** — dipertimbangkan untuk demo yang lebih "penuh", ditolak karena tidak forced oleh KK manapun dan menambah scope di luar yang literal diminta dokumen sumber.

---

### Keputusan 13: Verifikasi UI Wajib via Browser Nyata + Query SQL Manual Independen

**Sumber Paksaan**
Preseden Keputusan 10 M5.3 (insiden akses `localhost:3000` sesi sebelumnya) — verifikasi UI wajib lewat tool Browser (DOM/console nyata), bukan `curl`/status code. KK1 M5.4 secara literal menuntut "cocok dengan penghitungan manual terhadap data yang sama di Supabase" — ini forced tambahan: perlu pembanding independen via query SQL langsung, bukan cuma percaya angka yang tampil di UI.

**Keputusan yang Diikuti**
Checkpoint 3 (query agregat) diverifikasi dulu via query manual langsung ke Supabase SEBELUM UI dibangun; Checkpoint 4 (UI) diverifikasi via Browser nyata DAN dicocokkan ulang ke angka manual yang sama.

**Catatan Ketergantungan**
Dua lapis verifikasi independen (query manual + Browser) memastikan KK1 "tidak ada penyimpangan akibat kesalahan agregasi" benar-benar dibuktikan, bukan diasumsikan dari membaca kode.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden M5.3 + teks literal KK1.

---

## Keputusan 14 (Addendum): `page.tsx` Diberi `force-dynamic` + `db.ts` Dibuat Lazy — Cegah Static Render dan Koneksi DB Saat Build

**Status:** Ditemukan di Milestone 8.6 (2026-08-23, saat riset lalu eksekusi Plan Mode untuk menyambungkan `dashboard/` ke CI+Vercel), diperbaiki di sini atas konfirmasi eksplisit user — bukan ditutup di M8.6 sendiri, karena perbaikan perilaku rendering+koneksi DB dashboard adalah tanggung jawab milestone pemilik (M5.2 untuk `db.ts`, M5.4 untuk `page.tsx`; dicatat di sini karena keduanya satu root cause yang sama ditemukan bersamaan).

**Latar Belakang**
Investigasi M8.6 menemukan `dashboard/src/app/page.tsx` (Keputusan 1 di atas) tidak memakai `searchParams`/`cookies`/`headers`/dynamic API apa pun dan tidak punya `export const dynamic` — kandidat static rendering default Next.js App Router. `dashboard/src/lib/db.ts` (M5.2 Keputusan 4) membuat koneksi Postgres di level MODUL TOP-LEVEL (`export const sql = process.env.NODE_ENV === "production" ? createClient() : ...`, throw kalau `DATABASE_URL` kosong). Dugaan awal: kombinasi keduanya membuat `next build` mengeksekusi `getSummaryMetrics()` sekali saat build lalu membekukan datanya — bertentangan dengan prinsip arsitektur "Dashboard publik wajib identik isinya dengan dashboard privat (Grafana)" (`CLAUDE.md`).

**Koreksi empiris di tengah eksekusi (masih 2026-08-23):** perbaikan pertama (`export const dynamic = "force-dynamic"` saja di `page.tsx`) TERNYATA TIDAK CUKUP — dibuktikan salah lewat percobaan nyata (`.env.local` dihapus sementara, `npm run build` dijalankan): build tetap GAGAL di fase "Collecting page data" untuk `/` MAUPUN `/traces` dengan error persis `DATABASE_URL tidak diset`. Akar masalah sesungguhnya: Next.js App Router meng-import (mengevaluasi) modul SETIAP route saat fase itu untuk mengumpulkan konfigurasi route — ini terjadi untuk route dynamic MAUPUN static, jadi `db.ts` versi eager tetap ter-trigger apa pun status rendering halamannya. `export const dynamic` sama sekali tidak memengaruhi kapan modul di-*import*, hanya memengaruhi kapan konten di-*render*. Bug staleness produksi (bagian pertama temuan) tetap valid dan `force-dynamic` tetap solusi yang benar untuk itu — tapi TIDAK berdampak apa pun ke masalah `next build`/CI.

**Keputusan yang Dipilih**
1. `dashboard/src/app/page.tsx`: tetap diberi `export const dynamic = "force-dynamic";` (menutup bug staleness produksi — tidak berubah dari draf awal).
2. `dashboard/src/lib/db.ts`: `createClient()` DIBUAT LAZY lewat `Proxy` — client Postgres baru benar-benar dibuat saat query pertama dipanggil (trap `apply` untuk pemanggilan tagged-template `sql\`...\``, trap `get` untuk akses method seperti `.begin`), bukan saat modul di-*import*. Caching `globalThis.__nirwanaDashboardDb` disederhanakan berlaku sama untuk dev DAN production (sebelumnya dibedakan). `traces.ts`/`summary.ts` TIDAK perlu diubah sama sekali — keduanya tetap `import { sql } from "@/lib/db"` dan memakai `sql\`...\`` persis seperti sebelumnya, karena Proxy meneruskan pemanggilan itu transparan ke client lazy di baliknya.

**Alasan**
User memilih opsi "refactor `db.ts` jadi lazy" (dari 3 alternatif babak kedua: refactor lazy / beri `DATABASE_URL` ke CI / kombinasi keduanya) setelah koreksi di atas dibawa balik lewat `AskUserQuestion` — lihat `milestones/8.6-remote-ci-dashboard/decisions.md` Keputusan 9 untuk detail lengkap kedua babak pertanyaan. Pendekatan Proxy dipilih (bukan getter function `getSql()` yang mengharuskan seluruh call site diubah) karena `postgres()` mengembalikan objek callable+py method — Proxy meniru bentuk itu persis sehingga TIDAK ADA perubahan di `traces.ts`/`summary.ts`, meminimalkan blast radius perbaikan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Beri `DATABASE_URL` ke CI sebagai secret, `db.ts` tidak diubah** — ditolak: tidak menutup akar masalah (fase "Collecting page data" tetap butuh koneksi DB nyata setiap kali CI jalan, bukan cuma sekali), dan menambah kredensial DB yang sebenarnya bisa dihindari sepenuhnya di CI.
- **Getter function `getSql()` mengganti export `sql`** — dipertimbangkan sebagai pola lazy yang lebih konvensional, ditolak karena mengharuskan `traces.ts`+`summary.ts` diubah (setiap pemanggilan `sql\`...\`` jadi `getSql()\`...\``) tanpa manfaat tambahan dibanding Proxy yang mencapai hasil sama dengan blast radius lebih kecil.

**Dampak**
`dashboard/src/app/page.tsx` selalu dynamic-rendered (tiap request, bukan build-time) — menutup bug staleness. `dashboard/src/lib/db.ts` tidak lagi connect DB saat modul di-*import* dalam kondisi apa pun (dev maupun production, build maupun runtime) — menutup bug `next build`/CI. `milestones/8.6-remote-ci-dashboard/decisions.md` Keputusan 3 (job `build` tidak butuh `DATABASE_URL`) bergantung langsung pada perbaikan `db.ts` ini, BUKAN pada `force-dynamic` semata seperti dugaan awal. Dibuktikan nyata: `npm run build` dengan `.env.local` dihapus sementara sukses penuh (route `/`+`/traces`+`/traces/[traceId]` seluruhnya `ƒ Dynamic`); `npm run lint`+`npm test` (16/16) tetap hijau; smoke test `next start` dengan `DATABASE_URL` asli terisi mengonfirmasi `/` dan `/traces` tetap mengembalikan data nyata (HTTP 200, konten "Jumlah Query"/"Daftar Trace" tampil) — regresi fungsional nol.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Homepage `/` diisi jadi Halaman Ringkasan | B | Plan |
| 2 | "Jumlah Query" = `COUNT(*) FROM traces` | B | Plan |
| 3 | Distribusi Status Query Langsung dari `traces.status` | B | Plan |
| 4 | Latency per Layer Dikelompokkan `layer_name` Saja | B | Plan |
| 5 | Persentil via `PERCENTILE_CONT` (Postgres Native, Eksak) | B | Plan |
| 6 | `totalTraces`/`successRate` Dihitung dari `statusDistribution` | B | Plan |
| 7 | Query Agregat di File Terpisah `summary.ts` | B | Plan |
| 8 | `humanizeDuration()` Diekstrak ke `format.ts`, Gaya Test Persis `trace-tree.test.ts` | B | Plan |
| 9 | Struktur Visual Hybrid — `StatCard`+`Table` (Sibling) + `StatusBadge`+`humanizeDuration()` (Internal) | B | Plan |
| 10 | Tone `StatCard` Ringkasan Dibuat Neutral | B | Plan |
| 11 | Panel Kumulatif Seluruh Data, Tidak Berjendela Waktu | B | Plan |
| 12 | Tidak Ada Seed Data Baru | B | Plan |
| 13 | Verifikasi UI Wajib via Browser Nyata + Query SQL Manual Independen | B | Plan |
| 14 | Addendum M8.6: `page.tsx` diberi `force-dynamic` + `db.ts` dibuat lazy (Proxy), cegah static render dan koneksi DB saat build | A | Addendum 2026-08-23 |
