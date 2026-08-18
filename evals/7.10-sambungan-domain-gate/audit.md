# Audit — Sambungan 5: Pencocokan (jalur "perlu eksekusi") → Domain Gate (Milestone 7.10)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) dijalankan lokal sepanjang eksekusi.

## Ringkasan

**3/3 kejadian membuktikan MEKANISME filter benar** (span `domain_gate.identifikasi_semua` selalu terbuka, `intent.count` selalu tepat sama dengan panjang `domain_gate` — jumlah `perlu_eksekusi` di `matches`) — TAPI **E02 dan E03 tidak mereproduksi JUMLAH atomic_intent yang diprediksi `rancangan.md`** karena non-determinisme Decomposition (LLM, `temperature=0`) sungguhan: kedua payload menghasilkan `majemuk_bergantung` (3 atomic_intent), bukan `tunggal` (1 atomic_intent) seperti diprediksi — meski E03 memakai payload IDENTIK persis dengan `evals/7.9-.../E03` yang sebelumnya menghasilkan `tunggal`. Dicatat transparan di "Temuan Metodologi", BUKAN disembunyikan atau di-retry berulang sampai dapat hasil yang "sesuai prediksi" (itu sendiri akan jadi bentuk bias metodologi).

| ID | Ekspektasi jumlah `matches`/`domain_gate` | Aktual jumlah `matches`/`domain_gate` | `intent.count` span | Verdict MEKANISME |
|---|---|---|---|---|
| E01 | 3 / 2 | 3 / 2 | 2 | ✅ **PERSIS sesuai prediksi — bukti KK literal utama** |
| E02 | 1 / 1 | 3 / 3 | 3 | ✅ Mekanisme benar (semua `perlu_eksekusi` diteruskan semua), jumlah meleset |
| E03 | 1 / 0 | 3 / 2 | 2 | ✅ Mekanisme benar (campuran, hanya `perlu_eksekusi` diteruskan), jumlah DAN komposisi meleset dari rencana — TAPI jadi bukti KK literal KEDUA yang independen |

## Analisis Per Kejadian

### E01 — Campuran dua status (LOLOS — bukti KK literal utama, PERSIS sesuai prediksi)

`trace_id=671d4cdd94d3a793eef9e611021f5893`. Seeding: occupancy April 2026, `status=berhasil`. Payload identik `evals/7.9-.../E06`. Decomposition `majemuk_bergantung`, 3 atomic_intents (April 2025, April 2026, perbandingan) — PERSIS sama seperti hasil M7.9 E06 (Decomposition konsisten untuk payload ini di kedua run).

Pencocokan: April 2026 → `selesai` (match ke seeding), April 2025 dan perbandingan → `perlu_eksekusi`. **`KeadaanTurn.domain_gate` berisi TEPAT 2 item** (April 2025, perbandingan) — entri `selesai` (April 2026) BENAR ditahan, tidak diteruskan. Span `domain_gate.identifikasi_semua` py atribut **`intent.count=2`**, cocok persis panjang `domain_gate`.

**Kesimpulan: Kriteria Keberhasilan literal Milestone 7.10 TERPENUHI PENUH** — turn dengan campuran status (1 `selesai` + 2 `perlu_eksekusi`) hanya meneruskan yang `perlu_eksekusi` ke Domain Gate, dibuktikan lewat atribut span `intent.count=2` (bukan 3) yang diquery langsung dari Jaeger API, bukan asumsi kode.

### E02 — Seluruh match `perlu_eksekusi` (LOLOS mekanisme, jumlah meleset dari rencana)

`trace_id=3bcc53bc5dfe55ac5e454e8bc61d033e`. Payload turn 1 tanpa histori, "Berapa occupancy rate properti kita bulan Juni 2026?" — `rancangan.md` memprediksi Decomposition `tunggal` (1 atomic_intent). Aktual: `majemuk_bergantung`, 3 atomic_intents ("jumlah properti terisi", "total properti", "tingkat keterisian" sebagai rasio keduanya) — LLM menafsirkan "occupancy rate" sebagai metrik TURUNAN yang perlu dipecah jadi komponen pembilang+penyebut, bukan nilai tunggal langsung.

**Verdict mekanisme tetap benar**: seluruh 3 `matches` berstatus `perlu_eksekusi` (turn pertama, tidak ada kandidat sama sekali) → **seluruh 3 diteruskan ke `domain_gate`** (bukan ditahan sebagian), `intent.count=3` cocok persis. Prinsip "semua `perlu_eksekusi` diteruskan tanpa ada yang ditahan" tetap terbukti — hanya JUMLAHnya yang beda dari prediksi (3, bukan 1).

### E03 — Semua match `selesai` — TIDAK tereproduksi seperti rencana, jadi bukti KK literal KEDUA

`trace_id=f4ec0e1c2473ce22beea254bd2ec5db1`. Payload IDENTIK PERSIS `evals/7.9-sambungan-pencocokan/payloads/E03.json` ("Berapa lagi occupancy April 2026 itu?", histori sama) — run M7.9 sebelumnya menghasilkan `klasifikasi=tunggal` (1 atomic_intent, match penuh). Run M7.10 ini (`session_id` beda, `eval-7.10-e03`) menghasilkan `majemuk_bergantung` (3 atomic_intents: "jumlah kamar terisi", "total kamar tersedia", "occupancy rate" sebagai rasio keduanya, `retry_count=1`) — **non-determinisme Decomposition nyata untuk teks pertanyaan yang PERSIS SAMA** lintas dua run terpisah.

Dari 3 atomic_intent: hanya "occupancy rate April 2026" (intent ketiga, `bergantung`) yang match ke seeding (`status=selesai`); 2 lainnya ("jumlah kamar terisi", "total kamar tersedia" — pecahan baru yang tidak ada datanya) → `perlu_eksekusi`. **`domain_gate` berisi TEPAT 2 item**, `intent.count=2`.

**Rencana awal E03 (semua `selesai`, `domain_gate=[]`) TIDAK tereproduksi** — TAPI kejadian aktual justru jadi bukti KK literal KEDUA yang independen (campuran status lain, komposisi berbeda dari E01: di sini 1 `selesai`+2 `perlu_eksekusi` dari intent yang berbeda topik, bukan reuse persis E01), memperkuat kredibilitas mekanisme filter alih-alih melemahkannya.

**Klaim "span tetap terbuka dengan `intent.count=0` saat `domain_gate=[]`" TIDAK dibuktikan lewat eksekusi nyata di milestone ini** — divalidasi lewat INSPEKSI KODE alih-alih (`src/layers/domain_gate/domain_gate.py`): span `domain_gate.identifikasi_semua` dibuka TANPA kondisi apa pun (`with tracer.start_as_current_span(...)` dipanggil selalu, SETELAH `perlu_eksekusi` dihitung tapi SEBELUM ada percabangan berdasar isinya) — tidak ada `if not perlu_eksekusi: return` dini seperti fast-path `match_atomic_intents()` (M1.7). Span+atribut `intent.count` karena itu STRUKTURAL tidak bergantung nilai count — perilaku `count=0` mengikuti jalur kode PERSIS SAMA dengan `count=2`/`count=3` yang sudah terbukti nyata di E01/E02/E03, hanya beda nilai yang di-set. Retry eksekusi tambahan untuk memaksa hasil `count=0` TIDAK dilakukan — mengejar hasil tertentu lewat retry berulang sampai "sesuai" adalah bentuk bias metodologi yang harus dihindari.

## Temuan Metodologi

**Non-determinisme Decomposition untuk payload IDENTIK lintas run** (E03 vs `evals/7.9-.../E03`) — data point baru yang memperkuat `docs/keterbatasan-diterima.md` #3 (recency bias/non-determinisme `temperature=0`, sebelumnya teramati M1.3/M1.4/M1.7). Pelajaran untuk milestone Sambungan berikutnya: **jumlah atomic_intent hasil Decomposition TIDAK BOLEH diasumsikan tetap/reproducible** bahkan untuk teks pertanyaan yang identik lintas run berbeda — `rancangan.md` sebaiknya menulis ekspektasi dalam bentuk INVARIAN MEKANISME (mis. "seluruh `perlu_eksekusi` diteruskan, `selesai` ditahan, `intent.count` = panjang `domain_gate`"), bukan jumlah atomic_intent absolut, kecuali skenario itu sudah diverifikasi stabil lintas beberapa run percobaan.

**Nilai tambah tak terduga**: E03 yang gagal mereproduksi rencana awalnya justru menghasilkan bukti KK literal KEDUA yang independen dari E01 (komposisi/topik atomic_intent berbeda total) — memperkuat generalisasi klaim "filter Domain Gate benar" melampaui satu skenario tunggal, tanpa direncanakan sebagai demikian sejak awal.
