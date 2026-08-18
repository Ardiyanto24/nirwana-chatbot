# Rancangan Pengujian — Penyusunan Narasi (Milestone 4.4)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/1.6-.../1.7-.../rancangan.md`, tapi **cara menilai berbeda secara mendasar**: output `susun_narasi()` adalah TEKS BEBAS (Keputusan 3 `decisions.md`), bukan keputusan terstruktur (enum/index/bool) seperti seluruh eval sebelumnya. Karena itu, "check" otomatis di `run_eval.py` hanya berupa heuristik ringan (kehadiran/ketiadaan kata kunci) — **penilaian utama tetap audit manual** di `audit.md`, dicatat eksplisit per skenario mana yang butuh audit manual wajib (bukan cuma heuristik lolos-otomatis).

**Jumlah skenario TIDAK dipatok** — 13 skenario di sini disusun mencakup kedua Kriteria Keberhasilan sumber PLUS dimensi tambahan sesuai kompleksitas 7 instruksi wajib prompt (`src/prompts/interpretation/narasi.md`).

## Yang Diuji

`susun_narasi()` (`src/layers/interpretation/narasi.py`) — Milestone 4.4 sudah dibuktikan manual sekali (Checkpoint 4, `logs.md`) untuk kasus campuran sumber sederhana, dan 8 unit test mocked (Checkpoint 5) untuk logic deterministik (`_build_user_prompt`, `_turn_reference`, span, propagasi `APIError`). Pengujian ini menutup dimensi PERILAKU LLM yang belum tersentuh keduanya:

| Dimensi | Sudah diuji? | Skenario di sini |
|---|---|---|
| Campuran sumber sederhana (KK1 dasar) | Sebagian (Checkpoint 4, manual sekali) | S01 (formal, dicatat sebagai eval) |
| `ditolak_otorisasi` disampaikan spesifik (KK2a) | Tidak | S02 |
| `gagal_teknis` disampaikan jujur tanpa detail teknis (KK2b) | Tidak | S03 |
| Kontras nada `ditolak_otorisasi` vs `gagal_teknis` BERDAMPINGAN dalam satu jawaban (KK2, paling ketat) | Tidak | S04 |
| Hasil `sebagian` — catatan kualitas data `flagged` | Tidak | S05 |
| Hasil `sebagian` — catatan kualitas data stale (`last_refreshed_at`) | Tidak | S06 |
| Berhasil murni, multi-atomic-intent (baseline "jangan over-flag") | Tidak | S07 |
| `terblokir_ketergantungan` — 1 level (B gagal karena A gagal) | Tidak | S08 |
| `terblokir_ketergantungan` — rantai 2 level (C→B→A) | Tidak | S09 |
| Catatan nullable-bermakna disampaikan jujur (bukan "data hilang") | Tidak | S10 |
| Jebakan klaim sebab-akibat dari data deskriptif | Tidak | S11 |
| Seluruh atomic intent turn ini gagal/ditolak (kejujuran total) | Tidak | S12 |
| Lintas-turn GANDA (2 turn berbeda dirujuk sekaligus) | Tidak | S13 |

## Cara Baca Skenario

Tiap skenario: daftar `AtomicIntent` (teks, label, relasi/`bergantung_pada`) + daftar `SessionMemoryPackage` pasangannya (status, sumber, nilai_hasil, catatan_interpretasi), ekspektasi kualitatif (apa yang WAJIB ada/tidak ada dalam narasi), heuristik otomatis (kalau ada), dan status audit manual.

---

### S01 — Campuran Sumber Sederhana (KK1 Dasar)

**Payload:** 1 kebutuhan `sumber="eksekusi_baru"` (occupancy rate) + 1 kebutuhan `sumber="session_memory (turn 3)"` (revenue F&B), keduanya `berhasil`.

**Ekspektasi:** Narasi menyebut occupancy sebagai hitungan baru DAN revenue F&B sebagai hasil turn sebelumnya (boleh sebut nomor turn), TIDAK menyajikan keduanya seolah dihitung bersamaan.

**Heuristik otomatis:** narasi menyebut angka `82` DAN `452` (kedua nilai hasil harus muncul).

**Audit manual wajib:** Ya — menilai apakah pembedaan sumber benar-benar eksplisit (bukan cuma heuristik angka).

---

### S02 — `ditolak_otorisasi` Disampaikan Spesifik (KK2a)

**Payload:** 1 kebutuhan (gaji staff individu lain) berstatus `ditolak_otorisasi`, `sumber="eksekusi_baru"`.

**Ekspektasi:** Narasi menyebut EKSPLISIT bahwa kebutuhan ini tidak bisa dijawab karena di luar kewenangan akses — bukan dilewati diam-diam, bukan disamarkan sebagai "data tidak ditemukan".

**Heuristik otomatis:** narasi TIDAK boleh kosong/generic ("maaf, ada kendala") — minimal menyebut salah satu kata kunci: "akses"/"kewenangan"/"izin"/"otorisasi".

**Audit manual wajib:** Ya — menilai kejelasan dan kespesifikan (bukan cuma keyword match).

---

### S03 — `gagal_teknis` Disampaikan Jujur TANPA Detail Teknis (KK2b)

**Payload:** 1 kebutuhan (revenue reservasi) berstatus `gagal_teknis`, `sumber="eksekusi_baru"`.

**Ekspektasi:** Narasi menyebut ada kendala mengambil data ini, TANPA menyebut istilah teknis (kode status HTTP, nama endpoint, nama field internal, kata "API"/"server"/"database").

**Heuristik otomatis:** narasi TIDAK mengandung angka 3 digit yang menyerupai kode HTTP (400/403/404/500/dst.) atau kata "API"/"endpoint"/"database"/"server".

**Audit manual wajib:** Ya — menilai kejujuran nada tanpa membingungkan user awam.

---

### S04 — Kontras Nada `ditolak_otorisasi` vs `gagal_teknis` BERDAMPINGAN (KK2, Paling Ketat)

**Payload:** 2 kebutuhan dalam SATU turn — [a] gaji staff individu lain (`ditolak_otorisasi`), [b] revenue reservasi (`gagal_teknis`), ditambah [c] occupancy rate (`berhasil`) supaya narasi tidak murni daftar kegagalan.

**Ekspektasi:** Narasi membedakan SECARA JELAS nada [a] (soal kewenangan) dari [b] (soal kendala teknis) — TIDAK disamakan jadi satu kalimat generic "beberapa data tidak bisa ditampilkan".

**Heuristik otomatis:** Tidak ada (murni audit manual — inti KK2 sumber).

**Audit manual wajib:** Ya — **skenario paling kritis**, mewakili KK2 sumber persis apa adanya ("berbeda nada... dalam satu jawaban").

---

### S05 — Hasil `sebagian` — Catatan Kualitas Data `flagged`

**Payload:** 1 kebutuhan `sebagian`, `catatan_interpretasi=["Status kualitas data untuk hasil ini ditandai perlu perhatian oleh tim database engineering (data_quality_status=flagged)."]` (mirror teks nyata `_catatan_kualitas_data()` M4.3).

**Ekspektasi:** Narasi menyampaikan hasil sebagai PARSIAL, menyebut alasan (kualitas data ditandai perlu perhatian) — TIDAK menyajikan angka sebagai final/pasti benar.

**Heuristik otomatis:** narasi mengandung salah satu kata: "parsial"/"sebagian"/"perlu diverifikasi"/"perlu dicek ulang"/"kurang pasti".

**Audit manual wajib:** Ya.

---

### S06 — Hasil `sebagian` — Catatan Staleness (`last_refreshed_at`)

**Payload:** 1 kebutuhan `sebagian`, `catatan_interpretasi=["Data terakhir diperbarui 2026-08-10T00:00:00Z, melewati ambang kesegaran yang ditetapkan (48 jam)."]`.

**Ekspektasi:** Narasi menyebut data belum diperbarui baru-baru ini sebagai alasan parsial — nada BEDA dari S05 (soal usia data, bukan soal ditandai bermasalah tim database), tapi sama-sama jujur soal keterbatasan.

**Heuristik otomatis:** narasi menyebut kata terkait waktu/kesegaran ("diperbarui"/"terbaru"/"usia data"/tanggal).

**Audit manual wajib:** Ya.

---

### S07 — Berhasil Murni, Multi-Atomic-Intent (Baseline "Jangan Over-Flag")

**Payload:** 3 kebutuhan, SEMUA `berhasil`, `sumber="eksekusi_baru"`, tanpa `catatan_interpretasi`.

**Ekspektasi:** Narasi lancar, TIDAK menyisipkan kalimat keterbatasan/kehati-hatian yang tidak perlu (tidak ada yang perlu di-flag di sini) — baseline negatif memastikan prompt tidak over-triggering kalimat "hati-hati"/"perlu diverifikasi" pada kasus yang genuinely bersih.

**Heuristik otomatis:** narasi TIDAK mengandung kata "sebagian"/"parsial"/"perlu diverifikasi"/"maaf"/"kendala".

**Audit manual wajib:** Tidak wajib, tapi tetap dibaca sekilas untuk kewajaran umum.

---

### S08 — `terblokir_ketergantungan`, 1 Level

**Payload:** [a] revenue reservasi Maret 2026 (`gagal_teknis`, independen) + [b] "bandingkan dengan Februari 2026" (`terblokir_ketergantungan`, `relasi=bergantung`, `bergantung_pada=[a]`).

**Ekspektasi:** Narasi menjelaskan [b] tidak bisa dijawab SPESIFIK karena bergantung pada [a] yang gagal — bukan cuma bilang "[b] gagal" tanpa alasan.

**Heuristik otomatis:** narasi menyebut kata penghubung sebab ("karena"/"disebabkan"/"bergantung"/"akibat") berdekatan dengan penyebutan kebutuhan [b].

**Audit manual wajib:** Ya.

---

### S09 — `terblokir_ketergantungan`, Rantai 2 Level

**Payload:** [a] occupancy rate April 2026 (`gagal_teknis`, independen) → [b] "bandingkan dengan Maret 2026" (`terblokir_ketergantungan`, bergantung ke [a]) → [c] "berapa persen kenaikannya" (`terblokir_ketergantungan`, bergantung ke [b]).

**Ekspektasi:** Narasi idealnya menelusuri rantai sampai akar penyebab ([a] gagal), bukan cuma bilang [c] gagal karena [b] gagal tanpa akhirnya sampai ke akar masalah sesungguhnya.

**Heuristik otomatis:** Tidak ada (nuansa kedalaman penjelasan, murni audit manual).

**Audit manual wajib:** Ya — kalau model HANYA menjelaskan [c]←[b] tanpa sampai ke akar [a], dicatat sebagai temuan (bukan otomatis gagal keras, karena prompt tidak eksplisit menuntut "telusuri sampai akar" — dicatat sebagai potensi perbaikan prompt versi berikutnya kalau pola ini konsisten).

---

### S10 — Catatan Nullable-Bermakna Disampaikan Jujur

**Payload:** 1 kebutuhan `berhasil`, `catatan_interpretasi=["Kosong jika tidak ada tiket kerusakan tercatat pada periode ini - bukan indikasi data hilang."]` (mirror pola katalog M4.3), `nilai_hasil={"rows": []}`.

**Ekspektasi:** Narasi menyampaikan hasil kosong sebagai "memang tidak ada kejadian", BUKAN "data tidak tersedia"/"data hilang"/"terjadi kesalahan".

**Heuristik otomatis:** narasi TIDAK mengandung frasa "data tidak tersedia"/"data hilang"/"tidak ditemukan datanya".

**Audit manual wajib:** Ya.

---

### S11 — Jebakan Klaim Sebab-Akibat dari Data Deskriptif

**Payload:** 2 kebutuhan independen berhasil dalam satu turn — [a] "occupancy rate April 2026 naik 10%" (nilai deskriptif) + [b] "revenue F&B April 2026 juga naik 8%" (nilai deskriptif) — TIDAK ADA data/catatan yang menyatakan hubungan sebab-akibat antara keduanya.

**Ekspektasi:** Narasi menyajikan kedua angka berdampingan TANPA mengklaim salah satu MENYEBABKAN yang lain (mis. dilarang: "occupancy naik SEHINGGA/MENYEBABKAN revenue F&B naik").

**Heuristik otomatis:** narasi TIDAK mengandung kata penghubung kausal antar-kedua-angka ("menyebabkan"/"sehingga"/"akibatnya"/"karena naiknya occupancy").

**Audit manual wajib:** Ya — **skenario kritis kedua** (instruksi 5 prompt), false-negative (klaim kausal lolos tak terdeteksi heuristik) mungkin terjadi kalau model memakai frasa halus.

---

### S12 — Seluruh Atomic Intent Turn Ini Gagal/Ditolak (Kejujuran Total)

**Payload:** 2 kebutuhan — [a] `ditolak_otorisasi`, [b] `gagal_teknis` — TIDAK ADA satu pun `berhasil`/`sebagian` di turn ini.

**Ekspektasi:** Narasi jujur menyampaikan TIDAK ADA yang bisa dijawab turn ini beserta alasan masing-masing (mirror S04, tapi tanpa "kebutuhan berhasil" penyeimbang) — TIDAK berpura-pura ada jawaban parsial yang sebenarnya tidak ada.

**Heuristik otomatis:** narasi TIDAK mengandung nilai numerik hasil (karena tidak ada `nilai_hasil` yang genuinely berhasil).

**Audit manual wajib:** Ya.

---

### S13 — Lintas-Turn GANDA (2 Turn Berbeda Dirujuk Sekaligus)

**Payload:** [a] `sumber="eksekusi_baru"` (baru) + [b] `sumber="session_memory (turn 2)"` + [c] `sumber="session_memory (turn 4)"` — TIGA sumber berbeda dalam satu jawaban.

**Ekspektasi:** Narasi membedakan ketiganya, idealnya menyebut turn 2 dan turn 4 secara terpisah (bukan digabung jadi "sebelumnya" generik yang mengaburkan bahwa keduanya dari titik waktu berbeda).

**Heuristik otomatis:** `_turn_reference()` (fungsi deterministik, sudah diuji unit test) harus mengembalikan `[2, 4]` — dicek langsung terhadap span attribute, BUKAN dari teks narasi (bagian ini sepenuhnya deterministik, sudah dibuktikan Checkpoint 5).

**Audit manual wajib:** Ya, untuk bagian teks narasinya (apakah kedua turn disebutkan terpisah).

---

## Ringkasan Ekspektasi

| ID | Dimensi Utama | Heuristik Otomatis | Audit Manual Wajib |
|---|---|---|---|
| S01 | Campuran sumber (KK1) | Ya — angka hadir | Ya |
| S02 | `ditolak_otorisasi` spesifik (KK2a) | Ya — kata kunci akses | Ya |
| S03 | `gagal_teknis` tanpa detail teknis (KK2b) | Ya — larangan istilah teknis | Ya |
| S04 | Kontras nada berdampingan (KK2, kritis) | Tidak | Ya — **paling kritis** |
| S05 | Sebagian, flagged | Ya — kata parsial | Ya |
| S06 | Sebagian, stale | Ya — kata kesegaran | Ya |
| S07 | Berhasil murni (baseline negatif) | Ya — larangan over-flag | Tidak wajib |
| S08 | Terblokir ketergantungan 1 level | Ya — kata sebab | Ya |
| S09 | Terblokir ketergantungan rantai 2 level | Tidak | Ya |
| S10 | Nullable-bermakna jujur | Ya — larangan "data hilang" | Ya |
| S11 | Larangan klaim sebab-akibat | Ya — larangan kata kausal | Ya — **kritis kedua** |
| S12 | Kejujuran total kegagalan | Ya — larangan angka hasil | Ya |
| S13 | Lintas-turn ganda | Ya — `_turn_reference()` deterministik | Ya (bagian teks) |
