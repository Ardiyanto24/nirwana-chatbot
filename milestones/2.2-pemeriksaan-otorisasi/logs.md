# Logs — Milestone 2.2: Membangun Pemeriksaan Otorisasi

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `e6e2170` | `docs(milestone-2.2): decisions` |
| 2 | *(commit ini)* | `feat(milestone-2.2): skema data otorisasi` |

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

**Commit:** `e6e2170`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 2 — `src/schemas/authorization.py`

**Kesesuaian dengan plan:** Sesuai plan — unit test dedicated ditunda ke `tests/layers/domain_gate/test_otorisasi.py` (Checkpoint 4-5), sesuai opsi eksplisit yang sudah disebut plan sendiri ("mirror preseden M2.1 Checkpoint 2"). Sanity check manual dijalankan langsung (4 kasus: true/alasan-none valid, false/alasan-terisi valid, false/alasan-none ditolak, true/alasan-terisi ditolak) untuk konfirmasi cepat sebelum lanjut, bukan pengganti unit test formal.

**Apa yang dilakukan**
`DomainAuthorization` (`domain: Domain` reuse M2.1, `diizinkan: bool`, `alasan: str | None`) dengan validator `alasan_konsisten_dengan_diizinkan`, dan `AtomicIntentAuthorization` (`atomic_intent`, `domain_decisions: list[DomainAuthorization]`).

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Sanity check manual (`uv run python -c "..."`) — 4/4 kasus validator berperilaku benar (2 valid diterima, 2 invalid ditolak `ValidationError`).

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
