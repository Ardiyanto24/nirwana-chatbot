"""Pemeriksaan Otorisasi (Milestone 2.2, Domain Gate).

Murni pencocokan aturan berbasis lookup ke role_permissions - TIDAK ada
pemanggilan LLM sama sekali (beda total dari identifikasi.py/verifikasi_
titik_buta.py, M2.1). Ruang kesalahan tertutup: 20 role x 10 domain sudah
terdaftar lengkap, tidak ada ambiguitas bahasa untuk ditafsirkan. Lihat
decisions.md Keputusan 2.

Output granular PER DOMAIN (list[DomainAuthorization]), bukan satu
keputusan tunggal per atomic intent - forced KK2 sumber, lihat
decisions.md Keputusan 3. Entri berstatus GAGAL_TEKNIS (M2.1) dilewati -
tidak ada domain untuk diperiksa, lihat decisions.md Keputusan 9.
"""

from src.config.role_permissions import load_role_permissions
from src.observability.tracing import get_tracer
from src.schemas.authorization import AtomicIntentAuthorization, DomainAuthorization
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.session_memory import StatusEksekusi

_TRACER_NAME = "domain_gate.otorisasi"


def periksa_domain(domain: Domain, role_title: str) -> DomainAuthorization:
    """Murni fungsi, TANPA span - dipanggil berulang oleh
    periksa_otorisasi_atomic_intent(), span diemisikan di level situ per
    domain."""
    domain_diizinkan = load_role_permissions().get(role_title, frozenset())
    if domain in domain_diizinkan:
        return DomainAuthorization(domain=domain, diizinkan=True)
    return DomainAuthorization(
        domain=domain,
        diizinkan=False,
        alasan=f"role '{role_title}' tidak memiliki akses ke domain '{domain.value}'",
    )


def periksa_otorisasi_atomic_intent(
    atomic_intent_domains: AtomicIntentDomains, role_title: str
) -> AtomicIntentAuthorization:
    """Untuk SATU atomic intent, periksa seluruh domainnya - span
    `authorization.check` per domain (atribut rbac.domain/rbac.decision/
    rbac.role_title, error.type=ditolak_otorisasi bila ditolak), sesuai
    kontrak rancangan-observability-ai-chatbot.md Bagian 2 baris 38.
    `rbac.role_title` BARU (M6.1 addendum) - role_title sudah dipakai
    untuk keputusan sejak awal tapi tidak pernah direkam di span-nya
    sendiri, melemahkan nilai span ini sebagai jejak audit akses ("domain
    apa ditolak" tanpa "untuk role apa"). Lihat
    milestones/6.1-membangun-exporter-dasar/decisions.md addendum."""
    tracer = get_tracer(_TRACER_NAME)
    domain_decisions: list[DomainAuthorization] = []

    for domain in atomic_intent_domains.domains:
        with tracer.start_as_current_span("authorization.check") as span:
            span.set_attribute("rbac.domain", domain.value)
            span.set_attribute("rbac.role_title", role_title)

            keputusan = periksa_domain(domain, role_title)

            span.set_attribute("rbac.decision", "allow" if keputusan.diizinkan else "deny")
            if not keputusan.diizinkan:
                span.set_attribute("error.type", "ditolak_otorisasi")

            domain_decisions.append(keputusan)

    return AtomicIntentAuthorization(
        atomic_intent=atomic_intent_domains.atomic_intent,
        domain_decisions=domain_decisions,
    )


def periksa_otorisasi_semua(
    atomic_intent_domains_list: list[AtomicIntentDomains], role_title: str
) -> list[AtomicIntentAuthorization]:
    """Untuk seluruh AtomicIntentDomains dalam satu turn, periksa
    otorisasinya - melewati entri status=GAGAL_TEKNIS (domain kosong,
    tidak ada yang diperiksa)."""
    diproses = [
        aid
        for aid in atomic_intent_domains_list
        if aid.status != StatusEksekusi.GAGAL_TEKNIS
    ]

    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("domain_gate.periksa_otorisasi_semua") as span:
        span.set_attribute("intent.count", len(diproses))

        hasil = [periksa_otorisasi_atomic_intent(aid, role_title) for aid in diproses]

        ditolak_count = sum(
            1 for h in hasil for d in h.domain_decisions if not d.diizinkan
        )
        span.set_attribute("authorization.ditolak_count", ditolak_count)

        return hasil
