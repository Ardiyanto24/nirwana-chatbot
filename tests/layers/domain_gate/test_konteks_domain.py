"""Regression guard: DESKRIPSI_DOMAIN harus cocok 1:1 dengan anggota Domain
Enum (Milestone 2.1) - mencegah drift kalau Domain Enum berubah tapi
konteks grounding lupa diperbarui."""

from src.layers.domain_gate.konteks_domain import CATATAN_POLA_JEBAKAN, DESKRIPSI_DOMAIN
from src.schemas.domain_gate import Domain


def test_deskripsi_domain_cocok_1_1_dengan_enum():
    assert set(DESKRIPSI_DOMAIN.keys()) == set(Domain)
    assert len(DESKRIPSI_DOMAIN) == 10


def test_deskripsi_domain_tidak_kosong():
    for domain, deskripsi in DESKRIPSI_DOMAIN.items():
        assert deskripsi.strip(), f"deskripsi {domain} tidak boleh kosong"


def test_catatan_pola_jebakan_menyebut_kasus_terdokumentasi():
    assert "gop_margin" in CATATAN_POLA_JEBAKAN
    assert "guests_pii" in CATATAN_POLA_JEBAKAN
    assert "guests_profile" in CATATAN_POLA_JEBAKAN
