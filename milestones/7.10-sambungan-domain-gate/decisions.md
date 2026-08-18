# Decisions — Milestone 7.10: Sambungan 5 (Pencocokan (jalur "perlu eksekusi") → Domain Gate)

Dokumen ini mencatat keputusan desain untuk Milestone 7.10, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: `identifikasi_domain_semua()` dipanggil dengan `matches` apa adanya, tanpa konversi

**Sumber Paksaan**
`identifikasi_domain_semua(matches: list[AtomicIntentMatch]) -> list[AtomicIntentDomains]` (`src/layers/domain_gate/domain_gate.py`, M2.1) sudah menerima `list[AtomicIntentMatch]` langsung sesuai bentuk output M7.9 — filter ke `status=PERLU_EKSEKUSI` adalah tanggung jawab INTERNAL fungsi ini sendiri (docstring modul eksplisit menyebutnya, sudah diuji nyata sejak M2.1). `KeadaanTurn.matches` (M7.9) sudah `list[AtomicIntentMatch]` non-Optional — beda dari M7.9 (yang butuh konversi `session_memory or []`), tidak ada konversi yang dibutuhkan di sini.

**Keputusan yang Diikuti**
`domain_gate_result = identifikasi_domain_semua(matches)` di `proses_turn()`, `matches` diteruskan utuh tanpa filter/transformasi apa pun oleh orkestrator.

**Catatan Ketergantungan**
Kalau orkestrator ikut memfilter `matches` sebelum memanggil (mis. `[m for m in matches if m.status == PERLU_EKSEKUSI]`), itu DUPLIKASI logic yang sudah ada di `identifikasi_domain_semua()` sendiri — melanggar "Tidak termasuk" (logic internal tidak dirombak/diduplikasi) dan berisiko dua tempat filter bisa divergen di masa depan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Orkestrator memfilter `matches` ke `PERLU_EKSEKUSI` sebelum memanggil `identifikasi_domain_semua()`** — ditolak karena duplikasi logic filter yang sudah ada dan teruji di M2.1, tidak ada alasan valid untuk memindahkan tanggung jawab itu ke orkestrator.

---

### Keputusan 2: Dipanggil sekuensial setelah `matches` (M7.9) final, bukan paralel baru

**Sumber Paksaan**
Domain Gate genuinely butuh `matches` (output Pencocokan M7.9) sebagai argumen — data dependency searah. Lingkup/KK M7.10 tidak menyebut kebutuhan paralelisme baru. Preseden identik M7.9 Keputusan 2, M7.8 Keputusan 3 (YAGNI).

**Keputusan yang Diikuti**
`identifikasi_domain_semua()` dipanggil di thread utama, sekuensial, setelah `matches` final.

**Catatan Ketergantungan**
Memaksakan paralelisme di sini tidak mungkin secara logis (Domain Gate butuh OUTPUT Pencocokan sebagai argumen).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced oleh data dependency struktural.

---

### Keputusan 3: Field `KeadaanTurn.domain_gate: list[AtomicIntentDomains]` non-Optional, tanpa try/except baru

**Sumber Paksaan**
Dibaca langsung `identifikasi_domain_atomic_intent()` (dipanggil per intent oleh `identifikasi_domain_semua()`): `identifikasi_domain()` dan `verifikasi_titik_buta()` (M2.1) keduanya py `try/except APIError` dengan fallback (`gagal=True`) — kegagalan diterjemahkan jadi `status=GAGAL_TEKNIS`/`SEBAGIAN` pada `AtomicIntentDomains`, BUKAN exception yang menjalar. `identifikasi_domain_semua()` karena itu TIDAK PERNAH raise — beda dari `matches` (M7.9, yang bisa raise karena arsip DB lewat `store_session_memory()`).

**Keputusan yang Diikuti**
`domain_gate: list[AtomicIntentDomains]` (wajib, tanpa default) di `KeadaanTurn`, mirror pola `rewrite`/`decomposition` (M7.7/M7.8) — TIDAK dibungkus try/except baru di `proses_turn()`.

**Catatan Ketergantungan**
Panjang list `domain_gate` BISA lebih kecil dari `matches`/`decomposition.atomic_intents` (entri `status=selesai` difilter) — bukan indikasi kegagalan, murni desain filter yang diminta Lingkup M7.10 sendiri.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by bukti langsung kode `identifikasi_domain_semua()`/sub-fungsinya.

---

### Keputusan 4: Tidak merefactor/mengubah logic internal `identifikasi_domain_semua()`/sub-fungsinya

**Sumber Paksaan**
"Tidak termasuk" `rancangan-orkestrasi-api.md` — logic internal 9 layer tidak dirombak ulang di M7.x. Preseden identik M7.2/M7.3/M7.8/M7.9.

**Keputusan yang Diikuti**
`identifikasi_domain_semua()`, `identifikasi_domain_atomic_intent()`, `identifikasi_domain()`, `verifikasi_titik_buta()` dipakai apa adanya, tanpa modifikasi.

**Catatan Ketergantungan**
Kode ini sudah diverifikasi bekerja benar dan teruji sejak M2.1 (termasuk filter status yang PERSIS diminta Lingkup M7.10) — mengubahnya di M7.10 berisiko meregresi milestone yang sudah closed tanpa alasan bug yang valid.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by batasan dokumen sumber + preseden M7.2/M7.3/M7.8/M7.9.

---

### Keputusan 5: Folder `evals/7.10-.../` dengan 3 kejadian, verdict primer berbasis atribut span `intent.count`

**Sumber Paksaan**
Preseden default Level 2 sejak M7.8 Keputusan 1 (folder `evals/` penuh terlepas sifat KK). Span `domain_gate.identifikasi_semua` (tracer `domain_gate.domain_gate`) SUDAH mencatat atribut `intent.count` langsung di kode M2.1 — KK M7.10 ("dibuktikan lewat span yang menunjukkan Domain Gate hanya menerima jumlah atomic intent yang sesuai") bisa dicek LANGSUNG lewat atribut ini, tidak perlu teknik hitung child-span lewat relasi parent seperti M7.9 (yang terpaksa dipakai karena span Pencocokan M1.7 tidak py atribut count eksplisit yang identik).

**Keputusan yang Diikuti**
3 kejadian (E01 campuran/utama, E02 semua `perlu_eksekusi`, E03 semua `selesai`) — mencakup kombinasi bermakna ruang kejadian filter status (lebih sederhana dari M7.9 karena Domain Gate hanya py SATU filter kondisi, bukan multi-dimensi seperti titik pertemuan M7.9). Verdict primer: `intent.count` dari span + panjang `KeadaanTurn.domain_gate`.

**Catatan Ketergantungan**
E03 (`domain_gate=[]`) berisiko disalahartikan sebagai "Domain Gate tidak dipanggil sama sekali" kalau span tidak dicek — `identifikasi_domain_semua()` SELALU membuka span `domain_gate.identifikasi_semua` terlepas isi `matches` (beda dari M7.7 di mana cabang Tarik Memory genuinely skip). `rancangan.md`/`audit.md` wajib menegaskan ini eksplisit.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Cukup 1 kejadian (campuran saja)** — ditolak karena tidak membuktikan batas kedua sisi (semua-perlu vs semua-selesai), terutama E03 yang py risiko kesalahpahaman mekanisme (span tetap ada vs span hilang) yang perlu dibuktikan eksplisit.

---

### Keputusan 6: Kejadian utama (E01) reuse payload+seeding `evals/7.9-.../E06`, dengan `session_id` baru

**Sumber Paksaan**
Skenario "campuran dua status" PERSIS yang diminta KK M7.10 SUDAH pernah tereproduksi nyata di `evals/7.9-sambungan-pencocokan/payloads/E06.json` (1 `selesai` + 2 `perlu_eksekusi` dari 3 atomic_intent, hasil Decomposition majemuk_bergantung nyata). Preseden reuse skenario existing sudah dipakai M7.3 (`gop_margin`), M7.4/M7.5 (skenario mismatch/klaim-kausal), M7.8/M7.9 (skenario elipsis M1.4).

**Keputusan yang Diikuti**
E01 M7.10 memakai payload+seeding IDENTIK M7.9 E06 (pertanyaan "Bandingkan dengan occupancy satu tahun sebelumnya.", seeding occupancy April 2026 `status=berhasil`), TAPI dengan `session_id="eval-7.10-e01"` BARU (bukan `eval-7.9-e06`) supaya tidak bentrok/campur dengan data M7.9 yang sudah tersimpan permanen di Supabase.

**Catatan Ketergantungan**
Memakai `session_id` yang sama akan membuat `retrieve_session_memory()` membaca baris LAMA dari run M7.9 sebelumnya (kalau ada sisa), bukan seeding baru yang genuinely dikontrol run M7.10 ini — berisiko hasil tidak reproducible/tidak murni dari eksekusi M7.10.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menyusun skenario campuran baru dari nol** — ditolak karena tidak efisien, skenario yang sudah terbukti bekerja (menghasilkan majemuk_bergantung dengan hasil match campuran) sudah tersedia dan reusable.

---

### Keputusan 7: 3 test existing di `tests/orchestration/test_turn_pipeline.py` ditambah mock `identifikasi_domain_semua`

**Sumber Paksaan**
Docstring file itu sendiri: "Cakupan SEMPIT... hanya kejadian yang TIDAK butuh LLM/DB/Jaeger nyata" (preseden M7.6-M7.9). Begitu `proses_turn()` memanggil `identifikasi_domain_semua()` sungguhan (M7.10), ketiga test lama akan memicu panggilan LLM nyata tanpa disadari.

**Keputusan yang Diikuti**
Ketiga test existing ditambah `monkeypatch.setattr(turn_pipeline_module, "identifikasi_domain_semua", lambda *a, **k: [])`.

**Catatan Ketergantungan**
Tanpa perubahan ini, test suite yang seharusnya cepat/deterministik diam-diam jadi bergantung jaringan+API key — pola kegagalan PERSIS yang ditemukan+diperbaiki di M7.9 Checkpoint 3 (lupa mock, 47.66s tanpa disadari).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by docstring cakupan file + preseden M7.7/M7.8/M7.9.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | `identifikasi_domain_semua()` dipanggil dengan `matches` apa adanya | B | Plan |
| 2 | Dipanggil sekuensial, bukan paralel baru | B | Plan |
| 3 | Field `domain_gate` non-Optional, tanpa try/except baru | B | Plan |
| 4 | Tidak merefactor `identifikasi_domain_semua()` internal | B | Plan |
| 5 | Folder `evals/` dengan 3 kejadian, verdict via atribut `intent.count` | B | Plan |
| 6 | E01 reuse payload+seeding M7.9 E06, `session_id` baru | B | Plan |
| 7 | 3 test existing ditambah mock `identifikasi_domain_semua` | B | Plan |
