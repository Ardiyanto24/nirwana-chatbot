# Logs — Milestone 2.1: Membangun Identifikasi Domain dan Verifikasi Titik Buta

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | *(pending)* | `docs(milestone-2.1): decisions` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama, sebelum kode apa pun, setelah plan disetujui user lewat Plan Mode (riset 3 agen Explore paralel + baca langsung `rancangan-rbac-authorization.md`, `rancangan-rbac-ai-chatbot.md` Bagian 1-2, `rancangan-observability-ai-chatbot.md` Bagian 2, dan kode preseden `matching.py`/`decompose.py`/`session_memory.py`).

**Apa yang dilakukan**
12 entri keputusan: 9 Jenis B forced/preseden (dua pemanggilan LLM terpisah, union aditif bukan retry, struktur subpackage file terpisah, Enum domain tertutup, bounds-check, fallback reuse `StatusEksekusi`, konstanta model terisolasi, span `chat`×2 cakupan terbatas, `decisions.md` sebagai task pertama), 3 Jenis A genuinely terbuka (2 dari `AskUserQuestion` sebelum plan ditulis — model M2.1 pola M1.6, granularitas per atomic intent; 1 dari riset katalog data selama penulisan plan — cakupan konteks grounding hanya 10 domain + 1 contoh cross-domain terdokumentasi, bukan seluruh 67 view).

**Temuan**
Katalog 67 view (`katalog-data-chatbot.md`) hanya menandai SATU view eksplisit "Cross-domain" (`v_reservation_gop_impact_monthly`) di seluruh dokumen — dikonfirmasi lewat pencarian string literal, bukan sampel. Juga ditemukan `CLAUDE.md` menulis "19 role" padahal `rancangan-rbac-authorization.md`/`rancangan-rbac-ai-chatbot.md` keduanya konsisten menyebut 20 role — dijadwalkan diperbaiki di Checkpoint 12 (tidak berdampak ke M2.1 karena M2.1 tidak menyentuh `role_permissions`).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
