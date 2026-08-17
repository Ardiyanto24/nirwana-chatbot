# Keputusan Tertunda — Backlog Project-Wide

Dokumen ini mencatat keputusan teknis yang genuinely terbuka tapi **belum saatnya diambil** — beda dari `docs/keterbatasan-diterima.md` (keterbatasan yang sudah ditemukan dan sengaja diterima) dan `decisions.md` per-milestone (keputusan yang sudah final). Tiap entri menyebut konteks kemunculannya dan pemicu peninjauan ulang yang membuatnya layak diputuskan.

---

## 1. Database untuk Proyek Ini (Session Memory + Kemungkinan Migrasi Daftar Role) — ✅ SELESAI (M1.5)

**Status:** SELESAI di Milestone 1.5 (2026-08-15). Keputusan final: **Supabase** (Postgres terkelola, project sama dengan rencana dashboard observability M5.x/M6.x) diakses lewat **SQLModel**; `src/config/roles.yaml` **dimigrasi penuh** ke tabel `roles` di database yang sama (file YAML dihapus). Detail lengkap + opsi yang dipertimbangkan tapi ditolak: `milestones/1.5-tarik-session-memory/decisions.md` Keputusan 1-3, 9.

**Muncul di:** Milestone 1.2 (Input Layer), saat mendiskusikan penyimpanan daftar 20 `role_title` untuk validasi struktural (2026-08-14).

**Konteks kemunculan:** Awalnya dipertimbangkan hardcode daftar role sebagai konstanta Python di Input Layer. User mempertanyakan apakah proyek ini sebaiknya punya database sendiri, mengingat Milestone 1.5 (Session Memory) akan butuh storage juga. Dikonfirmasi secara arsitektur: proyek ini **boleh** punya database sendiri (terpisah dari database data platform — larangan "REST API bukan akses SQL" di `arsitektur-ai-chatbot-rbac.md` baris 7 hanya soal database data platform, bukan database milik proyek Lapis 1 ini sendiri). Milestone 1.5 sendiri eksplisit menyatakan "keputusan implementasi bebas" soal teknologi storage Session Memory.

Untuk Milestone 1.2 spesifik, diputuskan **file config YAML** (`src/config/roles.yaml`) sebagai jalan tengah — tidak menambah kompleksitas database sebelum kebutuhan Session Memory yang sesungguhnya diketahui, tapi juga tidak serigid hardcode Python. Keputusan database *utuh* untuk proyek (dipakai Session Memory, dan berpotensi juga jadi tempat daftar role dipindahkan) sengaja ditunda ke sini.

**Kenapa belum saatnya diputuskan:** Milestone 1.5 belum dimulai — teknologi storage yang tepat sebaiknya dipilih dengan konteks kebutuhan Session Memory yang sesungguhnya (skema paket per atomic intent, pola akses/query, TTL, dst — lihat `arsitektur-ai-chatbot-rbac.md` §7), bukan diputuskan sekarang hanya berdasar kebutuhan kecil (20 baris statis daftar role).

**Pemicu peninjauan ulang:** Awal implementasi Milestone 1.5 (Penarikan/Penyimpanan Data Session Memory) — saat itu, putuskan teknologi storage (mis. SQLite/PostgreSQL/lainnya) untuk Session Memory, dan sekalian evaluasi apakah `src/config/roles.yaml` sebaiknya dipindahkan ke database yang sama (kemudahan admin terpusat) atau tetap sebagai file config terpisah (kesederhanaan, tidak ada dependency tambahan untuk data yang jarang berubah).

---

## 2. Model Embedding Final Retriever (Milestone 3.1) — Provisional, Belum Ditutup Permanen

**Status:** AKTIF — model SUDAH dipilih dan dipakai produksi (`OPENROUTER_MODEL_RETRIEVER_EMBEDDING = "openai/text-embedding-3-small"`, `src/config/llm.py`), TAPI keputusan ini **sengaja tidak ditutup permanen** seperti pola model chat/completion milestone lain (M1.3-M2.3) — instruksi eksplisit user.

**Muncul di:** Milestone 3.1 (Pengumpulan Kandidat View), Checkpoint 7-9 (2026-08-17).

**Konteks kemunculan:** Mekanisme pencarian kandidat M3.1 diputuskan Hybrid (BM25 utama + fallback embedding semantik). User eksplisit meminta 3 kandidat model embedding (Qwen3-Embedding-4B, Qwen3-Embedding-8B, `text-embedding-3-small`) dibandingkan secara empiris lewat eval nyata (`evals/3.1-pengumpulan-kandidat-view/`) sebelum dikunci — bukan dipilih di depan tanpa bukti, beda dari preseden M1.4 (model chat dipilih dari benchmark publik SEA-HELM tanpa eval internal). Hasil eval (5 skenario stress-test kegagalan BM25): Qwen3-Embedding-4B gagal total (0/5 recall), Qwen3-Embedding-8B dan `text-embedding-3-small` sama-sama sempurna (5/5) — `text-embedding-3-small` dipilih karena rank rata-rata lebih baik, jauh lebih konsisten, dan latensi ~2.5x lebih rendah.

**Kenapa belum ditutup permanen:** Cakupan eval Checkpoint 7 sengaja terbatas (5 skenario stress-test, dirancang manual — bukan ratusan kasus produksi nyata). Model dengan performa TERBAIK dari 3 kandidat yang diuji dipakai SEKARANG sebagai keputusan pragmatis, tapi ini bukan klaim bahwa `text-embedding-3-small` adalah pilihan optimal untuk SELURUH ruang kasus nyata yang belum tentu tercermin di 5 skenario buatan tangan.

**Pemicu peninjauan ulang:**
1. Milestone 3.2 (atau tahap produksi manapun setelah M3.1) menunjukkan pola kegagalan fallback nyata (recall rendah pada kasus nyata) yang tidak tertangkap 5 skenario eval Checkpoint 7 — revisit dengan skenario tambahan dari data produksi asli.
2. OpenRouter merilis model embedding baru yang relevan untuk Bahasa Indonesia (mis. Qwen versi lebih baru, atau model spesifik-Indonesia) — bandingkan ulang terhadap `text-embedding-3-small` yang sedang dipakai.
3. Evaluasi biaya/latensi berubah signifikan setelah dipakai pada volume request nyata (harga per-token OpenRouter berubah, atau volume fallback ternyata jauh lebih tinggi dari perkiraan karena temuan trigger di bawah).
4. **Terkait erat:** trigger `BM25_SKOR_MINIMUM` (lihat `milestones/3.1-pengumpulan-kandidat-view/decisions.md` Keputusan 1 + Checkpoint 9) juga provisional — kalau trigger direvisi signifikan (mis. fallback jadi jauh lebih sering terpicu), volume pemakaian model embedding ini berubah drastis, yang bisa mengubah kalkulasi biaya/latensi di atas dan layak jadi pemicu peninjauan ulang tersendiri.

---

## 3. Konvensi Parameter `chatbot_api` per-View (Milestone 3.4) — Provisional, Menunggu Rekonsiliasi

**Status:** AKTIF — konvensi SUDAH dipakai produksi (`PARAM_WHITELIST_VIEW`, `src/layers/query_engine/param_whitelist.py`; didokumentasikan lengkap di `docs/kontrak-parameter-chatbot-api-usulan.md`), TAPI eksplisit BUKAN kontrak resmi — instruksi langsung user.

**Muncul di:** Milestone 3.4 (Penyusunan Request), Checkpoint 1-2 (2026-08-17).

**Konteks kemunculan:** `docs/03-domain-source/api-chatbot.md` hanya mendokumentasikan 4 parameter global (`role_title`, `employee_id`, `property_id`, `limit`/`offset`) — whitelist parameter PER-VIEW yang dirujuk dokumen itu sendiri (`whitelist_<domain>.py`) sepenuhnya di luar repo ini (kode `chatbot_api` eksternal), ditandai eksplisit "masih terbuka" di `arsitektur-ai-chatbot-rbac.md` Bagian 8 butir 5. User dimintai klarifikasi (dua CSV yang sempat diberikan — `properties.csv`, `employees_deduped.csv` — ternyata data isi tabel, bukan dokumentasi kontrak), yang kemudian mengonfirmasi: file kontrak resmi `chatbot_api` MEMANG belum final ("masih menunggu project ini selesai untuk parameter pastinya"), dan secara eksplisit meminta konvensi provisional (nama kolom asli view, lihat `milestones/3.4-penyusunan-request/decisions.md` Keputusan 1) dipakai SEKARANG, DIDOKUMENTASIKAN formal di `docs/kontrak-parameter-chatbot-api-usulan.md` untuk direkonsiliasi dengan tim pembangun `chatbot_api` di akhir proyek.

**Kenapa belum ditutup permanen:** Konvensi ini murni diturunkan dari nama kolom yang terdokumentasi di `katalog-data-chatbot.md` (data platform sisi kita) — TIDAK ada verifikasi langsung terhadap kode `chatbot_api` sungguhan (di luar akses repo ini) bahwa nama query parameter benar-benar meniru nama kolom SELECT 1:1. Arsitektur sistem sendiri sudah mendesain jalur pemulihan untuk kasus param salah (respons `400` dari Execution M4.x kembali ke M3.4 untuk revisi) — mengonfirmasi bahwa konvensi ini memang dirancang untuk diuji/dikoreksi berdasar perilaku nyata, bukan diklaim benar dari awal.

**Pemicu peninjauan ulang:**
1. Rekonsiliasi langsung dengan tim pembangun `chatbot_api` di akhir proyek — WAJIB, bukan opsional.
2. Milestone 4.x (Execution) menunjukkan pola kegagalan `400` berulang yang mengindikasikan nama parameter salah secara sistematis (bukan kesalahan LLM per-kasus).
3. Dokumentasi/akses resmi ke `whitelist_<domain>.py` (atau setara) menjadi tersedia sebelum akhir proyek — revisit segera begitu tersedia, tidak perlu menunggu sampai akhir.

**Addendum (Milestone 4.2, 2026-08-17): usulan kontrak `last_refreshed_at`/`data_quality_status`.** Saat merancang klasifikasi respons Execution (M4.2), muncul pertanyaan yang tidak bisa dijawab dari dalam project ini: begitu `chatbot_api` mengembalikan `200`, tidak ada cara membedakan hasil yang genuinely benar (mis. `COUNT=0` karena memang tidak ada kejadian) dari hasil yang keliru (mis. `COUNT=0` karena filter salah atau pipeline data belum ter-refresh). Ide awal "daftar nilai valid per kolom" (filter DISTINCT + monitoring drift kategorikal) HANYA menutup drift kategorikal (mis. nilai `channel` baru yang belum terdaftar) — TIDAK menutup korektnes nilai AGREGAT (COUNT/SUM selalu "valid" secara struktural, tidak ada "daftar COUNT yang sah" untuk dicocokkan).

Solusi yang benar-benar menutup celah ini butuh sinyal KESEHATAN PIPELINE, bukan tebakan isi data — diusulkan ke tim database engineering:

1. **`last_refreshed_at` per view/domain** — timestamp kapan reverse ETL terakhir berhasil mengisi view tersebut. Sinyal objektif/tertutup (bukan judgment konten) — kalau data ternyata basi, ini terdeteksi tanpa perlu tahu apa pun soal isinya.
2. **`data_quality_status: "ok" | "flagged"` per view/domain** — hasil data-contract check (row-count range wajar, null-rate maksimum per kolom, PLUS perluasan ide DISTINCT-value asli: daftar nilai kategorikal dikenal per kolom + monitoring berkala yang men-trigger notifikasi ke PIC database kalau muncul nilai baru, PIC mengonfirmasi apakah masuk akal secara bisnis sebelum daftar diperbarui).

Bentuk implementasi diusulkan 2 opsi ke tim database: (A) tambahkan ke response envelope tiap endpoint (`{"data": [...], "meta": {"last_refreshed_at": ..., "data_quality_status": ...}}`), atau (B) endpoint metadata terpisah ringan (`GET /chatbot/{domain}/{view_name}/_meta`). Draf pesan lengkap ke tim database sudah disiapkan (lihat riwayat sesi 2026-08-17), siap diajukan saat rekonsiliasi kontrak parameter (pemicu #1 di atas) — TIDAK mendesak, tidak memblokir M4.2 (M4.2 berjalan dengan asumsi konservatif: seluruh `200` dianggap `berhasil` sampai sinyal ini tersedia, lihat `milestones/4.2-klasifikasi-respons-dan-penanganan-kegagalan/decisions.md` Keputusan 1-2).

**Pemicu peninjauan ulang tambahan:** begitu tim database menyediakan `last_refreshed_at`/`data_quality_status` (atau setara), revisit klasifikasi berhasil/sebagian M4.2 — sinyal ini akan jadi basis tertutup pertama yang sah untuk `StatusEksekusi.SEBAGIAN` di layer Execution.

**Addendum kedua (2026-08-17): pemicu TERPENUHI — endpoint `_meta` aktif (Milestone 4.7 tim database), TAPI ambang batas kesegaran wajib dikomunikasikan balik.** Tim database mengonfirmasi `GET /chatbot/{domain}/{view_name}/_meta` sudah live, Opsi B (endpoint terpisah) dipilih persis seperti diusulkan, digate otorisasi identik endpoint data. Detail respons dan keterbatasan V1 (per pesan tim database, disimpan verbatim untuk rujukan):
- Field `null` = genuinely tidak diketahui, BUKAN default "ok" — dikonfirmasi eksplisit, dipakai sebagai dasar Keputusan 11 `milestones/4.2-.../decisions.md` (null TIDAK disamakan `flagged`).
- 2 view `guests-contact`/`guests-profile`: `last_refreshed_at`/`data_quality_status` HANYA mencerminkan freshness tabel `guests`, BELUM termasuk data booking terkait.
- `data_quality_status` mencerminkan hasil run pengecekan TERAKHIR yang tercatat, bukan real-time — bisa sedikit basi mengikuti jadwal job.
- V1 reuse pengecekan yang sudah ada (BUKAN pengecekan baru seperti rentang row-count/null-rate/nilai kategorikal yang sempat didiskusikan) — disimpan sebagai backlog tim database, akan dibahas ulang kalau sinyal V1 terbukti kurang presisi (terutama kasus COUNT/SUM keliru yang tidak terdeteksi pengecekan otomatis manapun).

**Keputusan sisi kita**: `EXECUTION_DATA_STALENESS_THRESHOLD_JAM` (konstanta di `src/config/chatbot_api.py`, nilai starting point 48 jam) dipakai untuk menandai `SEBAGIAN` kalau `last_refreshed_at` melewatinya — TAPI ini murni starting point non-empiris, BUKAN kalibrasi berdasar jadwal refresh nyata per view (67 view kemungkinan besar punya kadensi sangat berbeda — reservasi harian vs referensi properti yang jarang berubah). Lihat `milestones/4.2-.../decisions.md` Keputusan 11 untuk detail lengkap desain (`flagged`/stale → `SEBAGIAN`; `null`/gagal → tetap `berhasil`+catatan).

**Item aksi eksplisit — WAJIB dikomunikasikan balik ke tim database** (draf pesan siap dikirim user, isi pokok):
> Terima kasih infonya, sudah kami integrasikan. Satu hal yang perlu kami sampaikan: kami memakai ambang batas kesegaran seragam 48 jam untuk SELURUH view (belum per-view) untuk menentukan kapan `last_refreshed_at` dianggap "basi" dan memengaruhi jawaban ke user — ini murni starting point kami, bukan angka yang dikalibrasi dari jadwal refresh nyata kalian. Kalau kalian punya informasi jadwal refresh tipikal per-domain/view (mis. reservasi harian vs referensi properti jarang berubah), kami sangat terbuka menyesuaikan supaya tidak salah tandai data yang sebenarnya masih segar sesuai jadwalnya masing-masing. Kabari kalau ada masukan.

**Pemicu peninjauan ulang tambahan (kedua):** (a) tim database membalas dengan masukan jadwal refresh per view — kalibrasi ulang `EXECUTION_DATA_STALENESS_THRESHOLD_JAM` (kemungkinan jadi per-view, bukan konstanta tunggal); (b) begitu ada data produksi nyata, evaluasi apakah 48 jam terlalu ketat/longgar berdasar frekuensi `SEBAGIAN` yang genuinely muncul; (c) kalau tim database membangun pengecekan V2 (row-count/null-rate/nilai kategorikal, item backlog mereka), evaluasi apakah `data_quality_status` masih perlu digabung dengan cek `last_refreshed_at` terpisah atau cukup satu sinyal gabungan.
