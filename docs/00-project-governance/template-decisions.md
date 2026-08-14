# Decisions — Milestone <id>: <Nama Milestone>

Dokumen ini mencatat setiap keputusan desain yang diambil untuk milestone ini — baik yang ditentukan sebelum implementasi dimulai (dari Plan Mode) maupun yang ditemukan di tengah pengerjaan dan perlu diputuskan saat itu juga. Satu file ini bisa berisi banyak entri keputusan, masing-masing diberi nomor urut sesuai kemunculan kronologisnya (bukan diurutkan ulang berdasar topik), supaya pembaca bisa mengikuti alur berpikir sepanjang milestone berjalan.

Ada dua jenis entri, dengan bentuk yang berbeda — pilih sesuai sifat keputusannya, jangan memaksakan satu bentuk untuk keduanya:

- **Jenis A — Genuinely Terbuka**: keputusan yang tidak py jawaban tunggal dari dokumen manapun, biasanya berasal dari section "Keputusan yang Ditanyakan ke User" di plan, atau ditemukan baru di tengah implementasi. Wajib py Opsi yang Dipertimbangkan tapi Ditolak.
- **Jenis B — Preseden/Forced**: keputusan yang sebenarnya sudah dipaksa oleh kontrak, prinsip arsitektur, atau keputusan milestone lain yang sudah final — dicatat di sini bukan untuk didebat ulang, melainkan supaya jejak "kenapa begini" tetap tertelusuri tanpa perlu membuka dokumen sumbernya lagi. Tidak wajib py Opsi Ditolak (karena sering memang tidak py alternatif nyata yang dipertimbangkan) — cukup nyatakan itu eksplisit kalau memang begitu.

---

## Template Entri — Jenis A (Genuinely Terbuka)

### Keputusan <n>: <Judul Singkat Keputusan>

**Status:** <Diputuskan sebelum implementasi (dari plan) / Ditemukan di tengah implementasi pada Checkpoint <n>>

**Latar Belakang**
<Kenapa keputusan ini perlu diambil — masalah/kebutuhan apa yang memicunya, dan kenapa ia genuinely terbuka (tidak bisa ditarik dari dokumen sumber manapun). Kalau ditemukan di tengah implementasi, jelaskan juga bagaimana ia ditemukan — task/checkpoint mana yang memicunya.>

**Keputusan yang Dipilih**
<Apa yang diputuskan, dinyatakan konkret dan bisa diverifikasi — bukan kalimat samar.>

**Alasan**
<Kenapa opsi ini yang dipilih — argumen substantif, idealnya merujuk trade-off nyata (biaya, kompleksitas, keselarasan dengan prinsip arsitektur), bukan sekadar "karena lebih baik".>

**Opsi yang Dipertimbangkan tapi Ditolak**
- **<Opsi 1>** — <kenapa ditolak: bukti/kendala teknis/prinsip arsitektur yang dilanggar opsi ini>
- **<Opsi 2>** — <dst>

**Dampak**
<Siapa/apa yang terpengaruh keputusan ini — milestone lain yang perlu tahu, file yang perlu diperbarui, atau catatan bahwa keputusan ini murni internal milestone ini tanpa dampak lintas-pekerjaan.>

---

## Template Entri — Jenis B (Preseden/Forced)

### Keputusan <n>: <Judul Singkat Keputusan>

**Sumber Paksaan**
<Dokumen/milestone/prinsip spesifik yang memaksa keputusan ini — sebutkan nama dokumen dan bagian/baris kalau memungkinkan, bukan rujukan samar seperti "sudah diatur di arsitektur".>

**Keputusan yang Diikuti**
<Apa yang diikuti/diterapkan sesuai sumber paksaan tersebut.>

**Catatan Ketergantungan**
<Kenapa keputusan ini tidak py ruang untuk dipertimbangkan ulang di milestone ini — apa yang akan rusak/tidak konsisten kalau keputusan ini diubah sepihak di sini.>

**Opsi yang Dipertimbangkan tapi Ditolak**
<Isi kalau memang ada alternatif yang sempat terpikir sebelum menyadari ini forced. Kalau tidak ada, nyatakan singkat: "Tidak ada alternatif dipertimbangkan karena forced by <sumber paksaan>.">

---

## Daftar Isi Keputusan

<Perbarui daftar ini setiap kali entri baru ditambahkan — memudahkan pembaca menemukan keputusan tanpa scroll seluruh file untuk milestone yang py banyak entri.>

| # | Judul | Jenis | Checkpoint Terkait |
|---|---|---|---|
| 1 | <judul> | A/B | <nomor checkpoint, atau "Plan" kalau diputuskan sebelum implementasi> |
