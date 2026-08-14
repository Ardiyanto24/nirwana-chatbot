# Rancangan Implementasi — Observability Dashboard

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Observability Dashboard) |
| **Dokumen induk** | `rancangan-observability-ai-chatbot.md` (seluruh bagian, terutama Bagian 3-4) |
| **Cakupan pekerjaan** | Konfigurasi Grafana di atas Jaeger dan Prometheus (jalur privat), dan pembangunan dashboard Next.js yang membaca dari Supabase (jalur publik) |
| **Tidak termasuk** | Membangun OTel Collector maupun instrumentasi span di kesembilan layer (lihat empat dokumen implementasi PIC 1-4 — pekerjaan ini murni mengonsumsi, tidak menghasilkan sinyal); membangun custom exporter yang menulis ke Supabase (lihat `rancangan-custom-exporter-supabase.md` — pekerjaan ini menerima data yang sudah tersedia di Supabase, tidak membangun jalur masuknya) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic. Setiap milestone mencakup satu lingkup kerja koheren — kalau dipecah lebih jauh ke task teknis, seluruh pecahan itu tetap berada dalam lingkup yang sama. Milestone tidak menentukan tech stack, library, atau arsitektur detail secara spesifik — itu keputusan yang sengaja diserahkan ke saat pengerjaan nyata berlangsung.

Kecuali untuk hal yang sudah dikunci eksplisit di dokumen observability induk. Yang paling mengikat untuk pekerjaan ini: skema tabel `traces` dan `spans` di Supabase (Bagian 4 dokumen induk) adalah kontrak yang wajib diikuti apa adanya — bukan diasumsikan atau ditebak dari bentuk data yang kebetulan ditemukan saat pengerjaan; dan prinsip bahwa dashboard publik harus menampilkan isi yang identik dengan dashboard privat, bukan versi ringkas.

Urutan milestone adalah urutan yang disarankan, bukan kaku — bagian Next.js secara khusus bisa dimulai dengan data dummy mengikuti skema Bagian 4, tanpa menunggu `rancangan-custom-exporter-supabase.md` benar-benar mengalirkan data asli.

---

## Konteks: Kenapa Ada Dua Dashboard, Bukan Satu

Pekerjaan ini menghasilkan dua permukaan yang berbeda secara teknis tapi sengaja dijaga isinya identik: Grafana untuk kebutuhan debugging pribadi (mengonsumsi Jaeger dan Prometheus langsung, akses privat), dan dashboard Next.js untuk publikasi ke siapa saja sebagai bukti sistem berjalan dan diawasi (mengonsumsi Supabase). Pemisahan ini murni alasan operasional — Grafana Cloud versi gratis tidak menyediakan fitur publish dashboard ke publik, dan membagikan kredensial akun Grafana pribadi bukan pilihan yang wajar — bukan karena ada perbedaan tingkat kerahasiaan data antara keduanya. Karena itu, pekerjaan ini secara sengaja tidak meringkas atau menyaring data untuk versi publik; keduanya menampilkan cerita yang sama tentang bagaimana sistem berjalan.

---

## Milestone 5.1 — Membangun Dashboard Grafana untuk Trace dan Metrics

### Lingkup
Menyiapkan Grafana yang terhubung ke Jaeger (sebagai sumber data trace) dan Prometheus (sebagai sumber data metrics) yang sudah disediakan fondasi Collector dari `rancangan-context-decomposition.md`, lalu menyusun panel-panel yang menceritakan kondisi sistem secara menyeluruh: daftar trace per turn dengan kemampuan melihat detail urutan span di dalamnya, latency di tiap layer (agar bottleneck mudah diketahui dari melihat layer mana yang paling lama), distribusi status (berhasil/sebagian/ditolak/gagal), dan frekuensi tiap jenis `error.type` — dengan perhatian khusus pada kemunculan `403`/`404` yang menandakan bug di layer otorisasi, bukan kegagalan wajar biasa.

### Kenapa Ini Jadi Milestone Terpisah
Ini kapabilitas debugging paling dasar yang dibutuhkan begitu layer-layer mulai menghasilkan span sungguhan — layak selesai lebih dulu sebelum dashboard publik dibangun, karena panel privat ini juga jadi rujukan bentuk visual yang perlu ditiru kesetaraannya di Next.js.

### Output
Instance Grafana dengan sumber data Jaeger dan Prometheus terhubung, beserta kumpulan panel yang menampilkan trace individual, agregat latency per layer, distribusi status, dan frekuensi error.type — semuanya bisa diakses dan dibuktikan menampilkan data nyata dari span yang dikirim layer-layer yang sudah berjalan.

### Kriteria Keberhasilan
- Trace dari satu turn percakapan nyata (dicoba dari sistem yang sudah berjalan, bukan data dummy) bisa ditelusuri di Grafana sampai terlihat urutan span dan durasi tiap layer yang dilaluinya.
- Kemunculan `error.type` bertipe `ditolak_otorisasi` atau `gagal_teknis` (dari skenario uji terkontrol) terlihat menonjol dan bisa dibedakan dari sekadar hasil berhasil biasa.

---

## Milestone 5.2 — Membangun Skema Data dan Koneksi Next.js ke Supabase

### Lingkup
Menyiapkan proyek Next.js yang terhubung ke tabel `traces` dan `spans` di Supabase, mengikuti skema yang sudah dikunci di dokumen observability induk (Bagian 4) apa adanya — pekerjaan ini tidak merancang ulang skema tersebut, hanya membangun lapisan query dan tipe data di sisi Next.js yang sesuai dengannya. Karena `rancangan-custom-exporter-supabase.md` mungkin belum selesai mengalirkan data asli saat pekerjaan ini dimulai, bagian ini dibangun dengan kemampuan bekerja dari data contoh yang sengaja dimasukkan manual ke Supabase mengikuti skema yang sama, sehingga pengembangan tampilan bisa berjalan tanpa menunggu.

### Kenapa Ini Jadi Milestone Terpisah
Fondasi teknis (koneksi dan tipe data) perlu berdiri lebih dulu dan stabil sebelum tampilan-tampilan konkret di milestone berikutnya dibangun di atasnya — memisahkan keduanya memudahkan penelusuran kalau nanti ada masalah, apakah dari sisi koneksi/data atau dari sisi tampilan.

### Output
Proyek Next.js dengan koneksi Supabase yang berfungsi, lapisan query yang bisa mengambil trace beserta seluruh span anaknya (menghormati struktur `parent_span_id` yang hierarkis, bukan sekadar daftar datar), dan data contoh di Supabase yang mengikuti skema kontrak untuk keperluan pengembangan sebelum data asli tersedia.

### Kriteria Keberhasilan
- Query dari Next.js terhadap data contoh berhasil mengembalikan satu trace lengkap beserta seluruh span anaknya tersusun sesuai urutan waktu dan hubungan induk-anaknya.
- Struktur data yang diambil sudah dalam bentuk yang siap dipakai komponen tampilan, tidak perlu transformasi tambahan yang rumit di sisi komponen.

---

## Milestone 5.3 — Membangun Tampilan Waterfall Trace dan Daftar Turn

### Lingkup
Membangun dua tampilan inti dashboard publik: daftar trace yang bisa disaring per sesi/turn, dan tampilan waterfall untuk satu trace terpilih yang menggambarkan urutan span secara visual — durasi tiap layer digambar sebagai batang horizontal yang panjangnya sesuai durasi, tersusun sesuai hubungan induk-anak, meniru bentuk yang sudah lebih dulu ada di panel Grafana Milestone 5.1 sebagai rujukan kesetaraan tampilan.

### Kenapa Ini Jadi Milestone Terpisah
Ini jantung dari dashboard publik — kemampuan menelusuri satu trace secara detail adalah nilai inti yang membedakan dashboard ini dari sekadar angka ringkasan, dan layak menjadi fokus tersendiri sebelum menambahkan panel agregat di milestone berikutnya.

### Output
Halaman daftar trace yang bisa disaring, dan halaman detail trace yang menampilkan waterfall visual span-span di dalamnya lengkap dengan nama layer, durasi, dan status masing-masing — dibuktikan bekerja baik dengan data contoh maupun (setelah tersedia) data asli dari `rancangan-custom-exporter-supabase.md`.

### Kriteria Keberhasilan
- Trace dengan banyak span bercabang (skenario uji: turn dengan lebih dari satu atomic intent yang diproses dalam wave berbeda) tergambar dengan hubungan induk-anak yang benar, bukan sekadar daftar datar tanpa struktur.
- Trace yang mengandung span berstatus gagal (`error.type` terisi) menampilkan penanda visual yang jelas berbeda dari span yang berhasil.

---

## Milestone 5.4 — Membangun Panel Agregat dan Metrik Ringkasan

### Lingkup
Melengkapi dashboard publik dengan panel yang menceritakan kondisi sistem secara keseluruhan, bukan hanya per trace individual — jumlah query yang diproses, distribusi status, latency rata-rata dan persentil per layer, serta frekuensi tiap jenis `error.type`, setara dengan yang sudah ada di panel Grafana Milestone 5.1.

### Kenapa Ini Jadi Milestone Terpisah
Panel agregat dan tampilan trace individual (Milestone 5.3) melayani kebutuhan yang berbeda — satu untuk memahami tren keseluruhan, satu untuk menelusuri kejadian spesifik. Keduanya layak dibangun sebagai unit kerja terpisah meski saling melengkapi di halaman yang sama.

### Output
Panel ringkasan yang menampilkan metrik agregat lintas seluruh trace yang tersimpan — jumlah query, tingkat keberhasilan, latency per layer, dan distribusi jenis kegagalan — yang isinya dapat dibandingkan langsung kesetaraannya dengan panel Grafana Milestone 5.1.

### Kriteria Keberhasilan
- Angka ringkasan yang ditampilkan (jumlah query, tingkat keberhasilan) terbukti cocok dengan penghitungan manual terhadap data yang sama di Supabase, tidak ada penyimpangan akibat kesalahan agregasi.
- Kemunculan `error.type` bertipe `ditolak_otorisasi` atau `gagal_teknis` sama-sama terlihat menonjol di dashboard publik ini seperti di Grafana, membuktikan kesetaraan isi yang dijanjikan di awal dokumen ini benar-benar terwujud, bukan sekadar niat.

---

## Catatan Serah Terima ke Pekerjaan Lain

Pekerjaan ini tidak menyerahkan apa pun ke pekerjaan lain — sebagai konsumen akhir dari seluruh rangkaian observability, hasilnya adalah produk yang berdiri sendiri. Namun pekerjaan ini bergantung penuh pada dua pihak: `rancangan-context-decomposition.md` (Milestone 1.1) untuk fondasi Jaeger dan Prometheus yang menjadi sumber data Milestone 5.1, dan `rancangan-custom-exporter-supabase.md` untuk data asli yang mengisi tabel `traces` dan `spans` yang menjadi sumber data Milestone 5.2-5.4. Perubahan skema tabel Supabase oleh pemilik pekerjaan tersebut di kemudian hari berdampak langsung pada lapisan query yang dibangun di Milestone 5.2, dan perlu dikomunikasikan sebelum diubah.
