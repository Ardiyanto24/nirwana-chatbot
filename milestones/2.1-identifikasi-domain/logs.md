# Logs — Milestone 2.1: Membangun Identifikasi Domain dan Verifikasi Titik Buta

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `11c0db7` | `docs(milestone-2.1): decisions` |
| 2 | `0d06870` | `feat(milestone-2.1): skema data identifikasi domain` |
| 3 | *(commit ini)* | `chore(milestone-2.1): konstanta model identifikasi domain` |

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

**Commit:** `11c0db7`

---

## Checkpoint 2 — Skema Data

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 2 — `src/schemas/domain_gate.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian eksplisit: unit test skema (validator `domains_konsisten_dengan_status`) TIDAK dibuat sebagai file terpisah `tests/schemas/test_domain_gate.py` — dicek `tests/` project tidak py preseden direktori `tests/schemas/` sama sekali (skema M1.7 `AtomicIntentMatch` juga tidak py test dedicated terpisah). Diikutkan ke `tests/layers/domain_gate/test_domain_gate.py` (Checkpoint 7) alih-alih, sesuai opsi eksplisit yang sudah disebut plan ("atau digabung ke test layer Checkpoint 8/7") — bukan penyimpangan tersembunyi.

**Apa yang dilakukan**
`Domain` (`StrEnum` 10 nilai persis Keputusan 4) dan `AtomicIntentDomains` (`atomic_intent`, `domains: list[Domain]`, `status: StatusEksekusi` reuse M1.5) dengan validator `domains_konsisten_dengan_status` — `GAGAL_TEKNIS` wajib `domains` kosong, selain itu wajib non-kosong.

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** `0d06870`

---

## Checkpoint 3 — Konstanta Model

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 3 — `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI` (`qwen/qwen3-32b`) dan `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA` (`deepseek/deepseek-v4-pro`) ditambahkan, terisolasi dari konstanta M1.6 meski nilai identifikasi kebetulan sama (Keputusan 7).

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
