# Decisions — Milestone 2.2: Membangun Pemeriksaan Otorisasi

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 2.2 — pekerjaan kedua PIC 2 (Domain Gate), konsumen langsung `list[AtomicIntentDomains]` (Milestone 2.1).

---

## Keputusan 1: Tidak Boleh Query `mart_cleaned.role_permissions` Produksi Langsung

**Sumber Paksaan**
`api-chatbot.md` baris 29-30: `authorize(role_title, domain) -- lookup mart_cleaned.role_permissions via kredensial chatbot_authz_reader (M4.4, SELECT-only ke tabel itu SAJA)`. Kredensial ini eksklusif milik Milestone 4.4 (PIC 4, Execution) — di luar cakupan proyek ini. Diperkuat `CLAUDE.md` "Batas Implementasi Saat Ini": "Jangan memodifikasi `chatbot_api`, 67 view `chatbot_views`, atau `role_permissions`... Konsumsi sebagai HTTP client saja."

**Keputusan yang Diikuti**
M2.2 tidak pernah membuka koneksi ke database produksi analytics (tempat `mart_cleaned.role_permissions` berada) — seluruh pemeriksaan otorisasi Lapis 1 menggunakan salinan matriks milik proyek ini sendiri (lihat Keputusan 10).

**Catatan Ketergantungan**
Melanggar ini berarti M2.2 butuh kredensial produksi yang memang sengaja tidak diberikan ke Lapis 1 (segregasi kredensial per pola akses, prinsip arsitektur `CLAUDE.md`: "kredensial least-privilege yang dipisah menurut pola akses").

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced oleh ketiadaan kredensial itu sendiri, bukan pilihan desain.

---

## Keputusan 2: Mekanisme Murni Deterministik, TANPA LLM

**Sumber Paksaan**
`rancangan-rbac-authorization.md`, Lingkup Milestone 2.2: "Ini murni pencocokan aturan berbasis lookup — bukan pemanggilan model AI — karena seluruh ruang kemungkinan hasilnya (role mana boleh domain apa) sudah terdaftar lengkap dan tertutup, tidak ada ambiguitas bahasa yang perlu ditafsirkan di titik ini." Konsisten Prinsip Arsitektur `CLAUDE.md` #3: verifikasi boleh murni deterministik hanya kalau ruang kesalahan tertutup — di sini persis kondisinya (20×10 = 200 kombinasi, seluruhnya sudah terdaftar).

**Keputusan yang Diikuti**
Tidak ada pemanggilan LLM sama sekali di M2.2 — beda total dari M2.1 (dua langkah LLM). Konsekuensi turunan: tidak ada `evals/2.2-.../` (lihat Keputusan 5), tidak ada keputusan model/provider yang perlu diajukan ke user.

**Catatan Ketergantungan**
Kalau dipaksa memakai LLM di sini, itu melanggar prinsip arsitektur langsung — ruang kesalahan tertutup yang "dipaksa" tetap pakai LLM adalah pemborosan tanpa manfaat penangkapan kesalahan tambahan.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced ganda oleh Lingkup dokumen sumber dan prinsip arsitektur.

---

## Keputusan 3: Output Granular PER DOMAIN, Bukan Keputusan Tunggal per Atomic Intent

**Sumber Paksaan**
Kriteria Keberhasilan 2 `rancangan-rbac-authorization.md`: "Kebutuhan dengan lebih dari satu domain... yang sebagian domainnya diizinkan dan sebagian ditolak, menghasilkan keputusan per-domain yang benar untuk masing-masing, bukan keputusan tunggal yang menyamaratakan semuanya."

**Keputusan yang Diikuti**
`AtomicIntentAuthorization.domain_decisions: list[DomainAuthorization]` — satu keputusan izin/tolak eksplisit PER domain, bukan satu bool tunggal untuk keseluruhan atomic intent.

**Catatan Ketergantungan**
Menyamaratakan ke satu keputusan (mis. tolak semua kalau ada satu domain ditolak) akan langsung melanggar KK2 dan berpotensi menolak domain yang sebenarnya diizinkan — kehilangan informasi yang downstream (Retriever M3.x, Interpretation M4.5) mungkin butuh untuk jawaban parsial.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu keputusan tunggal (all-or-nothing) per atomic intent** — ditolak, forced langsung bertentangan dengan KK2.

---

## Keputusan 4: Tidak Menangani `access_scope`/`own_property`/`all_properties`

**Sumber Paksaan**
`CLAUDE.md` "Batas Implementasi Saat Ini": "Jangan membangun ulang penegakan RBAC row-level (`property_id`/`own_property`/`all_properties`) — itu sepenuhnya tanggung jawab `chatbot_api`."

**Keputusan yang Diikuti**
`DomainAuthorization` hanya menjawab izin/tolak BINER per domain (role boleh/tidak boleh akses domain itu sama sekali) — TIDAK menentukan `own_property` vs `all_properties`, TIDAK me-resolve `property_id`. Itu murni Lapis 2 (`chatbot_api`, sudah selesai dan terverifikasi independen).

**Catatan Ketergantungan**
Membangun ulang logic `access_scope` di sini akan menduplikasi tanggung jawab Lapis 2 — persis anti-pola yang eksplisit dilarang prinsip arsitektur "Sistem ini adalah Lapis 1 RBAC, bukan pengganti Lapis 2."

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced eksplisit oleh batas implementasi yang dikunci `CLAUDE.md`.

---

## Keputusan 5: Tidak Ada Folder `evals/2.2-pemeriksaan-otorisasi/`

**Sumber Paksaan**
Konvensi project (`CLAUDE.md` tabel Struktur Repository, baris `evals/`): "Pengujian **perilaku LLM** (beda dari `tests/` unit test kode biasa)." M2.2 nol pemanggilan model AI (Keputusan 2).

**Keputusan yang Diikuti**
Verifikasi KK1 (200 kombinasi) dan KK2 (multi-domain campuran) dilakukan sepenuhnya lewat `tests/layers/domain_gate/test_otorisasi.py` — bukan `evals/`.

**Catatan Ketergantungan**
Membuat folder `evals/` untuk mekanisme yang tidak menyentuh LLM akan menyalahgunakan konvensi yang eksplisit didefinisikan project untuk tujuan lain (menguji perilaku probabilistik model, bukan logic deterministik).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced oleh definisi konvensi `evals/` itu sendiri.

---

## Keputusan 6: File Baru Masuk Subpackage `src/layers/domain_gate/` yang Sama dengan M2.1

**Sumber Paksaan**
`CLAUDE.md` tabel Struktur Repository, baris `src/`: "`src/layers/domain_gate/` menaungi Milestone 2.1 (awal, akan menaungi 2.2-2.3 juga)" — catatan ini ditulis eksplisit saat M2.1 ditutup, mengantisipasi M2.2.

**Keputusan yang Diikuti**
`src/layers/domain_gate/otorisasi.py` (baru) hidup di subpackage yang SAMA dengan `identifikasi.py`/`verifikasi_titik_buta.py`/`domain_gate.py` (M2.1) — bukan subpackage terpisah.

**Catatan Ketergantungan**
Membuat subpackage baru akan bertentangan langsung dengan catatan struktur yang sudah dikunci di penutupan M2.1.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced oleh keputusan struktur M2.1 yang sudah final.

---

## Keputusan 7: Skema Hasil di File `schemas/` Terpisah (`authorization.py`)

**Sumber Paksaan**
Preseden `src/schemas/matching.py` (M1.7) — mendapat file skema sendiri meski satu subpackage layer (`context_resolution/`) dengan `decomposition.py`/`session_memory.py` milik milestone lain. Pola project: satu mekanisme/milestone = satu file skema, meski berbagi subpackage layer yang sama.

**Keputusan yang Diikuti**
`DomainAuthorization`/`AtomicIntentAuthorization` di `src/schemas/authorization.py` (baru) — bukan ditambahkan ke `src/schemas/domain_gate.py` (M2.1).

**Catatan Ketergantungan**
Mencampur skema M2.1 dan M2.2 dalam satu file akan mengaburkan batas kepemilikan/tanggung jawab per milestone, menyulitkan penelusuran "skema mana milik mekanisme mana" di kemudian hari.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambahkan ke `schemas/domain_gate.py`** — dipertimbangkan (kedua milestone sama-sama "Domain Gate"), ditolak demi konsistensi preseden M1.7 yang memisahkan per mekanisme, bukan per layer arsitektur.

---

## Keputusan 8: Pola Seed Sekali-Jalan di `milestones/2.2-.../`, Bukan `src/`

**Sumber Paksaan**
Preseden identik `milestones/1.5-tarik-session-memory/seed_roles.py` — skrip migrasi data sekali-pakai disimpan di folder milestone, bukan jadi bagian runtime permanen `src/`.

**Keputusan yang Diikuti**
`milestones/2.2-pemeriksaan-otorisasi/seed_role_permissions.py`.

**Catatan Ketergantungan**
Tidak ada — pola sudah established dan tidak ada alasan menyimpang untuk kasus yang strukturnya identik (migrasi data referensi statis sekali jalan).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Taruh di `src/config/` atau `src/db/`** — ditolak, akan menyiratkan skrip ini bagian alur runtime aplikasi (dijalankan berulang), padahal ini murni migrasi data sekali-pakai — forced by preseden M1.5.

---

## Keputusan 9: Entri `GAGAL_TEKNIS` dari M2.1 Dilewati, Tidak Diproses M2.2

**Sumber Paksaan**
Forced oleh sifat data itu sendiri: `AtomicIntentDomains.domains` WAJIB kosong kalau `status=GAGAL_TEKNIS` (validator M2.1, `decisions.md` M2.1 Keputusan 6) — tidak ada domain untuk diperiksa otorisasinya. Konsisten preseden M2.1 sendiri yang juga memfilter (`PERLU_EKSEKUSI` saja yang diproses M2.1, `SELESAI` dilewati).

**Keputusan yang Diikuti**
`periksa_otorisasi_semua()` melewati (skip) entri `AtomicIntentDomains` berstatus `GAGAL_TEKNIS` — tidak menghasilkan `AtomicIntentAuthorization` untuk entri itu. Penanganan status `GAGAL_TEKNIS` yang perlu diteruskan ke user adalah tanggung jawab pipeline/Interpretation di luar cakupan M2.2.

**Catatan Ketergantungan**
Memaksa proses domain kosong akan menghasilkan `AtomicIntentAuthorization` dengan `domain_decisions=[]` yang tidak bermakna (tidak ada yang benar-benar diperiksa) — berpotensi disalahartikan downstream sebagai "semua domain diizinkan" (list kosong) padahal sebenarnya "tidak ada yang diketahui domainnya".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tetap proses dengan `domain_decisions=[]`** — ditolak, berisiko ambiguitas makna "kosong" di titik konsumsi berikutnya.

---

## Keputusan 10: Sumber Matriks — Tabel Baru di Supabase (Bukan Konstanta Python Statis)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Genuinely terbuka — M2.2 butuh salinan matriks `role_permissions` sendiri (Keputusan 1 di atas melarang query produksi langsung), tapi dokumen sumber tidak menentukan BENTUK salinan itu. Dua opsi sama-sama valid secara arsitektur: konstanta Python statis (preseden M2.1 untuk deskripsi domain) vs tabel Supabase baru (preseden M1.5 untuk daftar role).

**Keputusan yang Dipilih**
Tabel `role_permissions` baru di project Supabase milik proyek ini sendiri (BUKAN tabel `mart_cleaned.role_permissions` produksi), diakses via SQLModel, di-seed sekali lewat `seed_role_permissions.py`.

**Alasan**
Lebih auditable/queryable via SQL langsung (bisa `SELECT` untuk verifikasi ad-hoc tanpa baca kode), konsisten preseden M1.5 Keputusan 9 yang memigrasi `roles.yaml` ke DB dengan alasan serupa (satu sumber kebenaran, bukan config file yang berpotensi drift diam-diam dari kode yang membacanya). Data otorisasi juga lebih sensitif secara keamanan dibanding deskripsi domain M2.1 (yang murni teks grounding prompt) — layak mendapat perlakuan "data", bukan "konstanta kode yang di-deploy bersama aplikasi".

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Konstanta Python statis (dict di `src/`)** — lebih sederhana, tanpa round-trip DB atau migrasi/seed, preseden M2.1 (`DESKRIPSI_DOMAIN`). Ditolak user demi auditability dan konsistensi pola M1.5 untuk data otorisasi yang lebih sensitif.

**Dampak**
`RolePermissionRow` (`src/db/models.py`), `seed_role_permissions.py` (`milestones/2.2-.../`), `load_role_permissions()` (`src/config/role_permissions.py`) — seluruhnya butuh koneksi `DATABASE_URL` aktif, konsisten pola M1.5/M1.7.

---

## Keputusan 11: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M2.1.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Catatan Ketergantungan**
Konsisten `CLAUDE.md` Workflow Wajib butir 2.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Tidak boleh query `mart_cleaned.role_permissions` produksi | B | Plan |
| 2 | Mekanisme murni deterministik, tanpa LLM | B | Plan |
| 3 | Output granular per domain | B | Plan |
| 4 | Tidak menangani `access_scope`/`own_property`/`all_properties` | B | Plan |
| 5 | Tidak ada folder `evals/2.2-.../` | B | Plan |
| 6 | File baru di subpackage `domain_gate/` yang sama | B | Checkpoint 4-5 |
| 7 | Skema di file `authorization.py` terpisah | B | Checkpoint 2 |
| 8 | Pola seed sekali-jalan di `milestones/2.2-.../` | B | Checkpoint 3 |
| 9 | Entri `GAGAL_TEKNIS` dilewati | B | Checkpoint 5 |
| 10 | Sumber matriks: tabel Supabase baru | A | Checkpoint 3 |
| 11 | `decisions.md` sebagai Task pertama | B | Plan |
