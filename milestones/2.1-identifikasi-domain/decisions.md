# Decisions — Milestone 2.1: Membangun Identifikasi Domain dan Verifikasi Titik Buta

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 2.1 — pekerjaan LLM pertama PIC 2 (Domain Gate), konsumen langsung `list[AtomicIntentMatch]` (Milestone 1.7) dan kalimat mandiri (Milestone 1.4).

---

## Keputusan 1: Dua Pemanggilan LLM Terpisah (Identifikasi + Verifikasi Titik Buta)

**Sumber Paksaan**
`rancangan-rbac-authorization.md`, bagian Output Milestone 2.1 (baris 47): "Dua mekanisme berurutan (dua pemanggilan model AI): satu untuk identifikasi domain awal dari teks kebutuhan atomik, satu lagi yang secara independen menilai ulang untuk mencari domain yang mungkin terlewat".

**Keputusan yang Diikuti**
`identifikasi_domain()` dan `verifikasi_titik_buta()` sebagai dua fungsi/pemanggilan LLM terpisah, bukan digabung jadi satu prompt majemuk.

**Catatan Ketergantungan**
Menggabungkan jadi satu prompt akan menghilangkan independensi penalaran yang eksplisit diminta dokumen sumber ("proses yang independen dari proses berpikir langkah pertama") — satu prompt majemuk berisiko langkah kedua sekadar melanjutkan konteks penalaran langkah pertama dalam satu pass yang sama, bukan benar-benar mencari ulang dari sudut pandang baru.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by Output dokumen sumber secara eksplisit menyebut "dua pemanggilan".

---

## Keputusan 2: Verifikasi Titik Buta = Pencarian Independen Aditif (Union), Bukan Retry/Re-scoring

**Sumber Paksaan**
`rancangan-rbac-authorization.md` bagian Lingkup (baris 41): "langkah identifikasi awal sengaja diikuti langkah verifikasi terpisah yang mencari titik buta — bukan menilai ulang hasil yang sama, melainkan secara aktif mencari apa yang mungkin terlewat, sebagai proses yang independen dari proses berpikir langkah pertama."

**Keputusan yang Diikuti**
`verifikasi_titik_buta()` menerima `domain_awal` (hasil langkah 1) sebagai konteks, tapi outputnya adalah `domain_tambahan` — domain BARU yang ditemukan, bukan penilaian valid/invalid atas `domain_awal`. Hasil akhir = `domain_awal ∪ domain_tambahan` (union, dedupe), TANPA loop retry balik ke langkah 1.

**Catatan Ketergantungan**
Beda arsitektur eksplisit dari pola retry-dengan-feedback M1.6 (Langkah 5↔6, `decisions.md` M1.6 Keputusan 3) — pola itu lagipula sudah ditemukan tidak menunjukkan bukti perbaikan sama sekali di eval M1.6 (`docs/keterbatasan-diterima.md` #5), jadi tidak ada alasan menirunya di sini walau permukaannya mirip (generate-lalu-verify). Mengikuti pola retry M1.6 secara sembarangan akan salah menerapkan preseden yang justru sudah terbukti lemah.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Retry-dengan-feedback seperti M1.6** — ditolak, bertentangan langsung dengan kata-kata Lingkup sumber ("bukan menilai ulang") dan preseden M1.6 sendiri sudah menunjukkan pola ini tidak efektif.
- **Verifikasi titik buta menghasilkan valid/invalid seperti M1.6 Langkah 6** — ditolak, tidak sesuai framing dokumen sumber yang eksplisit minta "mencari apa yang terlewat" (positif/generatif), bukan menilai (evaluatif) hasil langkah 1.

**Dampak**
`AtomicIntentDomains.domains` (Checkpoint 2) adalah hasil union, bukan hasil langkah 1 yang "disetujui" langkah 2.

---

## Keputusan 3: Struktur Subpackage `src/layers/domain_gate/`, File Terpisah per Mekanisme

**Sumber Paksaan**
Preseden `milestones/1.6-decomposition/decisions.md` Keputusan 10 (layer/milestone dengan >1 mekanisme LLM jadi subpackage dengan file terpisah per langkah, supaya "tiap langkah bisa diuji/di-mock terpisah dengan jelas"). Diperkuat oleh Kriteria Keberhasilan 2 milestone ini sendiri: langkah verifikasi titik buta wajib bisa dipanggil terisolasi dengan hasil langkah pertama yang **sengaja dibuat tidak lengkap** dalam pengujian terkontrol — hanya bersih dicapai kalau kedua fungsi independen secara file/import, bukan digabung dalam satu fungsi besar.

**Keputusan yang Diikuti**
`src/layers/domain_gate/{__init__.py, konteks_domain.py, identifikasi.py, verifikasi_titik_buta.py, domain_gate.py}`.

**Catatan Ketergantungan**
Menggabungkan identifikasi dan verifikasi titik buta ke satu file (mengikuti pola `matching.py` M1.7 yang menggabungkan match+archive) akan tetap memungkinkan pengujian terisolasi secara teknis (fungsi privat tetap importable), tapi menyimpang dari preseden eksplisit M1.6 Keputusan 10 yang sudah menetapkan pola "subpackage multi-mekanisme = file terpisah" untuk kasus yang secara struktural identik (milestone dengan >1 mekanisme LLM independen).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu file `domain_gate.py` berisi kedua mekanisme + orkestrator (pola M1.7 `matching.py`)** — dipertimbangkan karena M1.7 juga preseden valid, tapi ditolak karena M1.7 hanya py SATU mekanisme LLM (matching), sedangkan M2.1 py DUA mekanisme LLM independen — situasi M2.1 lebih dekat ke M1.6 (3 mekanisme LLM, file terpisah) daripada M1.7.

---

## Keputusan 4: Domain sebagai Enum Tertutup 10 Nilai

**Sumber Paksaan**
`rancangan-rbac-ai-chatbot.md` Bagian 1-2: ruang domain sudah tertutup dan terdaftar lengkap — 6 domain operasional (`reservation`, `fnb`, `facility`, `spa_event`, `hr`, `financial`) tidak berubah dari skema lama, ditambah 4 kelompok granular hasil pemecahan `corporate_master` (`properties_ref`, `employees_directory`, `guests_pii`, `guests_profile`). Total 10, persis sama dengan yang dipakai `role_permissions` (`rancangan-rbac-authorization.md` baris 59: "20 role × 10 domain").

**Keputusan yang Diikuti**
`class Domain(str, Enum)` 10 nilai persis: `RESERVATION`, `FNB`, `FACILITY`, `SPA_EVENT`, `HR`, `FINANCIAL`, `PROPERTIES_REF`, `EMPLOYEES_DIRECTORY`, `GUESTS_PII`, `GUESTS_PROFILE`.

**Catatan Ketergantungan**
`role_permissions` (M2.2) hanya mengenal 10 domain ini — kalau `identifikasi_domain()`/`verifikasi_titik_buta()` menghasilkan string di luar set ini, itu PASTI hasil hallucinated LLM, bukan domain valid yang "terlewat ditambahkan ke skema" (lihat Keputusan 5).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by skema `role_permissions` yang sudah final dan teraudit tim database engineering, di luar cakupan revisi proyek ini.

---

## Keputusan 5: Bounds-Check Deterministik untuk Domain Hasil LLM di Luar Closed-Set

**Sumber Paksaan**
Preseden identik: M1.3 Keputusan 9 (dangling turn index), M1.6 Keputusan 7 (dangling local-index Langkah 5), M1.7 Keputusan bounds-check `candidate_index` (`_parse_and_decide`, `matching.py`).

**Keputusan yang Diikuti**
Domain string hasil LLM yang tidak match salah satu dari 10 nilai `Domain` di-drop (tidak diloloskan ke hasil akhir), dicatat sebagai span attribute anomali (`domain_gate.<langkah>.dropped_invalid_domains`). Tidak pernah crash, tidak pernah meloloskan nilai di luar closed-set ke `AtomicIntentDomains.domains`.

**Catatan Ketergantungan**
Konsisten dengan pola project-wide: kesalahan struktural murni (nilai di luar enum tertutup) ditangani deterministik tanpa LLM kedua, beda dari kesalahan makna (domain yang salah tapi valid secara string) yang memang jadi tanggung jawab `verifikasi_titik_buta()`.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by preseden bounds-check yang sudah konsisten dipakai di M1.3/M1.6/M1.7 untuk kelas masalah yang sama persis (LLM mengarang referensi/nilai di luar domain yang valid).

---

## Keputusan 6: Fallback Kegagalan Teknis Reuse `StatusEksekusi`, Bukan Field Boolean Baru

**Sumber Paksaan**
Prinsip Arsitektur `CLAUDE.md`: "Kejujuran terhadap keterbatasan — status non-normal, hasil parsial, penolakan, kegagalan teknis harus selalu tersurat ke user, tidak pernah disamarkan demi jawaban yang terlihat lengkap." Diperkuat preseden reuse kosakata bersama: `LabelBentukJawaban` (M1.6 Keputusan 8, reuse dari `session_memory.py` alih-alih didefinisikan ulang).

**Keputusan yang Diikuti**
`AtomicIntentDomains.status: StatusEksekusi` (reuse `src/schemas/session_memory.py`, M1.5) — bukan field `bool` baru semacam `gagal_teknis`. Pemetaan: `GAGAL_TEKNIS` kalau `identifikasi_domain()` gagal total (domain tidak bisa ditentukan sama sekali, `domains=[]`); `SEBAGIAN` kalau identifikasi awal sukses tapi `verifikasi_titik_buta()` gagal teknis (domain langkah 1 tetap dipakai, tapi belum diverifikasi independen); `BERHASIL` kalau keduanya sukses.

**Catatan Ketergantungan**
Fallback "domain kosong = aman" secara diam-diam akan **berbahaya**, bukan aman — domain kosong yang tidak ditandai eksplisit berisiko diperlakukan M2.2 sebagai "tidak ada domain yang perlu diperiksa otorisasinya", padahal sebenarnya berarti "sistem gagal menentukan domain apa pun", potensi kebocoran RBAC kalau permintaan tetap diteruskan tanpa pemeriksaan. Hanya 3 dari 5 nilai `StatusEksekusi` yang relevan di titik pipeline ini (`DITOLAK_OTORISASI` milik M2.2, `TERBLOKIR_KETERGANTUNGAN` tidak relevan konteks ini) — didokumentasikan eksplisit di docstring `src/schemas/domain_gate.py` supaya tidak membingungkan pembaca kode yang mengharapkan seluruh nilai valid di sini.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Field `bool` baru (`gagal_teknis: bool`)** — dipertimbangkan (lebih sederhana), ditolak karena menciptakan kosakata status kedua yang paralel dengan `StatusEksekusi` yang sudah dikunci project-wide, berisiko drift semantik antara dua cara berbeda menyatakan "gagal" di sistem yang sama.
- **Exception Python alih-alih nilai balik** — dipertimbangkan, ditolak karena tidak konsisten dengan pola fallback-aman project-wide (M1.7 `matching.py` mengembalikan nilai fallback, bukan raise, pada `APIError`) dan mempersulit `identifikasi_domain_semua()` memproses list campuran hasil sukses/gagal.

**Dampak**
`src/schemas/domain_gate.py` (Checkpoint 2), `src/layers/domain_gate/domain_gate.py` (Checkpoint 7).

---

## Keputusan 7: Model Diisolasi jadi Konstanta Baru per Konsumen

**Sumber Paksaan**
Preseden M1.4 Keputusan 9 dan M1.6 Keputusan 11: satu konstanta model per konsumen/milestone, meski nilainya kebetulan sama dengan konstanta lain, untuk menghindari coupling tak sengaja.

**Keputusan yang Diikuti**
`OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI` dan `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA` — konstanta baru di `src/config/llm.py`, terisolasi dari `OPENROUTER_MODEL_DECOMPOSITION`/`OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI` (M1.6) meski nilainya kebetulan sama (lihat Keputusan 9 di bawah).

**Catatan Ketergantungan**
Reuse konstanta M1.6 langsung akan menciptakan coupling tak sengaja — mengganti model Verifikasi Decomposition (M1.6) di masa depan berisiko diam-diam ikut mengganti model Verifikasi Titik Buta (M2.1) tanpa disadari.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse langsung `OPENROUTER_MODEL_DECOMPOSITION`/`OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI`** — ditolak, forced by preseden anti-coupling M1.4/M1.6.

---

## Keputusan 8: Span `chat` × 2 per Atomic Intent, Cakupan Terbatas ke Identifikasi (Bukan Lookup Otorisasi)

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` Bagian 2 baris 38: "Domain Gate | `chat` (identifikasi + verifikasi titik buta) + span non-LLM (lookup otorisasi) | + `rbac.domain`, `rbac.decision` (`allow`/`deny`), `error.type=ditolak_otorisasi` bila ditolak, penanda constraint cakupan-individu bila terdeteksi".

**Keputusan yang Diikuti**
M2.1 hanya mengimplementasikan DUA span `chat` (identifikasi + verifikasi titik buta) per atomic intent, dengan atribut `gen_ai.*` standar (pola `matching.py`/`decompose.py`). Span non-LLM lookup otorisasi beserta atribut `rbac.domain`/`rbac.decision`/`error.type=ditolak_otorisasi` **BUKAN cakupan M2.1** — itu tanggung jawab Milestone 2.2 (baris tabel yang sama sengaja menggabungkan span M2.1-2.3 karena satu baris tabel = satu "Layer" arsitektur, bukan berarti satu milestone).

**Catatan Ketergantungan**
Mengimplementasikan span `rbac.decision`/`error.type=ditolak_otorisasi` di M2.1 akan mendahului keputusan M2.2 (yang belum dikerjakan) dan berpotensi menciptakan kontrak yang harus direvisi ulang begitu M2.2 benar-benar dibangun.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada alternatif dipertimbangkan — forced by pembagian cakupan eksplisit `rancangan-rbac-authorization.md` (Lingkup M2.1 vs M2.2).

---

## Keputusan 9: Model M2.1 — Pola M1.6 (Qwen3-32B Identifikasi, DeepSeek V4 Pro Verifikasi Titik Buta)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Genuinely terbuka — tidak ada model/provider yang dikunci dokumen manapun untuk M2.1 khususnya (`CLAUDE.md`: model per langkah "boleh reuse salah satu konvensi ini... atau mengajukan pilihan baru kalau kebutuhannya beda — bukan otomatis dianggap final untuk seluruh proyek"). Dua preseden tersedia dengan argumen berlawanan: M1.6 (model beda untuk peran verifier independen) vs M1.7 (model sama, argumen risiko-asimetris-aman). M2.1's verifikasi titik buta lebih dekat secara sifat ke peran "mencari yang terlewat" (butuh sudut pandang berbeda) daripada M1.7's "menilai kecocokan makna sederhana".

**Keputusan yang Dipilih**
Qwen3-32B (`qwen/qwen3-32b`) untuk `identifikasi_domain()`; DeepSeek V4 Pro (`deepseek/deepseek-v4-pro`), `reasoning="high"`, untuk `verifikasi_titik_buta()`.

**Alasan**
Risiko M2.1 asimetris ke arah SEBALIKNYA dari M1.7: di M1.7, false negative (gagal match) aman/murah (fallback ke eksekusi ulang), false positive berbahaya. Di M2.1, false negative (domain terlewat tidak terdeteksi) justru berbahaya — berpotensi kebocoran RBAC kalau M2.2 tidak sempat memeriksa otorisasi domain yang sebenarnya tersentuh. Keragaman model ("otak" berbeda antara identifikasi dan pencari-titik-buta) mengurangi risiko blind spot berkorelasi — argumen persis yang sama dengan M1.6 Keputusan 2, dan di sini levelnya lebih tinggi karena taruhannya keamanan data, bukan sekadar kualitas dekomposisi bahasa.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Pola M1.7 (Qwen3-32B untuk kedua langkah)** — lebih murah/sederhana, tapi argumen risiko-asimetris-aman M1.7 tidak berlaku di M2.1 (asimetri terbalik, lihat Alasan).
- **Model/provider baru di luar kedua preseden** — tidak diajukan sebagai opsi konkret oleh user maupun peneliti; kedua preseden yang ada sudah punya argumentasi extend langsung ke kebutuhan M2.1.

**Dampak**
`OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI` = `qwen/qwen3-32b`, `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA` = `deepseek/deepseek-v4-pro` di `src/config/llm.py` (Checkpoint 3). `verifikasi_titik_buta()` (Checkpoint 6) perlu eksplisit set parameter `reasoning="high"` saat memanggil API, sama seperti `verifikasi_pemecahan()` M1.6.

---

## Keputusan 10: Granularitas Panggilan — Per Atomic Intent, Bukan Batch per Turn

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Genuinely terbuka — dua preseden berlawanan tersedia: M1.6 (Pemecahan memproses SEMUA atomic intent sekaligus dalam satu respons LLM terstruktur) vs M1.7 (`matching.py`, satu panggilan LLM per atomic intent). Trade-off nyata: batch lebih hemat biaya/latensi (2 panggilan per turn vs 2×N panggilan untuk N atomic intent), tapi per-item lebih mudah diuji/diisolasi dan konsisten preseden M1.7 untuk posisi pipeline yang serupa (pasca-Decomposition, beroperasi per atomic intent individual).

**Keputusan yang Dipilih**
Per atomic intent — `identifikasi_domain()` dan `verifikasi_titik_buta()` masing-masing dipanggil satu kali per atomic intent, bukan dibatch untuk seluruh atomic intent dalam satu turn.

**Alasan**
Identifikasi domain satu kebutuhan atomik secara logis independen dari kebutuhan atomik lain dalam turn yang sama (beda dari Pemecahan M1.6 yang inherently perlu melihat keseluruhan teks sekaligus untuk membagi kebutuhan majemuk) — lebih dekat ke posisi M1.7 (matching, pasca-Decomposition, per-item) daripada M1.6 (pra-Decomposition, perlu melihat keseluruhan). Prompt tetap sederhana (tidak perlu melacak domain per-item dalam satu respons terstruktur kompleks), dan memenuhi kebutuhan isolasi pengujian KK2 (Keputusan 3) secara alami.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Batch per turn (pola Pemecahan M1.6)** — lebih hemat biaya, tapi prompt lebih kompleks dan menyimpang dari preseden M1.7 untuk posisi pipeline yang setara; ditolak user demi konsistensi preseden dan kesederhanaan pengujian per-item.

**Dampak**
`identifikasi_domain_semua()` (Checkpoint 7) memanggil `identifikasi_domain_atomic_intent()` dalam loop Python biasa, bukan satu panggilan LLM batch.

---

## Keputusan 11: Cakupan Konteks Grounding — 10 Domain + Satu Contoh Cross-Domain Terdokumentasi, Bukan Seluruh 67 View

**Status:** Diputuskan sebelum implementasi (dari plan, berdasar riset katalog data — tidak diajukan lewat `AskUserQuestion` karena mudah direvisi/tidak mahal diubah kalau eval menunjukkan tidak cukup).

**Latar Belakang**
`katalog-data-chatbot.md` (67 view) hanya menandai SATU view eksplisit dengan penanda "Cross-domain": `v_reservation_gop_impact_monthly` (`gop_margin` berasal dari `financial`) — dikonfirmasi lewat pencarian literal string "Cross-domain" di seluruh dokumen, hanya satu hasil. Tidak ada penanda cross-domain lain di 66 view sisanya. Ini genuinely terbuka soal seberapa luas grounding yang perlu dimasukkan ke prompt: seluruh 67 view (grounding maksimal, prompt besar) vs kurasi (10 domain + pola umum + 1 contoh, prompt ringkas).

**Keputusan yang Dipilih**
Grounding (`konteks_domain.py`, Checkpoint 4) berisi: 10 nama+deskripsi domain, SATU contoh cross-domain terdokumentasi (`gop_margin`/`v_reservation_gop_impact_monthly`) sebagai ilustrasi prinsip umum (bukan daftar tertutup), dan aturan pemisahan kolom `guests_pii`/`guests_profile` verbatim dari `rancangan-rbac-ai-chatbot.md` Bagian 1.

**Alasan**
Mengingat hanya SATU kasus cross-domain yang benar-benar terdokumentasi di seluruh katalog, menyertakan seluruh 67 view hanya akan membengkakkan prompt tanpa menambah grounding cross-domain yang nyata (66 view lain tidak py penanda serupa untuk dijadikan contoh tambahan) — prinsip umum + satu ilustrasi konkret dinilai cukup untuk melatih pola pikir "cek kolom turunan", sementara kelengkapan berlebih (seluruh 67 view beserta kolomnya) berisiko justru mengalihkan perhatian model dari sinyal yang relevan (needle-in-haystack).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Sertakan seluruh 67 view + kolom sebagai konteks penuh** — ditolak, prompt jadi sangat besar (menaikkan biaya/latensi tiap panggilan) untuk manfaat grounding yang minim mengingat hanya 1 dari 67 view py penanda cross-domain eksplisit.
- **Hardcode HANYA nama view `v_reservation_gop_impact_monthly` tanpa prinsip umum** — ditolak, akan membuat kapabilitas identifikasi overfit ke satu kasus uji spesifik (KK1) alih-alih benar-benar mengenali pola "kolom turunan lintas-domain" secara umum seperti diminta Lingkup dokumen sumber.

**Dampak**
Dicatat sebagai risiko provisional di `report.md` (Checkpoint 12) — kemampuan generalisasi ke pola leakage lain di luar `gop_margin` belum benar-benar terbukti sampai eval (Checkpoint 9-11) menguji skenario sintetis kedua.

---

## Keputusan 12: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, berlaku sejak Milestone 1.4, dikonfirmasi preseden nyata M1.6 Keputusan 14 dan urutan commit M1.7 (`2dd65ca` "docs(milestone-1.7): decisions" adalah commit paling awal milestone itu).

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Catatan Ketergantungan**
Konsisten `CLAUDE.md` Workflow Wajib butir 2: "Setelah pilihan pengguna final, tulis keputusan di `decisions.md`... ditulis sebagai Task 1 dari breakdown plan (sebelum kode/skema/apa pun ditulis)."

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Keputusan 13 (Addendum): Migrasi Model Verifikasi Titik Buta — DeepSeek V4 Pro 0423 → DeepSeek V4 Pro 0813

**Status:** Diputuskan 2026-08-20, di luar siklus milestone ini (sudah closed) — perubahan cross-cutting terhadap 6 titik verifier DeepSeek V4 Pro project sekaligus, diinisiasi permintaan user, dikonfirmasi lewat `AskUserQuestion`.

**Latar Belakang**
User meminta migrasi biaya untuk 6 titik verifier project yang semula seragam `deepseek/deepseek-v4-pro` (versi `0423`): kombinasi antara `deepseek/deepseek-v4-flash-0731` (jauh lebih murah/cepat) dan `deepseek/deepseek-v4-pro-0813` (rilis resmi 2026-08-13, upgrade dari versi preview `0423`). Riset menemukan Artificial Analysis Intelligence Index kedua model nyaris identik (Flash 0731 = 52, Pro 0813 = 53), sementara lompatan skor Pro 0813 terkonsentrasi di benchmark coding/agentic/cyber yang tidak relevan untuk tugas verifier project ini. Pro 0813 juga LEBIH MAHAL dari Pro 0423 lama (+26% input, +90% output) — migrasi bukan downgrade seragam, melainkan realokasi berdasar risiko per titik.

**Keputusan yang Dipilih**
Konstanta `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA` (`verifikasi_titik_buta.py`) diubah dari `deepseek/deepseek-v4-pro` menjadi `deepseek/deepseek-v4-pro-0813` — **tetap tier Pro**, hanya upgrade versi.

**Alasan**
Keputusan 9 milestone ini eksplisit menandai risiko verifikasi titik buta ASIMETRIS ke arah "domain terlewat" (false-negative = domain yang seharusnya diperiksa lolos tanpa terdeteksi = potensi kebocoran otorisasi lintas-domain). Ini titik pencegah kebocoran RBAC paling awal di pipeline (Domain Gate). Mempertahankan tier Pro (versi terbaru 0813) menjaga margin keamanan yang sama seperti desain awal; premium biaya Pro 0813 vs Pro 0423 diterima karena taruhannya adalah kebocoran data lintas-role, bukan sekadar kualitas jawaban.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Migrasi ke Flash 0731 (ikut 3 titik simetris lain)** — ditolak, menghapus margin ekstra di titik yang eksplisit didokumentasikan asimetris/berisiko kebocoran RBAC (Keputusan 9 milestone ini).
- **Tetap di Pro 0423 (status quo)** — ditolak, versi preview lama tidak lagi jadi rilis utama DeepSeek per 2026-08-13; tidak ada alasan menahan versi lama saat versi lebih baru tersedia di tier harga yang sama (Pro).

**Dampak**
`src/config/llm.py` konstanta `OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA` diubah nilainya (docstring diperbarui, pointer ke keputusan ini). Tidak ada perubahan skema/signature/`reasoning="high"`/kontrak fungsi.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Dua pemanggilan LLM terpisah | B | Plan |
| 2 | Verifikasi titik buta = union aditif, bukan retry | B | Plan |
| 3 | Struktur subpackage `domain_gate/`, file terpisah | B | Plan |
| 4 | Domain sebagai Enum tertutup 10 nilai | B | Checkpoint 2 |
| 5 | Bounds-check domain di luar closed-set | B | Checkpoint 5-6 |
| 6 | Fallback kegagalan reuse `StatusEksekusi` | B | Checkpoint 2, 7 |
| 7 | Model diisolasi konstanta baru per konsumen | B | Checkpoint 3 |
| 8 | Span `chat` × 2, cakupan terbatas ke identifikasi | B | Plan |
| 9 | Model M2.1: pola M1.6 (Qwen3-32B + DeepSeek V4 Pro) | A | Plan |
| 10 | Granularitas: per atomic intent | A | Plan |
| 11 | Cakupan grounding: 10 domain + 1 contoh, bukan 67 view | A | Checkpoint 4 |
| 12 | `decisions.md` sebagai Task pertama | B | Plan |
| 13 | Addendum: migrasi model verifikasi titik buta Pro 0423 → Pro 0813 | A | Addendum 2026-08-20 |
