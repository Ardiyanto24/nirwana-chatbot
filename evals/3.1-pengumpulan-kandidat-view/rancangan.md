# Rancangan Pengujian — Pengumpulan Kandidat View (Milestone 3.1)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Beda dari eval milestone LLM lain di proyek ini: eval M3.1 punya **dua tujuan sekaligus**, dipisah jadi dua bagian eksplisit — (A) validasi KK1/KK2 sumber lewat jalur hybrid penuh, dan (B) **perbandingan empiris 3 kandidat model embedding fallback** (Qwen3-Embedding-4B, Qwen3-Embedding-8B, `text-embedding-3-small`) — kebutuhan baru yang belum pernah ada di milestone manapun sebelumnya (lihat `milestones/3.1-pengumpulan-kandidat-view/decisions.md` Keputusan 2).

## Temuan Penting Sebelum Eksekusi (Analisis Lokal, Tanpa Panggilan API)

Sebelum menyusun skenario Bagian B, `cari_bm25()` (Checkpoint 5) diuji lokal (murni Python, tanpa biaya) terhadap kandidat query paraphrase. Ditemukan **celah desain nyata pada trigger fallback**: skenario B1 di bawah menunjukkan BM25 bisa GAGAL TOTAL menemukan `view_name` yang benar (target sama sekali tidak muncul di kandidat) TANPA memicu `perlu_fallback=True` — karena trigger saat ini (`BM25_SKOR_MINIMUM=0.0`, provisional sejak Checkpoint 5) hanya berbunyi kalau **seluruh** kandidat berskor nol, bukan kalau kandidat yang ditemukan **salah/tidak lengkap**. Ini artinya trigger saat ini tidak menangkap mode kegagalan yang justru paling relevan untuk KK1 sumber ("tidak terlewat karena pencarian terlalu sempit").

**Implikasi untuk desain eval ini:** skenario Bagian B memanggil `cari_embedding()` LANGSUNG (bukan lewat orkestrator `cari_kandidat_view()` yang belum dibangun — itu Checkpoint 10, dan lewat trigger produksi yang sudah terbukti buta terhadap kasus ini) — supaya kualitas 3 model embedding bisa dibandingkan independen dari bug trigger. Temuan trigger di atas dicatat sebagai bahan revisi Checkpoint 9, terpisah dari perbandingan model itu sendiri.

## Bagian A — Validasi KK1/KK2 Sumber (Jalur BM25, Sekali Jalan)

Sudah lolos sebagai unit test deterministik (`tests/layers/retriever/test_pencarian_bm25.py`, Checkpoint 5) — bagian ini mengulang sebagai bukti tambahan lewat `run_eval.py` (payload tersimpan), bukan klaim baru.

### A1 — KK1: Okupansi Bali Bulan Ini

**Kebutuhan:** "okupansi Bali bulan ini" · **Domain diizinkan:** `reservation`

**Ekspektasi:** `v_reservation_room_type_daily` ada di kandidat BM25, `perlu_fallback=False`.

### A2 — KK2: Zero-Leakage Domain Ditolak

**Kebutuhan:** "okupansi Bali bulan ini" (sama) · **Domain diizinkan:** `fnb` (RESERVATION sengaja tidak diizinkan)

**Ekspektasi:** Tidak ada kandidat berdomain `reservation` sama sekali, meski `v_reservation_room_type_daily` jelas paling relevan secara leksikal.

---

## Bagian B — Perbandingan 3 Model Embedding (Stress-Test Kegagalan BM25)

Tiap skenario dijalankan **BM25 dulu** (dokumentasi baseline, bukti kandidat yang ditemukan/tidak) lalu **`cari_embedding()` TIGA KALI** — satu run per model (`qwen/qwen3-embedding-4b`, `qwen/qwen3-embedding-8b`, `openai/text-embedding-3-small`). Dinilai terutama lewat **recall** (apakah `view_name` target ada di kandidat, di posisi berapa) — bukan presisi (presisi itu tugas M3.2/3.3) — plus catatan biaya/latensi.

| Kategori | Skenario |
|---|---|
| Sinonim non-literal (istilah "kanal"/"OTA"/"Direct" diganti total) | B1 |
| Bahasa sehari-hari vs istilah teknis ("bahan terbuang" -> "duit kebuang") | B2 |
| Typo/variasi ejaan ("okupansi" -> "okupasi") | B3 |
| Framing bisnis abstrak (hubungan sebab-akibat, bukan istilah domain) | B4 |
| Partial-stem/istilah umum lintas-view dalam 1 domain (uji presisi recall saat banyak view berbagi kosakata) | B5 |

---

### B1 — Sinonim Non-Literal: Kanal Booking (`reservation`)

**Kebutuhan:** "tamu-tamu ini pesannya lewat mana aja ya, langsung ke kita apa lewat aplikasi pihak ketiga"
**Domain diizinkan:** `reservation` · **Target:** `v_reservation_channel_daily`

**Baseline BM25 (lokal, dikonfirmasi sebelum eksekusi):** target **TIDAK MUNCUL** di kandidat (0 overlap leksikal berarti dengan "kanal booking", "Direct vs OTA"), `perlu_fallback` tetap `False` (5 kandidat lain ditemukan via kata umum) — **inilah temuan trigger di atas, bukti nyata bukan hipotetis**.

**Ekspektasi embedding:** target muncul di kandidat (idealnya top-3) untuk ketiga model — inilah skenario paling kritis membuktikan fallback genuinely berguna.

**Toleransi:** Tidak ada untuk "target harus muncul" — kalau ketiga model gagal juga, itu temuan signifikan (bukan mekanisme embedding yang gagal, tapi keterbatasan genuine kasus ini).

---

### B2 — Bahasa Sehari-Hari vs Istilah Teknis: Waste F&B (`fnb`)

**Kebutuhan:** "berapa duit yang kebuang percuma gara-gara bahan makanan gak kepake, dan kenapa bisa gitu"
**Domain diizinkan:** `fnb` · **Target:** `v_fnb_waste_daily`

**Baseline BM25 (lokal):** target ADA di kandidat tapi posisi ke-3 dari 3 (skor rendah, tenggelam oleh `v_lookup_fnb_inventory`/`v_lookup_recipe_bom` yang kebetulan berbagi kata "bahan").

**Ekspektasi embedding:** target naik ke posisi lebih tinggi (idealnya top-1/2) untuk ketiga model — recall sudah aman di BM25, ini menguji apakah embedding memperbaiki RANKING, bukan cuma recall biner.

**Toleransi:** Ya — kalau ranking tidak membaik, dicatat sebagai temuan (embedding tidak selalu superior di kasus recall-sudah-aman), bukan fail keras karena target tetap "ditemukan" bukan "hilang".

---

### B3 — Typo/Variasi Ejaan: Okupansi (`reservation`)

**Kebutuhan:** "okupasi hotel minggu ini gimana" (typo: "okupasi" bukan "okupansi")
**Domain diizinkan:** `reservation` · **Target:** `v_reservation_room_type_daily`

**Baseline BM25 (lokal):** `perlu_fallback=True` (SATU-SATUNYA skenario B yang benar-benar memicu trigger saat ini — 0 kandidat sama sekali, typo memutus exact-match token).

**Ekspektasi embedding:** target ditemukan (idealnya top-1) untuk ketiga model — kasus PALING SEDERHANA untuk fallback karena trigger produksi saat ini benar-benar akan memanggilnya.

**Toleransi:** Tidak ada — ini kasus yang trigger-nya sudah BEKERJA (beda dari B1), jadi kegagalan di sini murni soal kualitas model embedding itu sendiri.

---

### B4 — Framing Bisnis Abstrak: Diskon vs Margin (`reservation`)

**Kebutuhan:** "kenapa untung kita turun padahal harga kamar lagi didiskon gede-gedean"
**Domain diizinkan:** `reservation` · **Target:** `v_reservation_gop_impact_monthly`

**Baseline BM25 (lokal):** target ADA di kandidat, posisi ke-2 dari 4 (skor sedang, kata "harga" jadi sinyal parsial).

**Ekspektasi embedding:** target tetap teridentifikasi kuat (idealnya rank 1) untuk ketiga model — menguji pemahaman hubungan sebab-akibat bisnis ("diskon menekan margin"), bukan sekadar kata kunci "harga".

**Toleransi:** Ya untuk posisi persis (boleh rank 1-2), tidak ada toleransi untuk "target hilang total".

---

### B5 — Partial-Stem/Kosakata Umum Lintas-View: Turnover HR (`hr`)

**Kebutuhan:** "berapa banyak karyawan yang keluar atau berhenti kerja di tiap departemen"
**Domain diizinkan:** `hr` · **Target:** `v_hr_turnover_snapshot`

**Baseline BM25 (lokal):** target ADA di kandidat tapi posisi ke-7 dari 10 (SELURUH 10 view domain `hr` muncul sebagai kandidat via kata umum "karyawan"/"departemen" — filter BM25 nyaris tidak menyaring apa pun di skenario ini).

**Ekspektasi embedding:** target naik signifikan ke posisi atas (idealnya top-2) untuk ketiga model — kasus ekstrem "BM25 mengembalikan hampir seluruh domain tanpa presisi", menguji apakah embedding benar-benar menyaring makna vs BM25 yang cuma menyaring domain.

**Toleransi:** Ya untuk posisi persis, tidak ada untuk "tidak ada perbaikan sama sekali dibanding baseline BM25".

---

## Ringkasan Ekspektasi

| ID | Baseline BM25 (lokal) | Ekspektasi Embedding (3 model) | Toleransi |
|---|---|---|---|
| A1 (KK1) | target ada, `perlu_fallback=False` | — (BM25 saja) | Tidak |
| A2 (KK2) | zero-leakage domain | — (BM25 saja) | Tidak |
| B1 | target **hilang total**, trigger TIDAK aktif | target harus muncul (idealnya top-3) | Tidak — kasus paling kritis |
| B2 | target ada, rank 3/3 | ranking membaik | Ya, bukan fail keras |
| B3 | target hilang, trigger AKTIF | target harus muncul (idealnya top-1) | Tidak |
| B4 | target ada, rank 2/4 | tetap teridentifikasi kuat | Ya untuk rank persis |
| B5 | target ada, rank 7/10 (nyaris tidak tersaring) | naik signifikan (idealnya top-2) | Ya untuk rank persis |

## Metrik yang Dicatat per Model (di `audit.md`)

- Recall biner per skenario B1-B5 (target muncul/tidak).
- Posisi rank target (kalau muncul).
- Latensi panggilan (dari respons API nyata, `payloads/`).
- Estimasi biaya (dari token usage kalau tersedia di respons, atau ukuran korpus×harga per-model kalau tidak).
