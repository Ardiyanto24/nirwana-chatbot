# Logs — Milestone 5.4: Membangun Panel Agregat dan Metrik Ringkasan

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Menyimpang dari urutan penulisan plan awal — plan pertama yang diajukan (`ExitPlanMode`) ditolak user dengan instruksi "riset lagi milestone 4.5 dengan lebih mendalam dan susun lagi plannya" (dikonfirmasi via `AskUserQuestion` sebagai typo untuk milestone 5.4, bukan benar-benar milestone 4.5 yang sudah selesai). Plan ditulis ulang dari nol dengan riset tambahan sebelum Checkpoint 1 benar-benar dimulai — bukan penyimpangan pada isi task itu sendiri.

**Apa yang dilakukan**
1. Riset awal (sebelum plan pertama): baca `docs/02-implementation-plan/rancangan-observability-dashboard.md` (Lingkup+KK M5.4), `src/db/models.py` (`TraceRow`/`SpanRow`), `dashboard/src/lib/traces.ts`/`trace-tree.ts`, `infra/observability/grafana/dashboards/observability.json` (5 panel Grafana M5.1 sebagai rujukan kesetaraan), `dashboard/src/app/page.tsx`/`components/{Badge,Nav}.tsx`.
2. Plan pertama ditulis dan diajukan via `ExitPlanMode` — **ditolak user**.
3. Klarifikasi via `AskUserQuestion`: "milestone 4.5" di instruksi penolakan dikonfirmasi typo untuk "milestone 5.4".
4. Riset lanjutan: 2 agent Explore dijalankan paralel (foreground) —
   - Agent 1: menelusuri seluruh kemunculan kata "query" di `rancangan-observability-dashboard.md`, `arsitektur-ai-chatbot-rbac.md`, `rancangan-observability-ai-chatbot.md` Bagian 4, `observability.json`, dan `milestones/5.1-.../report.md`+`decisions.md`, untuk memastikan makna "jumlah query" di KK1.
   - Agent 2: menelusuri konvensi UI ringkasan/agregat di `nirwana-database/web` (sibling project) dan tooling `dashboard/` (package.json, ada/tidaknya `vitest.config.ts`, gaya `trace-tree.test.ts`).
5. Berdasar hasil kedua agent, dibaca langsung `nirwana-database/web/src/app/warehouse/chatbot-performance/page.tsx` (halaman preseden nyaris identik: p50/p95/p99 latency + tingkat ditolak) dan `nirwana-database/web/src/components/ui.tsx` (`StatCard`/`Table`/`Badge`/`Section`/`PageHeader`/`EmptyState`) untuk konfirmasi detail struktur+styling.
6. Plan ditulis ulang (Context+14 Keputusan Turunan direvisi jadi 13 entri konsolidasi di `decisions.md`), diajukan ulang via `ExitPlanMode` — **disetujui user**.
7. `milestones/5.4-panel-agregat-metrik-ringkasan/decisions.md` ditulis — 13 entri Jenis B (Preseden/Forced), semuanya dengan section "Opsi yang Dipertimbangkan tapi Ditolak" terisi.

**Temuan**
- Kata "query" tidak pernah didefinisikan formal di dokumen manapun di project ini — hanya muncul 3× dan seluruhnya di dalam Milestone 5.4 sendiri. Bukti tekstual (grain tabel `traces`, kesetaraan Grafana "Distribusi Status (per turn)") konsisten mengarah ke satu "query" = satu trace/turn, tapi ini murni derivasi penalaran, bukan definisi eksplisit di tempat manapun.
- Grafana M5.1 memakai dua workaround signifikan akibat keterbatasan Jaeger/Prometheus (proksi span `riwayat.simpan` untuk status level-turn, dimensi ganda `(span_name, prompt_id)` untuk disambiguasi layer, histogram bucket untuk persentil) yang TIDAK perlu direplikasi di Next.js/Supabase karena skema Supabase tidak punya keterbatasan yang sama.
- `nirwana-database/web/src/app/warehouse/chatbot-performance/page.tsx` adalah preseden yang jauh lebih dekat dari yang diperkirakan plan pertama — nyaris identik kasus pakainya (p50/p95/p99 latency chatbot + tingkat ditolak). Plan pertama (ditolak) mengasumsikan pola bar-chart CSS width% (meniru `Waterfall` M5.3) tanpa mengecek dulu apakah sibling project punya pola serupa — riset lanjutan mengonfirmasi sibling SAMA SEKALI tidak punya pola bar visual, konsisten pakai `Table`+`Badge`. Ini jadi alasan utama BarList (ide plan pertama) dibatalkan, diganti `StatCard`+`Table`.
- `dashboard/` tidak punya `vitest.config.ts`, dan test existing (`trace-tree.test.ts`) memakai import relatif bukan alias `@/lib/...` — informasi ini akan dipakai langsung di Checkpoint 2 (test `format.ts`).

**Error/Kegagalan (jika ada)**
Tidak ada error teknis — "kegagalan" satu-satunya adalah plan pertama ditolak user karena kedalaman riset dianggap kurang, ditindaklanjuti sesuai instruksi (riset lebih dalam + agent Explore), bukan dipaksakan.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku (bukan error teknis).

**Hasil Verifikasi**
`decisions.md` lengkap 13 entri Jenis B, masing-masing dengan Sumber Paksaan+Keputusan yang Diikuti+Catatan Ketergantungan+Opsi yang Dipertimbangkan tapi Ditolak terisi penuh, sesuai `template-decisions.md`. Daftar Isi Keputusan di akhir file mencakup seluruh 13 entri.

**Commit:** `7c10970` — `docs(milestone-5.4): keputusan desain panel agregat dan metrik ringkasan`

---

## Checkpoint 2 — Util Format Bersama

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 2 — Buat `format.ts`, refactor `WaterfallRow.tsx`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Dibuat `dashboard/src/lib/format.ts` berisi `humanizeDuration(ms: number | null)` (dipindah persis dari `WaterfallRow.tsx`, logic tidak diubah) dan `formatPercent(ratio: number)` baru (`${(ratio*100).toFixed(1)}%`). `WaterfallRow.tsx` diedit: definisi lokal `humanizeDuration` dihapus, diganti `import { humanizeDuration } from "@/lib/format";`.

**Temuan**
Tidak ada temuan baru di luar yang sudah dicatat Checkpoint 1 (gaya import relatif untuk test, tidak ada `vitest.config.ts`).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`grep humanizeDuration` di seluruh `dashboard/src` mengonfirmasi HANYA satu definisi (`format.ts`), dipakai `WaterfallRow.tsx` via import alias `@/lib/format` (komponen tetap boleh pakai alias karena bukan file test) dan dipakai `format.test.ts` via import relatif.

**Commit:** *(gabung dengan Task 3, lihat di bawah)*

### Task 3 — Tulis `format.test.ts`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Ditulis `dashboard/src/lib/format.test.ts` mengikuti gaya persis `trace-tree.test.ts` (`import {describe,expect,it} from "vitest"`, import relatif `from "./format"`). 6 `it()` (3 `humanizeDuration`: null→"?", <1000ms polos, >=1000ms 2-desimal termasuk kasus nyata 5600ms dari span narasi M5.2; 3 `formatPercent`: 0&1, 2/3 - kasus nyata tingkat keberhasilan data sample M5.2+M5.3, pembulatan 1/3 dan 0.005).

**Temuan**
Tidak ada.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`npm test` di `dashboard/` (real, dijalankan lewat Bash tool) → `Test Files 2 passed (2)`, `Tests 16 passed (16)` (10 test lama `trace-tree.test.ts` + 6 test baru `format.test.ts`, masing-masing `it()` dihitung Vitest sebagai satu test meski berisi >1 `expect`; output dikonfirmasi nyata, bukan asumsi).

**Commit:** `dc61cea` (repo `dashboard/`) — `refactor(dashboard): ekstrak humanizeDuration ke lib/format.ts + formatPercent`

---

## Checkpoint 3 — Query Agregat (`summary.ts`)

**Mulai:** 2026-08-21 · **Selesai:** 2026-08-21

### Task 4 — Buat `summary.ts`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu detail teknis tambahan yang tidak eksplisit disebut plan: seluruh angka SQL (`COUNT(*)`, `AVG(...)`) di-cast eksplisit `::int`/`::float8` di query, bukan dibiarkan tipe native Postgres (`bigint`/`numeric`) yang berisiko dikembalikan sebagai string oleh driver `postgres` tanpa konfigurasi tambahan.

**Apa yang dilakukan**
Dibuat `dashboard/src/lib/summary.ts` — `getStatusDistribution()`, `getLatencyPerLayer()` (`GROUP BY layer_name`, `PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)`, urut p95 DESC), `getErrorTypeFrequency()`, fungsi murni `computeOverallStats(statusDistribution)`, dan `getSummaryMetrics()` yang menjalankan ketiga query paralel (`Promise.all`) lalu memanggil `computeOverallStats()`.

Verifikasi dijalankan lewat skrip ad-hoc `verify_summary.mjs` (di scratchpad session, TIDAK di-commit — mereplikasi query SQL persis `summary.ts` langsung via `postgres` package, dijalankan `node` dari `cwd=dashboard/` supaya resolusi module `"postgres"` jalan, baca `DATABASE_URL` dari `.env.local` manual karena tidak pakai `next dev`).

**Temuan**
- Dengan cast eksplisit, seluruh field (`count`, `avg_ms`, `p95_ms`) dikonfirmasi `typeof === "number"` di JS — tidak ada ambiguitas tipe.
- Data nyata Supabase saat ini punya 10 `layer_name` distinct di tabel `spans` (`orchestration`, `retriever`, `interpretation`, `domain_gate`, `query_engine`, `execution`, `decomposition`, `context_resolution`, `input_layer`, `verification_gate`) — sebaran cukup kaya untuk tabel Latency per Layer meski hanya 3 trace.
- `layer_name="orchestration"` py p95 tertinggi (40200ms) — masuk akal karena span ini membungkus `invoke_agent`/durasi total turn, bukan bug.

**Error/Kegagalan (jika ada)**
Percobaan pertama skrip verifikasi gagal: `ERR_UNSUPPORTED_ESM_URL_SCHEME` karena `import postgres from "<path-absolut-windows>"` — Node ESM loader menolak path Windows absolut (`C:\...`) sebagai specifier import tanpa `file://` prefix.

**Diagnosis dan Perbaikan (jika ada error)**
Diperbaiki dengan mengganti import jadi bare specifier `import postgres from "postgres"` dan menjalankan `node` dengan working directory `dashboard/` (supaya resolusi `node_modules` standar berfungsi) — bukan mengubah `summary.ts` itu sendiri (bug murni di skrip verifikasi ad-hoc, bukan kode produksi).

**Hasil Verifikasi**
Output skrip nyata dicocokkan dengan hitung manual dari data yang sudah diketahui (M5.2/M5.3):
- `statusDistribution`: `berhasil=2, sebagian=1` — cocok persis.
- `errorTypeFrequency`: `ditolak_otorisasi=2, gagal_teknis=1` — cocok persis.
- `totalTraces=3, successRate=0.6666666666666666` (= 2/3 eksak) — cocok persis.
- `latencyPerLayer`: 10 baris, seluruhnya angka bertipe `number` valid, terurut `p95_ms` DESC.

Ini bukti awal KK1 ("cocok dengan penghitungan manual") SEBELUM UI dibangun, sesuai rencana verifikasi checkpoint ini di plan.

**Commit:** `576b24f` (repo `dashboard/`) — `feat(dashboard): query agregat lintas-trace (summary.ts)`

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — penolakan plan pertama dan riset ulang terjadi SEBELUM Checkpoint 1 resmi dimulai (bagian dari proses "Rencanakan sebelum mengimplementasikan" di `CLAUDE.md`, bukan checkpoint implementasi), sehingga dicatat sebagai bagian dari narasi Task 1 di atas, bukan checkpoint terpisah di luar plan.
