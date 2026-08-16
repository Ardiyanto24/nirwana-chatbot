# Decisions — Milestone 2.4: Membangun Verification Gate

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 2.4 — pekerjaan keempat dan terakhir PIC 2, gerbang terakhir sebelum request dikirim ke `chatbot_api`.

---

## Keputusan 1: Konvensi Filter Cakupan-Individu — Reuse `employee_id`

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`, dua putaran).

**Latar Belakang**
Genuinely terbuka dan berdampak material — riset kontrak sebelum plan ditulis menemukan `docs/01-architecture/arsitektur-ai-chatbot-rbac.md` Bagian 8 (item 5) eksplisit menandai "Skema parameter per `view_name`" sebagai masih terbuka, dan `docs/03-domain-source/api-chatbot.md` **tidak mendokumentasikan parameter apa pun** untuk membatasi hasil ke data milik individu pemanggil sendiri. Satu-satunya ID individu di kontrak resmi adalah `employee_id`, yang saat ini HANYA dipakai `chatbot_api` untuk resolusi `property_id` (level properti, baris 64 `api-chatbot.md`), bukan filter baris level-individu. Contoh `staff_id=self` di dokumen arsitektur (baris 187) murni ilustrasi prosa, bukan parameter yang dikontrakkan secara resmi.

**Proses**
Putaran pertama `AskUserQuestion` mengajukan gap ini langsung. User bertanya klarifikasi ("berarti anda perlu seluruh employee id? dalam kontrak chatbot_api ada berapa employee id?") — dijelaskan bahwa `employee_id` di kontrak selalu merujuk SATU orang (si pemanggil sendiri), bukan daftar. User kemudian memberikan `employees_deduped.csv` (84 baris nyata, format `employee_id` persis `E####`, satu baris = satu karyawan, join eksplisit ke `role_title`/`property_id`/`property_name`) sebagai konfirmasi model data. Putaran kedua mengonfirmasi arah keputusan secara eksplisit.

**Keputusan yang Dipilih**
`employee_id` milik si pemanggil (sudah tersedia sejak `TurnPayload`, `src/schemas/turn_payload.py:31`, mengalir tanpa perubahan sejak M1.2) di-inject/ditimpa paksa ke `params["employee_id"]` request kalau `ConstraintCakupanIndividu.terdeteksi=True` (M2.3).

**Alasan**
`employee_id` adalah satu-satunya ID individu yang benar-benar ada di kontrak `chatbot_api`, sudah mengalir di seluruh pipeline (tidak perlu perubahan payload/skema hulu), dan model datanya (CSV nyata dari user) mengonfirmasi setiap `employee_id` memang unik per orang — pilihan paling defensif yang tersedia tanpa mengarang parameter baru yang `chatbot_api` (sistem eksternal sudah final) mungkin tidak kenali sama sekali.

**Status: PROVISIONAL, BELUM DIKONFIRMASI**
Tidak ada bukti/dokumentasi bahwa `chatbot_api` benar-benar MENERAPKAN filter baris berdasarkan `employee_id` untuk 9 view performa-individu (M2.3) — dokumen sumber hanya menegaskan `employee_id` dipakai untuk resolusi `property_id`. Risiko ini dicatat eksplisit sebagai keterbatasan diterima RISIKO TINGGI di penutupan milestone (`report.md` Bagian 5, `docs/keterbatasan-diterima.md` entri baru) — BUKAN diasumsikan pasti benar.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Mengarang nama parameter baru** (mis. `individual_scope_filter`) — ditolak, `chatbot_api` (eksternal, sudah final, di luar cakupan revisi proyek ini) hampir pasti tidak mengenali parameter yang tidak ada di kontraknya; mengirim parameter yang tidak dikenali tidak memberi jaminan apa pun.
- **Tunda seluruh M2.4 sampai kontrak dikonfirmasi tim database engineering** — dipertimbangkan sebagai opsi kedua di `AskUserQuestion` putaran pertama, tidak dipilih user; user memilih tetap lanjut dengan konvensi provisional yang didokumentasikan jujur.

---

## Keputusan 2: Tabel `employees` Supabase — Fixture Test SAJA, Bukan Dikonsultasi Produksi

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
User menyediakan `employees_deduped.csv` (84 baris) sebagai respons klarifikasi Keputusan 1, dan menawarkan opsi mengunggahnya ke Supabase.

**Keputusan yang Dipilih**
Tabel `employees` baru (SQLModel, mirror pola `roles`/`role_permissions`), diseed sekali dari CSV — dipakai KHUSUS sebagai fixture test M2.4 yang realistis (employee_id/role_title/property_id nyata, bukan karangan sintetis). Logic produksi `verifikasi_gate()` **TIDAK PERNAH** query tabel ini — `employee_id` caller sudah tersedia sebagai parameter biasa sejak `TurnPayload` (persis pola `role_title` di M2.1-2.3, yang juga tidak pernah di-lookup ulang dari tabel `roles` oleh layer domain_gate).

**Alasan**
Data nyata membuat test lebih meyakinkan (bukan `employee_id="E9999"` karangan yang bisa kebetulan benar meski logic-nya salah), konsisten preseden M1.5 (`roles`)/M2.2 (`role_permissions`) menyimpan referensi sebagai tabel Supabase yang auditable via SQL langsung.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tidak perlu tabel, cukup `employee_id` sintetis di test** — opsi eksplisit ditawarkan di `AskUserQuestion`, tidak dipilih user demi realisme fixture test.
- **Logic produksi query tabel `employees` untuk validasi `employee_id`** — dipertimbangkan implisit, ditolak: `employee_id` sudah divalidasi/tersedia dari `TurnPayload`, menambah query DB di jalur produksi untuk data yang sudah ada di parameter adalah pekerjaan berlebihan tanpa manfaat baru.

---

## Keputusan 3: Subpackage Baru `src/layers/verification_gate/`

**Sumber Paksaan**
Peta layer arsitektur (`arsitektur-ai-chatbot-rbac.md` Bagian 3): Verification Gate = Layer 7, entitas TERPISAH dari Domain Gate (Layer sebelumnya) meski sama-sama dimiliki PIC 2 (`rancangan-rbac-authorization.md` cakupan pekerjaan: "Domain Gate ... dan Verification Gate").

**Keputusan yang Diikuti**
File baru M2.4 masuk `src/layers/verification_gate/` (baru) — BUKAN ditambahkan ke `src/layers/domain_gate/` meski satu PIC.

**Catatan Ketergantungan**
Menyatukan keduanya akan mengaburkan batas layer arsitektur yang eksplisit dipisah dokumen sumber — Domain Gate *mendeteksi*, Verification Gate *menegakkan*, dua tanggung jawab konseptual berbeda meski satu pemilik.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambahkan ke `src/layers/domain_gate/`** — ditolak, bertentangan langsung dengan peta layer arsitektur yang sudah final.

---

## Keputusan 4: `QueryEngineRequest.params` Tetap `dict[str, Any]` Opaque

**Sumber Paksaan**
`arsitektur-ai-chatbot-rbac.md` Bagian 8 item 5 eksplisit: "Skema parameter per `view_name` (`whitelist_<domain>.py`) — perlu dibaca detail sebelum Retriever & Query Engine bisa diimplementasi." Milestone 3.x (yang akan memproduksi `params` nyata) belum dibangun; file `whitelist_*.py` tidak ada di repo ini (kode `chatbot_api` sepenuhnya eksternal).

**Keputusan yang Diikuti**
`params: dict[str, Any]` — tidak divalidasi granular per-nama-parameter per-view. Validasi M2.4 HANYA yang eksplisit disebut Lingkup dokumen sumber: `domain`/`view_name` valid secara struktural, `limit` (kalau ada) ≤ 1000.

**Catatan Ketergantungan**
Memaksakan skema `params` granular sekarang berarti mengarang struktur yang belum terdokumentasi di mana pun — berisiko salah dan perlu direvisi total begitu M3.x/skema resmi tersedia.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Definisikan skema `params` granular per domain sekarang** — ditolak, tidak ada sumber kebenaran yang bisa dirujuk; forced menunggu M3.x atau dokumentasi resmi `whitelist_<domain>.py`.

---

## Keputusan 5: `error.type` Kegagalan Cek 1/2/4 = `gagal_teknis`

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` baris 45: "Prinsip pengisian `error.type`: nilainya mengikuti skema `status` yang sudah dikunci ... (`berhasil`/`sebagian`/`ditolak_otorisasi`/`gagal_teknis`/`terblokir_ketergantungan`)." `CLAUDE.md` Prinsip Arsitektur: "`403`/`404` dari `chatbot_api` adalah sinyal bug prioritas tinggi ... dieskalasi langsung tanpa retry."

**Keputusan yang Diikuti**
Kegagalan cek 1 (bentuk statis), cek 2 (kepatuhan sumber), dan cek 4 (verifikasi kelengkapan) direkam `error.type=gagal_teknis` — BUKAN `ditolak_otorisasi` (sudah eksklusif dipakai M2.2 untuk penolakan RBAC).

**Catatan Ketergantungan**
Kegagalan struktural di M2.4 secara konseptual berarti ketidaksesuaian internal upstream (bug di Query Engine/Retriever yang menghasilkan request tidak konsisten) — bukan keputusan RBAC "role ini tidak boleh domain itu" seperti M2.2. Menyamakan keduanya akan mengaburkan makna `error.type` di observability.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **`ditolak_otorisasi`** — ditolak, secara semantik keliru (M2.4 bukan keputusan RBAC).
- **Nilai baru custom (mis. `gagal_verifikasi`)** — ditolak, `rancangan-observability-ai-chatbot.md` eksplisit mewajibkan reuse 5 nilai `StatusEksekusi` yang sudah dikunci, bukan menambah kosakata baru.

---

## Keputusan 6: `verification.check_name` — 4 Nilai Didefinisikan Eksplisit

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` baris 41 mewajibkan atribut `verification.check_name` tapi tidak mengenumerasi nilai apa pun yang valid.

**Keputusan yang Diikuti**
4 nilai: `bentuk_request_statis`, `kepatuhan_sumber`, `constraint_cakupan_individu`, `kelengkapan_penegakan` — persis mengikuti 4 pemeriksaan yang disebut Lingkup M2.4 sumber (`rancangan-rbac-authorization.md`).

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — penamaan langsung mengikuti urutan/istilah yang sudah dipakai dokumen sumber sendiri, tidak ada ambiguitas penamaan alternatif yang masuk akal.

---

## Keputusan 7: Tidak Ada Folder `evals/2.4-verification-gate/`

**Sumber Paksaan**
Konvensi project (`evals/` khusus perilaku LLM). M2.4 sepenuhnya deterministik, nol pemanggilan LLM (Lingkup sumber eksplisit: "sepenuhnya deterministik, tanpa pemanggilan model AI sama sekali").

**Keputusan yang Diikuti**
Verifikasi KK1-3 sepenuhnya lewat `tests/layers/verification_gate/` — preseden identik M2.2 Keputusan 5.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced oleh definisi konvensi `evals/` itu sendiri.

---

## Keputusan 8: `hire_date` Disimpan `str` Polos di Tabel `employees`

**Sumber Paksaan**
Data nyata `employees_deduped.csv`: 83 dari 84 baris berformat `YYYY-MM-DD`, SATU baris (`Prasetyo Safitri`, `E0553`) berformat `DD/MM/YYYY` (`20/08/2019`). Ditemukan saat meninjau CSV sebelum seed.

**Keputusan yang Diikuti**
Kolom `hire_date: str` (bukan tipe `date`/`datetime`) — nilai disimpan apa adanya dari CSV, tanpa parsing/normalisasi paksa.

**Catatan Ketergantungan**
Field ini tidak pernah dipakai logic M2.4 (murni untuk realisme fixture test, Keputusan 2) — memaksakan parsing berisiko crash saat seed (format campur) atau diam-diam menormalkan data yang sebenarnya tidak konsisten, bertentangan prinsip `CLAUDE.md` "Kejujuran terhadap keterbatasan."

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Parse ke tipe `date`, normalisasi baris yang formatnya beda** — ditolak, field tidak dipakai logic apa pun sehingga usaha normalisasi tidak sepadan, dan berisiko menyembunyikan temuan data quality yang sebaiknya tersurat.
- **Skip/tolak baris dengan format tanggal tidak konsisten saat seed** — ditolak, akan mengurangi jumlah fixture nyata tanpa manfaat (field tidak relevan ke tujuan tabel ini).

---

## Keputusan 9: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M2.3.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Konvensi filter cakupan-individu: reuse employee_id (PROVISIONAL) | A | Checkpoint 7-8 |
| 2 | Tabel employees Supabase, fixture test saja | A | Checkpoint 4, 8 |
| 3 | Subpackage baru verification_gate/ | B | Checkpoint 2-8 |
| 4 | params tetap dict opaque | B | Checkpoint 2, 5 |
| 5 | error.type = gagal_teknis | B | Checkpoint 8 |
| 6 | verification.check_name 4 nilai | B | Checkpoint 8 |
| 7 | Tidak ada folder evals/2.4-.../ | B | Plan |
| 8 | hire_date disimpan str polos | B | Checkpoint 4 |
| 9 | decisions.md sebagai Task pertama | B | Plan |
