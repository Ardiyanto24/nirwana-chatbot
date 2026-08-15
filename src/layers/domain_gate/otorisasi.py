"""Pemeriksaan Otorisasi (Milestone 2.2, Domain Gate).

Murni pencocokan aturan berbasis lookup ke role_permissions - TIDAK ada
pemanggilan LLM sama sekali (beda total dari identifikasi.py/verifikasi_
titik_buta.py, M2.1). Ruang kesalahan tertutup: 20 role x 10 domain sudah
terdaftar lengkap, tidak ada ambiguitas bahasa untuk ditafsirkan. Lihat
decisions.md Keputusan 2.
"""

from src.config.role_permissions import load_role_permissions
from src.schemas.authorization import DomainAuthorization
from src.schemas.domain_gate import Domain


def periksa_domain(domain: Domain, role_title: str) -> DomainAuthorization:
    """Murni fungsi, TANPA span - dipanggil berulang oleh orkestrator
    (Checkpoint 5), span diemisikan di level situ per domain."""
    domain_diizinkan = load_role_permissions().get(role_title, frozenset())
    if domain in domain_diizinkan:
        return DomainAuthorization(domain=domain, diizinkan=True)
    return DomainAuthorization(
        domain=domain,
        diizinkan=False,
        alasan=f"role '{role_title}' tidak memiliki akses ke domain '{domain.value}'",
    )
