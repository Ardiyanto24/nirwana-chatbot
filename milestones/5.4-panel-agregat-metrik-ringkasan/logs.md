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

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada — penolakan plan pertama dan riset ulang terjadi SEBELUM Checkpoint 1 resmi dimulai (bagian dari proses "Rencanakan sebelum mengimplementasikan" di `CLAUDE.md`, bukan checkpoint implementasi), sehingga dicatat sebagai bagian dari narasi Task 1 di atas, bukan checkpoint terpisah di luar plan.
