# Rancangan Implementasi — Context & Decomposition + Fondasi Bersama

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Context & Decomposition) |
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` (Bagian 3-4), `rancangan-observability-ai-chatbot.md` (Bagian 1-3) |
| **Cakupan pekerjaan** | Input Layer, Context Resolution (Langkah 2, 3a, 3b, 7), Decomposition (Langkah 4-6), plus penyiapan OTel Collector sebagai fondasi observability bersama |
| **Tidak termasuk** | Domain Gate dan Verification Gate (lihat `rancangan-rbac-authorization.md`); pemilihan `view_name` dan penyusunan request ke `chatbot_api` (lihat `rancangan-retrieval-query.md`); pemanggilan `chatbot_api` dan penyusunan narasi jawaban (lihat `rancangan-execution-interpretation.md`); custom exporter Supabase (lihat `rancangan-custom-exporter-supabase.md`) — PIC ini hanya menyediakan *endpoint* OTLP Collector, bukan tujuan ekspor lanjutannya; mekanisme deployment/hosting produksi sistem secara keseluruhan (dibahas terpisah setelah tiap PIC terbukti bekerja sebagai kode lokal) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic. Setiap milestone mencakup satu lingkup kerja koheren — kalau dipecah lebih jauh ke task teknis, seluruh pecahan itu tetap berada dalam lingkup yang sama. Milestone **tidak** menentukan tech stack, library, atau arsitektur detail secara spesifik — itu keputusan yang sengaja diserahkan ke saat pengerjaan nyata berlangsung, karena kondisi lapangan sering menuntut penyesuaian yang belum terlihat saat desain arsitektur awal dibuat.

**Kecuali** untuk hal yang sudah dikunci eksplisit di dua dokumen induk (arsitektur 9-layer dan observability) — itu bukan pilihan bebas implementasi, melainkan kontrak yang wajib diikuti karena PIC lain bergantung padanya. Tiap milestone di bawah menyebutkan eksplisit mana yang kontrak wajib dan mana yang keputusan bebas.

Urutan milestone adalah urutan yang disarankan, bukan kaku — temuan di satu milestone wajar memengaruhi milestone sesudahnya. Sengaja tidak ada milestone "deployment" di paling awal — sistem perlu terbukti bekerja sebagai kode yang bisa dipanggil dan diuji secara lokal terlebih dulu, sebelum pertanyaan "bagaimana ini dijalankan sebagai layanan" jadi relevan.

---

## Milestone 1.1 — Penyiapan OTel Collector sebagai Fondasi Observability Bersama

### Lingkup
Menyiapkan satu proses OTel Collector yang berjalan lokal (mis. lewat Docker), berfungsi sebagai titik penerima tunggal untuk seluruh span yang akan dikirim oleh kesembilan layer, dari PIC manapun. Ini murni penyediaan wadah penerima — tidak menyentuh logic AI Chatbot sama sekali, dan tidak memerlukan sistem 9 layer sudah berjalan untuk bisa diuji. Termasuk mengonfigurasi pipeline Collector agar span yang masuk diteruskan (fan-out) ke dua jalur sesuai kontrak observability yang sudah dikunci: jalur privat (Jaeger untuk trace, Prometheus untuk metrics, keduanya untuk kebutuhan debugging pemilik project sendiri) yang sudah aktif penuh, dan satu slot kosong di konfigurasi untuk jalur publik yang nanti diisi implementasi PIC 6 — pekerjaan ini menyediakan tempatnya, bukan mengisinya. Pekerjaan ini juga mendokumentasikan konvensi dasar (endpoint yang dipakai, cara menjalankan Collector, cara memverifikasi ia menerima data) supaya PIC 2-4 bisa mengarahkan instrumentasi mereka ke titik yang sama tanpa perlu menebak-nebak. Termasuk secara khusus mengunci versi konvensi atribut GenAI (`gen_ai.*`) yang jadi acuan seluruh instrumentasi — konvensi ini masih berstatus pre-stable dan bisa berubah nama atributnya di rilis mendatang, sehingga versi yang dipakai perlu dicatat eksplisit di kode (bukan hanya disebut di dokumen), supaya PIC lain tahu persis versi mana yang harus diikuti dan perubahan di masa depan bisa ditelusuri dampaknya.

### Kenapa Ini Jadi Milestone Terpisah
Ini prasyarat infrastruktur murni yang perlu ada sebelum milestone manapun di pekerjaan ini — atau pekerjaan PIC lain — bisa benar-benar mengirim span dan melihat hasilnya. Dipisah secara sadar dari logic Context Resolution/Decomposition supaya keputusan platform (bagaimana Collector dikonfigurasi) tidak bercampur dengan keputusan konten (bagaimana Context Resolution bekerja) — dua jenis keputusan yang idealnya diuji dan divalidasi secara terpisah.

### Output
Sebuah Collector yang benar-benar berjalan dan bisa dibuktikan menerima data — dicoba dengan mengirim span percobaan sederhana dari skrip Python singkat dan melihatnya muncul di Jaeger. Konfigurasi pipeline Collector (file YAML atau setara) yang sudah punya dua jalur ekspor sesuai kontrak, satu aktif satu masih kosong menunggu PIC 6. Catatan singkat (bisa berupa README) yang menjelaskan ke PIC lain: endpoint mana yang dituju, bagaimana cara memverifikasi span mereka benar-benar sampai.

### Kriteria Keberhasilan
- Span percobaan sederhana (dummy, dibuat khusus untuk uji coba ini) berhasil dikirim dan terlihat di Jaeger dengan atribut yang benar.
- Setidaknya satu PIC lain (diverifikasi lewat percobaan nyata, bukan asumsi) berhasil mengarahkan instrumentasinya ke Collector yang sama dan span mereka juga muncul, membuktikan fondasi ini benar-benar bisa dipakai bersama tanpa perlu instance terpisah.
- Versi konvensi atribut GenAI yang dipakai tercatat eksplisit dan bisa ditemukan langsung di kode (bukan hanya di dokumen ini), sehingga siapa pun yang membaca kode PIC lain tahu persis versi konvensi mana yang harus diikuti.

---

## Milestone 1.2 — Membangun Input Layer

### Lingkup
Membangun titik masuk pertama sistem: menerima payload dari frontend untuk satu turn percakapan, dan memastikan bentuknya benar sebelum diteruskan ke logic apa pun setelahnya. Payload yang diterima berisi identitas sesi (`session_id`, `turn_index`), identitas pemanggil (`role_title`, `employee_id`), teks pertanyaan turn ini, dan — khusus bila ini bukan turn pertama dalam sesi — teks beserta jawaban dari turn sebelumnya, sesuai bentuk yang sudah disepakati di dokumen arsitektur. Pekerjaan ini murni validasi mekanis: memeriksa field wajib benar-benar ada dan berformat benar, tanpa melibatkan pemanggilan model AI sama sekali — ini kontrak yang disengaja, karena seluruh layer di belakangnya berasumsi kegagalan di titik ini selalu karena alasan struktural yang jelas, bukan karena kesalahan pemahaman makna.

### Kenapa Ini Jadi Milestone Terpisah
Ini satu-satunya titik di mana kekurangan atau kesalahan bentuk data dari frontend bisa ditangkap sedini mungkin, dengan pesan yang jelas menyebutkan apa yang salah — jauh lebih mudah dilacak dibanding membiarkan payload yang cacat merambat masuk dan baru gagal secara membingungkan di tengah pipeline, jauh dari sumber masalah sebenarnya.

### Output
Sebuah fungsi/endpoint yang menerima payload mentah dan mengembalikan salah satu dari dua hasil: payload yang sudah divalidasi dan siap diteruskan, atau penolakan dengan pesan yang menyebut secara spesifik field mana yang bermasalah dan kenapa. Span `input.validate` yang ter-emit ke Collector sesuai kontrak observability, mencatat identitas sesi dan turn yang sedang diproses.

### Kriteria Keberhasilan
- Payload dengan salah satu field wajib hilang (dicoba untuk tiap field secara bergantian) selalu ditolak dengan pesan yang menyebut field spesifik itu, bukan pesan generik seperti "payload tidak valid".
- Payload yang benar pada `turn_index = 1` (tanpa histori sama sekali) dan pada `turn_index > 1` (dengan histori turn sebelumnya turut disertakan) sama-sama diterima dan diteruskan dengan benar, membuktikan validasi menangani kedua kasus tanpa memperlakukan salah satunya sebagai kondisi khusus yang terlewat.

---

## Milestone 1.3 — Membangun Pemetaan Ketergantungan Turn

### Lingkup
Membangun kemampuan sistem untuk mengenali apakah pertanyaan di turn terakhir sebenarnya bergantung pada sesuatu yang sudah dibahas sebelumnya dalam sesi yang sama — dan kalau iya, turn mana persisnya yang dirujuk. Ketergantungan ini tidak selalu ke turn yang tepat sebelumnya; seorang user bisa saja, di turn ketujuh, tiba-tiba merujuk balik ke sesuatu yang ditanyakan di turn ketiga, dan sistem perlu bisa menangkap itu juga, bukan hanya memeriksa satu turn ke belakang. Pekerjaan ini secara sengaja **tidak** berusaha menentukan atomic intent spesifik mana yang dirujuk — di titik ini, sistem belum pernah membaca isi session memory sama sekali, sehingga memaksa keluaran berupa ID yang presisi hanya akan membuka risiko sistem "mengarang" rujukan yang sebenarnya tidak ada. Keluaran yang diminta cukup sesederhana referensi ke sesi dan nomor turn yang dirujuk.

### Kenapa Ini Jadi Milestone Terpisah
Keputusan di titik ini memicu dua jalur kerja berikutnya yang sifatnya sangat berbeda (Milestone 1.4 dan 1.5) dan berjalan paralel — layak diuji dan divalidasi sebagai satu keputusan yang berdiri sendiri sebelum kedua jalur itu mulai bekerja berdasarkan hasilnya.

### Output
Sebuah mekanisme (satu pemanggilan model AI) yang membaca teks turn terakhir beserta ringkasan/konteks percakapan sebelumnya yang tersedia di payload, lalu menghasilkan: penanda apakah turn ini bergantung ke turn lain, dan jika ya, referensi eksplisit berupa nomor turn yang dirujuk. Span `chat` yang ter-emit sesuai kontrak observability, mencatat model yang dipakai dan jumlah token.

### Kriteria Keberhasilan
- Kalimat dengan rujukan eksplisit ke turn sebelumnya (skenario uji: "bandingkan dengan bulan lalu", merujuk sesuatu yang memang sudah dibahas beberapa turn sebelumnya) menghasilkan referensi turn yang benar.
- Kalimat yang sepenuhnya berdiri sendiri tanpa rujukan apa pun ke percakapan sebelumnya menghasilkan penanda "tidak bergantung", tanpa memaksakan rujukan yang sebenarnya tidak ada.
- Kalimat yang merujuk balik ke turn yang bukan tepat sebelumnya (skenario uji: turn ketujuh merujuk turn ketiga, dengan beberapa turn lain di antaranya membahas topik berbeda) tetap terdeteksi dan diarahkan ke turn yang benar, bukan salah tangkap ke turn terdekat.

---

## Milestone 1.4 — Membangun Penulisan Ulang Pertanyaan Jadi Mandiri (berjalan paralel dengan Milestone 1.5)

### Lingkup
Membangun kemampuan menulis ulang teks turn terakhir menjadi kalimat yang bisa dipahami sepenuhnya berdiri sendiri, tanpa perlu tahu apa-apa soal percakapan sebelumnya untuk memahaminya — segala bentuk elipsis atau koreferensi bahasa sehari-hari ("dibanding itu", "yang tadi", "sama seperti sebelumnya") diubah menjadi penyebutan eksplisit terhadap entitas yang dimaksud. Pekerjaan ini secara sengaja **tidak peduli** apakah nanti nilai dari entitas yang disebutkan itu sudah pernah dihitung sebelumnya atau perlu dihitung baru — itu murni tugas linguistik yang berdiri sendiri, dipisahkan secara sadar dari urusan "apakah datanya sudah tersedia" yang jadi tanggung jawab Milestone 1.5 dan 1.7.

### Kenapa Ini Jadi Milestone Terpisah
Berjalan paralel dengan Milestone 1.5, bukan berurutan — keduanya benar-benar independen satu sama lain dalam cara kerjanya, dan baru bertemu belakangan di Milestone 1.7. Memisahkannya sebagai milestone sendiri memungkinkan keduanya diuji dan divalidasi tanpa saling bergantung.

### Output
Mekanisme (satu pemanggilan model AI) yang menerima teks turn terakhir beserta konteks percakapan yang relevan, menghasilkan satu kalimat pertanyaan yang utuh dan bisa dipahami tanpa konteks tambahan apa pun. Span `chat` ter-emit sesuai kontrak observability.

### Kriteria Keberhasilan
- Kalimat yang mengandung elipsis/koreferensi (skenario uji: "bandingkan dengan occupancy satu tahun sebelumnya", di mana "satu tahun sebelumnya" hanya bermakna jika tahu bulan/tahun yang dibahas di turn sebelumnya) menghasilkan kalimat mandiri yang menyebutkan bulan dan tahun secara eksplisit.
- Kalimat yang sudah mandiri sejak awal (tidak mengandung rujukan apa pun) diteruskan tanpa perubahan makna yang tidak perlu.

---

## Milestone 1.5 — Membangun Penarikan Data dari Session Memory (berjalan paralel dengan Milestone 1.4)

### Lingkup
Membangun mekanisme yang, berbekal referensi sesi dan nomor turn hasil Milestone 1.3, mengambil seluruh atomic intent beserta paket data lengkapnya (nilai hasil, status, catatan interpretasi — sesuai skema paket Session Memory yang sudah dikunci di dokumen arsitektur) dari turn yang dirujuk. Pekerjaan ini murni pengambilan data terstruktur — tidak melibatkan pemanggilan model AI sama sekali. Hasil yang diambil di sini **ditahan dulu**, tidak digabungkan ke jalur manapun sampai titik pertemuan di Milestone 1.7 — mencegah data yang belum tentu relevan ikut "menumpang" ke langkah-langkah lain yang sebenarnya tidak membutuhkannya.

### Kenapa Ini Jadi Milestone Terpisah
Sifat kerjanya sangat berbeda dari Milestone 1.4 — satu murni pengambilan data dari penyimpanan, satu murni generasi bahasa oleh model AI. Memisahkan keduanya memastikan masing-masing bisa gagal atau diperbaiki tanpa saling memengaruhi satu sama lain.

### Output
Mekanisme penyimpanan dan pengambilan Session Memory yang bisa dipanggil dengan referensi sesi dan turn, mengembalikan paket data lengkap sesuai skema yang sudah dikunci di dokumen arsitektur. Bentuk teknis penyimpanan (database apa yang dipakai, bagaimana strukturnya persis) adalah keputusan implementasi bebas — yang menjadi kontrak wajib hanyalah bentuk paket data yang keluar dan masuk. Span `memory.retrieve` ter-emit sesuai kontrak observability.

### Kriteria Keberhasilan
- Referensi ke turn yang memang pernah dieksekusi dan tersimpan mengembalikan paket data yang isinya persis sama dengan yang tersimpan sebelumnya (nilai, status, catatan interpretasi — tidak ada yang hilang atau berubah dalam proses pengambilan).
- Referensi ke turn yang datanya kosong atau belum pernah ada tidak menyebabkan kegagalan sistem — cukup mengembalikan hasil kosong yang bisa ditangani dengan wajar oleh langkah berikutnya.

---

## Milestone 1.6 — Membangun Decomposition (Klasifikasi, Pemecahan, Verifikasi)

### Lingkup
Membangun tiga langkah berurutan yang mengubah kalimat mandiri hasil Milestone 1.4 menjadi struktur kebutuhan yang jelas: pertama menentukan apakah pertanyaan ini kebutuhan tunggal, majemuk yang saling independen, atau majemuk yang saling bergantung; kedua, bila majemuk, memecahnya menjadi daftar kebutuhan atomik lengkap dengan relasi antar-kebutuhan dan label bentuk jawaban yang diharapkan (nilai tunggal, tren, perbandingan, peringkat, atau komposisi); ketiga, memverifikasi hasil pemecahan itu secara independen — tanpa melihat proses berpikir langkah kedua — untuk menangkap kekeliruan yang mungkin terlewat. Ketiga langkah ini secara sengaja tidak menyentuh domain data atau RBAC sama sekali (itu sepenuhnya cakupan `rancangan-rbac-authorization.md`), dan juga tidak peduli apakah kalimat yang diterimanya mengandung rujukan yang sudah atau belum ter-resolve ke session memory — itu baru jadi perhatian di Milestone 1.7.

### Kenapa Ini Jadi Milestone Terpisah
Ketiga langkah ini membentuk satu lingkup kerja yang koheren — memahami struktur kebutuhan murni dari bahasa — yang berbeda sifatnya baik dari Milestone 1.3-1.5 (soal ketergantungan lintas-turn) maupun Milestone 1.7 (soal pencocokan ke memory).

### Output
Tiga mekanisme berurutan (tiga pemanggilan model AI terpisah, dengan langkah verifikasi yang benar-benar independen dari proses berpikir langkah pemecahan) yang bersama-sama mengubah satu kalimat pertanyaan menjadi daftar kebutuhan atomik terstruktur, masing-masing dengan relasi dan label bentuk jawaban yang jelas. Span `chat` (tiga kali) ter-emit sesuai kontrak observability, termasuk atribut jumlah kebutuhan yang dihasilkan dan jenis relasi antar-kebutuhan.

### Kriteria Keberhasilan
- Pertanyaan majemuk yang saling bergantung (skenario uji: "bandingkan X dengan Y", di mana Y perlu diketahui dulu sebelum perbandingan bisa dilakukan) menghasilkan lebih dari satu kebutuhan atomik dengan relasi ketergantungan yang benar antara keduanya.
- Langkah verifikasi terbukti mampu menangkap setidaknya satu kasus pemecahan yang sengaja dibuat keliru dalam pengujian terkontrol — bukti bahwa verifikasi benar-benar menilai ulang secara independen, bukan sekadar mengulangi atau membenarkan hasil langkah sebelumnya.

---

## Milestone 1.7 — Membangun Pencocokan Atomic Intent terhadap Data Session Memory

### Lingkup
Membangun titik pertemuan antara dua jalur yang selama ini berjalan paralel: daftar kebutuhan atomik terstruktur hasil Milestone 1.6, dan paket data yang sudah ditarik (namun ditahan) dari Milestone 1.5. Untuk setiap kebutuhan atomik, pekerjaan ini menentukan apakah kebutuhan tersebut sebenarnya sudah punya jawabannya di antara data yang ditarik tadi — kalau cocok, kebutuhan itu ditandai selesai dan nilainya langsung dibawa maju ke Interpretation tanpa perlu dieksekusi ulang; kalau tidak ada yang cocok, kebutuhan itu ditandai perlu eksekusi baru dan diteruskan ke Domain Gate. Untuk atomic intent yang cocok dan diambil dari memory, pekerjaan ini juga menyimpan ulang paketnya sebagai bagian arsip turn yang sedang berjalan (dengan penanda sumber "session_memory (turn N)" tetap dipertahankan apa adanya) — bukan hanya "dipinjam" sesaat lalu dilupakan begitu turn ini selesai. Tanpa langkah ini, turn-turn berikutnya yang merujuk balik ke turn saat ini (bukan ke turn asal datanya) berisiko tidak menemukan apa-apa, padahal secara percakapan jawaban itu memang bagian dari apa yang disampaikan di turn ini.

### Kenapa Ini Jadi Milestone Terpisah
Titik pertemuan dua jalur yang berjalan paralel sejak Milestone 1.3 — layak berdiri sebagai satu langkah kerja tersendiri, terutama karena mekanisme pencocokannya sendiri (apakah lewat penilaian kemiripan makna oleh model AI, atau lewat pencocokan aturan yang dibantu struktur tambahan dari Milestone 1.3) belum diputuskan final di dokumen arsitektur — keputusan itu memang sengaja ditunda sampai ada bukti nyata dari percobaan implementasi, bukan diputuskan di atas kertas.

### Output
Mekanisme pencocokan yang menghasilkan, untuk setiap kebutuhan atomik, salah satu dari dua label: "selesai" (disertai nilai hasil yang diambil dari memory, dan paketnya disimpan ulang sebagai bagian arsip turn ini) atau "perlu eksekusi" (diteruskan tanpa nilai apa pun ke Domain Gate). Bentuk teknis pencocokan ini — pemanggilan model AI untuk menilai kemiripan makna, atau pendekatan berbasis aturan — adalah keputusan implementasi yang ditentukan saat pengerjaan, berdasarkan seberapa akurat masing-masing pendekatan terbukti bekerja terhadap kasus nyata.

### Kriteria Keberhasilan
- Kebutuhan atomik yang jelas merujuk hasil yang sudah dieksekusi di turn sebelumnya (skenario uji: "occupancy April 2026" yang memang sudah dihitung dan tersimpan, lalu dirujuk ulang di turn berikutnya) berhasil dicocokkan dengan benar dan tidak dieksekusi ulang.
- Kebutuhan atomik yang benar-benar baru (belum pernah muncul di sesi ini sama sekali) tidak pernah tercocokkan secara keliru ke data lama manapun — tidak ada kasus di mana sistem "memaksakan" kecocokan yang sebenarnya tidak ada.
- Paket yang diambil dari memory dan disimpan ulang sebagai arsip turn ini bisa ditarik kembali oleh turn berikutnya yang merujuk balik ke turn saat ini (skenario uji: turn ketujuh merujuk hasil turn kelima, di mana hasil itu sendiri sebenarnya berasal dari turn ketiga) — bukan hanya bisa ditemukan lewat turn asal datanya.

---

## Catatan Ketidakpastian: Mekanisme Milestone 1.7

Berbeda dari milestone lain di dokumen ini, mekanisme pencocokan di Milestone 1.7 belum ditentukan sebagai kontrak pasti di dokumen arsitektur induk — statusnya eksplisit ditandai "kerangka awal". Ini bukan kelalaian dokumentasi, melainkan pengakuan jujur bahwa keputusan antara pendekatan berbasis model AI atau berbasis aturan untuk langkah ini membutuhkan bukti empiris (seberapa akurat masing-masing pendekatan terhadap kasus nyata) yang baru tersedia saat implementasi dan pengujian benar-benar berlangsung — bukan sesuatu yang bisa diputuskan dengan yakin di atas kertas sebelum ada kode yang berjalan.

---

## Catatan Serah Terima ke Pekerjaan Lain

Fondasi Collector yang disiapkan di Milestone 1.1 menjadi dasar bersama yang diperluas oleh `rancangan-rbac-authorization.md`, `rancangan-retrieval-query.md`, dan `rancangan-execution-interpretation.md` — masing-masing menambahkan instrumentasi layer mereka ke endpoint OTLP yang sama, bukan membangun instance Collector terpisah. Konvensi yang didokumentasikan di Milestone 1.1 perlu diikuti konsisten oleh ketiganya. `rancangan-custom-exporter-supabase.md` (PIC 6) bergantung pada slot exporter kedua yang sudah disiapkan di konfigurasi Collector Milestone 1.1 — perubahan struktur pipeline Collector di kemudian hari perlu dikomunikasikan ke PIC 6 karena berdampak langsung pada pekerjaannya.

Output atomic intent berlabel "selesai" atau "perlu eksekusi" dari Milestone 1.7, beserta kalimat mandiri hasil Milestone 1.4, menjadi input langsung bagi Domain Gate (`rancangan-rbac-authorization.md`). Perubahan pada bentuk output ini — skema atomic intent, label bentuk jawaban — berdampak langsung pada pekerjaan tersebut dan perlu dikomunikasikan sebelum diubah.

Skema paket Session Memory yang dibaca oleh Milestone 1.5 juga dipakai untuk menyimpan hasil eksekusi baru oleh `rancangan-execution-interpretation.md` — kedua pekerjaan membaca dan menulis struktur data yang sama, sehingga perubahan skema perlu disepakati bersama, bukan diubah sepihak oleh salah satu pihak saja.
