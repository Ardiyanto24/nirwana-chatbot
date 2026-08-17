# Rancangan Pengujian — Pemeriksaan Kecukupan Struktural (Milestone 3.3)

Dokumen ini ditulis **sebelum** eksekusi `run_eval.py` — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/3.2-kecocokan-makna/rancangan.md`. **Jumlah skenario TIDAK dipatok** — 6 skenario di sini disesuaikan cakupan ruang kegagalan mekanisme hybrid (jalur deterministik pasti, jalur fallback LLM, tie-break), bukan konvensi wajib.

## Yang Diuji

`proses_retrieval_atomic_intent()` (`src/layers/retriever/kecukupan_struktural.py`) — orkestrator PENUTUP tiga langkah Retriever (M3.1→M3.2→M3.3) yang benar-benar dijalankan end-to-end (BM25/embedding M3.1 nyata, dua panggilan LLM M3.2 nyata, rule table + fallback LLM M3.3 nyata) — bukan fungsi M3.3 saja berdiri sendiri. Milestone ini sudah lolos 36 unit test (mocked LLM) di `tests/layers/retriever/test_kecukupan_struktural.py`, membuktikan MEKANISME (rule table, fail-safe, tie-break, default aman) bekerja benar terhadap respons LLM yang disimulasikan. Eval ini menguji sisi yang TIDAK bisa dibuktikan unit test: apakah model NYATA (fallback LLM Qwen3-32B) benar-benar konservatif pada kasus ambigu sungguhan, dan apakah pipeline penuh M3.1-3.3 menghasilkan `view_name_final` yang benar terhadap skenario dari dokumen sumber.

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Rule table/fallback/tie-break (LLM disimulasikan) | Ya | — |
| KK1 sumber persis (tren + kandidat snapshot tanpa dimensi waktu berulang → tidak cukup) | Tidak (LLM nyata) | S01 |
| KK2 sumber persis (nilai_tunggal + grain sesuai → cukup) | Tidak (LLM nyata) | S02 |
| KK3 sumber (retrieval.selected_view konsisten dengan view_name_final yang benar-benar dipilih) | Sebagian (span diverifikasi Jaeger Checkpoint 11, konsistensi NILAI diverifikasi di sini) | S01-S06 (semua) |
| Jalur fallback LLM genuinely terpicu (grain row-level ambigu) | Tidak | S03 |
| Perbandingan/peringkat/komposisi dengan dimensi pembanding jelas → cukup | Tidak | S04 |
| Tie-break nyata (≥2 kandidat cukup, kedua sinyal M3.2+M3.1 dipakai) | Tidak (bergantung hasil M3.2 nyata, tidak bisa dikontrol penuh seperti unit test) | S05 |
| Tidak ada kandidat cukup sama sekali → view_name_final=None (kejujuran keterbatasan) | Tidak | S06 |

## Cara Baca Skenario

Tiap skenario: `AtomicIntent` dikonstruksi manual (teks kebutuhan + label bentuk jawaban) + domain diizinkan, dijalankan lewat `proses_retrieval_atomic_intent()` end-to-end (M3.1 nyata → M3.2 nyata → M3.3 nyata). Ekspektasi difokuskan pada `view_name_final` dan (bila relevan) `sumber_keputusan` kandidat kunci.

---

### S01 — KK1 Sumber Persis: Tren + Kandidat Snapshot Tanpa Dimensi Waktu Berulang

**Kebutuhan:** "Bagaimana tren turnover departemen Housekeeping di Bali 3 bulan terakhir?" (bentuk jawaban: `tren`), domain `hr`

**Ekspektasi:** Kandidat `v_hr_turnover_snapshot` (kalau muncul di hasil M3.1/M3.2) dinyatakan `cukup=False` oleh rule table deterministik (`punya_time_series=tidak`, teks Fungsi katalog eksplisit "tidak ada tren historis") — `sumber_keputusan=deterministik`, BUKAN dilempar ke fallback LLM.

**Toleransi:** Tidak ada untuk kandidat `v_hr_turnover_snapshot` spesifik — ini KK1 sumber persis (`rancangan-retrieval-query.md` Milestone 3.3). Kandidat lain (kalau M3.1/M3.2 menemukan yang lebih baik) boleh membuat `view_name_final` terisi view LAIN yang genuinely cukup — itu bukan kegagalan, cukup catat di `audit.md`.

---

### S02 — KK2 Sumber Persis: Nilai Tunggal + Grain Sesuai

**Kebutuhan:** "Berapa okupansi Suite di Bali bulan ini?" (bentuk jawaban: `nilai_tunggal`), domain `reservation`

**Ekspektasi:** `view_name_final = "v_reservation_room_type_daily"` — `nilai_tunggal` selalu `cukup` di rule table apa pun grain-nya, jadi begitu M3.2 melabeli kandidat ini `ditemukan`, otomatis jadi `view_name_final`.

**Toleransi:** Tidak ada — KK2 sumber persis, mirror skenario S02 `evals/3.2-.../rancangan.md`.

---

### S03 — Jalur Fallback LLM Genuinely Terpicu (Grain Row-Level Ambigu)

**Kebutuhan:** "Bagaimana tren booking di Bali 3 bulan terakhir?" (bentuk jawaban: `tren`), domain `reservation`

**Ekspektasi:** Kandidat `v_lookup_bookings` (row-level, "1 baris = 1 reservasi", `punya_time_series=tidak_pasti`) genuinely dilempar ke fallback LLM (`sumber_keputusan=llm`), model menjawab `cukup=False` mengikuti instruksi konservatif v2 (batasan sistem: tidak ada agregasi sisi klien, row-level bukan ringkasan siap pakai per periode).

**Toleransi:** Ya, terbatas — kalau model tetap menjawab `cukup=True` meski prompt v2 sudah diperbaiki, ini DICATAT sebagai temuan nyata (bukan fail keras otomatis, karena prompt sudah direvisi sekali berdasar bukti Checkpoint 7 dan masih ada ruang model salah pada kasus genuinely ambigu) — bukan diam-diam ditoleransi tanpa catatan.

---

### S04 — Perbandingan Antar Tipe Kamar (Dimensi Pembanding Jelas)

**Kebutuhan:** "Bandingkan performa revenue antar tipe kamar di Bali bulan ini" (bentuk jawaban: `perbandingan`), domain `reservation`

**Ekspektasi:** `view_name_final = "v_reservation_room_type_daily"` (`punya_dimensi_pembanding=ya`, breakdown per `room_type_name`) — deterministik, bukan lewat fallback LLM.

**Toleransi:** Tidak ada untuk kandidat fokus — sinyal `punya_dimensi_pembanding` sudah pasti (`ya`) di `grain_view.py`.

---

### S05 — Tie-Break Nyata (Dua Kandidat Sama-Sama Cukup)

**Kebutuhan:** "Tren revenue dan okupansi kamar di Bali 3 bulan terakhir" (bentuk jawaban: `tren`), domain `reservation`

**Ekspektasi:** M3.1 kemungkinan mengembalikan >1 kandidat dengan `punya_time_series=ya` (mis. `v_reservation_room_type_daily`, `v_reservation_property_daily`) — kalau M3.2 melabeli lebih dari satu `ditemukan`/`sebagian`, `view_name_final` WAJIB konsisten dengan aturan tie-break (label M3.2 dulu, lalu skor `KandidatView` tertinggi) - diverifikasi manual dari `kecukupan` penuh di payload, bukan cuma ditebak.

**Toleransi:** Ya, sebagian — hasil M3.2 (kandidat mana yang `ditemukan` vs `sebagian`) tidak bisa dikontrol penuh (bergantung penilaian LLM nyata); yang diverifikasi ketat adalah KONSISTENSI `view_name_final` TERHADAP aturan tie-break dari `kecukupan` yang benar-benar dihasilkan, bukan terhadap prediksi kandidat mana yang menang di depan.

---

### S06 — Tidak Ada Kandidat Cukup Sama Sekali (Kejujuran Keterbatasan)

**Kebutuhan:** "Tren nama dan region seluruh properti dari waktu ke waktu" (bentuk jawaban: `tren`), domain `properties_ref`

**Ekspektasi:** `view_name_final = None` — `v_properties_ref` (satu-satunya view domain ini) adalah tabel referensi murni tanpa dimensi waktu (`punya_time_series=tidak`), rule table deterministik menyatakan `tidak_cukup`, tidak ada kandidat lain di domain ini untuk dicoba.

**Toleransi:** Tidak ada — domain `properties_ref` cuma 1 view (`katalog-data-chatbot.md`), hasil harus deterministik `None` kalau M3.1 mengembalikan kandidat itu sebagai satu-satunya opsi.

---

## Ringkasan Ekspektasi

| ID | Kandidat Fokus | Ekspektasi `view_name_final`/kandidat | Toleransi |
|---|---|---|---|
| S01 | `v_hr_turnover_snapshot` | `cukup=False`, deterministik | Tidak (untuk kandidat ini) |
| S02 | `v_reservation_room_type_daily` | `view_name_final` = kandidat ini | Tidak — KK2 sumber |
| S03 | `v_lookup_bookings` | `cukup=False`, via fallback LLM | Ya — dicatat kalau model masih salah |
| S04 | `v_reservation_room_type_daily` | `view_name_final` = kandidat ini, deterministik | Tidak |
| S05 | (bergantung hasil M3.2 nyata) | `view_name_final` konsisten aturan tie-break | Ya — hasil M3.2 tidak dikontrol, aturan tie-break WAJIB benar |
| S06 | `v_properties_ref` | `view_name_final = None` | Tidak |
