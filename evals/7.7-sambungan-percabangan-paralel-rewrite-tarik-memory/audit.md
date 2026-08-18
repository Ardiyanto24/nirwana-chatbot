# Audit — Sambungan 2: Pemetaan Ketergantungan → Percabangan Paralel (Rewrite + Tarik Memory) (Milestone 7.7)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus, warisan sesi M7.6) dijalankan lokal sepanjang eksekusi.

## Ringkasan

**4/4 kejadian sesuai ekspektasi** (E01/E02 dieksekusi nyata lewat `run_eval.py`, E03/E04 dibuktikan sebelumnya lewat `tests/orchestration/test_turn_pipeline.py` Checkpoint 4 — dirujuk di sini untuk kelengkapan peta, bukan dieksekusi ulang).

| ID | Ekspektasi | Aktual | Verdict |
|---|---|---|---|
| E01 | `is_dependent=True`/`referenced_turn_index=1`, `chat`+`memory.retrieve` sama-sama `parentSpanID`=`invoke_agent` | Sesuai persis, `kedua_span_anak_dari_span_sama=true` | ✅ Lolos — **bukti KK literal M7.7** |
| E02 | `session_memory=None`, span `memory.retrieve` TIDAK ADA dalam trace | Sesuai persis | ✅ Lolos — **bukti KK literal M7.7 bagian 2** |
| E03 | `ValidationError` menjalar, tidak masuk percabangan | Terbukti `tests/orchestration/` Checkpoint 4 | ✅ Lolos (dirujuk, tidak dieksekusi ulang) |
| E04 | Kegagalan teknis satu cabang menjalar, cabang lain tetap selesai | Terbukti `tests/orchestration/` Checkpoint 4 | ✅ Lolos (dirujuk, tidak dieksekusi ulang) |

## Analisis Per Kejadian

### E01 — Referensi terdeteksi, kedua jalur paralel (LOLOS — bukti utama)

**Payload:** turn kedua, histori 1 entri (revenue reservasi Maret 2026), pertanyaan "Bandingkan dengan bulan sebelumnya."

**Aktual:**
- `ketergantungan = {is_dependent: true, referenced_turn_index: 1}` — mewarisi Sambungan 1 (M7.6) dengan benar.
- `rewrite.rewritten_question` terisi (LLM sungguhan, Qwen3-32B).
- `session_memory = []` — Tarik Memory DIPANGGIL (bukan `None`), genuinely tidak menemukan data tersimpan untuk `session_id="eval-7.7-e01"` (sesi baru, belum pernah ada penyimpanan) — konsisten ekspektasi "dipanggil, kosong" beda dari E02 "tidak dipanggil sama sekali".
- **Bukti span nyata** (`trace_id=1209dcff1ddf138a4a1118239a53dec6`, di-query langsung lewat Jaeger API, bukan asumsi kode — lihat `payloads/E01.json` field `span_structure_jaeger`):

  | spanID | operationName | parentSpanID |
  |---|---|---|
  | `5f88085f1577dcaf` | `invoke_agent` | *(null — root)* |
  | `0ff30bd557ac075a` | `input.validate` | `5f88085f1577dcaf` |
  | `0b06f8b3ce3a3983` | `chat` (Pemetaan Ketergantungan, M7.6) | `5f88085f1577dcaf` |
  | `a1f8ca3b65606d64` | `chat` (Rewrite, M7.7) | `5f88085f1577dcaf` |
  | `4cb147891fbf7920` | `memory.retrieve` (Tarik Memory, M7.7) | `5f88085f1577dcaf` |

  **KEDUA span baru M7.7** (`chat` dari Rewrite dan `memory.retrieve` dari Tarik Memory) **SAMA-SAMA anak langsung `invoke_agent`** — `parentSpanID` identik (`5f88085f1577dcaf`), dalam satu trace yang sama, dieksekusi lewat `ThreadPoolExecutor` sungguhan (bukan berurutan). Ini bukti konkret bahwa kedua jalur genuinely berjalan bersamaan sebagai anak dari span pembungkus yang sama, bukan salah satu jadi anak dari yang lain (yang akan menunjukkan eksekusi berurutan) — persis teks KK M7.7: *"dibuktikan lewat span dengan `parent_span_id` yang sama, menunjukkan keduanya anak dari span yang sama, bukan berurutan."*

**Kesimpulan:** **Kriteria Keberhasilan literal Milestone 7.7 bagian 1 TERPENUHI PENUH** — dari eksekusi nyata (LLM+DB sungguhan, propagasi context OTel manual ke thread worker, Jaeger live), bukan simulasi/mock/asumsi kode.

### E02 — Tanpa referensi, hanya jalur Rewrite (LOLOS — bukti utama)

**Payload:** turn pertama, tanpa histori, "Berapa occupancy rate properti kita bulan Juni 2026?"

**Aktual:**
- `ketergantungan = {is_dependent: false, referenced_turn_index: null}`.
- `rewrite.rewritten_question` terisi (LLM sungguhan).
- `session_memory = null` (Python `None`) — Tarik Memory TIDAK PERNAH dipanggil.
- Struktur span (`trace_id=be61c3ce528b50dc28a84561952e85da`): `invoke_agent` → `input.validate` + 2× `chat` (satu dari Pemetaan Ketergantungan M7.6, satu dari Rewrite M7.7 — keduanya SELALU jalan terlepas dari hasil dependency) — **TIDAK ADA span `memory.retrieve` sama sekali** dalam trace.

**Kesimpulan:** **Kriteria Keberhasilan literal Milestone 7.7 bagian 2 TERPENUHI PENUH** — pembuktian bukan cuma di level field Python (`session_memory=None`), tapi juga di level observability nyata (span `memory.retrieve` genuinely tidak pernah tercatat, konsisten dengan "tidak terpanggil sama sekali" — bukan "terpanggil lalu menghasilkan kosong", yang akan tetap memunculkan span `memory.retrieve` dengan `memory.packages_found=0`).

### E03 — Payload gagal validasi (LOLOS, dirujuk)

Dibuktikan `tests/orchestration/test_turn_pipeline.py::test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil` (warisan M7.6, tetap berlaku karena short-circuit terjadi SEBELUM percabangan paralel M7.7 dimulai).

### E04 — Kegagalan teknis satu cabang (LOLOS, dirujuk)

Dibuktikan `tests/orchestration/test_turn_pipeline.py::test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai` (Checkpoint 4) — Tarik Memory di-mock gagal, exception menjalar keluar `proses_turn()`, cabang Rewrite tetap terpanggil/selesai (membuktikan `ThreadPoolExecutor.__exit__`'s `shutdown(wait=True)` menunggu kedua thread sebelum exception benar-benar menjalar).

## Temuan Pola

Satu perbaikan teknis ditemukan DAN diperbaiki di tengah eksekusi Checkpoint 6 (dicatat detail di `logs.md`): query Jaeger API awal (`_query_jaeger_trace`, mirror persis pola `evals/7.6-.../run_eval.py`) berhenti retry begitu respons pertama tidak kosong, TANPA memeriksa apakah SELURUH span yang diharapkan sudah ter-index — ditemukan race nyata pada percobaan pertama E01 (`kedua_span_anak_dari_span_sama=False` karena `invoke_agent` sendiri belum terindeks Jaeger saat query pertama berhasil menemukan 3 dari 4 span). Diperbaiki dengan menambah parameter `span_wajib_ada` yang membuat retry menunggu SET LENGKAP span yang diharapkan, bukan cuma "ada data apa saja". Setelah perbaikan, percobaan kedua langsung sukses penuh. Dicatat sebagai temuan metodologi untuk milestone Sambungan berikutnya yang juga butuh bukti span multi-cabang: preseden `evals/7.6-.../` (2 span saja) tidak mengalami race ini kemungkinan karena jumlah span lebih sedikit/timing kebetulan lebih longgar — milestone dengan lebih banyak span paralel (seperti M7.7, 5 span) lebih rentan terhadap race indexing Jaeger, retry berbasis "set span lengkap" lebih robust dan sebaiknya jadi pola default ke depan.
