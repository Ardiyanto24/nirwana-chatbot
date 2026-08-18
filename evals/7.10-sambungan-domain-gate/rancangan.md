# Rancangan Pengujian — Sambungan 5: Pencocokan (jalur "perlu eksekusi") → Domain Gate (Milestone 7.10)

Dokumen ini ditulis **sebelum** eksekusi (`run_eval.py` belum dijalankan saat dokumen ini selesai) — kejadian dan ekspektasi ditetapkan dulu, supaya hasil aktual dinilai objektif terhadap kriteria yang sudah ada. Struktur mirror `evals/7.6-.../` s.d. `evals/7.9-.../`. Verdict primer berbasis atribut span `intent.count` (span `domain_gate.identifikasi_semua`, tracer `domain_gate.domain_gate`) — atribut ini SUDAH disediakan langsung oleh kode M2.1, tidak perlu teknik hitung child-span lewat relasi parent seperti `evals/7.9-.../` (lihat `decisions.md` Keputusan 5).

## Yang Diuji

`proses_turn()` — khusus segmen baru M7.10: `identifikasi_domain_semua(matches)` dipanggil sekuensial setelah Pencocokan (M7.9) selesai, `matches` diteruskan APA ADANYA (filter ke `status=PERLU_EKSEKUSI` adalah tanggung jawab internal `identifikasi_domain_semua()` sendiri, sudah ada sejak M2.1). Kejadian di sini menjalankan pipeline PENUH — Decomposition, Tarik Memory, Pencocokan benar-benar dari `proses_turn()` nyata, BUKAN `list[AtomicIntentMatch]` buatan tangan langsung dipassing ke `identifikasi_domain_semua()`.

## Kejadian

### E01 — Campuran dua status (bukti KK literal utama, reuse payload+seeding `evals/7.9-.../E06`)

**Seeding:** `store_session_memory()` untuk `session_id="eval-7.10-e01"` (BARU, bukan `eval-7.9-e06` — lihat `decisions.md` Keputusan 6), `turn_index=1`: `teks_kebutuhan="Berapa occupancy rate bulan April 2026?"`, `status=berhasil`, `nilai_hasil={"occupancy_rate": 78}`.

**Payload:** turn 2, histori turn 1 "Berapa occupancy rate bulan April 2026?" → "Occupancy April 2026 mencapai 78%.", pertanyaan: "Bandingkan dengan occupancy satu tahun sebelumnya." (persis skenario M7.9 E06/M7.8 E01).

**Ekspektasi (mengacu hasil nyata M7.9 E06):**
- Decomposition `majemuk_bergantung`, 3 atomic_intents (April 2025, April 2026, perbandingan).
- Pencocokan: 1 `selesai` (April 2026, match ke seeding) + 2 `perlu_eksekusi` (April 2025, perbandingan).
- **`KeadaanTurn.domain_gate` berisi TEPAT 2 item** (bukan 3) — hanya yang `perlu_eksekusi`.
- Span `domain_gate.identifikasi_semua` py atribut **`intent.count=2`** — bukti KK literal ("Domain Gate hanya menerima jumlah atomic intent yang sesuai, bukan seluruhnya").

---

### E02 — Seluruh match `perlu_eksekusi` (tidak ada yang ditahan)

**Payload:** turn 1, tanpa histori, "Berapa occupancy rate properti kita bulan Juni 2026?" (tidak ada seeding — turn pertama, tidak mungkin ada match).

**Ekspektasi:**
- `ketergantungan.is_dependent=False` → `session_memory=None` → Pencocokan fast-path, 1 atomic_intent, `status=perlu_eksekusi`.
- **`KeadaanTurn.domain_gate` berisi TEPAT 1 item** — SAMA BANYAK dengan `matches` (semua diteruskan, tidak ada yang ditahan).
- Span `domain_gate.identifikasi_semua` py atribut **`intent.count=1`**.

---

### E03 — Seluruh match `selesai` (semua ditahan, TIDAK ada yang diteruskan)

**Seeding:** `store_session_memory()` untuk `session_id="eval-7.10-e03"`, `turn_index=1`: `teks_kebutuhan="Berapa occupancy rate bulan April 2026?"`, `status=berhasil`.

**Payload:** turn 2, histori sama, pertanyaan: "Berapa lagi occupancy April 2026 itu?" (persis skenario M7.9 E03 — match penuh, tunggal).

**Ekspektasi:**
- Decomposition tunggal, 1 atomic_intent, Pencocokan `status=selesai` (match ke seeding).
- **`KeadaanTurn.domain_gate` berisi LIST KOSONG (`[]`)** — satu-satunya atomic_intent ditahan (sudah py jawaban dari Session Memory).
- **PENTING**: span `domain_gate.identifikasi_semua` TETAP TERBUKA dengan atribut `intent.count=0` — `identifikasi_domain_semua()` SELALU dipanggil terlepas isi `matches` (beda mekanisme dari M7.7, di mana cabang Tarik Memory genuinely TIDAK dipanggil sama sekali saat tidak ada referensi). Span yang tetap ada dengan `intent.count=0` BUKAN indikasi "Domain Gate tidak dipanggil" — itu bukti Domain Gate dipanggil dan BENAR menyaring semuanya.

## Ringkasan Ekspektasi

| ID | Jumlah `matches` | Jumlah `selesai` | Jumlah `perlu_eksekusi` | `domain_gate` panjang | `intent.count` span |
|---|---|---|---|---|---|
| E01 | 3 | 1 | 2 | 2 | 2 |
| E02 | 1 | 0 | 1 | 1 | 1 |
| E03 | 1 | 1 | 0 | 0 | 0 (span tetap ada) |
