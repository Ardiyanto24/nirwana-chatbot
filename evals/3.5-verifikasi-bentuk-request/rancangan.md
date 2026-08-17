# Rancangan Pengujian — Verifikasi Bentuk Request (Milestone 3.5)

Dokumen ini ditulis **sebelum** eksekusi `run_eval.py` — skenario dan ekspektasi ditetapkan dulu. Struktur mirror `evals/3.4-penyusunan-request/rancangan.md`. **Jumlah skenario TIDAK dipatok** — 5 skenario di sini disesuaikan cakupan kedua Kriteria Keberhasilan sumber (kepatuhan sumber, kecukupan semantik) plus satu replikasi temuan nyata M3.4.

## Yang Diuji

`verifikasi_bentuk_request_atomic_intent()` (`src/layers/query_engine/verifikasi_bentuk_request.py`) — sudah lolos 16 unit test (mocked LLM) di `tests/layers/query_engine/`, membuktikan MEKANISME (pre-check short-circuit, parsing, fallback gagal-teknis) bekerja benar terhadap respons LLM yang disimulasikan. Eval ini menguji sisi yang TIDAK bisa dibuktikan unit test: apakah model NYATA (DeepSeek V4 Pro `reasoning="high"`) benar-benar menilai kecukupan semantik `params` terhadap `label_bentuk_jawaban` secara akurat.

| Dimensi | Sudah diuji di `tests/`? | Skenario di sini |
|---|---|---|
| Pre-check short-circuit (LLM disimulasikan) | Ya | — |
| KK1: `view_name` sengaja tidak sesuai Retriever → ditangkap dan ditolak | Ya (mocked), belum LLM nyata (tidak relevan - pre-check tidak menyentuh LLM) | S01 |
| KK2: label `tren` dengan rentang tanggal dipersempit satu hari → ditangkap tidak cukup | Tidak (LLM nyata) | S02 |
| Request `tren` valid dengan rentang cukup panjang → lolos | Tidak (LLM nyata) | S03 |
| Request `nilai_tunggal` valid → lolos | Tidak (LLM nyata) | S04 |
| Replikasi temuan nyata S04 M3.4 (`occupancy_rate: "nilai_tunggal"`, nilai nonsensikal) → ditangkap | Tidak (LLM nyata) | S05 |

## Cara Baca Skenario

Tiap skenario: `AtomicIntent` dikonstruksi manual + `QueryEngineRequest` dikonstruksi manual (mensimulasikan hasil M3.4, sudah pasti bentuknya valid secara schema) + `view_name_tervalidasi_retriever` (mensimulasikan hasil M3.1-3.3), dijalankan lewat `verifikasi_bentuk_request_atomic_intent()` end-to-end.

---

### S01 — KK1: `view_name` Sengaja Tidak Sesuai Retriever

**Kebutuhan:** "Berapa okupansi Bali bulan lalu?" (bentuk jawaban: `nilai_tunggal`)

**Setup:** `request.view_name = "v_reservation_channel_daily"`, TAPI `view_name_tervalidasi_retriever = "v_reservation_room_type_daily"` (sengaja beda, mensimulasikan request yang salah menyebut view).

**Ekspektasi:** `lolos=False`, `alasan` menyebut ketidaksesuaian `view_name`. Pre-check deterministik seharusnya menangkap ini TANPA memanggil LLM sama sekali (dibuktikan lewat `gen_ai.usage.*` yang tidak ada di span, ATAU secara sederhana lewat kecepatan eksekusi — dicatat di `audit.md`, bukan fail-kondisi keras karena ini soal implementasi bukan soal hasil akhir).

**Toleransi:** Tidak ada untuk `lolos=False`.

---

### S02 — KK2: Label `tren` dengan Rentang Tanggal Dipersempit Satu Hari

**Kebutuhan:** "Bagaimana tren revenue outlet F&B tiga bulan terakhir?" (bentuk jawaban: `tren`), `view_name = v_fnb_outlet_daily`

**Setup:** `params = {"period_date_from": "2026-08-17", "period_date_to": "2026-08-17"}` (sengaja dipersempit satu hari, meski kebutuhan asli minta tren 3 bulan).

**Ekspektasi:** `lolos=False`, `alasan` menyebut rentang tanggal tidak cukup untuk membentuk tren.

**Toleransi:** Tidak ada untuk `lolos=False` — ini KK2 sumber persis.

---

### S03 — Request `tren` Valid, Rentang Cukup Panjang

**Kebutuhan:** Sama seperti S02, TAPI `params = {"period_date_from": "2026-05-17", "period_date_to": "2026-08-17"}` (rentang ~3 bulan, sesuai kebutuhan).

**Ekspektasi:** `lolos=True`.

**Toleransi:** Tidak ada.

---

### S04 — Request `nilai_tunggal` Valid

**Kebutuhan:** "Berapa okupansi Bali bulan lalu?" (bentuk jawaban: `nilai_tunggal`), `view_name = v_reservation_room_type_daily`, `params = {"property_id": "P01", "period_date_from": "2026-07-01", "period_date_to": "2026-07-31"}`.

**Ekspektasi:** `lolos=True`.

**Toleransi:** Tidak ada.

---

### S05 — Replikasi Temuan Nyata S04 M3.4: Nilai Parameter Nonsensikal

**Kebutuhan:** "Okupansi Nirwana Lombok Escape bulan ini" (bentuk jawaban: `nilai_tunggal`), `view_name = v_reservation_room_type_daily`, `params = {"property_name": "Nirwana Lombok Escape", "period_date_from": "2026-08-01", "period_date_to": "2026-08-31", "occupancy_rate": "nilai_tunggal"}` — payload PERSIS direplikasi dari `evals/3.4-penyusunan-request/payloads/S04.json` (nilai nonsensikal yang lolos filter nama M3.4, SENGAJA tidak diperbaiki M3.4 karena "mengonfirmasi kenapa Milestone 3.5 dirancang terpisah").

**Ekspektasi:** `lolos=False`, `alasan` menyebut `occupancy_rate` diisi nilai yang tidak masuk akal (bukan angka/persentase).

**Toleransi:** Tidak ada — ini pembuktian langsung nilai milestone ini terhadap temuan M3.4 yang sengaja dibiarkan.

---

## Ringkasan Ekspektasi

| ID | Fokus | Ekspektasi Utama | Toleransi |
|---|---|---|---|
| S01 | KK1: kepatuhan sumber | `lolos=False`, pre-check tanpa LLM | Tidak |
| S02 | KK2: rentang tren terlalu sempit | `lolos=False` | Tidak |
| S03 | Kontrol positif: tren valid | `lolos=True` | Tidak |
| S04 | Kontrol positif: nilai_tunggal valid | `lolos=True` | Tidak |
| S05 | Replikasi temuan M3.4: nilai nonsensikal | `lolos=False` | Tidak |
