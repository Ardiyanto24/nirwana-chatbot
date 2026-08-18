# Report — Milestone 7.1: Audit Kontrak Antar-Layer yang Sudah Terimplementasi

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai dengan penyesuaian dari plan.

Milestone 7.1 mengaudit kontrak aktual (dari kode nyata, bukan dokumen `rancangan-*.md`) untuk 18 baris unit kerja yang membentuk 9 layer pemrosesan (Milestone 1.2-4.5), menghasilkan `milestones/7.1-audit-kontrak-antar-layer/audit-kontrak-antar-layer.md` sebagai rujukan tunggal untuk Milestone 7.2-7.18 berikutnya. 16 dari 18 baris unit terbukti lewat panggilan nyata (real LLM/Supabase/HTTP, bukan mock) — baik dijalankan ulang minimal di milestone ini, maupun dikutip sah dari bukti historis yang diverifikasi masih valid. 4 penyimpangan material ditemukan dan dicatat eksplisit (retry loop Decomposition sampai 7 pemanggilan LLM, cross-layer call-back Execution M4.2→M3.4/M3.5/M2.4, docstring basi `narasi.py`, dan celah bukti nyata `chatbot_api` untuk `panggil_meta_chatbot_api()`+`eksekusi_atomic_intent()`) — yang terakhir didokumentasikan sebagai keterbatasan diterima baru (`docs/keterbatasan-diterima.md` #13) karena `chatbot_api` lokal tidak reachable saat Checkpoint 6 dikerjakan.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Setiap satu dari sembilan layer sudah py setidaknya satu panggilan percobaan nyata (bukan cuma baca kode) yang membuktikan bentuk kontraknya sesuai yang dicatat di dokumen audit." | 16/18 baris unit (semua 9 layer) dibuktikan lewat panggilan nyata — lihat tabel "Ringkasan Kontrak" di `audit-kontrak-antar-layer.md` dan detail run per checkpoint di `logs.md` (Checkpoint 2-6). 2 baris (`panggil_meta_chatbot_api()`, `eksekusi_atomic_intent()`, keduanya di layer Execution M4.1-4.2) TIDAK terpenuhi — `chatbot_api` lokal tidak reachable saat dicoba (Checkpoint 6). | **Sebagian** — 8 dari 9 layer terpenuhi penuh (Input Layer, Context Resolution, Decomposition, Domain Gate, Verification Gate, Retriever, Query Engine, Interpretation); layer Execution terpenuhi untuk unit HTTP-mekanik dasar (M4.1 fungsi raw, dikutip sah dari bukti Checkpoint 5 M4.1) tapi TIDAK untuk unit orkestrator M4.2 dan fungsi `_meta` M4.1 — lihat Bagian 5. |
| "Penyimpangan yang ditemukan (jika ada) dicatat eksplisit dengan rujukan ke milestone/PIC asalnya, bukan didiamkan atau diperbaiki diam-diam tanpa jejak." | 4 penyimpangan dicatat di section "Penyimpangan Ditemukan" `audit-kontrak-antar-layer.md`, masing-masing dengan rujukan checkpoint/milestone asal dan milestone 7.x yang terdampak. | **Ya**. |

## Bagian 3 — Cara Kerja dan Arsitektur

Milestone ini menghasilkan dokumen audit (`audit-kontrak-antar-layer.md`, `decisions.md`, `logs.md`) dan satu entri baru di `docs/keterbatasan-diterima.md` — tidak ada kode/sistem baru yang berjalan untuk didiagramkan. Lihat Bagian 1 untuk ringkasan hasil dan `audit-kontrak-antar-layer.md` untuk peta kontrak lengkap tiap unit kerja.

## Bagian 4 — Perubahan dari Plan

- **Checkpoint 6 tidak menghasilkan test integrasi baru** (`tests/layers/execution/test_klasifikasi_respons_integrasi.py`, yang direncanakan Task 11 kalau `chatbot_api` reachable) — sesuai fallback yang sudah disepakati di plan (Keputusan 7), karena `chatbot_api` lokal terbukti tidak reachable saat dicoba (`ConnectError [WinError 10061]`). Ini BUKAN penyimpangan dari plan (skenario ini eksplisit diantisipasi), melainkan realisasi cabang fallback yang memang direncanakan.
- **Satu koreksi temuan di tengah Checkpoint 6**: klaim awal draft audit ("file `pemanggilan_chatbot_api.py` tidak berubah sejak bukti nyata M4.1") diperiksa ulang lewat `git log` dan ternyata KELIRU — file berubah 2 kali setelah commit awal M4.1, termasuk penambahan `panggil_meta_chatbot_api()` SEHARI setelah tanggal bukti nyata M4.1 Checkpoint 5. Dikoreksi di tempat sebelum masuk konsolidasi Checkpoint 7 (lihat `logs.md` Checkpoint 6) — memperluas cakupan celah yang tercatat di `docs/keterbatasan-diterima.md` #13 dari sekadar "orkestrator M4.2" jadi juga mencakup fungsi `_meta` M4.1.
- Selain dua hal di atas, seluruh checkpoint dan task dikerjakan persis sesuai plan yang disetujui.

## Bagian 5 — Keterbatasan dan Item Provisional

- **`docs/keterbatasan-diterima.md` #13** (baru, ditulis milestone ini): `panggil_meta_chatbot_api()` (M4.1) dan `eksekusi_atomic_intent()` (M4.2) belum pernah dibuktikan panggilan nyata ke `chatbot_api` — trigger revisit eksplisit sebelum Milestone 7.14 (Level 2 Sambungan 9) dimulai. Lihat file itu untuk konteks lengkap.
- **`docs/keterbatasan-diterima.md` #4, #9, #12** dan **`docs/keputusan-tertunda.md` #2-4** — dikonfirmasi ulang statusnya saat audit (masih berlaku persis seperti tercatat), tidak ada perubahan status sebagai akibat milestone ini.
- Bukti nyata PIC 3 (Retriever, Query Engine) diambil lewat panggilan langsung fungsi produksi (mereplikasi skenario `evals/3.x-*/run_eval.py`), BUKAN lewat test `pytest` `skipif`-gated seperti PIC 1/2/M4.3 — dikonfirmasi tidak ada infrastruktur test real-call untuk PIC 3 di codebase saat ini (seluruh `tests/layers/{retriever,query_engine}/` memakai `monkeypatch`). Bukan gap yang perlu ditutup M7.1 (audit ini terpenuhi lewat cara lain), tapi dicatat sebagai observasi untuk PIC 3 kalau nanti butuh test real-call reguler.

## Bagian 6 — Follow-up

- **Milestone 7.2** (Level 1, Decomposition) wajib memperhitungkan retry loop Decomposition (hingga 7 pemanggilan LLM) saat merancang penyambungan internal — bukan pipa linear 3-langkah sederhana.
- **Milestone 7.5** (Level 1, Interpretation) — sebaiknya koreksi docstring basi `narasi.py` (masih menyebut M4.5 "belum dibangun") sebagai bagian kerja, bukan dibiarkan.
- **Milestone 7.14** (Level 2 Sambungan 9, Verification Gate → Execution) — WAJIB mengulang percobaan reachability `chatbot_api` sebelum dianggap selesai (jangan mewarisi status "belum diverifikasi nyata" M4.1-4.2 secara diam-diam); span `execute_tool` M4.2 membungkus span `chat` M3.4/M3.5 pada jalur revisi 400 lewat context propagation — perlu dikonfirmasi ulang perilaku ini nyata saat Sambungan 9 dibangun.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md` sebagai akibat milestone ini.
