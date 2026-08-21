"""Orkestrator Deteksi Constraint Cakupan-Individu (Milestone 2.3):
Deteksi Awal -> Verifikasi Titik Buta, union aditif (OR-merge) - lihat
decisions.md Keputusan 2.

Dua pre-filter deterministik SEBELUM panggilan LLM apa pun (Keputusan 4-5):
role bukan tier Staff, atau domain diizinkan tidak menyentuh facility/hr -
kedua kasus langsung terdeteksi=False TANPA memanggil LLM sama sekali.
Fail-closed (terdeteksi=True) kalau kedua langkah LLM gagal teknis
(Keputusan 7).
"""

from src.layers.domain_gate.deteksi_cakupan_individu import deteksi_cakupan_individu
from src.layers.domain_gate.verifikasi_cakupan_individu import verifikasi_cakupan_individu
from src.observability.tracing import get_tracer
from src.schemas.authorization import AtomicIntentAuthorization
from src.schemas.cakupan_individu import AtomicIntentConstraint, ConstraintCakupanIndividu
from src.schemas.domain_gate import Domain

_TRACER_NAME = "domain_gate.cakupan_individu"

# 7 role tier Staff (transkripsi manual dari rancangan-rbac-ai-chatbot.md
# baris 58-64) - ruang kesalahan tertutup, 20 role sudah final. Lihat
# decisions.md Keputusan 3.
ROLE_STAFF_TIER: frozenset[str] = frozenset(
    {
        "Front Office Staff",
        "F&B Staff",
        "Housekeeping Staff",
        "Maintenance Staff",
        "Spa & Event Staff",
        "HR Staff",
        "Finance Staff",
    }
)

_DOMAIN_RELEVAN = frozenset({Domain.FACILITY, Domain.HR})


def _domain_diizinkan_relevan(atomic_intent_authorization: AtomicIntentAuthorization) -> bool:
    return any(
        d.domain in _DOMAIN_RELEVAN and d.diizinkan
        for d in atomic_intent_authorization.domain_decisions
    )


def deteksi_constraint_atomic_intent(
    atomic_intent_authorization: AtomicIntentAuthorization, role_title: str
) -> AtomicIntentConstraint:
    """Untuk SATU atomic intent, deteksi constraint cakupan-individu -
    pre-filter role/domain dulu (tanpa panggilan LLM), baru panggil
    Langkah 1+2 kalau lolos keduanya."""
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("domain_gate.cakupan_individu.check") as span:
        # rbac.role_title BARU (M6.1 addendum) - role_title dipakai untuk
        # keputusan constraint sejak awal tapi tidak pernah direkam di
        # span-nya sendiri. Diset di awal (bukan per-cabang) supaya
        # SELURUH jalur return (4 titik di bawah) konsisten membawanya.
        span.set_attribute("rbac.role_title", role_title)

        if role_title not in ROLE_STAFF_TIER:
            span.set_attribute("rbac.individual_scope_constraint", False)
            span.set_attribute("domain_gate.cakupan_individu.pre_filter", "role_bukan_staff_tier")
            return AtomicIntentConstraint(
                atomic_intent=atomic_intent_authorization.atomic_intent,
                domain_decisions=atomic_intent_authorization.domain_decisions,
                constraint=ConstraintCakupanIndividu(terdeteksi=False),
            )

        if not _domain_diizinkan_relevan(atomic_intent_authorization):
            span.set_attribute("rbac.individual_scope_constraint", False)
            span.set_attribute(
                "domain_gate.cakupan_individu.pre_filter", "domain_tidak_relevan"
            )
            return AtomicIntentConstraint(
                atomic_intent=atomic_intent_authorization.atomic_intent,
                domain_decisions=atomic_intent_authorization.domain_decisions,
                constraint=ConstraintCakupanIndividu(terdeteksi=False),
            )

        atomic_intent = atomic_intent_authorization.atomic_intent
        hasil_awal = deteksi_cakupan_individu(atomic_intent)
        hasil_verifikasi = verifikasi_cakupan_individu(atomic_intent, hasil_awal.terdeteksi)

        if hasil_awal.gagal and hasil_verifikasi.gagal:
            span.set_attribute("rbac.individual_scope_constraint", True)
            span.set_attribute(
                "domain_gate.cakupan_individu.forced_fallback_reason",
                "gagal_teknis_kedua_langkah_fail_closed",
            )
            constraint = ConstraintCakupanIndividu(
                terdeteksi=True,
                alasan="gagal teknis pada kedua langkah deteksi - dipasang konservatif",
            )
        else:
            terdeteksi = hasil_awal.terdeteksi or hasil_verifikasi.terdeteksi_tambahan
            span.set_attribute("rbac.individual_scope_constraint", terdeteksi)
            constraint = ConstraintCakupanIndividu(
                terdeteksi=terdeteksi,
                alasan=(
                    "kebutuhan menyentuh kategori data performa individu staf"
                    if terdeteksi
                    else None
                ),
            )

        return AtomicIntentConstraint(
            atomic_intent=atomic_intent,
            domain_decisions=atomic_intent_authorization.domain_decisions,
            constraint=constraint,
        )


def deteksi_constraint_semua(
    atomic_intent_authorization_list: list[AtomicIntentAuthorization], role_title: str
) -> list[AtomicIntentConstraint]:
    """Untuk seluruh AtomicIntentAuthorization dalam satu turn, deteksi
    constraint cakupan-individunya satu per satu."""
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("domain_gate.deteksi_constraint_semua") as span:
        span.set_attribute("intent.count", len(atomic_intent_authorization_list))

        hasil = [
            deteksi_constraint_atomic_intent(aia, role_title)
            for aia in atomic_intent_authorization_list
        ]

        terdeteksi_count = sum(1 for h in hasil if h.constraint.terdeteksi)
        span.set_attribute("constraint.terdeteksi_count", terdeteksi_count)

        return hasil
