# Decisions — Milestone 1.5: Membangun Penarikan Data dari Session Memory

## Keputusan 1: Database — Supabase (Project Sama dengan Rencana Milestone 5.x/6.x)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`; ini penyelesaian keputusan tertunda #1 `docs/keputusan-tertunda.md`, diinisialisasi Milestone 1.2).

**Latar Belakang**
Milestone 1.2 (Keputusan 5) sengaja menunda keputusan database utuh proyek ke awal implementasi Milestone 1.5, karena skema/pola akses/TTL Session Memory baru jelas di titik ini. User sudah menyiapkan project Supabase sebelum plan ditulis. Klarifikasi lanjutan dibutuhkan karena proyek ini juga sudah merencanakan Supabase untuk tujuan lain sama sekali (dashboard observability publik Milestone 5.x + custom exporter Milestone 6.x, lihat `rancangan-observability-ai-chatbot.md` Bagian 4-5) — perlu dipastikan apakah ini project yang sama atau berbeda.

**Keputusan yang Dipilih**
Supabase (Postgres terkelola) — **project yang sama** dengan yang direncanakan untuk Milestone 5.x/6.x, dikonfirmasi eksplisit user.

**Alasan**
User sudah menyiapkan project ini. Karena project sama dipakai bersama rencana M5/M6, ada kebutuhan koordinasi penamaan tabel (lihat Keputusan 5) supaya tidak bertabrakan dengan skema `traces`/`spans` yang sudah "dipesan" secara konsep di dokumen observability.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **SQLite (file lokal)** — direkomendasikan awal (zero-config, tidak perlu container/service terpisah, cocok skala solo-project). Ditolak karena user sudah menyiapkan Supabase.
- **PostgreSQL via Docker Compose lokal** — alternatif kedua yang diajukan (konsisten pola `infra/observability/`). Ditolak dengan alasan sama.
- **Project Supabase terpisah khusus data aplikasi** — sempat jadi opsi klarifikasi (pemisahan data aplikasi vs observability lebih bersih secara konseptual), tapi user memilih memakai project yang sama dengan rencana M5/M6.

**Dampak**
Perlu penamaan tabel yang jelas terpisah dari skema observability masa depan (Keputusan 5). Dicatat sebagai dependency lintas-milestone — kalau skema `rancangan-observability-ai-chatbot.md` Bagian 4 berubah nanti (M5/M6), perlu dicek ulang tidak bertabrakan dengan tabel M1.5.

---

## Keputusan 2: Library Akses Database — SQLModel

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Perlu cara mengakses Postgres (Supabase) dari Python. Proyek ini sudah pakai Pydantic native di seluruh schema (`TurnPayload`, `RewriteResult`, `TurnDependencyResult`).

**Keputusan yang Dipilih**
SQLModel.

**Alasan**
Dibuat oleh pembuat FastAPI, secara eksplisit didesain menyatukan Pydantic+SQLAlchemy — fit alami dengan stack yang sudah dipakai proyek ini. Bekerja transparan di atas koneksi Postgres standar, termasuk Supabase (Supabase mendukung koneksi client Postgres apa pun, bukan cuma lewat REST/PostgREST-nya sendiri).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Raw SQL (`psycopg` langsung, tanpa ORM)** — kontrol penuh atas query, dependency minimal. Ditolak: lebih banyak boilerplate manual untuk serialize/deserialize field JSON (`nilai_hasil`, `catatan_interpretasi`) ke/dari Pydantic schema, tanpa manfaat nyata untuk kebutuhan proyek ini yang masih sederhana (dua tabel, query dasar).

**Dampak**
`psycopg[binary]` tetap jadi dependency (driver yang dipakai SQLAlchemy/SQLModel di bawahnya untuk koneksi Postgres) — lihat Keputusan 8.

---

## Keputusan 3: `roles.yaml` (Milestone 1.2) Dimigrasi ke Database

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`; ini bagian kedua penyelesaian keputusan tertunda #1).

**Latar Belakang**
Milestone 1.2 (Keputusan 5) eksplisit menyisakan evaluasi ini untuk "awal implementasi Milestone 1.5": apakah `src/config/roles.yaml` (20 baris statis daftar `role_title`) sebaiknya dipindah ke database yang sama dengan Session Memory begitu ada, atau tetap sebagai file config terpisah.

**Keputusan yang Dipilih**
Dimigrasi ke database (tabel `roles` di Supabase yang sama).

**Alasan**
User memilih migrasi untuk admin terpusat — satu tempat mengelola seluruh data referensi/state proyek, bukan tersebar file config + database.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tetap `roles.yaml`** — direkomendasikan awal (20 baris jarang berubah, alasan asli Keputusan 5 M1.2 soal kesederhanaan belum berubah secara objektif). Ditolak, user memilih migrasi untuk admin terpusat.

**Dampak**
`src/config/roles.py` diubah query DB (Checkpoint 9), `roles.yaml` dihapus setelah migrasi terverifikasi ganda (Checkpoint 10) — lihat Keputusan 9. Ini juga berarti Input Layer (Milestone 1.2, sebelumnya murni in-memory) sekarang transitif bergantung pada database — dampak dan mitigasinya dibahas eksplisit di Keputusan 9.

---

## Keputusan 4 (Forced): Store + Retrieve Dua-duanya Dibangun di Milestone Ini

**Sumber Paksaan:** Output Milestone 1.5 sendiri (`rancangan-context-decomposition.md`): "Mekanisme **penyimpanan dan pengambilan** Session Memory yang bisa dipanggil dengan referensi sesi dan turn".

**Keputusan yang Diikuti:** `store_session_memory()` dan `retrieve_session_memory()` keduanya diimplementasikan di M1.5, meski peran resmi M1.5 di pipeline 9-layer hanya "Langkah 3b — Tarik Data" (retrieve). Store dibutuhkan sebagai utilitas pendukung supaya Kriteria Keberhasilan M1.5 sendiri bisa dibuktikan (butuh data yang "memang pernah dieksekusi dan tersimpan").

**Catatan Ketergantungan:** Pemanggil produksi sisi store yang sesungguhnya (Execution, Milestone 4.5) baru datang belakangan — mekanismenya lahir di sini, pemakaiannya di pipeline nanti.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by Output milestone doc sendiri.

---

## Keputusan 5 (Forced): Penamaan Tabel `session_memory_packages` dan `roles`

**Sumber Paksaan:** Keputusan 1 (project Supabase sama dengan rencana M5/M6) + skema tabel `traces`/`spans` yang sudah tercantum di `rancangan-observability-ai-chatbot.md` Bagian 4.

**Keputusan yang Diikuti:** Nama tabel M1.5 dipilih eksplisit tidak bertabrakan dengan nama yang sudah "dipesan" secara konsep untuk skema observability M5/M6.

**Catatan Ketergantungan:** Kalau skema Bagian 4 dokumen observability berubah nanti, perlu dicek ulang tidak ada tabrakan baru dengan `session_memory_packages`/`roles`.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada alternatif dipertimbangkan — forced by kebutuhan menghindari tabrakan nyata dalam satu project Supabase yang sama.

---

## Keputusan 6 (Forced): Hanya Span `memory.retrieve` yang Wajib

**Sumber Paksaan:** Output Milestone 1.5 + tabel kontrak observability (`rancangan-observability-ai-chatbot.md` baris 35) — satu-satunya span M1.5 yang disebut eksplisit.

**Keputusan yang Diikuti:** `retrieve_session_memory()` memancarkan span `memory.retrieve` (`session.id`, `turn.index`, jumlah atomic intent ditemukan). `store_session_memory()` TIDAK diinstrumentasi span khusus — tidak ada span "store" di kontrak manapun (dicek juga baris Execution/`execute_tool`, tidak menyebutnya).

**Catatan Ketergantungan:** Kalau Milestone 4.5 (Execution, pemanggil produksi store) nanti butuh span sendiri untuk operasi simpan, itu jadi kontrak milik milestone tersebut, bukan diwariskan dari sini.

> **Koreksi (Milestone 4.3, 2026-08-17):** "Milestone 4.5" di atas SALAH NOMOR — sesuai `rancangan-execution-interpretation.md` yang jadi rujukan resmi, milestone penyimpanan paket ke Session Memory adalah **4.3** ("Membangun Penyimpanan Paket ke Session Memory"), bukan 4.5 ("Verifikasi Kesetiaan Data dan Penyusunan Visualisasi" — pekerjaan berbeda sama sekali). Span `memory.store` benar-benar ditambahkan di Milestone 4.3, lihat `milestones/4.3-penyimpanan-paket-session-memory/decisions.md` Keputusan 5. Entri ini dipertahankan apa adanya (bukan ditulis ulang) sesuai prinsip `CLAUDE.md` menjaga jejak sejarah.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada.

---

## Keputusan 7 (Forced): `sumber: str` Bebas, Bukan Enum

**Sumber Paksaan:** `arsitektur-ai-chatbot-rbac.md` §7 — nilai `sumber` bisa `"eksekusi_baru"` ATAU string dinamis `"session_memory (turn N)"` dengan N konkret.

**Keputusan yang Diikuti:** Field `sumber` bertipe `str` bebas di schema maupun kolom DB — beda dari `label_bentuk_jawaban`/`status` yang genuinely tertutup jadi `Enum` (lihat Keputusan 8).

**Catatan Ketergantungan:** Validasi nilai `sumber` yang benar adalah tanggung jawab penulis (Milestone 1.7 atau 4.5 nanti), bukan M1.5 yang hanya menyimpan/mengembalikan apa adanya.

> **Koreksi (Milestone 4.3, 2026-08-17):** "4.5" di atas juga SALAH NOMOR, sama seperti Keputusan 6 — penulis produksi `sumber="eksekusi_baru"` adalah Milestone **4.3**, bukan 4.5. Lihat catatan koreksi di Keputusan 6.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced oleh sifat dinamis nilai yang sudah dikunci dokumen sumber.

---

## Keputusan 8 (Forced): Struktur Kode dan Pemisahan Row DB vs Schema Publik

**Sumber Paksaan:** Preseden separation-of-concern yang sudah dipakai proyek (`src/config/` vs `src/observability/` vs `src/schemas/` vs `src/layers/`) + preseden `RewriteResult`/`TurnDependencyResult` (fungsi layer selalu mengembalikan objek `src/schemas/` murni, bukan objek framework-spesifik).

**Keputusan yang Diikuti:**
- `src/config/database.py` — `DATABASE_URL` + `get_engine()`, mirror pola `src/config/llm.py`.
- `src/db/models.py` (folder baru) — tabel SQLModel `table=True`: `SessionMemoryPackageRow`, `RoleRow`. `nilai_hasil`/`catatan_interpretasi` sebagai kolom JSON (forced oleh tipe §7: "data terstruktur, bukan teks" / `string[]`).
- `src/schemas/session_memory.py` — `SessionMemoryPackage` Pydantic murni (TANPA `table=True`), enum `LabelBentukJawaban`/`StatusEksekusi`. Row DB dan schema publik SENGAJA dipisah — kalau digabung jadi satu kelas SQLModel `table=True`, objek yang dikembalikan `retrieve_session_memory()` berisiko jadi instance SQLAlchemy "terlepas sesi" (detached instance) begitu koneksi ditutup, berpotensi error kalau field lazy-loaded diakses belakangan oleh business logic. Memisahkan row dari schema publik menghindari risiko ini sejak desain, sekaligus konsisten pola `RewriteResult`/`TurnDependencyResult`.
- `src/layers/context_resolution/session_memory.py` — fungsi layer (`store_session_memory()`, `retrieve_session_memory()`), konversi row↔schema, span `memory.retrieve`.
- Migrasi skema: `SQLModel.metadata.create_all(engine)`, TANPA Alembic — belum ada riwayat migrasi untuk dikelola (skema pertama), menambah Alembic sekarang adalah kompleksitas prematur (YAGNI).

**Catatan Ketergantungan:** Kalau skema berkembang nanti (kolom baru, tabel baru lain), Alembic bisa diperkenalkan saat itu — bukan sekarang.

**Opsi yang Dipertimbangkan tapi Ditolak:** Satu kelas SQLModel `table=True` merangkap schema publik (pola "single model" yang didukung SQLModel) — ditolak karena risiko detached-instance dan mencampur concern persistence dengan bentuk data publik, seperti dijelaskan di atas.

---

## Keputusan 9 (Forced): `roles.yaml` Dihapus Setelah Migrasi Terverifikasi Ganda, `@lru_cache` Dipertahankan

**Sumber Paksaan:** Prinsip single-source-of-truth (membiarkan dua sumber yang sama-sama "valid" tapi bisa drift adalah anti-pattern) + Keputusan 3 (migrasi dipilih user).

**Keputusan yang Diikuti:** `roles.yaml` dihapus HANYA setelah dua verifikasi lolos: (a) regresi penuh `tests/layers/test_input_layer.py` (M1.2, 12 test, fungsional), (b) perbandingan data langsung 20 role DB vs `roles.yaml` (persis sebelum penghapusan, sebagai pengaman terakhir atas tindakan ireversibel). `load_valid_roles()` tetap `@lru_cache(maxsize=1)` — DB cuma diquery sekali per siklus hidup proses, BUKAN per-request.

**Catatan Ketergantungan:** Migrasi ini membuat Input Layer (sebelumnya murni in-memory/instan, Keputusan 8 M1.2: "murni mekanis") sekarang transitif bergantung pada koneksi database saat cold-start. `@lru_cache` adalah mitigasi eksplisit dan sadar atas kekhawatiran ini — bukan diabaikan. Dicatat sebagai risiko di plan (lihat Risiko & Mitigasi).

**Opsi yang Dipertimbangkan tapi Ditolak:** Hapus langsung setelah satu kali verifikasi (pola awal draf plan) — direvisi jadi verifikasi ganda + urutan hapus SETELAH regresi (bukan sebelum) setelah diskusi lebih lanjut soal keamanan checkpoint (lihat `logs.md` Checkpoint 10 untuk kronologi revisi ini).

**Dampak:** `tests/layers/test_input_layer.py` (M1.2) yang sebelumnya tidak butuh infra apa pun sekarang transitif butuh `DATABASE_URL` tersedia.

---

## Keputusan 10 (Forced): Kredensial Database via `.env`, Tanpa Folder `evals/`, Tanpa TTL, Tidak Wired HTTP

**Sumber Paksaan:** Beberapa prinsip/preseden sekaligus, dikelompokkan karena masing-masing forced tanpa alternatif nyata:
- **`.env`/`.env.example`: `DATABASE_URL`** — forced by "rahasia tidak boleh di-hardcode" (`CLAUDE.md`) + preseden `OPENROUTER_API_KEY` (Keputusan 11 M1.3). User mengisi `.env` sendiri.
- **Tanpa folder `evals/1.5-...`** — forced karena `evals/` (per `evals/README.md`) khusus pengujian *perilaku LLM*, dan M1.5 sama sekali tidak memanggil LLM.
- **Tanpa mekanisme TTL/expiry** — Kriteria Keberhasilan sumber tidak memintanya; `arsitektur-ai-chatbot-rbac.md` Bagian 8 poin 2 eksplisit menandainya "masih terbuka" tanpa memaksa keputusan sekarang.
- **Tidak wired ke endpoint HTTP** — konsisten preseden M1.3/M1.4 (pipeline 9 layer belum dirangkai).

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada untuk keempatnya — masing-masing forced oleh prinsip/kontrak yang sudah ada.

---

## Keputusan 11 (Forced): `decisions.md` sebagai Task Pertama

**Sumber Paksaan:** Preferensi eksplisit user, ditetapkan di Milestone 1.4, berlaku untuk seluruh milestone berikutnya.

**Keputusan yang Diikuti:** Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode apa pun.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by instruksi eksplisit user.

---

## Keputusan 12 (Forced): Normalisasi Dialect `postgresql+psycopg://` + Wajib Pakai Connection Pooler Supabase

**Status:** Ditemukan di tengah implementasi pada Checkpoint 3, Task 4.

**Latar Belakang**
Dua temuan berurutan saat verifikasi koneksi nyata: (1) SQLAlchemy default me-resolve skema URL `postgresql://`/`postgres://` ke driver `psycopg2` (tidak diinstal — proyek ini sengaja pakai `psycopg` v3, Keputusan 2), menyebabkan `ModuleNotFoundError`. (2) Setelah dialect diperbaiki, koneksi ke hostname *direct connection* Supabase (`db.<project-ref>.supabase.co`) gagal dengan `failed to resolve host` — dikonfirmasi lewat `nslookup` bahwa hostname itu **hanya punya alamat IPv6**, sementara jaringan lokal tidak mendukung IPv6. Ini keterbatasan Supabase yang sudah dikenal luas (bukan bug proyek ini) — direct connection Supabase memang IPv6-only, solusi resminya pakai Connection Pooler (Supavisor) yang IPv4-compatible.

**Keputusan yang Diikuti**
- `get_engine()` (`src/config/database.py`) menormalisasi skema URL apa pun yang diawali `postgresql://`/`postgres://` jadi `postgresql+psycopg://` secara eksplisit, sebelum diteruskan ke `create_engine()`.
- `DATABASE_URL` di `.env` **wajib** pakai connection string dari mode **Transaction pooler** (port 6543) atau **Session pooler** (port 5432) Supabase Dashboard — BUKAN "Direct connection".

**Alasan**
Satu-satunya perbaikan yang mengatasi akar masalah (bukan workaround) — normalisasi dialect memastikan driver yang benar-benar terinstal (Keputusan 2) yang dipakai; pooler mengatasi keterbatasan IPv6-only direct connection tanpa perlu proyek ini mengatur IPv6 di level jaringan (di luar kendali proyek).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tambah `psycopg2-binary` sebagai dependency kedua** — ditolak, bertentangan dengan Keputusan 2 yang eksplisit memilih psycopg3, dan menambah dependency ganda untuk fungsi yang sama.
- **Setup IPv6 di level jaringan/OS** — di luar kendali dan cakupan proyek ini, jauh lebih rumit dari sekadar ganti connection string ke pooler yang memang disediakan resmi oleh Supabase untuk kasus ini.

**Dampak**
Perlu dicatat jelas di `.env.example`/dokumentasi supaya siapa pun (termasuk sesi kerja berikutnya) tidak mengulang jebakan yang sama — connection string Supabase yang benar untuk proyek ini SELALU dari mode pooler, tidak pernah direct connection.

---

## Keputusan 13 (Forced): `label_bentuk_jawaban`/`status` Disimpan `str` Polos, Bukan Kolom Enum Native Postgres

**Status:** Ditemukan di tengah implementasi pada Checkpoint 5 (smoke test `store_session_memory()`).

**Latar Belakang**
Skema tabel awal (Checkpoint 4) mentipekan `label_bentuk_jawaban: LabelBentukJawaban` dan `status: StatusEksekusi` langsung sebagai Python Enum, membuat SQLModel/SQLAlchemy otomatis membuat kolom ENUM native Postgres. Smoke test menemukan nilai yang tersimpan adalah **nama member Python** (`"NILAI_TUNGGAL"`, `"BERHASIL"`), BUKAN **value string** yang dikunci arsitektur SS7 (`"nilai_tunggal"`, `"berhasil"`) — perilaku default SQLAlchemy Enum native yang menyimpan `.name`, bukan `.value`, kecuali dikonfigurasi eksplisit `values_callable`.

**Keputusan yang Diikuti**
Kolom `label_bentuk_jawaban`/`status` diubah jadi `str` polos di `src/db/models.py` (bukan kolom Enum native Postgres). Validasi/tipe Enum tetap dipertahankan penuh di level Pydantic (`src/schemas/session_memory.py`) — `store_session_memory()` memakai `package.model_dump(mode="json")` yang menyerialisasi `StrEnum` ke `.value` dengan benar; `retrieve_session_memory()` mengandalkan Pydantic mengoersi string DB kembali jadi member Enum yang tepat saat membangun `SessionMemoryPackage`.

**Alasan**
Menghindari kerumitan mengelola tipe ENUM native Postgres (evolusi nilai butuh `ALTER TYPE ... ADD VALUE`, lebih rumit tanpa Alembic — Keputusan 8) untuk manfaat yang marginal, mengingat validasi bentuk data yang sesungguhnya penting sudah terjadi di batas Pydantic (`SessionMemoryPackage`) sebelum data pernah menyentuh DB sama sekali — konsisten pola `sumber` yang juga `str` polos di level DB.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Kolom Enum native Postgres + `values_callable` eksplisit** — teknis bisa menyelesaikan masalah value vs name, tapi tetap mewarisi kerumitan evolusi tipe ENUM native Postgres tanpa Alembic untuk manfaat yang tidak terbukti dibutuhkan proyek ini saat ini.

**Dampak**
Tabel `session_memory_packages` di Supabase perlu dibuat ulang (drop+recreate) karena perubahan tipe kolom — dilakukan sebelum ada data produksi nyata (hanya data smoke test), jadi tanpa risiko kehilangan data penting. **Catatan insiden terkait** (dicatat detail di `logs.md`): proses pembersihan tipe ENUM lama sempat menjalankan query yang tidak di-scope ke schema `public`, sempat berisiko menyentuh tipe internal Supabase sendiri (`auth.*`, `storage.*`, `realtime.*`) — dikonfirmasi TIDAK ada kerusakan nyata (query `DROP TYPE IF EXISTS` tanpa schema-qualifier + `search_path` default `public` membuat drop ke schema lain jadi no-op), tapi tetap dicatat sebagai near-miss yang harus dihindari (query administratif ke Supabase wajib schema-qualified eksplisit sejak sekarang).

---

## Keputusan 14 (Addendum): `retrieve_session_memory()` Diberi `try/except` — Mirror Persis `store_session_memory()`

**Status:** Ditemukan di Milestone 7.7 (2026-08-18, saat memetakan percabangan paralel Rewrite+Tarik Memory untuk disambungkan ke orkestrator lintas-layer), diperbaiki di sini atas keputusan langsung — bukan ditutup di M7.7 sendiri, karena perbaikan logic internal M1.5 adalah tanggung jawab milestone pemilik layer ini, mengikuti preseden persis penanganan celah `detect_turn_dependency()` (M1.3, Addendum, ditemukan+diperbaiki sesi sebelumnya).

**Latar Belakang**
Investigasi M7.7 menemukan `retrieve_session_memory()` TIDAK punya `try/except` sama sekali di sekitar query DB-nya (`Session(get_engine())`/`session.exec()`) — beda dari fungsi kembarnya di file yang sama, `store_session_memory()`, yang sudah menangkap exception, menandai `error.type=gagal_teknis` di span, baru raise ulang (Keputusan 13 tidak menyentuh soal ini — celah murni terlewat saat `retrieve_session_memory()` ditulis, bukan pertimbangan sadar). Celah ini LEBIH SEMPIT dari celah `detect_turn_dependency()` (M1.3): exception tetap menjalar keluar di kedua kondisi (dengan atau tanpa fix) — perilaku eksternal terhadap pemanggil sama — cuma sebelum fix, span `memory.retrieve` tidak pernah ditandai `error.type` dulu sebelum exception menjalar, sehingga kegagalan teknis di titik ini tidak akan terlihat lewat query span berbasis `error.type` di observability (Jaeger/dashboard), meski trace-nya sendiri tetap tercatat.

**Keputusan yang Diikuti**
`retrieve_session_memory()` dibungkus `try/except Exception: span.set_attribute("error.type", "gagal_teknis"); raise` — identik pola `store_session_memory()`, tanpa mengubah signature/tipe return.

**Alasan**
Konsistensi murni antar dua fungsi kembar di file yang sama — tidak ada pertanyaan desain baru (beda dari M1.3's `detect_turn_dependency()` yang butuh keputusan soal fallback value karena `TurnDependencyResult` tidak py field `status`; di sini return type `list[SessionMemoryPackage]` tidak berubah sama sekali, murni menambah observability + mempertahankan raise-on-failure yang sudah terjadi secara implisit).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Fallback ke `[]` (list kosong) saat DB gagal, alih-alih raise** — ditolak, akan mengaburkan "genuinely tidak ada data" (`[]` yang valid, forced KK M1.5 asli) dengan "gagal mengecek karena DB down" (situasi teknis berbeda total) — silent data loss risk: pemanggil bisa salah menyimpulkan "tidak ada histori relevan" padahal query-nya sendiri gagal dijalankan.
- **Tidak diperbaiki, dicatat sebagai keterbatasan diterima** (mirror penuh preseden M1.3) — ditolak, tidak ada alasan menunda ketika perbaikannya sudah jelas dan sempit (tinggal mirror pola yang sudah ada persis di baris atas fungsi ini) — beda situasi dari M1.3 yang ditemukan di tengah milestone lain yang genuinely tidak menyentuh area itu.

**Dampak**
Test baru `tests/layers/context_resolution/test_session_memory_kegagalan.py::test_kegagalan_db_saat_retrieve_menghasilkan_error_type_lalu_raise_ulang` (mirror fixture `_TracerRekam`/`_SpanRekam` yang sudah ada di file, `_SessionExecGagal` baru untuk mensimulasikan `exec()` gagal). Dicatat juga secara ringkas di `milestones/7.7-.../decisions.md` Keputusan 6 sebagai catatan silang (kenapa `session_memory.py` berubah di bawah commit ber-tag M7.7 padahal isinya perbaikan M1.5). **TIDAK ada entri baru di `docs/keterbatasan-diterima.md`** — celah ini ditutup sebelum M7.7 sendiri selesai, tidak pernah benar-benar berstatus "diterima sebagai keterbatasan".

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Database: Supabase (project sama M5/M6) | A | Plan |
| 2 | Library akses: SQLModel | A | Plan |
| 3 | Migrasi `roles.yaml` ke database | A | Plan |
| 4 | Store + Retrieve dua-duanya dibangun | B | Plan |
| 5 | Penamaan tabel `session_memory_packages`/`roles` | B | Plan |
| 6 | Hanya span `memory.retrieve` wajib | B | Plan |
| 7 | `sumber: str` bebas, bukan Enum | B | Plan |
| 8 | Struktur kode + pemisahan row DB vs schema publik | B | Checkpoint 4 |
| 9 | `roles.yaml` dihapus setelah verifikasi ganda | B | Checkpoint 10 |
| 10 | Kredensial `.env`, tanpa `evals/`, tanpa TTL, tidak wired HTTP | B | Plan |
| 11 | `decisions.md` sebagai Task pertama | B | Plan |
| 12 | Normalisasi dialect psycopg3 + wajib pakai Connection Pooler Supabase | B | Checkpoint 3 |
| 13 | `label_bentuk_jawaban`/`status` str polos, bukan Enum native Postgres | B | Checkpoint 5 |
