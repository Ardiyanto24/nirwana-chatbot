# Rancangan Implementasi — Execution & Interpretation

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Execution & Interpretation) |
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` (Bagian 5-7), `rancangan-observability-ai-chatbot.md` (Bagian 2) |
| **Dokumen rujukan kebutuhan** | `api-chatbot.md` (kontrak endpoint, kode status, mekanisme penolakan), `katalog-data-chatbot.md` (pola nullable-bermakna per kolom, untuk catatan interpretasi) |
| **Cakupan pekerjaan** | Execution (pemanggilan `chatbot_api`, klasifikasi respons, penyimpanan paket ke Session Memory) dan Interpretation (penyusunan narasi, verifikasi kesetiaan data, penyusunan data visualisasi) |
| **Tidak termasuk** | Penyusunan request `{domain, view_name, params}` itu sendiri (lihat `rancangan-retrieval-query.md` — pekerjaan ini menerima request yang sudah lolos Verification Gate, tidak menyusunnya); keputusan otorisasi (lihat `rancangan-rbac-authorization.md`); `chatbot_api` itu sendiri (sistem eksternal, sudah selesai dan terverifikasi, tidak dimodifikasi di sini) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic. Setiap milestone mencakup satu lingkup kerja koheren — kalau dipecah lebih jauh ke task teknis, seluruh pecahan itu tetap berada dalam lingkup yang sama. Milestone tidak menentukan tech stack, library, atau arsitektur detail secara spesifik — itu keputusan yang sengaja diserahkan ke saat pengerjaan nyata berlangsung.

Kecuali untuk hal yang sudah dikunci eksplisit di dua dokumen induk. Yang paling mengikat untuk pekerjaan ini: klasifikasi kegagalan `403`/`404` sebagai sinyal bug prioritas tinggi yang dieskalasi langsung tanpa retry (bukan alur normal yang dicoba ulang atau dikirim balik untuk revisi) — ini keputusan yang sudah dipertimbangkan matang di dokumen arsitektur dan tidak boleh diubah sepihak di sini; dan skema paket Session Memory yang wajib konsisten dengan yang dipakai `rancangan-context-decomposition.md`.

Urutan milestone adalah urutan yang disarankan, bukan kaku.

---

## Konteks: Titik Akhir yang Dipakai User

Pekerjaan ini adalah dua langkah terakhir dari sembilan layer — satu-satunya titik yang benar-benar menyentuh dunia luar (`chatbot_api`) dan satu-satunya titik yang hasilnya langsung dibaca user tanpa ada gerbang lagi setelahnya. Karena posisinya di ujung, kesalahan di sini tidak punya kesempatan diperbaiki oleh layer berikutnya — bobot verifikasinya karena itu berbeda dari layer-layer di depan, dan baru bisa difinalisasi dengan baik setelah bentuk request final dari `rancangan-retrieval-query.md` dan keputusan otorisasi dari `rancangan-rbac-authorization.md` sudah stabil.

---

## Milestone 4.1 — Membangun Pemanggilan chatbot_api

### Lingkup
Membangun satu-satunya titik dalam seluruh sistem yang benar-benar melakukan panggilan HTTP ke `chatbot_api`, menerima request yang sudah lolos Verification Gate, dan mengembalikan responsnya apa adanya tanpa modifikasi. Pekerjaan ini murni teknis, tanpa keterlibatan model AI sama sekali — konsisten dengan prinsip bahwa titik commit (di mana efek nyata terjadi ke sistem eksternal) harus steril dari proses generatif apa pun. Satu-satunya titik yang perlu tahu detail koneksi ke `chatbot_api` (alamat, format autentikasi bila ada) adalah di sini — tidak ada layer lain yang boleh memanggilnya secara langsung.

### Kenapa Ini Jadi Milestone Terpisah
Ini fondasi paling dasar dari seluruh pekerjaan ini — kemampuan klasifikasi respons dan penanganan kegagalan (milestone berikutnya) tidak berguna tanpa mekanisme pemanggilan yang bekerja lebih dulu.

### Output
Mekanisme HTTP client yang menerima request final `{domain, view_name, params}` dan mengembalikan respons mentah dari `chatbot_api` (kode status beserta isi body-nya), tanpa interpretasi apa pun di tahap ini. Span `execute_tool` ter-emit sesuai kontrak observability, mencatat `http.response.status_code`.

### Kriteria Keberhasilan
- Request yang valid terhadap salah satu endpoint `chatbot_api` (dicoba nyata terhadap sistem yang sudah berjalan) menghasilkan respons `200` dengan data yang benar diterima dan diteruskan apa adanya.
- Request yang sengaja dibuat melanggar otorisasi (skenario uji: role tanpa akses ke suatu domain) menghasilkan respons `403` yang tertangkap dan diteruskan apa adanya ke langkah klasifikasi, tanpa memodifikasi atau menyembunyikannya.

---

## Milestone 4.2 — Membangun Klasifikasi Respons dan Penanganan Kegagalan

### Lingkup
Membangun logika yang membaca kode status hasil Milestone 4.1 dan menentukan jalur penanganannya, mengikuti pembagian yang sudah dikunci di dokumen arsitektur: respons `200` dikumpulkan sebagai hasil berhasil atau sebagian; respons `400` (bentuk parameter salah) dikirim balik ke Query Engine untuk direvisi, karena ini murni kesalahan bentuk yang bisa diperbaiki tanpa mengubah keputusan otorisasi; kegagalan infrastruktural (`5xx`, timeout, connection refused) dicoba ulang persis sama, karena sifatnya tidak berkorelasi dengan isi request; dan yang paling penting, respons `403`/`404` dieskalasi langsung sebagai kegagalan teknis tanpa dicoba ulang sama sekali dan tanpa dikirim balik untuk revisi — karena keduanya deterministik terhadap isi request (akan selalu gagal lagi dengan permintaan yang sama), dan kemunculannya berarti ada kegagalan di layer yang seharusnya sudah mencegah ini terjadi lebih awal (Domain Gate salah meloloskan sesuatu yang seharusnya ditolak, atau Retriever memilih `view_name` yang ternyata tidak eksis).

### Kenapa Ini Jadi Milestone Terpisah
Pemanggilan (Milestone 4.1) dan penanganan hasil (di sini) adalah dua tanggung jawab yang berbeda — satu soal melakukan aksi, satu soal menafsirkan konsekuensinya. Memisahkannya memungkinkan logika klasifikasi diuji secara menyeluruh dengan berbagai skenario respons tanpa perlu benar-benar memanggil `chatbot_api` berulang kali untuk tiap kasus.

### Output
Mekanisme klasifikasi yang mengubah kode status mentah menjadi salah satu dari lima jalur penanganan yang sudah ditentukan (berhasil/sebagian, kirim balik untuk revisi, retry infrastruktural, eskalasi sebagai bug prioritas tinggi), lengkap dengan batas jumlah percobaan ulang yang wajar untuk mencegah pengulangan tak berkesudahan. Atribut `error.type` dan jumlah percobaan ulang ter-emit ke span sesuai kontrak observability.

### Kriteria Keberhasilan
- Respons `403`/`404` (dicoba dengan skenario uji terkontrol) langsung dieskalasi tanpa satu pun percobaan ulang, dan ditandai sebagai sinyal prioritas tinggi yang berbeda perlakuannya dari kegagalan biasa.
- Respons `5xx`/timeout (disimulasikan) dicoba ulang sesuai batas yang ditentukan, dan kalau tetap gagal setelah batas itu, dieskalasi sebagai kegagalan teknis — bukan dicoba tanpa henti.
- Respons `400` (disimulasikan dengan parameter yang sengaja salah bentuk) benar-benar terkirim balik ke jalur revisi Query Engine, bukan diperlakukan sama seperti kegagalan lain.

---

## Milestone 4.3 — Membangun Penyimpanan Paket ke Session Memory

### Lingkup
Membangun mekanisme yang menyusun paket lengkap sesuai skema yang sudah dikunci di dokumen arsitektur — nilai hasil, status, catatan interpretasi, dan penanda sumber "eksekusi_baru" — untuk setiap atomic intent yang selesai diproses (baik berhasil, sebagian, ditolak, maupun gagal teknis), lalu menyimpannya ke Session Memory. Catatan interpretasi di sini bukan field yang otomatis terisi dari `chatbot_api`, melainkan pengetahuan yang perlu ditempelkan berdasarkan pola nullable-bermakna yang sudah teridentifikasi di katalog data (misalnya kolom yang kosong karena memang tidak ada kejadian, bukan karena data hilang) — pekerjaan ini perlu tahu pola-pola semacam ini untuk kolom yang relevan dengan hasil yang diterima.

### Kenapa Ini Jadi Milestone Terpisah
Ini titik di mana hasil eksekusi turn ini menjadi tersedia untuk dirujuk turn-turn berikutnya — cukup penting untuk berdiri sebagai langkah tersendiri, terpisah dari klasifikasi respons murni (Milestone 4.2), karena skemanya harus persis sama dengan yang dipakai `rancangan-context-decomposition.md` saat menarik data ini kembali.

### Output
Mekanisme yang menerima hasil terklasifikasi dari Milestone 4.2 dan menyusunnya menjadi paket sesuai skema kontrak, lalu menyimpannya ke penyimpanan Session Memory yang sama dipakai `rancangan-context-decomposition.md`. Bentuk teknis penyimpanan mengikuti keputusan yang sudah diambil pemilik pekerjaan tersebut, bukan dibangun ulang secara terpisah di sini. Span non-LLM ter-emit sesuai kontrak observability untuk operasi penulisan ini, sejalan dengan operasi pembacaan setara (`memory.retrieve`) yang sudah diinstrumentasi di Milestone 1.5 — supaya durasi dan kegagalan operasi tulis ke Session Memory juga bisa diamati, bukan hanya operasi bacanya.

### Kriteria Keberhasilan
- Paket yang tersimpan untuk suatu atomic intent bisa ditarik kembali oleh mekanisme Milestone 1.5 (`rancangan-context-decomposition.md`) dan menghasilkan isi yang identik dengan yang disimpan, membuktikan kedua pekerjaan benar-benar menggunakan skema dan penyimpanan yang sama.
- Span penulisan ke Session Memory terlihat di Jaeger/Grafana dengan durasi yang tercatat, dan skenario uji penulisan yang sengaja dibuat gagal (mis. penyimpanan tidak terjangkau sesaat) menghasilkan `error.type` yang sesuai pada span tersebut.
- Atomic intent dengan hasil non-normal (skenario uji: kolom yang kosong karena pola nullable-bermakna) tersimpan dengan catatan interpretasi yang tepat, bukan disimpan seolah data itu hilang atau bermasalah.

---

## Milestone 4.4 — Membangun Penyusunan Narasi

### Lingkup
Membangun mekanisme yang menyusun jawaban akhir dalam bahasa natural dari campuran dua sumber paket data — yang baru selesai dieksekusi di Milestone 4.3, dan yang ditarik dari session memory turn sebelumnya (hasil kerja `rancangan-context-decomposition.md`) — yang secara sengaja diperlakukan identik oleh mekanisme ini karena keduanya berbagi skema yang sama persis. Penyusunan ini mengikuti lima ketentuan wajib yang sudah dikunci di dokumen arsitektur: status kualitas non-normal disampaikan jujur, hasil parsial disampaikan sebagai parsial, penolakan dan kegagalan disampaikan eksplisit (dengan bahasa yang berbeda nada untuk penolakan otorisasi yang memang harus disebutkan spesifik ke user, dibanding kegagalan teknis yang cukup disampaikan jujur tanpa detail teknis internal), tidak ada klaim sebab-akibat yang dipaksakan dari data yang sifatnya deskriptif, dan kebutuhan yang gagal karena bergantung pada kebutuhan lain yang juga gagal disampaikan spesifik penyebabnya. Ditambah satu ketentuan yang lahir khusus dari kebutuhan multi-turn sistem ini: narasi perlu jujur menyebutkan mana bagian jawaban yang baru dihitung dan mana yang merujuk hasil turn sebelumnya, memanfaatkan penanda sumber yang sudah ada di tiap paket.

### Kenapa Ini Jadi Milestone Terpisah
Ini langkah "menghasilkan" dalam pola generate-verify — dipisah dari langkah verifikasinya (Milestone 4.5) agar keduanya independen satu sama lain, konsisten dengan prinsip yang sama diterapkan di seluruh sistem.

### Output
Mekanisme (pemanggilan model AI) yang menerima kumpulan paket data (dari kedua sumber) beserta relasi antar-atomic-intent dari Decomposition, menghasilkan narasi jawaban yang koheren dan jujur. Span `chat` ter-emit sesuai kontrak observability.

### Kriteria Keberhasilan
- Jawaban yang mencampur hasil baru dan hasil dari turn sebelumnya (skenario uji: pertanyaan lanjutan yang merujuk balik ke turn lain) secara eksplisit menyebutkan mana yang baru dihitung dan mana yang merujuk hasil sebelumnya, bukan menyajikan keduanya seolah dihitung bersamaan.
- Jawaban yang mengandung atomic intent berstatus ditolak_otorisasi menyebutkan penolakan itu secara jelas dan spesifik ke user, sementara atomic intent berstatus gagal_teknis disampaikan jujur tanpa detail teknis internal yang membingungkan.

---

## Milestone 4.5 — Membangun Verifikasi Kesetiaan Data dan Penyusunan Visualisasi

### Lingkup
Membangun langkah penilaian ulang narasi hasil Milestone 4.4 secara independen — tidak melihat proses berpikir langkah penyusunan — memeriksa bahwa tidak ada bagian data yang hilang dari narasi, status non-normal disampaikan jujur, tidak ada klaim sebab-akibat yang tidak berdasar, angka yang disebutkan benar-benar berasal dari data yang diterima (bukan dikarang), dan status terblokir disampaikan spesifik bukan digeneralisasi. Digabung dalam milestone yang sama dengan penyusunan data terstruktur untuk visualisasi (transformasi struktur data murni, tanpa model AI, menyesuaikan label bentuk jawaban dari Decomposition) karena keduanya sama-sama langkah penutup yang dijalankan setelah narasi final disetujui.

### Kenapa Ini Jadi Milestone Terpisah
Sebagai layer terakhir sebelum jawaban sampai ke user tanpa ada gerbang lagi setelahnya, langkah verifikasi ini menanggung bobot yang lebih besar dibanding verifikasi di layer-layer sebelumnya — layak diuji secara eksplisit dan terpisah dari proses penyusunan narasi itu sendiri.

### Output
Mekanisme (pemanggilan model AI) yang menilai narasi hasil Milestone 4.4 dan mengembalikan keputusan lolos atau perlu revisi dengan alasan spesifik. Untuk narasi yang lolos, dilanjutkan dengan penyusunan data terstruktur (bukan model AI) yang siap dikonsumsi frontend untuk ditampilkan sebagai grafik atau tabel sesuai label bentuk jawabannya. Span `chat` (verifikasi) ter-emit sesuai kontrak observability.

### Kriteria Keberhasilan
- Narasi yang sengaja dibuat mengandung klaim sebab-akibat tidak berdasar dari data deskriptif (skenario uji terkontrol) berhasil ditangkap dan ditolak oleh verifikasi ini.
- Data terstruktur yang dihasilkan untuk kebutuhan berlabel tren benar-benar berbentuk deret yang bisa digambar sebagai grafik garis, dan untuk kebutuhan berlabel nilai tunggal berbentuk angka tunggal yang sesuai — tidak ada ketidaksesuaian antara label bentuk jawaban dan struktur data yang dihasilkan.

---

## Catatan Serah Terima ke Pekerjaan Lain

Jalur revisi untuk respons `400` di Milestone 4.2 dikirim balik ke Query Engine (`rancangan-retrieval-query.md`) — bentuk dan mekanisme pengiriman balik ini adalah kontrak dua arah yang perlu disepakati bersama pemilik pekerjaan tersebut, bukan diputuskan sepihak di sini.

Skema paket Session Memory yang ditulis di Milestone 4.3 wajib identik dengan yang dibaca `rancangan-context-decomposition.md` (Milestone 1.5) — kedua pekerjaan menulis dan membaca struktur data yang sama; perubahan skema apa pun (field baru, perubahan tipe) perlu disepakati bersama sebelum diimplementasikan salah satu pihak.

Klasifikasi `403`/`404` sebagai sinyal bug prioritas tinggi (Milestone 4.2) idealnya juga menjadi masukan penting bagi pekerjaan observability (`rancangan-observability-ai-chatbot.md`) — kemunculan sinyal ini seharusnya terlihat menonjol di dashboard, baik privat maupun publik, karena menandakan kegagalan di layer lain (Domain Gate atau Retriever) yang perlu segera ditelusuri, bukan sekadar dicatat sebagai baris log biasa.
