# Logs — Milestone 8.2: Test Gate — Unit & Integration

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-22 · **Selesai:** 2026-08-22

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Riset plan menemukan: dari 705 test, ~48 (8 dari 12 unit M8.1) genuinely butuh `OPENROUTER_API_KEY`/`DATABASE_URL` (mekanisme `skipif` sudah ada). Percobaan pengukuran pertama (`env -u` unset kredensial) keliru — `.env` lokal ikut termuat ulang `load_dotenv()`, dikoreksi dengan baca kode (`.gitignore`+`load_dotenv()` no-op) bukan run coba-coba berikutnya (menghindari insiden `.env` sempat ke-rename tanpa restore tepat waktu saat percobaan verifikasi kedua — segera dipulihkan, integritas file dikonfirmasi).

Diajukan ke user via `AskUserQuestion`: kredensial CI provisioned atau tidak — user memilih "full CI tapi path-filtered per layer" (bukan salah satu dari 3 opsi yang saya ajukan awal). Diskusi lanjutan (user eksplisit minta dijelaskan standar industri untuk deteksi "layer mana yang berubah" sebelum plan ditulis) — 4 pendekatan diajukan (`dorny/paths-filter`, `pytest-testmon`, native `on: paths:`, tooling monorepo besar), user pilih `dorny/paths-filter`. Plan sempat diajukan prematur sebelum diskusi ini tuntas — dikoreksi eksplisit atas permintaan user ("jangan buat plan dulu, saya diatas masih bertanya").

Menulis `milestones/8.2-test-gate/decisions.md` (9 keputusan: 2 Jenis A + 7 Jenis B).

**Hasil Verifikasi**
Review manual `decisions.md` — format Jenis A/B sesuai template, kedua keputusan `AskUserQuestion`+diskusi tercermin akurat.

**Commit:** (menyusul)

---
