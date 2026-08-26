# Kebijakan Keamanan

*[English](SECURITY.md)*

## Cakupan

Repository ini mengimplementasikan **Lapis 1** dari desain RBAC dua lapis: memahami maksud pengguna, mengklasifikasikan domain data apa yang tersentuh, dan menegakkan otorisasi berbasis peran serta cakupan individu — **sebelum** request data apa pun dibentuk. Repository ini tidak pernah query langsung ke platform data yang mendasarinya.

**Lapis 2** — penegakan row-level (`property_id` / `own_property` / `all_properties`) — diimplementasikan oleh `chatbot_api`, layanan eksternal milik tim lain. Layanan itu dikonsumsi di sini sebagai HTTP client dan di luar cakupan kebijakan ini; laporkan isu di layanan tersebut ke pemiliknya masing-masing.

## Melaporkan Kerentanan

Proyek ini adalah portofolio solo, bukan produk dengan tim keamanan berdedikasi, tapi laporan tetap disambut dan ditanggapi serius. Gunakan **[GitHub Security Advisories](../../security/advisories/new)** ("Report a vulnerability" di tab Security repo ini) daripada issue publik, supaya perbaikan bisa diverifikasi dulu sebelum detailnya terbuka ke publik. Waktu respons bersifat best-effort.

## Temuan Aktif (per 2026-08-23)

### Prompt injection menembus klasifikasi RBAC di Domain Gate — belum diperbaiki, prioritas tinggi

**Apa yang ditemukan.** Job pengujian adversarial otomatis terjadwal (`.github/workflows/redteam.yml`) menemukan bahwa dua prompt yang bertanggung jawab mengklasifikasikan domain data apa yang tersentuh oleh sebuah pertanyaan — klasifikator utama dan pengecekan opini kedua independennya ("verifikasi titik buta") — tidak punya pertahanan apa pun terhadap prompt injection. Pesan pengguna yang berisi pola override instruksi eksplisit (menyamar sebagai perintah level sistem) secara konsisten membuat KEDUA langkah klasifikasi independen tersebut melewatkan domain sensitif (`financial`) yang sebenarnya genuinely tersentuh pertanyaan itu. Ini tereproduksi identik di empat kali percobaan independen, termasuk satu run CI terjadwal yang nyata — bukan kebetulan sekali jalan.

**Kenapa ini penting.** Klasifikasi domain adalah yang pertama dari dua pengecekan otorisasi berbasis LLM independen yang membentuk Lapis 1 sistem ini (lihat [`docs/ARCHITECTURE.id.md`](docs/ARCHITECTURE.id.md) untuk pola "generate lalu verify independen" yang jadi andalan proyek ini di tempat lain). Kalau klasifikasi berhasil dikelabui melewatkan domain sensitif, pengecekan otorisasi setelahnya tidak pernah mengevaluasi domain itu sama sekali — request berjalan seolah domain sensitif itu tidak pernah disebut. Lapis 2 (`chatbot_api`) tetap menegakkan akses row-level terhadap request apa pun yang benar-benar sampai ke sana, jadi ini bukan dengan sendirinya jalan menuju akses data tanpa batas — tapi ini berarti tujuan Lapis 1 (menangkap maksud sebelum request bahkan terbentuk) bisa dikalahkan dengan frasa override instruksi sederhana, tanpa butuh teknik jailbreak canggih.

**Status.** Terbuka, belum diperbaiki, prioritas tinggi. Scan terjadwal berjalan tiap minggu dan akan terus memunculkan temuan ini sampai diperbaiki. Sengaja dibuat non-blocking (tidak menggagalkan CI atau memblokir merge) selagi perbaikan yang tepat dirancang dan diverifikasi — lihat [`docs/KNOWN_LIMITATIONS.id.md`](docs/KNOWN_LIMITATIONS.id.md) untuk posisinya dalam pelacakan isu terbuka proyek secara keseluruhan.

**Rencana perbaikan** (belum diimplementasikan atau diverifikasi): menambahkan instruksi anti-injection eksplisit ke kedua prompt — memperlakukan teks dari pengguna murni sebagai data yang diklasifikasikan, bukan pernah sebagai instruksi yang diikuti — lalu menjalankan ulang suite adversarial untuk memastikan bypass ini genuinely tidak lagi berhasil sebelum ditutup.

Tulisan internal lengkap — metodologi penemuan, seluruh skenario yang diuji, dan proses red-team lengkap — didokumentasikan (Bahasa Indonesia) di [`docs/keterbatasan-diterima.md`](docs/keterbatasan-diterima.md) (entri #22) dan [`milestones/8.5-red-team-adversarial-scan/`](milestones/8.5-red-team-adversarial-scan/). Sengaja tidak direproduksi di sini dalam detail yang bisa langsung dieksploitasi (tanpa payload yang berfungsi).

## Prinsip Desain

Proyek ini menjalankan pola "generate, lalu verify independen" di setiap titik yang keputusannya bergantung pada pemahaman makna, bukan aturan tetap (lihat [`docs/ARCHITECTURE.id.md`](docs/ARCHITECTURE.id.md)). Temuan di atas jadi contoh penyeimbang yang berguna: dua pengecekan independen tidak banyak membantu kalau keduanya berbagi titik buta yang sama (keduanya sejak awal memang tidak dirancang untuk menahan input adversarial). Keterbatasan yang belum sampai level kerentanan aktif dilacak terpisah di [`docs/KNOWN_LIMITATIONS.id.md`](docs/KNOWN_LIMITATIONS.id.md).
