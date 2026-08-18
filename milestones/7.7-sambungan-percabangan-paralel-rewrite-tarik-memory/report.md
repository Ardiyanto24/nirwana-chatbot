# Report — Milestone 7.7: Sambungan 2 (Pemetaan Ketergantungan → Percabangan Paralel: Rewrite + Tarik Memory)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai penuh. Mekanisme konkurensi PERTAMA di seluruh codebase berhasil diimplementasikan dan dibuktikan nyata.

Milestone 7.7 (Sambungan 2 Level 2 PIC 7) menyambungkan hasil Pemetaan Ketergantungan Turn (M7.6) ke dua percabangan paralel: Rewrite (M1.4, selalu jalan) dan Tarik Session Memory (M1.5, hanya jalan kalau ada referensi terdeteksi). `proses_turn()` sekarang menjalankan keduanya BENAR-BENAR bersamaan lewat `concurrent.futures.ThreadPoolExecutor` — pilihan yang dikonfirmasi user lewat `AskUserQuestion` setelah penjelasan detail trade-off vs `asyncio.gather`/`asyncio.to_thread` (mekanisme dasar identik, `ThreadPoolExecutor` tidak memaksa `proses_turn()` dan milestone Sambungan berikutnya berubah bentuk jadi async). Context span OpenTelemetry dipropagasi manual ke thread worker (`opentelemetry.context.attach()`/`detach()`) — teknik yang diverifikasi nyata terhadap Jaeger live sebelum dikunci sebagai pendekatan, dan dikonfirmasi ulang bekerja lewat eksekusi Checkpoint 6.

Satu celah kedua ditemukan dan diperbaiki (mirror pola celah M1.3 sesi sebelumnya): `retrieve_session_memory()` (M1.5) tidak punya `try/except` di sekitar query DB-nya — diperbaiki mirror persis pola `store_session_memory()`, didokumentasikan di M1.5 (bukan M7.7), TANPA perlu entri `docs/keterbatasan-diterima.md` karena celah ditutup sebelum sempat "diterima" sebagai keterbatasan.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Turn dengan referensi terdeteksi memicu kedua jalur berjalan bersamaan (dibuktikan lewat span dengan `parent_span_id` yang sama, menunjukkan keduanya anak dari span yang sama, bukan berurutan)" | Kejadian E01 (`evals/7.7-.../audit.md`) — `trace_id=1209dcff1ddf138a4a1118239a53dec6`, span `chat` (Rewrite) dan `memory.retrieve` (Tarik Memory) SAMA-SAMA `parentSpanID=5f88085f1577dcaf` (span `invoke_agent`), diquery langsung lewat Jaeger API, bukan asumsi kode. | **Ya, penuh.** |
| "turn tanpa referensi hanya memicu jalur Rewrite, jalur Tarik Memory tidak terpanggil sama sekali (bukan terpanggil lalu menghasilkan kosong)" | Kejadian E02 — `session_memory=None` (bukan `[]`) di level Python, DAN span `memory.retrieve` genuinely TIDAK ADA sama sekali dalam trace (`trace_id=be61c3ce528b50dc28a84561952e85da`) — dibuktikan di dua lapis (field + observability). Ditambah test deterministik `tests/orchestration/test_turn_pipeline.py::test_orkestrator_wiring_keadaan_turn_berisi_objek_identik` yang membuktikan `retrieve_session_memory` sama sekali tidak terpanggil (spy raise `AssertionError` kalau terpanggil). | **Ya, penuh.** |

## Bagian 3 — Cara Kerja dan Arsitektur

`proses_turn()` setelah `ketergantungan` didapat: hitung `harus_tarik_memory = ketergantungan.is_dependent and ketergantungan.referenced_turn_index is not None`, tangkap `ctx = otel_context.get_current()` (DI DALAM span `invoke_agent`), submit `_jalankan_rewrite(ctx, payload)` selalu dan `_jalankan_tarik_memory(ctx, session_id, turn_index)` kondisional ke `ThreadPoolExecutor(max_workers=2)`, `.result()` keduanya, kembalikan `KeadaanTurn` lengkap. Tiap fungsi worker melakukan `attach(ctx)`/`detach(token)` supaya span yang dibuka di dalamnya (`chat` dari Rewrite, `memory.retrieve` dari Tarik Memory) tetap tercatat sebagai anak `invoke_agent`, bukan trace terpisah.

`KeadaanTurn` bertambah `rewrite: RewriteResult` (selalu terisi — `rewrite_to_standalone()` py fallback penuh, tidak pernah raise) dan `session_memory: list[SessionMemoryPackage] | None` (`None` = tidak dipanggil, `[]` = dipanggil tapi genuinely kosong — dua kondisi yang harus terbedakan sesuai KK). Kegagalan ganda (kedua cabang gagal bersamaan) sengaja tidak ditangani khusus — diterima sebagai skenario tepi sangat sempit, didokumentasikan eksplisit di `decisions.md` Keputusan 5. Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

- Tidak ada penyimpangan checkpoint-vs-eksekusi pada struktur plan — seluruh 8 checkpoint dikerjakan sesuai rencana yang disetujui.
- **Dua perbaikan teknis ditemukan DAN diperbaiki di tengah eksekusi** (dicatat detail di `logs.md`), keduanya tidak mengubah struktur checkpoint: (1) identity check Pydantic `list[BaseModel]` butuh dicek per-elemen bukan container penuh (Checkpoint 4); (2) retry query Jaeger API perlu menunggu SET LENGKAP span, bukan cuma "ada data apa saja" — race nyata ditemukan+diperbaiki saat eksekusi pertama Checkpoint 6, percobaan kedua langsung sukses penuh.

## Bagian 5 — Keterbatasan dan Item Provisional

- **Kegagalan ganda (kedua cabang paralel gagal bersamaan) kehilangan satu exception tanpa peringatan** — diterima eksplisit sebagai skenario tepi sangat sempit (`decisions.md` Keputusan 5), tidak diminta KK sumber, tidak dibangun penanganan defensif tambahan.
- **`retrieve_session_memory()` (M1.5) diperbaiki** — lihat `milestones/1.5-tarik-session-memory/report.md` Addendum untuk detail lengkap, tidak diulang di sini.
- **Test M1.7 (`test_matching.py::test_kelompok_c_rantai_arsip_ulang_turn_tujuh_lima_tiga`) ditemukan flaky** saat regresi Checkpoint 2 — masalah isolasi test pra-eksisting (session_id hardcoded, data menumpuk di Supabase nyata antar-run), TIDAK TERKAIT perubahan M7.7/M1.5. Dicatat sebagai observasi, tidak diperbaiki (di luar Lingkup, kepemilikan test ada di M1.7) — kandidat follow-up kalau M1.7 disentuh lagi.

## Bagian 6 — Follow-up

- **2/11 Sambungan Level 2 selesai** — M7.8 ("Sambungan 3: Rewrite → Decomposition") adalah milestone berikutnya, WAJIB berurutan.
- **Pola `ThreadPoolExecutor` + propagasi context OTel manual** yang dibangun di sini kemungkinan dipakai ulang milestone Sambungan lain yang juga butuh percabangan paralel — kode helper (`_jalankan_rewrite`/`_jalankan_tarik_memory` pattern) bisa dijadikan referensi langsung, meski tidak diekstrak jadi utilitas generik di milestone ini (YAGNI — belum ada kebutuhan nyata kedua sampai milestone Sambungan lain benar-benar membutuhkannya).
- **Retry query Jaeger API berbasis "set span lengkap"** (bukan "ada data apa saja") sebaiknya jadi pola default untuk milestone Sambungan berikutnya yang butuh bukti span — dicatat di `audit.md` Temuan Pola.
- Follow-up M7.4 (potensi deduplikasi `_revisi_request()` M4.2) dan follow-up M7.6 (Struktur Repository `src/orchestration/`) masih berlaku, tidak terkait langsung M7.7.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
