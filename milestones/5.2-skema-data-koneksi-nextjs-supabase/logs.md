# Logs — Milestone 5.2: Membangun Skema Data dan Koneksi Next.js ke Supabase

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-20 · **Selesai:** 2026-08-20

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Sebelum plan ditulis, dilakukan riset 2-jalur paralel (2 agent Explore) mencakup: isi lengkap `docs/02-implementation-plan/rancangan-observability-dashboard.md` (fokus M5.2) dan `docs/01-architecture/rancangan-observability-ai-chatbot.md` Bagian 4 (skema Supabase), state nyata `src/db/models.py`/`src/config/database.py` (pola koneksi Python existing), dan repo tetangga `nirwana-database/web/` (satu-satunya preseden Next.js di ekosistem ini). Satu agent Plan mendesain mekanisme konkret (library Postgres Node, bentuk query hierarkis, breakdown checkpoint). Satu pertanyaan genuinely-terbuka (lokasi repo Next.js) diajukan ke user lewat `AskUserQuestion` — riset awal SEMPAT salah mengasumsikan preseden tetangga adalah subfolder biasa, dikoreksi lewat verifikasi langsung `.gitignore`/`git status` repo tetangga (genuinely repo terpisah, bukan subfolder) sebelum pertanyaan diajukan. Setelah user memilih (repo terpisah), plan final ditulis dan disetujui (`ExitPlanMode`). Setelah plan disetujui, `milestones/5.2-skema-data-koneksi-nextjs-supabase/decisions.md` ditulis berisi 12 entri keputusan (1 Jenis A genuinely-terbuka, 11 Jenis B preseden/forced/beralasan) mengikuti `template-decisions.md`.

**Temuan**
- Koreksi faktual penting: repo tetangga `nirwana-database/web/` TERNYATA genuinely repo Git terpisah (`.git` sendiri, remote `nirwana-monitoring-web`, digitignore eksplisit oleh repo induk) — bukan subfolder biasa seperti dugaan riset awal. Ini mengubah rekomendasi lokasi repo Next.js M5.2 dari "folder di repo ini" (dugaan awal) jadi genuinely pertanyaan terbuka dengan bukti dua arah.
- Tabel `traces`/`spans` belum pernah dibuat di Supabase manapun — M5.2 adalah milestone PERTAMA yang benar-benar membuatnya (sebelumnya hanya "dipesan secara konsep" oleh M1.5/M2.2 lewat penghindaran nama tabel).
- Preseden konsisten (2 milestone: M2.2, M2.4) untuk lokasi+bentuk seed script one-off: hidup di folder milestone-nya sendiri, `SQLModel.metadata.create_all(engine)` dipanggil DI DALAM script (bukan langkah terpisah).
- `psycopg3` Python vs `postgres.js`/`pg` Node punya default SSL behavior BERBEDA (`sslmode=prefer` fallback diam-diam vs `ssl:false` tanpa fallback) — connection string yang sama tidak menjamin hasil sama antar bahasa, perlu SSL eksplisit di sisi Node.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` lengkap dengan 12 entri, setiap entri py section "Opsi yang Dipertimbangkan tapi Ditolak" terisi, Daftar Isi Keputusan di akhir dokumen mencantumkan seluruh 12 entri dengan Checkpoint Terkait.

**Commit:** *(diisi setelah commit checkpoint ini)*

---
