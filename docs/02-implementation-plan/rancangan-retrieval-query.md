# Rancangan Implementasi — Data Retrieval & Query Engine

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Data Retrieval & Query) |
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` (Bagian 3, 5), `rancangan-observability-ai-chatbot.md` (Bagian 2) |
| **Dokumen rujukan kebutuhan** | `katalog-data-chatbot.md` (definisi 67 view: grain, sumber, kolom turunan, catatan lintas-domain), `api-chatbot.md` (kontrak parameter per domain, whitelist per view) |
| **Cakupan pekerjaan** | Retriever (pengumpulan kandidat, pemeriksaan kecocokan makna, pemeriksaan kecukupan struktural) dan Query Engine (penyusunan request, verifikasi bentuk request) |
| **Tidak termasuk** | Keputusan otorisasi domain dan constraint cakupan-individu (lihat `rancangan-rbac-authorization.md` — pekerjaan ini menerima hasilnya sebagai input, tidak membuat keputusan izin/tolak sendiri); pemanggilan `chatbot_api` yang sesungguhnya dan penanganan responsnya (lihat `rancangan-execution-interpretation.md`); perubahan pada definisi 67 view itu sendiri (sudah final, ditetapkan tim database engineering, di luar kendali pekerjaan ini) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic. Setiap milestone mencakup satu lingkup kerja koheren — kalau dipecah lebih jauh ke task teknis, seluruh pecahan itu tetap berada dalam lingkup yang sama. Milestone tidak menentukan tech stack, library, atau arsitektur detail secara spesifik — itu keputusan yang sengaja diserahkan ke saat pengerjaan nyata berlangsung.

Kecuali untuk hal yang sudah dikunci eksplisit di dua dokumen induk. Yang paling mengikat untuk pekerjaan ini: bentuk keluaran akhir Query Engine wajib `{domain, view_name, params}` — bukan SQL — karena `chatbot_api` hanya menerima permintaan dalam bentuk ini; dan prinsip "ruang kesalahan tertutup vs terbuka" yang menjelaskan kenapa langkah verifikasi bentuk request di Query Engine tetap memakai model AI meski tugasnya kelihatan sempit (lihat penjelasan di Milestone 3.5).

Urutan milestone adalah urutan yang disarankan, bukan kaku.

---

## Konteks: Kenapa Pekerjaan Ini Tidak Menulis SQL

Serving layer sistem ini berbentuk 67 view yang sudah pre-agregat dan pre-joined, diakses lewat `GET /chatbot/{domain}/{view_name}` — bukan koneksi database langsung. Seluruh kerumitan penggabungan tabel dan perhitungan metrik bisnis (mis. `revpar`, `occupancy_rate`, `gop_margin`) sudah "dibekukan" di dalam definisi view itu sendiri sejak proses reverse ETL, jauh sebelum permintaan apa pun datang. Karena itu, pekerjaan pemilihan data di sini bukan soal menyusun logika query yang kompleks, melainkan dua hal yang jauh lebih sempit: memilih `view_name` yang tepat dari 67 pilihan yang sudah tersedia, lalu mengisi parameter filter yang memang disediakan `chatbot_api` untuk view tersebut (rentang tanggal, kode properti, dan sejenisnya).

---

## Milestone 3.1 — Membangun Pengumpulan Kandidat View

### Lingkup
Membangun mekanisme pencarian yang, dari satu kebutuhan atomik beserta daftar domain yang sudah diizinkan (hasil Domain Gate), mengumpulkan kandidat `view_name` yang mungkin relevan — sengaja dikumpulkan secara luas dulu di tahap ini, bukan langsung memutuskan satu pilihan final. Pencarian ini murni mekanisme pencocokan (bukan generasi model AI), memanfaatkan deskripsi fungsi bisnis yang sudah tertulis eksplisit untuk tiap-tiap 67 view di katalog data — jauh lebih mudah dicari secara semantik dibanding mencari di antara nama-nama kolom individual yang pendek dan ambigu seperti pada rancangan sebelumnya.

### Kenapa Ini Jadi Milestone Terpisah
Mengumpulkan kandidat secara luas terlebih dulu, sebelum menyempit ke satu pilihan, mengurangi risiko terpaku pada pilihan pertama yang kelihatan cocok padahal ada pilihan lain yang lebih tepat — pola yang sama dipertahankan dari rancangan L4 semula meski unit pencariannya sudah berubah dari kolom individual menjadi view.

### Output
Mekanisme pencarian (index atau bentuk pencocokan semantik lain terhadap 67 deskripsi view) yang menerima teks kebutuhan atomik dan domain yang diizinkan, mengembalikan daftar kandidat `view_name` yang mungkin relevan, tanpa memutuskan satu pilihan final. Bentuk teknis pencarian (embedding, keyword matching, atau pendekatan lain) adalah keputusan implementasi bebas. Span pencarian non-LLM ter-emit sesuai kontrak observability, dengan atribut `retrieval.candidates_count` mencatat jumlah kandidat yang ditemukan.

### Kriteria Keberhasilan
- Kebutuhan yang jelas cocok dengan satu atau beberapa view tertentu (skenario uji: "okupansi Bali bulan ini") menghasilkan kandidat yang mencakup view yang benar, tidak terlewat karena pencarian terlalu sempit.
- Kandidat yang dikembalikan terbatas pada domain yang sudah diizinkan Domain Gate — tidak ada kandidat dari domain yang seharusnya ditolak yang ikut lolos ke tahap berikutnya.

---

## Milestone 3.2 — Membangun Pemeriksaan Kecocokan Makna

### Lingkup
Membangun mekanisme yang menilai kandidat hasil Milestone 3.1 satu per satu terhadap definisi lengkapnya di katalog — bukan hanya nama view, melainkan grain, sumber data, dan catatan jebakan yang eksplisit tertulis (misalnya kolom yang di-*join* dari tabel lain, bukan native ke view tersebut). Hasil penilaian untuk tiap kandidat berupa salah satu dari tiga label: ditemukan, sebagian, atau tidak ditemukan — sesuai pola yang sama dengan rancangan sebelumnya, hanya sekarang jenis jebakan yang perlu diwaspadai bergeser dari "nama kolom sama tapi makna beda antar tabel" menjadi "view yang kelihatan cocok tapi grain-nya berbeda dari yang dibutuhkan".

### Kenapa Ini Jadi Milestone Terpisah
Pengumpulan kandidat secara luas (Milestone 3.1) dan penilaian kecocokan mendalam (di sini) adalah dua tugas dengan sifat berbeda — satu soal cakupan yang luas, satu soal ketelitian terhadap detail definisi. Memisahkannya menjaga agar penilaian yang teliti tidak terburu-buru dilakukan bersamaan dengan pencarian yang masih longgar.

### Output
Mekanisme (pemanggilan model AI) yang menerima kandidat `view_name` beserta definisi lengkapnya, mengembalikan label kecocokan untuk masing-masing kandidat beserta alasan singkat, terutama untuk kasus yang tampak cocok di permukaan tapi ternyata tidak (grain berbeda, atau kolom yang dibutuhkan ternyata hasil join dari sumber lain yang berpotensi tidak selalu terisi). Span `chat` ter-emit sesuai kontrak observability. System prompt-nya mengikuti konvensi storage/versioning/reliability testing di `rancangan-manajemen-prompt.md`.

### Kriteria Keberhasilan
- Kandidat yang namanya terdengar cocok tapi grain-nya sebenarnya berbeda dari yang dibutuhkan (skenario uji: kebutuhan butuh breakdown per tipe kamar, kandidat yang tersedia hanya ringkasan per properti) diberi label yang tepat (sebagian atau tidak ditemukan), bukan disamaratakan sebagai cocok penuh.
- Kandidat yang benar-benar cocok penuh (nama, grain, dan sumber data semuanya sesuai kebutuhan) diberi label ditemukan tanpa keraguan yang tidak perlu.

---

## Milestone 3.3 — Membangun Pemeriksaan Kecukupan Struktural

### Lingkup
Membangun mekanisme yang mencocokkan label bentuk jawaban dari kebutuhan atomik (nilai tunggal, tren, perbandingan, peringkat, atau komposisi — hasil Decomposition) terhadap grain view yang sudah dinyatakan cocok makna di Milestone 3.2. Karena grain tiap view sudah dideklarasikan eksplisit di katalog (misalnya "grain: properti × tipe kamar × tanggal" untuk kebutuhan tren, versus "grain: satu baris per properti, snapshot" yang tidak cukup untuk tren), pemeriksaan ini bisa dilakukan sebagai pencocokan yang jauh lebih terstruktur dibanding rancangan lama, yang hanya bisa menyimpulkan dari nama kolom.

### Kenapa Ini Jadi Milestone Terpisah
Pemeriksaan makna (Milestone 3.2) dan pemeriksaan kecukupan struktural (di sini) adalah dua pertanyaan yang berbeda — satu soal "apakah ini hal yang benar", satu soal "apakah bentuknya cukup untuk menjawab dengan cara yang diminta". Kebutuhan yang view-nya sudah tepat secara makna masih bisa gagal di sini kalau grain-nya tidak mencukupi bentuk jawaban yang diminta.

### Output
Mekanisme yang menerima label bentuk jawaban dan grain view, mengembalikan keputusan cukup/tidak cukup, dengan alasan spesifik untuk kasus tidak cukup (misalnya "label meminta tren waktu, tapi view yang tersedia hanya snapshot satu titik waktu"). Menandai penutupan tiga langkah Retriever (Milestone 3.1-3.3): pada titik ini, span pencarian dari Milestone 3.1 dilengkapi atribut `retrieval.selected_view` begitu `view_name` final ditentukan, sesuai kontrak observability.

### Kriteria Keberhasilan
- Kebutuhan berlabel tren yang hanya punya kandidat view snapshot (tanpa dimensi waktu berulang) dinyatakan tidak cukup, bukan dipaksakan lolos.
- Kebutuhan berlabel nilai tunggal yang view-nya memang menyediakan grain sesuai (satu baris relevan) dinyatakan cukup.
- Atribut `retrieval.selected_view` pada span Milestone 3.1 terisi dengan `view_name` yang benar-benar dipilih setelah melalui Milestone 3.2-3.3, terlihat konsisten saat trace ditelusuri di Jaeger/Grafana.

---

## Milestone 3.4 — Membangun Penyusunan Request

### Lingkup
Membangun mekanisme yang menyusun bentuk permintaan akhir — `{domain, view_name, params}` — dari `view_name` yang sudah divalidasi Retriever dan teks kebutuhan atomik. Bagian `params` diisi berdasarkan parameter yang memang tersedia untuk view tersebut sesuai kontrak `api-chatbot.md` (rentang tanggal, kode properti untuk kasus `all_properties`, `limit`/`offset`, dan filter khusus domain lainnya). Pekerjaan ini bersifat lebih dekat ke pengisian slot terstruktur daripada penulisan bebas — tidak ada lagi keputusan semacam "GROUP BY apa" atau "JOIN dengan apa" yang perlu diambil, karena itu semua sudah dibekukan di dalam definisi view.

### Kenapa Ini Jadi Milestone Terpisah
Ini langkah "menghasilkan" dalam pola generate-verify yang dipertahankan di seluruh sistem — dipisah dari langkah verifikasinya (Milestone 3.5) agar keduanya independen satu sama lain, konsisten dengan prinsip yang sama diterapkan di seluruh layer lain.

### Output
Mekanisme (pemanggilan model AI, berupa ekstraksi parameter terstruktur) yang menghasilkan objek request lengkap `{domain, view_name, params}` siap diverifikasi. Span `chat` ter-emit sesuai kontrak observability, dengan atribut `request.domain` dan `request.view_name`. System prompt-nya mengikuti konvensi storage/versioning/reliability testing di `rancangan-manajemen-prompt.md`.

### Kriteria Keberhasilan
- Kebutuhan dengan rentang waktu relatif dalam bahasa sehari-hari (skenario uji: "bulan lalu", "tiga bulan terakhir") diterjemahkan menjadi rentang tanggal konkret yang benar di parameter, bukan diteruskan sebagai teks mentah.
- Request yang dihasilkan hanya berisi parameter yang memang terdaftar valid untuk `view_name` tersebut sesuai kontrak `api-chatbot.md` — tidak ada parameter yang dikarang di luar yang tersedia.

---

## Milestone 3.5 — Membangun Verifikasi Bentuk Request

### Lingkup
Membangun mekanisme yang menilai ulang hasil Milestone 3.4 secara independen — tidak melihat proses berpikir langkah penyusunan — memeriksa dua hal: apakah `view_name` yang tercantum benar-benar sama dengan yang divalidasi Retriever (kepatuhan sumber), dan apakah parameter yang disusun benar-benar akan menghasilkan bentuk jawaban yang diminta (misalnya untuk label tren, apakah rentang tanggal yang diisi cukup panjang untuk membentuk tren, bukan hanya satu hari). Langkah ini secara sengaja tetap memakai model AI, bukan pencocokan aturan sederhana, meskipun cakupan tugas Milestone 3.4 sendiri sudah menyempit menjadi pengisian slot — karena yang diperiksa di sini masih menyentuh soal kesesuaian *makna* terhadap kebutuhan asli, bukan sekadar kepatuhan struktural yang seluruh ruang kesalahannya bisa didaftar sebagai aturan tertutup di depan.

### Kenapa Ini Jadi Milestone Terpisah
Melengkapi pola generate-verify yang dipertahankan dari Milestone 3.4 — independensi antara langkah penyusunan dan langkah penilaian ulang ini mencegah bias "membenarkan diri sendiri" yang muncul kalau proses yang sama diminta menilai hasilnya sendiri.

### Output
Mekanisme (pemanggilan model AI) yang menerima request hasil Milestone 3.4 beserta teks kebutuhan asli, mengembalikan keputusan lolos atau perlu revisi dengan alasan spesifik untuk kasus revisi. Span `chat` ter-emit sesuai kontrak observability. System prompt-nya mengikuti konvensi storage/versioning/reliability testing di `rancangan-manajemen-prompt.md`.

### Kriteria Keberhasilan
- Request dengan `view_name` yang sengaja dibuat tidak sesuai hasil Retriever (skenario uji terkontrol) berhasil ditangkap dan ditolak oleh verifikasi ini.
- Request berlabel tren yang parameter rentang tanggalnya sengaja dipersempit jadi satu hari saja (skenario uji terkontrol) berhasil ditangkap sebagai tidak sesuai bentuk jawaban yang diminta.

---

## Catatan Serah Terima ke Pekerjaan Lain

Daftar `view_name` yang divalidasi di Milestone 3.1-3.3 menjadi rujukan yang dipakai Verification Gate (`rancangan-rbac-authorization.md`, Milestone 2.4) untuk memeriksa kepatuhan sumber — pastikan bentuk keluaran Retriever (nama field, format daftar kandidat) terdokumentasi jelas dan tidak berubah sepihak tanpa dikomunikasikan ke pemilik pekerjaan tersebut.

Request final hasil Milestone 3.4-3.5 dikirim ke Verification Gate (`rancangan-rbac-authorization.md`) sebagai bagian dari alur normal sebelum diteruskan ke Execution (`rancangan-execution-interpretation.md`) — skema `{domain, view_name, params}` adalah kontrak yang mengikat ketiga pekerjaan ini sekaligus, perubahan pada skema ini perlu disepakati bersama.

Jalur perbaikan untuk request yang gagal di tahap Execution karena status `400` (bentuk parameter salah, bukan pelanggaran otorisasi) kembali ke Milestone 3.4 untuk direvisi — mekanisme pengiriman balik ini perlu disepakati bentuknya dengan pemilik `rancangan-execution-interpretation.md` sebelum diimplementasikan di kedua sisi.
