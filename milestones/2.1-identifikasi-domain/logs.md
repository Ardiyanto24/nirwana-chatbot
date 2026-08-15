# Logs — Milestone 2.1: Membangun Identifikasi Domain dan Verifikasi Titik Buta

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `11c0db7` | `docs(milestone-2.1): decisions` |
| 2 | `0d06870` | `feat(milestone-2.1): skema data identifikasi domain` |
| 3 | `15e39bd` | `chore(milestone-2.1): konstanta model identifikasi domain` |
| 4 | `f84980f` | `feat(milestone-2.1): konteks grounding domain` |
| 5 | *(commit ini)* | `feat(milestone-2.1): mekanisme identifikasi domain awal` |

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

**Commit:** `15e39bd`

---

## Checkpoint 4 — Konteks Grounding Domain

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 4 — `src/layers/domain_gate/konteks_domain.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`DESKRIPSI_DOMAIN` (dict 10 domain, deskripsi dikutip dari kolom "Isi" tabel Ringkasan 10 Domain `katalog-data-chatbot.md` baris 45-54) dan `CATATAN_POLA_JEBAKAN` (3 pola: kebocoran kolom turunan + contoh `gop_margin`/`v_reservation_gop_impact_monthly`, fokus terlalu sempit, pemisahan kolom `guests_pii`/`guests_profile` verbatim `rancangan-rbac-ai-chatbot.md` Bagian 1). Unit test regression: `DESKRIPSI_DOMAIN` cocok 1:1 dengan `Domain` Enum, tidak kosong, dan menyebut kedua kasus terdokumentasi.

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
`uv run pytest tests/layers/domain_gate/test_konteks_domain.py -v` — 3/3 PASSED.

**Commit:** `f84980f`

---

## Checkpoint 5 — Mekanisme Identifikasi Awal

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 5 — `src/layers/domain_gate/identifikasi.py`

**Kesesuaian dengan plan:** Menyimpang dari plan pada pendekatan test — plan menyebut "unit test dengan LLM di-mock". Setelah cek preseden nyata (`tests/layers/context_resolution/test_matching.py`, `tests/layers/decomposition/test_decompose.py`), ditemukan project TIDAK PERNAH memakai mock untuk panggilan LLM di `tests/` — konvensi nyata adalah panggilan LLM SUNGGUHAN, di-skip otomatis kalau `OPENROUTER_API_KEY` tidak diset. Diikuti pola preseden ini, bukan pola "mock" yang disebut plan: (a) fungsi pure (`bounds_check_domains`, `_parse_and_decide`) diuji langsung dengan string buatan tangan (deterministik, tanpa API, tanpa mock) untuk kasus hallucinated/parse-error, (b) `identifikasi_domain()` end-to-end diuji dengan panggilan LLM nyata untuk skenario KK1/KK3/baseline.

**Apa yang dilakukan**
`identifikasi_domain()` (span `chat`, model `OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI`), `_call_llm()` (mentah, dipisah untuk reuse eval), `bounds_check_domains()` + `_parse_and_decide()` (pure, deterministik). `IdentifikasiDomainResult` ditambahkan ke `src/schemas/domain_gate.py` (mirror pola `PemecahanResult`/`VerifikasiResult` M1.6 - hasil antara di schemas/, bukan lokal di file layer).

**Temuan**
Bug nyata ditemukan lewat panggilan LLM sungguhan (bukan mock) pada skenario `guests_profile`/nationality-mix: respons OpenRouter kembali dengan `response.choices` bernilai `None` (bukan exception `APIError`), menyebabkan `TypeError: 'NoneType' object is not subscriptable` saat mengakses `response.choices[0]`. Kode awal tidak menjaga kasus ini.

**Error/Kegagalan (jika ada)**
`TypeError: 'NoneType' object is not subscriptable` di `identifikasi_domain()`, dipicu test `test_kelompok_c_guests_profile_nationality_mix` (run pertama, 433s untuk 4 test - lihat Diagnosis).

**Diagnosis dan Perbaikan**
Root cause: `response.choices` bisa `None` pada respons yang secara teknis valid (bukan exception) tapi tidak berisi hasil apa pun (kemungkinan provider-side hiccup/moderasi/timeout parsial di sisi OpenRouter). Perbaikan: tambah guard eksplisit `if not response.choices:` sebelum indexing, dipetakan ke jalur fallback aman yang sama dengan `APIError` (`gagal=True`, span attribute `domain_gate.identifikasi.forced_fallback_reason="empty_choices"`) alih-alih crash.

**Hasil Verifikasi**
Sebelum fix: `pytest -k kelompok -s` — 3/4 PASSED (gop_margin leakage, guests_pii kontak, baseline domain tunggal), 1 FAILED (`TypeError`, guests_profile) dalam 433.30s.
Setelah fix: `pytest test_identifikasi.py::test_kelompok_c_guests_profile_nationality_mix -v -s` dijalankan ulang sendiri — PASSED dalam 33.91s (deteksi domain `guests_profile` tepat, `guests_pii` tidak ikut, konsisten KK3). `pytest tests/layers/domain_gate/ -k "not kelompok"` (7 test pure-function domain_gate + 3 test konteks_domain) — 10/10 PASSED setelah fix, memastikan tidak ada regresi di jalur parsing. Catatan kejujuran: 3 test real-LLM yang sudah PASSED sebelum fix (`kelompok_a`/`kelompok_b`/`kelompok_d`) TIDAK di-run-ulang penuh setelah fix (perubahan hanya menambah guard baru yang tidak tersentuh jalur respons normal) - keputusan sadar menghindari pemborosan panggilan API berbayar untuk kode yang tidak berubah perilakunya di jalur itu.

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
