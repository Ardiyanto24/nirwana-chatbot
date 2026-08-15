# Logs — Milestone 2.1: Membangun Identifikasi Domain dan Verifikasi Titik Buta

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya. Logs adalah catatan peristiwa, bukan ringkasan hasil akhir (itu tugas `report.md`).

**Ringkasan commit per checkpoint:**

| Checkpoint | Commit | Pesan |
|---|---|---|
| 1 | `11c0db7` | `docs(milestone-2.1): decisions` |
| 2 | `0d06870` | `feat(milestone-2.1): skema data identifikasi domain` |
| 3 | `15e39bd` | `chore(milestone-2.1): konstanta model identifikasi domain` |
| 4 | `f84980f` | `feat(milestone-2.1): konteks grounding domain` |
| 5 | `b9daa52` | `feat(milestone-2.1): mekanisme identifikasi domain awal` |
| 6 | `541820f` | `feat(milestone-2.1): mekanisme verifikasi titik buta` |
| 7 | `91abe27` | `feat(milestone-2.1): orkestrator identifikasi domain gate` |
| 8 | `73c5c78` | `docs(milestone-2.1): verifikasi span nyata` |
| 9 | *(commit ini)* | `docs(evals): rancangan pengujian identifikasi domain` |

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

**Commit:** `b9daa52`

---

## Checkpoint 6 — Mekanisme Verifikasi Titik Buta

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 6 — `src/layers/domain_gate/verifikasi_titik_buta.py`

**Kesesuaian dengan plan:** Sesuai plan setelah penyesuaian pendekatan test (sudah dicatat di Checkpoint 5, berlaku sama di sini — pure-function + panggilan LLM nyata, bukan mock). Satu detail teknis: parameter `reasoning="high"` OpenRouter TIDAK dikirim langsung sebagai kwarg (bukan parameter native SDK OpenAI) — dikirim lewat `extra_body={"reasoning": {"effort": "high"}}`, dicek dari kode nyata `src/layers/decomposition/verifikasi.py` (M1.6) supaya format persis konsisten, bukan menebak.

**Apa yang dilakukan**
`verifikasi_titik_buta()` (span `chat`, model `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA`, `reasoning="high"`), `_call_llm()` (mentah, reuse `bounds_check_domains()` dari `identifikasi.py`), `_parse_and_decide()` (pure — domain_tambahan kosong genuinely BUKAN dianggap anomali, beda dari `identifikasi.py` yang memaksa `gagal=True` kalau domain kosong). Guard `empty_choices` (preventif, mengantisipasi bug yang sama seperti ditemukan Checkpoint 5) langsung disertakan sejak awal, tidak menunggu ditemukan ulang.

**Temuan**
Tidak ada bug baru ditemukan (guard `empty_choices` preventif tidak pernah ter-trigger di test run ini).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Pure-function: `pytest test_verifikasi_titik_buta.py -k "not kelompok"` — 4/4 PASSED (1.82s). Panggilan LLM nyata: `pytest test_verifikasi_titik_buta.py -k kelompok -s` — 2/2 PASSED (33.51s) — **membuktikan KK2 langsung**: `test_kelompok_a_kk2_menangkap_domain_sengaja_dihilangkan` memberi `domain_awal=[reservation]` yang sengaja tidak lengkap untuk pertanyaan `gop_margin`, verifikasi titik buta berhasil menangkap `financial` sebagai `domain_tambahan`. `test_kelompok_b_guard_anti_false_positive...` mengonfirmasi tidak ada tambahan palsu saat `domain_awal` sudah lengkap.

**Commit:** `541820f`

---

## Checkpoint 7 — Orkestrator

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 7 — `src/layers/domain_gate/domain_gate.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan catatan kejujuran verifikasi eksplisit: cabang status `GAGAL_TEKNIS`/`SEBAGIAN` (pemetaan `hasil_awal.gagal`/`hasil_verifikasi.gagal`) TIDAK diuji lewat kegagalan API yang dipaksa nyata — project tidak pernah mock panggilan LLM, dan kegagalan API tidak bisa dipicu deterministik on-demand. Divalidasi lewat review kode (pemetaan if/else langsung dari flag `gagal` yang SUDAH teruji di level `identifikasi.py`/`verifikasi_titik_buta.py` via pure-function test Checkpoint 5-6) — dicatat eksplisit sebagai keterbatasan verifikasi, bukan diklaim teruji end-to-end.

**Apa yang dilakukan**
`identifikasi_domain_atomic_intent()` (gabung Langkah 1+2, union dedupe, verifikasi titik buta TIDAK dipanggil kalau identifikasi awal gagal) dan `identifikasi_domain_semua()` (filter `PERLU_EKSEKUSI`, span pembungkus `domain_gate.identifikasi_semua`).

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Hasil Verifikasi**
Deterministik (tanpa LLM): `test_filter_perlu_eksekusi_kosong_kalau_semua_selesai` — PASSED (2.12s), membuktikan jalur pintas filter bekerja tanpa satu pun panggilan LLM. Panggilan LLM nyata: `test_kelompok_a_union_domain_berhasil` (union `reservation`+`financial` benar, tanpa duplikat, `status=BERHASIL`) dan `test_kelompok_b_filter_campuran_selesai_dan_perlu_eksekusi` (hanya entri `PERLU_EKSEKUSI` yang diproses) — 2/2 PASSED dalam 161.93s.

**Commit:** `91abe27`

---

## Checkpoint 8 — Verifikasi Span Nyata

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 8 — Verifikasi span di Jaeger

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian eksplisit: skrip verifikasi awal mencoba 3 atomic intent sekaligus (gop_margin + guests_pii + guests_profile dalam satu `identifikasi_domain_semua()` call, hingga 6 panggilan LLM berantai) - dihentikan paksa setelah ~25 menit tanpa output karena disangka macet, ternyata proses masih hidup (CPU tumbuh lambat, wajar untuk I/O-bound menunggu respons LLM bergiliran, BUKAN deadlock). Diganti pendekatan: 1 atomic intent per run (2 panggilan LLM), dijalankan 2 kali terpisah untuk KK1 dan KK3 - lebih cepat dapat sinyal, dan cukup untuk tujuan checkpoint ini (membuktikan jalur ekspor span, bukan menguji ulang kualitas identifikasi - itu sudah dibuktikan Checkpoint 5-7, dan akan diuji lebih luas lagi di eval Checkpoint 9-11).

**Apa yang dilakukan**
Docker Desktop dimulai (belum jalan sebelumnya), `docker compose up -d` di `infra/observability/` (Jaeger+Collector+Prometheus, 3 container sehat). Skrip verifikasi one-off (scratchpad, TIDAK di-commit) memanggil `setup_tracing()` + `identifikasi_domain_semua()` nyata, dibungkus span `invoke_agent`, untuk skenario KK1 (`gop_margin`) dan KK3 (`nationality mix` -> `guests_profile`). Trace di-query langsung lewat Jaeger API (`curl http://localhost:16686/api/traces/<trace_id>`), bukan asumsi dari kode.

**Temuan**
(1) Latensi panggilan LLM signifikan lebih tinggi dari M1.6/M1.7 - Qwen3-32B tercatat 25-38 detik per panggilan, DeepSeek V4 Pro (`reasoning=high`) 14-16 detik, jauh dari perkiraan awal (kemungkinan beban/antrian provider saat ini, bukan karakteristik model tetap - butuh observasi lanjut, bukan kesimpulan final). (2) Trace KK3 (`nationality mix`) menunjukkan Langkah 1 (identifikasi) BENAR hanya mengenali `guests_profile` (persis KK3, `guests_pii` TIDAK ikut) - tapi Langkah 2 (verifikasi titik buta) menambahkan `reservation` sebagai `domain_tambahan` yang tidak jelas dasarnya untuk pertanyaan murni demografis tamu ("bulan ini" kemungkinan diasosiasikan verifier dengan konteks booking/reservasi). Ini POTENSI over-triggering blind-spot yang sudah diantisipasi sebagai risiko di plan ("Verifikasi titik buta... berisiko over-triggering") - sekarang punya satu data point nyata, bukan cuma hipotetis. Belum cukup bukti untuk kesimpulan (baru 1 kejadian) - didorong jadi fokus skenario eval Checkpoint 9-11, bukan diperbaiki prematur di sini.

**Error/Kegagalan (jika ada)**
Tidak ada error teknis - satu-satunya "kegagalan" adalah keputusan operasional membunuh proses run-3-intent yang disangka macet (lihat Kesesuaian dengan plan), bukan bug kode.

**Hasil Verifikasi**
Trace KK1 (`trace_id=ed0a755f60696aaaf3148458d510060a`): span `invoke_agent` (session.id, turn.index) -> `domain_gate.identifikasi_semua` (`intent.count=1`, `gagal_teknis_count=0`, `sebagian_count=0`) -> 2x span `chat` (Langkah 1: `qwen/qwen3-32b`, `domains_found=reservation,financial`, token usage terisi; Langkah 2: `deepseek/deepseek-v4-pro`, `domain_tambahan_count=1`) - **KK1 terbukti langsung**: `gop_margin` mengenali `reservation` DAN `financial`. Trace KK3 (`trace_id=6fed6752842c1f6f2ea9c7345046be40`): struktur span identik, Langkah 1 `domains_found=guests_profile` (persis, `guests_pii` tidak ikut) - **KK3 terbukti langsung**. Seluruh atribut `gen_ai.*` (operation.name, request.model, usage.input/output_tokens) dan atribut kustom (`domain_gate.identifikasi.domains_found`, `domain_gate.verifikasi_titik_buta.domain_tambahan_count`, `domain_gate.gagal_teknis_count`, `domain_gate.sebagian_count`, `intent.count`) terkonfirmasi ADA dan berisi nilai benar di Jaeger - sesuai kontrak Bagian 2 `rancangan-observability-ai-chatbot.md` (cakupan M2.1: span `chat` identifikasi+verifikasi titik buta; span lookup otorisasi bukan cakupan di sini, lihat decisions.md Keputusan 8).

**Commit:** `73c5c78`

---

## Checkpoint 9 — Rancangan Eval

**Mulai:** 2026-08-15 · **Selesai:** 2026-08-15

### Task 9 — `evals/2.1-identifikasi-domain/rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
10 skenario (S01-S10) fokus ke dimensi BELUM tercakup `tests/` (KK1-3 sudah teruji nyata di Checkpoint 5-8): generalisasi pola cross-domain kasus baru (S01), fokus terlalu sempit pola umum (S02), `guests_pii`+`guests_profile` gabungan (S03), retest temuan over-triggering Checkpoint 8 (S04), baseline `financial` murni (S05), guard anti-false-positive `hr` (S06), domain minor `properties_ref` (S07), multi-domain eksplisit kontrol (S08), `employees_directory`+`hr` (S09), jebakan payroll `financial` vs `hr` (S10).

**Temuan**
Tidak ada temuan baru.

**Error/Kegagalan (jika ada)**
Tidak ada.

**Commit:** *(pending — commit setelah entri ini ditulis)*

---
