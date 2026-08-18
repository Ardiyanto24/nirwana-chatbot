# Decisions — Milestone 7.8: Sambungan 3 (Rewrite → Decomposition)

Dokumen ini mencatat keputusan desain untuk Milestone 7.8, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Metodologi pembuktian KK — folder `evals/` penuh, bukan cukup test connectivity di `tests/orchestration/`

**Status:** Diputuskan sebelum implementasi (dari plan), dikonfirmasi lewat `AskUserQuestion`.

**Latar Belakang**
KK M7.8 murni soal KONTEN ("pemecahan atomik yang konsisten dengan makna kalimat mandiri itu, bukan makna kalimat asli sebelum di-rewrite") — TIDAK menyebut span/`parent_span_id` sama sekali, beda tegas dari KK M7.6/M7.7 yang eksplisit menuntut bukti span. Preseden Level 1 (M7.2-M7.5) membuktikan KK serupa (soal konten/nilai yang mengalir, bukan struktur span) cukup lewat test connectivity ber-LLM nyata di `tests/`, tanpa folder `evals/`. Ini genuinely terbuka — tidak ada dokumen yang memaksa satu jawaban tunggal soal struktur pengujian mana yang dipakai untuk kombinasi "butuh LLM nyata TAPI tidak butuh bukti span" ini, kombinasi yang belum pernah muncul persis di milestone Level 2 sebelumnya (M7.6/M7.7 selalu butuh keduanya sekaligus).

**Keputusan yang Dipilih**
Tetap membangun folder `evals/7.8-sambungan-rewrite-decomposition/` penuh (`rancangan.md` → `run_eval.py` → `payloads/` → `audit.md`), mirror struktur M7.6/M7.7 — dengan penyesuaian: verdict utama berbasis kecocokan konten (`required_phrases`/`forbidden_phrases`, format `evals/1.4-rewrite-mandiri/`), bukti span jadi konfirmasi sekunder (bukan syarat kelulusan).

**Alasan**
Konsistensi struktur pengujian di seluruh milestone Level 2 (Sambungan 1-11) — folder `evals/` per Sambungan jadi pola yang bisa diandalkan pembaca mana pun tanpa perlu ingat KK persis milestone mana yang butuh span dan mana yang tidak. Trade-off (kerja tambahan dibanding cukup test di `tests/`) diterima demi keseragaman format dokumentasi Level 2.

**Alasan (dari user)**
User memilih opsi ini secara eksplisit lewat `AskUserQuestion`, dipresentasikan dua opsi dengan trade-off jelas (test connectivity ringkas vs folder `evals/` penuh demi konsistensi).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Test connectivity di `tests/orchestration/` saja (mirror pola Level 1 M7.2-M7.5)** — lebih ringkas, tidak butuh Jaeger/docker karena KK tidak memintanya secara literal. Ditolak karena user memilih konsistensi struktur Level 2 di atas efisiensi per-KK.

**Dampak**
Menetapkan preseden: milestone Sambungan Level 2 berikutnya (M7.9-7.16) default memakai folder `evals/`, terlepas dari apakah KK masing-masing menuntut bukti span atau tidak — kecuali user secara eksplisit memutuskan lain untuk milestone tertentu.

---

### Keputusan 2: `decompose_question()` dipanggil dengan `rewrite_result.rewritten_question`, bukan `payload.question` asli

**Sumber Paksaan**
Lingkup M7.8 (`rancangan-orkestrasi-api.md`): "Output Rewrite (kalimat mandiri) benar-benar jadi input Decomposition". KK M7.8 eksplisit: "...bukan makna kalimat asli sebelum di-rewrite."

**Keputusan yang Diikuti**
`decomposition_result = decompose_question(rewrite_result.rewritten_question)` di `proses_turn()`.

**Catatan Ketergantungan**
Kalau `payload.question` (bukan hasil rewrite) yang dipakai, milestone ini gagal memenuhi definisi Lingkup/KK-nya sendiri — bukan lagi "Rewrite → Decomposition" tapi "Input Layer → Decomposition" yang melewati Rewrite sama sekali.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by Lingkup+KK M7.8 sendiri secara literal.

---

### Keputusan 3: Dipanggil sekuensial setelah blok `ThreadPoolExecutor` selesai, bukan cabang paralel baru

**Sumber Paksaan**
Lingkup+KK M7.8 tidak menyebut kebutuhan paralel apa pun (beda tegas dari M7.7). Decomposition genuinely bergantung data pada hasil Rewrite (data dependency searah — Decomposition butuh `rewrite_result` sudah final sebelum bisa mulai), bukan pada Tarik Memory. Prinsip `CLAUDE.md` "Don't add features... beyond what the task requires" (YAGNI).

**Keputusan yang Diikuti**
`decompose_question()` dipanggil di thread utama, sekuensial, setelah `with ThreadPoolExecutor(...)` selesai dan `rewrite_result` final — bukan disisipkan sebagai worker ketiga ke `ThreadPoolExecutor` yang sama.

**Catatan Ketergantungan**
Memaksakan paralelisme di sini (mis. menjalankan Decomposition bersamaan dengan Tarik Memory, dua-duanya independen dari satu sama lain) menambah kompleksitas (executor 3-worker, propagasi context tambahan) yang tidak diminta KK M7.8 manapun — M7.9 (Sambungan 4) yang nanti menggabungkan kedua hasil ini di titik Pencocokan, bukan tanggung jawab M7.8.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menjalankan Decomposition paralel dengan Tarik Memory (keduanya independen)** — secara arsitektur mungkin valid untuk milestone jauh ke depan, tapi ditolak di sini karena tidak diminta Lingkup/KK M7.8 dan melanggar prinsip tidak menambah fitur di luar yang diminta task.

---

### Keputusan 4: Field `KeadaanTurn.decomposition: DecompositionResult` non-Optional, tanpa default

**Sumber Paksaan**
Dibaca langsung ketiga sub-langkah `decompose_question()` (`klasifikasi_kebutuhan`, `pecah_atomik`, `verifikasi_pemecahan` di `src/layers/decomposition/`): seluruhnya py `try/except APIError` dengan fallback penuh (`_FALLBACK`/`_fallback_result()`), termasuk fallback saat parse JSON/enum gagal — `decompose_question()` TIDAK PERNAH raise ke pemanggilnya. Preseden identik field `rewrite: RewriteResult` (M7.7 Keputusan 3, `rewrite_to_standalone()` juga py fallback penuh).

**Keputusan yang Diikuti**
`decomposition: DecompositionResult` (wajib, tanpa `| None`, tanpa default) di `KeadaanTurn`.

**Catatan Ketergantungan**
Kalau field ini dibuat `Optional`, itu menyiratkan ada kondisi di mana Decomposition genuinely tidak terpanggil/gagal total — klaim yang tidak didukung bukti kode (fallback penuh di tiap sub-langkah membuat itu mustahil terjadi via jalur normal).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by bukti langsung kode `decompose_question()` + preseden field `rewrite`.

---

### Keputusan 5: Tidak merefactor/mengubah logic internal `decompose_question()`

**Sumber Paksaan**
"Tidak termasuk" `rancangan-orkestrasi-api.md` — logic internal 9 layer tidak dirombak ulang di M7.x. Preseden identik `milestones/7.2-menyambungkan-decomposition/decisions.md` Keputusan 1 ("kode yang sudah bekerja dan teruji tidak boleh diubah tanpa alasan bug").

**Keputusan yang Diikuti**
`decompose_question()`, `klasifikasi_kebutuhan()`, `pecah_atomik()`, `verifikasi_pemecahan()` dipakai apa adanya, tanpa modifikasi.

**Catatan Ketergantungan**
Kode ini sudah diverifikasi bekerja benar dan teruji sejak M1.6/M7.2 — mengubahnya di M7.8 berisiko meregresi milestone yang sudah closed tanpa alasan bug yang valid.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by batasan dokumen sumber + preseden M7.2.

---

### Keputusan 6: 3 test existing di `tests/orchestration/test_turn_pipeline.py` ditambah mock `decompose_question`

**Sumber Paksaan**
Docstring file itu sendiri: "Cakupan SEMPIT... hanya kejadian yang TIDAK butuh LLM/DB/Jaeger nyata" (preseden M7.6 Keputusan 8, dipertahankan M7.7 Keputusan 7). Begitu `proses_turn()` memanggil `decompose_question()` sungguhan (M7.8), ketiga test lama (yang tidak memock fungsi ini) akan memicu panggilan LLM nyata tanpa disadari — melanggar kontrak cakupan file itu sendiri. Preseden identik: M7.7 Checkpoint 4 menambah mock `rewrite_to_standalone` ke test wiring M7.6 yang sudah ada, dengan alasan sama persis.

**Keputusan yang Diikuti**
`test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil`, `test_orkestrator_wiring_keadaan_turn_berisi_objek_identik`, dan `test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai` masing-masing ditambah `monkeypatch.setattr(turn_pipeline_module, "decompose_question", ...)` dengan `DecompositionResult` dummy.

**Catatan Ketergantungan**
Tanpa perubahan ini, test suite yang seharusnya cepat/deterministik diam-diam jadi bergantung jaringan+API key, berisiko flaky/lambat tanpa terlihat dari nama test-nya.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by docstring cakupan file + preseden M7.7 Checkpoint 4.

---

### Keputusan 7: Test wiring baru (mocked, spy) khusus membuktikan argumen yang diterima `decompose_question`

**Sumber Paksaan**
Pola pembuktian connectivity-spesifik yang konsisten dipakai M7.2-M7.5 dan M7.7 (Keputusan test M7.7 CP4) — bukti "hasil akhir benar" saja tidak cukup untuk klaim connectivity; wajib ada bukti nilai spesifik di titik sambung (argumen yang benar-benar diterima fungsi tujuan).

**Keputusan yang Diikuti**
Test baru dengan payload+rewrite dummy yang teksnya SENGAJA berbeda dari `payload.question` (supaya kalau kode keliru memakai `payload.question` alih-alih `rewrite_result.rewritten_question`, test gagal jelas, bukan kebetulan lolos karena teks sama) — spy merekam argumen yang diterima `decompose_question`, assert argumen tersebut adalah `rewrite_result.rewritten_question`, DAN `KeadaanTurn.decomposition` adalah objek identik (`is`) hasil mock.

**Catatan Ketergantungan**
Tanpa test ini, klaim inti M7.8 ("Rewrite → Decomposition", bukan "Input Layer → Decomposition") tidak punya bukti deterministik sama sekali — hanya bergantung pada eval real-execution (Checkpoint 5) yang lebih lambat dan tidak dijalankan tiap kali test suite jalan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Cukup assert `KeadaanTurn.decomposition` terisi (tanpa spy argumen)** — ditolak karena tidak membuktikan APA yang dikirim ke Decomposition, hanya bahwa sesuatu dipanggil — celah yang sama yang mendorong preseden spy M7.2 Keputusan 2.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Metodologi pembuktian KK: folder `evals/` penuh | A | Plan |
| 2 | `decompose_question()` dipanggil dengan `rewrite_result.rewritten_question` | B | Plan |
| 3 | Dipanggil sekuensial, bukan cabang paralel baru | B | Plan |
| 4 | Field `KeadaanTurn.decomposition` non-Optional | B | Plan |
| 5 | Tidak merefactor `decompose_question()` internal | B | Plan |
| 6 | 3 test existing ditambah mock `decompose_question` | B | Plan |
| 7 | Test wiring baru spy argumen `rewritten_question` | B | Plan |
