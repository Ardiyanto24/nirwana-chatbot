# Rancangan Implementasi — Orkestrasi & API Layer

**AI Chatbot RBAC — Nirwana Hospitality Group**

| | |
|---|---|
| **Pemilik pekerjaan** | 1 orang (PIC Orkestrasi & API Layer) |
| **Dokumen induk** | `arsitektur-ai-chatbot-rbac.md` (seluruh bagian — pekerjaan ini menyambungkan apa yang sudah dipisah per layer di dokumen tersebut), `rancangan-observability-ai-chatbot.md` (Bagian 2, khususnya span pembungkus `invoke_agent` yang sampai saat ini belum py pemilik) |
| **Cakupan pekerjaan** | Audit kontrak antar-layer; penyambungan bertahap LLM call di dalam layer yang py lebih dari satu pemanggilan (Level 1); penyambungan bertahap antar-layer mengikuti urutan eksekusi sembilan layer, termasuk percabangan paralel dan wave (Level 2); endpoint HTTP yang menerima payload dari frontend dan mengembalikan response akhir; skema dan penulisan Database Percakapan (riwayat chat untuk kebutuhan aplikasi, terpisah dari Session Memory) |
| **Tidak termasuk** | Logic internal kesembilan layer itu sendiri (sudah dibangun PIC 1-4, tidak dirombak ulang di sini — pekerjaan ini memanggil mekanisme yang sudah ada, bukan menulis ulang); Session Memory (sudah dibangun PIC 1/PIC 4, tujuannya beda dari Database Percakapan — lihat "Konteks" di bawah); observability lintas-layer di luar span pembungkus (sudah tercakup instrumentasi masing-masing PIC 1-4) |
| **Status dokumen** | Rancangan implementasi kerja — bukan dokumen arsitektur. **Ditulis reaktif, setelah PIC 1-6 selesai sampai Milestone 4.5** — lihat "Catatan Ketidakpastian" di bawah untuk konsekuensinya. |

---

## Cara Membaca Dokumen Ini

Berisi **milestone**, bukan task list atomic — mengikuti pola yang sama seperti enam dokumen implementasi lain. Yang berbeda dari keenam dokumen itu: pekerjaan ini py **prasyarat historis**, bukan cuma prasyarat logis — ia baru bisa dimulai setelah kontrak nyata dari PIC 1-6 sudah terbukti bekerja (bukan sekadar terdokumentasi di kertas), karena tugas utamanya adalah menyambungkan implementasi yang sudah ada, bukan merancang dari nol seperti enam dokumen sebelumnya.

Kecuali untuk hal yang sudah dikunci eksplisit di dokumen arsitektur. Yang paling mengikat untuk pekerjaan ini: urutan sembilan layer dan aturan percabangan wave/paralel yang sudah dirancang di `arsitektur-ai-chatbot-rbac.md` — pekerjaan ini **tidak** py wewenang mengubah urutan itu, hanya mewujudkannya jadi kode yang benar-benar mengalirkan data.

---

## Konteks: Kenapa Dokumen Ini Ada, dan Kenapa Ditulis Belakangan

Enam dokumen implementasi sebelumnya (PIC 1-6) masing-masing menulis kontrak "menerima dari layer/pekerjaan sebelumnya" dan "menyerahkan ke layer/pekerjaan berikutnya" — tapi tidak satupun dari keenamnya diberi tanggung jawab eksplisit untuk benar-benar **menghubungkan** kontrak-kontrak itu jadi satu aliran kerja yang hidup dari ujung ke ujung. Akibatnya, sampai Milestone 4.5 selesai, kesembilan layer sudah masing-masing terbukti bekerja **secara terisolasi** (diuji dengan input buatan sendiri per milestone), tapi belum pernah terbukti bekerja **bersama-sama** sebagai satu sistem yang menerima pertanyaan sungguhan dari frontend sampai mengembalikan jawaban. Gap ini juga mencakup dua hal spesifik yang sebelumnya luput: Input Layer (Milestone 1.2) ditulis sebagai fungsi yang menerima parameter, bukan endpoint HTTP yang mendengarkan request sungguhan; dan hasil akhir Interpretation (Milestone 4.4-4.5) berhenti di "narasi siap konsumsi", tanpa mekanisme yang benar-benar mengirimkannya balik ke frontend maupun menyimpannya sebagai riwayat aplikasi.

**Session Memory vs Database Percakapan — dua hal yang mirip tapi tujuannya berbeda, jangan disatukan.** Session Memory (dibangun PIC 1 Milestone 1.5/1.7, ditulis PIC 4 Milestone 4.3) menyimpan paket per **atomic intent**, murni untuk kebutuhan internal AI menjawab "apakah kebutuhan ini sudah pernah dieksekusi" — bentuknya granular dan teknis (nilai hasil, status, catatan interpretasi), tidak dirancang dibaca manusia sebagai riwayat chat. Database Percakapan yang jadi cakupan pekerjaan ini menyimpan per **turn** — pertanyaan user dan jawaban akhir yang sudah jadi narasi, untuk kebutuhan aplikasi (frontend menampilkan riwayat sesi lama, kemungkinan kebutuhan audit/analitik). Keduanya py sumber data yang tumpang tindih (sama-sama berasal dari hasil tiap turn) tapi skema dan tujuan bacanya berbeda — pekerjaan ini **tidak** menggantikan atau merombak Session Memory, hanya menambahkan lapisan penyimpanan baru di sampingnya.

---

## Catatan Ketidakpastian: Dokumen Ini Ditulis Setelah Implementasi Berjalan

Enam dokumen implementasi PIC 1-6 seluruhnya ditulis **sebelum** satu baris kode pun ditulis — kontraknya murni berdasar desain di atas kertas. Dokumen ini berbeda: ditulis **setelah** PIC 1-4 sudah selesai sampai Milestone 4.5, dan PIC 2/3/6 mungkin sudah berjalan sebagian mengikuti urutan paralel yang disarankan. Konsekuensinya, milestone di dokumen ini py risiko yang tidak dimiliki keenam dokumen sebelumnya: **bentuk kontrak aktual dari tiap layer (skema fungsi, nama parameter, cara memanggilnya) mungkin sedikit berbeda dari yang tertulis di dokumen `rancangan-*.md` masing-masing**, karena implementasi nyata kadang menyimpang dari plan (persis seperti yang diantisipasi `logs.md` tiap milestone). Milestone 7.1 di bawah secara eksplisit dimulai dengan langkah audit kontrak nyata — bukan mengasumsikan dokumen lama masih 100% akurat.

---

## Milestone 7.1 — Audit Kontrak Antar-Layer yang Sudah Terimplementasi

### Lingkup
Sebelum menyambungkan apa pun, pekerjaan ini dimulai dengan meninjau ulang kode sungguhan dari kesembilan layer (bukan dokumen `rancangan-*.md` semata) untuk memastikan bentuk input/output aktual tiap layer — nama fungsi yang bisa dipanggil, skema parameter, skema return value — dan mencatat setiap penyimpangan yang ditemukan dari yang tertulis di dokumen desain masing-masing PIC. Ini langkah yang tidak dibutuhkan enam dokumen lain (karena mereka menulis kontrak untuk kode yang belum ada), tapi wajib di sini karena kode sungguhan sudah ada dan mungkin sudah menyimpang dari rencana awal selama implementasi berjalan.

### Kenapa Ini Jadi Milestone Terpisah
Menyambungkan layer di atas asumsi yang keliru soal bentuk kontraknya akan menghasilkan kegagalan integrasi yang sulit dilacak sumbernya — lebih murah menemukan ketidaksesuaian di titik ini, sebelum kode penyambung ditulis, daripada menemukannya belakangan saat penyambungan sudah gagal.

### Output
Dokumen audit singkat (bisa jadi bagian `decisions.md` milestone ini) yang mendaftar tiap unit kerja beserta kontrak aktualnya dan penyimpangan dari dokumen desain (jika ada) — jadi rujukan tunggal yang dipakai seluruh milestone berikutnya di dokumen ini.

### Kriteria Keberhasilan
- Setiap satu dari sembilan layer sudah py setidaknya satu panggilan percobaan nyata (bukan cuma baca kode) yang membuktikan bentuk kontraknya sesuai yang dicatat di dokumen audit.
- Penyimpangan yang ditemukan (jika ada) dicatat eksplisit dengan rujukan ke milestone/PIC asalnya, bukan didiamkan atau diperbaiki diam-diam tanpa jejak.

---

## Level 1 — Menyambungkan LLM Call di Dalam Satu Layer

**Prinsip pengerjaan:** empat unit kerja di bawah adalah satu-satunya yang py lebih dari satu pemanggilan LLM berurutan secara internal (dikonfirmasi dari kontrak span observability — unit kerja lain cuma satu pemanggilan LLM atau sepenuhnya non-LLM, sehingga otomatis "tersambung" tanpa milestone terpisah). **Seluruh empat milestone Level 1 wajib selesai dan stabil, satu per satu, sebelum Level 2 (sambung antar-layer) dimulai sama sekali** — jangan mulai Level 2 dengan asumsi salah satu Level 1 "kemungkinan besar akan beres", karena tujuan pemisahan level ini justru mencegah kegagalan menumpuk dan sulit dilacak sumbernya.

Urutan pengerjaan antar-keempatnya boleh fleksibel (tidak saling bergantung satu sama lain) — kerjakan sesuai kenyamanan, tapi seluruhnya wajib tuntas sebelum Milestone 7.6 (Level 2 pertama) dimulai.

### Milestone 7.2 — Menyambungkan Decomposition (Klasifikasi → Pemecahan → Verifikasi)

**Lingkup.** Menyambungkan tiga pemanggilan LLM berurutan yang membentuk Decomposition (Milestone 1.6 di `rancangan-context-decomposition.md`) jadi satu alur yang benar-benar mengalirkan output satu langkah sebagai input langkah berikutnya — output Klasifikasi jadi input Pemecahan, output Pemecahan (bukan proses berpikirnya) jadi input Verifikasi. Sebelumnya, ketiga langkah ini terbukti bekerja terisolasi (diuji dengan input buatan sendiri per langkah di Milestone 1.6) — pekerjaan ini membuktikan ketiganya bekerja **berurutan** sebagai satu kesatuan.

**Kriteria Keberhasilan:** Satu teks kebutuhan mandiri (hasil Context Resolution, bisa berupa contoh buatan) yang dialirkan lewat ketiga langkah menghasilkan output akhir Verifikasi yang konsisten dengan Kriteria Keberhasilan asli Milestone 1.6 — dibuktikan dengan kasus kebutuhan majemuk-bergantung yang benar-benar mengalir melalui ketiga langkah tanpa intervensi manual di antaranya.

### Milestone 7.3 — Menyambungkan Domain Gate (Identifikasi → Verifikasi Titik Buta)

**Lingkup.** Menyambungkan dua pemanggilan LLM berurutan Domain Gate (Milestone 2.1 di `rancangan-rbac-authorization.md`) — output Identifikasi Domain jadi input Verifikasi Titik Buta, dengan Verifikasi bekerja independen dari proses berpikir Identifikasi (bukan sekadar menerima kesimpulannya).

**Kriteria Keberhasilan:** Kasus domain "bocor" lewat kolom turunan (skenario uji `gop_margin` yang sudah dipakai Milestone 2.1) berhasil mengalir dari Identifikasi ke Verifikasi dan menghasilkan daftar domain lengkap yang benar, dibuktikan lewat pemanggilan berurutan nyata bukan dua pemanggilan terpisah yang hasilnya digabung manual.

### Milestone 7.4 — Menyambungkan Query Engine (Susun Request → Verifikasi Bentuk Request)

**Lingkup.** Menyambungkan dua pemanggilan LLM berurutan Query Engine (Milestone 3.4-3.5 di `rancangan-retrieval-query.md`) — output Penyusunan Request jadi input Verifikasi Bentuk Request, dengan Verifikasi independen dari proses berpikir penyusunan.

**Kriteria Keberhasilan:** Request yang sengaja dibuat tidak sesuai hasil Retriever (skenario uji yang sudah dipakai Milestone 3.5) berhasil ditangkap saat mengalir dari langkah Susun ke langkah Verifikasi secara berurutan nyata, bukan diuji dengan input Verifikasi yang disusun manual terpisah dari output Susun.

### Milestone 7.5 — Menyambungkan Interpretation (Narasi → Verifikasi Kesetiaan Data)

**Lingkup.** Menyambungkan dua pemanggilan LLM berurutan Interpretation (Milestone 4.4-4.5 di `rancangan-execution-interpretation.md`) — output Penyusunan Narasi jadi input Verifikasi Kesetiaan Data, dengan Verifikasi independen dari proses berpikir penyusunan narasi.

**Kriteria Keberhasilan:** Narasi yang sengaja dibuat mengandung klaim sebab-akibat tidak berdasar (skenario uji yang sudah dipakai Milestone 4.5) berhasil ditangkap saat mengalir dari Penyusunan Narasi ke Verifikasi secara berurutan nyata.

---

## Level 2 — Menyambungkan Antar-Layer

**Prinsip pengerjaan:** sebelas milestone di bawah **wajib dikerjakan berurutan sesuai nomornya** — satu sambungan selesai dan teruji dulu, baru pindah ke sambungan berikutnya. Ini beda dari Level 1 (yang boleh fleksibel urutannya) karena Level 2 memang mengikuti urutan eksekusi nyata sistem — sambungan ke-6 secara logis tidak bisa diuji sebelum sambungan ke-1 sampai ke-5 terbukti bekerja, karena setiap sambungan di Level 2 menerima output dari sambungan sebelumnya sebagai bahan ujinya.

### Milestone 7.6 — Sambungan 1: Input Layer → Pemetaan Ketergantungan Turn

**Lingkup.** Payload yang lolos validasi Input Layer (Milestone 1.2) benar-benar diteruskan sebagai input pemanggilan LLM Pemetaan Ketergantungan Turn (Milestone 1.3) — bukan dua fungsi yang masing-masing diuji dengan input buatan terpisah seperti sebelumnya.

**Kriteria Keberhasilan:** Payload turn kedua dalam sesi (mengandung histori turn sebelumnya) yang lolos Input Layer menghasilkan pemanggilan Pemetaan Ketergantungan yang benar-benar menerima histori itu, dibuktikan lewat span yang menunjukkan data mengalir dari satu fungsi ke fungsi lain secara nyata.

### Milestone 7.7 — Sambungan 2: Pemetaan Ketergantungan → Percabangan Paralel (Rewrite + Tarik Memory)

**Lingkup.** Hasil Pemetaan Ketergantungan Turn memicu dua pemanggilan yang benar-benar berjalan paralel — Rewrite (Milestone 1.4) menerima teks turn terakhir, dan (jika ada referensi terdeteksi) Tarik Session Memory (Milestone 1.5) menerima referensi `{session_id, turn_index}` hasil Sambungan 1 — bukan dua mekanisme yang dipanggil manual satu-satu secara berurutan seolah tidak paralel.

**Kriteria Keberhasilan:** Turn dengan referensi terdeteksi memicu kedua jalur berjalan bersamaan (dibuktikan lewat span dengan `parent_span_id` yang sama, menunjukkan keduanya anak dari span yang sama, bukan berurutan); turn tanpa referensi hanya memicu jalur Rewrite, jalur Tarik Memory tidak terpanggil sama sekali (bukan terpanggil lalu menghasilkan kosong).

### Milestone 7.8 — Sambungan 3: Rewrite → Decomposition (hasil Level 1 Milestone 7.2)

**Lingkup.** Output Rewrite (kalimat mandiri) benar-benar jadi input Decomposition yang sudah tersambung internal di Milestone 7.2 — titik ini membuktikan hasil Level 1 sungguhan dipakai di Level 2, bukan cuma teruji terisolasi.

**Kriteria Keberhasilan:** Kalimat hasil Rewrite dari kasus elipsis/koreferensi (skenario uji Milestone 1.4) mengalir ke Decomposition dan menghasilkan pemecahan atomik yang konsisten dengan makna kalimat mandiri itu, bukan makna kalimat asli sebelum di-rewrite.

### Milestone 7.9 — Sambungan 4: (Decomposition + Tarik Memory) → Pencocokan

**Lingkup.** Titik pertemuan pertama — output Decomposition (dari Sambungan 3) dan output Tarik Memory (dari Sambungan 2, jika ada) benar-benar keduanya jadi input Pencocokan (Milestone 1.7), bukan salah satu jalur diuji sendirian seolah jalur lainnya tidak ada.

**Kriteria Keberhasilan:** Skenario uji Milestone 1.7 (atomic intent yang jelas merujuk hasil turn sebelumnya) berhasil dicocokkan dengan benar saat kedua jalur benar-benar berasal dari Sambungan 2 dan 3 sungguhan, bukan data buatan yang disusun manual menyerupai output kedua jalur itu.

### Milestone 7.10 — Sambungan 5: Pencocokan (jalur "perlu eksekusi") → Domain Gate

**Lingkup.** Atomic intent berstatus "perlu eksekusi" hasil Pencocokan benar-benar diteruskan sebagai input Domain Gate yang sudah tersambung internal di Milestone 7.3 — sementara atomic intent berstatus "selesai" ditahan dulu (tidak diteruskan ke sini), memastikan percabangan status berjalan benar.

**Kriteria Keberhasilan:** Turn dengan campuran dua status (sebagian "selesai" dari memory, sebagian "perlu eksekusi") hanya meneruskan yang "perlu eksekusi" ke Domain Gate — dibuktikan lewat span yang menunjukkan Domain Gate hanya menerima jumlah atomic intent yang sesuai, bukan seluruhnya.

### Milestone 7.11 — Sambungan 6: Domain Gate → Retriever

**Lingkup.** Daftar domain yang lolos otorisasi (hasil Domain Gate Sambungan 5) benar-benar jadi input pembatas pencarian Retriever (Milestone 3.1-3.3) — Retriever tidak mencari di luar domain yang sudah diizinkan.

**Kriteria Keberhasilan:** Kebutuhan yang domainnya sebagian ditolak Domain Gate (skenario uji Milestone 2.2) menghasilkan Retriever yang hanya mencari kandidat view dari domain yang lolos, dibuktikan tidak ada kandidat dari domain yang ditolak muncul di hasil pencarian.

### Milestone 7.12 — Sambungan 7: Retriever → Query Engine (hasil Level 1 Milestone 7.4)

**Lingkup.** View yang divalidasi Retriever benar-benar jadi input Query Engine yang sudah tersambung internal di Milestone 7.4.

**Kriteria Keberhasilan:** View hasil Retriever untuk suatu kebutuhan mengalir ke Query Engine dan menghasilkan request dengan `view_name` yang persis sama — dibuktikan lewat span yang menunjukkan kepatuhan sumber ini terjadi dari data nyata, bukan dicocokkan manual.

### Milestone 7.13 — Sambungan 8: Query Engine → Verification Gate

**Lingkup.** Request final hasil Query Engine (Sambungan 7) benar-benar jadi input Verification Gate (Milestone 2.4) — termasuk constraint cakupan-individu yang dicatat Domain Gate (Sambungan 6) benar-benar dicek konsisten di titik ini, bukan diuji dengan constraint buatan terpisah.

**Kriteria Keberhasilan:** Skenario uji constraint cakupan-individu (staff menanyakan performa staf lain) yang mengalir dari Domain Gate asli sampai Verification Gate menghasilkan koreksi paksa yang benar, dibuktikan constraint yang dicek benar-benar berasal dari Domain Gate sungguhan di alur ini, bukan dicatat manual.

### Milestone 7.14 — Sambungan 9: Verification Gate → Execution (termasuk uji wave berulang)

**Lingkup.** Request yang lolos Verification Gate benar-benar dipanggilkan ke Execution (Milestone 4.1-4.2) — termasuk kasus kebutuhan majemuk-bergantung yang memicu lebih dari satu wave, memastikan wave kedua benar-benar menunggu hasil wave pertama sebelum Verification Gate-nya sendiri dipanggil ulang untuk wave kedua itu.

**Kriteria Keberhasilan:** Kebutuhan majemuk-bergantung (skenario "bandingkan X dengan Y" yang butuh Y dulu) menghasilkan dua wave yang benar-benar berurutan lewat Verification Gate dan Execution yang sama, bukan dua panggilan independen yang hasilnya digabung manual di luar alur.

### Milestone 7.15 — Sambungan 10: (Pencocokan jalur "selesai" + Execution) → Interpretation

**Lingkup.** Titik pertemuan kedua — atomic intent berstatus "selesai" (ditahan sejak Sambungan 5) dan hasil Execution (Sambungan 9) benar-benar keduanya jadi input Interpretation yang sudah tersambung internal di Milestone 7.5, dengan skema paket yang identik terlepas dari sumbernya (sesuai kontrak arsitektur).

**Kriteria Keberhasilan:** Turn dengan campuran atomic intent dari kedua sumber menghasilkan narasi yang menyebutkan dengan benar mana yang baru dihitung dan mana yang merujuk turn sebelumnya (kriteria yang sama dipakai Milestone 4.4), sekarang dibuktikan dengan kedua sumber data yang benar-benar berasal dari alur sungguhan.

### Milestone 7.16 — Sambungan 11: Verifikasi Alur Penuh End-to-End

**Lingkup.** Dengan seluruh sepuluh sambungan sebelumnya terbukti bekerja satu-satu, milestone ini menjalankan alur penuh dari Input Layer sampai Interpretation dalam satu pemanggilan tunggal tanpa intervensi manual di titik manapun — pembuktian akhir bahwa integrasi bertahap yang sudah dilakukan benar-benar menyatu jadi satu sistem hidup, bukan sekadar sepuluh pasang sambungan yang masing-masing benar sendiri-sendiri tapi belum tentu benar sebagai satu kesatuan penuh.

**Kriteria Keberhasilan:** Tiga skenario dari kriteria keberhasilan Milestone 7.2 versi awal (kebutuhan tunggal sederhana, kebutuhan dengan wave, turn dengan rujukan lintas-turn) berhasil dijalankan penuh dari ujung ke ujung tanpa pemanggilan manual antar-layer di titik manapun. Span `invoke_agent` ter-emit membungkus seluruh span dari kesembilan layer di dalamnya untuk setiap skenario.

---

## Milestone 7.17 — Membangun Endpoint API

### Lingkup
Membangun endpoint HTTP yang menerima payload dari frontend (sesuai bentuk yang sudah dikunci di dokumen arsitektur — `session_id`, `turn_index`, `role_title`, `employee_id`, teks pertanyaan, dan histori turn sebelumnya bila relevan), meneruskannya lewat rangkaian sambungan Level 2 yang sudah terbukti bekerja penuh di Milestone 7.16, dan mengembalikan response berisi narasi jawaban beserta data visualisasi terstruktur ke frontend. Termasuk penanganan bentuk response untuk kasus kegagalan di titik manapun sepanjang alur (ditolak otorisasi, gagal teknis) — endpoint ini yang menerjemahkan status internal jadi bentuk response HTTP yang wajar diterima klien, bukan meneruskan detail teknis internal mentah-mentah.

### Kenapa Ini Jadi Milestone Terpisah
Endpoint (antarmuka luar, menerima format HTTP) dan orkestrator (alur kontrol internal) adalah dua tanggung jawab berbeda — memisahkannya memungkinkan orkestrator diuji tanpa bergantung pada mekanisme HTTP, dan endpoint bisa berganti bentuk (mis. protokol lain di masa depan) tanpa menyentuh logic orkestrasi.

### Output
Endpoint HTTP yang bisa dipanggil nyata dari klien mana pun (dicoba dengan `curl`/klien HTTP sederhana), menerima payload sesuai kontrak, mengembalikan response terstruktur yang mencakup narasi dan data visualisasi untuk kasus berhasil, serta bentuk error yang informatif namun aman (tidak membocorkan detail internal) untuk kasus gagal.

### Kriteria Keberhasilan
- Payload valid yang dikirim lewat panggilan HTTP nyata menghasilkan response 200 dengan narasi dan data visualisasi yang sesuai dengan hasil yang sama seperti dipanggil langsung lewat rangkaian Level 2 (Milestone 7.16) tanpa lapisan HTTP — membuktikan endpoint tidak mengubah makna hasil, hanya membungkusnya.
- Payload yang memicu penolakan otorisasi di Domain Gate menghasilkan response yang menyampaikan penolakan itu secara jujur ke klien (sesuai prinsip kejujuran L9), bukan error generik yang menyembunyikan alasannya.

---

## Milestone 7.18 — Membangun Database Percakapan

### Lingkup
Merancang skema dan mekanisme penulisan untuk riwayat percakapan yang ditujukan bagi kebutuhan aplikasi — bukan kebutuhan internal AI seperti Session Memory. Skema minimal per turn: identitas sesi, teks pertanyaan user, narasi jawaban akhir, waktu, dan status keseluruhan turn. Penulisan terjadi di akhir rangkaian sambungan Level 2, setelah Interpretation selesai dan sebelum/bersamaan response dikirim lewat endpoint (Milestone 7.17) — sehingga kegagalan penulisan riwayat tidak boleh menggagalkan pengiriman response ke user (dua operasi ini independen, kegagalan salah satu tidak boleh menghambat yang lain).

### Kenapa Ini Jadi Milestone Terpisah
Skema dan tujuan baca database ini berbeda total dari Session Memory (lihat "Konteks" di atas) — meski sama-sama "penyimpanan hasil turn", keduanya melayani pembaca yang berbeda (AI vs aplikasi/user) dan layak dirancang skemanya secara sadar terpisah, bukan dipaksa jadi satu tabel yang melayani dua tujuan sekaligus.

### Output
Skema tabel (atau koleksi, tergantung teknologi penyimpanan yang dipilih) untuk riwayat percakapan, dan mekanisme penulisan yang terpanggil otomatis di akhir tiap turn yang diproses orkestrator.

### Kriteria Keberhasilan
- Turn yang berhasil diproses penuh menghasilkan satu entri baru di Database Percakapan yang bisa ditarik kembali dan cocok dengan apa yang sesungguhnya ditanyakan dan dijawab.
- Penulisan ke Database Percakapan yang sengaja dibuat gagal (skenario uji terkontrol, mis. penyimpanan tidak terjangkau) tidak menyebabkan response ke frontend ikut gagal — user tetap menerima jawabannya meski riwayatnya gagal tersimpan, dengan kegagalan itu dicatat sebagai sinyal terpisah (bukan disembunyikan sepenuhnya).

---

## Catatan Serah Terima ke Pekerjaan Lain

Endpoint API (Milestone 7.17) adalah satu-satunya titik kontak yang perlu diketahui frontend — perubahan bentuk payload atau response di kemudian hari berdampak langsung ke pihak yang membangun frontend (di luar cakupan dokumen ini) dan perlu dikomunikasikan.

Skema Database Percakapan (Milestone 7.18) adalah sumber data yang relevan bagi kebutuhan analitik/audit di masa depan, bila project ini diperluas ke arah itu — dicatat sebagai catatan untuk pertimbangan lanjutan, bukan cakupan aktif dokumen ini.

Span `invoke_agent` yang dibangun bertahap sepanjang Milestone 7.6-7.16 melengkapi kontrak observability yang sebelumnya baru terisi span anak-anaknya saja (dari PIC 1-4) tanpa span pembungkus — `rancangan-observability-dashboard.md` (PIC 5) sebaiknya diperbarui untuk memanfaatkan span ini sebagai unit trace utama per turn di tampilan waterfall, alih-alih merangkai span anak tanpa konteks pembungkus seperti sebelumnya.
