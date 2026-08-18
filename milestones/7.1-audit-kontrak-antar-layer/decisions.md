# Decisions — Milestone 7.1: Audit Kontrak Antar-Layer yang Sudah Terimplementasi

Dokumen ini mencatat seluruh keputusan desain untuk Milestone 7.1, ditentukan sebelum implementasi dimulai (Plan Mode).

---

### Keputusan 1: Kriteria "panggilan percobaan nyata" bersifat generik, bukan wajib LLM/`chatbot_api`

**Sumber Paksaan**
Kutipan literal Kriteria Keberhasilan Milestone 7.1 di `docs/02-implementation-plan/rancangan-orkestrasi-api.md`: "Setiap satu dari sembilan layer sudah py setidaknya satu panggilan percobaan nyata (bukan cuma baca kode) yang membuktikan bentuk kontraknya sesuai yang dicatat di dokumen audit." — wording ini tidak membatasi jenis panggilan (LLM vs HTTP vs database), hanya mensyaratkan "nyata, bukan cuma baca kode".

**Keputusan yang Diikuti**
Unit kerja yang secara desain tidak pernah memanggil LLM/`chatbot_api` (mis. M1.2 endpoint HTTP sendiri, M1.5/M2.2/M2.4/M4.3 yang memanggil Supabase) dibuktikan lewat jenis panggilan nyata yang memang relevan dengan kontraknya sendiri (real HTTP request lewat `TestClient`, real query Supabase), bukan dipaksa mencari bukti LLM/`chatbot_api` yang memang tidak relevan untuk unit tersebut.

**Catatan Ketergantungan**
Kalau kriteria ini dipersempit jadi "wajib LLM/`chatbot_api` saja", separuh lebih unit kerja (semua yang murni deterministik) tidak akan pernah bisa lolos syarat ini, padahal kontraknya memang tidak melibatkan LLM/`chatbot_api` sama sekali.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by wording literal Kriteria Keberhasilan sumber.

---

### Keputusan 2: Granularitas audit per "unit kerja" (16 unit), bukan hanya 9 layer

**Sumber Paksaan**
Bagian "Output" Milestone 7.1 di `rancangan-orkestrasi-api.md`: "Dokumen audit singkat... yang mendaftar **tiap unit kerja** beserta kontrak aktualnya dan penyimpangan dari dokumen desain" — kata "unit kerja" dipakai eksplisit (plural), bukan "tiap layer" (9).

**Keputusan yang Diikuti**
Audit mencatat 16 unit kerja nyata (fungsi entry-point per mekanisme, termasuk sub-langkah internal seperti 3 langkah Decomposition atau 2 langkah Domain Gate), bukan hanya merangkum di level 9 layer besar.

**Catatan Ketergantungan**
Granularitas 9-layer akan kehilangan detail penting untuk Level 1 (M7.2-7.5) — mis. nuansa retry Decomposition (bisa sampai 7 pemanggilan LLM) hanya terlihat kalau diaudit di level sub-langkah, bukan di level "Decomposition" sebagai satu blok.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by wording literal Output sumber.

---

### Keputusan 3: Checkpoint diorganisir per grup PIC (1-4)

**Sumber Paksaan**
Preseden struktur project yang sudah ada — `milestones/` dan `docs/02-implementation-plan/rancangan-*.md` sudah dikelompokkan per PIC (PIC 1 = M1.x, PIC 2 = M2.x, dst.), dan prinsip checkpoint independen/rollback-able di `CLAUDE.md` ("Implementasikan per checkpoint").

**Keputusan yang Diikuti**
Checkpoint 2-6 mengaudit satu grup PIC per checkpoint (PIC1, PIC2, PIC3, PIC4-tanpa-`chatbot_api`, PIC4-dengan-`chatbot_api`), karena partisi ini genuinely independen secara verifikasi — audit satu grup PIC tidak bergantung hasil grup PIC lain (wiring antar-layer belum jadi cakupan M7.1).

**Catatan Ketergantungan**
Kalau checkpoint diorganisir dengan cara lain (mis. acak lintas PIC), rollback satu checkpoint yang gagal akan lebih sulit dilacak karena tidak match dengan struktur `milestones/` yang sudah ada sebagai rujukan silang.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden struktur project yang sudah konsisten dipakai sejak Milestone 1.1.

---

### Keputusan 4: Dokumen audit ditulis sebagai file terpisah `audit-kontrak-antar-layer.md`

**Sumber Paksaan**
Wording permisif Output Milestone 7.1: "Dokumen audit singkat (**bisa jadi bagian** `decisions.md` milestone ini)..." — memberi keleluasaan, bukan mewajibkan.

**Keputusan yang Diikuti**
Audit kontrak (inventori 16 unit kerja + tabel ringkasan + daftar penyimpangan) ditulis sebagai file terpisah `audit-kontrak-antar-layer.md`, sementara `decisions.md` ini tetap murni berisi keputusan desain milestone (format Jenis A/Jenis B).

**Catatan Ketergantungan**
Format `decisions.md` (Jenis A "Genuinely Terbuka" / Jenis B "Preseden/Forced") tidak cocok dipaksakan untuk inventori fakta kontrak — memaksakannya akan membuat `decisions.md` sulit dibaca dan audit kontrak sulit dijadikan rujukan cepat oleh M7.2-7.18.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menaruh seluruh audit di dalam `decisions.md`** — ditolak karena mencampur dua jenis konten yang tujuan bacanya beda (keputusan vs katalog fakta), padahal dokumen sumber sendiri permisif dan tidak mewajibkan opsi ini.

---

### Keputusan 5: Panggilan nyata baru memakai infrastruktur test/eval yang sudah ada

**Sumber Paksaan**
Prinsip umum "reuse over new code" (`CLAUDE.md`) dan preseden project — seluruh 15 dari 16 unit kerja sudah py mekanisme test `skipif`-gated (`OPENROUTER_API_KEY`/`DATABASE_URL`) atau `evals/<id>/run_eval.py` yang genuinely memanggil provider/database asli.

**Keputusan yang Diikuti**
Checkpoint 2-5 dan bagian M4.1 di Checkpoint 6 menjalankan ulang test/eval yang sudah ada (dengan env var diaktifkan), bukan menulis script baru dari nol. Pengecualian satu-satunya: M4.2 (`eksekusi_atomic_intent()`) memang belum py infrastruktur real-call sama sekali, sehingga Checkpoint 6 Task 11 membuat test integrasi baru khusus untuk unit ini.

**Catatan Ketergantungan**
Menulis script baru dari nol untuk 15 unit yang sudah py infrastruktur setara akan jadi duplikasi kerja yang tidak perlu dan berisiko drift dari skenario yang sudah divalidasi di milestone aslinya.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menulis script audit baru yang seragam untuk seluruh 16 unit** — ditolak karena mengabaikan infrastruktur skipif-gated/eval yang sudah teruji dan spesifik per unit, menambah kerja tanpa manfaat proporsional.

---

### Keputusan 6: Kekakuan bukti panggilan nyata — jalankan ulang minimal per unit

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`)

**Latar Belakang**
13 dari 16 unit kerja sudah py bukti panggilan nyata tercatat dari milestone aslinya (evals/audit.md, trace_id Jaeger, dll). Genuinely terbuka apakah M7.1 harus (a) menjalankan ulang satu panggilan nyata minimal per unit untuk memastikan kontrak masih valid hari ini, atau (b) cukup mengutip bukti historis yang sudah ada tanpa panggilan baru — tidak ada preseden yang menjawab ini secara eksplisit di dokumen manapun, karena M7.1 adalah milestone audit pertama semacam ini di project.

**Keputusan yang Dipilih**
Opsi (a): jalankan ulang minimal — satu panggilan nyata baru per unit kerja, reuse skenario test/eval yang sudah ada (bukan re-run seluruh suite).

**Alasan**
User menekankan bahwa output M7.1 akan jadi dasar seluruh milestone 7.2-7.18 berikutnya — risiko drift kontrak sejak bukti historis direkam (beberapa sudah beberapa checkpoint yang lalu) lebih mahal untuk dibiarkan daripada biaya tambahan satu panggilan API minimal per unit.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Cukup kutip bukti historis yang sudah ada** — ditolak karena tidak menjamin kontrak belum berubah sejak bukti tsb direkam, padahal M7.1 eksplisit jadi fondasi milestone berikutnya (risiko lebih mahal daripada biaya panggilan tambahan yang minimal).

**Dampak**
Checkpoint 2-6 (Task 4, 6, 8, 10, 11) — semuanya menjalankan minimal satu panggilan nyata baru, bukan hanya mengutip laporan lama.

---

### Keputusan 7: Ketersediaan `chatbot_api` lokal untuk celah M4.2 — checkpoint sebagai percobaan dengan fallback

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`)

**Latar Belakang**
Eksplorasi kode menemukan `eksekusi_atomic_intent()` (M4.2) belum pernah sekali pun dipanggil ke `chatbot_api` sungguhan (seluruh test-nya mock). Menutup celah ini butuh instance `chatbot_api` lokal yang reachable — statusnya tidak pasti hari ini (terakhir konfirmasi reachable 2026-08-17, untuk keperluan lain/M4.1). User belum bisa memastikan ketersediaannya saat plan ditulis.

**Keputusan yang Dipilih**
Checkpoint 6 tetap direncanakan sebagai percobaan nyata (cek ketersediaan saat checkpoint itu mulai dikerjakan). Kalau reachable, tutup celah penuh (real call + test integrasi baru). Kalau tidak, dokumentasikan sebagai keterbatasan diterima baru di `docs/keterbatasan-diterima.md` dengan trigger revisit eksplisit — tidak memblokir penutupan milestone.

**Alasan**
Ketidakpastian ketersediaan adalah fakta eksternal yang tidak bisa diputuskan di titik plan ditulis; menunda keputusan konkret sampai checkpoint itu mulai (bukan memaksa keputusan sekarang) adalah pendekatan paling pragmatis, konsisten dengan preseden project yang sudah pernah mendokumentasikan status serupa untuk M4.1/M4.2 Checkpoint 7.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Wajib berhasil menutup celah sekarang (blocking)** — ditolak karena bergantung pada ketersediaan infrastruktur eksternal yang tidak terjamin, berisiko memblokir seluruh penutupan milestone tanpa alasan yang proporsional terhadap satu celah spesifik.
- **Langsung terima sebagai keterbatasan tanpa dicoba** — ditolak karena tidak menghormati kemungkinan `chatbot_api` memang reachable saat checkpoint itu dikerjakan; mencoba dulu adalah langkah berbiaya rendah sebelum jatuh ke fallback.

**Dampak**
Checkpoint 6 (Task 11-12) — hasil bergantung kondisi nyata saat checkpoint dikerjakan; `docs/keterbatasan-diterima.md` berpotensi bertambah satu entri baru kalau fallback terpicu.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Kriteria "panggilan percobaan nyata" bersifat generik | B | Plan |
| 2 | Granularitas audit per unit kerja (16 unit) | B | Plan |
| 3 | Checkpoint diorganisir per grup PIC | B | Plan |
| 4 | Dokumen audit sebagai file terpisah `audit-kontrak-antar-layer.md` | B | Plan |
| 5 | Panggilan nyata baru memakai infrastruktur test/eval yang sudah ada | B | Plan |
| 6 | Kekakuan bukti panggilan nyata — jalankan ulang minimal per unit | A | Plan |
| 7 | Ketersediaan `chatbot_api` lokal untuk celah M4.2 — percobaan dengan fallback | A | Plan / Checkpoint 6 |
