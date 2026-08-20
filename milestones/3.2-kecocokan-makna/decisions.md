# Decisions — Milestone 3.2: Pemeriksaan Kecocokan Makna

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 3.2 — tahap kedua Retriever (PIC 3), menilai tiap kandidat `view_name` hasil Milestone 3.1 terhadap definisi lengkapnya di katalog (grain, sumber data, jebakan eksplisit), memberi label ditemukan/sebagian/tidak ditemukan.

---

## Keputusan 1: Mekanisme Verifikasi — Generate + Verifikator Independen, Koreksi Dua Arah

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Risiko M3.2 simetris — KK1 (kandidat "kedengarannya cocok" tapi grain berbeda tidak boleh dilabel cocok penuh) dan KK2 (kandidat cocok penuh tidak boleh diragukan berlebihan) sama-sama penting. Tidak ada preseden mekanisme identik di project ini: M1.7 (satu panggilan konservatif, tanpa verifier kedua) hanya sah untuk risiko SEARAH (false-negative aman); M2.1/M2.3 (union-aditif) hanya menambah domain/constraint yang terlewat, tidak pernah mengoreksi keputusan Langkah 1 yang sudah salah. Genuinely terbuka — prinsip arsitektur "generate lalu verify independen WAJIB kalau ruang kesalahan terbuka" (`CLAUDE.md`) memaksa ADA verifikasi independen, tapi bentuknya (koreksi dua arah vs union aditif vs tanpa verifier) tidak forced oleh dokumen manapun.

**Keputusan yang Dipilih**
Dua panggilan LLM berurutan: Langkah 1 (generate, Qwen3-32B) memberi label+alasan awal per kandidat; Langkah 2 (verifikasi, DeepSeek V4 Pro reasoning="high") independen menilai ulang dari definisi lengkap SEBELUM melihat label Langkah 1 secara eksplisit diinstruksikan re-derivasi dulu, lalu hasilnya MENGGANTIKAN Langkah 1 sepenuhnya (bisa mengoreksi label ke arah manapun — ditemukan→sebagian ATAU sebagian→ditemukan), bukan union aditif yang hanya menambah.

**Alasan**
Union aditif (pola M2.1/M2.3) tidak cocok untuk risiko dua-arah — union hanya bisa menambah kandidat/domain baru, tidak bisa mengoreksi label yang sudah salah di kandidat yang sama. Model "hasil Langkah 2 menggantikan" adalah satu-satunya bentuk generate-verify yang bisa memperbaiki kesalahan Langkah 1 di kedua arah sekaligus, konsisten prinsip ruang-kesalahan-terbuka. Biaya (1 panggilan LLM tambahan) bukan tradeoff baru — M1.6/M2.1/M2.3 sudah menjalankan 2-3 panggilan berurutan di jalur eksekusi nyata (bukan cuma eval).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu panggilan konservatif saja, tanpa verifier kedua (pola M1.7)** — ditolak, justifikasi M1.7 (risiko searah, false-negative aman) tidak berlaku di M3.2 (risiko dua arah); memakainya di sini berarti menyimpang dari prinsip generate-verify tanpa dasar yang sama.
- **Verifikator "blind" (tidak melihat label Langkah 1 sama sekali) + rekonsiliasi otomatis pilih label lebih hati-hati** — dipertimbangkan (menghindari anchoring bias sepenuhnya), tapi ditolak: menambah logic rekonsiliasi baru ("mana yang lebih hati-hati" antar 3 label berurutan tidak selalu jelas), dan kehilangan kemampuan Langkah 2 menjelaskan KENAPA ia tidak setuju dengan Langkah 1 secara spesifik (alasan lebih lemah untuk audit KK1/KK2).
- **Retry-with-feedback (pola M1.6: verifier hanya menilai valid/invalid, trigger retry Langkah 1)** — ditolak, `docs/keterbatasan-diterima.md` #5 sudah mencatat retry-dengan-feedback M1.6 TIDAK menunjukkan bukti perbaikan di eval nyata; mengulang mekanisme yang sudah terbukti tidak efektif untuk versi M3.2 tidak beralasan, terutama karena label 3-nilai per-kandidat tidak punya "invalid" yang jelas seperti keluaran terstruktur M1.6.

**Dampak**
Menentukan bentuk kode `_langkah_generate`/`_langkah_verifikasi` di `kecocokan_makna.py` (Checkpoint 7-8) dan atribut observability `kecocokan_makna.dikoreksi_count` (Checkpoint 10) sebagai sinyal nyata seberapa sering Langkah 2 benar-benar mengoreksi (bukan cuma anchoring/menyalin Langkah 1).

---

## Keputusan 2: Granularitas Batch — Per Kebutuhan Atomik, Bukan Per Kandidat

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Tidak diatur dokumen sumber. M3.1 pernah menghasilkan hingga 10 kandidat (domain `hr`) untuk satu kebutuhan atomik dalam skenario eval Bagian B — kalau dinilai per-kandidat, satu kebutuhan atomik bisa butuh hingga 20 panggilan LLM berurutan (10 kandidat × 2 langkah) di jalur eksekusi nyata, bukan hanya eval.

**Keputusan yang Dipilih**
Satu panggilan Langkah 1 + satu panggilan Langkah 2 menilai SELURUH kandidat satu `HasilPencarianKandidat` (satu kebutuhan atomik) sekaligus dalam satu prompt.

**Alasan**
Ukuran token skenario terburuk (~1500-3000 token untuk 10 definisi lengkap) jauh di bawah context window kedua model — tidak ada tekanan latensi/biaya yang mendorong ke arah per-kandidat. Batching juga py efek samping positif: penilaian grain komparatif ("apakah grain kandidat ini tepat DIBANDING kandidat lain yang ditawarkan") lebih mudah bagi model kalau seluruh kandidat terlihat bersamaan dalam satu konteks, dibanding dinilai terisolasi. Granularitas ini mirror pola M2.1/M2.3 yang menilai seluruh domain dalam satu panggilan per atomic intent.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu panggilan per kandidat** — ditolak, mengalikan jumlah panggilan LLM sesuai jumlah kandidat (hingga 20 round-trip berurutan per kebutuhan atomik pada kasus terburuk), menambah latensi nyata di jalur eksekusi produksi, bukan cuma di eval; juga kehilangan konteks komparatif antar kandidat yang berguna untuk penilaian grain relatif.

**Dampak**
Satu kegagalan/respons malformed di satu langkah mempengaruhi SELURUH kandidat kebutuhan atomik itu sekaligus (bukan hanya satu kandidat) — dimitigasi oleh jaminan struktural Keputusan 9 (tidak boleh drop kandidat, default aman per-kandidat kalau ada anomali parsing sebagian).

---

## Keputusan 3: Sertakan Fungsi Orkestrator `_semua()`

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
M3.1 sengaja TIDAK membuat `_semua()` (lihat `milestones/3.1-.../decisions.md` Keputusan 4), tapi restraint itu forced oleh redaksi Lingkup M3.1 sendiri ("dari satu kebutuhan atomik"). Redaksi Lingkup M3.2 ("menilai kandidat... satu per satu") soal evaluasi per-KANDIDAT dalam satu kebutuhan atomik, bukan soal cakupan daftar atomic intent — sehingga restraint M3.1 tidak otomatis berlaku sama untuk M3.2. Genuinely terbuka.

**Keputusan yang Dipilih**
M3.2 menyertakan `nilai_kecocokan_makna_semua(daftar_hasil_pencarian: list[HasilPencarianKandidat]) -> list[HasilKecocokanMakna]`, selain `nilai_kecocokan_makna_atomic_intent()` single-item.

**Alasan**
Bentuk mekanisme M3.2 (generate+verify dua langkah) secara struktural lebih dekat ke M2.1/M2.3 (yang keduanya memang memiliki `_semua()`) dibanding ke M3.1 (BM25/embedding murni, single-item). Menyediakan entry point lengkap sekarang menghindari pekerjaan wiring tambahan nanti di M3.4 tanpa menambah risiko desain — pola orkestrasi loop-sederhana (`[fn(x) for x in daftar]` + span agregat) sudah terbukti aman dipakai berulang.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hanya single-item, serahkan looping ke pemanggil masa depan (M3.4)** — dipertimbangkan sebagai mirror restraint M3.1, tapi ditolak karena restraint M3.1 forced oleh redaksi Lingkup yang spesifik untuk M3.1, tidak berlaku sama untuk M3.2 sesuai analisis Latar Belakang di atas.

**Dampak**
`kecocokan_makna.py` py dua entry point publik (bukan satu), test coverage mencakup keduanya secara terpisah (Checkpoint 9 vs 10).

---

## Keputusan 4: Model Langkah 1/Langkah 2 — Reuse Qwen3-32B / DeepSeek V4 Pro

**Sumber Paksaan**
Preseden konsisten M1.6 Langkah 6, M2.1, M2.3 — pola "generate pakai Qwen3-32B, verifikator independen pakai DeepSeek V4 Pro `reasoning=\"high\"`" sudah dipakai berulang untuk kebutuhan verifikasi independen semantik.

**Keputusan yang Diikuti**
`OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE = "qwen/qwen3-32b"`, `OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI = "deepseek/deepseek-v4-pro"` (reasoning="high") — konstanta terisolasi sendiri (bukan reuse konstanta modul lain) mengikuti pola "satu konstanta per konsumen" (preseden Keputusan 9 M1.4).

**Catatan Ketergantungan**
Ini model chat/completion biasa (bukan model class baru seperti embedding M3.1) — tidak perlu perbandingan empiris baru sebelum dipakai, beda dari `docs/keputusan-tertunda.md` #2 yang statusnya provisional karena genuinely model class baru.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by preseden konsisten M1.6/M2.1/M2.3, tidak ada indikasi kebutuhan M3.2 berbeda cukup jauh untuk menjustifikasi perbandingan model baru.

---

## Keputusan 5: Corpus Definisi Lengkap Ditranskripsi Verbatim, Bukan Diringkas

**Sumber Paksaan**
Preseden `korpus_view.py` (M3.1): transkripsi verbatim + test drift-detection independen, bukan ringkasan interpretatif. Dikombinasikan dengan ukuran token realistis (~1500-3000 token skenario terburuk, jauh di bawah context window Qwen3-32B/DeepSeek V4 Pro).

**Keputusan yang Diikuti**
`DEFINISI_LENGKAP_VIEW` di `definisi_view.py` berisi blok Markdown penuh per view (Sumber+grain, Fungsi, tabel Kolom lengkap termasuk baris "Kolom turunan", blockquote Catatan inline kalau ada) — ditranskripsi apa adanya dari `katalog-data-chatbot.md`, tanpa dipangkas.

**Catatan Ketergantungan**
Bagian yang paling mungkin terpangkas oleh ringkasan (Catatan, baris "Kolom turunan") justru persis bagian yang jadi target KK1 — meringkas berarti mengambil keputusan interpretatif sepihak atas konten yang seharusnya dinilai LLM sendiri, bertentangan dengan semangat generate-verify yang jadi alasan milestone ini ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Versi ringkas (hanya Sumber+Fungsi+kolom yang ditandai turunan, tanpa kolom native biasa)** — ditolak, budget token tidak menuntutnya, dan berisiko memangkas detail yang relevan tapi tidak terlihat "penting" secara sepintas.

---

## Keputusan 6: `Catatan Lintas-Domain` Diinject Sekali sebagai Konteks Statis, Bukan Diduplikasi per View

**Sumber Paksaan**
Instruksi eksplisit dokumen sumber sendiri (`katalog-data-chatbot.md` baris 34 dan 999): "aturan lintas-domain... dijelaskan sekali di akhir dokumen, tidak diulang di tiap view."

**Keputusan yang Diikuti**
`CATATAN_LINTAS_DOMAIN: str` (konstanta terpisah di `definisi_view.py`, transkripsi verbatim 7 butir) diinject sekali ke system prompt Langkah 1 dan Langkah 2 — bukan disalin ke 67 entri `DEFINISI_LENGKAP_VIEW`. Mirror pola `CATATAN_POLA_JEBAKAN` M2.1.

**Catatan Ketergantungan**
Butir 5 (kolom `property_id` hasil join, dengan daftar view eksplisit) adalah jebakan inti yang jadi target KK1 — kalau tidak diinject, prompt kehilangan sinyal penting ini sama sekali.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Duplikasi 7 butir ke tiap entri 67 view yang relevan** — ditolak, bertentangan langsung dengan instruksi eksplisit dokumen sumber sendiri, dan menambah redundansi token tanpa manfaat (informasi sudah lengkap kalau diinject sekali).

---

## Keputusan 7: Fallback Langkah 1 Gagal Total → `GAGAL_TEKNIS` + `kecocokan` Kosong

**Sumber Paksaan**
Pola identik `AtomicIntentDomains` (M2.1) dan `AtomicIntentMatch` (M1.7) — kegagalan teknis total dinyatakan jujur via status, bukan dipalsukan jadi label per-kandidat yang sebenarnya tidak pernah dinilai LLM. Forced by prinsip "kejujuran terhadap keterbatasan" (`CLAUDE.md`).

**Keputusan yang Diikuti**
Kalau `_langkah_generate` gagal total (API error, dst.), `nilai_kecocokan_makna_atomic_intent()` mengembalikan `status=GAGAL_TEKNIS`, `kecocokan=[]`.

**Catatan Ketergantungan**
Konsisten dengan validator satu-arah Keputusan 10 di bawah (`GAGAL_TEKNIS` → `kecocokan` wajib kosong).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Setiap kandidat didowngrade jadi label `sebagian` default dengan alasan "gagal teknis"** — ditolak, ini fabrikasi label yang sebenarnya tidak pernah dinilai LLM sama sekali, melanggar prinsip kejujuran; `GAGAL_TEKNIS` sudah cukup jujur menyatakan "tidak ada penilaian" tanpa berpura-pura py penilaian.

---

## Keputusan 8: Fallback Langkah 2 Gagal Teknis → `SEBAGIAN`, Hasil Langkah 1 Dipertahankan

**Sumber Paksaan**
Pola eksplisit terdokumentasi M2.1 ("verifikasi titik buta gagal teknis: domain langkah 1 tetap dipakai"), sudah dipakai ulang identik di M3.1 sendiri (fallback embedding gagal → BM25 dipertahankan, `status=SEBAGIAN`).

**Keputusan yang Diikuti**
Kalau Langkah 1 sukses tapi `_langkah_verifikasi` gagal teknis, `nilai_kecocokan_makna_atomic_intent()` mengembalikan `status=SEBAGIAN`, `kecocokan=` hasil Langkah 1 utuh (belum terkoreksi Langkah 2).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by preseden yang sudah dipakai berulang (M2.1, M3.1).

---

## Keputusan 9: Jaminan Struktural — Tidak Boleh Drop Kandidat Asli

**Sumber Paksaan**
Prinsip kejujuran + karakter simetris risiko M3.2 (Keputusan 1) — beda dari `verifikasi_titik_buta` M2.1 yang boleh drop entri halusinasi karena arahnya aditif-saja (kehilangan tambahan tidak berbahaya).

**Keputusan yang Diikuti**
`len(kecocokan) == len(kandidat)` kapan pun `status != GAGAL_TEKNIS`, dijamin di kode (bukan hanya skema): kalau LLM menghasilkan `view_name` halusinasi atau melewatkan satu kandidat dari daftar, kandidat yang hilang tetap dimasukkan ke `kecocokan` dengan label aman default (mis. `sebagian`, alasan `"parse_anomaly: ..."`), bukan diam-diam dijatuhkan.

**Catatan Ketergantungan**
Men-drop kandidat asli di M3.2 mengecilkan pool M3.3 tanpa sinyal apa pun — berbahaya untuk risiko dua-arah, beda dari M2.1 di mana kehilangan tambahan aditif tidak mengurangi apa pun yang sudah pasti benar.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Ikuti pola `verifikasi_titik_buta` M2.1 (drop entri anomali diam-diam)** — ditolak, forced-nya M2.1 spesifik untuk arah aditif-saja; M3.2 py risiko dua arah sehingga drop kandidat asli berpotensi menyembunyikan kegagalan sistem tanpa sinyal.

---

## Keputusan 10: Validator `HasilKecocokanMakna` Satu Arah (Beda dari `AtomicIntentDomains` Dua Arah)

**Sumber Paksaan**
Keberadaan kasus valid `BERHASIL` + `kecocokan=[]` — M3.1 memang bisa tidak menemukan kandidat sama sekali (`HasilPencarianKandidat.kandidat` boleh kosong), kasus yang tidak dimiliki `AtomicIntentDomains` (M2.1 selalu mengharuskan minimal satu domain kalau bukan gagal teknis).

**Keputusan yang Diikuti**
Validator `HasilKecocokanMakna` hanya mengecek satu arah: `status == GAGAL_TEKNIS` → `kecocokan` wajib kosong. TIDAK mengecek arah sebaliknya (status lain boleh `kecocokan` kosong, kalau memang M3.1 tidak mengirim kandidat apa pun).

**Catatan Ketergantungan**
Kalau validator meniru `AtomicIntentDomains` (dua arah) apa adanya, kasus `BERHASIL`+`kecocokan=[]` yang genuinely valid akan ditolak keliru.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Validator dua arah identik `AtomicIntentDomains`** — ditolak, akan salah menolak kasus valid "M3.1 tidak menemukan kandidat apa pun" yang memang bisa terjadi secara sah.

---

## Keputusan 11: Nama Span Pemanggilan LLM Literal `"chat"`

**Sumber Paksaan**
Kontrak observability Bagian 2 `rancangan-observability-ai-chatbot.md` (baris span Retriever "chat (kecocokan makna)"), diverifikasi identik di kode nyata `context_resolution/matching.py` (`with tracer.start_as_current_span("chat")`).

**Keputusan yang Diikuti**
`_langkah_generate` dan `_langkah_verifikasi` membuka span bernama literal `"chat"` (bukan nama custom seperti `retriever.nilai_kecocokan_makna`), dengan atribut `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`/`output_tokens`, `prompt.id`, `prompt.version`. Span pembungkus orkestrasi `nilai_kecocokan_makna_semua()` pakai nama deskriptif (`retriever.nilai_kecocokan_makna_semua`, tracer `retriever.kecocokan_makna`) — mirror `domain_gate.identifikasi_semua`/`matching.evaluate`.

**Catatan Ketergantungan**
Beda dari span non-LLM M3.1 (`retriever.cari_kandidat_view`, nama custom `<subpackage>.<function>` per Keputusan 9 M3.1) — span M3.2 adalah pemanggilan `chat` sungguhan sehingga literal `"chat"` berlaku, bukan konvensi custom M3.1.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by kontrak observability + bukti langsung dari kode M1.7 yang sudah memakai pola ini.

---

## Keputusan 12: Reuse Skema `AtomicIntent`/`Domain`/`KandidatView`/`StatusEksekusi` Tanpa Redefinisi

**Sumber Paksaan**
Preseden konsisten seluruh `src/schemas/` — tidak ada modul yang mendefinisikan ulang tipe yang sudah ada di modul lain.

**Keputusan yang Diikuti**
`KecocokanKandidat.kandidat: KandidatView` (objek utuh, bukan `view_name: str` polos) — mempertahankan `domain`/`skor`/`sumber` asal dari M3.1 di keluaran M3.2, berguna untuk audit/observability tanpa join balik ke `HasilPencarianKandidat`.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`KecocokanKandidat.view_name: str` polos, tanpa objek `KandidatView` utuh** — ditolak, kehilangan informasi `domain`/`skor`/`sumber` yang berguna untuk M3.3 dan observability tanpa alasan penghematan yang berarti (objek `KandidatView` sudah kecil).

---

## Keputusan 13: Konvensi Nama Fungsi `_atomic_intent`/`_semua`

**Sumber Paksaan**
Preseden konsisten M2.1 (`identifikasi_domain_atomic_intent`/`identifikasi_domain_semua`) dan M2.3 (`deteksi_constraint_atomic_intent`/`deteksi_constraint_semua`).

**Keputusan yang Diikuti**
`nilai_kecocokan_makna_atomic_intent()` (single-item) dan `nilai_kecocokan_makna_semua()` (orkestrator list) — `_atomic_intent` dipilih (bukan `_kandidat`) karena granularitas kerja nyatanya adalah "satu kebutuhan atomik beserta seluruh kandidatnya" (Keputusan 2, batch), bukan "satu kandidat".

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by preseden penamaan konsisten M2.1/M2.3, selaras dengan Keputusan 2 (batch per atomic intent).

---

## Keputusan 14: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M3.1.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Keputusan 15 (Addendum): Migrasi Model Verifikasi Langkah 2 — DeepSeek V4 Pro 0423 → DeepSeek V4 Flash 0731

**Status:** Diputuskan 2026-08-20, di luar siklus milestone ini (sudah closed) — perubahan cross-cutting terhadap 6 titik verifier DeepSeek V4 Pro project sekaligus, diinisiasi permintaan user, dikonfirmasi lewat `AskUserQuestion`.

**Latar Belakang**
User meminta migrasi biaya untuk 6 titik verifier project yang semula seragam `deepseek/deepseek-v4-pro` (versi `0423`): kombinasi antara `deepseek/deepseek-v4-flash-0731` (jauh lebih murah/cepat) dan `deepseek/deepseek-v4-pro-0813` (rilis resmi 2026-08-13, upgrade dari versi preview `0423`). Riset menemukan Artificial Analysis Intelligence Index kedua model nyaris identik (Flash 0731 = 52, Pro 0813 = 53), sementara lompatan skor Pro 0813 terkonsentrasi di benchmark coding/agentic/cyber yang tidak relevan untuk tugas verifier project ini. Pro 0813 juga LEBIH MAHAL dari Pro 0423 lama — migrasi bukan downgrade seragam, melainkan realokasi berdasar risiko per titik.

**Keputusan yang Dipilih**
Konstanta `OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI` (`kecocokan_makna.py`, Langkah 2) diubah dari `deepseek/deepseek-v4-pro` menjadi `deepseek/deepseek-v4-flash-0731`.

**Alasan**
Keputusan 4 milestone ini eksplisit menandai risiko Langkah 2 SIMETRIS ("KK1 dan KK2 sama-sama penting") — beda dari verifikasi titik buta Domain Gate (M2.1)/cakupan-individu (M2.3) yang asimetris dan berisiko kebocoran RBAC. Hasil Langkah 2 MENGGANTIKAN Langkah 1 (koreksi dua arah), tapi tidak ada arah kesalahan yang lebih dikhawatirkan dari arah lainnya di sini — bukan titik pencegah kebocoran otorisasi. Selisih reasoning yang nyaris tidak ada (52 vs 53) membuat Flash 0731 memadai, penghematan biaya jadi prioritas.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tetap di tier Pro (upgrade ke 0813)** — ditolak, risiko titik ini simetris (bukan leak-risk RBAC seperti M2.1/M2.3), tidak ada argumen kuat menahan tier lebih mahal di sini.
- **Tetap di Pro 0423 (status quo)** — ditolak, versi preview lama tidak lagi jadi rilis utama DeepSeek per 2026-08-13, tidak memberi penghematan biaya.

**Dampak**
`src/config/llm.py` konstanta `OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI` diubah nilainya (docstring diperbarui, pointer ke keputusan ini). Tidak ada perubahan skema/signature/`reasoning="high"`/kontrak fungsi Langkah 2 — Langkah 1 (`OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE`, Qwen3-32B) tidak tersentuh.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Mekanisme verifikasi: generate + verifikator independen, koreksi dua arah | A | Checkpoint 7-8 |
| 2 | Granularitas batch: per kebutuhan atomik, bukan per kandidat | A | Checkpoint 7-10 |
| 3 | Sertakan fungsi orkestrator `_semua()` | A | Checkpoint 10 |
| 4 | Model Langkah 1/Langkah 2: reuse Qwen3-32B / DeepSeek V4 Pro | B | Checkpoint 4 |
| 5 | Corpus definisi lengkap ditranskripsi verbatim | B | Checkpoint 2 |
| 6 | Catatan Lintas-Domain diinject sekali sebagai konteks statis | B | Checkpoint 2, 5-6 |
| 7 | Fallback Langkah 1 gagal total: GAGAL_TEKNIS + kecocokan kosong | B | Checkpoint 9 |
| 8 | Fallback Langkah 2 gagal teknis: SEBAGIAN + Langkah 1 dipertahankan | B | Checkpoint 9 |
| 9 | Jaminan struktural: tidak boleh drop kandidat asli | B | Checkpoint 7-9 |
| 10 | Validator HasilKecocokanMakna satu arah | B | Checkpoint 3 |
| 11 | Nama span pemanggilan LLM literal "chat" | B | Checkpoint 7-8, 10 |
| 12 | Reuse skema AtomicIntent/Domain/KandidatView/StatusEksekusi | B | Checkpoint 3 |
| 13 | Konvensi nama fungsi `_atomic_intent`/`_semua` | B | Checkpoint 9-10 |
| 14 | decisions.md sebagai Task pertama | B | Plan |
| 15 | Addendum: migrasi model verifikasi Langkah 2 Pro 0423 → Flash 0731 | A | Addendum 2026-08-20 |
