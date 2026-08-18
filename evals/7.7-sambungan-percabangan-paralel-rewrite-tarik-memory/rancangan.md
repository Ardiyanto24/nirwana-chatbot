# Rancangan Pengujian — Sambungan 2: Pemetaan Ketergantungan → Percabangan Paralel (Rewrite + Tarik Memory) (Milestone 7.7)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — kejadian dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada. Mengikuti struktur `evals/README.md`, mirror `evals/7.6-.../rancangan.md`: unit pengujian adalah **kejadian struktural**, bukan variasi bahasa. Tujuannya memastikan Rewrite dan Tarik Session Memory benar-benar berjalan paralel dan wiring kondisionalnya benar — bukan menilai kualitas jawaban LLM (itu tuntas di `evals/1.4-.../`).

## Yang Diuji

`proses_turn()` (`src/orchestration/turn_pipeline.py`) — bagian percabangan paralel yang ditambahkan Milestone 7.7: `rewrite_to_standalone()` (M1.4) dan `retrieve_session_memory()` (M1.5, kondisional).

## Peta Kejadian

| ID | Kejadian | Butuh LLM/DB? | Dibuktikan lewat |
|---|---|---|---|
| E01 | Turn dengan referensi terdeteksi — **skenario KK literal bagian 1**: kedua jalur berjalan bersamaan, dibuktikan span `parent_span_id` sama | Ya (LLM + DB nyata) | `run_eval.py` (skrip ini) + Jaeger |
| E02 | Turn tanpa referensi — **skenario KK literal bagian 2**: hanya jalur Rewrite, Tarik Memory sama sekali tidak terpanggil | Ya (LLM nyata, real end-to-end) | `run_eval.py` (skrip ini) + Jaeger |
| E03 | Payload gagal validasi Input Layer (short-circuit sebelum percabangan) | Tidak | `tests/orchestration/test_turn_pipeline.py` (sudah lolos, Checkpoint 4, warisan M7.6) |
| E04 | Kegagalan teknis satu cabang (Tarik Memory gagal DB) — exception menjalar, cabang lain tetap selesai | Tidak (mocked) | `tests/orchestration/test_turn_pipeline.py` (sudah lolos, Checkpoint 4) |

E03/E04 dipetakan di sini untuk kelengkapan peta kejadian milestone, tapi TIDAK dieksekusi ulang lewat `run_eval.py` — sudah dibuktikan deterministik, tidak butuh LLM/DB/Jaeger nyata (lihat `decisions.md` Keputusan 7 untuk rasional penempatan ini).

---

### E01 — Turn dengan referensi terdeteksi, kedua jalur paralel (KK literal)

**Tujuan:** membuktikan `rewrite_to_standalone()` dan `retrieve_session_memory()` BENAR-BENAR berjalan bersamaan (bukan berurutan seolah paralel), sesuai teks KK M7.7: "dibuktikan lewat span dengan `parent_span_id` yang sama, menunjukkan keduanya anak dari span yang sama, bukan berurutan".

**Payload:** `turn_index=2`, `history=[{turn_index=1, question="Berapa revenue reservasi bulan Maret 2026?", answer="Revenue reservasi Maret 2026 sebesar Rp 800 juta."}]`, `question`: "Bandingkan dengan bulan sebelumnya." (skenario dependency eksplisit sederhana — cukup untuk memicu `is_dependent=True`, bukan menguji ulang ketahanan model M1.3 terhadap kasus ambigu yang sudah tuntas di `evals/1.3-.../`).

**Ekspektasi:**
- `proses_turn()` mengalir penuh TANPA error, `KeadaanTurn.rewrite` dan `.session_memory` sama-sama terisi.
- `ketergantungan.is_dependent=True`, `referenced_turn_index=1` (mewarisi hasil Sambungan 1, sama seperti `evals/7.6-.../` E02).
- **Span `chat` (dari Rewrite) DAN span `memory.retrieve` (dari Tarik Memory) SAMA-SAMA `parentSpanID` = span `invoke_agent`** — dibuktikan lewat query Jaeger API nyata, bukan asumsi kode.

**Kriteria Keberhasilan:** kedua nilai (`is_dependent=True`, `referenced_turn_index=1`) TERCAPAI, DAN trace Jaeger menunjukkan `chat`+`memory.retrieve` genuinely anak `invoke_agent` yang sama — bukti span nyata literal sesuai KK M7.7.

---

### E02 — Turn tanpa referensi, hanya jalur Rewrite

**Tujuan:** buktikan Tarik Memory TIDAK terpanggil sama sekali (bukan terpanggil lalu menghasilkan kosong) — teks KK M7.7 literal bagian kedua. Test deterministik `tests/orchestration/` (M7.6, warisan) sudah membuktikan ini secara mocked; kejadian ini menambahkan bukti end-to-end nyata (LLM sungguhan untuk Rewrite, tanpa mock sama sekali) untuk melengkapi klaim "mengalir nyata" seperti preseden E01 M7.6.

**Payload:** `turn_index=1`, `history=[]`, `question`: "Berapa occupancy rate properti kita bulan Juni 2026?" (turn pertama, structurally tidak ada yang bisa dirujuk).

**Ekspektasi:**
- `proses_turn()` mengalir penuh TANPA error.
- `KeadaanTurn.rewrite` terisi (LLM nyata), `KeadaanTurn.session_memory=None`.
- Trace Jaeger HANYA menunjukkan span `chat` (dari Rewrite) di bawah `invoke_agent` — TIDAK ADA span `memory.retrieve` sama sekali dalam trace tersebut.

**Kriteria Keberhasilan:** `session_memory is None` DAN trace Jaeger genuinely tidak mengandung span `memory.retrieve` — bukan cuma field kosong di level Python, tapi juga tidak ada jejak pemanggilan sama sekali di observability.

---

## Ringkasan Ekspektasi

| ID | `rewrite` | `session_memory` | Span `memory.retrieve` ada? |
|---|---|---|---|
| E01 | Terisi | Terisi (list, kemungkinan 1 paket dari turn 1) | Ya, `parentSpanID`=`invoke_agent` sama dengan `chat` |
| E02 | Terisi | `None` | Tidak — tidak ada sama sekali dalam trace |
