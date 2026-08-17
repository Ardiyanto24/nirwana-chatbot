# Keterbatasan Diterima — Backlog Project-Wide

Dokumen ini mencatat keterbatasan teknis yang **ditemukan** selama pengerjaan proyek dan **sengaja diterima** (bukan diperbaiki), karena biaya perbaikan tidak sepadan atau di luar kendali tim ini. Lintas milestone — berbeda dari `decisions.md` per-milestone yang isinya keputusan desain, bukan keterbatasan yang ditemukan di tengah jalan.

Format tiap entri: konteks penemuan, kenapa diterima, dampak + mitigasi, dan pemicu peninjauan ulang.

---

## 1. Governance OTel GenAI Semantic Conventions pindah repo, belum ada paket Python resmi di repo baru

**Ditemukan di:** Milestone 1.1, Checkpoint 3, Task 8 (2026-08-14).

**Konteks penemuan:** Saat mengunci versi konvensi atribut `gen_ai.*` (kewajiban eksplisit Milestone 1.1), ditemukan bahwa seluruh konstanta `gen_ai.*` di paket `opentelemetry-semantic-conventions` (versi ter-install: `0.65b0`) sudah ditandai "Deprecated" di docstring, dengan catatan governance spesifikasi GenAI pindah dari repo utama `open-telemetry/semantic-conventions` ke repo terpisah `open-telemetry/semantic-conventions-genai` sejak rilis `semantic-conventions v1.42.0` (2026-06-12). Dikonfirmasi lewat web search + `WebFetch` ke repo baru: per 2026-08-14, repo tersebut **belum punya release/tag resmi maupun paket PyPI generated-code sendiri** untuk konstanta atribut Python. Nilai string atribut yang dipakai proyek ini (`gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.conversation.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) dikonfirmasi **identik** antara paket lama dan dokumentasi repo baru — belum ada rename, hanya perpindahan governance dokumentasi/stabilitas.

**Kenapa diterima (bukan diperbaiki):** Tidak ada alternatif yang lebih baik tersedia saat ini — repo baru belum menerbitkan paket Python apa pun untuk dependency langsung. Menunda Milestone 1.1 sampai repo baru merilis paket resmi bukan pilihan wajar (tidak ada linimasa yang diketahui, dan konvensi ini memang secara eksplisit didesain "pre-stable" oleh OTel sendiri — sesuai catatan di header `rancangan-observability-ai-chatbot.md`).

**Dampak + mitigasi:** Kode proyek (`src/observability/genai_semconv.py`, dipindah dari `infra/observability/` di Milestone 1.2) tetap mengimpor dari `opentelemetry.semconv._incubating.attributes.gen_ai_attributes`, dipin lewat `opentelemetry-semantic-conventions==0.65b0` di `uv.lock`. Dampak: perubahan nama atribut di masa depan (kalau terjadi saat repo baru mulai stabil) tidak akan otomatis tertangkap oleh dependency checker manapun — harus dicek manual. Mitigasi: seluruh konstanta yang dipakai proyek diisolasi lewat satu modul (`genai_semconv.py`), sehingga kalau terjadi perubahan nyata, cukup satu file yang perlu diperbarui, bukan tersebar di seluruh kode 9 layer.

**Pemicu peninjauan ulang:** (a) setiap kali `opentelemetry-semantic-conventions` di-upgrade versi lewat `uv lock --upgrade`, cek ulang apakah modul `gen_ai_attributes` masih ada dan nilainya belum berubah; (b) sebelum Milestone 2.1 (instrumentasi PIC 2 pertama di luar PIC 1) dimulai, cek apakah `open-telemetry/semantic-conventions-genai` sudah merilis paket Python resmi — kalau sudah, evaluasi migrasi; (c) kalau ada breaking rename pada atribut yang dipakai proyek ini di rilis semantic-conventions manapun, revisi `genai_semconv.py` segera dan catat sebagai entri `decisions.md` baru di milestone yang sedang berjalan saat itu.

---

## 2. Payload turn membawa histori sesi penuh — bisa membesar untuk sesi sangat panjang

**Ditemukan di:** Milestone 1.3, Checkpoint 1 (2026-08-14), sebagai konsekuensi langsung revisi kontrak payload (lihat `decisions.md` Milestone 1.3 Keputusan 1).

**Konteks penemuan:** Payload M1.2 direvisi membawa seluruh histori turn dalam sesi (bukan window terbatas) supaya Milestone 1.3 bisa mendeteksi rujukan ke turn manapun dalam sesi, termasuk yang jauh dari turn saat ini. Konsekuensinya: ukuran payload bertambah linear seiring sesi memanjang — tidak ada mekanisme ringkasan, pemangkasan, atau kompresi histori sama sekali di titik ini.

**Kenapa diterima (bukan diperbaiki):** Belum ada bukti nyata bahwa ini jadi masalah operasional (belum ada frontend/traffic sungguhan). Membangun mekanisme ringkas/pangkas sekarang berarti menyelesaikan masalah yang belum terbukti ada, berpotensi menambah kompleksitas yang tidak diperlukan (mis. threshold panjang sesi, strategi ringkasan mana yang dipilih) sebelum ada data nyata soal pola panjang sesi yang sesungguhnya terjadi.

**Dampak + mitigasi:** Sesi yang sangat panjang (puluhan turn) akan mengirim payload besar tiap request, berpotensi memperlambat request atau menyentuh limit ukuran body HTTP/context window LLM di langkah-langkah yang memprosesnya (M1.3 dan seterusnya). Mitigasi saat ini: tidak ada mekanisme aktif — diterima sebagai keterbatasan awal desain.

**Pemicu peninjauan ulang:** (a) begitu ada payload sungguhan dari frontend nyata dengan sesi yang cukup panjang untuk diukur, evaluasi apakah ukuran payload benar-benar jadi masalah; (b) kalau context window model LLM manapun yang dipakai di Context Resolution (M1.3/1.4/1.7) mulai terlampaui oleh histori panjang, revisi mendesak diperlukan (mis. ringkasan histori lama, atau batasi ke N-turn + fallback ke session memory untuk turn yang lebih tua — catatan: opsi terakhir ini butuh Session Memory, M1.5, sudah tersedia).

---

## 3. Recency Bias Model LLM pada Kasus Rujukan Ambigu-Multi-Kandidat

**Ditemukan di:** Milestone 1.3 (`evals/1.3-.../audit.md` S07, 2026-08-15) dan terulang di Milestone 1.4 (`evals/1.4-.../audit.md` S07, 2026-08-15), lintas model (DeepSeek V4 Flash 0731 dan Qwen3-32B) dan lintas tugas (deteksi ketergantungan turn dan rewrite mandiri).

**Konteks penemuan:** Skenario uji dengan dua atau lebih kandidat turn yang topiknya sama-sama defensible untuk dirujuk (mis. "bandingkan dengan bulan sebelumnya" saat ada dua turn occupancy di histori) — pada kedua milestone, model malah salah menangkap turn yang **paling akhir/terdekat secara posisi** meski topiknya sebenarnya tidak koheren untuk dirujuk (mis. topik rekrutmen staff yang cuma py satu data point, tidak punya "bulan sebelumnya" untuk dibandingkan), alih-alih turn yang topiknya benar-benar cocok. Pola berulang persis di dua model dan dua tugas berbeda mengindikasikan ini kemungkinan karakteristik umum LLM pada resolusi rujukan ambigu, bukan kelemahan satu model spesifik.

**Kenapa diterima (bukan diperbaiki):** Baru 2 data point (satu per milestone) — belum cukup bukti untuk merancang mitigasi spesifik (mis. instruksi system prompt tambahan) tanpa risiko overfit ke skenario yang kebetulan sudah diuji. Kedua milestone (M1.3, M1.4) sudah eksplisit menandai model yang dipakai sebagai "untuk testing", bukan klaim final produksi — perbaikan prompt/model idealnya dilakukan sekali dengan model final, bukan berulang tiap kali model testing berganti.

**Dampak + mitigasi:** Pada kasus genuinely ambigu (bukan mayoritas kasus — skenario non-ambigu lain di kedua eval lolos bersih), sistem berisiko meresolusi rujukan ke turn yang salah. Mitigasi saat ini: tidak ada perbaikan prompt aktif; kedua milestone sudah membuktikan mekanisme dasarnya bekerja benar di luar kasus ambigu ini (M1.3: 11/12, M1.4: 11/12 skenario benar).

---

### Tambahan (Milestone 1.7, 2026-08-15): Distractor Confusion + Non-Determinisme `temperature=0`

**Ditemukan di:** Milestone 1.7 (`evals/1.7-pencocokan-atomic-intent/audit.md` S09, 2026-08-15) — mekanisme berbeda (`match_atomic_intents()`, LLM semantik satu-panggilan-per-item, Qwen3-32B) dari dua data point sebelumnya (deteksi ketergantungan turn M1.3, rewrite mandiri M1.4).

**Konteks penemuan:** Skenario uji dengan 3 kandidat — 1 BENAR secara makna (index 1), 1 pengisi topik lain (index 2), 1 SALAH bulan tapi topik sama persis dan di posisi PALING AKHIR (index 3). Run pertama: model memilih index 1 dengan benar (tidak terjadi recency bias klasik). Run KEDUA (prompt+kandidat identik persis, `temperature=0`): model gagal mencocokkan SAMA SEKALI (`perlu_eksekusi`), bahkan terhadap kandidat index 1 yang objektif tidak ambigu — BUKAN salah pilih ke index 3 (arah aman, bukan false-positive). Ini menunjukkan dua hal: (a) `temperature=0` TIDAK menjamin determinisme penuh untuk `qwen/qwen3-32b` via OpenRouter; (b) mode kegagalan lebih halus dari sekadar "pilih yang posisinya paling akhir" — kehadiran distractor topikal (bukan cuma posisi) bisa memicu ketidakpastian model bahkan pada kasus yang seharusnya jelas.

**Kenapa diterima (bukan diperbaiki):** Sama seperti entri asli — baru 1 data point tambahan (3 total lintas M1.3/M1.4/M1.7). Fallback M1.7 sendiri sudah aman-by-design (Keputusan 2 `milestones/1.7-.../decisions.md`: prompt konservatif + fallback `perlu_eksekusi`), jadi dampak langsungnya rendah (efisiensi berkurang, bukan korektnes).

**Dampak + mitigasi:** Sama seperti dampak asli, plus: debugging/re-run eval TIDAK selalu bisa mengasumsikan hasil identik meski `temperature=0` — relevan untuk seluruh milestone LLM proyek (M1.3, M1.4, M1.6 juga memakai `temperature=0`). Mitigasi saat ini: tidak ada perubahan prompt/kebijakan; M1.7 sudah gagal ke arah aman di kedua kasus (recency M1.3/M1.4 dan distractor confusion M1.7).

**Pemicu peninjauan ulang tambahan:** Kalau pola non-determinisme `temperature=0` terbukti memengaruhi Kriteria Keberhasilan formal manapun (bukan cuma eval eksploratif), revisi mendesak diperlukan (mis. beberapa kali sampling + majority vote, atau terima non-determinisme sebagai sifat sistem dan desain ulang test agar toleran terhadapnya).

---

## 4. Taksonomi `label_bentuk_jawaban` (5 Nilai) Punya Gap untuk Kebutuhan Deskriptif/Multi-Nilai

**Ditemukan di:** Milestone 1.6 (`evals/1.6-decomposition/audit.md` S05, S07, 2026-08-15).

**Konteks penemuan:** `label_bentuk_jawaban` (`nilai_tunggal`/`tren`/`perbandingan`/`peringkat`/`komposisi`) dikunci `arsitektur-ai-chatbot-rbac.md` §7 sebagai kontrak bersama PIC 1 (Decomposition, Session Memory) dan PIC 4 (Execution/Interpretation). Eval Milestone 1.6 menemukan dua kelas kebutuhan yang tidak punya label cocok di antara kelima nilai itu: (a) pertanyaan deskriptif/naratif terbuka (skenario uji: "Bagaimana performa Front Office bulan ini?" — Verifikasi independen menolak `nilai_tunggal` karena "mengharapkan deskripsi atau ringkasan, bukan nilai tunggal", tidak ada label lain yang cocok); (b) kebutuhan pendukung multi-nilai yang jadi input untuk `tren` (skenario uji: "occupancy rate tiap bulan dalam 6 bulan terakhir" sebagai prasyarat sebelum menghitung trennya — Verifikasi eksplisit menyarankan label "nilai_berganda" atau "deret_waktu", KEDUANYA tidak ada dalam taksonomi 5-nilai). Di kedua kasus, Pemecahan (Qwen3-32B) memilih `nilai_tunggal` sebagai pendekatan terdekat yang tersedia, tapi Verifikasi independen (DeepSeek V4 Pro) konsisten menolaknya di seluruh 3 percobaan retry — bukan kesalahan Pemecahan, murni keterbatasan pilihan yang tersedia.

**Kenapa diterima (bukan diperbaiki):** `label_bentuk_jawaban` adalah kontrak bersama PIC 1/PIC 4 yang dikunci dokumen arsitektur — Milestone 1.6 (atau agen mana pun yang mengerjakannya sendirian) tidak berwenang mengubahnya sepihak (`CLAUDE.md` Prinsip Arsitektur eksplisit: "perubahan wajib disepakati kedua pemilik"). Baru 2 data point dari 1 milestone — perlu dikonfirmasi dulu apakah PIC 4 (konsumen berikutnya, mulai Milestone 4.5) juga menemukan gap yang sama sebelum mengajukan perubahan taksonomi bersama.

**Dampak + mitigasi:** Kebutuhan atomik dengan bentuk jawaban deskriptif/multi-nilai akan terus gagal verifikasi (retry exhausted) di Milestone 1.6 sampai taksonomi direvisi atau `_SYSTEM_PROMPT` Pemecahan/Verifikasi disesuaikan untuk menerima `nilai_tunggal` sebagai pendekatan yang cukup pada kasus ini. Mitigasi saat ini: tidak ada — `verifikasi_valid=False` yang exhausted tetap diteruskan apa adanya ke pemanggil (Milestone 1.7), jujur soal keterbatasannya, tidak disamarkan.

**Pemicu peninjauan ulang:** (a) sebelum Milestone 4.5 (Execution/Interpretation, konsumen `label_bentuk_jawaban` berikutnya untuk penyusunan visualisasi) mulai — cek apakah gap yang sama relevan untuk kebutuhan visualisasi; (b) kalau eval milestone LLM berikutnya yang juga memakai `label_bentuk_jawaban` menemukan pola gap serupa, ajukan revisi taksonomi ke pemilik kontrak (bukan diputuskan sepihak satu milestone).

---

## 5. Mekanisme Retry-dengan-Feedback (Milestone 1.6) Belum Menunjukkan Bukti Perbaikan

**Ditemukan di:** Milestone 1.6 (`evals/1.6-decomposition/audit.md`, 2026-08-15).

**Konteks penemuan:** `decompose_question()` retry Pemecahan+Verifikasi maksimal 3 kali kalau Verifikasi menilai hasil invalid, dengan alasan invalid disisipkan sebagai feedback ke percobaan berikutnya (Keputusan 3, keputusan eksplisit user). Eval 14 skenario menemukan: di SELURUH 13 skenario yang menjalankan `decompose_question()`, `retry_count` cuma bernilai 0 (langsung benar di percobaan pertama, 8 skenario) atau tepat 2/exhausted (gagal di ketiga percobaan tanpa perbaikan sama sekali, 5 skenario) — TIDAK ADA satu pun kasus yang membaik di percobaan kedua meski feedback alasan invalid disisipkan eksplisit ke prompt retry.

**Kenapa diterima (bukan diperbaiki):** Baru 5 data point kegagalan dari 1 milestone — belum cukup untuk menyimpulkan mekanisme retry genuinely tidak berguna (bisa jadi kebetulan kelima kasus itu representasi masalah yang butuh perubahan struktural, bukan sekadar penjelasan ulang, sehingga feedback prosa tidak cukup). Kebijakan retry adalah keputusan eksplisit user yang baru saja diputuskan (`milestones/1.6-decomposition/decisions.md` Keputusan 3) — mengubahnya sekarang berdasar 5 data point berisiko premature.

**Dampak + mitigasi:** Setiap kasus yang gagal verifikasi di percobaan pertama kemungkinan besar akan tetap gagal setelah 2 retry (menghabiskan token 3x lipat tanpa manfaat nyata yang teramati) — biaya tanpa hasil untuk kelas kegagalan tertentu. Mitigasi saat ini: tidak ada perubahan kebijakan; hasil akhir tetap jujur (tidak disamarkan) apa pun hasilnya.

**Pemicu peninjauan ulang:** Kalau milestone LLM berikutnya yang juga punya mekanisme retry serupa menemukan pola sama (retry tidak pernah membaik di tengah), pertimbangkan bersama user: (a) redesign feedback jadi lebih terstruktur/actionable (bukan cuma prosa alasan), atau (b) evaluasi ulang apakah retry benar-benar menambah nilai dibanding flag-and-pass-through (opsi yang sebelumnya ditolak user di M1.6).

**Pemicu peninjauan ulang:** (a) sebelum Milestone 1.6 (Decomposition)/1.7 (Pencocokan) mulai — keduanya juga berurusan dengan resolusi/pencocokan rujukan, evaluasi apakah pola ini relevan untuk desain mekanismenya; (b) kalau model produksi final (menggantikan model testing M1.3/M1.4) menunjukkan pola sama di eval ulang, pertimbangkan penguatan system prompt eksplisit ("abaikan kedekatan posisi, fokus ke topik yang benar-benar cocok untuk dibandingkan") sebagai mitigasi lintas-langkah.

---

## 6. Verifikasi Titik Buta (Milestone 2.1) Cenderung Over-Triggering pada Kata Bertema Finansial/Temporal

**Ditemukan di:** Milestone 2.1 (`evals/2.1-identifikasi-domain/audit.md` S04, S08, 2026-08-15; direplikasi dari temuan awal `milestones/2.1-identifikasi-domain/logs.md` Checkpoint 8).

**Konteks penemuan:** `verifikasi_titik_buta()` (DeepSeek V4 Pro, `reasoning="high"`) secara konsisten menambahkan domain yang tidak jelas dasarnya untuk pertanyaan yang mengandung kata bertema finansial/temporal dalam konteks domain lain — direplikasi 2x identik untuk skenario "Berapa nationality mix tamu bulan ini?" (menambahkan `reservation` di Checkpoint 8 DAN di eval S04, `guests_profile` sendiri sudah benar tanpa bantuan Langkah 2), dan pola serupa di S08 ("Bandingkan revenue F&B dengan tingkat okupansi kamar bulan ini" — menambahkan `financial` di luar `fnb`+`reservation` yang sudah eksplisit disebut). Sebaliknya, 6 dari 10 skenario eval M2.1 lain (baseline `financial`/`hr` murni, domain minor `properties_ref`, jebakan payroll) menghasilkan domain BERSIH tanpa tambahan apa pun — pola ini TIDAK universal, tampak terkonsentrasi pada kombinasi kata tertentu ("revenue", "bulan ini", metrik finansial) dalam konteks domain non-`financial`/non-`reservation`.

**Kenapa diterima (bukan diperbaiki):** Ini adalah trade-off yang SENGAJA dipilih arsitektur M2.1 (`decisions.md` Keputusan 9) — risiko M2.1 asimetris ke arah SEBALIKNYA dari M1.7: domain yang TERLEWAT (false negative) berpotensi kebocoran RBAC di Milestone 2.2 (domain tak terdeteksi = tak diperiksa otorisasinya), sementara domain BERLEBIH (false positive) hanya berisiko penolakan otorisasi yang tidak perlu (gangguan UX, bukan kebocoran keamanan). Verifikasi titik buta condong ke arah lebih inklusif adalah konsekuensi wajar dari desain yang sengaja mengutamakan tidak-terlewat — baru 2-3 data point konsisten, belum cukup untuk mitigasi prompt spesifik tanpa risiko overfit ke kasus yang kebetulan sudah teruji.

**Dampak + mitigasi:** Milestone 2.2 (Pemeriksaan Otorisasi) berpotensi memeriksa/menolak akses ke domain yang sebenarnya tidak esensial bagi kebutuhan sesungguhnya (mis. `reservation` untuk pertanyaan demografis tamu murni) — kalau role pemanggil kebetulan tidak py akses `reservation` tapi py akses `guests_profile`, permintaan bisa ditolak keliru meski data yang benar-benar dibutuhkan (guests_profile) sebenarnya diizinkan. Mitigasi saat ini: tidak ada perubahan prompt/kebijakan — dicatat eksplisit sebagai konteks desain yang perlu disadari M2.2 saat merancang UX pesan penolakan (mis. mempertimbangkan penolakan parsial per-domain, bukan blanket-reject seluruh permintaan).

**Pemicu peninjauan ulang:** (a) kalau Milestone 2.2 menemukan pola penolakan yang mencurigakan sering terjadi karena domain "berlebih" dari M2.1 (bukan domain yang genuinely diminta), evaluasi bersama apakah prompt verifikasi titik buta perlu diperketat; (b) kalau eval milestone berikutnya (2.2/2.3) menemukan pola serupa dengan kata kunci tema lain (bukan cuma finansial/temporal), pertimbangkan revisi `CATATAN_POLA_JEBAKAN` untuk eksplisit menekankan "hanya tambahkan domain yang BENAR-BENAR dibutuhkan untuk menjawab, bukan yang sekadar berkaitan secara konseptual".

---

## 7. Panggilan LLM via `get_openrouter_client()` Kadang Hang Berkepanjangan Tanpa Exception (Root Cause Tidak Teridentifikasi Penuh)

**Ditemukan di:** Milestone 2.1, Checkpoint 10 (`milestones/2.1-identifikasi-domain/logs.md`, 2026-08-15), saat eksekusi eval.

**Konteks penemuan:** Beberapa kali eksekusi `evals/2.1-identifikasi-domain/run_eval.py` mengalami hang tanpa exception apa pun — proses tetap hidup (`Responding=True`, CPU nyaris nol, konsisten pola I/O-bound blocking) tapi tidak selesai selama puluhan menit, jauh melebihi latensi normal (14-38 detik, teramati konsisten di Checkpoint 5-8). Terjadi tidak konsisten (kadang skenario ke-2 dalam satu proses panjang, kadang skenario tunggal terisolasi). Upaya isolasi menyeluruh (panggilan mentah `_call_llm()` terpisah, fungsi wrapped `identifikasi_domain()`/`verifikasi_titik_buta()` terpisah, bahkan `curl` langsung ke endpoint `chat/completions`) SEMUANYA terbukti cepat dan normal saat diuji sendiri-sendiri — root cause pasti (connection pooling, provider-side queueing, atau lapisan lain) TIDAK berhasil diisolasi dalam waktu wajar.

**Kenapa diterima (bukan diperbaiki dengan solusi definitif):** Mengingat komponen individual semuanya terbukti bekerja normal saat diuji terisolasi, kemungkinan besar ini karakteristik infrastruktur (provider OpenRouter/jaringan lokal) di luar kendali langsung kode proyek, bukan bug logic yang bisa diperbaiki dengan mengubah kode `src/`. Menginvestigasi lebih dalam (mis. packet capture, debugging level TCP) berada di luar cakupan wajar satu milestone LLM.

**Dampak + mitigasi:** Eksekusi eval/testing yang melibatkan banyak panggilan LLM berurutan berisiko memakan waktu jauh lebih lama dari perkiraan wajar, kadang perlu diulang manual per-skenario. Mitigasi yang diterapkan: `get_openrouter_client()` (`src/config/llm.py`) diberi `timeout=90.0, max_retries=1` eksplisit (sebelumnya tanpa timeout eksplisit sama sekali) — batas atas ~180s terburuk per panggilan, jatuh ke jalur fallback aman (`gagal=True`) yang sudah ada di tiap layer, bukan hang tanpa batas. Berlaku untuk SELURUH konsumen fungsi ini (M1.3-M1.7 turut terdampak positif).

**Pemicu peninjauan ulang:** (a) kalau pola hang ini terulang di milestone LLM berikutnya (2.2 dst.) meski sudah ada timeout eksplisit, investigasi lebih dalam layak dilakukan (mis. cek versi library `httpx`/`openai`, environment jaringan spesifik); (b) kalau timeout 90s terbukti terlalu pendek untuk model reasoning berat (`reasoning="high"`) yang genuinely butuh waktu lebih lama secara sah, sesuaikan nilai timeout berdasar data nyata durasi maksimum yang legitimate (bukan menaikkan tanpa dasar).

---

## 8. Salinan Matriks `role_permissions` (Milestone 2.2) Berpotensi Drift dari Produksi

**Ditemukan di:** Milestone 2.2 (`milestones/2.2-pemeriksaan-otorisasi/decisions.md` Keputusan 1 dan 10, `report.md` Bagian 5, 2026-08-15) — konsekuensi langsung dari keputusan arsitektur, bukan bug yang ditemukan mid-implementation.

**Konteks penemuan:** M2.2 (Lapis 1) tidak boleh dan tidak bisa query tabel produksi `mart_cleaned.role_permissions` secara langsung — kredensial `chatbot_authz_reader` untuk tabel itu eksklusif milik Milestone 4.4 (Lapis 2, `api-chatbot.md` baris 29-30), di luar cakupan proyek ini. Sebagai gantinya, M2.2 menyimpan SALINAN matriks 20 role × 10 domain di tabel `role_permissions` milik project Supabase-nya sendiri, diseed sekali secara manual (`seed_role_permissions.py`) dari transkripsi `rancangan-rbac-ai-chatbot.md` Bagian 2. Tidak ada mekanisme sinkronisasi otomatis antara salinan ini dan tabel produksi maupun dokumen sumbernya.

**Kenapa diterima (bukan diperbaiki):** Membangun mekanisme sinkronisasi otomatis akan butuh akses ke database produksi yang memang sengaja tidak diberikan ke Lapis 1 (segregasi kredensial per pola akses adalah prinsip arsitektur yang disengaja, bukan kelalaian) — solusi "benar" (akses live ke produksi) bertentangan langsung dengan batasan yang sudah dikunci. Alternatif seperti webhook/polling ke tim database engineering di luar kendali dan cakupan proyek portofolio solo ini.

**Dampak + mitigasi:** Kalau tim database engineering merevisi `role_permissions` produksi (menambah role baru, mengubah izin domain suatu role) TANPA proyek ini diberi tahu, salinan Lapis-1 akan menjadi stale — berpotensi menghasilkan keputusan otorisasi Lapis 1 yang berbeda dari Lapis 2 (`chatbot_api`) yang sesungguhnya menegakkan akses. Dampak keamanan riil RENDAH karena Lapis 2 tetap independen menegakkan otorisasi sesungguhnya (defense in depth — `CLAUDE.md` prinsip "AI hanya penulis rencana, bukan pengeksekusi langsung") — staleness Lapis 1 paling buruk menghasilkan penolakan dini yang keliru (UX terganggu) atau body request yang ditolak ulang oleh Lapis 2 (403), BUKAN kebocoran data (Lapis 2 tetap jadi penjaga akhir). Mitigasi saat ini: tidak ada sinkronisasi otomatis — `seed_role_permissions.py` perlu dijalankan ulang manual kalau `rancangan-rbac-ai-chatbot.md` direvisi.

**Pemicu peninjauan ulang:** (a) setiap kali `rancangan-rbac-ai-chatbot.md` Bagian 2 direvisi oleh tim database engineering, jalankan ulang `seed_role_permissions.py` (perlu proses notifikasi manual — belum ada mekanisme otomatis untuk tahu kapan dokumen sumber berubah); (b) kalau proyek ini nanti mendapat akses read-only resmi ke `mart_cleaned.role_permissions` produksi (di luar cakupan M2.2 saat ini), evaluasi migrasi ke sinkronisasi otomatis (mis. scheduled job) alih-alih seed manual.

---

## 9. Daftar 9 View Kategori "Performa Individu" (Milestone 2.3) Berpotensi Tidak Lengkap Kalau Katalog Data Direvisi

**Ditemukan di:** Milestone 2.3 (`milestones/2.3-deteksi-cakupan-individu/decisions.md` Keputusan 1, 2026-08-16) — konsekuensi langsung dari keputusan desain, bukan bug yang ditemukan mid-implementation. Pola identik entri #8 (M2.2), diterapkan ke jenis data berbeda (daftar view grounding prompt, bukan matriks otorisasi).

**Konteks penemuan:** Daftar 9 view kategori "performa individu staf" (4 `facility` + 5 `hr`) yang dipakai sebagai grounding kedua prompt LLM M2.3 (`konteks_cakupan_individu.py`) disusun lewat tinjauan manual langsung ke `docs/03-domain-source/katalog-data-chatbot.md` (67 view) pada satu titik waktu (2026-08-16), dikonfirmasi user. Tidak ada mekanisme yang mendeteksi otomatis kalau tim database engineering menambah view baru dengan pola sensitivitas serupa (grain per-individu + metrik kerja/kehadiran) di masa depan, atau mengubah salah satu dari 9 view yang sudah terdaftar.

**Kenapa diterima (bukan diperbaiki):** Katalog data (`docs/03-domain-source/`) adalah dokumen sumber kebenaran domain yang sudah final dan diverifikasi tim database engineering — bukan cakupan yang direvisi proyek ini (`CLAUDE.md` eksplisit). Membangun mekanisme deteksi otomatis "view baru dengan pola sensitivitas ini" akan butuh akses/analisis berkelanjutan ke skema database produksi yang di luar cakupan Lapis 1, dan berisiko over-engineering untuk kebutuhan yang belum terbukti berulang (katalog 67 view relatif stabil, revisi besar tidak terjadi tiap milestone).

**Dampak + mitigasi:** Kalau view baru dengan pola performa-individu ditambahkan ke domain `facility`/`hr` (atau domain lain) tanpa daftar ini diperbarui, kebutuhan yang menyentuh view baru itu berisiko TIDAK terdeteksi (`terdeteksi=False` keliru) — gap yang sama persis dengan yang coba ditutup Milestone 2.3 sendiri terhadap gap Lapis 2. Dampak sebagian dimitigasi oleh sifat LLM generate-verify: kedua prompt (`deteksi_cakupan_individu.md`/`verifikasi_cakupan_individu.md`) memberi contoh 9 view SEBAGAI ILUSTRASI pola ("data granular per-staf/karyawan tertentu di domain facility/hr", bukan daftar tertutup harfiah) — S05 evals (`evals/2.3-.../audit.md`) sudah membuktikan generalisasi ke kasus yang tidak eksplisit di daftar 9 view. Risiko residual: view baru di domain SELAIN `facility`/`hr` tidak akan pernah diperiksa sama sekali karena pre-filter domain (Keputusan 5) memblokir panggilan LLM sebelum sempat menilai teksnya.

**Pemicu peninjauan ulang:** (a) setiap kali `katalog-data-chatbot.md` direvisi tim database engineering (view baru ditambahkan/dihapus), tinjau ulang apakah ada view baru berpola performa-individu, perbarui `konteks_cakupan_individu.py` kalau perlu; (b) kalau ada bukti nyata (mis. dari eval/prompt_reliability berkelanjutan) bahwa domain di luar `facility`/`hr` py view berpola sama, revisi pre-filter domain (Keputusan 5) untuk memasukkan domain itu.

---

## 10. Konvensi Filter Cakupan-Individu `employee_id` (Milestone 2.4) Belum Dikonfirmasi Tim Database Engineering — RISIKO TINGGI

**Ditemukan di:** Milestone 2.4 (`milestones/2.4-verification-gate/decisions.md` Keputusan 1, 2026-08-16), lewat riset kontrak (agent Explore) sebelum plan ditulis, dikonfirmasi lewat dua putaran `AskUserQuestion` dengan user.

**Konteks penemuan:** `docs/01-architecture/arsitektur-ai-chatbot-rbac.md` Bagian 8 item 5 eksplisit menandai "Skema parameter per `view_name`" sebagai masih terbuka. `docs/03-domain-source/api-chatbot.md` **tidak mendokumentasikan parameter apa pun** untuk membatasi hasil ke data milik individu pemanggil sendiri — satu-satunya ID individu di kontrak (`employee_id`) HANYA dipakai untuk resolusi `property_id` (level properti), bukan filter baris. Contoh `staff_id=self` di dokumen arsitektur (baris 187) murni ilustrasi prosa, bukan parameter terkontrak. M2.4 (`tegakkan_constraint_cakupan_individu()`, `src/layers/verification_gate/verifikasi_gate.py`) tetap menimpa paksa `params["employee_id"]` dengan `employee_id` caller sebagai satu-satunya opsi yang tersedia dari kontrak resmi — dikonfirmasi user sebagai konvensi provisional, BUKAN diasumsikan pasti benar.

**Kenapa diterima (bukan diperbaiki):** Tidak ada mekanisme untuk memverifikasi perilaku server-side `chatbot_api` dari dalam proyek ini — `chatbot_api` sudah final dan di luar cakupan revisi (`CLAUDE.md` eksplisit), file `whitelist_<domain>.py` yang mungkin mendefinisikan parameter sebenarnya tidak ada di repo ini (kode sepenuhnya eksternal). Menunda M2.4 sampai konfirmasi resmi tersedia bukan pilihan yang diambil user — user memilih lanjut dengan konvensi terbaik yang tersedia, didokumentasikan jujur sebagai provisional.

**Dampak + mitigasi:** **RISIKO LEBIH TINGGI dari entri #8/#9** — kalau `chatbot_api` genuinely TIDAK menerapkan filter baris berdasarkan `employee_id` untuk 9 view performa-individu (M2.3), maka seluruh mekanisme cek 3-4 M2.4 (`tegakkan_constraint_cakupan_individu()`/`verifikasi_kelengkapan_penegakan()`) tidak benar-benar melindungi apa pun — parameter terkirim tapi diabaikan server-side, constraint cakupan-individu M2.3 jadi TIDAK ditegakkan secara substantif meski secara struktural (request) terlihat benar. Ini BUKAN kebocoran data yang tidak diketahui — `error.type=gagal_teknis`/`verification.check_name` tetap tercatat benar di observability, tapi keefektifan RIIL filter tidak bisa dibuktikan dari dalam proyek ini. Mitigasi saat ini: tidak ada verifikasi independen ke perilaku `chatbot_api` — murni menerapkan konvensi terbaik yang tersedia dari kontrak resmi.

**Pemicu peninjauan ulang:** (a) SEGERA begitu ada akses/dokumentasi resmi ke perilaku `chatbot_api` per-view (mis. `whitelist_<domain>.py` tersedia untuk ditinjau, atau konfirmasi langsung tim database engineering) — verifikasi ulang apakah `employee_id` benar-benar diterapkan sebagai filter baris untuk 9 view performa-individu; (b) kalau ternyata TIDAK, revisi mendesak diperlukan sebelum M2.4 dianggap benar-benar menegakkan constraint cakupan-individu (kandidat: parameter lain yang benar, atau eskalasi kebutuhan penambahan parameter baru ke tim database engineering); (c) sebelum Milestone 4.x (Execution) mengirim request nyata ke `chatbot_api` produksi, ini WAJIB diverifikasi — bukan asumsi yang boleh dibawa tanpa konfirmasi ke tahap produksi.

---

## 11. Pencarian BM25 (M3.1) Tetap Gagal Menemukan Kandidat Tanpa Overlap Kata Bermakna Sama Sekali, Bahkan Setelah Stopword Filtering

**Ditemukan di:** Milestone 3.1 (Checkpoint 7-9, `evals/3.1-pengumpulan-kandidat-view/audit.md` skenario B1, 2026-08-17).

**Konteks penemuan:** Eval perbandingan model embedding (Checkpoint 7) menemukan bug lebih mendasar terlebih dahulu: tokenizer `pencarian_bm25.py` (Checkpoint 5) tanpa stopword filtering membuat trigger `perlu_fallback` nyaris tidak pernah aktif (kata fungsi umum "yang"/"dan"/"di" muncul di hampir seluruh 67 teks korpus, membuat skor BM25 selalu positif untuk query apa pun). Diperbaiki Checkpoint 9 dengan menambah stopword filtering (`_STOPWORDS_ID`). Setelah perbaikan, diverifikasi ulang: 4 dari 5 skenario stress-test (B2-B5) langsung membaik (trigger bekerja sesuai desain atau recall tetap terjaga BM25 murni). **Skenario B1 ("tamu-tamu ini pesannya lewat mana aja...", target `v_reservation_channel_daily`, tema "kanal booking") TETAP tidak ditemukan BM25 bahkan pasca-perbaikan** — query dan teks Fungsi target genuinely tidak berbagi SATU KATA BERMAKNA pun (paraphrase penuh: "kanal"→"lewat mana", "OTA/Direct"→"aplikasi pihak ketiga"). BM25 murni tidak punya mekanisme mengenali kesamaan makna tanpa kesamaan kata — ini bukan bug tokenizer, melainkan batas struktural metode leksikal.

**Kenapa diterima (bukan diperbaiki lebih lanjut):** Trigger fallback saat ini (`perlu_fallback = 0 kandidat ditemukan`) TIDAK aktif untuk kasus B1 karena BM25 tetap menemukan 5 kandidat LAIN (salah, tapi bukan nol) di domain yang sama — memperbaiki ini butuh redesain trigger yang lebih fundamental (mis. selalu memanggil embedding sebagai pelengkap, bukan cuma fallback kondisional) yang mengubah arsitektur Hybrid yang sudah disetujui user, atau kalibrasi threshold berbasis skor absolut yang butuh jauh lebih banyak data eval daripada 5 skenario buatan tangan untuk tidak asal tebak. Kedua opsi di luar cakupan revisi "threshold berbasis bukti" yang disepakati Checkpoint 9.

**Dampak + mitigasi:** Kebutuhan dengan paraphrase yang SANGAT jauh dari kosakata katalog (sinonim total, tanpa kata bermakna yang sama) berisiko tidak masuk kandidat BM25 SAMA SEKALI dan tidak memicu fallback embedding — potensi pelanggaran KK1 sumber ("tidak terlewat karena pencarian terlalu sempit") untuk sub-kelas kasus ini. Mitigasi sebagian: model embedding (Checkpoint 8, `text-embedding-3-small`) TERBUKTI bisa menemukan kasus ini dengan baik (B1 recall=True, rank 2) KALAU dipanggil — masalahnya murni di trigger, bukan kapabilitas fallback itu sendiri.

**Pemicu peninjauan ulang:** (a) M3.2 atau tahap produksi menunjukkan pola kegagalan recall nyata yang match pola B1 (paraphrase jauh tanpa overlap kata) — kumpulkan skenario nyata tambahan sebagai basis kalibrasi ulang; (b) pertimbangkan desain trigger alternatif (skor absolut, atau "selalu panggil kedua jalur lalu union" mengorbankan sebagian efisiensi demi recall) sebagai bagian revisi arsitektur M3.2/3.3 kalau data mendukung; (c) terkait `docs/keputusan-tertunda.md` #2 (model embedding provisional) — kalau trigger direvisi jadi lebih sering aktif, volume pemakaian model embedding berubah, layak dievaluasi bersamaan.
