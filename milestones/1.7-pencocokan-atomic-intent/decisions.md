# Decisions — Milestone 1.7: Membangun Pencocokan Atomic Intent terhadap Data Session Memory

## Keputusan 1: Mekanisme Pencocokan — LLM Semantik

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
`arsitektur-ai-chatbot-rbac.md` Bagian 8 poin 1 eksplisit menandai mekanisme Langkah 7 "KERANGKA AWAL" — belum diputuskan apakah perlu LLM (pencocokan semantik) atau bisa deterministik dengan bantuan struktur tambahan dari Langkah 2 (M1.3), karena teks atomic intent hasil rewrite tidak dijamin identik string dengan `teks_kebutuhan` yang tersimpan.

**Keputusan yang Dipilih**
LLM semantik — satu jenis pemanggilan LLM menilai kesesuaian MAKNA antara `teks_kebutuhan` atomic intent baru vs kandidat tersimpan.

**Alasan**
Sejalan Prinsip Arsitektur #3 (`CLAUDE.md`/`arsitektur-ai-chatbot-rbac.md` §1.3): ruang kesalahan terbuka (kesesuaian makna bahasa) wajib LLM independen. Prinsip Baru §9 dokumen arsitektur sendiri eksplisit: "kesempitan permukaan tugas tidak otomatis mengizinkan verifikasi deterministik" — pencocokan makna dua kalimat Indonesia (paraphrase, granularitas berbeda) genuinely ruang kesalahan terbuka, bukan closed error space yang bisa didaftar tertutup di depan.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Deterministik murni** (mis. label_bentuk_jawaban sama + overlap kata kunci/entitas ternormalisasi) — ditolak user; risiko melanggar Prinsip Arsitektur #3 sendiri kalau ruang kesalahan paraphrase tidak genuinely closed, dan dokumen arsitektur eksplisit mencatat teks bisa tidak identik string.
- **Hybrid: pre-filter deterministik + LLM final judgment** — dipertimbangkan sebagai opsi menengah (mengurangi panggilan LLM), tapi tidak dipilih user; menambah satu lapis logic untuk manfaat yang bergantung ukuran pool kandidat riil (biasanya kecil — M1.5 hanya menarik dari SATU turn spesifik yang dirujuk M1.3).

**Dampak**
`src/layers/context_resolution/matching.py` memanggil LLM per atomic intent (bukan aturan statis). Lihat Keputusan 4 (model).

---

## Keputusan 2: Pola Verifikasi — Satu Panggilan + Fallback Aman (Bukan Generate-lalu-Verify Penuh)

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Precedent yang tersedia: M1.3 (`detect_turn_dependency()`, satu panggilan + bounds-check deterministik, karena fallback amannya jelas — `is_dependent=False`) vs M1.6 (generate-lalu-verify penuh dengan LLM verifier independen kedua, karena KEDUA arah kesalahan Decomposition sama-sama material). M1.7 perlu kebijakan serupa untuk keputusan cocok/tidak cocok.

**Keputusan yang Dipilih**
Satu panggilan LLM per atomic intent, prompt didesain konservatif (hanya klaim cocok kalau yakin), plus bounds-check deterministik (index kandidat yang dirujuk harus benar-benar ada di pool yang dikirim) sebagai jaring pengaman struktural. TANPA LLM verifier independen kedua.

**Alasan**
Risiko di titik ini asimetris, beda dari Decomposition M1.6: false negative (gagal cocok → atomic intent jatuh ke `perlu_eksekusi`, di-eksekusi ulang) aman dan murah — hasil akhirnya tetap benar, cuma boros. False positive (cocok keliru → data basi/salah dipakai diam-diam sebagai "selesai") adalah risiko sebenarnya yang perlu dicegah. Asimetri ini ditangani cukup lewat desain prompt konservatif + fallback deterministik ke `perlu_eksekusi` pada kegagalan apa pun (parse gagal, API gagal, index dangling) — tidak butuh LLM kedua untuk menilai ulang, karena arah amannya sudah jelas dan murah untuk selalu jadi default.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Generate-lalu-verify penuh (2 LLM independen, pola M1.6)** — presisi lebih tinggi terhadap false positive, tapi ditolak user; 2x biaya/latensi per pengecekan untuk risiko yang sudah bisa ditangani lewat desain prompt + fallback aman satu arah (beda dari M1.6 yang risikonya dua arah sama-sama material).

**Dampak**
`match_atomic_intents()` tidak punya loop retry/verifier terpisah — beda struktur dari `decompose_question()` M1.6.

---

## Keputusan 3: Model — Reuse Qwen3-32B

**Status:** Diputuskan sebelum implementasi (dari plan, lewat `AskUserQuestion`).

**Latar Belakang**
Tugas pencocokan (satu panggilan, output JSON + index/referensi opsional) strukturnya mirip M1.3 (DeepSeek V4 Flash 0731) dan M1.6 Langkah 4-5 (Qwen3-32B). Karena Keputusan 2 menolak verifier independen kedua, argumen "butuh keragaman model" yang mendasari pilihan DeepSeek V4 Pro di M1.6 Langkah 6 tidak berlaku di sini.

**Keputusan yang Dipilih**
Qwen3-32B via OpenRouter (`qwen/qwen3-32b`) — reuse model M1.4 dan M1.6 Langkah 4-5.

**Alasan**
Sudah terbukti andal untuk tugas berbahasa Indonesia + output JSON terstruktur di project ini (M1.4: 11/12 benar makna; M1.6: dangling reference index jarang terjadi). Termurah, tidak menambah model baru ke project tanpa alasan kuat.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Riset model baru** — ditawarkan eksplisit ke user (mengikuti pola M1.4/M1.6 yang selalu buka putaran riset untuk keputusan model), tapi user memilih langsung reuse tanpa riset tambahan karena tidak ada karakteristik tugas yang berbeda secara material dari klasifikasi/pemecahan/rewrite yang sudah terbukti bekerja dengan Qwen3-32B.

**Dampak**
Konstanta `OPENROUTER_MODEL_MATCHING` di `src/config/llm.py`, terisolasi dari `OPENROUTER_MODEL_DECOMPOSITION` meski nilainya kebetulan sama — lihat Keputusan 9.

---

## Keputusan 4 (Jenis A — Judgment Call Penulis, Dikonfirmasi User): Filter Kandidat Hanya `status == berhasil`

**Status:** Diajukan penulis lewat diskusi pemahaman sistem (bukan `AskUserQuestion` formal), dikonfirmasi user sebelum plan ditulis ("sudah benar").

**Latar Belakang**
Dokumen sumber tidak eksplisit membahas apakah kandidat dari Session Memory perlu difilter berdasarkan `status` sebelum ditawarkan sebagai kandidat cocok. Kandidat yang `status`-nya `gagal_teknis`/`ditolak_otorisasi`/`sebagian`/`terblokir_ketergantungan` merepresentasikan eksekusi yang tidak sepenuhnya berhasil — kalau tetap ditawarkan sebagai kandidat cocok, atomic intent baru berisiko ditandai "selesai" padahal yang ditempel adalah kegagalan atau hasil parsial lama, membuat Interpretation nanti keliru menyimpulkan kebutuhan itu benar-benar terjawab.

**Keputusan yang Dipilih**
`match_atomic_intents()` memfilter `candidates` ke `status == berhasil` SAJA sebelum dijadikan pool yang ditawarkan ke LLM. Kandidat dengan status lain diperlakukan seakan tidak ada di pool — atomic intent yang seharusnya cocok ke kandidat non-`berhasil` tetap jatuh ke `perlu_eksekusi` (aman: dieksekusi ulang, berpotensi dapat hasil lebih baik daripada mewarisi kegagalan/hasil parsial lama).

**Alasan**
Konsisten Prinsip Arsitektur "Kejujuran terhadap keterbatasan" — status non-normal tidak pernah disamarkan jadi terlihat "selesai". `perlu_eksekusi` untuk kasus ini adalah default paling aman yang tersedia tanpa perlu logic tambahan (mis. mencoba "mewarisi" status lama, yang berisiko lebih rumit dan tidak diminta dokumen sumber).

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Tidak memfilter (semua status jadi kandidat)** — lebih sederhana, tapi ditolak karena risiko nyata di atas (silently menawarkan kegagalan lama sebagai "selesai").
- **Filter longgar (`berhasil` + `sebagian`)** — dipertimbangkan (data parsial mungkin masih berguna dibanding eksekusi ulang penuh), tapi ditolak: "sebagian" secara definisi berarti belum lengkap, re-eksekusi berpotensi mendapat hasil lebih lengkap, jadi tidak ada alasan kuat mewarisi hasil yang diketahui belum lengkap.

**Dampak**
`match_atomic_intents()` melakukan filter status di awal fungsi, sebelum jalur pintas kandidat-kosong dievaluasi (kandidat kosong SETELAH filter, bukan sebelum).

---

## Keputusan 5 (Jenis A — Judgment Call Penulis, Dikonfirmasi User): Satu Panggilan LLM per Atomic Intent

**Status:** Diajukan penulis lewat diskusi pemahaman sistem, dikonfirmasi user.

**Latar Belakang**
Satu turn bisa punya beberapa atomic intent baru (hasil M1.6 majemuk) yang masing-masing perlu dicek terhadap pool kandidat yang sama. Perlu diputuskan: satu panggilan LLM per atomic intent (N panggilan), atau satu panggilan batch untuk seluruh atomic intent turn ini sekaligus (1 panggilan, LLM mengembalikan pemetaan penuh).

**Keputusan yang Dipilih**
Satu panggilan LLM per atomic intent.

**Alasan**
Konsisten granularitas M1.3 (satu panggilan per turn)/M1.6 Langkah 5 (satu panggilan per pemanggilan fungsi) — tiap keputusan cocok/tidak bisa dilacak dan diuji terpisah dengan span `chat` sendiri, kegagalan satu item tidak mencemari keputusan item lain dalam prompt/response yang sama.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Satu panggilan batch untuk seluruh atomic intent turn ini** — lebih hemat biaya/latensi kalau atomic intent banyak, dan memberi LLM konteks penuh (bisa menghindari dua atomic intent berbeda "berebut" kandidat yang sama secara tidak sengaja). Tidak dipilih: menambah kompleksitas parsing (satu respons JSON memetakan banyak item) untuk manfaat yang tidak terbukti dibutuhkan mengingat jumlah atomic intent per turn biasanya kecil (lihat M1.6: mayoritas skenario eval 1-3 atomic intent).

**Dampak**
`match_atomic_intents()` melakukan loop atas `atomic_intents`, satu span `chat` per iterasi (kalau pool kandidat tidak kosong).

---

## Keputusan 6 (Jenis A — Judgment Call Penulis, Dikonfirmasi User): Tidak Ada Eksklusivitas Antar Match

**Status:** Diajukan penulis lewat diskusi pemahaman sistem, dikonfirmasi user.

**Latar Belakang**
Karena Keputusan 5 memproses tiap atomic intent secara independen, mungkin saja dua atomic intent baru yang berbeda sama-sama dinilai cocok ke kandidat yang sama persis.

**Keputusan yang Dipilih**
Tidak ada mekanisme yang memaksa keunikan — kalau dua atomic intent baru sama-sama cocok ke kandidat yang sama, keduanya tetap ditandai "selesai" dengan paket yang sama.

**Alasan**
Dokumen sumber tidak melarang ini, dan skenarionya wajar terjadi (mis. pertanyaan majemuk yang tidak sengaja menanyakan hal yang sama dua kali dengan frasa berbeda) — memaksa eksklusivitas butuh logic tambahan (mis. urutan prioritas siapa yang "menang") yang tidak diminta dan berpotensi menciptakan perilaku arbitrer yang lebih sulit dijelaskan daripada membiarkan keduanya cocok.

**Opsi yang Dipertimbangkan tapi Ditolak**
- **Paksa eksklusivitas (kandidat hanya bisa dipakai sekali)** — tidak dipilih; menambah kompleksitas (aturan tie-breaking) untuk kasus yang jarang terjadi dan tidak diminta dokumen sumber.

**Dampak**
Tidak ada state "kandidat sudah dipakai" yang perlu dilacak lintas iterasi loop Keputusan 5.

---

## Keputusan 7 (Forced): Arsip Ulang Memakai `atomic_intent_id` Original, Field Lain Disalin Utuh

**Sumber Paksaan:** Komentar eksplisit di kode `src/db/models.py` (`SessionMemoryPackageRow`, ditulis M1.5): *"Primary key sintetik (auto-increment), BUKAN atomic_intent_id - Milestone 1.7 nanti akan menyimpan ULANG paket yang sama (atomic_intent_id sama) sebagai baris arsip baru di bawah turn yang berjalan... jadi atomic_intent_id BUKAN unik per baris."* Diperkuat teks Lingkup M1.7 (`rancangan-context-decomposition.md`): "menyimpan ulang **paketnya**" (paket yang SAMA, bukan paket baru).

**Keputusan yang Diikuti:** `archive_matched_packages()` membangun `SessionMemoryPackage` baru dengan `atomic_intent_id`/`teks_kebutuhan`/`label_bentuk_jawaban`/`nilai_hasil`/`catatan_interpretasi`/`status` disalin UTUH dari `paket` (hasil match, ASAL dari turn yang dirujuk M1.3) — BUKAN dari `atomic_intent_id` baru yang di-generate M1.6 untuk turn saat ini. Hanya `turn_index` yang diganti jadi turn SAAT INI. `sumber` TETAP nilai original ("session_memory (turn N)", N = turn asal), TIDAK ditimpa.

**Catatan Ketergantungan:** Ini yang membuat KK3 (rantai turn 7→5→3) bisa lolos — rantai `sumber` tidak pernah putus meski paket diarsipkan ulang berkali-kali lintas turn.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced eksplisit oleh komentar desain M1.5 yang sudah mengantisipasi kebutuhan ini sebelum M1.7 dimulai.

---

## Keputusan 8 (Forced): Span Langkah 7 — Wrapper Non-LLM + `chat` Bersarang

**Sumber Paksaan:** `rancangan-observability-ai-chatbot.md` Bagian 2 baris 36 — "Context Resolution — Langkah 7 (Pencocokan) | custom, non-LLM atau `chat` (tergantung mekanisme final — lihat status KERANGKA AWAL...) | jumlah atomic intent cocok/tidak cocok".

**Keputusan yang Diikuti:** Karena mekanisme final (Keputusan 1) adalah LLM per-item (0..N panggilan, bukan satu panggilan tunggal), desain paling sesuai kontrak: span pembungkus non-LLM (`matching.evaluate`) membawa atribut agregat kontrak (`intent.matched_count`/`intent.unmatched_count`, interpretasi "jumlah atomic intent cocok/tidak cocok"), dengan span `chat` anak untuk TIAP panggilan LLM sungguhan (`gen_ai.request.model`, token usage — mirror pola M1.3/M1.6). Kalau pool kandidat kosong (jalur pintas Keputusan 4), TIDAK ada span `chat` sama sekali (nol panggilan LLM sungguhan) — hanya span `matching.evaluate` dengan count kosong.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by kontrak observability, interpretasi paling faithful terhadap kalimat "custom, non-LLM ATAU chat" sebagai kombinasi (bukan pilih salah satu secara eksklusif) mengingat mekanisme LLM per-item yang genuinely dipilih.

---

## Keputusan 9 (Forced): Struktur Kode — `matching.py` di Subpackage `context_resolution/`

**Sumber Paksaan:** `CLAUDE.md` Struktur Repository — `src/layers/context_resolution/` sudah eksplisit dicatat menaungi Milestone 1.3/1.4/1.5/**1.7**.

**Keputusan yang Diikuti:** `src/layers/context_resolution/matching.py` (bukan subpackage baru terpisah). Nama fungsi/parameter Inggris — mirror konvensi 3 file lain di subpackage ini (`turn_dependency.py`, `rewrite.py`, `session_memory.py`, semua nama fungsi Inggris), beda dari `decomposition/` yang pakai nama Indonesia. Skema baru `src/schemas/matching.py`: `MatchStatus` (Enum `selesai`/`perlu_eksekusi`), `AtomicIntentMatch` (`atomic_intent: AtomicIntent`, `status: MatchStatus`, `paket: SessionMemoryPackage | None`, validator konsistensi status↔paket — mirror pola validator `AtomicIntent.bergantung_pada_konsisten_dengan_relasi` M1.6). Fungsi mengembalikan `list[AtomicIntentMatch]` langsung tanpa kelas pembungkus tambahan. Konstanta model terisolasi `OPENROUTER_MODEL_MATCHING` (preseden Keputusan 9 M1.4/Keputusan 11 M1.6).

**Opsi yang Dipertimbangkan tapi Ditolak:** Subpackage baru terpisah (`src/layers/matching/`) — tidak dipertimbangkan serius, bertentangan langsung dengan CLAUDE.md yang sudah menaruh M1.7 di bawah `context_resolution/` sejak M1.2.

---

## Keputusan 10 (Forced): Fungsi Menerima `candidates` sebagai Parameter, Tidak Memanggil `retrieve_session_memory()` Sendiri

**Sumber Paksaan:** Preseden pola komposisi yang sudah dipakai konsisten di seluruh proyek — `pecah_atomik()` (M1.6) menerima `klasifikasi` sebagai parameter, tidak memanggil `klasifikasi_kebutuhan()` sendiri; `decompose_question()` menerima `question: str` polos, tidak memanggil `rewrite_to_standalone()` sendiri.

**Keputusan yang Diikuti:** `match_atomic_intents()`/`match_and_archive()` menerima `candidates: list[SessionMemoryPackage]` sebagai parameter biasa — pemanggil (nanti `src/main.py`, belum dirangkai) bertanggung jawab memanggil `retrieve_session_memory()` (atau memberi list kosong kalau Langkah 2/M1.3 bilang `is_dependent=False`) sebelum memanggil fungsi M1.7.

**Opsi yang Dipertimbangkan tapi Ditolak:** M1.7 memanggil `retrieve_session_memory()` secara internal — ditolak, akan menciptakan coupling langsung M1.7→M1.5 yang tidak konsisten dengan pola composability longgar yang sudah dipakai di seluruh pipeline (setiap fungsi layer murni menerima output layer sebelumnya, orkestrasi penuh adalah tanggung jawab terpisah).

---

## Keputusan 11 (Forced): `archive_matched_packages()` Tanpa Span Baru

**Sumber Paksaan:** Preseden Keputusan 6 `milestones/1.5-tarik-session-memory/decisions.md` — `store_session_memory()` sengaja TANPA span (tidak ada baris "store" di kontrak observability manapun); dicatat eksplisit di sana bahwa kalau pemanggil produksi (M1.7 atau M4.5) butuh span sendiri, itu jadi kontrak milik milestone tersebut, bukan otomatis diwariskan.

**Keputusan yang Diikuti:** M1.7, sebagai pemanggil produksi PERTAMA `store_session_memory()`, tetap TIDAK menambah span baru untuk operasi arsip ulang — kontrak observability Langkah 7 (Keputusan 8) sudah mencakup seluruh operasi pencocokan+arsip dalam satu span pembungkus `matching.evaluate`, tidak ada baris kontrak terpisah untuk "archive".

**Opsi yang Dipertimbangkan tapi Ditolak:** Span `matching.archive` terpisah — tidak dipertimbangkan serius, akan menambah instrumentasi di luar yang diminta kontrak (prinsip "jangan menambah fitur di luar yang diminta").

---

## Keputusan 12 (Forced): `decisions.md` sebagai Task Pertama

**Sumber Paksaan:** Preferensi eksplisit user, ditetapkan sejak Milestone 1.4, berlaku seluruh milestone berikutnya.

**Keputusan yang Diikuti:** Dokumen ini ditulis sebagai Task 1, Checkpoint 1 — sebelum kode apa pun.

**Opsi yang Dipertimbangkan tapi Ditolak:** Tidak ada — forced by instruksi eksplisit user.

---

## Keputusan 13 (Forced): Verifikasi Memakai Data Seed Manual, Bukan Pipeline Organik

**Sumber Paksaan:** Kondisi nyata proyek — `session_memory_packages` di Supabase masih kosong (belum ada pemanggil produksi nyata; Execution/M4.5 belum dibangun). Preseden identik M1.5 (Keputusan 4: `store_session_memory()` dibangun sebagai utilitas seed test, bukan cuma pemanggil produksi).

**Keputusan yang Diikuti:** Test/smoke test M1.7 memakai `store_session_memory()` untuk menyuntik data "seakan-akan sudah dieksekusi" secara manual sebelum menguji `match_atomic_intents()`/`match_and_archive()`. Untuk KK3 (rantai turn 7→5→3) khususnya: verifikasi lewat DUA pemanggilan `match_and_archive()` NYATA berantai (simulasi turn 5 merujuk turn 3, lalu turn 7 merujuk turn 5 memakai baris yang BENAR-BENAR ditulis pemanggilan pertama) — bukan dua fixture yang masing-masing dibuat manual terpisah, supaya rantai arsip ulang teruji lewat eksekusi kode sungguhan, bukan simulasi ganda. LLM dan DB tetap panggilan sungguhan di seluruh test; hanya titik masuk data awal yang disimulasikan.

**Catatan Ketergantungan:** Dicatat eksplisit di `report.md` Bagian 5 sebagai keterbatasan verifikasi — disepakati langsung dengan user sebelum plan ditulis, bukan ditemukan diam-diam di tengah implementasi.

**Opsi yang Dipertimbangkan tapi Ditolak:** Menunggu M2-M4 selesai sebelum menguji M1.7 dengan data organik — ditolak (tidak sesuai urutan pengerjaan proyek; PIC 1 tidak menunggu PIC lain, lihat `CLAUDE.md` "Urutan pengerjaan yang disarankan"). Dua fixture independen untuk KK3 (bukan rantai eksekusi nyata) — dipertimbangkan sebagai jalan pintas lebih sederhana, tapi ditolak karena tidak benar-benar membuktikan mekanisme arsip ulang bekerja, hanya membuktikan dua potongan kode terpisah masing-masing "benar" tanpa bukti keduanya benar-benar tersambung.

---

## Daftar Isi Keputusan

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | Mekanisme pencocokan: LLM semantik | A | Plan |
| 2 | Pola verifikasi: satu panggilan + fallback aman | A | Plan |
| 3 | Model: reuse Qwen3-32B | A | Plan |
| 4 | Filter kandidat hanya status=berhasil | A | Checkpoint 4 |
| 5 | Satu panggilan LLM per atomic intent | A | Checkpoint 4 |
| 6 | Tidak ada eksklusivitas antar match | A | Checkpoint 4 |
| 7 | Arsip ulang: atomic_intent_id original dipertahankan | B | Checkpoint 5 |
| 8 | Span wrapper non-LLM + chat bersarang | B | Checkpoint 4 |
| 9 | Struktur kode: matching.py di context_resolution/ | B | Checkpoint 2, 4 |
| 10 | Fungsi menerima candidates sebagai parameter | B | Checkpoint 4, 6 |
| 11 | archive_matched_packages() tanpa span baru | B | Checkpoint 5 |
| 12 | decisions.md sebagai Task pertama | B | Plan |
| 13 | Verifikasi memakai data seed manual | B | Checkpoint 4-9 |
