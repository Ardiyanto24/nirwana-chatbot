# Audit — Membangun Database Percakapan (Milestone 7.18)

Ditulis **setelah** eksekusi `run_eval.py` (2026-08-20), membandingkan hasil aktual terhadap ekspektasi `rancangan.md`. Payload final: `payloads/E01.json` (`session_id=eval-7.18-e01f`, percobaan yang berhasil — 3 percobaan sebelumnya gagal karena alasan berbeda-beda, lihat "Insiden Operasional").

## Ringkasan

**KK1 M7.18 TERPENUHI PENUH**, dibuktikan nyata lewat HTTP sungguhan (bukan simulasi/mock) — dengan catatan jujur bahwa jalan ke sana tidak lurus: perjalanan Checkpoint 7 justru menemukan dan menutup bug produksi genuinely baru di luar cakupan M7.18 sendiri (`klasifikasi_kebutuhan()`, M1.6), pola yang konsisten dengan preseden M7.6/M7.7/M7.17 (eksekusi nyata menemukan celah yang tidak kelihatan dari test mocked).

KK2 M7.18 (kegagalan penulisan riwayat tidak boleh menggagalkan response) **TIDAK diuji ulang di sini** — sudah dibuktikan deterministik penuh di Checkpoint 3 (unit, mocked `Session`/`get_engine`) dan Checkpoint 5 (level HTTP, mocked `simpan_riwayat_turn` untuk raise) sebelum Checkpoint 7 dimulai, sesuai `rancangan.md` yang eksplisit menyatakan KK2 "tidak relevan di sini" — eval Checkpoint 7 fokus murni ke KK1 (butuh eksekusi nyata; KK2 justru butuh SIMULASI kegagalan yang controlled, bukan kondisi nyata).

| ID | Fokus KK | Hasil aktual | HTTP status | Baris `conversation_turns` |
|---|---|---|---|---|
| E01 | KK1 — riwayat tersimpan cocok | `gagal_teknis` (data Juni 2026 belum tersedia), narasi jujur | 200 | 1 baris, seluruh field cocok persis |

## Analisis Kejadian

### E01 — Kebutuhan tunggal sederhana (LOLOS PENUH — KK1 terbukti)

Payload identik `evals/7.17-.../E01.json` (General Manager, "Berapa occupancy rate properti kita bulan Juni 2026?"), `session_id=eval-7.18-e01f` (percobaan ke-4 keseluruhan, ke-1 yang genuinely mencapai eksekusi bersih — lihat Insiden Operasional).

Hasil: HTTP 200, narasi *"Saat ini, sistem mengalami kendala teknis dalam mengambil data tingkat keterisian properti untuk bulan Juni tahun 2026..."*, `terverifikasi=true`. Query langsung `conversation_turns` mengembalikan TEPAT 1 baris baru:

| Invarian `rancangan.md` | Hasil |
|---|---|
| HTTP 200 | ✓ |
| Tepat 1 baris baru, `turn_index` sesuai payload | ✓ (`turn_index=1`) |
| `pertanyaan` PERSIS sama dengan `question` payload | ✓ |
| `narasi` PERSIS sama dengan body response HTTP (bukan `HasilNarasi.narasi` internal) | ✓ |
| `status` konsisten dengan execution/`paket_narasi` yang genuinely terjadi | ✓ (`"gagal_teknis"`, seragam — 1 atomic intent, narasi jujur melaporkan kendala teknis, bukan `"campuran"`) |

**Kesimpulan**: `_simpan_riwayat_percakapan_aman()` (M7.18) genuinely menyimpan versi riwayat yang PERSIS sama dengan yang diterima user (`TurnResponse.narasi`, versi pasca-suppression M7.17 kalau berlaku) — KK1 M7.18 terbukti nyata, bukan cuma lewat unit test mocked.

## Insiden Operasional

4 percobaan total sebelum sukses, TIGA penyebab berbeda (bukan pengulangan penyebab yang sama):

1. **Percobaan 1** (`eval-7.18-e01`): chatbot_api DAN app server mati bersamaan tanpa traceback tertangkap (stderr `DEVNULL`) — diagnosis: kemungkinan besar interupsi lingkungan (bukan bug kode, satu-satunya request yang sempat diproses berperilaku normal).
2. **Percobaan 2** (`eval-7.18-e01b`): selesai bersih (exit 0) TAPI hasil **HTTP 500** — genuinely bug produksi baru, BUKAN infra. Traceback (ditangkap manual via server debug terpisah dengan stderr tidak dibuang) menunjuk `TypeError: 'NoneType' object is not subscriptable` di `klasifikasi_kebutuhan()` (`src/layers/decomposition/klasifikasi.py:69`) — `response.choices` bernilai `None` (respons OpenRouter HTTP 200 dengan body malformed, tidak raise `openai.APIError` sehingga tidak tertangkap `except` yang sudah ada). Titik ini SUDAH terdaftar lebih dulu di `docs/keterbatasan-diterima.md` #17 (ditemukan riset M7.17, sengaja diterima sampai terbukti nyata) — pemicu peninjauan ulang entri itu sendiri terpenuhi di sini. Diperbaiki DI M1.6 (milestone pemilik layer), BUKAN di M7.18 — mirror pola perbaikan M7.6/M7.7. Detail lengkap: `milestones/1.6-decomposition/decisions.md` Keputusan 15 (Addendum).
3. **Percobaan 3** (`eval-7.18-e01e`): chatbot_api mati lagi SEBELUM eval sempat mulai (`_cek_prasyarat()` gagal secepatnya) — root cause BEDA dari percobaan 1: proses `nohup ... &` manual yang dipakai me-restart chatbot_api ternyata tidak survive antar-tool-call di lingkungan kerja sesi ini. Diperbaiki dengan menjalankan chatbot_api via mekanisme `run_in_background` bawaan tool (lebih stabil, tidak terulang di percobaan berikutnya).
4. **Percobaan 4** (`eval-7.18-e01f`): **BERHASIL PENUH**, seperti dilaporkan di atas.

## Temuan Metodologi

Konsisten pola M7.6/M7.7/M7.11/M7.17: **eksekusi HTTP nyata sekali lagi menemukan bug produksi yang genuinely tidak kelihatan dari test mocked** — 200+ test project (termasuk `tests/test_main.py` M7.17/M7.18 yang mock `proses_turn()`/`_call_llm` di titik lain) tidak pernah memanggil `klasifikasi_kebutuhan()` dengan respons OpenRouter sungguhan yang malformed, karena kondisi itu (HTTP 200 + body `choices=None`) bukan sesuatu yang bisa disimulasikan lewat mock deterministik yang biasa ditulis — ia murni karakteristik infrastruktur pihak ketiga yang cuma muncul dari panggilan API sungguhan. Ini memperkuat nilai eksplisit skenario "eksekusi nyata" (Checkpoint 7 setiap milestone Level 2/endpoint) sebagai lapisan verifikasi yang TIDAK tergantikan oleh cakupan unit test semata, bukan sekadar formalitas penutup milestone.

Catatan tambahan: 3 dari 4 percobaan gagal di sini punya AKAR PENYEBAB BERBEDA-BEDA (infra transient, bug produksi genuinely baru, ketidakstabilan proses background lokal) — bukan pengulangan satu masalah yang sama seperti `docs/keterbatasan-diterima.md` #7 (hang LLM tanpa exception). Dicatat apa adanya, tidak disamarkan sebagai satu kejadian tunggal.
