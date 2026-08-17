# Decisions — Milestone 3.1: Pengumpulan Kandidat View

Dokumen ini mencatat setiap keputusan desain yang diambil untuk Milestone 3.1 — pekerjaan pertama PIC 3 (Retriever, Query Engine), membangun mekanisme pencarian kandidat `view_name` dari kebutuhan atomik + domain yang diizinkan.

---

## Keputusan 1: Mekanisme Pencarian Kandidat — Hybrid (BM25 + Fallback Embedding)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
`rancangan-retrieval-query.md` baris 41 eksplisit menyatakan "bentuk teknis pencarian (embedding, keyword matching, atau pendekatan lain) adalah keputusan implementasi bebas" — genuinely terbuka, tidak ada preseden milestone lain yang bisa ditarik untuk mekanisme pencarian non-LLM semacam ini.

**Proses**
Empat alternatif diajukan lewat `AskUserQuestion`: (1) BM25 murni — deterministik, tanpa network call, direkomendasikan atas dasar korpus 67 deskripsi pendek dan skenario KK1 sumber ("okupansi Bali bulan ini") yang frasanya literal ada di teks Fungsi `v_reservation_room_type_daily`; (2) TF-IDF+cosine similarity — pendekatan serupa BM25, dependency lebih berat (`scikit-learn`), tanpa keunggulan empiris nyata di skala 67 dokumen; (3) embedding semantik murni via OpenRouter — generalisasi lebih baik ke parafrase, tapi menambah network call per pencarian dan ambiguitas terhadap kontrak "non-LLM"; (4) hybrid (BM25 utama + fallback embedding). User awalnya diberi penjelasan detail per opsi sebelum memutuskan.

**Keputusan yang Dipilih**
Hybrid — BM25 (`rank-bm25`, murni Python, deterministik) sebagai jalur utama; fallback ke embedding semantik HANYA ketika BM25 gagal menemukan kandidat memadai (skor tertinggi di bawah ambang provisional).

**Alasan**
User eksplisit memilih hybrid meski rekomendasi awal adalah BM25 murni — trade-off yang diterima: kompleksitas tambahan (dua mekanisme, bukan satu) demi recall yang lebih tinggi untuk kasus paraphrase/sinonim yang tidak tertangkap leksikal murni, konsisten prinsip KK1 sumber ("tidak terlewat karena pencarian terlalu sempit").

**Opsi yang Dipertimbangkan tapi Ditolak**
- **BM25 murni tanpa fallback** — direkomendasikan penulis (zero network dependency, cocok literal dengan syarat dokumen "non-LLM"), tidak dipilih user karena risiko false-negative pada kasus sinonim/istilah tak identik dengan teks Fungsi katalog dinilai perlu mitigasi tambahan.
- **TF-IDF+cosine similarity** — ditolak, dependency lebih berat (`scikit-learn`) tanpa keunggulan performa nyata dibanding BM25 untuk dokumen pendek semacam ini.
- **Embedding semantik murni (tanpa BM25)** — ditolak, kehilangan jalur deterministik-murah yang terbukti cukup untuk mayoritas kasus (termasuk KK1 sumber), dan menjadikan SETIAP pencarian bergantung network call.

---

## Keputusan 2: Model Embedding untuk Jalur Fallback — Dibandingkan Empiris, Dikunci Provisional

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`, dua putaran + klarifikasi lanjutan setelah plan awal ditolak user).

**Latar Belakang**
Tidak ada preseden benchmark Bahasa Indonesia untuk model *embedding* spesifik di proyek ini — beda dari model chat/completion yang sudah py preseden SEA-HELM sejak M1.4 (`Qwen3-32B`). OpenRouter mendukung endpoint `/embeddings` native (diverifikasi lewat riset web sebelum plan ditulis — bukan risiko lagi), termasuk model Qwen3-Embedding-4B/8B dan `text-embedding-3-small` OpenAI.

**Proses**
Tiga kandidat diajukan lewat `AskUserQuestion` dengan rekomendasi Qwen3-Embedding-4B (konsisten preseden Qwen, murah/cepat, cocok untuk jalur fallback yang jarang terpakai). User menjawab tidak ingin memilih satu di depan tanpa bukti — eksplisit meminta ketiga model dicoba dan dibandingkan secara empiris (`evals/3.1-.../`, Checkpoint 7) sebelum dikunci. Setelah draft plan awal (yang menyiratkan model final dikunci "tertutup" pasca-eval) diajukan, user mengoreksi: model dengan performa tertinggi dipakai SEKARANG, tapi keputusan ini harus dicatat sebagai **keputusan tertunda** (`docs/keputusan-tertunda.md`) — bukan ditutup permanen seperti pola M1.3-M2.3.

**Keputusan yang Dipilih**
Checkpoint 7 menjalankan eval nyata (Bagian A: KK1/KK2 standar; Bagian B: 5-6 skenario stress-test kegagalan BM25) untuk ketiga model. Checkpoint 8 mengunci model dengan **recall tertinggi** di `audit.md` sebagai `OPENROUTER_MODEL_RETRIEVER_EMBEDDING` aktif. Checkpoint 9 menambah entri `docs/keputusan-tertunda.md` yang menyatakan pilihan ini provisional, dengan tiga pemicu peninjauan ulang eksplisit (pola kegagalan produksi nyata di M3.2+, model baru relevan Bahasa Indonesia dirilis OpenRouter, evaluasi biaya/latensi berubah pada volume nyata).

**Alasan**
Konsisten budaya eval-driven proyek ini (M1.6/M1.7/M2.1 semua menemukan hal nyata lewat bukti, bukan asumsi upfront) — TAPI berbeda dari model chat/completion lain karena cakupan eval Checkpoint 7 sengaja terbatas (5-6 skenario, bukan ratusan), sehingga menutup keputusan secara permanen berisiko overclaim kepastian yang sebenarnya tidak dimiliki.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Pilih satu model di depan berdasar benchmark publik (mis. leaderboard MTEB) tanpa eval internal** — ditolak eksplisit oleh user; catatan: ini SENGAJA beda dari preseden M1.4 (Qwen3-32B dipilih dari benchmark publik SEA-HELM tanpa eval internal terpisah) — bukan inkonsistensi, melainkan pilihan user yang genuinely berbeda untuk milestone ini.
- **Kunci model final permanen pasca-eval Checkpoint 7 (seperti pola M1.3-M2.3)** — bentuk awal plan sebelum dikoreksi user; ditolak karena cakupan eval Checkpoint 7 dinilai user belum cukup luas untuk klaim kepastian permanen.
- **Uji 3 model HANYA dengan skenario KK1/KK2 standar (tanpa Bagian B stress-test)** — ditolak saat desain proses eval: KK1 sumber terbukti trivial untuk BM25 sendiri (frasa literal ada di korpus), sama sekali tidak memberi sinyal pembeda antar model embedding.

**Addendum (setelah Checkpoint 7 — hasil eval nyata, lihat `evals/3.1-pengumpulan-kandidat-view/audit.md`):**

Hasil: Qwen3-Embedding-4B **0/5 recall** (gagal total di seluruh skenario Bagian B, termasuk satu kasus di mana BM25 murni sudah lebih baik). Qwen3-Embedding-8B dan `text-embedding-3-small` sama-sama **5/5 recall**; `text-embedding-3-small` unggul di rank rata-rata (2.4 vs 2.6), konsistensi posisi (nyaris selalu rank 2, dibanding Qwen3-8B yang berayun 1-5), dan latensi query-only (~0.79s vs ~1.99s rata-rata, ~2.5x lebih cepat).

**Model dikunci: `openai/text-embedding-3-small`** (`OPENROUTER_MODEL_RETRIEVER_EMBEDDING`, Checkpoint 8) — recall sempurna + rank paling konsisten + latensi terendah, tiga dimensi penilaian sekaligus, bukan trade-off yang harus dipilih. Berstatus PROVISIONAL (dicatat `docs/keputusan-tertunda.md`, bukan ditutup permanen — lihat Keputusan 2 di atas), sesuai instruksi eksplisit user.

**Insiden operasional dicatat sebagai bagian keputusan ini**: panggilan pertama ke `openai/text-embedding-3-small` sempat gagal `404 NotFoundError` karena setting akun OpenRouter "Allowed Providers" awalnya hanya mengizinkan `siliconflow` — bukan bug kode. User mengubah setting (menambahkan `OpenAI` ke Allowed Providers, `openrouter.ai/settings/privacy`) sebelum eval penuh dijalankan ulang. Dicatat di sini karena ini prasyarat operasional yang harus tetap terpenuhi di lingkungan mana pun kode ini dijalankan produksi (bukan cuma sesi pengembangan ini) — kalau di lingkungan lain Allowed Providers dikonfigurasi ulang membatasi ke `siliconflow` saja, `OPENROUTER_MODEL_RETRIEVER_EMBEDDING` akan gagal teknis (`gagal=True`, jatuh ke `status=SEBAGIAN`, bukan crash — sudah ditangani `cari_embedding()`), bukan silently memakai model lain.

---

## Keputusan 3: Relokasi `DAFTAR_VIEW_PER_DOMAIN` ke `src/config/katalog_view.py`

**Sumber Paksaan**
Preseden arsitektur `src/config/` sebagai rumah data referensi lintas-layer yang sudah konsisten dipakai (`role_permissions.py`, `employees.py`, `llm.py` — semua dikonsumsi lebih dari satu titik pipeline), dikombinasikan dengan `docs/keterbatasan-diterima.md` #9 yang sudah mencatat risiko drift dari duplikasi katalog serupa (daftar 9-view performa-individu M2.3) sebagai preseden yang sebaiknya tidak diulang.

**Keputusan yang Diikuti**
`DAFTAR_VIEW_PER_DOMAIN` (docstring+data byte-identik) dipindah dari `src/layers/verification_gate/katalog_view.py` (M2.4) ke `src/config/katalog_view.py` (baru). `verifikasi_gate.py` diubah jadi konsumen (import), bukan pemilik data.

**Catatan Ketergantungan**
M3.1 (layer hulu, jalan lebih dulu di pipeline) dan Verification Gate M2.4 (layer hilir) sama-sama butuh mapping domain→67 `view_name` identik. Tanpa relokasi, salah satu opsi tersisa adalah dependency edge terbalik (hulu bergantung modul hilir) — membingungkan arah import graph.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **M3.1 transkripsi ulang sendiri (duplikasi disengaja)** — ditolak, menciptakan dua salinan independen dari dokumen sumber yang sama tanpa mekanisme deteksi divergensi; menggandakan risiko yang sudah tercatat di `docs/keterbatasan-diterima.md` #9, bukan menguranginya.
- **M3.1 import langsung dari `src.layers.verification_gate.katalog_view` tanpa relokasi** — ditolak, menciptakan dependency edge terbalik secara arsitektural (layer hulu bergantung modul layer hilir); data ini bukan "milik" Verification Gate, pemiliknya dokumen katalog itu sendiri.

---

## Keputusan 4: Fungsi Utama Menerima Satu `AtomicIntent`, Bukan `_semua()` per-List

**Sumber Paksaan**
Kalimat Lingkup `rancangan-retrieval-query.md` baris 35 sendiri: "dari **satu kebutuhan atomik**... mengumpulkan kandidat".

**Keputusan yang Diikuti**
`cari_kandidat_view(atomic_intent: AtomicIntent, domain_diizinkan: list[Domain])` beroperasi per-request tunggal — pola sama `verifikasi_gate()` M2.4, berbeda dari `identifikasi_domain_semua()` M2.1 yang orkestrasi list eksplisit diminta arsitektur.

**Catatan Ketergantungan**
Orkestrasi lintas banyak atomic intent (kalau dibutuhkan pemanggil, mis. Query Engine M3.4) adalah keputusan di luar M3.1, bukan tanggung jawab modul ini.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by kalimat Lingkup sumber sendiri, tidak ada ambiguitas.

---

## Keputusan 5: Parameter `list[Domain]`, Bukan Objek `AtomicIntentAuthorization` Utuh

**Sumber Paksaan**
Prinsip minimal coupling yang dipegang konsisten di layer lain (M2.3 `deteksi_constraint_atomic_intent()` juga menerima tipe spesifik, bukan objek upstream penuh).

**Keputusan yang Diikuti**
Pemanggil M3.1 wajib memfilter `AtomicIntentAuthorization.domain_decisions` (M2.2) ke `diizinkan=True` SEBELUM memanggil `cari_kandidat_view()` — M3.1 sendiri hanya menerima `list[Domain]` yang sudah bersih.

**Catatan Ketergantungan**
M3.1 tidak perlu tahu BAGAIMANA domain diotorisasi (lookup `role_permissions`, dst.) — cukup domain APA yang lolos. Mengikat M3.1 ke skema `authorization.py` penuh tidak memberi manfaat tambahan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Terima `AtomicIntentAuthorization` utuh, filter di dalam M3.1** — ditolak, menambah coupling ke skema M2.2 tanpa manfaat; filter satu baris di titik pemanggilan sudah cukup dan menjaga M3.1 fokus pada tanggung jawabnya sendiri.

---

## Keputusan 6: Filter Domain di Titik Materialisasi Kandidat (Structural, Bukan Post-Filter)

**Sumber Paksaan**
KK2 sumber yang zero-tolerance: "tidak ada kandidat dari domain yang ditolak yang ikut lolos ke tahap berikutnya" (`rancangan-retrieval-query.md`).

**Keputusan yang Diikuti**
`cari_bm25()` dan `cari_embedding()` sama-sama membangun `KandidatView` HANYA untuk `view_name` yang domain-nya ada di `domain_diizinkan` — tidak pernah mengonstruksi objek kandidat untuk domain terlarang sama sekali, baru difilter belakangan.

**Catatan Ketergantungan**
Post-filter (bangun semua kandidat dulu, saring belakangan) masih menyisakan risiko satu jalur kode lupa memfilter. Filter struktural di titik materialisasi membuat kebocoran domain terlarang mustahil terjadi tanpa mengubah logic konstruksi itu sendiri.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Bangun seluruh kandidat dari 67 view lalu filter domain di langkah terpisah** — ditolak, KK2 zero-tolerance menuntut jaminan struktural, bukan jaminan berbasis "asal langkah filter tidak lupa dipanggil".

---

## Keputusan 7: `AtomicIntent` Objek Utuh (Bukan `str` Mentah) sebagai Parameter

**Sumber Paksaan**
Preseden konsisten `identifikasi_domain_atomic_intent(atomic_intent: AtomicIntent)` (M2.1) dan pola serupa M2.3.

**Keputusan yang Diikuti**
`cari_kandidat_view()` menerima objek `AtomicIntent` utuh, bukan `teks_kebutuhan: str` mentah — hasil (`HasilPencarianKandidat.atomic_intent`) membawa balik referensi objek asal, mirror `AtomicIntentDomains.atomic_intent`/`AtomicIntentAuthorization.atomic_intent`.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by preseden konsisten seluruh layer domain_gate/.

---

## Keputusan 8: `retrieval.selected_view` TIDAK Diisi M3.1

**Sumber Paksaan**
`rancangan-retrieval-query.md` Milestone 3.3 baris 75 eksplisit: atribut itu baru diisi "begitu `view_name` final ditentukan" — setelah M3.2-3.3 selesai, mengayakan span M3.1 yang sama secara lintas-milestone.

**Keputusan yang Diikuti**
Span `retriever.cari_kandidat_view` M3.1 tidak pernah men-set `retrieval.selected_view` — hanya `retrieval.candidates_count` (dan atribut tambahan non-kontrak `retrieval.fallback_terpicu`/`retrieval.sumber_utama`).

**Catatan Ketergantungan**
M3.3 (milestone masa depan, di luar cakupan M3.1) bertanggung jawab mengisi atribut ini pada span yang sama begitu `view_name` final ditentukan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Isi `retrieval.selected_view` dengan kandidat skor tertinggi M3.1** — ditolak, bertentangan langsung dengan Lingkup M3.1 sendiri ("tanpa memutuskan satu pilihan final") dan kontrak M3.3 yang eksplisit menjadikan pengisian atribut ini tanggung jawabnya.

---

## Keputusan 9: Nama Span Custom `<subpackage>.<function>`, Bukan Literal `gen_ai.retrieval.documents`

**Sumber Paksaan**
Preseden kode: span Verification Gate M2.4 bernama `verification_gate.verifikasi_gate`/`verification_gate.check`, BUKAN literal frasa tabel kontraknya sendiri ("span non-LLM (deterministik)") — membuktikan kolom "jenis span" di `rancangan-observability-ai-chatbot.md` Bagian 2 bersifat deskriptif/kategorikal, bukan nama span literal wajib.

**Keputusan yang Diikuti**
Span pencarian M3.1 diberi nama `retriever.cari_kandidat_view` (tracer `retriever.retriever`) — mengikuti konvensi `<subpackage>.<function>` yang konsisten dipakai seluruh layer lain (`domain_gate.identifikasi_semua`, `verification_gate.verifikasi_gate`), bukan literal string `gen_ai.retrieval.documents` dari tabel baris 39.

**Catatan Ketergantungan**
Atribut yang benar-benar dikontrak (`retrieval.candidates_count`, dst.) tetap wajib di-set persis sesuai kontrak — hanya nama span itu sendiri yang mengikuti konvensi project, bukan string tabel.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Nama span literal `gen_ai.retrieval.documents`** — ditolak, tidak konsisten dengan preseden M2.4 dan seluruh layer lain yang memakai konvensi `<subpackage>.<function>`.

---

## Keputusan 10: `prompt.id`/`prompt.version` Tidak Berlaku untuk Span M3.1

**Sumber Paksaan**
`rancangan-observability-ai-chatbot.md` baris 47 eksplisit: atribut itu khusus "pemanggilan `chat`" (system prompt bertemplate `src/prompts/`, dari Manajemen Prompt Fase 2).

**Keputusan yang Diikuti**
Span pencarian M3.1 (non-LLM) dan span anak embedding fallback (operasi `embeddings`, bukan `chat`, tanpa system prompt Jinja2) TIDAK men-set `prompt.id`/`prompt.version` — atribut itu baru relevan di M3.2 (span `chat`, kecocokan makna).

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by penjelasan eksplisit dokumen kontrak sendiri.

---

## Keputusan 11: Panggilan Embedding Fallback Reuse `get_openrouter_client()` Apa Adanya

**Sumber Paksaan**
`docs/keterbatasan-diterima.md` #7: mitigasi timeout eksplisit (90s, max_retries=1) "berlaku untuk SELURUH konsumen fungsi ini" — bukan cakupan yang sengaja diperluas per-konsumen baru.

**Keputusan yang Diikuti**
`embed_korpus()`/`cari_embedding()` (`pencarian_embedding.py`) memanggil `get_openrouter_client()` tanpa parameter timeout/retry custom tambahan.

**Catatan Ketergantungan**
Kegagalan teknis (timeout/error) pada panggilan embedding fallback ditangani graceful — tetap mengembalikan kandidat BM25 (`status=SEBAGIAN`), tidak memblokir pipeline, pola sama M2.1 "verifikasi titik buta gagal teknis".

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by keterbatasan-diterima yang sudah mengikat seluruh konsumen `get_openrouter_client()`.

---

## Keputusan 12: `__init__.py` Dibuat Sejak Checkpoint Pertama yang Menyentuh Folder

**Sumber Paksaan**
Lesson-learned M2.4 (`logs.md` Checkpoint 2): lupa membuat `__init__.py` menyebabkan `ModuleNotFoundError`.

**Keputusan yang Diikuti**
`src/layers/retriever/__init__.py` dan `tests/layers/retriever/__init__.py` dibuat di Checkpoint 3 (checkpoint pertama yang menyentuh kedua folder), bukan ditunda ke checkpoint kode utama.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by lesson-learned tercatat eksplisit di governance M2.4.

---

## Keputusan 13: `decisions.md` sebagai Task Pertama

**Sumber Paksaan**
Instruksi eksplisit user, preseden konsisten M1.4-M2.4.

**Keputusan yang Diikuti**
Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode/skema apa pun ditulis.

**Catatan Ketergantungan**
Tidak ada.

**Opsi yang Dipertimbangkan tapi Ditolak**
Tidak ada — forced by instruksi eksplisit user/`CLAUDE.md`.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Mekanisme pencarian kandidat: Hybrid BM25 + fallback embedding | A | Checkpoint 5-6, 10 |
| 2 | Model embedding fallback: dibandingkan empiris, dikunci provisional | A | Checkpoint 6-9 |
| 3 | Relokasi DAFTAR_VIEW_PER_DOMAIN ke src/config/ | B | Checkpoint 2 |
| 4 | Fungsi utama menerima satu AtomicIntent, bukan _semua() | B | Checkpoint 10 |
| 5 | Parameter list[Domain], bukan AtomicIntentAuthorization utuh | B | Checkpoint 10 |
| 6 | Filter domain di titik materialisasi kandidat (structural) | B | Checkpoint 5-6 |
| 7 | AtomicIntent objek utuh sebagai parameter | B | Checkpoint 3, 10 |
| 8 | retrieval.selected_view TIDAK diisi M3.1 | B | Checkpoint 10 |
| 9 | Nama span custom &lt;subpackage&gt;.&lt;function&gt;, bukan literal gen_ai.retrieval.documents | B | Checkpoint 10 |
| 10 | prompt.id/prompt.version tidak berlaku untuk span M3.1 | B | Checkpoint 10 |
| 11 | Embedding fallback reuse get_openrouter_client() apa adanya | B | Checkpoint 6, 10 |
| 12 | __init__.py dibuat sejak checkpoint pertama | B | Checkpoint 3 |
| 13 | decisions.md sebagai Task pertama | B | Plan |
