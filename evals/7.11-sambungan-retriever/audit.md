# Audit — Sambungan 6: Domain Gate → Retriever (Milestone 7.11)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-19), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) dijalankan lokal sepanjang eksekusi. Verifikasi substantif "tidak ada kandidat dari domain ditolak" dilakukan lewat inspeksi langsung return value `proses_turn()` (`hasil.retriever[i].kecukupan[*].kandidat.domain`), BUKAN parsing tag Jaeger — span `retriever.cari_kandidat_view` hanya merekam `retrieval.candidates_count` (jumlah), tidak merekam domain per-kandidat individual (dikonfirmasi sebelum `run_eval.py` ditulis, lihat komentar modul).

## Ringkasan

**4/4 kejadian LOLOS — zero_leakage=True di SELURUH atomic intent yang diproses (7 atomic intent total lintas 4 kejadian), tanpa satu pun kebocoran domain.** KK literal M7.11 terbukti PALING JELAS di E01 intent ketiga (kombinasi `gop_margin` PERSIS seperti M2.1/M7.3): domain teridentifikasi `[reservation, financial, properties_ref]`, `financial` DITOLAK otorisasi (Front Office Staff), `view_name_final=v_reservation_gop_impact_monthly` — view domain `reservation` yang membawa kolom turunan `gop_margin`, BUKAN view domain `financial` mana pun. E03 membuktikan ketahanan edge case (domain kosong, 0 kandidat, `proses_turn()` selesai normal tanpa exception). E04 membuktikan sambungan M2.3 bekerja (`cakupan_individu.terdeteksi=True` untuk pertanyaan performa individu dari role Staff).

**Penyimpangan dari rencana (non-determinisme Decomposition, pola sama seperti M7.9/M7.10)**: E01 dan E02 sama-sama diklasifikasikan `tunggal` oleh Decomposition TAPI menghasilkan 3 atomic_intents (bukan 1) — perilaku internal Decomposition (M1.6) di luar cakupan revisi M7.11, dicatat transparan sebagai observasi, bukan disembunyikan. Ini TIDAK melemahkan verdict: justru MEMPERKUATNYA — 3 atomic intent independen di E01 berarti 3 kesempatan independen untuk kebocoran domain terjadi, dan zero_leakage tetap `True` di ketiganya.

| ID | `role_title` | Jumlah atomic intent | Domain ditolak (union) | Kandidat bocor (union) | Verdict |
|---|---|---|---|---|---|
| E01 | Front Office Staff | 3 | `financial` (2 intent) | **Tidak ada** | ✅ **LOLOS — bukti KK literal utama, PERSIS skenario gop_margin** |
| E02 | CEO | 3 | — (tidak ada, semua diizinkan) | — | ✅ LOLOS — baseline bersih |
| E03 | F&B Staff | 1 | `financial` (seluruh domain intent) | **Tidak ada** (0 kandidat) | ✅ LOLOS — edge case domain kosong, tanpa crash |
| E04 | HR Staff | 1 | — (hr diizinkan) | — | ✅ LOLOS — sambungan M2.3 (`cakupan_individu=True`) terbukti |

## Analisis Per Kejadian

### E01 — Multi-domain sebagian ditolak otorisasi (LOLOS — bukti KK literal utama)

`trace_id=607bf2c76d3e529fea2d5798dbe50cef`. Payload: `role_title="Front Office Staff"`, pertanyaan "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?" (skenario `gop_margin` PERSIS M2.1/M7.3). Decomposition `klasifikasi=tunggal` tapi menghasilkan **3 atomic_intents** (bukan 1 seperti prediksi `rancangan.md`) — dicatat sebagai penyimpangan (lihat "Temuan Metodologi").

Ketiga atomic intent dan hasilnya:
1. Domain `[reservation, properties_ref]`, keduanya diizinkan → `view_name_final=v_reservation_gop_impact_monthly`. `zero_leakage=True`.
2. Domain `[financial, properties_ref]`, `financial` DITOLAK → `domain_diizinkan=[properties_ref]` saja → `view_name_final=None` (tidak ada kandidat `properties_ref` yang cukup untuk kebutuhan ini). `zero_leakage=True`.
3. **Intent inti (persis skenario gop_margin)**: domain `[reservation, financial, properties_ref]` — replikasi PERSIS identifikasi cross-domain M2.1/M7.3 (KK literal M2.1: "kolom turunan `financial` di view domain `reservation`"). `financial` DITOLAK, `domain_diizinkan=[reservation, properties_ref]` → `view_name_final=v_reservation_gop_impact_monthly`. **`zero_leakage=True`** — tidak ada kandidat domain `financial` yang muncul di `kecukupan` intent ini, dikonfirmasi lewat inspeksi langsung `KecukupanKandidat.kandidat.domain` untuk seluruh kandidat yang dievaluasi M3.2/M3.3.

Span Jaeger mengonfirmasi: `domain_gate.periksa_otorisasi_semua` (`intent.count=3`), `authorization.check` × 7 (3 intent × domain masing-masing: 2+2+3=7, cocok), `retriever.proses_semua` (`intent.count=3`), 3× span `retriever.cari_kandidat_view` dengan `retrieval.candidates_count`/`retrieval.selected_view` sesuai hasil di atas.

**Kesimpulan: Kriteria Keberhasilan literal Milestone 7.11 TERPENUHI PENUH** — kebutuhan dengan domain sebagian ditolak (`financial`) menghasilkan Retriever yang hanya menemukan kandidat dari domain yang lolos (`reservation`), dibuktikan lewat inspeksi langsung hasil `proses_turn()` sungguhan (bukan mock), bukan dicocokkan manual.

### E02 — Baseline seluruh domain diizinkan (LOLOS)

`trace_id=4608f3d00be84a1fb65367af4061d17e`. Payload: `role_title="CEO"`, "Berapa occupancy rate properti kita bulan ini?" — Decomposition juga `klasifikasi=tunggal` tapi 3 atomic_intents (pola sama E01). Ketiganya domain-nya seluruhnya diizinkan (CEO akses semua 7 domain + referensi) — `zero_leakage=True` trivially untuk ketiganya (tidak ada domain ditolak untuk dibandingkan). 2 dari 3 intent mendapat `view_name_final` terisi (`v_reservation_room_type_daily`, `v_properties_ref`); 1 intent (`[properties_ref, facility]`) tidak menemukan kandidat cukup (`view_name_final=None`) — bukan kegagalan, murni tidak ada view yang cocok untuk kombinasi kebutuhan itu, konsisten desain M3.3 ("tidak pernah gagal teknis, `view_name_final=None` adalah hasil valid").

**Kesimpulan: baseline bersih terbukti** — tanpa pembatasan otorisasi, Retriever bekerja normal, tidak ada distorsi dari wiring M7.11 pada jalur happy-path.

### E03 — Edge case domain kosong (LOLOS — ketahanan mekanisme)

`trace_id=e57b3b52847c83f600ae691719817945`. Payload: `role_title="F&B Staff"`, "Berapa GOP (gross operating profit) properti bulan ini?" — Decomposition `tunggal`, 1 atomic_intent, PERSIS sesuai prediksi. Domain teridentifikasi `[financial]` — F&B Staff TIDAK punya akses `financial` sama sekali → `domain_diizinkan=[]` (kosong). `proses_retrieval_semua()` (Checkpoint 6) TETAP memanggil `proses_retrieval_atomic_intent(atomic_intent, [])` apa adanya (tidak di-skip, sesuai Keputusan 7) — hasil: `retrieval.candidates_count=0`, `view_name_final=None`, `status=BERHASIL` (bukan `GAGAL_TEKNIS`). `proses_turn()` selesai NORMAL tanpa exception apa pun.

**Kesimpulan: ketahanan mekanisme edge case terbukti nyata** — item dengan seluruh domain ditolak tidak menyebabkan crash maupun perilaku tak terduga, murni hasil jujur "tidak ada view yang bisa ditemukan" (konsisten prinsip kejujuran keterbatasan `CLAUDE.md`).

### E04 — Bukti sambungan M2.3 (LOLOS)

`trace_id=54f6978bd875fc9552b72759d2a8d267`. Payload: `role_title="HR Staff"`, "Bagaimana hasil review kinerja Budi semester ini?" (PERSIS teks `evals/2.3-.../S01.json`). Decomposition `tunggal`, 1 atomic_intent, PERSIS sesuai prediksi. Domain `[hr]`, diizinkan penuh (HR Staff punya akses `hr`). `domain_gate.deteksi_constraint_semua` menghasilkan `constraint.terdeteksi_count=1` — **`cakupan_individu.terdeteksi=True`**, PERSIS direplikasi dari hasil M2.3 asli (S01: role Staff tier + domain relevan `hr` + pertanyaan menyebut nama individu "Budi" + kategori performa → kedua pre-filter deterministik lolos, kedua langkah LLM (deteksi+verifikasi) dipanggil, terdeteksi). `domain_diizinkan=[hr]` tetap diteruskan ke Retriever apa adanya (constraint TIDAK menahan pemanggilan Retriever, sesuai Keputusan 8) → `view_name_final=v_hr_employee_performance_semester`.

**Kesimpulan: sambungan M2.3 (Deteksi Cakupan Individu, gap yang ditutup M7.11 di luar Lingkup aslinya) TERBUKTI BEKERJA NYATA** — `deteksi_constraint_semua()` menerima input dari rantai M2.1→M2.2 sungguhan dan menghasilkan `terdeteksi=True` yang benar, direkam di `KeadaanTurn.cakupan_individu`, siap dikonsumsi M7.13 (Verification Gate) nanti tanpa gap wiring tersisa.

## Temuan Metodologi

**Non-determinisme Decomposition berulang (E01, E02)**: kedua kejadian sama-sama diklasifikasikan `klasifikasi=tunggal` oleh langkah Klasifikasi Decomposition, TAPI langkah Pemecahan tetap menghasilkan 3 atomic_intents terpisah alih-alih 1 — pola INTERNAL yang tidak konsisten (label `tunggal` secara intuitif menyiratkan 1 atomic intent, tapi bukan itu yang direalisasikan). Ini BUKAN temuan baru M7.11 — konsisten `docs/keterbatasan-diterima.md` #3 (non-determinisme `temperature=0`) dan pola berulang M7.9/M7.10 — logic internal Decomposition (M1.6) di luar cakupan revisi M7.11 (`rancangan-orkestrasi-api.md`: "Tidak termasuk: Logic internal kesembilan layer"). Tidak di-retry untuk memaksa hasil `rancangan.md` — hasil aktual (3 atomic intent per kejadian) justru memperkuat verdict zero-leakage (lebih banyak kesempatan independen untuk kebocoran domain terjadi, semuanya tetap bersih).

**Nilai tambah tak terduga**: E01's intent ke-2 (`[financial, properties_ref]`, BUKAN kombinasi gop_margin utama) menjadi bukti zero-leakage TAMBAHAN yang independen dari intent ke-3 (bukti KK literal utama) — total 3 kesempatan kebocoran diuji di E01 saja (bukan 1 seperti rencana awal), seluruhnya lolos.

**Verifikasi substantif via Python return value, bukan Jaeger span tags** — dicatat eksplisit sebagai keputusan metodologi (bukan penyimpangan): span `retriever.cari_kandidat_view` hanya merekam `retrieval.candidates_count` (angka), TIDAK merekam domain per-kandidat. Klaim "tidak ada kandidat dari domain ditolak" karena itu diverifikasi lewat inspeksi langsung `KecukupanKandidat.kandidat.domain` di `KeadaanTurn.retriever[i].kecukupan` (hasil asli `proses_turn()` real-execution, bukan mock) — Jaeger tetap dipakai untuk membuktikan span+atribut ringkasan (`intent.count`, `authorization.check` count, `retrieval.selected_view`) benar-benar ter-emit sesuai kontrak observability, peran keduanya saling melengkapi bukan saling menggantikan.
