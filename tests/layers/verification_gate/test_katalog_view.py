"""Test katalog 67 view (Milestone 2.4) - cross-check total DAN per-domain
count terhadap tabel api-chatbot.md, ditulis independen dari hasil
transkripsi (bukan len() dari data yang sama) supaya bukan pengujian
sirkular."""

from src.layers.verification_gate.katalog_view import DAFTAR_VIEW_PER_DOMAIN
from src.schemas.domain_gate import Domain

# Ditranskripsi independen dari tabel per-domain api-chatbot.md baris 46-57.
_EXPECTED_COUNT_PER_DOMAIN: dict[Domain, int] = {
    Domain.RESERVATION: 10,
    Domain.FNB: 11,
    Domain.FACILITY: 12,
    Domain.SPA_EVENT: 9,
    Domain.HR: 10,
    Domain.FINANCIAL: 11,
    Domain.PROPERTIES_REF: 1,
    Domain.EMPLOYEES_DIRECTORY: 1,
    Domain.GUESTS_PII: 1,
    Domain.GUESTS_PROFILE: 1,
}


def test_total_67_view():
    total = sum(len(views) for views in DAFTAR_VIEW_PER_DOMAIN.values())
    assert total == 67


def test_seluruh_10_domain_tercakup():
    assert set(DAFTAR_VIEW_PER_DOMAIN.keys()) == set(Domain)


def test_count_per_domain_cocok_api_chatbot_md():
    for domain, expected in _EXPECTED_COUNT_PER_DOMAIN.items():
        actual = len(DAFTAR_VIEW_PER_DOMAIN[domain])
        assert actual == expected, f"{domain.value}: {actual} != {expected}"


def test_tidak_ada_view_name_duplikat_lintas_domain():
    seluruh_view = [v for views in DAFTAR_VIEW_PER_DOMAIN.values() for v in views]
    assert len(seluruh_view) == len(set(seluruh_view))


def test_guests_view_pengecualian_penamaan():
    """guests_contact_view/guests_profile_view TIDAK diawali v_ - pengecualian
    nyata di dokumen sumber, bukan typo transkripsi."""
    assert "guests_contact_view" in DAFTAR_VIEW_PER_DOMAIN[Domain.GUESTS_PII]
    assert "guests_profile_view" in DAFTAR_VIEW_PER_DOMAIN[Domain.GUESTS_PROFILE]
