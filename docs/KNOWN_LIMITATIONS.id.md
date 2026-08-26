# Keterbatasan & Keputusan Terbuka

*[English](KNOWN_LIMITATIONS.md)*

Proyek ini menyimpan catatan kerja untuk setiap keterbatasan yang ditemukan dan setiap keputusan yang sengaja ditunda, sejak hari pertama — [`docs/keputusan-tertunda.md`](keputusan-tertunda.md) (keputusan terbuka, 5 entri aktif) dan [`docs/keterbatasan-diterima.md`](keterbatasan-diterima.md) (keterbatasan diterima, 22 entri termasuk yang sudah selesai). Kedua file itu adalah riwayat lengkap dan otoritatif, ditulis dalam Bahasa Indonesia sebagai catatan kerja internal.

Halaman ini adalah ringkasan terkurasi untuk pembaca luar, berisi item yang masih terbuka dan paling mungkin relevan bagi siapa pun yang mengevaluasi atau mengembangkan lebih lanjut codebase ini — **bukan pengganti** kedua file di atas, yang tetap jadi sumber kebenaran (termasuk konteks lengkap, bukti, dan seluruh item yang sudah ditutup).

Untuk satu item yang levelnya sudah masuk kerentanan keamanan aktif (bukan sekadar keterbatasan desain), lihat **[SECURITY.id.md](../SECURITY.id.md)**.

---

## RBAC & integritas data

### Tabel izin role→domain adalah salinan manual, bukan pembacaan langsung dari produksi

**Masalah.** Proyek ini tidak bisa query langsung tabel `role_permissions` produksi (kredensial itu eksklusif untuk API Lapis 2 milik platform data). Sebagai gantinya, proyek ini menyimpan salinannya sendiri, diseed sekali secara manual dari spesifikasi sumber.
**Kenapa ada.** Segregasi kredensial per pola akses adalah batas arsitektur yang disengaja, bukan kelalaian — memberi Lapis 1 akses baca ke tabel produksi yang sebenarnya tidak ia butuhkan akan memperluas blast radius tanpa manfaat.
**Mitigasi saat ini.** Lapis 2 (`chatbot_api`) tetap menegakkan izin sesungguhnya secara independen apa pun keputusan Lapis 1 — staleness di sini bisa menyebabkan penolakan dini yang keliru (gangguan UX), bukan kebocoran data.
**Apa yang akan menutupnya.** Proses notifikasi (atau, pada akhirnya, sinkronisasi terjadwal) setiap kali matriks izin sumber berubah.

### Parameter API per-view dan threshold kesegaran data masih provisional

**Masalah.** Parameter query persis yang diterima tiap 67 view data tidak pernah dipublikasikan resmi oleh tim platform, sehingga proyek ini menurunkan konvensi terbaik dari nama kolom di katalog data dan mendokumentasikannya sebagai usulan, menunggu rekonsiliasi. Demikian pula, threshold "data basi" 48 jam dipilih sebagai titik awal yang wajar, bukan dikalibrasi terhadap jadwal refresh nyata tiap view.
**Kenapa ada.** Kontrak resmi genuinely belum ada saat ini harus dibangun; sistem sengaja dirancang dengan jalur pemulihan (request yang gagal direvisi dan dicoba ulang) alih-alih terblokir menunggu dependensi eksternal.
**Mitigasi saat ini.** Tidak ada di luar loop revisi/retry yang sudah dibangun dalam penanganan request.
**Apa yang akan menutupnya.** Rekonsiliasi resmi dengan tim platform data; data jadwal refresh per-view begitu tersedia.

---

## Perilaku LLM

### Resolusi rujukan menunjukkan recency bias pada input yang genuinely ambigu

**Masalah.** Saat pertanyaan lanjutan bisa saja merujuk lebih dari satu topik sebelumnya, model yang dipakai untuk deteksi ketergantungan turn dan penulisan ulang pertanyaan kadang default ke topik yang paling baru disebut, meski itu bukan topik yang genuinely koheren untuk dibandingkan.
**Kenapa ada.** Teramati konsisten di dua model berbeda dan dua tugas berbeda — kemungkinan besar kecenderungan umum LLM pada resolusi rujukan ambigu, bukan bug prompt yang bisa diperbaiki dari satu data point.
**Mitigasi saat ini.** Tidak ada yang aktif; mode kegagalannya sempit (hanya kasus multi-kandidat genuinely ambigu) dan seluruh skenario non-ambigu di evaluasi lolos bersih.
**Apa yang akan menutupnya.** Lebih banyak bukti produksi sebelum berinvestasi pada perbaikan prompt bertarget, supaya tidak overfit ke segelintir skenario uji buatan tangan.

### Pengecekan opini-kedua Domain Gate sengaja bias ke arah menandai domain berlebih

**Masalah.** Pengecekan "titik buta" independen yang berjalan setelah klasifikasi domain awal cenderung menambahkan domain yang sebenarnya tidak jelas dibutuhkan saat pertanyaan mengandung kata kunci finansial/temporal dalam konteks yang tidak berkaitan.
**Kenapa ada.** Ini trade-off asimetris yang sengaja dipilih: domain sensitif yang terlewat adalah gap RBAC nyata, sementara domain berlebih hanya menyebabkan penolakan otorisasi yang tidak perlu. Pengecekan ini dituning untuk gagal ke arah yang lebih aman.
**Mitigasi saat ini.** Tidak ada — ini diterima sebagai trade-off yang benar mengingat risiko alternatifnya.
**Apa yang akan menutupnya.** Bukti bahwa over-flagging menyebabkan penolakan keliru yang mengganggu terlalu sering di praktik nyata akan membenarkan pengetatan prompt.

---

## Trade-off level produk

### Narasi yang gagal fact-check diganti total, termasuk bagian yang sebenarnya benar

**Masalah.** Jawaban akhir ke pengguna melewati langkah fact-check independen sebelum dikembalikan. Kalau gagal — bahkan karena satu klaim tak berdasar yang terselip di tengah jawaban yang sebagian besar akurat — SELURUH respons diganti pesan generik "coba lagi", membuang informasi benar yang sebenarnya dikandungnya.
**Kenapa ada.** Keputusan konservatif fase awal untuk versi PERTAMA endpoint HTTP publik: mencegah klaim tak berdasar sampai ke pengguna dinilai lebih penting daripada mempertahankan jawaban yang sebagian benar, sementara strategi yang lebih presisi belum dirancang.
**Mitigasi saat ini.** Respons tetap menyertakan catatan bahwa verifikasi gagal beserta alasannya, jadi kegagalannya tidak pernah disembunyikan diam-diam.
**Apa yang akan menutupnya.** Bukti bahwa ini cukup sering terjadi di praktik nyata untuk sepadan merancang perbaikan yang lebih bertarget (mis. meregenerasi hanya bagian yang tak berdasar).

### Sejumlah pengecekan kualitas prompt gagal intermiten, gate CI tetap memblokir semuanya

**Masalah.** Evaluasi berkelanjutan atas prompt proyek ini (17 suite test otomatis) memunculkan 9 skenario gagal pra-existing di 8 suite saat pertama kali disambungkan ke CI sebagai gate wajib 100% lolos — termasuk dua yang sensitif RBAC. Ini perilaku prompt nyata pra-existing, bukan regresi yang disebabkan menyalakan gate-nya.
**Kenapa ada.** Keputusan sadar mempertahankan ambang 100% alih-alih membuat pengecualian, menerima bahwa PR yang tidak terkait bisa sesekali terblokir salah satu skenario yang sudah dikenal flaky ini sampai masing-masing diinvestigasi dan diperbaiki satu per satu.
**Mitigasi saat ini.** Tidak ada yang otomatis; kegagalan ditriase manual per kejadian.
**Apa yang akan menutupnya.** Investigasi dan perbaikan kesembilan skenario satu per satu (dua yang sensitif RBAC ternyata tumpang tindih dengan temuan keamanan di atas, bukan sekadar flakiness biasa).

---

## Infrastruktur & operasional

### Panggilan LLM kadang hang tanpa batas tanpa exception apa pun

**Masalah.** Panggilan ke provider LLM, di segelintir kejadian sepanjang riwayat proyek ini, hang berkepanjangan (puluhan menit) tanpa error, tanpa timeout terpicu, dan tanpa penyebab yang bisa dibedakan — diisolasi sampai level `curl` mentah langsung ke endpoint completions provider, menyingkirkan kemungkinan HTTP client/SDK codebase ini sebagai penyebab.
**Kenapa ada.** Semua komponen yang diisolasi berperilaku normal saat diuji sendiri-sendiri; ini tampak seperti karakteristik intermiten infrastruktur provider atau jalur jaringan, di luar kendali proyek ini.
**Mitigasi saat ini.** Timeout eksplisit sisi klien + retry terbatas, dan pemantauan trace aktif selama operasi panjang alih-alih menunggu buta.
**Apa yang akan menutupnya.** Investigasi level jaringan lebih dalam (packet capture) kalau ini mulai memengaruhi Kriteria Keberhasilan formal, bukan sekadar gangguan test sesekali.

### Histogram latency dashboard observability belum mencakup rentang latency nyata proyek

**Masalah.** Bucket histogram bawaan pipeline metrik mencakup kira-kira 2ms-15 detik, tapi span nyata di sistem ini berkisar dari pengecekan deterministik <5ms sampai panggilan LLM reasoning 90+ detik — jadi sebagian panel "latency per layer" tampil kosong/`NaN` alih-alih nilai bermakna.
**Kenapa ada.** Menuning batas bucket custom lintas lebih dari lima order-of-magnitude butuh data latency skala produksi nyata untuk hasil yang baik; tujuan inti panel (menunjukkan langkah LLM mendominasi latency) sudah tercapai dengan default.
**Mitigasi saat ini.** Tidak ada; panel dipakai apa adanya, dengan gap ini dinyatakan eksplisit di deskripsi panelnya sendiri.
**Apa yang akan menutupnya.** Volume traffic nyata yang cukup untuk mengkalibrasi batas bucket custom dari data asli, bukan tebakan.

---

*Terakhir dikurasi bersamaan rilis v1.0.0. Kalau Anda perlu memastikan apakah suatu keterbatasan masih berlaku, cek langsung entri bertanggal di [`keputusan-tertunda.md`](keputusan-tertunda.md) / [`keterbatasan-diterima.md`](keterbatasan-diterima.md) — halaman ini merangkum satu titik waktu, kedua file itu yang selalu dijaga tetap terkini.*
