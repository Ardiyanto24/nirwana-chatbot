# Rancangan Pengujian — Sambungan 1: Input Layer → Pemetaan Ketergantungan Turn (Milestone 7.6)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — kejadian dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada, bukan kriteria yang disesuaikan setelah lihat hasil. Mengikuti struktur `evals/README.md`, TAPI beda dari `evals/1.3-pemetaan-ketergantungan-turn/` (yang menguji variasi bahasa pertanyaan untuk memilih model/prompt terbaik): dokumen ini memetakan **kejadian struktural** yang bisa terjadi di boundary `proses_turn()` — bukan variasi isi pertanyaan user. Tujuannya memastikan layer saling terhubung dengan benar, bukan menilai kualitas jawaban LLM (itu sudah tuntas di `evals/1.3-.../`).

## Yang Diuji

`proses_turn()` (`src/orchestration/turn_pipeline.py`) — orkestrator lintas-layer pertama project, menyambungkan `validate_turn_payload()` (M1.2) ke `detect_turn_dependency()` (M1.3).

## Peta Kejadian

| ID | Kejadian | Butuh LLM? | Dibuktikan lewat |
|---|---|---|---|
| E01 | Payload valid, turn pertama (tanpa histori) | Ya (nyata) | `run_eval.py` (skrip ini) |
| E02 | Payload valid, turn kedua+ dengan histori — **skenario KK literal M7.6** | Ya (nyata) | `run_eval.py` + Jaeger (span nesting) |
| E03 | Payload gagal validasi Input Layer | Tidak | `tests/orchestration/test_turn_pipeline.py` (sudah lolos, Checkpoint 3) |
| E04 | Kegagalan teknis LLM (`openai.APIError`) saat Pemetaan Ketergantungan | Dipaksa (mock) | `run_eval.py` (skrip ini) |

E03 dipetakan di sini untuk kelengkapan peta kejadian (supaya seluruh kejadian struktural yang mungkin terjadi di boundary ini tercatat di satu tempat), tapi TIDAK dieksekusi ulang lewat `run_eval.py` — buktinya sudah ada di `tests/orchestration/test_turn_pipeline.py::test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil`, murni deterministik, tidak menyentuh LLM sama sekali.

---

### E01 — Payload valid, turn pertama (tanpa histori)

**Tujuan:** buktikan cabang kode `_build_user_prompt()` "Tidak ada histori - ini turn pertama dalam sesi" (di `turn_dependency.py`) teraktivasi dengan benar lewat `proses_turn()`, bukan cuma diuji terisolasi seperti M1.3 asli.

**Payload:** `turn_index=1`, `history=[]`, `question`: "Berapa occupancy rate properti kita bulan Juni 2026?"

**Ekspektasi:**
- `proses_turn()` mengalir penuh TANPA error.
- `KeadaanTurn.payload` sama persis payload yang divalidasi.
- `KeadaanTurn.ketergantungan.is_dependent` — tidak ada toleransi ketat pada NILAI (histori kosong secara struktural memang tidak ada yang bisa dirujuk, jadi `False` diharapkan, tapi ini bukan fokus pengujian ini — fokusnya kejadian mengalir tanpa error, bukan menilai ulang kualitas LLM M1.3).

**Kriteria Keberhasilan:** `proses_turn()` tidak melempar exception apa pun, `KeadaanTurn` valid terbentuk.

---

### E02 — Payload valid, turn kedua dengan histori (skenario KK literal M7.6)

**Tujuan:** ini SATU-SATUNYA kejadian yang literal disebut Kriteria Keberhasilan sumber M7.6: "Payload turn kedua dalam sesi (mengandung histori turn sebelumnya) yang lolos Input Layer menghasilkan pemanggilan Pemetaan Ketergantungan yang benar-benar menerima histori itu, dibuktikan lewat span yang menunjukkan data mengalir dari satu fungsi ke fungsi lain secara nyata."

**Payload:** `turn_index=2`, `history=[{turn_index=1, question="Berapa revenue reservasi bulan Maret 2026?", answer="Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Bandingkan dengan bulan sebelumnya." *(skenario dependency eksplisit sederhana — cukup untuk membuktikan wiring, bukan menguji ulang ketahanan model M1.3 terhadap kasus ambigu/implisit yang sudah tuntas di `evals/1.3-.../`)*

**Ekspektasi:**
- `proses_turn()` mengalir penuh TANPA error.
- `KeadaanTurn.ketergantungan.is_dependent=True`, `referenced_turn_index=1` (histori benar-benar diterima dan diproses, bukan diabaikan).
- **Span `invoke_agent` terbuka, membungkus span `input.validate` DAN span `chat` (dari `detect_turn_dependency`) — keduanya harus berada dalam trace yang sama, dibuktikan lewat query Jaeger API nyata (bukan asumsi dari kode).**

**Kriteria Keberhasilan:** `is_dependent=True` dan `referenced_turn_index=1` TERCAPAI, DAN trace Jaeger menunjukkan span `chat` genuinely anak dari (atau minimal satu trace dengan) `invoke_agent` — bukti span nyata sesuai teks KK literal.

---

### E03 — Payload gagal validasi Input Layer

**Tujuan:** buktikan `proses_turn()` short-circuit sebelum `detect_turn_dependency()` pernah terpanggil — Pemetaan Ketergantungan tidak boleh menerima payload yang belum lolos Input Layer.

**Payload:** `turn_index=2`, `history=[]` (kosong, padahal `turn_index=2` mensyaratkan tepat 1 entri histori — melanggar `TurnPayload.history_matches_turn_index()`).

**Ekspektasi:** `pydantic.ValidationError` menjalar keluar `proses_turn()`; `detect_turn_dependency()` TIDAK PERNAH terpanggil.

**Kriteria Keberhasilan:** sudah TERPENUHI — dibuktikan `tests/orchestration/test_turn_pipeline.py::test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil` (Checkpoint 3, lolos). Tidak dieksekusi ulang di `run_eval.py` ini karena tidak menyentuh LLM/span sama sekali — sepenuhnya cakupan `tests/`.

---

### E04 — Kegagalan teknis LLM saat Pemetaan Ketergantungan

**Tujuan:** `detect_turn_dependency()` (M1.3) ditemukan TIDAK punya `try/except` sama sekali di sekitar pemanggilan LLM-nya (beda dari semua layer LLM lain project) — kejadian ini mendokumentasikan perilaku NYATA celah tersebut mengalir lewat `proses_turn()`, BUKAN memperbaikinya (di luar Lingkup M7.6, forced "tidak dirombak ulang").

**Payload:** sama seperti E02 (`turn_index=2`, ada histori) — validasi Input Layer lolos, tapi `_call_llm` di dalam `turn_dependency` module DIPAKSA (mock, di-scope ketat pakai `unittest.mock.patch` sebagai context manager) melempar `openai.APIError` saat dipanggil.

**Ekspektasi:** `openai.APIError` menjalar KELUAR `proses_turn()` tanpa ditangkap di titik mana pun (tidak ada `try/except` baru ditambahkan orkestrator).

**Kriteria Keberhasilan:** `pytest.raises(APIError)` (atau setara) terbukti membungkus pemanggilan `proses_turn()` di skrip eksekusi — perilaku ini kemudian dicatat sebagai entri baru `docs/keterbatasan-diterima.md` (Checkpoint 6), bukan diperbaiki di sini.

---

## Ringkasan Ekspektasi

| ID | `is_dependent` | `referenced_turn_index` | Exception? | Bukti span wajib? |
|---|---|---|---|---|
| E01 | (tidak difokuskan, kejadian bukan nilai) | — | Tidak | Tidak |
| E02 | `True` | `1` | Tidak | **Ya — trace_id dicatat** |
| E03 | — | — | `ValidationError` | Tidak |
| E04 | — | — | `openai.APIError` | Tidak |
