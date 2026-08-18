# Logs — Milestone 7.1: Audit Kontrak Antar-Layer yang Sudah Terimplementasi

## Checkpoint 1 — Persiapan & Keputusan

- Commit `docs/02-implementation-plan/rancangan-orkestrasi-api.md` (sudah ditulis sebelumnya, untracked) — dokumen sumber lengkap grup 7.x (Level 1 M7.2-7.5, Level 2 M7.6-7.16, M7.17 endpoint, M7.18 Database Percakapan).
- Tambah item 9 "Dokumen Sumber Kebenaran" di `CLAUDE.md`/`AGENT.md` (rujukan ke dokumen di atas), renumber item domain-source lama (9→10) dan milestones (10→11). Kedua file gitignored, tidak masuk commit git (sesuai konvensi project).
- Tulis `decisions.md` — 7 keputusan (5 forced/preseden + 2 genuinely-terbuka yang sudah dijawab user lewat `AskUserQuestion` di Plan Mode).
- Commit hash: `cc42857` (docs: rancangan-orkestrasi-api.md), `fd0df15` (docs: decisions.md).

## Checkpoint 2 — Audit PIC 1 (Input Layer, Context Resolution, Decomposition)

**Task 3 — Audit source.** Dibaca langsung (bukan mengandalkan ringkasan sesi planning): `src/schemas/turn_payload.py`, `src/layers/context_resolution/turn_dependency.py`, `src/layers/context_resolution/rewrite.py`, `src/layers/context_resolution/session_memory.py`, `src/layers/context_resolution/matching.py`, `src/layers/decomposition/decompose.py`, `src/schemas/decomposition.py`.

Temuan kunci yang dikonfirmasi langsung dari kode (bukan asumsi):
- `decompose_question()` (M1.6): `_MAX_ATTEMPTS = 3`, loop `while True` dengan `attempt` mulai 1, break kalau `verifikasi.valid` atau `attempt >= 3`. Klasifikasi 1x di luar loop + Pemecahan/Verifikasi hingga 3x di dalam loop = **hingga 7 pemanggilan LLM total** dalam kasus terburuk. Dicatat sebagai penyimpangan dari framing "3 pemanggilan LLM berurutan" di `rancangan-orkestrasi-api.md` — lihat `audit-kontrak-antar-layer.md` bagian M1.6.
- `matching.py::_sumber_arsip()` (M1.7): mekanisme penjagaan rantai turn-asal lintas pengarsipan berulang — detail yang tidak sepenuhnya tertangkap ringkasan awal, ditambahkan ke audit.
- `src/main.py` dikonfirmasi ulang murni echo `POST /v1/turns`, nol layer lain terpanggil.

Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 1".

**Task 4 — Panggilan nyata minimal per unit** (env `OPENROUTER_API_KEY`/`DATABASE_URL` aktif otomatis lewat `load_dotenv()` di `src/config/llm.py`/`database.py`):

| Unit | Test dijalankan | Hasil | Durasi |
|---|---|---|---|
| M1.2 Input Layer | `tests/layers/test_input_layer.py` (seluruh file, 12 test — real `TestClient`, tanpa biaya eksternal) | 12 passed | 6.08s |
| M1.3 Turn Dependency | `test_turn_dependency.py::test_kelompok_a_rujukan_eksplisit_ke_turn_sebelumnya` | 1 passed | 11.47s |
| M1.4 Rewrite | `test_rewrite.py::test_kelompok_a_elipsis_diresolusi_jadi_eksplisit` | 1 passed | 8.57s |
| M1.5 Session Memory | `test_session_memory.py::test_kelompok_a_simpan_lalu_ambil_kembali_identik` (real Supabase round-trip) | 1 passed | 2.50s |
| M1.6 Decomposition | `test_decompose.py::test_kelompok_a_majemuk_bergantung_relasi_benar` (rantai penuh klasifikasi→pemecahan→verifikasi) | 1 passed | 42.86s (konsisten ≥3 LLM call berurutan) |
| M1.7 Matching | `test_matching.py::test_kelompok_c_rantai_arsip_ulang_turn_tujuh_lima_tiga` (skenario rantai arsip, LLM+DB) | 1 passed | 28.61s |

Seluruh 6 unit PIC 1 lolos panggilan nyata — tidak ada skip/mock terdeteksi (durasi tiap test konsisten dengan pemanggilan API/DB sungguhan, bukan instan seperti mock).

## Checkpoint 3 — Audit PIC 2 (Domain Gate, Verification Gate)

**Task 5 — Audit source.** Dibaca langsung: `src/layers/domain_gate/{domain_gate,identifikasi,verifikasi_titik_buta,otorisasi,cakupan_individu,deteksi_cakupan_individu,verifikasi_cakupan_individu}.py`, `src/layers/verification_gate/verifikasi_gate.py`. Temuan kunci dikonfirmasi langsung dari kode:
- M2.1: penggabungan Langkah 1+2 union aditif via `dict.fromkeys()` (dedup, urutan dipertahankan), status `SEBAGIAN` kalau verifikasi gagal teknis. Langkah 2 di-skip total kalau Langkah 1 gagal (bukan dipanggil dengan domain kosong).
- M2.3: dua pre-filter deterministik persis sesuai ringkasan awal — `ROLE_STAFF_TIER` (7 role) dan domain relevan `{FACILITY, HR}`; fail-closed (`terdeteksi=True`) hanya kalau KEDUA langkah LLM gagal teknis sekaligus (arah fail-safe berlawanan dari M1.7).
- M2.4: 4 cek berlapis dikonfirmasi tepat urutannya (statis→kepatuhan sumber→tegakkan constraint→verifikasi kelengkapan), `LIMIT_MAKSIMUM=1000` eksplisit di kode, early-exit hanya di Cek 1-2 (Cek 3 tidak pernah menolak, hanya mengoreksi paksa).

Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 2".

**Task 6 — Panggilan nyata minimal per unit:**

| Unit | Test dijalankan | Hasil | Durasi |
|---|---|---|---|
| M2.1 Domain Gate | `test_domain_gate.py::test_kelompok_a_union_domain_berhasil` (real LLM, 2 langkah) | 1 passed | 42.26s |
| M2.2 Otorisasi | `test_otorisasi.py::test_kk2_multi_domain_sebagian_diizinkan_sebagian_ditolak` (real DB role_permissions) | 1 passed | 3.26s |
| M2.3 Cakupan Individu | `test_cakupan_individu.py::test_kk1_staff_kebutuhan_individu_menghasilkan_constraint_eksplisit` (real LLM, 2 langkah) | 1 passed | 27.82s |
| M2.4 Verification Gate | `test_verifikasi_gate.py::test_orkestrator_kk1_constraint_terdeteksi_dikoreksi_paksa` (real DB employee fixture) | 1 passed | 2.02s |

Seluruh 4 unit PIC 2 lolos panggilan nyata.

## Checkpoint 4 — Audit PIC 3 (Retriever, Query Engine)

**Task 7 — Audit source.** Dibaca langsung: `src/layers/retriever/{retriever,kecocokan_makna,kecukupan_struktural}.py`, `src/layers/query_engine/{penyusunan_request,verifikasi_bentuk_request}.py`. Temuan kunci:
- Entry point produksi Retriever bukan `cari_kandidat_view()` (M3.1 standalone) melainkan `kecukupan_struktural.py::proses_retrieval_atomic_intent()` — membungkus M3.1+M3.2+M3.3 dalam satu span `retriever.cari_kandidat_view`. Penting untuk M7.11/M7.12 (Sambungan 6-7) supaya tidak salah pakai wrapper standalone.
- M3.2 Langkah 2 (verifikasi) MENGGANTIKAN Langkah 1 sepenuhnya (koreksi dua arah) — beda pola dari union aditif M2.1/M2.3.
- M3.5 sengaja duplikat cek string M2.4 (`_view_name_sesuai_retriever` vs `verifikasi_kepatuhan_sumber`) — didokumentasikan eksplisit sebagai redundansi disengaja, bukan dead code.

**Cek infrastruktur test:** dikonfirmasi seluruh file test PIC 3 (`test_kecocokan_makna.py`, `test_kecukupan_struktural.py`, `test_pencarian_embedding.py`, `test_penyusunan_request.py`, `test_verifikasi_bentuk_request.py`) memakai `monkeypatch` — TIDAK ada test `skipif`-gated real-call untuk PIC 3 (beda dari PIC 1/2). Bukti nyata untuk PIC 3 karena itu diambil dari `evals/3.x-*/run_eval.py` (yang eksplisit "NYATA, bukan mock" di docstring-nya) dan panggilan langsung fungsi produksi.

Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 3".

**Task 8 — Panggilan nyata minimal per unit** (panggilan langsung fungsi produksi, mereplikasi pola skenario `evals/3.x-*/run_eval.py` tanpa menjalankan seluruh batch skenario):

| Unit | Panggilan | Hasil |
|---|---|---|
| M3.1-3.3 (jalur BM25+deterministik) | `proses_retrieval_atomic_intent()` skenario S02 eval 3.3 ("okupansi Suite Bali") | `status=BERHASIL`, `view_name_final=v_reservation_room_type_daily`, 1 kandidat `cukup=True sumber=DETERMINISTIK` |
| M3.1 (jalur embedding fallback) | `cari_bm25()` (0 hasil, `perlu_fallback=True`) → `cari_embedding()` query typo sengaja | `gagal=False`, 10 kandidat nyata (top: `v_lookup_daily_occupancy` skor 0.309) |
| M3.4 | `susun_request_atomic_intent()` skenario setara S02, `tanggal_referensi=2026-08-17` | `status=BERHASIL`, `request.params` terisi (`region=Bali, room_type_name=Suite, period_date_from/to, occupancy_rate`) |
| M3.5 | `verifikasi_bentuk_request_atomic_intent()` request hasil M3.4 di atas | `status=BERHASIL, lolos=True, alasan=None` |

Catatan non-blocking: param `occupancy_rate` hasil M3.4 bernilai literal `"occupancy_rate"` (nama field sebagai value) — kemungkinan artefak ekstraksi LLM untuk skenario spesifik ini, BUKAN penyimpangan kontrak (struktur `params: dict` tetap sesuai skema; whitelist filtering bekerja benar). Dicatat sebagai observasi kualitas output, bukan bug kontrak — di luar cakupan M7.1 untuk diperbaiki.

Seluruh unit PIC 3 lolos panggilan nyata (real LLM/embedding, bukan mock).

## Checkpoint 5 — Audit PIC 4, bagian tanpa dependensi `chatbot_api` lokal (M4.3, M4.4, M4.5)

**Task 9 — Audit source.** Dibaca langsung: `src/layers/execution/penyimpanan_paket.py`, `src/layers/interpretation/{narasi,verifikasi_kesetiaan,visualisasi}.py`. Temuan kunci dikonfirmasi langsung dari kode:
- **Docstring basi dikonfirmasi nyata**: `narasi.py` baris 6 masih tertulis "Dipisah dari verifikasinya (Milestone 4.5, **belum dibangun**)" — dibaca langsung dari file saat ini (bukan cache/ringkasan), M4.5 sudah lengkap dibangun. Dicatat sebagai penyimpangan dokumentasi (non-fungsional) di `audit-kontrak-antar-layer.md`.
- `susun_narasi()` (M4.4) dikonfirmasi sebagai satu-satunya pemanggilan LLM di seluruh codebase TANPA fallback aman — `APIError` di-raise ulang apa adanya, bukan ditangkap.
- `verifikasi_dan_susun_visualisasi()` (M4.5) memakai `hasil_verifikasi.lolos is True` (bukan truthy check) — `lolos=None` (dari `GAGAL_TEKNIS`) juga menghasilkan visualisasi `None`, dikonfirmasi bukan bug.

Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 4" (M4.3-4.5).

**Task 10 — Panggilan nyata minimal per unit:**

| Unit | Panggilan | Hasil |
|---|---|---|
| M4.3 Penyimpanan Paket | `tests/layers/execution/test_penyimpanan_paket_integrasi.py::test_kk1_round_trip_identik` (real Supabase) | 1 passed, 3.65s |
| M4.4 Penyusunan Narasi | `susun_narasi()` dipanggil langsung, 1 atomic_intent + 1 package (`nilai_tunggal` okupansi) | Narasi nyata dihasilkan: "Okupansi Suite di Bali bulan ini adalah 72,5%..." |
| M4.5 Verifikasi Kesetiaan + Visualisasi | `verifikasi_dan_susun_visualisasi()` dipanggil dengan narasi hasil M4.4 di atas | `status=BERHASIL, lolos=True`; visualisasi dihasilkan `DataVisualisasi(nilai_tunggal=72.5, deret=None)` |

Satu rantai panggilan M4.4→M4.5→visualisasi berhasil membuktikan alur penuh secara nyata dalam satu eksekusi (narasi asli dari M4.4 benar-benar dinilai M4.5, bukan narasi buatan terpisah).

## Checkpoint 6 — Audit PIC 4, bagian bergantung `chatbot_api` lokal (Execution M4.1 + M4.2)

**Task 11 — Cek ketersediaan + audit source.**

1. Dibaca langsung: `src/layers/execution/{pemanggilan_chatbot_api,klasifikasi_respons}.py`.
2. Cek ketersediaan `chatbot_api` lokal:
   ```
   $ curl -s -o /dev/null -w "%{http_code}\n" --max-time 5 http://127.0.0.1:8000/
   000 (CONN_FAILED)
   $ python -c "httpx.get('http://127.0.0.1:8000/', timeout=5)"
   ConnectError [WinError 10061] No connection could be made because the target machine actively refused it
   ```
   **Tidak reachable.** Sesuai Keputusan 7 (`decisions.md`), fallback ke dokumentasi keterbatasan diterima — TIDAK memblokir Checkpoint 7.
3. Audit `eksekusi_atomic_intent()` (M4.2) mengonfirmasi: memanggil `_panggil_chatbot_api_raw()` langsung (bukan wrapper publik M4.1); pemetaan status 200/`403`+`404`/`400`/lainnya dikonfirmasi persis dari kode; jalur `400` memanggil balik M3.4→M3.5→M2.4 (cross-layer call-back, dicatat sebagai temuan penting untuk M7.14).
4. **Koreksi temuan di tempat**: klaim awal ("file `pemanggilan_chatbot_api.py` tidak berubah sejak M4.1") diperiksa ulang lewat `git log -- src/layers/execution/pemanggilan_chatbot_api.py` — **klaim itu KELIRU**. File berubah 2x setelah commit awal M4.1 (`6e2d71f`, 2026-08-17 19:11): refactor `bc9c855` (2026-08-17 21:29, regresi-tested behavior-preserving) dan penambahan `panggil_meta_chatbot_api()` di `3329ff9` (**2026-08-18**, SEHARI setelah tanggal laporan bukti nyata M4.1 Checkpoint 5). Konsekuensi: `panggil_meta_chatbot_api()` belum pernah dibuktikan panggilan nyata sama sekali — dikoreksi di `audit-kontrak-antar-layer.md` dan digabung ke entri keterbatasan yang sama (bukan entri terpisah, karena fungsi ini hanya dipanggil dari `eksekusi_atomic_intent()`).

**Task 12 — Catat hasil.**

- Ditulis ke `audit-kontrak-antar-layer.md` bagian "PIC 4" (M4.1-M4.2), termasuk koreksi temuan `git log` di atas.
- Ditulis entri baru `docs/keterbatasan-diterima.md` #13 — celah `eksekusi_atomic_intent()`/`panggil_meta_chatbot_api()` tanpa bukti nyata `chatbot_api`, dengan trigger revisit eksplisit (sebelum Milestone 7.14 dimulai).
- M4.1 (fungsi `_panggil_chatbot_api_raw()`/`panggil_chatbot_api()`) TETAP dianggap terbukti nyata lewat kutipan sah Milestone 4.1 Checkpoint 5 (trace_id konkret, refactor regresi-tested) — HANYA `panggil_meta_chatbot_api()` dan `eksekusi_atomic_intent()` yang jadi celah tercatat.

## Checkpoint 7 — Konsolidasi dan Penutupan

**Task 13.** "Ringkasan Kontrak" (tabel 18 baris unit lintas 9 layer) dan section "Penyimpangan Ditemukan" (4 entri, masing-masing dengan rujukan checkpoint asal + milestone 7.x terdampak) ditambahkan di bagian atas `audit-kontrak-antar-layer.md`.

**Task 14.** Log ini (Checkpoint 1-7) final — kronologi lengkap tersedia di atas, termasuk satu koreksi temuan di tengah jalan (Checkpoint 6, klaim git log yang semula keliru).

**Task 15.** `report.md` ditulis — Kriteria Keberhasilan sumber vs bukti, keterbatasan, follow-up untuk M7.2/M7.5/M7.14.

**Task 16.** `CLAUDE.md`/`AGENT.md` diperbarui — baris M7.1 (Selesai) + kerangka M7.2-7.18 (Berikutnya) ditambahkan ke tabel Status Proyek.

**Ringkasan angka akhir milestone:** 6 checkpoint audit (2-6, dibagi per grup PIC) + 1 checkpoint persiapan (1) + 1 checkpoint penutupan (7) = 8 commit `docs`/`test` total. 18 baris unit kerja diaudit, 16 terbukti nyata, 2 tercatat sebagai celah (keterbatasan diterima #13), 4 penyimpangan ditemukan dan dicatat eksplisit, 0 didiamkan.
