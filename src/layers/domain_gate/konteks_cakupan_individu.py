"""Konteks grounding statis untuk prompt deteksi constraint cakupan-individu
(Milestone 2.3).

Diimpor bersama oleh deteksi_cakupan_individu.py dan
verifikasi_cakupan_individu.py supaya kedua prompt konsisten, tidak drift
satu sama lain - mirror pola konteks_domain.py (M2.1).

Daftar 9 view hasil tinjauan langsung ke katalog-data-chatbot.md,
dikonfirmasi user lewat AskUserQuestion sebelum plan ditulis. Kriteria:
grain 1 baris = 1 staf/karyawan tertentu (bukan agregat tim/departemen)
DAN isinya metrik kerja/kehadiran/kinerja. Lihat decisions.md Keputusan 1.
"""

from dataclasses import dataclass

from src.schemas.domain_gate import Domain


@dataclass(frozen=True)
class ViewCakupanIndividu:
    nama: str
    domain: Domain
    kolom_identitas: str
    deskripsi: str


DAFTAR_VIEW_CAKUPAN_INDIVIDU: list[ViewCakupanIndividu] = [
    # facility (4 view)
    ViewCakupanIndividu(
        nama="v_housekeeping_staff_daily",
        domain=Domain.FACILITY,
        kolom_identitas="staff_id",
        deskripsi="Performa individu 1 staf housekeeping (durasi pembersihan) dibanding rata-rata tim.",
    ),
    ViewCakupanIndividu(
        nama="v_maintenance_technician_daily",
        domain=Domain.FACILITY,
        kolom_identitas="assigned_staff_id",
        deskripsi="Beban kerja individu 1 teknisi maintenance (jumlah tiket, jam kerja).",
    ),
    ViewCakupanIndividu(
        nama="v_lookup_housekeeping_log",
        domain=Domain.FACILITY,
        kolom_identitas="staff_id",
        deskripsi="Riwayat sesi pembersihan per staf tertentu (durasi, status keterlambatan).",
    ),
    ViewCakupanIndividu(
        nama="v_lookup_maintenance_tickets",
        domain=Domain.FACILITY,
        kolom_identitas="assigned_staff_id",
        deskripsi="Riwayat tiket per teknisi tertentu (jam kerja, biaya per tiket).",
    ),
    # hr (5 view)
    ViewCakupanIndividu(
        nama="v_hr_employee_monthly",
        domain=Domain.HR,
        kolom_identitas="employee_id",
        deskripsi="Performa kehadiran 1 karyawan (lembur, keterlambatan) dibanding rata-rata departemen.",
    ),
    ViewCakupanIndividu(
        nama="v_hr_employee_performance_semester",
        domain=Domain.HR,
        kolom_identitas="employee_id",
        deskripsi="Skor dan catatan penilaian kinerja 1 karyawan per semester.",
    ),
    ViewCakupanIndividu(
        nama="v_hr_watchlist_monthly",
        domain=Domain.HR,
        kolom_identitas="employee_id",
        deskripsi="Daftar pantau 1 karyawan dengan pola absensi/keterlambatan menyimpang dari baseline pribadinya.",
    ),
    ViewCakupanIndividu(
        nama="v_lookup_staff_shifts",
        domain=Domain.HR,
        kolom_identitas="employee_id",
        deskripsi="Status kehadiran (hadir/telat/cuti/absen) 1 karyawan per hari.",
    ),
    ViewCakupanIndividu(
        nama="v_lookup_employee_performance",
        domain=Domain.HR,
        kolom_identitas="employee_id",
        deskripsi="Skor dan catatan performa review terakhir 1 karyawan tertentu.",
    ),
]

CATATAN_INDIVIDU_VS_AGREGAT = """\
Perhatikan perbedaan berikut saat menilai apakah sebuah kebutuhan menyentuh \
kategori data performa INDIVIDU:

1. INDIVIDU (masuk kategori): kebutuhan yang hasilnya menunjukkan atau bisa \
menunjukkan data SATU staf/karyawan tertentu secara spesifik - termasuk \
ranking/perbandingan antar-individu ("siapa staf tercepat", "staf mana yang \
paling sering telat"), pencarian by name ("performa Budi bulan ini"), atau \
daftar yang tetap granular per-orang meski tidak menyebut nama spesifik \
("tampilkan skor kinerja semua staf housekeeping" - ini tetap granular per \
individu, hanya saja untuk banyak orang sekaligus).

2. AGREGAT (TIDAK masuk kategori): kebutuhan yang hasilnya sudah digabung/ \
dirangkum ke level tim, departemen, atau properti - individu di dalamnya \
tidak bisa dibedakan dari hasil akhirnya. Contoh: "berapa staf hadir hari \
ini" (hanya angka jumlah), "rata-rata skor kinerja departemen housekeeping" \
(satu angka gabungan), "tingkat turnover properti ini" (agregat properti).

3. JEBAKAN KATA KUNCI: jangan hanya mencocokkan kata "staf"/"karyawan"/ \
"individu" secara literal. Kalimat yang menyebut kata itu tapi hasilnya \
tetap agregat (poin 2) BUKAN kategori ini. Sebaliknya, kalimat yang tidak \
menyebut kata itu sama sekali tapi hasilnya genuinely granular per-orang \
(mis. "siapa yang paling banyak menangani tiket maintenance bulan ini") \
TETAP masuk kategori ini."""
