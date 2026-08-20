# Rancangan Pengujian — Membangun Database Percakapan (Milestone 7.18)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Mengadaptasi infrastruktur `evals/7.17-membangun-endpoint-api/run_eval.py` (server `uvicorn` port 8001 nyata via `sys.executable -m uvicorn` — VERSI YANG SUDAH DIPERBAIKI M7.17, BUKAN wrapper `uv run uvicorn` yang menyebabkan proses orphan) — beda fokus: setelah panggilan HTTP selesai, query LANGSUNG tabel `conversation_turns` (tidak ada fungsi retrieve produksi, `decisions.md` Keputusan 6) untuk memverifikasi baris riwayat tersimpan cocok.

## Yang Diuji

`POST http://127.0.0.1:8001/v1/turns` — endpoint HTTP sungguhan, `chatbot_api` (port 8000) DAN Jaeger HARUS `up`. Setelah response diterima, query `conversation_turns` via SQLModel langsung (bukan API) untuk `session_id` yang dipakai.

**Invarian yang wajib benar:**

1. Response HTTP 200 (KK2 M7.18 tidak relevan di sini — mekanisme "gagal tidak boleh menggagalkan response" SUDAH dibuktikan deterministik di Checkpoint 5, eval ini fokus KK1).
2. Tepat SATU baris baru muncul di `conversation_turns` untuk `session_id` yang dipakai, `turn_index` sesuai payload.
3. `pertanyaan` di baris tersimpan PERSIS sama dengan `question` yang dikirim di payload request.
4. `narasi` di baris tersimpan PERSIS sama dengan `narasi` di body response HTTP yang diterima (BUKAN `HasilNarasi.narasi` internal — membuktikan yang tersimpan adalah versi yang user GENUINELY terima, `decisions.md` Keputusan 3).
5. `status` di baris tersimpan adalah salah satu nilai valid (`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/`terblokir_ketergantungan`/`campuran`/`tidak_ada_kebutuhan`) — dicek KONSISTEN dengan `execution`/`paket_narasi` yang genuinely terjadi (dicek manual dari log, bukan diklaim tanpa bukti).

## Kejadian

### E01 — Kebutuhan tunggal sederhana, KK1 (payload valid via HTTP nyata)

**Payload:** identik `evals/7.17-.../E01.json` raw_payload_http (General Manager, "Berapa occupancy rate properti kita bulan Juni 2026?"), `session_id` BARU.

**Ekspektasi (mengacu M7.17 E01 — 1 atomic intent, kemungkinan besar `gagal_teknis`/`sebagian` mengingat data `chatbot_api` lokal stale, `docs/keterbatasan-diterima.md` #15 — TIDAK mensyaratkan `BERHASIL`):**
- Response HTTP 200, `narasi` non-kosong.
- SATU baris baru di `conversation_turns`, `pertanyaan` == payload `question`, `narasi` == response body `narasi` persis, `turn_index` == 1.
- `status` tersimpan konsisten dengan `execution`/`paket_narasi` yang genuinely terjadi (kemungkinan besar `gagal_teknis` mengingat 1 atomic intent, seragam → BUKAN `"campuran"`).

## Catatan Non-Determinisme

Sama seperti M7.9-7.17: hasil aktual (status execution) TIDAK dijamin identik run-ke-run meski payload sama persis — dicatat apa adanya di `audit.md`, `status` yang tersimpan hanya perlu KONSISTEN dengan apa yang genuinely terjadi di run itu sendiri, bukan dibandingkan ke ekspektasi kaku.

## Ringkasan Ekspektasi

| ID | `role_title` | Fokus KK | Verifikasi utama |
|---|---|---|---|
| E01 | General Manager | KK1 — riwayat tersimpan cocok | Query langsung `conversation_turns`, cocokkan `pertanyaan`/`narasi`/`turn_index` |
