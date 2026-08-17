# Decisions — Milestone 3.4: Penyusunan Request

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 3.4 — Langkah 1 (generate) Query Engine, menyusun `QueryEngineRequest {domain, view_name, params}` dari kebutuhan atomik + `view_name` yang sudah divalidasi Retriever (M3.1-3.3), lewat satu pemanggilan LLM (ekstraksi parameter terstruktur).

---

## Keputusan 1: Konvensi Penamaan Parameter — Nama Kolom Asli View (Opsi A), Ditambah Dokumen Kontrak Usulan Terpisah

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion` + klarifikasi lanjutan langsung ke user).

**Latar Belakang**
`docs/03-domain-source/api-chatbot.md` hanya mendokumentasikan 4 parameter GLOBAL (`role_title`, `employee_id` — khusus resolusi `own_property`, BUKAN filter baris; `property_id`; `limit`/`offset`). Whitelist parameter PER-VIEW yang dirujuk dokumen itu sendiri (`whitelist_<domain>.py`) sepenuhnya di luar repo ini (kode `chatbot_api` eksternal) — `arsitektur-ai-chatbot-rbac.md` Bagian 8 butir 5 eksplisit menandai ini "masih terbuka". Ini persis gap yang sudah dihadapi M2.4 untuk `employee_id` (`docs/keterbatasan-diterima.md` #10). Genuinely terbuka — tidak ada preseden milestone lain yang bisa ditarik untuk konvensi penamaan parameter API eksternal semacam ini.

**Proses**
Dua alternatif diajukan lewat `AskUserQuestion`: (A) nama kolom asli view (dari `DEFINISI_LENGKAP_VIEW`, M3.2) sebagai key param, suffix `_from`/`_to` untuk rentang tanggal — direkomendasikan karena nol nama dikarang, semua tertelusur ke katalog data final; (B) nama parameter generik seragam (`date_from`/`date_to` dst, sama untuk semua view) — ditolak sebagai rekomendasi karena frasa dokumen sumber sendiri ("filter lain PER WHITELIST DOMAIN") menyiratkan nama spesifik per-view, bukan nama generik seragam.

User merespons dengan memberikan dua file CSV (`properties.csv` — master 6 properti, `employees_deduped.csv` — master karyawan) yang setelah dibaca ternyata BUKAN dokumentasi kontrak parameter (keduanya data isi tabel, bukan skema API). Diklarifikasi langsung ke user — yang kemudian mengonfirmasi: file kontrak resmi `chatbot_api` MEMANG belum final ("masih menunggu project ini selesai untuk parameter pastinya"), dan secara eksplisit meminta (1) tetap lanjutkan dengan Opsi A sebagai basis kerja sekarang, DAN (2) buatkan dokumen kontrak parameter usulan terpisah, diterbitkan untuk direkonsiliasi dengan tim pembangun `chatbot_api` di akhir proyek.

**Keputusan yang Dipilih**
Opsi A (nama kolom asli per view) sebagai konvensi kerja M3.4, DITAMBAH `docs/kontrak-parameter-chatbot-api-usulan.md` (Checkpoint 2) — dokumen terpisah, eksplisit berstatus USULAN (bukan kontrak resmi), untuk direkonsiliasi dengan tim `chatbot_api` di akhir proyek.

**Alasan**
Opsi A tidak mengarang nama baru sama sekali — setiap key param bisa ditelusuri balik ke kolom nyata yang sudah final di katalog data (`katalog-data-chatbot.md`, diverifikasi tim database engineering). Menerbitkan dokumen kontrak terpisah (bukan cuma mencatat di `decisions.md` milestone) sesuai instruksi eksplisit user — memberi artefak konkret yang bisa langsung dibaca/direview tim eksternal tanpa perlu membaca kode Python proyek ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Nama parameter generik seragam (Opsi B)** — ditolak, tidak ada bukti `chatbot_api` menormalisasi nama param seperti ini; frasa dokumen sumber sendiri menyiratkan nama spesifik per-view.
- **Tunda implementasi M3.4 sampai kontrak resmi tersedia** — tidak eksplisit ditawarkan sebagai opsi ke user (mengingat instruksi user justru meminta lanjut dengan dokumen usulan, bukan menunda), tapi secara implisit ditolak oleh keputusan user untuk melanjutkan sekarang dengan konvensi provisional + dokumentasi formal, bukan memblokir pekerjaan.
- **Cukup catat konvensi di `decisions.md` milestone saja, tanpa dokumen terpisah** — ditolak eksplisit oleh instruksi user ("buatkan dokumen lagi khusus untuk kontrak dengan chatbot api").

**Dampak**
Menentukan bentuk `PARAM_WHITELIST_VIEW` (Checkpoint 2), isi prompt (Checkpoint 4), dan filter defensif (Checkpoint 5) — seluruhnya bergantung pada whitelist per-view yang pasti, bukan aturan longgar.

---

## Keputusan 2: `QueryEngineRequest` Reuse Persis, Tidak Didefinisikan Ulang

**Sumber Paksaan**
`src/schemas/verification_gate.py` (Milestone 2.4) sudah mengunci `QueryEngineRequest {domain, view_name, params}`, dikonsumsi `verifikasi_gate()` sebagai tipe murni. Catatan Serah Terima `rancangan-retrieval-query.md`: "skema `{domain, view_name, params}` adalah kontrak yang mengikat ketiga pekerjaan ini sekaligus, perubahan pada skema ini perlu disepakati bersama."

**Keputusan yang Diikuti**
`HasilPenyusunanRequest` (skema baru M3.4) mengimpor `QueryEngineRequest` langsung dari `src/schemas/verification_gate.py`, tidak mendefinisikan ulang.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by kontrak yang sudah terkunci, tidak ada alternatif dipertimbangkan.

---

## Keputusan 3: `domain` Diturunkan Kode via `view_ke_domain()[view_name]`, Tidak Diminta LLM

**Sumber Paksaan**
Preseden "jangan minta LLM menebak yang deterministik" (M1.6 Keputusan 7, `atomic_intent_id` digenerate kode bukan diminta LLM). Fungsi `view_ke_domain()` (`src/config/katalog_view.py`, M3.1, `@lru_cache(maxsize=1)`, mengembalikan `dict[str, Domain]` tanpa argumen) sudah tersedia.

**Keputusan yang Diikuti**
`susun_request_atomic_intent()` menurunkan `domain` lewat `view_ke_domain()[view_name]`, bukan bagian dari output LLM.

**Catatan Ketergantungan**
Dipanggil sebagai `view_ke_domain()[view_name]` (fungsi tanpa argumen mengembalikan dict penuh), BUKAN `view_ke_domain(view_name)`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Minta LLM mengembalikan domain juga** — ditolak, domain 100% derivable dari `view_name` yang sudah pasti benar (hasil M3.1-3.3), meminta LLM menebak sesuatu yang sudah pasti hanya menambah risiko halusinasi tanpa manfaat.

---

## Keputusan 4: Signature Menerima `view_name: str` Langsung, Bukan `HasilKecukupanStruktural` Penuh

**Sumber Paksaan**
`HasilKecukupanStruktural.view_name_final` (M3.3) bertipe `str | None`. Kalau M3.4 menerima wrapper penuh, ia harus menangani kasus `None` dengan nilai `StatusEksekusi` yang tidak ada satu pun cocok (bukan gagal teknis, bukan otorisasi, bukan ketergantungan — upstream genuinely tidak menemukan kandidat cukup, itu bukan kegagalan M3.4).

**Keputusan yang Diikuti**
`susun_request_atomic_intent(atomic_intent: AtomicIntent, view_name: str, tanggal_referensi: date | None = None) -> HasilPenyusunanRequest` — menerima `view_name` sudah pasti (non-`None`) langsung. Pengecekan `view_name_final is None` didorong ke pemanggil (M4.x, belum dibangun).

**Catatan Ketergantungan**
Menjaga ruang status `HasilPenyusunanRequest` tetap biner bersih (`BERHASIL`/`GAGAL_TEKNIS`).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Terima `HasilKecukupanStruktural` penuh, tambah nilai `StatusEksekusi` baru untuk kasus `None`** — ditolak, `StatusEksekusi` adalah enum bersama lintas-layer (`src/schemas/session_memory.py`), menambah nilai baru khusus M3.4 akan memecah konsistensi makna enum itu di seluruh pipeline.

---

## Keputusan 5: `tanggal_referensi` Dihitung Server-Side (Default WIB), Diparameterisasi

**Sumber Paksaan**
Tidak ada field tanggal/timestamp apa pun di `TurnPayload`/`HistoryTurn` (dicek eksplisit, nol hit) — resolusi tanggal relatif ("bulan lalu") butuh anchor "hari ini" yang tidak bisa diminta dari LLM (LLM tidak bisa dipercaya tahu tanggal sungguhan) maupun dari payload (tidak ada).

**Keputusan yang Diikuti**
`susun_request_atomic_intent()` menerima parameter opsional `tanggal_referensi: date | None`, default `datetime.now()` di zona **WIB (Asia/Jakarta, UTC+7)** kalau tidak diberikan. Dipilih WIB (bukan UTC) karena seluruh 6 properti (`properties.csv` yang diberikan user: Bali/Jakarta/Yogyakarta/Bandung/Lombok) beroperasi di konteks bisnis Indonesia.

**Catatan Ketergantungan**
**PROVISIONAL, dampak rendah** — hanya relevan di sekitar batas tengah malam; diparameterisasi (bukan hardcode) supaya gampang dikoreksi kalau konvensi zona waktu bisnis resmi ternyata berbeda.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Default UTC** — dipertimbangkan (satu-satunya preseden timestamp di repo, `src/db/models.py`, pakai UTC), ditolak karena konteks bisnis eksplisit Indonesia (seluruh nama kota di `properties.csv` adalah kota Indonesia) menjadikan WIB pilihan yang lebih masuk akal untuk resolusi "hari ini"/"bulan lalu" versi pengguna asli sistem.

---

## Keputusan 6: `HasilPenyusunanRequest.status` Biner, Validator Dua Arah

**Sumber Paksaan**
M3.4 adalah SATU pemanggilan LLM generate-only (M3.5 terpisah untuk verifikasi) — tanpa semantik batch/parsial/otorisasi/ketergantungan. Preseden `HasilVerifikasiGate` (M2.4) — juga status biner (`lolos: bool`) dengan `request_final` terikat validator dua arah, BUKAN pola satu-arah `HasilKecocokanMakna`/`HasilKecukupanStruktural` (M3.2/M3.3) yang punya kasus valid "berhasil tapi kosong" (kasus itu tidak berlaku di sini — `BERHASIL` di M3.4 SELALU berarti ada `request` konkret).

**Keputusan yang Diikuti**
`status ∈ {StatusEksekusi.BERHASIL, StatusEksekusi.GAGAL_TEKNIS}`. Validator dua arah: `status == BERHASIL` ⟺ `request is not None`.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Validator satu arah (pola `HasilKecocokanMakna`)** — ditolak, tidak ada kasus valid "`BERHASIL` tapi `request=None`" di M3.4 (beda dari M3.1 yang genuinely bisa "berhasil tanpa kandidat") — validator dua arah lebih ketat dan sesuai realita ruang keadaan M3.4.

---

## Keputusan 7: `employee_id`/`role_title`/`domain`/`view_name` Tidak Pernah Diisi LLM ke `params`

**Sumber Paksaan**
`employee_id` sudah jadi tanggung jawab penuh Verification Gate (M2.4 Cek 3, `tegakkan_constraint_cakupan_individu()` menimpa PAKSA kapan pun constraint cakupan-individu terdeteksi — mengisi dari M3.4 hanya berisiko konflik logic tanpa manfaat, karena akan ditimpa ulang). `role_title` adalah identity claim (bagian autentikasi request ke `chatbot_api`), bukan filter data. `domain`/`view_name` sudah diturunkan kode (Keputusan 3), bukan bagian `params`.

**Keputusan yang Diikuti**
Prompt secara eksplisit melarang LLM mengisi keempat key ini; filter defensif (Checkpoint 5, Keputusan 8) strip paksa kapan pun muncul di respons LLM, terlepas kepatuhan prompt.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by tanggung jawab M2.4 yang sudah ada, mengisi ulang dari M3.4 murni redundan dan berisiko.

---

## Keputusan 8: Filter Defensif Deterministik Pasca-LLM (Exact Match ke Whitelist)

**Sumber Paksaan**
KK2 sumber literal dan testable: "tidak ada parameter yang dikarang di luar yang tersedia." Preseden "jangan pernah percaya LLM sendirian untuk kriteria keberhasilan yang testable" — `verifikasi_bentuk_request_statis()` (M2.4), rule table (M3.3), default-aman M1.7.

**Keputusan yang Diikuti**
`_saring_params_tidak_dikenal(view_name, params)` membuang key mana pun yang TIDAK ada persis (exact match, bukan substring/fuzzy) di `PARAM_WHITELIST_VIEW[view_name]` (Checkpoint 2) — dijalankan SETELAH tiap panggilan LLM, sebelum `QueryEngineRequest` dibangun.

**Catatan Ketergantungan**
Kekuatan filter ini bergantung penuh pada akurasi `PARAM_WHITELIST_VIEW` (Checkpoint 2) — kalau whitelist salah (mis. lupa satu kolom sah), filter akan salah membuang param yang sebenarnya valid.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Andalkan instruksi prompt saja, tanpa filter kode** — ditolak, bertentangan langsung dengan prinsip "jangan percaya LLM sendirian untuk kriteria testable" yang sudah dipegang konsisten proyek ini.
- **Filter longgar (substring/fuzzy match terhadap nama kolom mentah)** — ditolak, kurang presisi dibanding exact match terhadap whitelist yang sudah diturunkan programatik; substring match berisiko false-positive (mis. `"revenue"` cocok substring untuk `"room_type_revenue_share_pct"` padahal beda kolom).

---

## Keputusan 9: Satu Pemanggilan LLM, Tanpa Retry, Tanpa Verifier Independen

**Sumber Paksaan**
`rancangan-retrieval-query.md` eksplisit: "Ini langkah 'menghasilkan' dalam pola generate-verify... dipisah dari langkah verifikasinya (Milestone 3.5) agar keduanya independen satu sama lain."

**Keputusan yang Diikuti**
`susun_request_atomic_intent()` melakukan SATU panggilan LLM, tanpa retry, tanpa verifikasi independen di dalam milestone ini. Kegagalan → `status=GAGAL_TEKNIS`, jujur tanpa memaksakan hasil.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced eksplisit oleh redaksi dokumen sumber sendiri.

---

## Keputusan 10: Model — Reuse Qwen3-32B, Konstanta Terisolasi Sendiri

**Sumber Paksaan**
Preseden "satu konstanta per konsumen" (M1.4 Keputusan 9) + preseden model chat/completion biasa tidak perlu perbandingan empiris baru (M1.6/M2.1/M2.3/M3.2/M3.3), beda dari model class embedding M3.1 yang genuinely dibandingkan.

**Keputusan yang Diikuti**
`OPENROUTER_MODEL_PENYUSUNAN_REQUEST = "qwen/qwen3-32b"` (`src/config/llm.py`, konstanta baru terisolasi meski nilai reuse).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by preseden konsisten, tidak ada indikasi kebutuhan M3.4 berbeda cukup jauh untuk menjustifikasi perbandingan model baru.

---

## Keputusan 11: Subpackage Baru `src/layers/query_engine/`

**Sumber Paksaan**
`rancangan-retrieval-query.md` header sendiri: "Cakupan pekerjaan: Retriever (...) dan Query Engine (penyusunan request, verifikasi bentuk request)" — dua komponen arsitektur berbeda meski satu PIC pemilik. Preseden `verification_gate/` dipisah dari `domain_gate/` (M2.4) meski juga satu PIC.

**Keputusan yang Diikuti**
`src/layers/query_engine/` (baru), BUKAN di bawah `src/layers/retriever/`.

**Catatan Ketergantungan**
`DEFINISI_LENGKAP_VIEW`/`CATATAN_LINTAS_DOMAIN` (M3.2, `src/layers/retriever/definisi_view.py`) tetap di-reuse LINTAS subpackage (import, bukan duplikasi) — konsisten preseden single-source-of-truth.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Taruh di `src/layers/retriever/`** — ditolak, dokumen sumber sendiri membedakan Retriever dan Query Engine sebagai dua komponen, preseden `verification_gate/` vs `domain_gate/` mendukung pemisahan.

---

## Keputusan 12: Observability — Span `"chat"` Literal + Konstanta `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` Baru

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 2, baris "Query Engine (Langkah 1 & 2)": `chat` ×2 (M3.4+M3.5 masing-masing satu), atribut `request.domain`, `request.view_name`, `prompt.id`/`prompt.version`.

**Keputusan yang Diikuti**
Span dibuka literal `"chat"` (bukan nama custom). `REQUEST_DOMAIN = "request.domain"`, `REQUEST_VIEW_NAME = "request.view_name"` ditambahkan ke `src/observability/genai_semconv.py`, mengikuti pola `PROMPT_ID`/`PROMPT_VERSION` (custom, tanpa prefix `gen_ai.`, karena bukan bagian OTel GenAI Semantic Conventions resmi).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced kontrak observability + preseden penamaan konstanta `PROMPT_ID`/`PROMPT_VERSION`.

---

## Keputusan 13: Dokumen Kontrak Parameter Usulan di Root `docs/`

**Sumber Paksaan**
`docs/03-domain-source/` eksplisit berstatus "final, bukan cakupan yang direvisi di sini" (dokumen dari tim database engineering) — dokumen kontrak usulan M3.4 adalah ARTEFAK YANG KITA TERBITKAN (proposal dari sisi `nirwana-chatbot`), bukan revisi dokumen final itu. Preseden `docs/keputusan-tertunda.md`/`docs/keterbatasan-diterima.md` — artefak project-wide di root `docs/`, bukan milik satu tim eksternal.

**Keputusan yang Diikuti**
`docs/kontrak-parameter-chatbot-api-usulan.md` (baru, root `docs/`).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Taruh di `docs/03-domain-source/`** — ditolak, folder itu eksplisit ditandai final/tidak direvisi, menaruh dokumen USULAN kita sendiri di situ akan mengaburkan status kepemilikan (siapa yang menulis, siapa yang final).

---

## Keputusan 14: Entri Baru `docs/keputusan-tertunda.md`

**Sumber Paksaan**
Instruksi eksplisit user (konvensi parameter belum final, akan direkonsiliasi di akhir proyek) + preseden entri #2 (model embedding M3.1, "belum ditutup permanen").

**Keputusan yang Diikuti**
Entri baru mencatat konvensi parameter sebagai provisional, dengan pemicu peninjauan eksplisit: (a) rekonsiliasi dengan tim `chatbot_api` di akhir proyek, (b) kegagalan `400` berulang di M4.x (Execution) yang menunjukkan pola nama parameter salah.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced instruksi eksplisit user.

---

## Keputusan 15: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M3.3.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Addendum Checkpoint 6-7 (Eval + Reliability Testing): Prompt Berakhir di Versi 2

Eval nyata (Checkpoint 6) menemukan model (prompt v1) salah menafsirkan "Nirwana" (nama grup, Nirwana Hospitality Group, disebut generik di kebutuhan seperti "venue yang dimiliki Nirwana") sebagai nilai filter `property_id` — padahal bukan nama properti spesifik. Direplikasi independen lewat Promptfoo (Checkpoint 7, skenario terpisah dengan teks sama). **Diperbaiki**: prompt v2 menambah aturan eksplisit membedakan nama grup vs nama properti spesifik. Hasil setelah perbaikan: eval nyata `params={}` benar, Promptfoo 4/4 lolos (dari 3/4).

Dua temuan LAIN dari eval Checkpoint 6 (skenario S04) SENGAJA TIDAK memicu revisi prompt lebih lanjut: (a) model memilih `property_name` alih-alih `property_id` untuk resolusi nama properti — ditinjau ulang BUKAN bug (keduanya parameter valid, model tidak pernah diberi tabel nama→kode di konteks prompt manapun); (b) nilai parameter nonsensikal (`occupancy_rate: "nilai_tunggal"`) — temuan kualitas nyata tapi SENGAJA dibiarkan, karena validasi kewajaran NILAI per parameter (bukan cuma nama key) adalah ruang kesalahan terbuka yang secara arsitektur menjadi tanggung jawab Milestone 3.5 (verifikasi independen), bukan celah M3.4 yang perlu ditambal sendiri. Detail lengkap: `evals/3.4-penyusunan-request/audit.md`.

**Opsi yang Dipertimbangkan tapi Ditolak (untuk addendum ini)**
- **Menambah validasi nilai per-parameter di M3.4 (Checkpoint 5) untuk mencegah kasus seperti temuan (b)** — dipertimbangkan, ditolak karena ruang kesalahan nilai (tipe data benar tapi makna salah, mis. "nilai_tunggal" masuk ke kolom numerik) genuinely terbuka (tidak bisa didaftar sebagai aturan tertutup di depan tanpa duplikasi logic verifikasi independen M3.5) — forced prinsip ruang-kesalahan-tertutup-vs-terbuka (`CLAUDE.md`), bukan celah yang lupa ditangani.
- **Berhenti di prompt v1 dan terima 3/4 Promptfoo sebagai temuan didokumentasikan (pola M3.2 14/16)** — dipertimbangkan, ditolak karena root cause temuan "Nirwana" jelas teridentifikasi dan mudah diperbaiki (beda dari temuan M3.2 yang lebih inheren) — mirror keputusan serupa M3.3 Addendum Checkpoint 7.

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Konvensi penamaan parameter: nama kolom asli + dokumen kontrak usulan terpisah | A | Checkpoint 2 |
| 2 | `QueryEngineRequest` reuse persis | B | Checkpoint 3 |
| 3 | `domain` diturunkan kode via `view_ke_domain()[view_name]` | B | Checkpoint 5 |
| 4 | Signature menerima `view_name: str` langsung, bukan wrapper `HasilKecukupanStruktural` | B | Checkpoint 5 |
| 5 | `tanggal_referensi` dihitung server-side, default WIB | B | Checkpoint 5 |
| 6 | `HasilPenyusunanRequest.status` biner, validator dua arah | B | Checkpoint 3 |
| 7 | `employee_id`/`role_title`/`domain`/`view_name` tidak pernah diisi LLM | B | Checkpoint 4-5 |
| 8 | Filter defensif deterministik pasca-LLM (exact match whitelist) | B | Checkpoint 5 |
| 9 | Satu pemanggilan LLM, tanpa retry, tanpa verifier independen | B | Checkpoint 5 |
| 10 | Model: reuse Qwen3-32B, konstanta terisolasi sendiri | B | Checkpoint 4 |
| 11 | Subpackage baru `src/layers/query_engine/` | B | Checkpoint 2-5 |
| 12 | Observability: span `"chat"` + `REQUEST_DOMAIN`/`REQUEST_VIEW_NAME` | B | Checkpoint 4-5 |
| 13 | Dokumen kontrak parameter usulan di root `docs/` | B | Checkpoint 2 |
| 14 | Entri baru `docs/keputusan-tertunda.md` | B | Checkpoint 2 |
| 15 | `decisions.md` sebagai Task pertama | B | Plan |
