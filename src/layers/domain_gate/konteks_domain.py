"""Konteks grounding statis untuk prompt identifikasi domain (Milestone 2.1).

Diimpor bersama oleh identifikasi.py dan verifikasi_titik_buta.py supaya
kedua prompt konsisten, tidak drift satu sama lain.

Cakupan SENGAJA dibatasi ke 10 domain + SATU contoh cross-domain
terdokumentasi (bukan seluruh 67 view) - katalog data hanya menandai
`v_reservation_gop_impact_monthly` eksplisit sebagai "Cross-domain" di
seluruh dokumen (dikonfirmasi lewat pencarian string literal, bukan
sampel). Lihat decisions.md Keputusan 11.

Deskripsi 10 domain dikutip dari kolom "Isi" tabel Ringkasan 10 Domain,
katalog-data-chatbot.md baris 45-54. Aturan guests_pii/guests_profile
dikutip verbatim dari rancangan-rbac-ai-chatbot.md Bagian 1.
"""

from src.schemas.domain_gate import Domain

DESKRIPSI_DOMAIN: dict[Domain, str] = {
    Domain.RESERVATION: "Booking kamar, okupansi, revenue kamar, pricing.",
    Domain.FNB: "Penjualan F&B, inventori bahan, resep, waste.",
    Domain.FACILITY: "Status kamar, housekeeping, tiket maintenance.",
    Domain.SPA_EVENT: "Booking spa & event/MICE, venue.",
    Domain.HR: "Kehadiran, performa karyawan, turnover - TANPA payroll (payroll eksklusif domain financial).",
    Domain.FINANCIAL: "Revenue/expense/profit/GOP, payroll - eksklusif domain ini.",
    Domain.PROPERTIES_REF: "Master 6 properti (nama, region, tanggal buka).",
    Domain.EMPLOYEES_DIRECTORY: "Direktori karyawan (nama, properti, departemen, level akses).",
    Domain.GUESTS_PII: "Kontak tamu: nama lengkap (full_name), email, telepon (phone) - HANYA kolom kontak.",
    Domain.GUESTS_PROFILE: "Atribut analitis tamu: loyalty_tier, nationality, riwayat booking - TIDAK termasuk kontak.",
}

CATATAN_POLA_JEBAKAN = """\
Perhatikan tiga pola jebakan berikut saat mengidentifikasi domain:

1. KEBOCORAN DOMAIN LEWAT KOLOM TURUNAN: sebuah view bisa terdaftar di satu \
domain tapi salah satu kolomnya sebenarnya dihitung/diturunkan dari domain \
lain. Kalau kebutuhan menyentuh kolom semacam itu, KEDUA domain tersentuh, \
bukan cuma domain tempat view itu terdaftar. Contoh nyata yang sudah \
terdokumentasi: view `v_reservation_gop_impact_monthly` terdaftar di domain \
`reservation`, tapi kolom `gop_margin` di dalamnya berasal dari domain \
`financial` (Gross Operating Profit margin properti). Pertanyaan yang \
menyentuh `gop_margin` HARUS mengenali domain `reservation` DAN `financial` \
sekaligus. Ini hanya SATU contoh ilustrasi - pola yang sama (kolom metrik \
finansial/turunan yang menempel di view domain lain) bisa muncul di view \
lain yang tidak eksplisit disebutkan di sini; pikirkan prinsipnya, jangan \
hanya menghapal contoh ini.

2. FOKUS TERLALU SEMPIT PADA KATA YANG EKSPLISIT DISEBUT: jangan hanya \
mencocokkan kata kunci literal di pertanyaan. Pertimbangkan makna penuh \
kebutuhannya - metrik apa yang benar-benar diminta, dan domain data mana \
saja yang menyimpan metrik itu.

3. PEMISAHAN KOLOM guests_pii vs guests_profile: keduanya bersumber dari \
tabel fisik `guests` yang SAMA, tapi terpisah di level KOLOM, bukan level \
domain/tabel. `guests_pii` HANYA mencakup kolom kontak (full_name, email, \
phone). `guests_profile` mencakup kolom atribut analitis (loyalty_tier, \
nationality, riwayat booking) - TIDAK termasuk kontak. Pertanyaan yang \
menyebut "data tamu" secara umum TIDAK CUKUP diklasifikasikan ke satu \
domain generik - Anda WAJIB menentukan kolom spesifik apa yang dimaksud: \
kalau yang diminta adalah cara menghubungi/kontak tamu (nama, email, \
telepon) maka domainnya guests_pii; kalau yang diminta adalah atribut \
analitis (loyalitas, kebangsaan, riwayat booking) maka domainnya \
guests_profile; kalau kebutuhan genuinely menyentuh keduanya, sebutkan \
keduanya."""
