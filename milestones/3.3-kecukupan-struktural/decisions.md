# Decisions — Milestone 3.3: Pemeriksaan Kecukupan Struktural

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 3.3 — langkah **penutup** tiga langkah Retriever (PIC 3), mencocokkan `label_bentuk_jawaban` (M1.6) terhadap grain kandidat `view_name` yang sudah dinyatakan cocok maknanya di Milestone 3.2, lalu memfinalkan SATU `view_name`.

---

## Keputusan 1: Mekanisme Evaluasi Kecukupan Struktural — Hybrid (Deterministik + Fallback LLM Konservatif)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
`rancangan-retrieval-query.md` Milestone 3.3 tidak mengunci mekanisme teknis — hanya menyiratkan "bisa dilakukan sebagai pencocokan yang jauh lebih terstruktur" dibanding rancangan lama, bukan wajib nol-LLM. Kontrak observability (`rancangan-observability-ai-chatbot.md` Bagian 2) hanya mencantumkan SATU baris `chat` untuk seluruh Retriever (milik M3.2) — sinyal tambahan tapi bukan kontrak literal yang melarang M3.3 menyentuh LLM sama sekali. Genuinely terbuka.

**Proses**
Tiga alternatif diajukan lewat `AskUserQuestion`, dengan penjelasan detail kelebihan/kekurangan per opsi atas permintaan eksplisit user sebelum menjawab: (A) Deterministik terstruktur murni — taksonomi grain 67 view dibangun sekali (mirror kurasi manual 9-view M2.3), aturan tetap Python, span non-LLM, direkomendasikan penulis; (B) LLM tunggal — satu panggilan chat per kebutuhan atomik menilai cukup/tidak langsung dari teks grain; (C) Hybrid — deterministik untuk kasus jelas, LLM hanya untuk kasus ambigu residual.

**Keputusan yang Dipilih**
Hybrid (Opsi C) — mekanisme dua tingkat mirror pola BM25→embedding fallback M3.1 sendiri: rule table deterministik tri-state (`ya`/`tidak`/`tidak_pasti`) sebagai jalur utama; SATU panggilan LLM konservatif (bukan generate-verify penuh) HANYA untuk kandidat yang rule table-nya menghasilkan `tidak_pasti`, dibatch per kebutuhan atomik.

**Alasan**
User secara eksplisit menolak deterministik-murni (Opsi A, rekomendasi awal penulis) dengan argumen forward-looking: taksonomi `label_bentuk_jawaban` (5 nilai sekarang — `nilai_tunggal`/`tren`/`perbandingan`/`peringkat`/`komposisi`) diperkirakan akan bertambah dan makin kompleks ke depan. Deterministik-murni tidak akan scale ke bentuk jawaban kompleks masa depan (tiap label baru butuh aturan Python baru yang mungkin tidak bisa ditulis sebagai ruang kesalahan tertutup), sementara LLM-murni (Opsi B) dinilai over-engineering untuk kasus-kasus yang sebenarnya sudah pasti jawabannya sekarang (mis. `nilai_tunggal` selalu cukup apa pun grain-nya). Hybrid memberi kecepatan+determinisme Opsi A untuk mayoritas kasus jelas, sekaligus jalur aman ke Opsi B untuk kasus ambigu atau label yang belum dikenal — genuinely forward-compatible.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Deterministik terstruktur murni (Opsi A)** — direkomendasikan penulis (gratis, instan, 100% konsisten, selaras sinyal kontrak observability), ditolak user karena tidak scale ke taksonomi `label_bentuk_jawaban` yang akan bertambah kompleks ke depan.
- **LLM tunggal murni (Opsi B)** — dipertimbangkan (paling robust untuk kasus ambigu, tidak perlu klasifikasi grain di depan), ditolak karena menambah panggilan LLM ketiga di layer Retriever untuk kasus-kasus yang sebenarnya sudah pasti jawabannya secara struktural (mis. `nilai_tunggal`), over-engineering dan menyimpang dari sinyal dokumen sumber yang menyiratkan langkah ini seharusnya LEBIH sederhana dari rancangan lama.

---

## Keputusan 2: Aturan Tie-Break `view_name_final` — Label M3.2 Dulu, Baru Skor M3.1

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Tidak ada dokumen manapun yang mengatur cara memilih SATU `view_name_final` kalau lebih dari satu kandidat sama-sama dinyatakan cukup secara struktural — genuinely terbuka, padahal `retrieval.selected_view` (field tunggal) dan Milestone 3.4 sama-sama butuh satu nama view pasti.

**Proses**
Dua alternatif diajukan lewat `AskUserQuestion`, dengan penjelasan detail latar belakang atas permintaan eksplisit user: (A) Prioritaskan label M3.2 `DITEMUKAN` di atas `SEBAGIAN`, lalu di antara kandidat berlabel sama pilih skor `KandidatView` (M3.1, BM25/cosine) tertinggi; (B) pilih kandidat cukup PERTAMA menurut urutan asli hasil M3.1, tanpa mempertimbangkan label M3.2 secara terpisah.

**Keputusan yang Dipilih**
Opsi A — label M3.2 dulu, baru skor M3.1 sebagai tie-break sekunder.

**Alasan**
User sepakat dengan rekomendasi: sinyal "makna cocok" dari M3.2 (hasil generate+verifikasi independen dua langkah, `chat` ×2) lebih dipercaya daripada sinyal "seberapa mirip kata-katanya" dari pencarian leksikal/embedding M3.1 (murni skor kemiripan tanpa penalaran). Mengabaikan sinyal M3.2 demi skor pencarian mentah akan mengecilkan manfaat investasi mekanisme generate+verify M3.2 yang cukup mahal.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Urutan asli hasil M3.1 (Opsi B)** — lebih sederhana, tapi ditolak karena berisiko memilih kandidat "sebagian" (meragukan) walau ada kandidat "ditemukan" (meyakinkan) lain yang skor pencariannya kebetulan lebih rendah.

---

## Keputusan 3: Konsumsi `HasilKecocokanMakna` (M3.2) Langsung, Filter ke Label `ditemukan`/`sebagian`

**Sumber Paksaan**
Preseden konsisten seluruh pipeline (tiap layer menerima tipe keluaran layer sebelumnya secara langsung, mis. M3.2 menerima `HasilPencarianKandidat` dari M3.1) dikombinasikan semantik 3-label M3.2 sendiri.

**Keputusan yang Diikuti**
M3.3 menerima `HasilKecocokanMakna` (M3.2) sebagai input. Kandidat yang dievaluasi strukturnya = label `ditemukan` ATAU `sebagian`; `tidak_ditemukan` di-exclude (sudah final gagal di M3.2, tidak relevan dicek strukturnya).

**Catatan Ketergantungan**
`sebagian` berarti "mungkin cocok, ada catatan" — meng-exclude-nya dari evaluasi struktural akan meniadakan tujuan label itu ada di M3.2.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hanya evaluasi kandidat berlabel `ditemukan`** — ditolak, bertentangan dengan semantik `sebagian` M3.2 yang secara eksplisit dirancang sebagai "masih mungkin cocok", bukan setara gagal.

---

## Keputusan 4: Refactor Span M3.1 — Ekstraksi Logic Murni + Orkestrator Penutup Membuka Span Bernama Sama

**Sumber Paksaan**
Kriteria Keberhasilan sumber #3 eksplisit: *"Atribut `retrieval.selected_view` pada span Milestone 3.1 terisi... terlihat konsisten saat trace ditelusuri di Jaeger/Grafana"* — literal span M3.1 (`retriever.cari_kandidat_view`), bukan span baru. Dikombinasikan batasan teknis OpenTelemetry SDK: `set_attribute()` pada span yang sudah `end()` adalah no-op — span M3.1 sudah tertutup begitu `cari_kandidat_view()` return, jauh sebelum M3.3 selesai menentukan `view_name_final`.

**Keputusan yang Diikuti**
Ekstrak logic murni M3.1 (`_kumpulkan_kandidat()`, tanpa span) dari isi `cari_kandidat_view()`. Fungsi publik `cari_kandidat_view()` standalone (dipakai M3.1 sendiri/test M3.1) TETAP tidak berubah perilaku/signature/nama span/atribut sama sekali (regresi penuh wajib hijau tanpa perubahan assertion — Checkpoint 9). Orkestrator BARU M3.3 (`proses_retrieval_atomic_intent()`, Checkpoint 10) membuka span **bernama sama** `retriever.cari_kandidat_view` yang membungkus `_kumpulkan_kandidat()` (M3.1 pure) → `nilai_kecocokan_makna_atomic_intent()` (M3.2) → evaluasi kecukupan struktural (M3.3) sekaligus — `retrieval.selected_view` diisi di situ sebelum span ditutup.

**Catatan Ketergantungan**
Menyentuh kode M3.1 yang sudah shipped+tested — diisolasi checkpoint sendiri (Checkpoint 9) dengan regresi penuh wajib sebelum Checkpoint 10 apa pun bergantung padanya, mirror preseden M3.1 Checkpoint 2 (menyentuh kode M2.4 shipped dengan aman).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Span M3.3 terpisah (child/sibling span baru), berkorelasi lewat trace_id saja** — ditolak, tidak menyentuh kode M3.1 sama sekali (nol risiko regresi), tapi menyimpang dari kalimat literal KK3 sumber ("span Milestone 3.1" secara spesifik, bukan "sebuah" span dalam trace yang sama).
- **`cari_kandidat_view()` diubah return `(hasil, span)` agar caller mengendalikan `span.end()` manual** — dipertimbangkan, ditolak karena manajemen lifecycle span manual (bukan context manager `with`) rawan span bocor kalau ada exception di antara pemanggilan M3.1 dan M3.3.

---

## Keputusan 5: Fallback LLM — SATU Panggilan Konservatif, Bukan Generate-Verify Penuh

**Sumber Paksaan**
Prinsip asimetri risiko (mirror M1.7, BUKAN M3.2 yang risikonya simetris) + prinsip "kejujuran terhadap keterbatasan" (`CLAUDE.md`).

**Keputusan yang Diikuti**
`_evaluasi_llm_fallback()` adalah SATU panggilan LLM (bukan generate+verifikator independen kedua seperti M3.2). Default aman kalau gagal teknis/respons anomali: kandidat itu `cukup=False` (bukan memblokir seluruh evaluasi kebutuhan atomik).

**Alasan**
Risiko di titik ini asimetris: salah bilang "tidak cukup" itu aman/jujur (kandidat lain masih dicoba, atau hasil akhir jujur menyatakan tidak ada yang cukup), sedangkan salah bilang "cukup" itu berbahaya (mengirim view berbentuk salah ke M3.4/Execution, berpotensi menghasilkan jawaban menyesatkan). Karena arah aman tunggal jelas ada (mirror M1.7: satu panggilan konservatif + fallback aman cukup, tanpa verifier independen kedua), verifikasi independen kedua (pola M3.2) tidak diperlukan di sini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Generate + verifikator independen kedua (pola M3.2)** — ditolak, justifikasi M3.2 (risiko simetris, KK1 dan KK2 sama-sama penting) tidak berlaku di sini; menambah panggilan LLM keempat di Retriever tanpa dasar risiko yang sama.

---

## Keputusan 6: Rule Table Deterministik Fail-Safe ke `tidak_pasti` untuk Label Tak Dikenal

**Sumber Paksaan**
Rasional eksplisit user di Keputusan 1 (taksonomi `label_bentuk_jawaban` akan bertambah ke depan) + `docs/keterbatasan-diterima.md` #4 (M1.6) yang sudah mencatat gap taksonomi 5-label ini duluan.

**Keputusan yang Diikuti**
`_evaluasi_deterministik()` mengembalikan `tidak_pasti` (bukan exception atau tebakan `cukup`/`tidak_cukup`) untuk `label_bentuk_jawaban` yang tidak dikenali rule table — otomatis dilempar ke jalur fallback LLM.

**Catatan Ketergantungan**
Ini yang membuat mekanisme hybrid genuinely forward-compatible: kalau taksonomi `label_bentuk_jawaban` bertambah di masa depan (mis. milestone lanjutan menambah nilai baru), M3.3 tidak perlu diubah kodenya untuk tetap berfungsi aman — otomatis lewat jalur LLM sampai rule table diperbarui eksplisit.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced langsung dari rasional user memilih hybrid di Keputusan 1; menolak fail-safe ini sama saja membatalkan alasan hybrid dipilih.

---

## Keputusan 7: Batching LLM Fallback per Kebutuhan Atomik

**Sumber Paksaan**
Preseden M3.2 Keputusan 2 (granularitas batch per kebutuhan atomik, bukan per kandidat).

**Keputusan yang Diikuti**
`_evaluasi_llm_fallback()` menerima SEMUA kandidat `tidak_pasti` satu kebutuhan atomik sekaligus dalam satu panggilan, bukan satu panggilan per kandidat.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu panggilan per kandidat tidak_pasti** — ditolak, mengalikan jumlah panggilan LLM sesuai jumlah kandidat ambigu, menambah latensi di jalur eksekusi nyata tanpa manfaat proporsional (alasan sama persis M3.2 Keputusan 2).

---

## Keputusan 8: Nama Span LLM Fallback Literal `"chat"`, Kondisional

**Sumber Paksaan**
Kontrak observability (pola sama M1.7/M2.1/M2.3/M3.2 — pemanggilan `chat` sungguhan memakai nama literal `"chat"`) dikombinasikan preseden span kondisional M3.1 (`retriever.pencarian_embedding_fallback` hanya muncul saat fallback embedding terpicu).

**Keputusan yang Diikuti**
Span `"chat"` untuk `_evaluasi_llm_fallback()` HANYA dibuka kalau ada minimal satu kandidat `tidak_pasti` di kebutuhan atomik itu (mirror pola M3.1 embedding fallback).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced kontrak observability + preseden kondisional M3.1.

---

## Keputusan 9: `HasilKecukupanStruktural.status` Selalu `BERHASIL`

**Sumber Paksaan**
Karakteristik mekanisme hybrid M3.3: jalur deterministik tidak mungkin gagal teknis (murni Python, tanpa network call), dan kegagalan LLM fallback diserap sebagai default aman per-kandidat (`cukup=False`, Keputusan 5) — tidak pernah dipropagasi jadi status gagal di level kebutuhan-atomik.

**Keputusan yang Diikuti**
`HasilKecukupanStruktural.status` divalidasi wajib `StatusEksekusi.BERHASIL` — beda dari M3.1/M3.2 yang memang py mode gagal teknis nyata di level atas (network/API call yang membungkus keputusan itu sendiri, bukan cuma satu bagian dari keputusan).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`status` bisa `SEBAGIAN` kalau LLM fallback gagal teknis untuk sebagian kandidat** — dipertimbangkan (mirror pola M3.1/M3.2), ditolak karena kegagalan itu sudah sepenuhnya diserap sebagai keputusan `cukup=False` yang sah (bukan "keputusan tidak lengkap") — menandainya `SEBAGIAN` di level atas akan mendua-artikan sesuatu yang sebenarnya sudah final dan jujur.

---

## Keputusan 10: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M3.2.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Addendum Checkpoint 7 (Reliability Testing): Prompt Fallback Berakhir di Versi 3

Eval Promptfoo nyata (Checkpoint 7) menemukan DAN memperbaiki dua gap berurutan pada prompt `retriever/kecukupan_struktural_fallback.md`: (a) v1 tidak menjelaskan batasan arsitektur "`chatbot_api` tidak melakukan agregasi sisi klien" — model salah menilai `cukup=true` untuk kandidat row-level (`v_lookup_bookings`) berdasar penalaran BI umum; (b) v2 (perbaikan a) overcorrection — model salah menolak kandidat yang genuinely cukup (`v_reservation_room_type_daily`) karena menyalahartikan granularitas periode grain (harian) harus persis cocok kata dalam kebutuhan ("bulan"/"tahun"). v3 menegaskan granularitas periode bukan kriteria kecukupan. **Hasil final: 4/4 skenario Promptfoo lolos, 6/6 skenario eval `evals/3.3-.../` lolos.** Detail lengkap tiap percobaan: `logs.md` Checkpoint 7.

**Opsi yang Dipertimbangkan tapi Ditolak (untuk addendum ini)**
- **Berhenti di v2 dan terima 2/4 sebagai temuan didokumentasikan (pola M3.2 14/16)** — dipertimbangkan (proyek ini punya preseden tidak mengejar 100% pass rate), tapi ditolak karena overcorrection v2 punya akar masalah yang jelas teridentifikasi dan mudah diperbaiki (beda dari temuan M3.2 yang lebih inheren/sulit — non-determinisme model, batas koreksi pada input adversarial) — memperbaiki root cause yang jelas lebih baik daripada menerima kegagalan yang sebenarnya bisa dihindari.

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Mekanisme evaluasi kecukupan struktural: hybrid (deterministik + fallback LLM konservatif) | A | Checkpoint 4, 6 |
| 2 | Aturan tie-break `view_name_final`: label M3.2 dulu, baru skor M3.1 | A | Checkpoint 8 |
| 3 | Konsumsi `HasilKecocokanMakna` langsung, filter label ditemukan/sebagian | B | Checkpoint 8 |
| 4 | Refactor span M3.1: ekstraksi logic murni + orkestrator penutup span bernama sama | B | Checkpoint 9-10 |
| 5 | Fallback LLM: satu panggilan konservatif, bukan generate-verify penuh | B | Checkpoint 6 |
| 6 | Rule table deterministik fail-safe ke tidak_pasti untuk label tak dikenal | B | Checkpoint 4 |
| 7 | Batching LLM fallback per kebutuhan atomik | B | Checkpoint 6 |
| 8 | Nama span LLM fallback literal "chat", kondisional | B | Checkpoint 6 |
| 9 | `HasilKecukupanStruktural.status` selalu BERHASIL | B | Checkpoint 3 |
| 10 | `decisions.md` sebagai Task pertama | B | Plan |
