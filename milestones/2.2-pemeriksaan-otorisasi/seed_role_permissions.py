"""Skrip seed sekali-jalan: transkripsi matriks role_permissions (20 role x
10 domain) dari rancangan-rbac-ai-chatbot.md Bagian 2, insert ke tabel
`role_permissions` (Supabase) - Milestone 2.2 Checkpoint 3.

Skrip sekali-pakai (BUKAN bagian runtime permanen src/) - dijalankan manual
satu kali untuk migrasi awal, mirror pola seed_roles.py Milestone 1.5.
Lihat decisions.md Keputusan 8.

Transkripsi ditranspose LANGSUNG dari tabel "Peran x Domain operasional /
properties_ref / employees_directory / guests_pii / guests_profile" -
setiap role dipetakan ke domain yang granted (ceklis di sumber), TANPA
access_scope (own_property/all_properties) karena M2.2 hanya menjawab
izin/tolak biner per domain (Keputusan 4 - access_scope tanggung jawab
chatbot_api).

Jalankan dari root repo: uv run python milestones/2.2-pemeriksaan-otorisasi/seed_role_permissions.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session

from src.config.database import get_engine
from src.db.models import RolePermissionRow

# Domain 7 operasional: reservation, fnb, facility, spa_event, hr, financial
# (corporate_master TIDAK ada - dipecah jadi 4 kelompok granular di bawah).
# 4 kelompok granular: properties_ref, employees_directory, guests_pii,
# guests_profile.
#
# Ditranskripsi baris-per-baris dari rancangan-rbac-ai-chatbot.md Bagian 2
# (baris 45-64) - urutan role dan domain PERSIS mengikuti tabel sumber.
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "CEO": [
        "reservation", "fnb", "facility", "spa_event", "hr", "financial",
        "properties_ref", "employees_directory", "guests_pii", "guests_profile",
    ],
    "Corporate Finance Director": [
        "financial", "reservation", "properties_ref", "employees_directory",
    ],
    "Corporate HR Director": [
        "hr", "properties_ref", "employees_directory",
    ],
    "Corporate Operations Director": [
        "facility", "fnb", "spa_event", "reservation",
        "properties_ref", "employees_directory",
    ],
    "Corporate Revenue Director": [
        "reservation", "financial",
        "properties_ref", "guests_pii", "guests_profile",
    ],
    "General Manager": [
        "reservation", "fnb", "facility", "spa_event", "hr", "financial",
        "properties_ref", "employees_directory",
    ],
    "Revenue Manager": [
        "reservation", "properties_ref", "guests_pii", "guests_profile",
    ],
    "F&B Manager": [
        "fnb", "reservation", "properties_ref", "employees_directory",
    ],
    "Housekeeping Manager": [
        "facility", "reservation", "properties_ref", "employees_directory",
    ],
    "Maintenance Manager": [
        "facility", "properties_ref", "employees_directory",
    ],
    "Spa & Event Manager": [
        "spa_event", "properties_ref", "employees_directory", "guests_pii",
    ],
    "HR Manager": [
        "hr", "properties_ref", "employees_directory",
    ],
    "Finance Manager": [
        "financial", "reservation", "properties_ref", "employees_directory",
    ],
    "Front Office Staff": [
        "reservation", "properties_ref", "guests_pii",
    ],
    "F&B Staff": [
        "fnb",
    ],
    "Housekeeping Staff": [
        "facility",
    ],
    "Maintenance Staff": [
        "facility",
    ],
    "Spa & Event Staff": [
        "spa_event", "guests_pii",
    ],
    "HR Staff": [
        "hr", "employees_directory",
    ],
    "Finance Staff": [
        "financial", "employees_directory",
    ],
}


def main() -> None:
    assert len(ROLE_PERMISSIONS) == 20, f"Harus 20 role, dapat {len(ROLE_PERMISSIONS)}"

    total_rows = 0
    with Session(get_engine()) as session:
        for role_title, domains in ROLE_PERMISSIONS.items():
            for domain in domains:
                session.add(RolePermissionRow(role_title=role_title, domain=domain))
                total_rows += 1
        session.commit()

    print(f"{total_rows} baris izin di-seed ke tabel role_permissions ({len(ROLE_PERMISSIONS)} role).")


if __name__ == "__main__":
    main()
