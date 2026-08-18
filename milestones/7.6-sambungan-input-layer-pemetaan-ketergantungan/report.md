# Report — Milestone 7.6: Sambungan 1 (Input Layer → Pemetaan Ketergantungan Turn)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai penuh, dengan revisi metodologi signifikan di tengah perencanaan (plan awal ditolak user, dirancang ulang mengikuti struktur `evals/`).

Milestone 7.6 adalah milestone **Level 2 pertama** PIC 7 — jenis pekerjaan baru (menyambungkan layer BERBEDA, bukan LLM call di dalam satu layer seperti Level 1). Orkestrator baru `proses_turn()` (`src/orchestration/turn_pipeline.py`, package `src/orchestration/` baru) menyambungkan `validate_turn_payload()` (M1.2) ke `detect_turn_dependency()` (M1.3), membuka span `invoke_agent` untuk pertama kalinya di `src/` produksi. Dua keputusan arsitektural berdampak-luas (lokasi kode lintas-layer, bentuk state akumulator) dikonfirmasi user lewat `AskUserQuestion` sebelum implementasi. Pengujian mengikuti struktur `evals/` (`rancangan.md`→`run_eval.py`→`payloads/`→`audit.md`) dengan unit "kejadian struktural" (bukan variasi bahasa), dieksekusi nyata dengan LLM sungguhan + Jaeger live (`docker compose`) — bukti span dikutip langsung dari Jaeger API, bukan asumsi kode.

Satu temuan signifikan: `detect_turn_dependency()` (M1.3) ternyata TIDAK punya `try/except` sama sekali di sekitar pemanggilan LLM-nya — celah yang belum pernah terdokumentasi, dikonfirmasi nyata (kejadian E04) dan dicatat sebagai `docs/keterbatasan-diterima.md` #14.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Payload turn kedua dalam sesi (mengandung histori turn sebelumnya) yang lolos Input Layer menghasilkan pemanggilan Pemetaan Ketergantungan yang benar-benar menerima histori itu, dibuktikan lewat span yang menunjukkan data mengalir dari satu fungsi ke fungsi lain secara nyata." | Kejadian E02 (`evals/7.6-.../audit.md`) — `is_dependent=True`, `referenced_turn_index=1` (histori benar-benar diproses), DAN struktur span nyata dari Jaeger API: span `input.validate` dan `chat` sama-sama `parentSpanID` = span `invoke_agent` (`trace_id=7fd067cab445721fd302defa26329a39`), diquery langsung `http://localhost:16686/api/traces/<trace_id>`, bukan asumsi kode. | **Ya, penuh.** |

Tambahan di luar KK literal sumber (atas instruksi eksplisit user, peta kejadian struktural bukan variasi input): E01 turn pertama tanpa histori (lolos), E03 short-circuit validasi gagal (lolos, dibuktikan `tests/orchestration/`), E04 kegagalan teknis LLM menjalar tanpa ditangkap (lolos, sekaligus temuan keterbatasan diterima baru).

## Bagian 3 — Cara Kerja dan Arsitektur

`proses_turn(raw: dict) -> KeadaanTurn`: buka span `invoke_agent` (atribut `session.id`/`turn.index`), panggil `validate_turn_payload(raw)` — kalau exception, menjalar keluar `with` block tanpa `detect_turn_dependency()` pernah terpanggil (short-circuit alami Python, tanpa `if`/`try` eksplisit); kalau berhasil, panggil `detect_turn_dependency(payload)`, kembalikan `KeadaanTurn(payload=payload, ketergantungan=ketergantungan)`.

`KeadaanTurn` (`src/schemas/orchestration.py`) adalah skema akumulator yang akan tumbuh field-demi-field tiap milestone Sambungan berikutnya (M7.7-7.16) — bukan tuple yang terus membesar. `src/main.py` SENGAJA belum disambungkan ke `proses_turn()` — ditunda ke Milestone 7.17 ("Membangun Endpoint API").

Pengujian terbagi dua jalur sesuai kebutuhan: `tests/orchestration/test_turn_pipeline.py` (deterministik, mocked, regresi otomatis cepat — kejadian E03 + wiring identity) dan `evals/7.6-sambungan-input-layer-pemetaan-ketergantungan/` (LLM sungguhan + Jaeger live — kejadian E01/E02/E04, mengikuti struktur `evals/README.md`). Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

- **Revisi metodologi signifikan di tengah Plan Mode** (bukan penyimpangan checkpoint-vs-eksekusi — terjadi SEBELUM checkpoint final ditulis): draf plan pertama mengusulkan fixture pytest `InMemorySpanExporter` untuk bukti span, ditolak user secara eksplisit lewat `ExitPlanMode`, diarahkan meniru workflow `evals/` dengan unit "kejadian struktural". Plan ditulis ulang total sebelum diajukan kembali dan disetujui — lihat `decisions.md` Keputusan 5-6 untuk detail investigasi ulang (ditemukan preseden nyata M2.1 Checkpoint 8 yang lebih kuat dari teknik yang diusulkan sebelumnya).
- Seluruh 7 checkpoint setelah plan disetujui dikerjakan persis sesuai rencana, tanpa penyesuaian di tengah jalan.

## Bagian 5 — Keterbatasan dan Item Provisional

- **`detect_turn_dependency()` (M1.3) tanpa `try/except APIError`** — temuan baru milestone ini (bukan keputusan sengaja seperti M4.4). **Status: DIPERBAIKI (2026-08-18), langsung setelah temuan, atas instruksi eksplisit user** — perbaikan kode DAN dokumentasinya dilakukan di `milestones/1.3-pemetaan-ketergantungan-turn/` (decisions.md Keputusan 12, logs.md Addendum), bukan di sini, karena logic internal layer tetap tanggung jawab milestone pemiliknya, konsisten prinsip yang sama yang membuat M7.6 semula tidak menutup celah ini sendiri. `docs/keterbatasan-diterima.md` #14 sekarang berstatus DIPERBAIKI. Kejadian E04 (`payloads/E04.json`, `audit.md`) di folder ini TETAP TIDAK DIUBAH — catatan historis yang mencerminkan kondisi nyata saat milestone ini dijalankan, bukan dokumen hidup yang di-update mengikuti kode terkini.
- **`KeadaanTurn`/span `invoke_agent` didesain dengan informasi tidak lengkap** (baru 2 dari 9 layer) — field dijaga minimal sesuai `decisions.md` Keputusan 2, tiap milestone Sambungan berikutnya adalah otoritas penuh untuk field tambahannya sendiri.

## Bagian 6 — Follow-up

- **1/11 Sambungan Level 2 selesai, 10 tersisa** — M7.7 ("Sambungan 2: Pemetaan Ketergantungan → Percabangan Paralel Rewrite + Tarik Memory") adalah milestone berikutnya, WAJIB berurutan (tidak boleh dikerjakan sebelum M7.6 tuntas — sudah terpenuhi).
- Fixture/infrastruktur test span (`InMemorySpanExporter`) yang sempat diusulkan draf plan pertama TIDAK dipakai — kalau milestone Sambungan berikutnya butuh verifikasi span tanpa Docker (mis. CI tanpa akses Docker), pertimbangkan ulang sebagai opsi tambahan (bukan pengganti) live Jaeger — belum genuinely dibutuhkan sekarang, dicatat sebagai catatan bukan keputusan tertunda resmi.
- `_revisi_request()` (M4.2, follow-up M7.4) dan potensi konsolidasi lain lintas PIC 7 tetap belum dikerjakan — tidak terkait M7.6.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
