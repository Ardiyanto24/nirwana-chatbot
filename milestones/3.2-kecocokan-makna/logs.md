# Logs — Milestone 3.2: Pemeriksaan Kecocokan Makna

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Dokumentasi Keputusan

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.2-kecocokan-makna/decisions.md`: 14 keputusan (3 Jenis A hasil `AskUserQuestion` dalam sesi perencanaan — mekanisme verifikasi generate+verifikator independen dengan koreksi dua arah, granularitas batch per kebutuhan atomik, cakupan orkestrator menyertakan `_semua()`; 11 Jenis B forced/preseden — termasuk reuse model Qwen3-32B/DeepSeek V4 Pro, transkripsi verbatim corpus definisi lengkap, injeksi sekali `Catatan Lintas-Domain`, dua fallback gagal-teknis, jaminan struktural anti-drop-kandidat, validator satu-arah `HasilKecocokanMakna`, nama span literal `"chat"`). Riset mendalam (3 agen Explore paralel + 1 agen Plan) dan verifikasi langsung terhadap kode sumber (`src/config/llm.py`, `domain_gate.py`, `matching.py`, `retriever.py` schemas, `katalog-data-chatbot.md`) dilakukan sebelum plan ditulis, memastikan tiap keputusan forced benar-benar bisa ditelusuri ke preseden/kontrak nyata, bukan asumsi.

**Temuan**
Plan draft pertama (format bebas, bukan mengikuti `template-plan-milestone-lengkap.md`) ditolak user lewat `ExitPlanMode` dengan instruksi eksplisit mengikuti template — plan ditulis ulang penuh mengikuti struktur template persis (Context dengan Temuan Penting/Batasan Mengikat/Klarifikasi → Keputusan Desain Turunan → Keputusan yang Ditanyakan ke User → Checkpoint & Task Breakdown Task 1-25 berurutan → Kriteria Keberhasilan → Commit → Risiko & Mitigasi) sebelum diajukan ulang dan disetujui. Verifikasi silang terhadap kode nyata (bukan hanya laporan agen) menemukan satu detail penting yang mengoreksi rekomendasi awal agen Plan: nama span pemanggilan LLM adalah literal `"chat"` (dibuktikan dari `context_resolution/matching.py`), bukan nama custom `retriever.nilai_kecocokan_makna_semua` seperti sempat diusulkan — dikoreksi sebelum plan final ditulis (Keputusan 11).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh keputusan di plan yang disetujui (Keputusan Desain Turunan + Keputusan yang Ditanyakan ke User) punya entri `decisions.md` yang sesuai dengan "Opsi yang Dipertimbangkan tapi Ditolak", tidak ada yang diam-diam jadi asumsi implisit.

**Commit:** `4c46591` — `docs(milestone-3.2): keputusan desain kecocokan makna`

---

---
