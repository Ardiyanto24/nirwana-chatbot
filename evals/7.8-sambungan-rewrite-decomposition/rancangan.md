# Rancangan Pengujian — Sambungan 3: Rewrite → Decomposition (Milestone 7.8)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — kejadian dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada. Struktur mirror `evals/7.6-.../` dan `evals/7.7-.../`, dengan penyesuaian format ekspektasi: KK M7.8 murni soal KONTEN (bukan struktur span seperti M7.6/M7.7), jadi verdict utama tiap kejadian berbasis `required_phrases`/`forbidden_phrases` (format `evals/1.4-rewrite-mandiri/rancangan.md`), bukan `parent_span_id` matching. Bukti span tetap dicatat sebagai konfirmasi sekunder (lihat `decisions.md` Keputusan 1).

## Yang Diuji

`proses_turn()` (`src/orchestration/turn_pipeline.py`) — khusus segmen baru M7.8: `decompose_question(rewrite_result.rewritten_question)` dipanggil sekuensial setelah blok `ThreadPoolExecutor` (M7.7) selesai. Kejadian di sini menjalankan pipeline PENUH dari payload mentah (bukan memanggil `decompose_question()` langsung dengan teks buatan) — supaya benar-benar membuktikan hasil Rewrite SUNGGUHAN (bukan teks yang disiapkan manual menyerupai output Rewrite) yang mengalir ke Decomposition.

## Kejadian

### E01 — Kasus elipsis/koreferensi (bukti KK literal utama)

**Tujuan:** Membuktikan literal KK M7.8: kalimat hasil Rewrite dari kasus elipsis/koreferensi mengalir ke Decomposition dan menghasilkan pemecahan atomik yang konsisten dengan makna kalimat MANDIRI itu, bukan makna kalimat ASLI sebelum di-rewrite.

**Payload** (reuse persis `test_kelompok_a_elipsis_diresolusi_jadi_eksplisit`, M1.4 — `tests/layers/context_resolution/test_rewrite.py`):
```json
{
  "session_id": "eval-7.8-e01",
  "turn_index": 2,
  "role_title": "General Manager",
  "employee_id": "emp-eval",
  "question": "Bandingkan dengan occupancy satu tahun sebelumnya.",
  "history": [
    {"turn_index": 1, "question": "Berapa occupancy rate bulan April 2026?", "answer": "Occupancy April 2026 mencapai 78%."}
  ]
}
```

**Ekspektasi Rewrite:** `rewrite.rewritten_question` menyebut "april" dan "2025" eksplisit (resolusi "satu tahun sebelumnya" dari April 2026) — sesuai KK M1.4 asli.

**Ekspektasi Decomposition (bukti KK M7.8 literal):** Gabungan `teks_kebutuhan` seluruh `decomposition.atomic_intents`:
- `required_phrases=["april", "2025"]` — WAJIB, tidak ditoleransi. Kalau tidak muncul, berarti Decomposition TIDAK menerima kalimat mandiri hasil Rewrite (mengulang kegagalan resolusi, bukan bukti connectivity).
- `forbidden_phrases=["satu tahun sebelumnya", "2026"]` — WAJIB tidak ditoleransi. Kalau "2026" muncul, ini sinyal KUAT Decomposition menerima `payload.question`/histori mentah (April 2026) alih-alih hasil Rewrite yang sudah diresolusi ke April 2025 — persis pelanggaran KK M7.8 ("bukan makna kalimat asli sebelum di-rewrite").

**Konfirmasi sekunder (bukan syarat kelulusan):** span `chat` dari 3 sub-langkah Decomposition (klasifikasi, pemecahan, verifikasi) muncul sebagai anak `invoke_agent` di Jaeger, mengikuti span `chat` Rewrite dan span `chat` Pemetaan Ketergantungan yang sudah ada dari M7.6/M7.7.

---

### E02 — Kasus sudah mandiri (baseline kontras)

**Tujuan:** Membuktikan jalur pass-through tetap benar saat tidak ada elipsis untuk diresolusi — kontras terhadap E01, memastikan verdict E01 bukan kebetulan (mis. Decomposition selalu "benar" terlepas dari isi Rewrite).

**Payload** (reuse persis `test_kelompok_b_sudah_mandiri_diteruskan_tanpa_distorsi`, M1.4):
```json
{
  "session_id": "eval-7.8-e02",
  "turn_index": 1,
  "role_title": "Corporate Revenue Director",
  "employee_id": "emp-eval",
  "question": "Berapa revenue reservasi bulan Maret 2026?",
  "history": []
}
```

**Ekspektasi Rewrite:** `rewrite.rewritten_question` tetap soal revenue reservasi Maret 2026, tanpa distorsi (turn pertama, tanpa histori — tidak ada yang perlu diresolusi).

**Ekspektasi Decomposition:**
- `required_phrases=["reservasi", "maret", "2026"]` — WAJIB.
- `klasifikasi` diharapkan `tunggal` (satu kebutuhan sederhana, tidak majemuk) — dicatat di audit, tidak jadi syarat gagal-keras kalau model menilai berbeda (klasifikasi adalah penilaian LLM, bukan aturan deterministik tertutup).

**Konfirmasi sekunder:** span `chat` Decomposition tetap anak `invoke_agent`, konsisten dengan E01.

## Ringkasan Ekspektasi

| ID | `required_phrases` | `forbidden_phrases` |
|---|---|---|
| E01 | april, 2025 | satu tahun sebelumnya, 2026 |
| E02 | reservasi, maret, 2026 | — |
