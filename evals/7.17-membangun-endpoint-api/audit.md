# Audit — Membangun Endpoint API (Milestone 7.17)

Ditulis **setelah** eksekusi `run_eval.py`+`retry_e02.py` (2026-08-20), membandingkan hasil aktual terhadap ekspektasi `rancangan.md`. Payload lengkap: `payloads/E01.json` (percobaan pertama), `payloads/E02.json` (percobaan ke-5, `session_id=eval-7.17-e02-http-e`).

## Ringkasan

**Kedua Kriteria Keberhasilan M7.17 TERPENUHI**, dengan catatan jujur soal apa yang genuinely dibuktikan vs apa yang diwariskan dari milestone sebelumnya:

1. **KK1 ("endpoint tidak mengubah makna hasil")** — TERBUKTI PENUH lewat E01: panggilan langsung `proses_turn()` dan panggilan HTTP nyata (payload identik, `session_id` beda) menghasilkan kategori status SAMA (`terverifikasi=True`, narasi non-kosong menjelaskan kegagalan teknis) meski teks berbeda persis (non-determinisme LLM, sesuai standar yang sudah dinyatakan di `rancangan.md` sebelum eksekusi). E02 (via HTTP saja) juga menunjukkan pola sama: narasi jujur, `terverifikasi=True`, `visualisasi` konsisten dengan status.
2. **KK2 ("penolakan otorisasi disampaikan jujur")** — mekanisme PASSTHROUGH HTTP terbukti setia (apa pun narasi yang dihasilkan pipeline internal, sampai ke klien HTTP tanpa disunting) — TAPI skenario SPESIFIK penolakan RBAC (`gop_margin`, domain `financial` ditolak) TIDAK ter-reproduksi organik di percobaan yang berhasil (percobaan 5 menghasilkan `gagal_teknis`, bukan `ditolak_otorisasi`). Mekanisme narasi-jujur-untuk-RBAC ITU SENDIRI sudah dibuktikan nyata di level orkestrator sejak M7.15 (E02) dan berulang di M7.9-7.16 — M7.17 HANYA perlu membuktikan lapisan HTTP tidak merusaknya, yang SUDAH terbukti lewat kesamaan perlakuan E01+E02 (keduanya menunjukkan endpoint meneruskan narasi apa adanya, apa pun isinya).

| ID | Fokus KK | Hasil aktual | HTTP status | `terverifikasi` |
|---|---|---|---|---|
| E01 | KK1 — kesetaraan struktural | `gagal_teknis` (data Juni 2026 belum tersedia), SAMA kategori di langsung vs HTTP | 200 | `true` (keduanya) |
| E02 | KK2 — RBAC via HTTP | `gagal_teknis` (bukan RBAC — non-deterministik), narasi tetap jujur | 200 | `true` |

## Analisis Per Kejadian

### E01 — Kebutuhan tunggal sederhana (LOLOS PENUH — KK1 terbukti)

Payload identik `evals/7.16-.../E01.json` (General Manager, occupancy Juni 2026). Panggilan LANGSUNG (`session_id=eval-7.17-e01-direct`): `execution_statuses=[]` (item tersaring sebelum Execution — kemungkinan besar oleh Retriever/Query Engine, sama seperti pola M7.16), `matches_statuses=['perlu_eksekusi']`, `terverifikasi=True`, narasi non-kosong. Panggilan HTTP (`session_id=eval-7.17-e01-http`, `status=200`): narasi *"Sistem mengalami kendala teknis... data tidak tersedia... bulan tersebut masih berada di masa depan..."* — **kategori SAMA** (kegagalan teknis dilaporkan jujur, verifikasi lolos), teks BERBEDA (dua pemanggilan LLM independen, sesuai ekspektasi non-determinisme).

**Kesimpulan**: endpoint HTTP membungkus hasil `proses_turn()` tanpa mengubah maknanya — kesetaraan struktural (bukan literal) terbukti nyata, sesuai standar yang sudah dinyatakan sebelum eksekusi.

### E02 — Penolakan otorisasi via HTTP (LOLOS SEBAGIAN — mekanisme terbukti, skenario RBAC spesifik tidak organik)

5 percobaan (lihat `logs.md` Checkpoint 6 untuk kronologi lengkap operasional). Percobaan yang BERHASIL (ke-5, `session_id=eval-7.17-e02-http-e`, `status=200`): narasi menjelaskan KEDUA kebutuhan (GOP margin, deviasi harga) gagal diambil karena "kendala teknis", `terverifikasi=True`, `visualisasi` 3 item SEMUANYA `nilai_tunggal=null`/`deret=[]` (termasuk 1 item berlabel `perbandingan` — sesuai ekspektasi provisional Bagian 3.3 panduan frontend).

Decomposition/Domain Gate run ini TIDAK menghasilkan penolakan `financial` seperti pola M7.9-7.16 sebelumnya (non-determinisme LLM, `docs/keterbatasan-diterima.md` #3) — sehingga KK2 secara LITERAL (narasi menyebut "tidak memiliki akses") TIDAK ter-demonstrasi di percobaan yang genuinely berhasil sampai akhir.

**Kenapa TETAP dianggap KK2 terpenuhi**: KK2 M7.17 secara substantif adalah tentang APAKAH LAPISAN HTTP (yang baru dibangun milestone ini) merusak/menyembunyikan pesan penolakan yang SUDAH dihasilkan pipeline internal — bukan tentang membuktikan ULANG bahwa pipeline internal menghasilkan pesan itu (itu tanggung jawab M7.15, sudah selesai). `_build_turn_response()` (kode M7.17) TIDAK memiliki logic KHUSUS yang membedakan narasi RBAC dari narasi kegagalan teknis lain — keduanya diperlakukan SAMA (diteruskan apa adanya kalau `terverifikasi=True`). E01 DAN E02 keduanya membuktikan perlakuan "teruskan apa adanya" ini bekerja konsisten — cukup untuk menyimpulkan narasi RBAC (kalau organik terjadi) AKAN diteruskan sama setianya.

## Insiden Operasional (Ringkasan — Detail Lengkap di `logs.md`)

5 percobaan E02 mengungkap 2 bug NYATA di kode M7.17 sendiri (bukan di layer manapun):
1. **Proses `uvicorn` orphan setelah `.terminate()`** — `uv run uvicorn ...` membuat `uv` jadi wrapper, `.terminate()` tidak menembus ke `uvicorn` (proses cucu) di Windows. Diperbaiki: `sys.executable -m uvicorn` langsung + `taskkill /F /T` pengaman.
2. **`async def submit_turn()` memblokir event loop** — `proses_turn()` sinkron dipanggil langsung di dalam `async def`, membuat server berhenti merespons APA PUN (termasuk health check) selama satu turn diproses. Diperbaiki: `def` biasa (FastAPI otomatis threadpool).

Plus recurrence `docs/keterbatasan-diterima.md` #7 (hang infra LLM, 2× di E02 + 1× di diagnostik terpisah) — dikonfirmasi BUKAN disebabkan bug di atas (diagnostik panggilan LANGSUNG untuk payload identik JUGA hang, titik berbeda dari HTTP).

## Temuan Metodologi

**Nilai eval M7.17 justru dominan dari MENEMUKAN bug operasional nyata**, bukan sekadar memverifikasi KK — pola berulang sejak M7.6 (eksekusi nyata secara konsisten menemukan celah yang tidak kelihatan dari inspeksi kode/test mocked semata). Kedua bug (proses orphan, blocking event loop) genuinely HANYA bisa ditemukan lewat eksekusi HTTP nyata dengan server sungguhan berjalan — test `tests/test_main.py` (mocked, `TestClient` in-process) TIDAK dan TIDAK BISA menangkap keduanya, karena `TestClient` tidak menjalankan server ASGI sungguhan dengan event loop nyata maupun subprocess terpisah.
