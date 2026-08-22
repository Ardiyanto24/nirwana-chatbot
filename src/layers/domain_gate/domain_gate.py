"""Orkestrator Identifikasi Domain (Milestone 2.1): Identifikasi Awal ->
Verifikasi Titik Buta, TANPA retry (union aditif - lihat decisions.md
Keputusan 2).

Titik masuk `identifikasi_domain_semua()` menerima langsung output M1.7
(`list[AtomicIntentMatch]`) - filter ke status=PERLU_EKSEKUSI saja, entri
SELESAI sudah py jawaban dari Session Memory, tidak butuh identifikasi
domain (langsung ke Interpretation per arsitektur §4/§5).
"""

from src.layers.domain_gate.identifikasi import identifikasi_domain
from src.layers.domain_gate.verifikasi_titik_buta import verifikasi_titik_buta
from src.observability.tracing import get_tracer
from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import AtomicIntentDomains
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.session_memory import StatusEksekusi

_TRACER_NAME = "domain_gate.domain_gate"


def identifikasi_domain_atomic_intent(
    atomic_intent: AtomicIntent,
) -> AtomicIntentDomains:
    """Gabungkan Langkah 1 (identifikasi) + Langkah 2 (verifikasi titik
    buta) untuk SATU atomic intent. Langkah 2 TIDAK dipanggil kalau Langkah
    1 gagal total - tidak ada domain_awal untuk diverifikasi."""
    hasil_awal = identifikasi_domain(atomic_intent)

    if hasil_awal.gagal:
        return AtomicIntentDomains(
            atomic_intent=atomic_intent,
            domains=[],
            status=StatusEksekusi.GAGAL_TEKNIS,
        )

    hasil_verifikasi = verifikasi_titik_buta(atomic_intent, hasil_awal.domains)

    domains_gabungan = list(
        dict.fromkeys(hasil_awal.domains + hasil_verifikasi.domain_tambahan)
    )

    status = (
        StatusEksekusi.SEBAGIAN if hasil_verifikasi.gagal else StatusEksekusi.BERHASIL
    )

    return AtomicIntentDomains(
        atomic_intent=atomic_intent,
        domains=domains_gabungan,
        status=status,
    )


def identifikasi_domain_semua(
    matches: list[AtomicIntentMatch],
) -> list[AtomicIntentDomains]:
    """Untuk seluruh atomic intent berstatus PERLU_EKSEKUSI dalam satu turn,
    identifikasi domainnya satu per satu (bukan batch - lihat decisions.md
    Keputusan 10)."""
    perlu_eksekusi = [
        m.atomic_intent for m in matches if m.status == MatchStatus.PERLU_EKSEKUSI
    ]

    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("domain_gate.identifikasi_semua") as span:
        span.set_attribute("intent.count", len(perlu_eksekusi))

        hasil = [identifikasi_domain_atomic_intent(ai) for ai in perlu_eksekusi]

        gagal_teknis_count = sum(
            1 for h in hasil if h.status == StatusEksekusi.GAGAL_TEKNIS
        )
        sebagian_count = sum(1 for h in hasil if h.status == StatusEksekusi.SEBAGIAN)
        span.set_attribute("domain_gate.gagal_teknis_count", gagal_teknis_count)
        span.set_attribute("domain_gate.sebagian_count", sebagian_count)

        return hasil
