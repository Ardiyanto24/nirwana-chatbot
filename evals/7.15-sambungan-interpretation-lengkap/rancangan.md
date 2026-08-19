# Rancangan Pengujian — Sambungan 10: (Pencocokan jalur "selesai" + Execution) → Interpretation (Milestone 7.15)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai). Struktur mirror `evals/7.14-.../rancangan.md`.

**Beda mendasar dari eval M7.6-7.14**: E01 di sini adalah **kejadian 2-TURN NYATA PERTAMA** yang genuinely bergantung pada M4.3 (Penyimpanan Paket) tersambung orkestrator — sebelum M7.15, `susun_dan_simpan_paket_semua()` belum ada, jadi turn manapun sebelumnya TIDAK PERNAH benar-benar menyimpan hasil Execution ke Session Memory lewat `proses_turn()`. `evals/7.9-.../E06` (skenario 2-turn serupa) terpaksa memakai SEED MANUAL (`store_session_memory()` langsung) karena saat itu M4.3 belum tersambung — di M7.15 ini, turn 1 dijalankan NYATA lewat `proses_turn()` itu sendiri, sehingga penyimpanannya genuinely berasal dari alur sungguhan (persis kata KK sumber: "dibuktikan dengan kedua sumber data yang benar-benar berasal dari alur sungguhan").

**Pelajaran metodologi M7.9-7.14**: non-determinisme Decomposition/klasifikasi dicatat sebagai invarian mekanisme, bukan jumlah/hasil absolut. `session_id` BARU per kejadian (`eval-7.15-eXX`).

## Yang Diuji

`proses_turn()` — segmen baru M7.15: setelah wave loop (M7.14), `susun_dan_simpan_paket_semua()` mengonversi+menyimpan hasil Execution, `susun_paket_narasi()` menggabungkan paket "selesai" (di-re-key)+eksekusi+gap sintetis, `susun_dan_verifikasi_narasi()` (M7.5) menyusun narasi akhir.

**Invarian mekanisme yang wajib benar di SEMUA kejadian:**

1. `len(hasil.paket_narasi) == len(hasil.matches)` — SETIAP atomic intent turn ini (apa pun statusnya) berakhir py TEPAT SATU paket di `paket_narasi`, tidak ada yang hilang.
2. Untuk item `matches[i].status == "selesai"`: `paket_narasi[i].atomic_intent_id == matches[i].atomic_intent.atomic_intent_id` (BUKAN ID turn asal) — bukti fix re-keying (Keputusan 1) bekerja.
3. `hasil.interpretation[0].narasi` (teks narasi final) WAJIB berupa string non-kosong, TIDAK mengandung istilah teknis mentah (`gagal_teknis`, `ditolak_otorisasi` sebagai kata harfiah — prompt M4.4 Aturan larangan eksplisit menyebut nama status mentah).
4. Span `orchestration.susun_paket_narasi` WAJIB ter-emit dengan 4 atribut count (`selesai_count`+`eksekusi_count`+`gap_rbac_count`+`gap_teknis_count`) yang jumlahnya sama dengan `len(matches)`.

## Kejadian

### E01 — Campuran "selesai" + Execution baru, 2-TURN NYATA (KK literal utama)

**Payload Turn 1:** `session_id="eval-7.15-e01"`, `turn_index=1`, `role_title="General Manager"`, `question="Berapa occupancy rate bulan April 2026?"` (mirror teks `evals/7.9-.../E06`, `session_id` baru).

**Payload Turn 2** (dijalankan SETELAH Turn 1 selesai, `history` mengacu hasil Turn 1 apa adanya): `session_id="eval-7.15-e01"` (SAMA — turn kedua sesi yang sama), `turn_index=2`, `question="Bandingkan dengan occupancy satu tahun sebelumnya."`.

**Ekspektasi (mengacu hasil nyata `evals/7.9-.../E06`, kali ini dengan Turn 1 genuinely dieksekusi bukan di-seed manual):**
- Turn 1: 1 atomic intent, `view_name_final` kemungkinan `v_lookup_daily_occupancy` (TERBUKTI 200 nyata Checkpoint 1) — hasil Execution TERSIMPAN via `susun_dan_simpan_paket_semua()` (BARU, pertama kali genuinely terjadi lewat `proses_turn()`).
- Turn 2: `ketergantungan.is_dependent=True`, Rewrite menghasilkan pertanyaan mandiri (mis. "occupancy April 2025 vs April 2026"), Decomposition kemungkinan `majemuk_bergantung` 3 atomic intent (April 2025 independen, April 2026 independen, perbandingan bergantung — mirror pola persis M7.9 E06).
- **Bukti KK literal M7.15**: atomic intent "April 2026" turn 2 dicocokkan Pencocokan (M1.7) ke paket Turn 1 (`status=selesai`) — di `paket_narasi`, paket ini WAJIB `atomic_intent_id` = ID atomic intent TURN 2 (bukan turn 1), `sumber="session_memory (turn 1)"`. Atomic intent "April 2025" (dan mungkin "perbandingan") mencapai Execution TURN 2 (`sumber="eksekusi_baru"`). Narasi akhir (`hasil.interpretation[0].narasi`) WAJIB menyebutkan SALAH SATU angka sebagai "sudah dihitung sebelumnya"/rujukan turn lalu, dan yang lain sebagai baru dihitung — DIBACA MANUAL dari teks narasi (bukan cuma structural check).

---

### E02 — Paket gap RBAC (bukti klasifikasi 2 tingkat, reuse skenario domain ditolak total M7.11 E03/M7.12 E02)

**Payload:** turn 1, `session_id="eval-7.15-e02"`, `role_title="F&B Staff"`, `question="Berapa GOP (gross operating profit) properti bulan ini?"` — teks IDENTIK `evals/7.11-.../E03`, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.11 E03/M7.12 E02: domain `financial` ditolak SELURUHNYA untuk F&B Staff, `view_name_final=None`, 0 kandidat):**
- Atomic intent ini TIDAK PERNAH mencapai Execution (konsisten hasil M7.11/M7.12 sebelumnya).
- **Bukti klasifikasi RBAC**: di `paket_narasi`, paket untuk atomic intent ini WAJIB `status=DITOLAK_OTORISASI`, `catatan_interpretasi=["Anda tidak memiliki akses untuk data ini sesuai peran Anda."]`. Narasi akhir WAJIB menyebutkan eksplisit soal keterbatasan akses (Aturan 3 prompt M4.4), TANPA menyamarkan sebagai kegagalan teknis biasa.

---

### E03 — Paket gap teknis (bukti klasifikasi 2 tingkat, sisi generik — reuse skenario HR "review kinerja Budi" M7.13/M7.14 yang terbukti non-deterministik klasifikasi label)

**Payload:** turn 1, `session_id="eval-7.15-e03"`, `role_title="HR Staff"`, `question="Bagaimana hasil review kinerja Budi semester ini?"` — teks IDENTIK M7.13/M7.14, `session_id` BARU.

**Ekspektasi (mengacu hasil nyata M7.14 E02 retry: `label_bentuk_jawaban` non-deterministik antara `nilai_tunggal`/`peringkat` — kasus `peringkat` menyebabkan M3.5 menolak `lolos=False`, item DI-SKIP sebelum Verification Gate, TIDAK PERNAH mencapai Execution):**
- **Prioritas LEBIH RENDAH dari E01/E02** — kejadian ini murni BONUS bukti "gap teknis" (kategori generik), TIDAK esensial untuk KK literal M7.15. Kalau run ini kebetulan menghasilkan `label_bentuk_jawaban=nilai_tunggal` (item BERHASIL mencapai Execution, seperti M7.13 asli), kejadian ini TETAP dicatat apa adanya di `audit.md` sebagai "tidak menghasilkan gap kali ini" — TIDAK di-retry paksa untuk memaksa hasil gap.
- **Kalau genuinely menghasilkan gap** (item tidak mencapai Execution karena alasan APA PUN — Retriever/Query Engine/Verification Gate): paket di `paket_narasi` WAJIB `status=GAGAL_TEKNIS`, `catatan_interpretasi=["Sistem tidak berhasil memproses kebutuhan ini karena kendala teknis."]`, narasi menyebut kendala teknis TANPA istilah internal (Aturan 4 prompt M4.4).

## Catatan Non-Determinisme

E01 adalah PRIORITAS UTAMA (satu-satunya yang wajib membuktikan KK literal) — kalau Decomposition Turn 2 kebetulan TIDAK menghasilkan campuran selesai+eksekusi baru (mis. seluruh 3 atomic intent kebetulan match "selesai" semua, atau tidak ada yang match sama sekali), dicatat transparan di `audit.md`, dipertimbangkan menjalankan Turn 2 ulang (session_id BARU untuk turn 1+2 sepasang, BUKAN retry turn 2 saja terhadap turn 1 yang sama — supaya tetap 1 pasang turn yang koheren) SEKALI sebelum audit ditulis kalau percobaan pertama genuinely tidak menghasilkan campuran sama sekali. E02 diprioritaskan kedua (reuse skenario TERBUKTI 2x konsisten). E03 murni bonus, non-determinisme diterima apa adanya tanpa retry.

## Ringkasan Ekspektasi

| ID | Turn | `role_title` | Fokus utama | Prioritas |
|---|---|---|---|---|
| E01 | 1+2 (sepasang) | General Manager | KK literal — campuran selesai+eksekusi dalam satu narasi | **Wajib** |
| E02 | 1 | F&B Staff | Klasifikasi gap RBAC | Penting |
| E03 | 1 | HR Staff | Klasifikasi gap teknis (bonus) | Opsional |
