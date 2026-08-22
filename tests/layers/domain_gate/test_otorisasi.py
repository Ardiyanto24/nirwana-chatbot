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
import uuid

import pytest

from src.layers.domain_gate.otorisasi import (
    periksa_domain,
    periksa_otorisasi_atomic_intent,
    periksa_otorisasi_semua,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL tidak diset - skip test yang butuh koneksi database nyata",
)


def _buat_atomic_intent_domains(
    domains: list[Domain], status: StatusEksekusi = StatusEksekusi.BERHASIL
) -> AtomicIntentDomains:
    return AtomicIntentDomains(
        atomic_intent=AtomicIntent(
            atomic_intent_id=str(uuid.uuid4()),
            teks_kebutuhan="kebutuhan uji",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
            bergantung_pada=None,
        ),
        domains=domains,
        status=status,
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
        "CEO",
        "Corporate Finance Director",
        "Corporate Operations Director",
        "Corporate Revenue Director",
        "General Manager",
        "Revenue Manager",
        "F&B Manager",
        "Housekeeping Manager",
        "Finance Manager",
        "Front Office Staff",
    },
    Domain.FNB: {
        "CEO",
        "Corporate Operations Director",
        "General Manager",
        "F&B Manager",
        "F&B Staff",
    },
    Domain.FACILITY: {
        "CEO",
        "Corporate Operations Director",
        "General Manager",
        "Housekeeping Manager",
        "Maintenance Manager",
        "Housekeeping Staff",
        "Maintenance Staff",
    },
    Domain.SPA_EVENT: {
        "CEO",
        "Corporate Operations Director",
        "General Manager",
        "Spa & Event Manager",
        "Spa & Event Staff",
    },
    Domain.HR: {
        "CEO",
        "Corporate HR Director",
        "General Manager",
        "HR Manager",
        "HR Staff",
    },
    Domain.FINANCIAL: {
        "CEO",
        "Corporate Finance Director",
        "Corporate Revenue Director",
        "General Manager",
        "Finance Manager",
        "Finance Staff",
    },
    Domain.PROPERTIES_REF: {
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
    },
    Domain.EMPLOYEES_DIRECTORY: {
        "CEO",
        "Corporate Finance Director",
        "Corporate HR Director",
        "Corporate Operations Director",
        "General Manager",
        "F&B Manager",
        "Housekeeping Manager",
        "Maintenance Manager",
        "Spa & Event Manager",
        "HR Manager",
        "Finance Manager",
        "HR Staff",
        "Finance Staff",
    },
    Domain.GUESTS_PII: {
        "CEO",
        "Corporate Revenue Director",
        "Revenue Manager",
        "Spa & Event Manager",
        "Front Office Staff",
        "Spa & Event Staff",
    },
    Domain.GUESTS_PROFILE: {
        "CEO",
        "Corporate Revenue Director",
        "Revenue Manager",
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


# --- KK2: multi-domain campuran izin/tolak ----------------------------------


def test_kk2_multi_domain_sebagian_diizinkan_sebagian_ditolak():
    """Front Office Staff: reservation DIIZINKAN, financial DITOLAK -
    hasil harus benar PER DOMAIN, bukan satu keputusan tunggal untuk
    seluruh atomic intent."""
    aid = _buat_atomic_intent_domains([Domain.RESERVATION, Domain.FINANCIAL])
    hasil = periksa_otorisasi_atomic_intent(aid, "Front Office Staff")

    assert len(hasil.domain_decisions) == 2
    by_domain = {d.domain: d for d in hasil.domain_decisions}

    assert by_domain[Domain.RESERVATION].diizinkan is True
    assert by_domain[Domain.RESERVATION].alasan is None

    assert by_domain[Domain.FINANCIAL].diizinkan is False
    assert by_domain[Domain.FINANCIAL].alasan is not None


def test_periksa_otorisasi_semua_melewati_gagal_teknis():
    """Entri status=GAGAL_TEKNIS (domain kosong) dilewati, tidak
    menghasilkan AtomicIntentAuthorization apa pun."""
    gagal = _buat_atomic_intent_domains([], status=StatusEksekusi.GAGAL_TEKNIS)
    berhasil = _buat_atomic_intent_domains([Domain.HR])

    hasil = periksa_otorisasi_semua([gagal, berhasil], "HR Staff")

    assert len(hasil) == 1
    assert (
        hasil[0].atomic_intent.atomic_intent_id
        == berhasil.atomic_intent.atomic_intent_id
    )
