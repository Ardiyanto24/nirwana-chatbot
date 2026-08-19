# Logs — Milestone 7.14: Sambungan 9 (Verification Gate → Execution, termasuk uji wave berulang)

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan + Prasyarat Reachability `chatbot_api`

**Mulai:** 2026-08-19 · **Selesai:** 2026-08-19

### Task 1 — Tulis decisions.md

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/7.14-sambungan-execution/decisions.md` — 10 entri keputusan (1 Jenis A genuinely terbuka: desain wave, dikonfirmasi user lewat diskusi chat sebelum plan ditulis setelah penjelasan konkret skenario `gop_margin`; 9 Jenis B forced/preseden termasuk koreksi folder `chatbot_api` yang benar).

**Temuan**
Tidak ada temuan baru di luar yang sudah ditemukan sebelum plan ditulis (riset plan sudah menemukan koreksi folder `api/` vs `scripts/chatbot_api/`, signature `eksekusi_atomic_intent()` butuh `constraint`).

**Error/Kegagalan (jika ada)**
Tidak ada.

**Diagnosis dan Perbaikan (jika ada error)**
Tidak berlaku.

**Hasil Verifikasi**
`decisions.md` ditulis lengkap, 10 entri + Daftar Isi Keputusan.

**Commit:** *(dicatat bersama Task 2)*

### Task 2 — Jalankan `chatbot_api` lokal, verifikasi reachability nyata

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Cek dependensi Python global (`fastapi 0.141.1`, `uvicorn 0.52.3`, `psycopg2`) — sudah terpasang, tidak perlu install ulang. Jalankan `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000` dari `nirwana-database/scripts/chatbot_api/` (background). `GET /health` → `200` (dikonfirmasi `curl`).

Tiga panggilan nyata berurutan (reuse skenario M4.1 Checkpoint 5: `role_title="Front Office Staff"`, `employee_id="E0071"`, `view_name="v_lookup_daily_occupancy"`, domain `reservation`, `params={"property_id": "P01"}`):
1. `panggil_chatbot_api()` (M4.1) langsung — `status_code=200`, body data occupancy nyata (8 kolom).
2. `panggil_meta_chatbot_api()` — `status_code=200`, `data_quality_status="ok"`, `last_refreshed_at="2026-08-11T06:03:04.668186+00:00"` — pertama kali fungsi ini tereksekusi terhadap server nyata sama sekali (celah spesifik yang dicatat `docs/keterbatasan-diterima.md` #13).
3. `eksekusi_atomic_intent()` (M4.2, orkestrator penuh, dipanggil langsung dengan `AtomicIntent`+`QueryEngineRequest`+`ConstraintCakupanIndividu(terdeteksi=False)` buatan tangan) — `status=StatusEksekusi.SEBAGIAN` (bukan `BERHASIL`), `retry_count_infra=0`, `revisi_count=0`, `data_quality_status="ok"`, `nilai_hasil` berisi data JSON asli.

Update `docs/keterbatasan-diterima.md` #13 — judul ditambah "DIVERIFIKASI (2026-08-19)", paragraf baru mencatat hasil ketiga panggilan di atas.

**Temuan**
`eksekusi_atomic_intent()` mengembalikan `SEBAGIAN` (bukan `BERHASIL`) untuk data nyata ini — `last_refreshed_at` (2026-08-11) lebih tua ~8 hari dari tanggal eksekusi (2026-08-19), melebihi `EXECUTION_DATA_STALENESS_THRESHOLD_JAM` (48 jam). Ini BUKAN bug — justru bukti POSITIF bahwa logika staleness M4.2 (dibangun murni via simulasi test sebelumnya) bekerja BENAR terhadap kondisi data sungguhan yang genuinely stale. Kekhawatiran risiko di `docs/keterbatasan-diterima.md` #13 ("bentuk respons HTTP nyata mungkin sedikit menyimpang dari simulasi test") TIDAK terwujud — bentuk body JSON konsisten dengan yang disimulasikan test M4.1/M4.2.

**Error/Kegagalan (jika ada)**
Percobaan pertama skrip verifikasi gagal `ModuleNotFoundError: No module named 'src.config.domain'` — import `Domain` salah lokasi.

**Diagnosis dan Perbaikan**
`Domain` enum sebenarnya ada di `src/schemas/domain_gate.py` (dikonfirmasi lewat `Grep` cepat), bukan `src/config/domain.py` yang tidak eksis. Diperbaiki, dijalankan ulang berhasil.

**Hasil Verifikasi**
3 panggilan nyata (`panggil_chatbot_api`, `panggil_meta_chatbot_api`, `eksekusi_atomic_intent`) seluruhnya `status_code=200` di level HTTP, `chatbot_api` server tetap `up` di background untuk checkpoint-checkpoint berikutnya yang butuh koneksi nyata.

**Commit:** *(dicatat di commit berikutnya)*

---
