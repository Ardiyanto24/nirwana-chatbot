# Decisions — Milestone 2.3: Membangun Deteksi Constraint Cakupan-Individu

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 2.3 — pekerjaan ketiga PIC 2 (Domain Gate), konsumen langsung `list[AtomicIntentAuthorization]` (Milestone 2.2).

---

## Keputusan 1: Daftar Eksplisit 9 View Kategori "Performa Individu"

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Genuinely terbuka — satu-satunya area yang ditandai eksplisit masih terbuka di `CLAUDE.md` sejak penutupan M2.1/M2.2: "daftar eksplisit view kategori 'cakupan-individu' untuk Milestone 2.3 (perlu tinjauan langsung ke 67 view)". Dokumen sumber (`rancangan-rbac-authorization.md` Lingkup M2.3) dan dokumen arsitektur sengaja tidak menentukan daftar ini — "sengaja didiskusikan terpisah saat pengerjaan dimulai" (`rancangan-rbac-authorization.md` baris 115).

**Proses**
Ditinjau langsung ke `docs/03-domain-source/katalog-data-chatbot.md` (67 view). Kriteria yang dipakai: grain 1 baris = 1 staf/karyawan tertentu (bukan agregat tim/departemen/properti) DAN isinya metrik kerja/kehadiran/kinerja (bukan sekadar identitas). Hanya 2 dari 10 domain ditandai eksplisit py sensitivitas ini di Ringkasan 10 Domain (katalog baris 47 dan 49): `facility` ("Sedang (data performa individu staff)") dan `hr` ("Sedang–Tinggi").

**Keputusan yang Dipilih**
9 view:
- `facility` (4): `v_housekeeping_staff_daily`, `v_maintenance_technician_daily`, `v_lookup_housekeeping_log` (kolom `staff_id`), `v_lookup_maintenance_tickets` (kolom `assigned_staff_id`)
- `hr` (5): `v_hr_employee_monthly`, `v_hr_employee_performance_semester`, `v_hr_watchlist_monthly`, `v_lookup_staff_shifts`, `v_lookup_employee_performance`

**Alasan**
Dikonfirmasi user setelah penjelasan detail kriteria dan daftar kandidat — precise match dengan penandaan eksplisit di katalog data, tidak melebar ke domain yang tidak disebutkan sama sekali.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Menyertakan view agregat departemen/properti di domain `facility`/`hr`** (mis. `v_hr_attendance_daily`, `v_hr_performance_department_semester`, `v_maintenance_ticket_daily`) — ditolak, grain-nya bukan per-individu, tidak ada risiko "melihat data pribadi rekan kerja" di situ.
- **Memperluas ke domain lain** (mis. `financial` karena py `v_lookup_payroll` per-individu) — ditolak, katalog tidak menandai domain lain dengan pola sensitivitas performa-individu-staf ini; payroll adalah kategori sensitivitas berbeda (exclusivity domain, bukan cakupan-individu).

**Dampak**
`src/layers/domain_gate/konteks_cakupan_individu.py` (Checkpoint 3) menjadikan daftar ini sebagai grounding kedua prompt LLM (Checkpoint 4-5).

---

## Keputusan 2: Mekanisme Deteksi — LLM, Generate-Verify Dual-Call, Union Aditif

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Dokumen sumber sengaja membiarkan ini terbuka: "Bila mekanisme deteksi ini memakai pemanggilan model AI, system prompt-nya mengikuti konvensi..." (`rancangan-rbac-authorization.md` baris 82) — tidak menegaskan LLM wajib dipakai atau tidak.

**Alasan**
Menentukan apakah `teks_kebutuhan` menyentuh kategori performa-individu vs agregat-tim adalah soal pemahaman bahasa (tidak bisa diandalkan lewat keyword matching — "siapa staf tercepat" vs "berapa staf hadir hari ini" sama-sama menyebut "staf"), jadi ruang kesalahan TERBUKA, bukan tertutup — Prinsip Arsitektur `CLAUDE.md` #3 mewajibkan LLM independen untuk kasus ini, bukan deterministik. Asimetri risiko sama seperti M2.1 (bukan M1.7): false-negative di sini (constraint terlewat) = potensi kebocoran data performa staf lain ke sesama staf — bahaya nyata, bukan sekadar over-restrict yang aman. Karena itu pola yang dipilih persis M2.1 (identifikasi awal + verifikasi titik buta independen, union aditif — verifier HANYA bisa menambah, tidak pernah mengurangi), bukan pola M1.7 (single-call konservatif tanpa verifier kedua, cocok untuk risiko yang justru sebaliknya).

**Keputusan yang Dipilih**
Dua panggilan LLM independen per atomic intent: Langkah 1 deteksi awal (model `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI`, reuse Qwen3-32B) + Langkah 2 verifikasi titik buta independen (model `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI`, reuse DeepSeek V4 Pro `reasoning="high"`, model beda untuk keragaman peran verifier — pola identik M2.1). Hasil akhir `terdeteksi = hasil_awal.terdeteksi OR hasil_verifikasi.terdeteksi_tambahan`.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **LLM single-call konservatif tanpa verifier kedua (pola M1.7)** — ditolak, asimetri risikonya berlawanan arah dari M1.7 (di sana false-positive berbahaya, di sini false-negative berbahaya).
- **Deterministik murni tanpa LLM** — ditolak, ruang kesalahan bahasa yang perlu ditafsirkan (individu vs agregat) tidak bisa didaftar sebagai aturan eksplisit tertutup di depan; melanggar Prinsip Arsitektur #3 langsung kalau dipaksakan.

**Dampak**
Checkpoint 4 (Langkah 1), Checkpoint 5 (Langkah 2), Checkpoint 6 (orkestrator OR-merge) — dan konsekuensi turunan Keputusan 8, 11, 12 di bawah.

---

## Keputusan 3: "Staff" di Dokumen Sumber = Tier 7 Role, Ditranskripsi sebagai `frozenset` Eksplisit

**Sumber Paksaan**
`rancangan-rbac-ai-chatbot.md` baris 58-64 mendaftar 7 role yang namanya berakhiran "Staff": `Front Office Staff`, `F&B Staff`, `Housekeeping Staff`, `Maintenance Staff`, `Spa & Event Staff`, `HR Staff`, `Finance Staff`. Tidak ada role literal bernama persis "Staff" di antara 20 role — dokumen sumber M2.3 memakai "Staff" sebagai kata generik tier/kelompok (pola pemakaian sama seperti kolom "Pola akses properti" di Ringkasan 10 Domain katalog, yang juga memakai "Staff"/"Manager"/"Corporate" generik).

**Keputusan yang Diikuti**
Transkripsi manual ke `frozenset[str]` 7 role_title persis (bukan `role_title.endswith(" Staff")`) — ruang kesalahan tertutup (20 role final, `role_permissions` M2.2 sudah mengaudit seluruhnya), preseden ketelitian sama seperti transkripsi manual matriks `role_permissions` M2.2.

**Catatan Ketergantungan**
Kalau frozenset ini typo, unit test pre-filter (Checkpoint 6, Task 11) akan menangkapnya lewat pengecekan "LLM tidak dipanggil untuk role non-Staff" yang gagal secara jelas.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`role_title.endswith(" Staff")`** — lebih ringkas, tapi fragile: bergantung pada kebetulan penamaan (kalau role baru ditambahkan dengan nama berakhiran "Staff" tapi bukan tier operasional, atau sebaliknya, klasifikasi salah tanpa terdeteksi). Ditolak demi eksplisit dan robust terhadap perubahan penamaan di masa depan.

---

## Keputusan 4: Pre-Filter Role Staff-Tier SEBELUM Panggilan LLM

**Sumber Paksaan**
Output constraint HANYA relevan untuk 7 role Staff (Lingkup M2.3: "Kebutuhan dari role Manager/Corporate tidak mendapat constraint tambahan ini") — memanggil LLM untuk role lain adalah biaya sia-sia yang tidak pernah mengubah output. Preseden identik: M2.2 skip status=`GAGAL_TEKNIS` (M2.1), M1.7 filter status=`berhasil`.

**Keputusan yang Diikuti**
`deteksi_constraint_atomic_intent()` mengecek `role_title` terhadap frozenset Keputusan 3 SEBELUM memanggil Langkah 1/2 — kalau bukan Staff-tier, langsung `terdeteksi=False` tanpa panggilan LLM.

**Catatan Ketergantungan**
Ini JUGA yang membuktikan KK2 sumber ("role Manager/Corporate tidak menghasilkan constraint") bekerja lewat mekanisme yang bisa diverifikasi langsung (nol panggilan LLM), bukan cuma "kebetulan LLM menjawab tidak".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Selalu panggil LLM, filter hasilnya berdasarkan role setelahnya** — ditolak, boros biaya/latensi tanpa manfaat (constraint untuk non-Staff selalu dibuang), dan KK2 jadi bergantung pada perilaku model yang tidak deterministik alih-alih pre-filter yang pasti.

---

## Keputusan 5: Pre-Filter Domain `facility`/`hr` SEBELUM Panggilan LLM

**Sumber Paksaan**
Forced langsung oleh Keputusan 1: kategori "performa individu" HANYA eksis di domain `facility` dan `hr`. Atomic intent yang `domain_decisions` (M2.2) tidak py domain itu dengan `diizinkan=True` TIDAK MUNGKIN menyentuh kategori ini.

**Keputusan yang Diikuti**
Setelah lolos pre-filter role (Keputusan 4), cek juga apakah `domain_decisions` mengandung `Domain.FACILITY`/`Domain.HR` dengan `diizinkan=True` — kalau tidak, `terdeteksi=False` tanpa panggilan LLM.

**Catatan Ketergantungan**
Sama seperti Keputusan 4 — pre-filter ini yang membuktikan KK3 sumber ("kebutuhan yang tidak menyentuh kategori ini sama sekali tidak mendapat constraint apa pun") lewat mekanisme deterministik yang pasti untuk kasus domain-tidak-relevan, bukan cuma bergantung pada LLM menjawab benar.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tidak pre-filter domain, serahkan seluruhnya ke LLM** — ditolak, boros biaya untuk kasus yang jawabannya sudah pasti dari struktur data M2.2 sendiri.

---

## Keputusan 6: Skema Output Rata (Flat), Bukan Nesting `AtomicIntentAuthorization`

**Sumber Paksaan**
Preseden ketat lintas 2 milestone: `AtomicIntentDomains` (M2.1) tidak nesting parent Decomposition — selalu bawa `atomic_intent: AtomicIntent` mentah. `AtomicIntentAuthorization` (M2.2) tidak nesting `AtomicIntentDomains` — pola yang sama diulang. "Catatan Serah Terima" dokumen sumber menegaskan Retriever/Query Engine (M3.x) butuh BAIK daftar domain (M2.1-2.2) MAUPUN constraint (M2.3) sekaligus.

**Keputusan yang Diikuti**
`AtomicIntentConstraint` (`src/schemas/cakupan_individu.py`) membawa `atomic_intent: AtomicIntent` + `domain_decisions: list[DomainAuthorization]` (diteruskan dari M2.2) + `constraint: ConstraintCakupanIndividu` — flat, tidak nesting `AtomicIntentAuthorization` sebagai sub-objek.

**Catatan Ketergantungan**
Nesting akan memaksa konsumen hilir (Retriever/Query Engine) menavigasi struktur berlapis (`.atomic_intent_authorization.atomic_intent`) alih-alih akses langsung (`.atomic_intent`) — memutus konsistensi pola akses yang sudah established sejak M1.6.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Nesting `AtomicIntentAuthorization` sebagai field di dalam `AtomicIntentConstraint`** — dipertimbangkan (lebih eksplisit menunjukkan "hasil M2.2 dibungkus M2.3"), ditolak demi konsistensi preseden flat lintas M2.1→M2.2 yang sudah dua kali diulang tanpa pengecualian.

---

## Keputusan 7: Fail-Closed (Bukan Fail-Open) saat Kegagalan Teknis LLM

**Sumber Paksaan**
Prinsip Arsitektur `CLAUDE.md` "Kejujuran terhadap keterbatasan" + asimetri risiko yang sudah ditegaskan di Keputusan 2 (false-negative = bahaya kebocoran). Beda arah dari M1.7 (fail-safe ke "tidak ada match" karena risiko M1.7 justru sebaliknya — false-positive yang berbahaya di sana).

**Keputusan yang Diikuti**
Kalau Langkah 1 DAN Langkah 2 sama-sama gagal teknis (`gagal=True` — API error, parse error, `response.choices` kosong), `deteksi_constraint_atomic_intent()` tetap memasang `terdeteksi=True` dengan `alasan` eksplisit menyebut kegagalan teknis dan pemasangan konservatif — BUKAN default ke `terdeteksi=False`. Kegagalan teknis juga tercatat di span (`domain_gate.cakupan_individu.forced_fallback_reason`) untuk observability, TANPA field `status`/`StatusEksekusi` tambahan di skema (beda dari `AtomicIntentDomains`) — satu-satunya efek yang dikonsumsi hilir (M2.4) adalah `constraint.terdeteksi` itu sendiri, field status tambahan tidak akan pernah dibaca siapa pun.

**Catatan Ketergantungan**
Default aman untuk RBAC adalah OVER-restrict saat tidak yakin, bukan UNDER-restrict — kalau dibalik (fail-open), kegagalan teknis LLM yang seharusnya netral jadi celah kebocoran RBAC diam-diam.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fail-open (`terdeteksi=False` saat gagal teknis)** — ditolak, bertentangan langsung dengan asimetri risiko yang sudah ditetapkan Keputusan 2.
- **Tambah field `status: StatusEksekusi` mirror `AtomicIntentDomains`** — dipertimbangkan untuk konsistensi pola, ditolak karena tidak ada konsumen hilir yang membutuhkan granularitas itu (beda dari M2.1 di mana `SEBAGIAN` berarti "domain langkah 1 dipakai, belum diverifikasi independen" — informasi yang genuinely berguna; di M2.3 hasil akhirnya sudah pasti aman dipakai apa adanya).

---

## Keputusan 8: Model Constants Baru Terisolasi

**Sumber Paksaan**
Preseden eksplisit M1.4 Keputusan 9: "satu konstanta per konsumen, hindari coupling tak sengaja" — diikuti konsisten tiap milestone LLM baru sejak itu (M1.6, M1.7, M2.1).

**Keputusan yang Diikuti**
`OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI` dan `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI` ditambahkan ke `src/config/llm.py` sebagai konstanta baru, meski nilainya reuse persis (Qwen3-32B / DeepSeek V4 Pro `reasoning="high"`) dari konstanta M2.1.

**Catatan Ketergantungan**
Reuse konstanta M2.1 langsung akan meng-couple keputusan model M2.3 dengan M2.1 secara tidak sengaja — kalau nanti model M2.1 perlu diganti (mis. hasil eval baru), M2.3 ikut berubah tanpa keputusan sadar terpisah.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Reuse langsung `OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI`/`OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA`** — ditolak, forced preseden M1.4 Keputusan 9.

---

## Keputusan 9: File Baru Masuk Subpackage `domain_gate/` yang Sama

**Sumber Paksaan**
`CLAUDE.md` tabel Struktur Repository: "`src/layers/domain_gate/` menaungi Milestone 2.1-2.2 (akan menaungi 2.3 juga)".

**Keputusan yang Diikuti**
`konteks_cakupan_individu.py`, `deteksi_cakupan_individu.py`, `verifikasi_cakupan_individu.py`, `cakupan_individu.py` (orkestrator) — seluruhnya di `src/layers/domain_gate/`, prompt terkait di `src/prompts/domain_gate/`.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced oleh struktur yang sudah dikunci sejak penutupan M2.1.

---

## Keputusan 10: `evals/2.3-deteksi-cakupan-individu/` Dibuat

**Sumber Paksaan**
Konvensi project (`CLAUDE.md`, `evals/` khusus perilaku LLM). Beda dari M2.2 (nol LLM, tidak py `evals/`), M2.3 py 2 pemanggilan LLM per atomic intent (Keputusan 2) — forced membuat folder eval mengikuti konvensi yang sama seperti M1.6/M1.7/M2.1.

**Keputusan yang Diikuti**
Skenario eval mengikuti pola nyata `evals/2.1-identifikasi-domain/` (bukan template minimal) — sesuai memori kerja yang sudah established: baca isi folder eval milestone sebelumnya, bukan template kosong.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced oleh konvensi project dan preseden langsung M2.1 (mekanisme paling mirip: dua-langkah LLM union aditif).

---

## Keputusan 11: Prompt-File-First + Reliability Testing Promptfoo Natif Sejak Awal

**Sumber Paksaan**
`docs/01-architecture/rancangan-manajemen-prompt.md` — kontrak Manajemen Prompt (Fase 1+2) SELESAI sebelum M2.3 dimulai (commit `c38955a`, sebelum M2.3). M2.3 adalah milestone LLM PERTAMA yang dibangun setelah kontrak ini mengikat. Prinsip Fondasi 1 dokumen itu: prompt RBAC-sensitif (Domain Gate) "wajib lewat commit git yang direview" sejak lahir, bukan ditunda.

**Keputusan yang Diikuti**
Kedua prompt (Checkpoint 4-5) langsung ditulis sebagai file `src/prompts/domain_gate/*.md` (frontmatter `id`/`version`/`milestone`/`model_compat`/`description`, Jinja2) — TIDAK hardcode Python string dulu lalu retrofit belakangan (pola M1.3-M2.1 sebelum kontrak ini ada). Reliability testing Promptfoo (`prompt_reliability/domain_gate/*.promptfooconfig.yaml`, Checkpoint 10) dibangun sebagai bagian NATIF checkpoint milestone ini, reuse skenario `evals/2.3-.../` (Keputusan 10), bukan ditunda ke inisiatif retrofit terpisah seperti Fase 2 sebelumnya.

**Catatan Ketergantungan**
Kalau ditunda seperti pola lama, M2.3 akan jadi utang teknis kesembilan yang perlu diretrofit — persis situasi yang mendorong lahirnya kontrak Manajemen Prompt ini. Prompt Domain Gate M2.3 RBAC-sensitif setara M2.1 (menentukan constraint yang berdampak langsung ke kebocoran data performa individu) — kualifikasi penuh untuk "seluruh skenario, bukan subset" per `rancangan-manajemen-prompt.md` Bagian 5.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Hardcode dulu, retrofit nanti (pola lama M1.3-M2.1)** — ditolak, forced karena kontrak sudah mengikat SEBELUM milestone ini dimulai; tidak ada alasan mengulang utang teknis yang baru saja dilunasi.

---

## Keputusan 12: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M2.2.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Keputusan 13 (Addendum): Migrasi Model Verifikasi Cakupan Individu — DeepSeek V4 Pro 0423 → DeepSeek V4 Pro 0813

**Status:** Diputuskan 2026-08-20, di luar siklus milestone ini (sudah closed) — perubahan cross-cutting terhadap 6 titik verifier DeepSeek V4 Pro project sekaligus, diinisiasi permintaan user, dikonfirmasi lewat `AskUserQuestion`.

**Latar Belakang**
User meminta migrasi biaya untuk 6 titik verifier project yang semula seragam `deepseek/deepseek-v4-pro` (versi `0423`): kombinasi antara `deepseek/deepseek-v4-flash-0731` (jauh lebih murah/cepat) dan `deepseek/deepseek-v4-pro-0813` (rilis resmi 2026-08-13, upgrade dari versi preview `0423`). Riset menemukan Artificial Analysis Intelligence Index kedua model nyaris identik (Flash 0731 = 52, Pro 0813 = 53), sementara lompatan skor Pro 0813 terkonsentrasi di benchmark coding/agentic/cyber yang tidak relevan untuk tugas verifier project ini. Pro 0813 juga LEBIH MAHAL dari Pro 0423 lama (+26% input, +90% output) — migrasi bukan downgrade seragam, melainkan realokasi berdasar risiko per titik.

**Keputusan yang Dipilih**
Konstanta `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI` (`verifikasi_cakupan_individu.py`) diubah dari `deepseek/deepseek-v4-pro` menjadi `deepseek/deepseek-v4-pro-0813` — **tetap tier Pro**, hanya upgrade versi.

**Alasan**
Keputusan 2/8 milestone ini menandai risiko verifikasi cakupan-individu ASIMETRIS arah sama dengan verifikasi titik buta Domain Gate (M2.1 Keputusan 9): false-negative = constraint cakupan-individu terlewat = potensi staff melihat data performa staff lain (kebocoran RBAC lintas-individu, bukan cuma lintas-domain). Prinsip yang sama berlaku: mempertahankan tier Pro (upgrade ke 0813) menjaga margin keamanan, premium biaya vs Pro 0423 diterima karena taruhannya kebocoran data.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Migrasi ke Flash 0731 (ikut 3 titik simetris lain)** — ditolak, menghapus margin ekstra di titik yang eksplisit didokumentasikan asimetris/berisiko kebocoran RBAC (Keputusan 2/8 milestone ini).
- **Tetap di Pro 0423 (status quo)** — ditolak, versi preview lama tidak lagi jadi rilis utama DeepSeek per 2026-08-13.

**Dampak**
`src/config/llm.py` konstanta `OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI` diubah nilainya (docstring diperbarui, pointer ke keputusan ini). Tidak ada perubahan skema/signature/`reasoning="high"`/kontrak fungsi.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Daftar eksplisit 9 view kategori performa individu | A | Checkpoint 3 |
| 2 | Mekanisme LLM generate-verify dual-call, union aditif | A | Checkpoint 4-6 |
| 3 | "Staff" = tier 7 role, frozenset eksplisit | B | Checkpoint 6 |
| 4 | Pre-filter role Staff-tier sebelum LLM | B | Checkpoint 6 |
| 5 | Pre-filter domain facility/hr sebelum LLM | B | Checkpoint 6 |
| 6 | Skema output rata (flat), bukan nesting | B | Checkpoint 2 |
| 7 | Fail-closed saat kegagalan teknis LLM | B | Checkpoint 6 |
| 8 | Model constants baru terisolasi | B | Checkpoint 3 |
| 9 | File baru di subpackage `domain_gate/` yang sama | B | Checkpoint 3-6 |
| 10 | `evals/2.3-.../` dibuat | B | Checkpoint 9 |
| 11 | Prompt-file-first + Promptfoo natif sejak awal | B | Checkpoint 4-5, 10 |
| 12 | `decisions.md` sebagai Task pertama | B | Plan |
| 13 | Addendum: migrasi model verifikasi cakupan individu Pro 0423 → Pro 0813 | A | Addendum 2026-08-20 |
