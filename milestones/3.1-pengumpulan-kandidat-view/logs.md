# Logs — Milestone 3.1: Pengumpulan Kandidat View

Dokumen ini mencatat peristiwa nyata sepanjang milestone ini dikerjakan — dikelompokkan per checkpoint, lalu per task di dalamnya, mengikuti struktur yang sama dengan Checkpoint & Task Breakdown di plan.

---

## Checkpoint 1 — Keputusan Desain

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 1 — Tulis `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `milestones/3.1-pengumpulan-kandidat-view/decisions.md`: 13 keputusan (2 Jenis A hasil `AskUserQuestion` dalam sesi perencanaan — mekanisme hybrid BM25+fallback embedding, dan proses perbandingan-empiris 3 model embedding dengan penguncian provisional; 11 Jenis B forced/preseden — termasuk relokasi `DAFTAR_VIEW_PER_DOMAIN` ke `src/config/`), format Jenis A/B + "Opsi yang Dipertimbangkan tapi Ditolak" mirror `milestones/2.4-verification-gate/decisions.md`, ditutup tabel Daftar Isi Keputusan.

**Temuan**
Keputusan 2 (model embedding) sempat direvisi user setelah draft plan pertama diajukan lewat `ExitPlanMode` — user menolak (rejection) karena plan awal secara implisit menutup keputusan model secara permanen pasca-eval; user mengoreksi: model performa tertinggi dipakai sekarang tapi WAJIB dicatat sebagai keputusan tertunda (`docs/keputusan-tertunda.md`), bukan ditutup final. Plan direvisi (Checkpoint 9 baru ditambahkan) sebelum `ExitPlanMode` diajukan ulang dan disetujui.

Draft plan kedua juga sempat ditolak user karena tidak mengikuti `docs/00-project-governance/template-plan-milestone-lengkap.md` secara ketat (section "Keputusan yang Ditanyakan ke User" terlewat, penomoran Task tidak berurutan lintas checkpoint) — plan direvisi ulang mengikuti template persis (Context → Keputusan Desain Turunan → Keputusan yang Ditanyakan ke User → Checkpoint & Task Breakdown dengan Task bernomor 1-26 berurutan → Kriteria Keberhasilan → Commit → Risiko & Mitigasi) sebelum disetujui.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Review manual — seluruh keputusan di plan yang disetujui (Keputusan Desain Turunan + Keputusan yang Ditanyakan ke User) punya entri `decisions.md` yang sesuai, tidak ada yang diam-diam jadi asumsi implisit.

**Commit:** `edf6ee1` — `docs(milestone-3.1): decisions.md keputusan awal`

---

---

## Checkpoint 2 — Relokasi Katalog View ke `src/config/`

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 2 — Pindahkan `DAFTAR_VIEW_PER_DOMAIN`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `src/config/katalog_view.py` (docstring diperluas menjelaskan alasan relokasi + rujukan `decisions.md` Keputusan 3, data `DAFTAR_VIEW_PER_DOMAIN` byte-identik dengan versi lama), update import di `verifikasi_gate.py` dari `src.layers.verification_gate.katalog_view` ke `src.config.katalog_view`, hapus `src/layers/verification_gate/katalog_view.py`.

**Temuan**
Tidak ada temuan di luar dugaan.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`grep -rn "from src\.layers\.verification_gate\.katalog_view"` di seluruh repo — nol hasil, tidak ada import lama tersisa.

**Commit:** *(digabung Task 3, lihat di bawah)*

---

### Task 3 — Pindahkan Test ke `tests/config/`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `tests/config/__init__.py` dan `tests/config/test_katalog_view.py` (isi sama persis dengan versi lama, hanya import path diubah ke `src.config.katalog_view`), hapus `tests/layers/verification_gate/test_katalog_view.py`.

**Temuan**
`git add` mendeteksi perpindahan file sebagai rename murni (`R src/layers/verification_gate/katalog_view.py -> src/config/katalog_view.py`, `R tests/layers/verification_gate/test_katalog_view.py -> tests/config/test_katalog_view.py`) — bukti tambahan bahwa perubahan ini murni refactor tanpa modifikasi isi substansial.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/verification_gate/ tests/config/ -v` — 25 test lolos (20 test verification_gate sisa + 5 test config pindahan), tanpa perubahan assertion. `CLAUDE.md`/`AGENT.md` diperbarui (baris `src/config/`, `src/layers/verification_gate/`, `tests/`) mencatat relokasi dan folder baru `tests/config/`, disinkronkan identik (`diff` kosong).

**Commit:** `fc9c342` — `refactor(config): relokasi katalog view ke src/config`

---

---

## Checkpoint 3 — Skema Retriever + Skeleton Subpackage

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 4 — `src/schemas/retriever.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyempurnaan desain: `model_validator` diimplementasikan sebagai konsistensi `status`↔`fallback_terpicu` (bukan `status`↔`kandidat` seperti draf awal plan) - karena BM25 murni deterministik tidak pernah punya mode "gagal_teknis" seperti pemanggilan LLM, sehingga hanya `BERHASIL`/`SEBAGIAN` yang relevan, dan `SEBAGIAN` hanya bermakna kalau fallback benar-benar terpicu lalu gagal teknis.

**Apa yang dilakukan**
Menulis `src/schemas/retriever.py`: `SumberPencarian` (Enum `bm25`/`embedding_fallback`), `KandidatView` (`view_name`/`domain`/`skor`/`sumber`), `HasilPencarianKandidat` (`atomic_intent`/`domain_diizinkan`/`kandidat`/`fallback_terpicu`/`status`) dengan `model_validator(mode="after")` menolak `status` selain BERHASIL/SEBAGIAN, dan menolak `fallback_terpicu=False` dipasangkan `status=SEBAGIAN`.

**Temuan**
Draf `model_validator` awal (status↔kandidat kosong, mirror `AtomicIntentDomains` M2.1) ternyata tidak punya skenario nyata yang valid untuk M3.1 - BM25 selalu berjalan sukses secara struktural (tidak ada "gagal total" seperti panggilan LLM). Diganti validator yang benar-benar mencerminkan invarian nyata pipeline M3.1.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`python -c "from src.schemas.retriever import HasilPencarianKandidat"` sukses. `pytest tests/layers/retriever/test_retriever_schema.py -v` — 6/6 lolos (status=GAGAL_TEKNIS ditolak, status=DITOLAK_OTORISASI ditolak, fallback_terpicu=False+status=SEBAGIAN ditolak, 3 kombinasi valid diterima).

**Commit:** *(digabung Task 5, lihat di bawah)*

---

### Task 5 — Skeleton Subpackage

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membuat `src/layers/retriever/__init__.py` dan `tests/layers/retriever/__init__.py` (keduanya kosong) sebelum file kode lain di subpackage ini ditulis - mengikuti lesson-learned M2.4 (`ModuleNotFoundError` kalau lupa).

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Test collection `pytest tests/layers/retriever/` berjalan tanpa `ModuleNotFoundError`. `CLAUDE.md`/`AGENT.md` diperbarui mencatat folder baru `src/layers/retriever/` dan `tests/layers/retriever/`, disinkronkan identik.

**Commit:** `5e22518` — `feat(milestone-3.1): skema retriever + skeleton subpackage`

---

---

## Checkpoint 4 — Korpus 67 Deskripsi Fungsi

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 6 — `src/layers/retriever/korpus_view.py`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Membaca penuh `docs/03-domain-source/katalog-data-chatbot.md` (1020 baris), mentranskripsi manual teks `**Fungsi**:` untuk seluruh 67 view (transkripsi PERSIS termasuk markup Markdown `**bold**` dan tanda kutip lurus, bukan dinormalisasi) ke `KORPUS_FUNGSI_VIEW: dict[str, str]`, key `view_name` bersumber dari `DAFTAR_VIEW_PER_DOMAIN` (Checkpoint 2).

**Temuan**
Verifikasi silang manual (`Grep` pola `\*\*Fungsi\*\*:` terhadap dokumen sumber, dibandingkan baris demi baris terhadap draf transkripsi) menemukan 2 markup `**bold**` yang terlewat pada transkripsi awal: `guests_contact_view` ("**tidak** ada atribut analitis") dan `guests_profile_view` ("**Tidak** ada kolom kontak") — keduanya diperbaiki SEBELUM commit, dikonfirmasi lolos test independen Task 7.

**Error/Kegagalan**
Tidak ada (2 temuan transkripsi di atas tertangkap sebelum commit, bukan kegagalan test yang lolos ke commit).

**Hasil Verifikasi**
Lihat Task 7 (test independen membuktikan korpus akhir 100% sama persis dengan dokumen sumber).

**Commit:** `51dfe2d` — `feat(milestone-3.1): korpus 67 deskripsi fungsi`

---

### Task 7 — Test Parse-Ulang Independen

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `tests/layers/retriever/test_korpus_view.py`: regex `^#### \`([^\`]+)\`.*\n\*Sumber:.*\n\*\*Fungsi\*\*:\s*(.+)$` (MULTILINE) memparse ulang dokumen sumber langsung dari file, dibandingkan `==` penuh terhadap `KORPUS_FUNGSI_VIEW`. Ditambah test prasyarat (regex sendiri menemukan tepat 67 entri — mencegah perbandingan `==` "lolos" keliru kalau kedua sisi sama-sama kosong/parsial), test bijektif terhadap `DAFTAR_VIEW_PER_DOMAIN`, dan spot-check "okupansi" (prasyarat KK1).

**Temuan**
Tidak ada temuan tambahan di luar Task 6 (test ini yang menangkap 2 markup terlewat sebelum commit final).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_korpus_view.py -v` — 5/5 lolos: `test_korpus_sama_persis_dengan_dokumen_sumber`, `test_regex_menemukan_67_entri_di_dokumen`, `test_korpus_67_entri`, `test_bijektif_dengan_daftar_view_per_domain`, `test_okupansi_ada_di_teks_v_reservation_room_type_daily`.

**Commit:** `aaae8ca` — `test(milestone-3.1): verifikasi korpus independen`

---

## Task/Checkpoint di Luar Plan (jika ada)

Tidak ada.
