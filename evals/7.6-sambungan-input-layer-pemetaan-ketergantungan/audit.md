# Audit — Sambungan 1: Input Layer → Pemetaan Ketergantungan Turn (Milestone 7.6)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-18), membandingkan hasil aktual terhadap ekspektasi yang sudah ditetapkan di `rancangan.md` sebelum eksekusi. Payload lengkap tiap kejadian ada di `payloads/<ID>.json`. Docker Compose (Jaeger+Collector+Prometheus) dijalankan lokal (`infra/observability/`) sepanjang eksekusi.

## Ringkasan

**4/4 kejadian sesuai ekspektasi** (E01/E02/E04 dieksekusi nyata lewat `run_eval.py`, E03 dibuktikan sebelumnya lewat `tests/orchestration/test_turn_pipeline.py` Checkpoint 3 — dirujuk di sini untuk kelengkapan peta, bukan dieksekusi ulang).

| ID | Ekspektasi | Aktual | Verdict |
|---|---|---|---|
| E01 | `proses_turn()` mengalir tanpa error | Mengalir tanpa error, `is_dependent=False` | ✅ Lolos |
| E02 | `is_dependent=True`, `referenced_turn_index=1`, bukti span nyata | `is_dependent=True`, `referenced_turn_index=1`, span terkonfirmasi lewat Jaeger API | ✅ Lolos — **bukti KK literal M7.6** |
| E03 | `ValidationError` menjalar, LLM tidak terpanggil | Terbukti `tests/orchestration/` Checkpoint 3 | ✅ Lolos (dirujuk, tidak dieksekusi ulang) |
| E04 | `APIError` menjalar tanpa ditangkap | `menjalar_tanpa_ditangkap=true` | ✅ Lolos (mendokumentasikan celah M1.3, bukan bug M7.6) |

## Analisis Per Kejadian

### E01 — Turn pertama, tanpa histori (LOLOS)

**Payload:** `turn_index=1`, `history=[]`, "Berapa occupancy rate properti kita bulan Juni 2026?"

**Aktual:** `proses_turn()` mengalir penuh tanpa error. `KeadaanTurn.ketergantungan = {is_dependent: false, referenced_turn_index: null}` — sesuai ekspektasi struktural (histori kosong, tidak ada yang bisa dirujuk). `trace_id=73ebea2fc98331410d5f5379d149d8e6` tercatat (lihat `payloads/E01.json`).

**Kesimpulan:** Cabang kode `_build_user_prompt()` "Tidak ada histori - ini turn pertama dalam sesi" (`turn_dependency.py`) teraktivasi dan mengalir benar lewat orkestrator baru, tanpa perlu diuji terisolasi seperti M1.3 asli.

### E02 — Turn kedua dengan histori, skenario KK literal M7.6 (LOLOS — bukti utama)

**Payload:** `turn_index=2`, histori 1 entri (revenue reservasi Maret 2026), pertanyaan "Bandingkan dengan bulan sebelumnya."

**Aktual:**
- `KeadaanTurn.ketergantungan = {is_dependent: true, referenced_turn_index: 1}` — histori benar-benar diterima dan diproses, tidak diabaikan.
- **Bukti span nyata** (`trace_id=7fd067cab445721fd302defa26329a39`, di-query langsung lewat Jaeger API `http://localhost:16686/api/traces/<trace_id>`, bukan asumsi dari kode — lihat `payloads/E02.json` field `span_structure_jaeger`):

  | spanID | operationName | parentSpanID |
  |---|---|---|
  | `291b010645607d11` | `invoke_agent` | *(null — root)* |
  | `aa7d5eed1978631c` | `input.validate` | `291b010645607d11` |
  | `083562ee523b8269` | `chat` | `291b010645607d11` |

  Span `input.validate` (Input Layer, M1.2) DAN span `chat` (Pemetaan Ketergantungan Turn, M1.3) SAMA-SAMA anak langsung dari `invoke_agent`, dalam satu trace yang sama — bukti konkret data mengalir dari satu fungsi ke fungsi lain secara nyata, persis teks KK M7.6: *"dibuktikan lewat span yang menunjukkan data mengalir dari satu fungsi ke fungsi lain secara nyata."*

**Kesimpulan:** **Kriteria Keberhasilan literal Milestone 7.6 TERPENUHI PENUH** — baik nilai (`is_dependent`/`referenced_turn_index`) maupun bukti span, keduanya dari eksekusi nyata (LLM sungguhan + Jaeger live), bukan simulasi/mock/asumsi kode.

### E03 — Payload gagal validasi Input Layer (LOLOS, dirujuk)

Dibuktikan sebelumnya di `tests/orchestration/test_turn_pipeline.py::test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil` (Checkpoint 3, murni deterministik, tidak menyentuh LLM). Tidak dieksekusi ulang di `run_eval.py` — kejadian ini tidak pernah mencapai LLM/span sama sekali, sepenuhnya cakupan `tests/`.

### E04 — Kegagalan teknis LLM saat Pemetaan Ketergantungan (LOLOS — temuan penting)

**Payload:** sama seperti E02 (lolos Input Layer), `_call_llm` di dalam `turn_dependency` module DIPAKSA raise `openai.APIError` (di-scope ketat lewat `unittest.mock.patch` context manager).

**Aktual:** `openai.APIError` menjalar KELUAR `proses_turn()` tanpa ditangkap di titik mana pun — `menjalar_tanpa_ditangkap=true` (lihat `payloads/E04.json`).

**Kesimpulan:** Perilaku ini SESUAI ekspektasi teknis (celah M1.3 yang ditemukan saat investigasi M7.6, dikonfirmasi mengalir apa adanya lewat orkestrator baru — bukan diperbaiki, forced "tidak dirombak ulang"). **Dicatat sebagai entri baru `docs/keterbatasan-diterima.md` #14** — kegagalan teknis LLM pada langkah ini akan crash pipeline turn (bukan graceful-degrade `GAGAL_TEKNIS` seperti layer lain), beda perlakuan yang perlu ditinjau ulang sebelum M7.17 menyambungkan endpoint publik.

## Temuan Pola

Berbeda dari `evals/1.3-pemetaan-ketergantungan-turn/audit.md` (yang menemukan pola kelemahan model pada kasus ambigu multi-kandidat, S07), audit ini tidak menemukan masalah kualitas LLM — fokusnya murni konektivitas struktural. Satu temuan signifikan: celah `try/except` M1.3 (E04) yang sebelumnya tidak terdokumentasi, sekarang tercatat resmi sebagai keterbatasan diterima dengan pemicu peninjauan ulang eksplisit sebelum M7.17.
