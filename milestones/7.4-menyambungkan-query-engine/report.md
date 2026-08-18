# Report — Milestone 7.4: Menyambungkan Query Engine (Susun Request → Verifikasi Bentuk Request)

## Bagian 1 — Ringkasan Hasil

**Status akhir:** Selesai sesuai plan, tanpa penyesuaian di tengah jalan.

Berbeda dari Milestone 7.2/7.3 (kode penyambung ternyata sudah ada), investigasi mengonfirmasi Milestone 7.4 genuinely butuh kode baru — tidak ada fungsi mana pun di `src/` yang menyambungkan `susun_request_atomic_intent()` (M3.4) ke `verifikasi_bentuk_request_atomic_intent()` (M3.5) untuk jalur utama sebelum milestone ini. Fungsi orkestrator baru `susun_dan_verifikasi_request_atomic_intent()` (`src/layers/query_engine/query_engine.py`) dibangun, diuji unit (mocked) untuk wiring/short-circuit, dan dibuktikan nyata (LLM sungguhan) menangkap skenario mismatch `view_name` yang jadi Kriteria Keberhasilan sumber.

Dua keputusan desain non-trivial diselesaikan selama plan: (1) konflik skema `HasilVerifikasiBentukRequest.request` yang wajib non-null memaksa bentuk return type tuple (bukan reuse tipe M3.5 seperti preseden `domain_gate.py`) — dipilih user lewat `AskUserQuestion`; (2) parameter `view_name_tervalidasi_retriever` wajib terpisah dari `view_name` (bukan satu parameter bersama seperti satu-satunya caller nyata yang ada, `_revisi_request()` M4.2) — dipaksa oleh teks Kriteria Keberhasilan M7.4 sendiri, supaya skenario mismatch tetap bisa direproduksi lewat chain nyata alih-alih mustahil by construction.

## Bagian 2 — Kriteria Keberhasilan vs Bukti Nyata

| Kriteria (dari `rancangan-orkestrasi-api.md`) | Bukti Aktual | Terpenuhi? |
|---|---|---|
| "Request yang sengaja dibuat tidak sesuai hasil Retriever (skenario uji yang sudah dipakai Milestone 3.5) berhasil ditangkap saat mengalir dari langkah Susun ke langkah Verifikasi secara berurutan nyata, bukan diuji dengan input Verifikasi yang disusun manual terpisah dari output Susun." | `test_konektivitas_mismatch_view_name_tertangkap_verifikasi_nyata` (Checkpoint 3) — `susun_dan_verifikasi_request_atomic_intent()` dipanggil dengan `view_name="v_reservation_room_type_daily"` dan `view_name_tervalidasi_retriever="v_reservation_channel_daily"` (skenario KK1 M3.5, reuse `test_pre_check_gagal_llm_tidak_pernah_dipanggil`). LLM sungguhan untuk langkah Susun, spy membuktikan `request` yang diterima Verifikasi adalah objek PERSIS (identity) dari return Susun. `hasil_verifikasi.lolos is False`, alasan menyebut view_name yang salah. Lolos nyata, 22.68s. | **Ya.** |

## Bagian 3 — Cara Kerja dan Arsitektur

`susun_dan_verifikasi_request_atomic_intent(atomic_intent, view_name, view_name_tervalidasi_retriever=None, tanggal_referensi=None, feedback=None) -> tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]`:

1. `view_name_tervalidasi_retriever` default ke `view_name` kalau tidak diisi.
2. Panggil `susun_request_atomic_intent()` (M3.4). Kalau gagal (`status != BERHASIL` atau `request is None`), return `(hasil_susun, None)` — langkah Verifikasi tidak pernah dipanggil.
3. Kalau berhasil, panggil `verifikasi_bentuk_request_atomic_intent()` (M3.5) dengan `request` hasil Susun, return `(hasil_susun, hasil_verifikasi)`.

Tidak membuka span baru — kontrak observability §2 Query Engine (2 span `chat`) sudah terpenuhi penuh oleh instrumentasi M3.4/M3.5 masing-masing. Tidak ada skema baru ditambahkan ke `src/schemas/query_engine.py`. Lihat `decisions.md` untuk rasional lengkap tiap keputusan.

## Bagian 4 — Perubahan dari Plan

Tidak ada penyimpangan checkpoint-vs-eksekusi — seluruh 4 checkpoint dikerjakan persis sesuai plan yang disetujui. Satu catatan operasional yang tidak diantisipasi plan: `python -m pytest` dari interpreter global gagal `ModuleNotFoundError` (dependensi OpenTelemetry OTLP exporter tidak terpasang di sana) — project py virtualenv terpisah `.venv/` yang perlu dipanggil eksplisit (`./.venv/Scripts/python.exe -m pytest`). Tidak mengubah hasil verifikasi, hanya catatan environment untuk sesi kerja berikutnya.

## Bagian 5 — Keterbatasan dan Item Provisional

- **Kontrak tuple return mengikat untuk M7.6+ (Level 2, belum dibangun) sebelum ada pemakai nyata kedua** — `decisions.md` Keputusan 5 mendokumentasikan rasional lengkap. Kalau M7.6 nanti menemukan bentuk ini menyulitkan, perlu dicatat sebagai revisit di `docs/keputusan-tertunda.md` sebelum kode Level 2 banyak bergantung padanya — belum terjadi sekarang karena Level 2 belum dimulai.
- **`_revisi_request()` (M4.2) tidak direfactor** untuk memakai orkestrator baru ini, meski secara logic melakukan hal serupa (susun→verifikasi dengan `view_name` identik) — di luar Lingkup M7.4 (lihat `decisions.md` Keputusan 6). Berisiko divergen kalau salah satu berubah tanpa yang lain; dicatat sebagai follow-up potensial di Bagian 6, bukan keterbatasan yang butuh perbaikan segera.

## Bagian 6 — Follow-up

- **Potensi deduplikasi `_revisi_request()` (M4.2) dengan `susun_dan_verifikasi_request_atomic_intent()` (M7.4)** — keduanya mengimplementasikan pola susun→verifikasi serupa untuk `view_name` identik. Belum dikerjakan (di luar Lingkup M7.4), dipertimbangkan kalau M4.2 disentuh lagi di masa depan untuk alasan lain.
- **Milestone 7.5** (Interpretation) — follow-up langsung, dikerjakan setelah milestone ini dalam sesi yang sama, mengikuti pola desain yang sama (return type tuple, tanpa span baru).
- Dengan M7.4 tuntas, Level 1 tersisa: M7.5 saja. Seluruh 4 milestone Level 1 (7.2-7.5) wajib tuntas sebelum Level 2 (M7.6) dimulai.
- Tidak ada keputusan tertunda baru untuk `docs/keputusan-tertunda.md`.
