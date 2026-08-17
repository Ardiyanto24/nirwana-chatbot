"""Katalog pola nullable-bermakna (Milestone 4.3) - subset representatif
(2-3 pasang view+kolom), BUKAN transkripsi penuh 67 view dari
`docs/03-domain-source/katalog-data-chatbot.md`. Dikonfirmasi user
(`AskUserQuestion`, sesi 2026-08-17): investasi transkripsi 1000+ baris
prosa bebas tanpa bukti nyata kolom mana yang genuinely sering
ditanyakan berisiko rendah nilai - mirror preseden
`docs/keterbatasan-diterima.md` #9 (M2.3, 9 dari sekian view, ilustratif
bukan daftar tertutup). Lihat milestones/4.3-.../decisions.md Keputusan 2
dan `docs/keterbatasan-diterima.md` #12.

Setiap entri ditranskripsi PERSIS (bukan diparafrase) dari katalog
sumber, dengan sitasi baris eksplisit - mirror preseden `katalog_view.py`
(transkripsi manual dari sumber eksternal final, ruang kesalahan
tertutup diaudit langsung ke sumbernya).

Perluasan katalog ini di kemudian hari (begitu ada bukti traffic nyata
kolom lain yang sering kosong) TIDAK butuh redesain logic konsumsinya
(`src/layers/execution/penyimpanan_paket.py`) - tinggal tambah entri dict.
"""

CATATAN_NULLABLE_BERMAKNA: dict[str, dict[str, str]] = {
    # katalog-data-chatbot.md baris 324-332 (domain fnb)
    "v_lookup_fnb_transactions": {
        "guest_id": (
            "Terisi selalu untuk customer_type='inhouse'; untuk walk-in hanya "
            "~30% terisi (member/repeat), ~70% kosong - pelanggan bayar tanpa "
            "memberi identitas, bukan data kotor."
        ),
    },
    # katalog-data-chatbot.md baris 500-518 (domain facility)
    "v_lookup_maintenance_tickets": {
        "room_id": (
            "Kosong jika kerusakan di fasilitas umum (Pool/Lobby/Elevator/"
            "Restaurant/Gym/Parking, bukan di dalam kamar)."
        ),
    },
    # katalog-data-chatbot.md baris 406-421 (domain facility, kolom turunan)
    "v_maintenance_ticket_daily": {
        "avg_exceeds_sla_threshold": (
            "Kolom turunan (boolean) - apakah avg_sla_duration_hours melebihi "
            "sla_threshold_hours. NULL jika durasi belum ada."
        ),
    },
}
