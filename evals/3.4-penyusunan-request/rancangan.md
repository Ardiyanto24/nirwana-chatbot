# Rancangan Pengujian — Penyusunan Request (Milestone 3.4)

Dokumen ini ditulis **sebelum** eksekusi `run_eval.py` — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/3.3-kecukupan-struktural/rancangan.md`. **Jumlah skenario TIDAK dipatok** — 7 skenario di sini disesuaikan cakupan kedua Kriteria Keberhasilan sumber (resolusi tanggal relatif, no-invented-params), bukan konvensi wajib.

## Yang Diuji

`susun_request_atomic_intent()` (`src/layers/query_engine/penyusunan_request.py`) — sudah lolos 35 unit test (mocked LLM) di `tests/layers/query_engine/`, membuktikan MEKANISME (filter defensif, derivasi domain, fallback gagal-teknis) bekerja benar terhadap respons LLM yang disimulasikan. Eval ini menguji sisi yang TIDAK bisa dibuktikan unit test: apakah model NYATA (Qwen3-32B) benar-benar meresolusi tanggal relatif dengan akurat dan menghormati whitelist parameter yang diberikan, terhadap `tanggal_referensi` TETAP (`2026-08-17`) supaya hasil bisa dinilai literal (bukan cuma "kelihatan masuk akal").

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Filter defensif/parsing/fallback (LLM disimulasikan) | Ya | — |
| KK1: "bulan lalu" → rentang tanggal konkret benar | Tidak (LLM nyata) | S01 |
| KK1: "tiga bulan terakhir" → jendela 3 bulan benar | Tidak (LLM nyata) | S02 |
| Filter kategorikal cocok nilai enumerasi persis | Tidak | S03 |
| Resolusi nama properti → `property_id` kode benar | Tidak | S04 |
| Kebutuhan minimal → tidak over-filling | Tidak | S05 |
| View tanpa kolom tanggal sama sekali → tidak ada param tanggal dikarang | Tidak | S06 |
| KK2: parameter masuk akal tapi TIDAK ada di whitelist → tersaring | Tidak (LLM nyata + filter defensif bersama-sama) | S07 |

## Cara Baca Skenario

Tiap skenario: `AtomicIntent` dikonstruksi manual (teks kebutuhan + label bentuk jawaban) + `view_name` (hasil M3.1-3.3 disimulasikan, sudah pasti benar), dijalankan lewat `susun_request_atomic_intent()` end-to-end dengan `tanggal_referensi=date(2026, 8, 17)` TETAP untuk seluruh skenario (reproduksibilitas penilaian tanggal).

---

### S01 — KK1: "Bulan Lalu"

**Kebutuhan:** "Berapa okupansi Bali bulan lalu?" (bentuk jawaban: `nilai_tunggal`), `view_name = v_reservation_room_type_daily`

**Ekspektasi:** `params` mengandung `property_id="P01"` (Bali = Nirwana Beach Resort Bali), `period_date_from="2026-07-01"`, `period_date_to="2026-07-31"` — "bulan lalu" dari 2026-08-17 adalah Juli 2026.

**Toleransi:** Tidak ada untuk rentang tanggal (KK1 sumber persis) — `property_id` boleh tidak terisi kalau model menganggap "Bali" ambigu (Bali cuma py 1 properti di data ini, tapi nama kota vs nama properti bisa beda tafsir), dicatat sebagai catatan bukan fail keras untuk bagian itu saja.

---

### S02 — KK1: "Tiga Bulan Terakhir"

**Kebutuhan:** "Bagaimana tren revenue outlet F&B tiga bulan terakhir?" (bentuk jawaban: `tren`), `view_name = v_fnb_outlet_daily`

**Ekspektasi:** `params` mengandung `period_date_from`/`period_date_to` yang membentuk jendela ~3 bulan berakhir di/dekat `2026-08-17` (mis. `2026-05-17` s.d. `2026-08-17`, ATAU interpretasi kalender bulan penuh Mei-Jul/Jun-Agu — keduanya diterima).

**Toleransi:** Ya, terbatas pada batas persis awal jendela (kalender bulan vs rolling 90 hari sama-sama valid tafsir "tiga bulan terakhir") — yang WAJIB benar adalah `period_date_to` mendekati tanggal referensi dan lebar jendela genuinely ~3 bulan (bukan 1 bulan atau 1 tahun).

---

### S03 — Filter Kategorikal Persis

**Kebutuhan:** "Bagaimana performa kanal Direct di Bali bulan Juni 2026?" (bentuk jawaban: `nilai_tunggal`), `view_name = v_reservation_channel_daily`

**Ekspektasi:** `params["channel_name"] == "Direct"` (persis kapitalisasi sesuai enumerasi katalog), `period_date_from="2026-06-01"`, `period_date_to="2026-06-30"`.

**Toleransi:** Tidak ada untuk `channel_name` (nilai enumerasi eksplisit di definisi view) dan rentang tanggal (bulan absolut disebutkan eksplisit, tidak ada ambiguitas relatif).

---

### S04 — Resolusi Nama Properti ke Kode

**Kebutuhan:** "Okupansi Nirwana Lombok Escape bulan ini" (bentuk jawaban: `nilai_tunggal`), `view_name = v_reservation_room_type_daily`

**Ekspektasi:** `params["property_id"] == "P05"` (Nirwana Lombok Escape, dari `properties.csv` nyata yang diberikan user), `period_date_from="2026-08-01"`, `period_date_to="2026-08-31"` ("bulan ini" dari 2026-08-17 adalah Agustus 2026).

**Toleransi:** Tidak ada untuk `property_id` (nama-ke-kode eksplisit di definisi view `v_reservation_room_type_daily`, meski kode itu sendiri tidak didaftar langsung di sana — model perlu tahu dari konteks umum properti Nirwana. Kalau model TIDAK bisa meresolusi nama properti ke kode P05, dicatat sebagai temuan nyata, bukan fail keras dari desain mekanisme — keterbatasan konteks yang diberikan, bukan bug filter).

---

### S05 — Kebutuhan Minimal, Tidak Over-Filling

**Kebutuhan:** "Ada berapa venue yang dimiliki Nirwana?" (bentuk jawaban: `nilai_tunggal`), `view_name = v_lookup_venues`

**Ekspektasi:** `params` kosong `{}` atau minimal — TIDAK ada filter properti/tanggal/tipe yang dikarang padahal kebutuhan tidak menyebutkannya sama sekali.

**Toleransi:** Tidak ada — anti over-filling adalah bagian eksplisit KK2 ("tidak ada parameter yang dikarang di luar yang tersedia" mencakup juga tidak mengarang FILTER yang tidak diminta, bukan cuma nama key).

---

### S06 — View Tanpa Kolom Tanggal Sama Sekali

**Kebutuhan:** "Bahan apa saja untuk membuat menu Nasi Goreng?" (bentuk jawaban: `nilai_tunggal`), `view_name = v_lookup_recipe_bom`

**Ekspektasi:** `params["item_name"] == "Nasi Goreng"`, TIDAK ada parameter tanggal apa pun (view ini genuinely tidak punya kolom tanggal di katalog — `PARAM_WHITELIST_VIEW` tidak menyediakan opsi tanggal untuk view ini sama sekali).

**Toleransi:** Tidak ada.

---

### S07 — KK2: Parameter Masuk Akal Tapi Tidak Ada di Whitelist

**Kebutuhan:** "Tampilkan properti Nirwana dengan rating bintang 5" (bentuk jawaban: `nilai_tunggal`), `view_name = v_properties_ref`

**Ekspektasi:** `params` TIDAK mengandung `star_rating` (kolom ini ADA di `properties.csv` mentah yang diberikan user, TAPI TIDAK ADA di definisi view `v_properties_ref` yang sesungguhnya di katalog — hanya `property_id`/`property_name`/`region`/`opening_date`) — baik karena model sendiri tidak menyebutkannya, ATAU karena `_saring_params_tidak_dikenal()` membuangnya kalau model tetap mencobanya.

**Toleransi:** Tidak ada untuk hasil akhir (`star_rating` TIDAK BOLEH ada di `request.params`) — tapi dicatat terpisah di `audit.md` APAKAH model sendiri yang menahan diri, atau filter defensif yang menyelamatkan (keduanya sah lolos KK2, tapi beda maknanya untuk kualitas prompt).

---

## Ringkasan Ekspektasi

| ID | Fokus | Ekspektasi Utama | Toleransi |
|---|---|---|---|
| S01 | Tanggal relatif "bulan lalu" | `period_date_from/to` = Juli 2026 | Tidak (tanggal) |
| S02 | Tanggal relatif "3 bulan terakhir" | Jendela ~3 bulan berakhir ~2026-08-17 | Ya (batas awal persis) |
| S03 | Filter kategorikal | `channel_name="Direct"` + bulan Juni persis | Tidak |
| S04 | Resolusi nama properti | `property_id="P05"` + bulan ini | Tidak (kalau gagal = temuan nyata) |
| S05 | Anti over-filling | `params={}` | Tidak |
| S06 | View tanpa tanggal | Tidak ada param tanggal dikarang | Tidak |
| S07 | Anti invented-param | `star_rating` tidak pernah lolos ke `request.params` | Tidak (hasil akhir) |
