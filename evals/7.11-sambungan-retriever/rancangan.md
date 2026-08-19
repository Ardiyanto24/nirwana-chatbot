# Rancangan Pengujian — Sambungan 6: Domain Gate → Retriever (Milestone 7.11)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — kejadian dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada. Struktur mirror `evals/7.6-.../` s.d. `evals/7.10-.../`.

**Pelajaran metodologi dari `evals/7.10-.../audit.md`** ("Temuan Metodologi"): jumlah/komposisi `atomic_intent` hasil Decomposition TIDAK BOLEH diasumsikan tetap bahkan untuk teks pertanyaan identik lintas run (non-determinisme `temperature=0` nyata, `docs/keterbatasan-diterima.md` #3) — ekspektasi di bawah ditulis sebagai **invarian mekanisme** (properti yang harus benar terlepas jumlah persis atomic_intent), bukan jumlah absolut.

## Yang Diuji

`proses_turn()` — SELURUH segmen baru M7.11 (3 unit wiring, lihat `decisions.md`): `periksa_otorisasi_semua()` (M2.2) → `deteksi_constraint_semua()` (M2.3) → `proses_retrieval_semua()` (Retriever, baru) dipanggil sekuensial setelah Domain Gate (M7.10) selesai. Kejadian di sini menjalankan pipeline PENUH dari `proses_turn()` nyata (Decomposition, Domain Gate identifikasi, Otorisasi, Cakupan Individu, Retriever) — bukan `list[AtomicIntentDomains]`/`list[AtomicIntentAuthorization]`/`list[AtomicIntentConstraint]` buatan tangan langsung dipassing ke fungsi manapun.

**Invarian mekanisme yang wajib benar di SEMUA kejadian** (independen dari jumlah/komposisi atomic_intent aktual):
1. Untuk tiap atomic intent, domain yang diteruskan ke Retriever (`domain_diizinkan`) = subset domain hasil identifikasi (M2.1) yang `diizinkan=True` di `otorisasi`/`cakupan_individu` — TIDAK PERNAH mengandung domain `diizinkan=False`.
2. Span `retriever.cari_kandidat_view` per atomic intent TIDAK PERNAH mengandung kandidat `view_name` dari domain yang ditolak otorisasi (atribut `retrieval.candidates_count` dan isi span anak `chat`/tag kandidat dicek langsung).
3. Span pembungkus `retriever.proses_semua` (tracer `retriever.retriever`) SELALU terbuka dengan atribut `intent.count` = panjang `KeadaanTurn.cakupan_individu` yang diteruskan — terlepas isinya (mirror pola E03 M7.10: span tetap ada meski `intent.count=0`).

## Kejadian

### E01 — Multi-domain, sebagian ditolak otorisasi (bukti KK literal utama, reuse skenario `gop_margin` M2.1/M7.3)

**Payload:** turn 1, `role_title="Front Office Staff"` (domain diizinkan HANYA `reservation`, per `rancangan-rbac-ai-chatbot.md` Bagian 2), `question="Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"` — skenario PERSIS sama dengan `tests/layers/domain_gate/test_domain_gate.py::test_konektivitas_identifikasi_verifikasi_titik_buta_skenario_gop_margin` (M7.3) dan `evals/2.1-.../` (M2.1 asli): pertanyaan yang secara eksplisit hanya menyebut satu domain (`reservation`, lewat "deviasi harga") tapi menyentuh kolom turunan `financial` (`gop_margin`).

**Ekspektasi:**
- Domain Gate (M2.1, tersambung M7.10) mengidentifikasi domain `reservation` DAN `financial` untuk atomic intent yang menyentuh `gop_margin` (KK literal M2.1/M7.3, sudah terbukti nyata sebelumnya).
- Otorisasi (M2.2, Checkpoint 2-3 M7.11): `reservation` → `diizinkan=True`; `financial` → `diizinkan=False` (Front Office Staff tidak punya akses `financial` — dikonfirmasi tabel role×domain DAN test existing `test_kk2_multi_domain_sebagian_diizinkan_sebagian_ditolak`).
- `domain_diizinkan` yang diteruskan ke `proses_retrieval_atomic_intent()` untuk atomic intent ini = `[reservation]` SAJA — TIDAK mengandung `financial`.
- **Bukti KK literal M7.11**: span `retriever.cari_kandidat_view` untuk atomic intent ini TIDAK mengandung kandidat `view_name` mana pun dari domain `financial` (mis. `v_financial_gop_summary_monthly` atau sejenis) — hanya kandidat domain `reservation`.

---

### E02 — Baseline: seluruh domain diizinkan (happy path)

**Payload:** turn 1, `role_title="CEO"` (akses SEMUA 7 domain operasional + `all_properties`), `question="Berapa occupancy rate properti kita bulan ini?"` (pertanyaan domain tunggal `reservation`, tidak ambigu).

**Ekspektasi:**
- Domain Gate mengidentifikasi `[reservation]` (kemungkinan besar tunggal, tanpa jebakan cross-domain seperti E01).
- Otorisasi: `reservation` → `diizinkan=True` (CEO py akses semua domain).
- `domain_diizinkan` diteruskan = `[reservation]` — Retriever mencari NORMAL, tidak ada pembatasan.
- `view_name_final` terisi (bukan `None`) — kandidat `reservation` ditemukan dan cukup struktural untuk label `nilai_tunggal`/`tren` (occupancy rate biasanya `nilai_tunggal` atau `tren`, KEDUANYA valid per taksonomi M1.6).

---

### E03 — Edge case: seluruh domain satu atomic intent ditolak

**Payload:** turn 1, `role_title="F&B Staff"` (domain diizinkan HANYA `fnb`, per tabel role×domain), `question="Berapa GOP (gross operating profit) properti bulan ini?"` (metrik murni `financial`, di luar cakupan `fnb`).

**Ekspektasi:**
- Domain Gate mengidentifikasi `[financial]` untuk atomic intent GOP.
- Otorisasi: `financial` → `diizinkan=False` (F&B Staff tidak punya akses `financial` sama sekali).
- `domain_diizinkan` hasil derive = `[]` (KOSONG) — TETAP diteruskan ke `proses_retrieval_atomic_intent(atomic_intent, [])`, TIDAK di-skip orkestrator (decisions.md Keputusan 7).
- **Bukti ketahanan mekanisme**: `proses_turn()` SELESAI NORMAL tanpa exception; `HasilKecukupanStruktural.view_name_final=None` untuk atomic intent ini (tidak ada kandidat sama sekali, bukan crash); `status=BERHASIL` (mekanisme M3.1-3.3 didesain "tidak pernah gagal teknis di level kebutuhan-atomik", Keputusan 6 M7.11).
- Span `retriever.cari_kandidat_view` tetap terbuka dengan `retrieval.candidates_count=0`.

---

### E04 — Bukti sambungan M2.3 (Deteksi Cakupan Individu), reuse skenario `evals/2.3-.../S01`

**Payload:** turn 1, `role_title="HR Staff"` (Staff tier, domain diizinkan `hr`), `question="Bagaimana hasil review kinerja Budi semester ini?"` — persis teks `evals/2.3-deteksi-cakupan-individu/payloads/S01.json` (skenario "Review kinerja individu by name (hr)", sudah terbukti `constraint.terdeteksi=True` di M2.3 asli).

**Ekspektasi:**
- Domain Gate mengidentifikasi `[hr]`.
- Otorisasi: `hr` → `diizinkan=True` (HR Staff punya akses `hr`).
- Cakupan Individu (M2.3, Checkpoint 4-5 M7.11): `role_title="HR Staff"` ADA di `ROLE_STAFF_TIER`, domain `hr` ADA di `_DOMAIN_RELEVAN={FACILITY, HR}` → kedua pre-filter deterministik LOLOS, kedua langkah LLM (deteksi + verifikasi) dipanggil → `KeadaanTurn.cakupan_individu[0].constraint.terdeteksi=True` (pertanyaan menyebut nama individu "Budi" + kategori data performa).
- `domain_diizinkan` tetap `[hr]` diteruskan ke Retriever apa adanya — `constraint.terdeteksi` TIDAK memengaruhi pemanggilan Retriever (decisions.md Keputusan 8, penegakan sesungguhnya ditunda ke Verification Gate M2.4/M7.13).
- Span `domain_gate.deteksi_constraint_semua` (tracer `domain_gate.cakupan_individu`) py atribut `constraint.terdeteksi_count=1`.

## Ringkasan Ekspektasi

| ID | `role_title` | Domain diidentifikasi | Diizinkan | Ditolak | `domain_diizinkan` ke Retriever | `view_name_final` | `cakupan_individu.terdeteksi` |
|---|---|---|---|---|---|---|---|
| E01 | Front Office Staff | reservation, financial | reservation | financial | `[reservation]` | terisi (reservation) | — (bukan hr/facility) |
| E02 | CEO | reservation | reservation | — | `[reservation]` | terisi | False |
| E03 | F&B Staff | financial | — | financial | `[]` | `None` | False |
| E04 | HR Staff | hr | hr | — | `[hr]` | terisi/`None` (tidak jadi fokus utama) | **True** |

**Catatan invarian vs jumlah absolut**: tabel di atas menyatakan domain YANG DIHARAPKAN untuk atomic intent UTAMA tiap skenario — kalau Decomposition nyata menghasilkan atomic intent TAMBAHAN di luar prediksi (pola berulang di M7.9/M7.10), invarian mekanisme (baris "Yang Diuji" di atas) tetap jadi kriteria lolos utama per-atomic-intent, bukan jumlah total yang harus persis cocok.
