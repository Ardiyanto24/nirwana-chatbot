# Logs — Milestone 2.3: Membangun Deteksi Constraint Cakupan-Individu

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | *(lihat di bawah)* | `docs(milestone-2.3): decisions` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-16 · **Selesai:** 2026-08-16

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama, sebelum kode apa pun, setelah plan disetujui user lewat Plan Mode. Dua keputusan genuinely terbuka (daftar 9 view, mekanisme LLM) dikonfirmasi lewat `AskUserQuestion` SEBELUM plan ditulis (bukan saat Checkpoint 1), sesuai instruksi `CLAUDE.md` — `decisions.md` di sini mendokumentasikan hasil konfirmasi itu, bukan tempat pertama kali keputusan diambil.

**Apa yang dilakukan**
12 entri keputusan: 2 Jenis A genuinely terbuka dari `AskUserQuestion` (daftar eksplisit 9 view kategori performa individu hasil tinjauan langsung ke `katalog-data-chatbot.md`; mekanisme LLM generate-verify dual-call union aditif, pola M2.1), 10 Jenis B forced/preseden (transkripsi tier "Staff" sebagai frozenset, pre-filter role sebelum LLM, pre-filter domain facility/hr sebelum LLM, skema output rata bukan nesting, fail-closed saat kegagalan teknis, model constants terisolasi, subpackage domain_gate/ yang sama, folder evals/ dibuat, prompt-file-first + Promptfoo natif sejak awal karena kontrak Manajemen Prompt sudah mengikat, decisions.md sebagai task pertama).

**Temuan**
Tinjauan langsung ke `docs/03-domain-source/katalog-data-chatbot.md` mengonfirmasi hanya 2 dari 10 domain (`facility`, `hr`) yang ditandai eksplisit py sensitivitas performa individu di Ringkasan 10 Domain (baris 47, 49) — bukan hasil tebakan, melainkan penandaan tersurat di dokumen sumber sendiri.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(menyusul)*
