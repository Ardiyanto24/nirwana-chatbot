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

---

## Checkpoint 5 — Pencarian BM25 Primer + Trigger Fallback (Provisional)

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 8 — `uv add rank-bm25`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
`uv add rank-bm25` — menambah `rank-bm25==0.2.2` (+ `numpy==2.5.2` transitif) ke `pyproject.toml`/`uv.lock`.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Install sukses, 2 paket ditambahkan.

**Commit:** `95b15cd` — `chore: tambah dependency rank-bm25`

---

### Task 9 — `src/layers/retriever/pencarian_bm25.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyempurnaan: kandidat hanya dikembalikan untuk skor > 0 (bukan seluruh domain_diizinkan tanpa syarat skor) — kandidat skor 0 bukan "mungkin relevan" secara leksikal, murni noise. Ini membuat `perlu_fallback = len(kandidat) == 0` (setara `skor_tertinggi <= BM25_SKOR_MINIMUM` yang direncanakan, tapi lebih sederhana secara implementasi).

**Apa yang dilakukan**
Index `BM25Okapi` dibangun sekali dari `KORPUS_FUNGSI_VIEW` (`@lru_cache`, tokenisasi regex `[a-z0-9]+` atas teks lowercase). `cari_bm25()` menghitung skor atas seluruh 67 view, MATERIALISASI `KandidatView` hanya untuk domain di `domain_diizinkan` DAN skor > 0.

**Temuan**
Tidak ada temuan tak terduga.

**Error/Kegagalan**
Proses (bukan kode): commit pertama keliru menggabungkan `chore` (dependency) dan `feat` (implementasi `pencarian_bm25.py`) dalam satu commit `chore: tambah dependency rank-bm25` — melanggar aturan pemisahan kategori Conventional Commits di `CLAUDE.md`.

**Diagnosis dan Perbaikan**
`git add` tidak sengaja menyertakan `src/layers/retriever/pencarian_bm25.py` bersama `pyproject.toml`/`uv.lock`. Diperbaiki dengan `git reset --soft HEAD~1` (uncommit, perubahan tetap ada) lalu commit ulang terpisah: `chore` (dependency saja) → `feat` (implementasi) → `test` (Task 10, terpisah).

**Hasil Verifikasi**
Lihat Task 10.

**Commit:** `9187f52` — `feat(milestone-3.1): pencarian bm25 primer`

---

### Task 10 — Test KK1/KK2/Trigger Boundary

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
6 test: KK1 literal (`"okupansi Bali bulan ini"` + `[RESERVATION]`), KK2 zero-leakage (query sama + `[FNB]`, RESERVATION sengaja tidak diizinkan), trigger boundary (`"xyzzy qwerty asdf"` — tanpa overlap leksikal sama sekali), urutan skor menurun, `sumber` selalu BM25, `domain_diizinkan=[]` selalu fallback.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_pencarian_bm25.py -v` — 6/6 lolos, deterministik murni Python tanpa network call.

**Commit:** `371ba20` — `test(milestone-3.1): skenario kk1/kk2/trigger bm25`

---

---

## Checkpoint 6 — Fallback Embedding Generik

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task Tambahan (di luar penomoran plan) — Refactor `view_ke_domain()`

Sebelum menulis `pencarian_embedding.py`, ditemukan kebutuhan reverse mapping `view_name -> Domain` yang IDENTIK dengan helper privat `_domain_per_view()` yang sudah ada di `pencarian_bm25.py` (Checkpoint 5). Alih-alih duplikasi atau import fungsi privat lintas modul, fungsi dipindah jadi publik `view_ke_domain()` di `src/config/katalog_view.py` (`@lru_cache`) - konsisten alasan relokasi `DAFTAR_VIEW_PER_DOMAIN` itu sendiri (data referensi dipakai >1 konsumen). `pencarian_bm25.py` diupdate reuse fungsi ini, test baru ditambahkan `tests/config/test_katalog_view.py`. Regresi penuh 43 test (`tests/config/`, `tests/layers/retriever/`, `tests/layers/verification_gate/`) tetap hijau. **Commit:** `22bfbec` — `refactor(milestone-3.1): view_ke_domain() reusable di src/config`.

### Task 11 — Konstanta Model Sementara + `pencarian_embedding.py`

**Kesesuaian dengan plan:** Sesuai plan. Verifikasi exact model ID string OpenRouter (`qwen/qwen3-embedding-4b`, `qwen/qwen3-embedding-8b`, `openai/text-embedding-3-small`) dikonfirmasi via `WebFetch` ke halaman koleksi model embedding OpenRouter sebelum ditulis ke `llm.py` - bukan tebakan format penamaan.

**Apa yang dilakukan**
3 konstanta sementara `OPENROUTER_MODEL_RETRIEVER_EMBEDDING_QWEN3_4B/_QWEN3_8B/_OPENAI_SMALL_3` di `src/config/llm.py` (docstring modul diperluas menjelaskan alasan sementara + rujukan `decisions.md` Keputusan 2). `src/layers/retriever/pencarian_embedding.py`: `embed_korpus(model)` (`@lru_cache` per-model, satu batch call ke `client.embeddings.create()`), `cari_embedding(teks_kebutuhan, domain_diizinkan, model)` (cosine similarity via `numpy`, filter struktural domain identik `cari_bm25()`, `try/except` luas menangkap kegagalan API jadi `gagal=True`).

**Temuan**
Tidak ada temuan tak terduga di luar yang sudah dicatat di Task Tambahan di atas.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Lihat Task 12.

**Commit:** `2361461` — `feat(milestone-3.1): fallback embedding generik`

---

### Task 12 — Test Monkeypatch

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
5 test, seluruhnya monkeypatch `get_openrouter_client()` (nol network call/biaya nyata): ranking cosine similarity benar (vektor one-hot terkontrol), domain filtering struktural identik pola BM25, parameter `model` benar-benar diteruskan ke KEDUA panggilan `embeddings.create()` (batch korpus + query), `sumber` selalu `EMBEDDING_FALLBACK`, kegagalan API (`RuntimeError` disimulasikan) menghasilkan `gagal=True` bukan exception bocor. Model name UNIK per test function untuk menghindari `lru_cache` `embed_korpus()` saling mengotori antar-test.

**Temuan**
Tidak ada.

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
`pytest tests/layers/retriever/test_pencarian_embedding.py -v` — 5/5 lolos.

**Commit:** `9d59197` — `test(milestone-3.1): pencarian embedding monkeypatch`

---

---

## Checkpoint 7 — Eval Perbandingan 3 Model Embedding + Validasi KK1/KK2

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 13 — `rancangan.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Sebelum menulis skenario Bagian B, `cari_bm25()` diuji lokal (murni Python, tanpa biaya) terhadap 5 draf query paraphrase untuk memvalidasi bahwa skenario benar-benar menstress kegagalan BM25 (bukan trivial seperti KK1 sumber). Menulis `rancangan.md`: Bagian A (A1/A2, KK1/KK2 standar) + Bagian B (B1-B5, 5 kategori: sinonim non-literal, bahasa sehari-hari vs teknis, typo, framing abstrak, partial-stem).

**Temuan**
Analisis lokal menemukan **celah desain trigger nyata**: skenario B1 (kanal booking) menunjukkan BM25 bisa gagal total menemukan target (`v_reservation_channel_daily` sama sekali tidak muncul di 5 kandidat) TANPA memicu `perlu_fallback=True` (trigger provisional Checkpoint 5 hanya aktif kalau SELURUH kandidat berskor nol, bukan kalau kandidat yang ditemukan salah/tidak lengkap). Dicatat eksplisit di `rancangan.md` sebagai temuan yang mengubah desain eksekusi eval (Bagian B memanggil `cari_embedding()` langsung, bukan lewat orkestrator produksi yang belum dibangun).

**Error/Kegagalan**
Tidak ada.

**Hasil Verifikasi**
Baseline BM25 tiap skenario B1-B5 dikonfirmasi lokal sebelum ditulis ke `rancangan.md` (posisi target dicatat presisi, bukan estimasi).

**Commit:** *(digabung Task 14-15, satu commit `docs`)*

---

### Task 14 — `run_eval.py` + Eksekusi Nyata

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis `run_eval.py` (Bagian A via `cari_bm25()` langsung, Bagian B via `cari_embedding()` 3x per skenario satu per model). Dry-run bertahap: A1/A2 (tanpa biaya) → B3 tunggal (3 model, verifikasi pipeline nyata) → batch penuh.

**Temuan**
Dry-run B3 menemukan `openai/text-embedding-3-small` gagal `404 NotFoundError` — pesan error OpenRouter: setting akun "Allowed Providers" hanya mengizinkan `siliconflow`. Diagnosis langsung (panggilan manual `client.embeddings.create()`) mengonfirmasi ini murni setting akun, bukan bug kode (Qwen3-4B/8B, sama-sama dilayani `siliconflow`, berhasil normal).

**Error/Kegagalan**
`openai.NotFoundError: Error code: 404 - ...your account's allowed-providers setting permits only: siliconflow...` — dicatat verbatim di `audit.md`.

**Diagnosis dan Perbaikan**
Bukan bug yang bisa diperbaiki di kode. Diajukan ke user lewat `AskUserQuestion` (lanjut 2 model saja vs user ubah setting) — user memilih ubah setting. Panduan diberikan (halaman `openrouter.ai/settings/privacy`, toggle "Enable paid endpoints that may train on inputs"/"ZDR Endpoints only"). User menambahkan `OpenAI` ke Allowed Providers lewat UI (screenshot dikonfirmasi: "SiliconFlow" + "OpenAI", status "Saved"). Diverifikasi ulang via panggilan manual (sukses, 1536 dimensi) SEBELUM eval penuh dijalankan ulang.

**Hasil Verifikasi**
Eval penuh (`run_eval.py` tanpa filter) dieksekusi nyata ke OpenRouter: Bagian A (2 skenario) + Bagian B (5 skenario × 3 model = 15 panggilan `cari_embedding()`, masing-masing minimal 1 panggilan API query + panggilan batch korpus 67 teks pada penggunaan pertama tiap model). Seluruh 17 payload tersimpan `payloads/` (JSON lengkap, termasuk kandidat per view + skor).

**Commit:** *(digabung Task 15, lihat di bawah)*

---

### Task 15 — `audit.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Tabel perbandingan recall/posisi/latensi 3 model × 5 skenario B. Analisis temuan utama, rekomendasi (bukan keputusan final).

**Temuan**
- **Qwen3-Embedding-4B: 0/5 recall (gagal total di SEMUA skenario B)** — termasuk B4 di mana BM25 baseline sendiri sudah menemukan target (model 4B lebih buruk dari BM25 murni di kasus itu).
- **Qwen3-Embedding-8B dan `text-embedding-3-small`: sama-sama 5/5 recall.** `text-embedding-3-small` sedikit lebih unggul (rank rata-rata 2.4 vs 2.6, JAUH lebih konsisten posisi, latensi query-only ~2.5x lebih cepat: 0.79s vs 1.99s).
- **Konfirmasi ulang temuan trigger dari Task 13**: 4 dari 5 skenario B (semua kecuali B3 yang typo/0-kandidat) TIDAK memicu `perlu_fallback` produksi saat ini — recall gap nyata untuk desain Checkpoint 9.

**Error/Kegagalan**
Tidak ada (di luar insiden Allowed Providers Task 14, sudah diselesaikan sebelum bagian ini).

**Hasil Verifikasi**
`audit.md` ditinjau manual, seluruh 15 baris tabel B dan 2 baris tabel A merujuk langsung ke payload tersimpan.

**Commit:** `1b836b6` — `docs(evals-3.1): rancangan+audit perbandingan 3 model embedding` (Task 13-15 digabung satu commit `docs` sesuai plan — eval bukan kode produksi).

---

## Task/Checkpoint di Luar Plan (jika ada)

Refactor `view_ke_domain()` (Checkpoint 6) - bukan checkpoint terpisah, penyesuaian kecil saat mengerjakan Task 11 begitu duplikasi terdeteksi.

Insiden Allowed Providers OpenRouter (Checkpoint 7, Task 14) - bukan task terpisah dari plan, tapi blocker operasional tak terduga yang butuh keterlibatan user (ubah setting akun) di tengah eksekusi eval.

---

## Checkpoint 8 — Kunci Keputusan Model Embedding Final

**Mulai:** 2026-08-17 · **Selesai:** 2026-08-17

### Task 16 — Addendum `decisions.md`

**Kesesuaian dengan plan:** Sesuai plan.

**Apa yang dilakukan**
Menulis addendum Keputusan 2 di `decisions.md`: `openai/text-embedding-3-small` dikunci berdasar hasil `audit.md` (recall 5/5, rank rata-rata terbaik, latensi terendah).

**Hasil Verifikasi**
Review manual - argumen recall+rank+latensi tercakup eksplisit, status PROVISIONAL ditegaskan ulang.

**Commit:** `b399913` — `docs(milestone-3.1): kunci model embedding final`

---

### Task 17 — Sederhanakan `src/config/llm.py`

**Kesesuaian dengan plan:** Sesuai plan, dengan satu penyesuaian tak terduga: `evals/3.1-pengumpulan-kandidat-view/run_eval.py` ternyata masih meng-import 3 konstanta sementara yang dihapus (dipakai untuk membandingkan 3 kandidat, bukan cuma model final) - diperbaiki dengan mengganti import jadi ID model literal di `run_eval.py` sendiri, supaya script perbandingan tetap re-runnable sebagai arsip historis tanpa bergantung konfigurasi produksi yang kini hanya 1 model.

**Apa yang dilakukan**
Hapus 3 konstanta `OPENROUTER_MODEL_RETRIEVER_EMBEDDING_QWEN3_4B/_QWEN3_8B/_OPENAI_SMALL_3`, tambah `OPENROUTER_MODEL_RETRIEVER_EMBEDDING = "openai/text-embedding-3-small"` (docstring modul diupdate). `pencarian_embedding.py` TIDAK diubah (fungsi generik `cari_embedding(..., model)` dipertahankan - titik pemanggilan produksi yang akan di-hardwire adalah orkestrator `retriever.py`, Checkpoint 10, belum dibangun).

**Temuan**
`run_eval.py` (Checkpoint 7, sudah commit) ternyata coupled ke 3 konstanta sementara - baru ketahuan saat menghapusnya (`ImportError` kalau dibiarkan). Diperbaiki di commit yang sama.

**Error/Kegagalan**
Tidak ada (ditangkap sebelum commit, bukan test yang gagal).

**Hasil Verifikasi**
`pytest tests/layers/retriever/ tests/config/ tests/layers/verification_gate/ -v` — 48/48 lolos (signature `cari_embedding()` tak berubah). `grep` project-wide untuk 2 konstanta lama — nol hasil.

**Commit:** `c893f41` — `refactor(milestone-3.1): sederhanakan config ke satu model final`
