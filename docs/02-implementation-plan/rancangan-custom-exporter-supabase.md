# Rancangan Implementasi — Custom Exporter Supabase (OTel Collector)

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Custom Exporter Supabase) |
| **Dokumen induk** | `rancangan-observability-ai-chatbot.md` (Bagian 2-4) |
| **Cakupan pekerjaan** | Exporter kustom di dalam OTel Collector yang menyalin span diterima Collector ke tabel `traces` dan `spans` di Supabase, sebagai jalur ekspor kedua paralel dengan jalur Jaeger/Prometheus yang sudah ada |
| **Tidak termasuk** | Konfigurasi dasar Collector dan jalur privat Jaeger/Prometheus (lihat `rancangan-context-decomposition.md`, Milestone 1.1 — pekerjaan ini hanya mengisi slot exporter kedua yang sudah disiapkan di sana, tidak membangun ulang pipeline Collector dari nol); instrumentasi span di kesembilan layer (lihat empat dokumen PIC 1-4); tampilan dashboard yang membaca dari Supabase (lihat `rancangan-observability-dashboard.md`) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic. Setiap milestone mencakup satu lingkup kerja koheren — kalau dipecah lebih jauh ke task teknis, seluruh pecahan itu tetap berada dalam lingkup yang sama. Milestone tidak menentukan tech stack, library, atau arsitektur detail secara spesifik — itu keputusan yang sengaja diserahkan ke saat pengerjaan nyata berlangsung.

Kecuali untuk hal yang sudah dikunci eksplisit di dokumen observability induk. Yang paling mengikat untuk pekerjaan ini: skema tabel `traces` dan `spans` (Bagian 4 dokumen induk) adalah kontrak yang wajib dipetakan persis, bukan direvisi sepihak; dan fallback ke pendekatan sidecar Python (dijelaskan di Catatan Ketidakpastian di bawah) adalah opsi yang sudah disepakati sejak awal, bukan tanda kegagalan bila diambil.

Urutan milestone adalah urutan yang disarankan, bukan kaku.

---

## Kenapa Pekerjaan Ini Dipisah Sebagai Kepemilikan Tersendiri

Pekerjaan ini berbeda sifat secara mendasar dari lima pekerjaan lain di seluruh sistem — satu-satunya yang ditulis dalam bahasa Go (mengikuti keharusan teknis OTel Collector), menyentuh internal arsitektur Collector (receiver-processor-exporter, siklus hidup komponen), dan dikompilasi sebagai binary terpisah, bukan berjalan sebagai bagian dari basis kode Python yang menyatukan seluruh pekerjaan lain. Kompleksitas dan keterampilan yang dibutuhkan berbeda cukup jauh sehingga layak berdiri sebagai kepemilikan tersendiri, bukan dititipkan ke pemilik fondasi Collector (`rancangan-context-decomposition.md`) yang cakupan utamanya adalah logic bahasa, bukan infrastruktur observability tingkat lanjut.

---

## Milestone 6.1 — Membangun Exporter Dasar yang Menulis ke Supabase

### Lingkup
Membangun komponen exporter yang mengimplementasikan interface exporter milik OTel Collector — menerima batch span dari pipeline internal Collector, lalu menuliskannya ke tabel `traces` dan `spans` di Supabase mengikuti pemetaan atribut yang ditentukan Bagian 2 dan skema Bagian 4 dari dokumen observability induk. Pada tahap ini, cukup jalur data paling sederhana yang perlu bekerja — satu span diterima, satu baris tertulis — tanpa dulu memikirkan penanganan kegagalan, retry, atau performa saat volume tinggi (itu Milestone 6.2).

### Kenapa Ini Jadi Milestone Terpisah
Ini fondasi paling dasar sebelum kompleksitas lain (penanganan error, batching) ditambahkan — memisahkan "apakah data bisa sampai sama sekali" dari "apakah data sampai dengan andal" memudahkan penelusuran masalah, karena keduanya adalah pertanyaan yang berbeda.

### Output
Exporter Go yang, setelah dikompilasi bersama Collector (lewat OpenTelemetry Collector Builder atau setara), berhasil menerima span percobaan dan menuliskannya sebagai baris baru di tabel `traces` dan `spans` di Supabase, dengan pemetaan atribut yang sesuai kontrak.

### Kriteria Keberhasilan
- Span percobaan sederhana yang dikirim dari skrip Python ke Collector benar-benar muncul sebagai baris baru di Supabase, dengan seluruh atribut wajib (nama layer, durasi, status) terisi sesuai nilai aslinya.
- Span anak dengan `parent_span_id` yang mengarah ke span induk yang sudah tertulis lebih dulu, tersimpan dengan relasi induk-anak yang benar dan bisa ditelusuri kembali lewat query sederhana.

---

## Milestone 6.2 — Membangun Penanganan Kegagalan dan Keandalan Pengiriman

### Lingkup
Melengkapi exporter dasar hasil Milestone 6.1 dengan penanganan kondisi yang tidak selalu mulus — Supabase yang lambat merespons atau sesaat tidak terjangkau, batch span dalam jumlah besar yang perlu dikirim efisien tanpa membebani baik Collector maupun Supabase, dan mekanisme retry yang wajar ketika penulisan gagal sementara. Tanpa penanganan ini, exporter yang bekerja baik dalam kondisi ideal berisiko diam-diam kehilangan span setiap kali ada gangguan sesaat pada jaringan atau layanan Supabase.

### Kenapa Ini Jadi Milestone Terpisah
Keandalan adalah kebutuhan yang berbeda sifat dari fungsi dasar (Milestone 6.1) — sebuah exporter yang "kadang bekerja" tidak cukup untuk dashboard yang diklaim identik isinya dengan sumber privat; kehilangan span secara diam-diam akan membuat kedua dashboard perlahan menyimpang tanpa disadari.

### Output
Exporter yang sudah dilengkapi mekanisme retry untuk kegagalan penulisan sementara, batching yang efisien untuk volume span yang lebih tinggi, dan pencatatan (log internal Collector, bukan span baru) ketika penulisan ke Supabase benar-benar gagal setelah batas percobaan ulang habis — supaya kehilangan data, jika memang terjadi, setidaknya diketahui dan tidak sepenuhnya senyap.

### Kriteria Keberhasilan
- Simulasi gangguan sesaat (Supabase tidak terjangkau untuk waktu singkat, lalu pulih) menghasilkan span yang akhirnya tetap tertulis lewat mekanisme retry, bukan hilang begitu saja.
- Pengiriman batch span dalam jumlah besar sekaligus (skenario uji: mensimulasikan satu turn dengan banyak wave dan banyak atomic intent, menghasilkan puluhan span sekaligus) berhasil tertulis semuanya tanpa ada yang terlewat atau menyebabkan Collector kehabisan sumber daya.

---

## Catatan Ketidakpastian: Fallback ke Pendekatan Sidecar Python

Pekerjaan ini dipilih dengan kesadaran penuh bahwa kompleksitasnya tinggi untuk lingkup portofolio yang dikerjakan solo — menulis dan memelihara kode Go yang menyentuh internal OTel Collector adalah keterampilan yang berdiri terpisah dari seluruh basis kode Python di lima pekerjaan lain. Keputusan ini diambil secara sadar karena nilai cerita yang dihasilkan (kontribusi ke tingkat internal Collector, bukan sekadar proxy sederhana) dianggap sepadan dengan risikonya.

Jika pekerjaan ini menjadi bottleneck waktu yang tidak kunjung selesai, fallback yang sudah disepakati sejak awal adalah pendekatan sidecar Python — sebuah proses Python terpisah yang menerima salinan OTLP secara paralel dengan Jaeger/Prometheus (Collector cukup dikonfigurasi mengirim ke alamat kedua, tanpa tahu bahwa tujuan itu sebenarnya kode Python biasa), men-decode formatnya, lalu menuliskannya ke Supabase dengan client Python biasa. Pemilihan fallback ini tidak mengubah kontrak span (Bagian 2 dokumen induk) maupun skema tabel Supabase (Bagian 4) sama sekali — perubahan hanya terjadi di sisi teknis bagaimana data berpindah dari Collector ke Supabase, sehingga keputusan pindah jalur ini tidak berdampak pada `rancangan-observability-dashboard.md` yang murni membaca dari Supabase tanpa peduli bagaimana data itu sampai ke sana.

---

## Catatan Serah Terima ke Pekerjaan Lain

Skema tabel `traces` dan `spans` yang diisi pekerjaan ini menjadi sumber data langsung bagi `rancangan-observability-dashboard.md` (Milestone 5.2 dan seterusnya) — perubahan pada pemetaan atribut span ke kolom Supabase, atau perubahan skema tabel itu sendiri, berdampak langsung pada lapisan query yang dibangun pemilik pekerjaan tersebut dan wajib dikomunikasikan sebelum diubah.

Slot exporter kedua yang diisi pekerjaan ini disediakan oleh `rancangan-context-decomposition.md` (Milestone 1.1) di konfigurasi pipeline Collector — perubahan pada cara Collector dikonfigurasi atau dijalankan oleh pemilik fondasi tersebut berpotensi memengaruhi cara exporter ini terpasang, dan sebaliknya, perubahan besar pada exporter ini (termasuk keputusan pindah ke fallback sidecar Python) perlu dikomunikasikan kembali ke pemilik fondasi Collector.
