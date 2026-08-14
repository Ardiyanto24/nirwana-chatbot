# Rancangan Implementasi — RBAC & Authorization

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC RBAC & Authorization) |
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` (Bagian 2, 5), `rancangan-observability-ai-chatbot.md` (Bagian 2) |
| **Dokumen rujukan kebutuhan** | `rancangan-rbac-ai-chatbot.md` (20 role × 10 domain, `role_permissions`; **Bagian 1 dan 2 dokumen ini merinci sampai level KOLOM untuk pemisahan `guests_pii`/`guests_profile` — bukan cuma level domain**, wajib dibaca detail sebelum Milestone 2.1, bukan sekadar direferensikan), `katalog-data-chatbot.md` (definisi 67 view, termasuk penanda domain "bocor" lewat kolom turunan dan view kategori performa individu), `api-chatbot.md` (kontrak `chatbot_api`, Lapis 2 RBAC yang sudah selesai dan independen dari pekerjaan ini) |
| **Cakupan pekerjaan** | Domain Gate (identifikasi domain, verifikasi titik buta, pemeriksaan otorisasi, deteksi constraint cakupan-individu) dan Verification Gate (validasi bentuk request statis, kepatuhan sumber, penegakan constraint, verifikasi kelengkapan) |
| **Tidak termasuk** | Penegakan RBAC row-level untuk `property_id` — itu sepenuhnya didelegasikan ke `chatbot_api` (Lapis 2), sudah selesai dan terverifikasi independen, tidak dibangun ulang di sini; pemilihan `view_name` dan penyusunan isi request (lihat `rancangan-retrieval-query.md`); pemanggilan `chatbot_api` yang sesungguhnya (lihat `rancangan-execution-interpretation.md`) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic. Setiap milestone mencakup satu lingkup kerja koheren — kalau dipecah lebih jauh ke task teknis, seluruh pecahan itu tetap berada dalam lingkup yang sama. Milestone tidak menentukan tech stack, library, atau arsitektur detail secara spesifik — itu keputusan yang sengaja diserahkan ke saat pengerjaan nyata berlangsung.

Kecuali untuk hal yang sudah dikunci eksplisit di dua dokumen induk — itu bukan pilihan bebas implementasi, melainkan kontrak yang wajib diikuti. Yang paling mengikat untuk pekerjaan ini: prinsip "ruang kesalahan tertutup vs terbuka" yang menentukan kapan suatu pemeriksaan boleh murni deterministik dan kapan wajib tetap memakai model AI — dilanggarnya prinsip ini bukan sekadar preferensi gaya, melainkan mengubah jenis kesalahan yang bisa ditangkap sistem.

Urutan milestone adalah urutan yang disarankan, bukan kaku.

---

## Kenapa Pekerjaan Ini Dipisah Sebagai Kepemilikan Tersendiri

Domain Gate dan Verification Gate sama-sama mengonsumsi satu sumber kebenaran yang sama: `role_permissions` dan definisi constraint cakupan-individu dari katalog data. Keduanya juga saling terikat dalam satu rangkaian keputusan yang tidak boleh berkontradiksi satu sama lain — Domain Gate *mendeteksi* apa yang boleh dan tidak boleh diakses beserta constraint tambahan yang perlu ditegakkan, sementara Verification Gate *menegakkan* deteksi itu tepat sebelum eksekusi. Kalau keduanya dibangun oleh pemilik yang berbeda, atau menyatu diam-diam ke layer-layer di sekitarnya (Decomposition di satu sisi, Query Engine di sisi lain), risikonya adalah dua sumber pemahaman berbeda untuk definisi otorisasi yang seharusnya satu — persis alasan kenapa `mart_aggregated` di project data platform dipegang satu kepemilikan tunggal, bukan dibangun terpisah oleh masing-masing tim konsumennya. Kesalahan pemahaman otorisasi juga menyangkut keamanan data sensitif secara langsung, sehingga layak mendapat kepemilikan yang bisa diaudit sebagai satu kesatuan yang koheren, bukan tersebar dan sulit ditelusuri tanggung jawabnya.

---

## Konteks: Posisi Pekerjaan Ini dalam RBAC Dua Lapis

Sistem AI Chatbot ini adalah Lapis 1 dari RBAC dua lapis. Lapis 2 — `chatbot_api`, yang menegakkan otorisasi domain via `role_permissions` dan me-resolve `property_id` dari `employee_id` secara independen — sudah selesai dibangun dan terverifikasi (KK1-3), sepenuhnya di luar cakupan pekerjaan ini. Peran Lapis 1 bukan mengulang apa yang sudah ditegakkan Lapis 2, melainkan menjaga hal yang tidak dijamin Lapis 2 sama sekali: memahami *maksud* pertanyaan sebelum sistem bahkan mencoba menyusun permintaan apa pun, termasuk kasus cakupan individu dalam satu properti (misalnya seorang Staff menanyakan performa staf lain di properti yang sama) yang tidak tersentuh resolusi `property_id` milik Lapis 2 sama sekali.

---

## Milestone 2.1 — Membangun Identifikasi Domain dan Verifikasi Titik Buta

### Lingkup
Membangun kemampuan sistem untuk membaca kebutuhan atomik hasil Decomposition dan mengenali domain data apa saja yang sebenarnya tersentuh olehnya — termasuk domain yang tidak disebut secara eksplisit dalam bahasa pertanyaan tapi tetap relevan. Pekerjaan ini secara khusus perlu menangani tiga pola jebakan nyata yang sudah teridentifikasi di dokumen rujukan kebutuhan: pertama, domain yang "bocor" lewat kolom turunan di dalam satu view (contohnya `v_reservation_gop_impact_monthly`, yang secara nominal berada di domain `reservation` tapi salah satu kolomnya berasal dari domain `financial`, sehingga kebutuhan yang menyentuh kolom itu perlu mengenali kedua domain sekaligus, bukan hanya domain tempat view itu terdaftar); kedua, kasus di mana identifikasi awal melewatkan sesuatu karena fokus terlalu sempit pada kata-kata yang eksplisit disebut; ketiga — dan ini yang paling perlu diperhatikan cermat — pemisahan di level **kolom, bukan domain**, khusus untuk `guests_pii` vs `guests_profile`. Keduanya sama-sama bersumber dari tabel fisik `guests` yang sama, tapi `rancangan-rbac-ai-chatbot.md` Bagian 1 merinci eksplisit: `guests_pii` mencakup hanya kolom kontak (`full_name`, `email`, `phone`), sementara `guests_profile` mencakup kolom atribut analitis (`loyalty_tier`, `nationality`, riwayat booking) — tidak termasuk kontak. Pertanyaan yang menyebut "data tamu" secara umum tidak cukup diklasifikasikan sebagai satu domain generik; identifikasi wajib menentukan kolom spesifik mana yang dimaksud untuk memutuskan domain mana (`guests_pii`, `guests_profile`, atau keduanya) yang sebenarnya tersentuh — dokumen ini eksplisit menyebut logika ini "dieksekusi saat AI Agent menyusun query sesuai lapis RBAC pertama", yaitu pekerjaan ini sendiri. Karena itu, langkah identifikasi awal sengaja diikuti langkah verifikasi terpisah yang mencari titik buta — bukan menilai ulang hasil yang sama, melainkan secara aktif mencari apa yang mungkin terlewat, sebagai proses yang independen dari proses berpikir langkah pertama.

### Kenapa Ini Jadi Milestone Terpisah
Mengidentifikasi domain dengan benar adalah prasyarat mutlak sebelum otorisasi bisa diperiksa sama sekali — kalau identifikasi salah atau tidak lengkap, pemeriksaan otorisasi berikutnya akan memeriksa hal yang salah, walau mekanismenya sendiri benar.

### Output
Dua mekanisme berurutan (dua pemanggilan model AI): satu untuk identifikasi domain awal dari teks kebutuhan atomik, satu lagi yang secara independen menilai ulang untuk mencari domain yang mungkin terlewat — termasuk pola domain tersembunyi lewat kolom turunan, dan pola pemisahan `guests_pii`/`guests_profile` di level kolom sesuai Bagian 1 `rancangan-rbac-ai-chatbot.md`. Hasil akhirnya adalah daftar domain lengkap yang tersentuh oleh satu kebutuhan atomik, siap diperiksa otorisasinya di milestone berikutnya. Span `chat` (dua kali) ter-emit sesuai kontrak observability, mencatat domain yang teridentifikasi di tiap langkah.

### Kriteria Keberhasilan
- Kebutuhan yang secara eksplisit menyebut satu domain saja, tapi sebenarnya menyentuh kolom turunan dari domain lain (skenario uji: pertanyaan yang menyentuh `gop_margin` di view domain `reservation`), berhasil mengenali kedua domain, bukan hanya domain yang disebut eksplisit.
- Langkah verifikasi titik buta terbukti mampu menangkap setidaknya satu domain yang sengaja dihilangkan dari hasil langkah pertama dalam pengujian terkontrol.
- Kebutuhan yang menyebut "data tamu" secara umum tanpa menegaskan jenis kolomnya (skenario uji: "beri saya data kontak Bapak Herman" vs "berapa nationality mix tamu bulan ini") diklasifikasikan ke domain `guests_pii` atau `guests_profile` secara tepat sesuai kolom yang sebenarnya dimaksud — bukan diklasifikasikan ke domain generik "guests" yang tidak eksis di `role_permissions`, dan bukan disamaratakan sebagai satu domain untuk kedua kasus.

---

## Milestone 2.2 — Membangun Pemeriksaan Otorisasi

### Lingkup
Membangun mekanisme yang mencocokkan daftar domain hasil Milestone 2.1 terhadap `role_title` pemanggil, merujuk langsung ke tabel `role_permissions` (20 role × 10 domain) yang sudah final dan teraudit di dokumen rujukan kebutuhan. Ini murni pencocokan aturan berbasis lookup — bukan pemanggilan model AI — karena seluruh ruang kemungkinan hasilnya (role mana boleh domain apa) sudah terdaftar lengkap dan tertutup, tidak ada ambiguitas bahasa yang perlu ditafsirkan di titik ini.

### Kenapa Ini Jadi Milestone Terpisah
Berbeda sifat sepenuhnya dari Milestone 2.1 — satu soal pemahaman bahasa (LLM), satu soal pencocokan aturan tertutup (deterministik). Memisahkan keduanya menjaga agar bagian yang seharusnya cepat dan pasti tidak tercampur dengan bagian yang inherently melibatkan model AI.

### Output
Mekanisme lookup yang menerima daftar domain dan `role_title`, mengembalikan keputusan izin/tolak per domain, beserta alasan penolakan yang spesifik (domain mana yang ditolak, bukan pesan generik) untuk domain yang ditolak. Span non-LLM ter-emit sesuai kontrak observability, dengan atribut `rbac.domain` dan `rbac.decision`, serta `error.type=ditolak_otorisasi` untuk kasus penolakan.

### Kriteria Keberhasilan
- Seluruh kombinasi role × domain yang tercatat di `role_permissions` diuji sistematis (bukan sampel), dan hasil izin/tolaknya cocok persis dengan tabel rujukan — tidak ada kombinasi yang menghasilkan keputusan berbeda dari yang seharusnya.
- Kebutuhan dengan lebih dari satu domain (hasil Milestone 2.1) yang sebagian domainnya diizinkan dan sebagian ditolak, menghasilkan keputusan per-domain yang benar untuk masing-masing, bukan keputusan tunggal yang menyamaratakan semuanya.

---

## Milestone 2.3 — Membangun Deteksi Constraint Cakupan-Individu

### Lingkup
Membangun kemampuan mengenali kebutuhan atomik yang menyentuh kategori view sensitif tertentu — data performa individu staf (misalnya kehadiran atau kecepatan kerja per orang) — di mana `chatbot_api` tidak menjamin pembatasan apa pun terhadap siapa yang datanya boleh dilihat, karena resolusinya hanya menjaga batas properti, bukan batas antar-individu dalam properti yang sama. Ketika kebutuhan semacam ini terdeteksi dan role pemanggilnya adalah Staff, pekerjaan ini mencatat constraint eksplisit — bahwa permintaan ini, kalau diteruskan, wajib membawa filter yang membatasi hasilnya hanya ke data milik pemanggil sendiri. Pekerjaan ini murni **mencatat** constraint tersebut sebagai metadata yang menempel ke kebutuhan atomik; ia tidak menegakkannya secara langsung — penegakan sesungguhnya terjadi belakangan di Verification Gate (Milestone 2.4).

### Kenapa Ini Jadi Milestone Terpisah
Ini gap yang secara sengaja tidak dijamin oleh Lapis 2 RBAC (`chatbot_api`), sehingga perlu penanganan eksplisit di Lapis 1. Memisahkan deteksi (di sini) dari penegakan (Milestone 2.4) mengikuti pola yang sama dengan pemisahan generate-verify di seluruh sistem: deteksi butuh pemahaman konteks (cocok untuk model AI), sementara penegakan murni soal kepatuhan terhadap catatan yang sudah ada (cocok deterministik, tanpa model AI).

### Output
Mekanisme yang, untuk kebutuhan atomik yang lolos Milestone 2.2, memeriksa apakah kebutuhan itu menyentuh kategori view performa individu, dan jika role pemanggilnya Staff, menempelkan catatan constraint eksplisit ke kebutuhan tersebut. Kebutuhan dari role Manager/Corporate tidak mendapat constraint tambahan ini. Span ter-emit sesuai kontrak observability, mencatat penanda constraint bila terdeteksi.

### Kriteria Keberhasilan
- Kebutuhan dari role Staff yang menyentuh view kategori performa individu (skenario uji: "siapa staf tercepat bulan ini") menghasilkan catatan constraint yang eksplisit dan bisa ditelusuri.
- Kebutuhan serupa dari role Manager/Corporate tidak menghasilkan constraint tambahan apa pun, membuktikan pembedaan berdasar role bekerja dengan benar.
- Kebutuhan yang tidak menyentuh kategori view sensitif ini sama sekali (baik dari Staff maupun role lain) tidak mendapat constraint apa pun, membuktikan deteksi tidak asal menempel ke semua kebutuhan.

---

## Milestone 2.4 — Membangun Verification Gate

### Lingkup
Membangun gerbang terakhir sebelum permintaan benar-benar dikirim ke `chatbot_api` — sepenuhnya deterministik, tanpa pemanggilan model AI sama sekali, karena seluruh hal yang diperiksa di sini adalah kepatuhan struktural yang bisa didaftar sebagai aturan eksplisit di depan, bukan soal kesesuaian makna yang masih terbuka kemungkinan kesalahannya. Ada empat pemeriksaan: bentuk request secara statis (domain dan `view_name` valid secara struktural, `limit` tidak melebihi batas yang ditetapkan `chatbot_api`), kepatuhan sumber (`view_name` yang akan dikirim benar-benar sama dengan yang divalidasi Retriever), penegakan constraint cakupan-individu (memastikan request yang membawa catatan constraint dari Milestone 2.3 benar-benar menyertakan filter yang sesuai — dan jika tidak, menimpanya secara paksa, bukan sekadar menolak), dan verifikasi kelengkapan penegakan itu sendiri.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik pertemuan antara keputusan yang dibuat Domain Gate (Milestone 2.1-2.3) dengan bentuk request nyata yang disusun Query Engine (pekerjaan lain) — layak berdiri sebagai gerbang independen yang memverifikasi keduanya benar-benar konsisten satu sama lain, bukan menyatu diam-diam ke salah satu sisi.

### Output
Mekanisme pemeriksaan berlapis yang menerima request final (hasil kerja Query Engine) beserta constraint yang tercatat dari Domain Gate, dan mengembalikan salah satu dari: request yang sudah diverifikasi lolos (siap diteruskan ke Execution), atau request yang sudah dikoreksi paksa (untuk kasus constraint cakupan-individu yang belum ditegakkan dengan benar), atau penolakan keras dengan alasan spesifik (untuk pelanggaran struktural yang tidak bisa dikoreksi otomatis). Span non-LLM ter-emit sesuai kontrak observability, dengan atribut `verification.check_name` dan `error.type` bila gagal.

### Kriteria Keberhasilan
- Request yang membawa catatan constraint cakupan-individu dari Milestone 2.3 tapi belum menyertakan filter yang sesuai, berhasil dikoreksi paksa dengan filter yang benar sebelum diteruskan — bukan ditolak begitu saja.
- Request yang `view_name`-nya tidak sesuai dengan yang divalidasi Retriever (skenario uji: dibuat sengaja tidak cocok) ditolak dengan alasan spesifik yang menyebut ketidaksesuaian tersebut.
- Request yang sudah benar sepenuhnya (tanpa pelanggaran struktural, constraint sudah ditegakkan dengan benar oleh langkah sebelumnya) lolos tanpa perubahan apa pun.

---

## Catatan Serah Terima ke Pekerjaan Lain

Daftar domain hasil Milestone 2.1-2.2 dan constraint cakupan-individu hasil Milestone 2.3 menjadi masukan langsung bagi Retriever dan Query Engine (`rancangan-retrieval-query.md`) — keduanya perlu tahu domain mana yang sudah diizinkan sebelum memilih `view_name`, dan constraint apa yang perlu dipenuhi saat menyusun parameter request. Perubahan bentuk keluaran Domain Gate (skema penanda domain, skema constraint) berdampak langsung pada pekerjaan tersebut dan perlu dikomunikasikan sebelum diubah.

Verification Gate (Milestone 2.4) menerima request final dari Query Engine (`rancangan-retrieval-query.md`) sebagai input langsung — bentuk request yang disepakati (skema `{domain, view_name, params}` sesuai dokumen arsitektur) adalah kontrak dua arah antara kedua pekerjaan ini; perubahan pada salah satu sisi (field baru, perubahan struktur) perlu disepakati bersama sebelum diimplementasikan, bukan diubah sepihak.

Daftar eksplisit view yang termasuk kategori "performa individu" untuk Milestone 2.3 adalah keputusan teknis yang perlu disusun berdasarkan tinjauan langsung ke seluruh 67 view di katalog data — belum ditentukan di dokumen ini maupun dokumen arsitektur, sengaja didiskusikan terpisah saat pengerjaan dimulai.
