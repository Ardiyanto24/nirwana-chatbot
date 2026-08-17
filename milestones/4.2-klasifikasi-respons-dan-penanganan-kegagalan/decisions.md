# Decisions — Milestone 4.2: Klasifikasi Respons dan Penanganan Kegagalan

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 4.2 — konsumen langsung `HasilPemanggilanChatbotAPI` (M4.1), yang membaca `status_code`/`kegagalan_transport`/`body` dan menentukan salah satu dari lima jalur penanganan yang dikunci `rancangan-execution-interpretation.md`.

---

## Keputusan 1: "Berhasil" vs "Sebagian" untuk Respons 200 — M4.2 Selalu Memetakan ke `berhasil`

**Status:** Diputuskan sebelum implementasi (diskusi mendalam dengan user, sebelum plan ditulis).

**Latar Belakang**
Genuinely terbuka — `rancangan-execution-interpretation.md` menulis "200 → kumpulkan hasil, status berhasil/sebagian" tanpa pernah menjelaskan kriteria pembeda keduanya. User awalnya mengusulkan solusi "kontrak nilai valid" (filter DISTINCT + monitoring tim database), lalu meminta riset lebih dalam.

Riset menelusuri 5 pemakaian `StatusEksekusi.SEBAGIAN` yang sudah ada di codebase (`src/schemas/retriever.py`, `src/schemas/domain_gate.py`, `src/layers/retriever/kecocokan_makna.py`) — polanya konsisten di semuanya: SEBAGIAN = proses 2+ langkah berbeda, satu langkah sukses penuh, langkah LAIN gagal secara TEKNIS (bukan soal isi/makna), hasil langkah sukses dipertahankan sebagai output berdegradasi. Contoh: `retriever.py` — BM25 (langkah 1) sukses, fallback embedding (langkah 2, kondisional) gagal teknis → SEBAGIAN (kandidat BM25 tetap dipakai).

M4.1 (input M4.2) hanya SATU langkah (1 panggilan HTTP, dikonfirmasi struktural: 1 atomic intent = 1 view_name = 1 `QueryEngineRequest` = 1 panggilan `chatbot_api`, ditelusuri lewat seluruh rantai skema M1.6-M3.5). Retry infra yang berhasil dianalogikan ke "fallback berhasil" di preseden — tetap `BERHASIL`, bukan `SEBAGIAN` (preseden `retriever.py`: fallback yang BEKERJA tetap `BERHASIL`, hanya fallback yang GAGAL TEKNIS jadi `SEBAGIAN`). Retry infra yang habis tanpa sukses = tidak ada hasil parsial apa pun untuk dipertahankan → `GAGAL_TEKNIS`, bukan `SEBAGIAN`.

Argumen tambahan dari prinsip arsitektur: M4.2 didesain non-LLM (deterministik) — sah secara arsitektur HANYA jika ruang kesalahannya tertutup (`CLAUDE.md`, prinsip ruang-kesalahan-tertutup-vs-terbuka). Membedakan berhasil/sebagian dari ISI data (mis. body kosong = data hilang vs body kosong = jawaban nol yang sah) adalah ruang kesalahan TERBUKA (butuh pemahaman makna) — yang menurut prinsip project WAJIB LLM independen (itu justru pekerjaan M4.5, bukan sah didekati M4.2).

**Keputusan yang Dipilih**
M4.2 SELALU memetakan respons 200 → `status=berhasil`. Tidak ada logic apa pun yang menghasilkan `SEBAGIAN` dari klasifikasi status code semata.

**Alasan**
Konsisten preseden SELURUH pemakaian `StatusEksekusi.SEBAGIAN` yang sudah ada; konsisten dengan sifat M4.2 sebagai layer deterministik (ruang kesalahan tertutup); tidak ada sinyal struktural apa pun di kontrak `api-chatbot.md` saat ini (tidak ada pagination/partial flag) yang bisa dipakai sebagai basis tertutup untuk `SEBAGIAN`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Body kosong (list `[]`) → `SEBAGIAN`** — ditolak: berisiko menandai jawaban nol yang LEGITIMATE (mis. "0 reservasi dibatalkan hari ini") sebagai `SEBAGIAN`, bertentangan dengan tujuan pola nullable-bermakna yang justru didesain M4.3 untuk mencegah kesalahan generalisasi ini.
- **Kontrak "nilai valid" (filter DISTINCT + monitoring tim database), usulan awal user** — dipertimbangkan serius, TIDAK ditolak sepenuhnya tapi diarahkan jadi usulan lintas-tim (lihat Keputusan 2) karena: (a) hanya menutup drift KATEGORIKAL, tidak menutup korektnes nilai AGREGAT (mis. COUNT=0) yang jadi contoh konkret kekhawatiran user; (b) butuh infrastruktur baru milik tim database (di luar kendali unilateral project ini); (c) bahkan kalau ada, konsumsinya tepat di M4.3 (catatan_interpretasi), bukan M4.2.

**Dampak**
Tidak ada dampak lintas-milestone langsung — M4.3 (konsumen berikutnya) tetap menerima `status=berhasil` untuk seluruh 200, konsisten kontrak `StatusEksekusi` yang sudah ada. Kalau nanti kontrak `chatbot_api` menyediakan sinyal freshness/kualitas data (Keputusan 2), keputusan ini WAJIB direvisit.

> **REVISIT (2026-08-17): pemicu peninjauan ulang TERPENUHI.** Tim database engineering mengonfirmasi endpoint `GET /chatbot/{domain}/{view_name}/_meta` (`last_refreshed_at`/`data_quality_status`) sudah tersedia — persis sinyal tertutup yang tadinya belum ada saat Keputusan 1 diambil. Keputusan "M4.2 SELALU `berhasil`" DIREVISI: `SEBAGIAN` sekarang genuinely dipakai untuk `data_quality_status="flagged"` ATAU `last_refreshed_at` melewati ambang kesegaran — TAPI `null`/kegagalan panggilan `_meta` TETAP `berhasil` (bukan `sebagian`), supaya sinyal `sebagian` tidak diencerkan oleh ketidaktahuan semata (lihat Keputusan 11 untuk detail lengkap + alasan). Argumen inti Keputusan 1 di atas (preseden `SEBAGIAN`=proses 2+ langkah, satu gagal teknis) TETAP RELEVAN — sekarang M4.2 genuinely punya 2 langkah (panggilan data + panggilan `_meta`), memenuhi pola precedent yang sama persis.

---

## Keputusan 2: Usulan Kontrak `last_refreshed_at`/`data_quality_status` — Dicatat sebagai Addendum `keputusan-tertunda.md` #3, Tidak Memblokir M4.2

**Status:** Diputuskan sebelum implementasi (diskusi dengan user).

**Latar Belakang**
Turunan langsung dari Keputusan 1 — user meminta solusi yang BENAR-BENAR menutup celah "apakah hasil 0 itu genuinely benar", termasuk kalau solusinya masuk domain database engineering. Riset mendalam menyimpulkan: masalah "korektnes nilai agregat" hanya bisa ditutup lewat sinyal KESEHATAN PIPELINE (freshness data, status data-quality-contract) yang objektif/tertutup — bukan lewat menebak isi data. `docs/keputusan-tertunda.md` #3 sudah mencatat kontrak `api-chatbot.md` masih belum final, sehingga ini momen tepat untuk diusulkan.

**Keputusan yang Dipilih**
Draf usulan (field `last_refreshed_at`, `data_quality_status` per view/domain, dua opsi bentuk implementasi) didokumentasikan sebagai addendum `docs/keputusan-tertunda.md` #3 (lihat file tersebut untuk teks lengkap) — BUKAN diimplementasikan di M4.2 sekarang, karena sinyal ini belum ada di kontrak `chatbot_api` hari ini dan pembuatannya di luar kendali unilateral project ini (butuh kerja sama tim database engineering).

**Alasan**
M4.2 tidak boleh diblokir menunggu perubahan kontrak lintas-tim yang belum tentu linimasanya. Draf usulan tetap didokumentasikan formal supaya tidak hilang, siap diajukan saat rekonsiliasi akhir proyek dengan tim `chatbot_api` (`docs/keputusan-tertunda.md` #3 sudah mengagendakan rekonsiliasi ini).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menunda M4.2 sampai sinyal ini tersedia** — ditolak, linimasa tidak pasti (bergantung tim lain), dan M4.2 tetap punya nilai penuh tanpa sinyal ini (menutup jalur 400/403/404/5xx/timeout yang tidak bergantung sinyal ini sama sekali).

**Dampak**
`docs/keputusan-tertunda.md` #3 diperluas (bukan entri baru). Pemicu peninjauan ulang eksplisit ditulis di sana: begitu tim database menyediakan sinyal ini, revisit Keputusan 1 (M4.2 mungkin perlu logic baru untuk `SEBAGIAN` berbasis sinyal freshness/kualitas).

---

## Keputusan 3: Cakupan Jalur 400 — Opsi B, Orkestrasi Loop Revisi Penuh ke Query Engine

**Status:** Diputuskan sebelum implementasi (user memilih eksplisit "Opsi B" setelah penjelasan detail cakupan).

**Latar Belakang**
Genuinely terbuka — `rancangan-retrieval-query.md` (M3.4) "Catatan Serah Terima" eksplisit menandai mekanisme kirim-balik 400 sebagai kontrak dua arah yang BELUM disepakati. Dua opsi diajukan: (A) M4.2 hanya mengklasifikasikan+menandai "perlu_revisi" tanpa memanggil balik Query Engine; (B) M4.2 mengorkestrasi loop penuh (memanggil balik `susun_request_atomic_intent()` dengan feedback, re-verifikasi M3.5+M2.4, panggil ulang `chatbot_api`).

Ditelusuri konkret cakupan Opsi B sebelum user memutuskan: butuh memperluas `susun_request_atomic_intent()` (M3.4, tambah parameter `feedback`, mirror pola `pecah_atokmik()` M1.6), memanggil ulang `verifikasi_bentuk_request_atomic_intent()` (M3.5, TIDAK berubah — sudah stateless) dan `verifikasi_gate()` (M2.4, TIDAK berubah — sudah stateless, butuh `constraint`+`view_name_tervalidasi_retriever` diteruskan dari pemanggil).

**Keputusan yang Dipilih**
Opsi B — M4.2 mengorkestrasi loop revisi PENUH: 400 → `susun_request_atomic_intent(feedback=...)` → `verifikasi_bentuk_request_atomic_intent()` → `verifikasi_gate()` → panggil ulang `chatbot_api`, maksimal `EXECUTION_MAX_REVISI=3` percobaan total (lihat Keputusan 6).

**Alasan**
User eksplisit memilih ini setelah dijelaskan konsekuensi cakupannya secara lengkap (perluasan kontrak M3.4). Memenuhi KK3 M4.2 sumber secara LITERAL ("benar-benar terkirim balik ke jalur revisi Query Engine"), bukan cuma secara deklaratif.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Opsi A (klasifikasi+tandai saja)** — ditawarkan lengkap dengan trade-off (konsisten pola milestone standalone M1.2-M4.1, tidak mengubah kontrak M3.4 yang sudah selesai), TIDAK dipilih user.

**Dampak**
`susun_request_atomic_intent()` (M3.4) dan prompt `penyusunan_request.md` (M3.4) diperluas — perubahan backward-compatible (`feedback` opsional default `None`), tidak mengubah perilaku existing caller. Cross-reference ditambahkan ke `milestones/3.4-penyusunan-request/report.md` Bagian 6 (Follow-up). Mekanisme feedback ini mewarisi keterbatasan `docs/keterbatasan-diterima.md` #5 (retry+feedback M1.6 belum terbukti empiris memperbaiki hasil LLM) — dicatat eksplisit, bukan diklaim solusi pasti terbukti.

---

## Keputusan 4: Real Testing ke `chatbot_api` Sungguhan Ditunda

**Status:** Diputuskan sebelum implementasi (instruksi eksplisit user sesi ini).

**Latar Belakang**
User meminta lanjut mengerjakan M4.2 dengan real testing ke `chatbot_api` ditunda — "lakukan apa yang bisa dilakukan di milestone ini terlebih dahulu". Genuinely dari instruksi user, bukan ditarik dari dokumen manapun.

**Keputusan yang Dipilih**
Checkpoint 1-6 (decisions, refactor M4.1, perluasan M3.4, skema, klasifikasi inti, integrasi revisi) dikerjakan dan diverifikasi PENUH lewat simulasi/mock (konsisten kata KK sumber sendiri: "disimulasikan"/"skenario uji terkontrol") — TIDAK butuh instance `chatbot_api` hidup. Checkpoint 7 (verifikasi nyata + penutupan milestone: `report.md` final, update status `CLAUDE.md`/`AGENT.md`) DITUNDA sebagai SATU unit sampai user melanjutkan.

**Alasan**
Mirror preseden M4.1 Keputusan 2 (verifikasi nyata + penutupan ditunda bersama sampai prasyarat siap) — menghindari milestone ditandai "Selesai" sebelum benar-benar terbukti nyata, konsisten prinsip kejujuran `CLAUDE.md`.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — instruksi eksplisit user, tidak ada ambiguitas.

**Dampak**
`CLAUDE.md`/`AGENT.md` status M4.2 TIDAK diperbarui jadi "Selesai" sampai Checkpoint 7 selesai. `report.md` final juga ditunda (hanya `logs.md` diisi progresif per checkpoint yang benar-benar dikerjakan).

---

## Keputusan 5: Refactor `pemanggilan_chatbot_api.py` — Ekstrak Logic Murni Tanpa Span

**Sumber Paksaan**
Preseden PERSIS M3.1/M3.3 Keputusan 4 (`milestones/3.3-kecukupan-struktural/decisions.md`) — `_kumpulkan_kandidat()` (M3.1, logic murni tanpa span) diekstrak dari `cari_kandidat_view()` (wrapper standalone, buka+tutup span sendiri, perilaku TIDAK berubah), supaya orkestrator penutup pipeline (`kecukupan_struktural.py`) bisa membuka SATU span yang membungkus M3.1+M3.2+M3.3 sekaligus.

**Keputusan yang Diikuti**
`pemanggilan_chatbot_api.py` direfactor identik: `_panggil_chatbot_api_raw()` (logic HTTP+parsing murni, TANPA span) diekstrak dari `panggil_chatbot_api()` (wrapper standalone, TIDAK berubah signature/perilaku/atribut span). M4.2 (`klasifikasi_respons.py`) memanggil `_panggil_chatbot_api_raw()` langsung, membungkus SATU span `execute_tool` untuk seluruh retry+revisi loop — bukan span baru tiap percobaan.

**Catatan Ketergantungan**
Kalau M4.2 memanggil `panggil_chatbot_api()` (wrapper, bukan `_raw`) untuk tiap percobaan retry/revisi, akan muncul span `execute_tool` TERPISAH per percobaan — bertentangan dengan kontrak observability (satu span `execute_tool` per Execution, dengan `retry count` sebagai ATRIBUT span yang sama, bukan span terpisah-pisah).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by preseden identik M3.1/M3.3 yang sudah terbukti bekerja untuk kasus struktural yang sama persis (span pembungkus multi-langkah).

---

## Keputusan 6: Batas Retry Infrastruktural dan Batas Revisi 400

**Sumber Paksaan**
Preseden numerik `_MAX_ATTEMPTS = 3` yang SUDAH jadi konvensi project (`src/layers/decomposition/decompose.py`, M1.6 Keputusan 3 — 1 percobaan awal + hingga 2 retry). Nilai delay retry (starting point non-empiris) mirror alasan Keputusan 8 M4.1 (`CHATBOT_API_TIMEOUT_DETIK` juga starting point, bukan hasil kalibrasi empiris).

**Keputusan yang Diikuti**
`EXECUTION_MAX_RETRY_INFRA = 2` (retry infra 5xx/timeout, 3 percobaan total per request), `EXECUTION_RETRY_DELAY_DETIK = 1.0` (delay tetap sederhana, bukan exponential backoff — starting point), `EXECUTION_MAX_REVISI = 3` (1 percobaan awal + hingga 2 revisi 400, mirror persis pola `_MAX_ATTEMPTS`). Ketiganya ditambahkan ke `src/config/chatbot_api.py`.

**Catatan Ketergantungan**
Biaya ubah rendah (konstanta tunggal, satu file) — tidak memenuhi ambang "berdampak material/mahal diubah" `CLAUDE.md` untuk perlu `AskUserQuestion`, konsisten preseden M4.1 Keputusan 8 (nilai timeout juga tidak ditanyakan).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Exponential backoff untuk retry infra** — dipertimbangkan sebagai pola lebih "canggih", tidak dipilih: menambah kompleksitas yang belum terbukti perlu (belum ada data nyata pola kegagalan `chatbot_api`), delay tetap 1 detik sudah cukup sebagai starting point yang bisa direvisi berbasis data nyata nanti (Checkpoint 7).

---

## Keputusan 7: Skema `HasilEksekusiAtomicIntent` — Reuse `StatusEksekusi`, `error.type` Terpisah dari Atribut Custom

**Sumber Paksaan**
Preseden konsisten SELURUH skema `Hasil<X>` lain di project (docstring "HANYA N dari 5 nilai `StatusEksekusi` relevan" — konvensi di `retriever.py`/`domain_gate.py`/`query_engine.py`) + preseden `model_validator` invarian di SETIAP skema `Hasil<X>`. "Prinsip pengisian `error.type`" (Bagian 2 `rancangan-observability-ai-chatbot.md`) — nilainya WAJIB satu kosakata dengan `status` project (`gagal_teknis`), BUKAN kode HTTP mentah. Preseden `kegagalan_transport` (M4.1 Keputusan 6) — field custom terpisah supaya tidak bentrok makna dengan `error.type`.

**Keputusan yang Diikuti**
`HasilEksekusiAtomicIntent` (`src/schemas/execution.py`) reuse `StatusEksekusi` (HANYA `BERHASIL`/`GAGAL_TEKNIS` relevan di M4.2 — lihat Keputusan 1 kenapa `SEBAGIAN` tidak dipakai). Field `kegagalan_alasan: str | None` (BUKAN `error_type`) menyimpan detail granular (`eskalasi_403`/`eskalasi_404`/`infra_exhausted_5xx`/`infra_exhausted_timeout`/`revisi_exhausted`/`revisi_gagal_susun`/`revisi_gagal_verifikasi_bentuk`/`revisi_gagal_verification_gate`) — dipetakan ke atribut span CUSTOM `execution.kegagalan_alasan`, terpisah dari atribut `error.type` (yang HANYA diisi `"gagal_teknis"`, uniform, sesuai prinsip observability). `bug_prioritas_tinggi: bool` menandai eskalasi 403/404 secara spesifik (Catatan Serah Terima M4.1: sinyal ini harus terlihat menonjol di dashboard).

**Catatan Ketergantungan**
Kalau `error.type` diisi nilai granular (mis. `"403"`) alih-alih `"gagal_teknis"`, akan melanggar prinsip satu-kosakata-status yang eksplisit dikunci dokumen observability, dan tidak konsisten dengan cara layer lain (Domain Gate, Retriever) mengisi `error.type`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`error.type` diisi kode HTTP granular langsung** — ditolak, melanggar "Prinsip pengisian `error.type`" yang eksplisit ("satu kosakata yang sama... supaya tidak ada dua 'bahasa status' berbeda").
- **Field granular dinamai `error_type` (bukan `kegagalan_alasan`)** — ditolak, berpotensi disalahartikan sebagai kosakata `error.type` observability, persis alasan M4.1 Keputusan 6 menolak nama serupa untuk `kegagalan_transport`.

---

## Keputusan 8: `verifikasi_bentuk_request_atomic_intent()` (M3.5) dan `verifikasi_gate()` (M2.4) Dipanggil Ulang Apa Adanya

**Sumber Paksaan**
Kedua fungsi sudah stateless — `verifikasi_bentuk_request_atomic_intent(atomic_intent, view_name_tervalidasi_retriever, request)` dan `verifikasi_gate(request, constraint, employee_id, view_name_tervalidasi_retriever)` menilai request YANG DIBERIKAN tanpa butuh histori percobaan sebelumnya (dicek langsung dari signature+isi fungsi, `src/layers/query_engine/verifikasi_bentuk_request.py` dan `src/layers/verification_gate/verifikasi_gate.py`).

**Keputusan yang Diikuti**
`_revisi_request()` (M4.2) memanggil kedua fungsi ini TANPA modifikasi signature — beda dari `susun_request_atomic_intent()` (M3.4) yang genuinely butuh tahu "kenapa percobaan sebelumnya ditolak" untuk menghasilkan revisi yang lebih baik (karena itu satu-satunya langkah GENERATE dalam rantai revisi ini).

**Catatan Ketergantungan**
Mengubah M3.5/M2.4 tanpa alasan struktural akan menambah cakupan modifikasi lintas-milestone yang tidak perlu, melanggar prinsip minimal-invasif terhadap kontrak milestone lain yang sudah selesai.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by sifat stateless kedua fungsi tersebut — tidak ada kebutuhan nyata untuk mengubahnya.

---

## Keputusan 9: `docs/keputusan-tertunda.md` #3 Diperluas (Addendum), Bukan Entri Baru

**Sumber Paksaan**
Isu freshness/kualitas data (Keputusan 2) adalah kelanjutan LANGSUNG isu kontrak parameter `chatbot_api` yang sudah tercatat di `docs/keputusan-tertunda.md` #3 (keduanya soal bagian kontrak `api-chatbot.md` yang masih terbuka, direncanakan direkonsiliasi di titik yang sama — akhir proyek).

**Keputusan yang Diikuti**
Ditambahkan sebagai addendum di entri #3 yang sudah ada, bukan entri baru terpisah.

**Catatan Ketergantungan**
Membuat entri terpisah akan memecah konteks rekonsiliasi kontrak `chatbot_api` yang seharusnya dibahas satu paket dengan tim database engineering.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan karena forced by keterkaitan topik yang jelas.

---

## Keputusan 10: `decisions.md` sebagai Task Pertama, `logs.md` Diisi per Checkpoint

**Sumber Paksaan**
`CLAUDE.md` Workflow Wajib "1. Rencanakan sebelum mengimplementasikan" dan "3. Implementasikan per checkpoint" — preseden konsisten seluruh milestone sebelumnya (mis. M4.1 Keputusan 10).

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis. `logs.md` diisi entri baru di setiap checkpoint selesai (1-6), TIDAK dikumpulkan di akhir — konsisten Keputusan 4 (hanya `report.md` FINAL dan update status `CLAUDE.md` yang ditunda ke Checkpoint 7, bukan `logs.md`).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit `CLAUDE.md`/preseden konsisten milestone sebelumnya.

---

## Keputusan 11: Revisit — `SEBAGIAN` Diaktifkan dari Sinyal `_meta` (`data_quality_status`/`last_refreshed_at`)

**Status:** Ditemukan pasca-milestone (2026-08-17) — tim database engineering mengabari endpoint `_meta` sudah tersedia, memenuhi pemicu peninjauan ulang eksplisit di Keputusan 1 dan `docs/keputusan-tertunda.md` #3 addendum.

**Latar Belakang**
Keputusan 1 sengaja SELALU memetakan 200→`berhasil` karena TIDAK ADA sinyal tertutup untuk `SEBAGIAN` saat itu. Tim database sekarang menyediakan `GET /chatbot/{domain}/{view_name}/_meta` mengembalikan `last_refreshed_at`/`data_quality_status` (Opsi B — endpoint terpisah, sesuai usulan kita — 67 endpoint data existing TIDAK berubah bentuk). Genuinely terbuka: bagaimana persisnya memetakan nilai-nilai ini (termasuk `null`/kegagalan panggilan) ke `StatusEksekusi`.

**Keputusan yang Dipilih**
- `data_quality_status="flagged"` → `SEBAGIAN` (sinyal terkonfirmasi tim database, closed-rule).
- `last_refreshed_at` melewati `EXECUTION_DATA_STALENESS_THRESHOLD_JAM` (Keputusan Jenis B baru, lihat commit Checkpoint 3) → `SEBAGIAN` (independen dari `data_quality_status` — bisa trigger sendiri-sendiri, digabung tanpa dobel-hitung).
- `data_quality_status=null` ATAU panggilan `_meta` gagal (timeout/5xx/dsb) → TETAP `berhasil` — TIDAK PERNAH `SEBAGIAN` dari ketidaktahuan semata. Dicatat jujur lewat `catatan_interpretasi` (M4.3, Keputusan terkait di `milestones/4.3-.../decisions.md`), nada BEDA dari `flagged`/stale (bukan menyiratkan masalah terkonfirmasi).
- Panggilan `_meta` SATU percobaan saja (TIDAK ikut `EXECUTION_MAX_RETRY_INFRA`) — kegagalannya tidak boleh menahan/menggagalkan atomic intent yang datanya sendiri sudah berhasil diambil.
- `HasilEksekusiAtomicIntent` validator diperluas: `SEBAGIAN` valid, structurally MIRIP `BERHASIL` (`nilai_hasil` wajib terisi, TIDAK boleh `kegagalan_alasan`/`bug_prioritas_tinggi` — beda dari `GAGAL_TEKNIS` yang genuinely gagal).

**Alasan**
Tim database eksplisit memperingatkan: "kalau field null, itu genuinely tidak diketahui — bukan aman/ok default, jangan diperlakukan sama dengan ok". Tapi disamakan dengan `flagged` (SEBAGIAN) JUGA salah arah — 2 view `guests-*` dikonfirmasi tim database akan sering `null` BUKAN karena masalah, murni keterbatasan cakupan pengecekan otomatis mereka (V1). Kalau `null` disamakan `SEBAGIAN`, sinyal itu akan sering muncul untuk alasan yang bukan genuinely masalah — mengencerkan `SEBAGIAN` sebagai sinyal prioritas yang jarang+berarti (argumen inti Keputusan 1 yang sama, sekarang diterapkan ke kasus baru). Opsi tengah (tetap `berhasil` + catatan jujur) menjaga KEDUA prinsip: tidak menyembunyikan ketidaktahuan (kejujuran `CLAUDE.md`), tidak menyamakan "belum diverifikasi" dengan "dikonfirmasi bermasalah".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`null`/kegagalan `_meta` juga dianggap `SEBAGIAN`** — ditawarkan eksplisit ke user (`AskUserQuestion`), TIDAK dipilih: risiko pengenceran sinyal `SEBAGIAN`, terutama untuk 2 view `guests-*` yang akan sering `null`.
- **`last_refreshed_at` murni informasi teks, TANPA ambang klasifikasi** — direkomendasikan awal (menghindari menebak angka tanpa dasar empiris), TIDAK dipilih user: user memilih tetap pakai ambang (dengan syarat eksplisit ambang itu provisional + wajib dikomunikasikan ke tim database, lihat `docs/keputusan-tertunda.md` #3 addendum kedua).
- **Panggilan `_meta` ikut retry infra sama seperti data utama** — ditolak: menggandakan potensi latensi (retry data + retry meta) untuk sinyal yang sifatnya sekunder/best-effort, tidak proporsional.

**Dampak**
`src/config/chatbot_api.py` (konstanta ambang baru), `src/schemas/execution.py` (validator+field baru), `src/layers/execution/pemanggilan_chatbot_api.py` (fungsi baru `panggil_meta_chatbot_api()`), `src/layers/execution/klasifikasi_respons.py` (integrasi), `src/layers/execution/penyimpanan_paket.py` (M4.3, catatan kualitas data) — lihat `milestones/4.3-.../decisions.md` untuk sisi M4.3.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Berhasil vs sebagian (200): selalu berhasil (DIREVISI Keputusan 11) | A | Plan |
| 2 | Usulan kontrak last_refreshed_at/data_quality_status | A | Checkpoint 1 |
| 3 | Cakupan 400: Opsi B, orkestrasi loop penuh | A | Plan |
| 4 | Real testing chatbot_api ditunda | A | Checkpoint 7 |
| 5 | Refactor pemanggilan_chatbot_api.py: pisahkan span | B | Checkpoint 2 |
| 6 | Batas retry infra dan batas revisi 400 | B | Checkpoint 2 |
| 7 | Skema HasilEksekusiAtomicIntent | B | Checkpoint 4 |
| 8 | M3.5/M2.4 dipanggil ulang apa adanya | B | Checkpoint 6 |
| 9 | keputusan-tertunda.md #3 diperluas, bukan entri baru | B | Checkpoint 1 |
| 10 | decisions.md Task pertama, logs.md per checkpoint | B | Plan |
| 11 | Revisit: SEBAGIAN diaktifkan dari sinyal _meta | A | Revisit Checkpoint 1 |
