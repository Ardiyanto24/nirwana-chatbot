# Logs — Milestone 2.2: Membangun Pemeriksaan Otorisasi

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | *(commit ini)* | `docs(milestone-2.2): decisions` |

---

## Checkpoint 1 — Keputusan

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan — ditulis sebagai task pertama, sebelum kode apa pun, setelah plan disetujui user lewat Plan Mode (riset langsung ke `rancangan-rbac-authorization.md` Milestone 2.2, `api-chatbot.md` kredensial `chatbot_authz_reader`, kontrak span, dan kode preseden `seed_roles.py`/`src/db/models.py`/`src/config/roles.py`).

**Apa yang dilakukan**
11 entri keputusan: 10 Jenis B forced/preseden (larangan query produksi langsung, mekanisme deterministik tanpa LLM, output granular per domain, tidak menangani access_scope, tidak ada folder evals/, subpackage domain_gate/ yang sama, file skema terpisah, pola seed di milestones/, entri GAGAL_TEKNIS dilewati, decisions.md sebagai task pertama), 1 Jenis A genuinely terbuka dari `AskUserQuestion` (sumber matriks — tabel Supabase baru, bukan konstanta Python statis).

**Temuan**
Dikonfirmasi lewat `api-chatbot.md` baris 29-30: kredensial `chatbot_authz_reader` untuk query `mart_cleaned.role_permissions` eksklusif milik Milestone 4.4 — M2.2 (Lapis 1) definitif tidak punya jalur akses ke tabel produksi ini, memaksa kebutuhan salinan matriks sendiri.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
