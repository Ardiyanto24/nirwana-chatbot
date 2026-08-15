"""Test suite Pemeriksaan Otorisasi (Milestone 2.2).

KK1: exhaustive 20 role x 10 domain = 200 kombinasi, dibandingkan terhadap
ekspektasi yang DITULIS ULANG independen dari `seed_role_permissions.py`
(ditranskripsi ulang DOMAIN-per-domain di sini, bukan role-per-role seperti
skrip seed - supaya bukan pengujian sirkular; kalau ada transkripsi salah
di salah satu, kemungkinan besar tidak akan identik di keduanya). Sumber:
rancangan-rbac-ai-chatbot.md Bagian 2, baris 45-64.

Butuh `DATABASE_URL` aktif DAN tabel role_permissions sudah di-seed
(Checkpoint 3) - di-skip otomatis kalau tidak tersedia, mirror preseden
test_input_layer.py.
"""

import os

import pytest

from src.layers.domain_gate.otorisasi import periksa_domain
from src.schemas.domain_gate import Domain

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL tidak diset - skip test yang butuh koneksi database nyata",
)

_ALL_ROLES = [
    "CEO",
    "Corporate Finance Director",
    "Corporate HR Director",
    "Corporate Operations Director",
    "Corporate Revenue Director",
    "General Manager",
    "Revenue Manager",
    "F&B Manager",
    "Housekeeping Manager",
    "Maintenance Manager",
    "Spa & Event Manager",
    "HR Manager",
    "Finance Manager",
    "Front Office Staff",
    "F&B Staff",
    "Housekeeping Staff",
    "Maintenance Staff",
    "Spa & Event Staff",
    "HR Staff",
    "Finance Staff",
]

# Ditranskripsi DOMAIN-per-domain (independen dari seed_role_permissions.py
# yang role-per-role) - "role mana saja yang punya akses ke domain ini".
_EXPECTED_GRANTED_ROLES: dict[Domain, set[str]] = {
    Domain.RESERVATION: {
        "CEO", "Corporate Finance Director", "Corporate Operations Director",
        "Corporate Revenue Director", "General Manager", "Revenue Manager",
        "F&B Manager", "Housekeeping Manager", "Finance Manager", "Front Office Staff",
    },
    Domain.FNB: {
        "CEO", "Corporate Operations Director", "General Manager",
        "F&B Manager", "F&B Staff",
    },
    Domain.FACILITY: {
        "CEO", "Corporate Operations Director", "General Manager",
        "Housekeeping Manager", "Maintenance Manager",
        "Housekeeping Staff", "Maintenance Staff",
    },
    Domain.SPA_EVENT: {
        "CEO", "Corporate Operations Director", "General Manager",
        "Spa & Event Manager", "Spa & Event Staff",
    },
    Domain.HR: {
        "CEO", "Corporate HR Director", "General Manager",
        "HR Manager", "HR Staff",
    },
    Domain.FINANCIAL: {
        "CEO", "Corporate Finance Director", "Corporate Revenue Director",
        "General Manager", "Finance Manager", "Finance Staff",
    },
    Domain.PROPERTIES_REF: {
        "CEO", "Corporate Finance Director", "Corporate HR Director",
        "Corporate Operations Director", "Corporate Revenue Director",
        "General Manager", "Revenue Manager", "F&B Manager",
        "Housekeeping Manager", "Maintenance Manager", "Spa & Event Manager",
        "HR Manager", "Finance Manager", "Front Office Staff",
    },
    Domain.EMPLOYEES_DIRECTORY: {
        "CEO", "Corporate Finance Director", "Corporate HR Director",
        "Corporate Operations Director", "General Manager", "F&B Manager",
        "Housekeeping Manager", "Maintenance Manager", "Spa & Event Manager",
        "HR Manager", "Finance Manager", "HR Staff", "Finance Staff",
    },
    Domain.GUESTS_PII: {
        "CEO", "Corporate Revenue Director", "Revenue Manager",
        "Spa & Event Manager", "Front Office Staff", "Spa & Event Staff",
    },
    Domain.GUESTS_PROFILE: {
        "CEO", "Corporate Revenue Director", "Revenue Manager",
    },
}


def test_expected_matrix_total_74_baris():
    """Sanity check struktur ekspektasi test itu sendiri sebelum dipakai
    parametrize - total granted harus 74 (cocok independen dengan hasil
    seed Checkpoint 3, dua kali dihitung dengan cara berbeda: role-per-role
    di seed script, domain-per-domain di sini)."""
    total = sum(len(roles) for roles in _EXPECTED_GRANTED_ROLES.values())
    assert total == 74
    assert set(_EXPECTED_GRANTED_ROLES.keys()) == set(Domain)


@pytest.mark.parametrize("role_title", _ALL_ROLES)
@pytest.mark.parametrize("domain", list(Domain))
def test_exhaustive_200_kombinasi_role_domain(domain: Domain, role_title: str):
    hasil = periksa_domain(domain, role_title)
    seharusnya_diizinkan = role_title in _EXPECTED_GRANTED_ROLES[domain]

    assert hasil.diizinkan == seharusnya_diizinkan, (
        f"role={role_title!r} domain={domain.value!r}: "
        f"diizinkan={hasil.diizinkan}, seharusnya={seharusnya_diizinkan}"
    )
    if not seharusnya_diizinkan:
        assert hasil.alasan is not None
