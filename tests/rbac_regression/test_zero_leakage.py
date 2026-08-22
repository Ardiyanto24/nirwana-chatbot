"""Regression test permanen untuk skenario "zero-leakage" RBAC yang sudah
terbukti nyata di M7.11-M7.14 (Milestone 8.3). Klasifikasi Domain Gate
(LLM) di-fix ke hasil historis yang sudah terbukti benar (Keputusan 1,
decisions.md) - file ini fokus MURNI ke logika enforcement deterministik
(otorisasi + pencarian kandidat + koreksi paksa cakupan individu), TANPA
panggilan LLM sama sekali. Butuh `DATABASE_URL` (role_permissions nyata),
TIDAK butuh `OPENROUTER_API_KEY` - diverifikasi empiris (Checkpoint 2):
`cari_bm25()` 100% deterministik (rank_bm25, bukan API), skor cocok
persis data historis `evals/7.11-.../E01.json`.

Beda dari test unit `tests/layers/domain_gate/` (menguji SATU fungsi
terisolasi) - file ini menguji RANTAI enforcement lintas-layer terhadap
skenario zero-leakage nyata, sinyal kebocoran RBAC prioritas tinggi
terpisah dari `test-gate` generik (M8.2) - lihat job CI `rbac-regression`.
"""

import uuid

from src.layers.domain_gate.otorisasi import periksa_otorisasi_semua
from src.layers.retriever.pencarian_bm25 import cari_bm25
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


def _buat_atomic_intent(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _domain_diizinkan(role_title: str, domains: list[Domain]) -> list[Domain]:
    """Panggilan NYATA periksa_otorisasi_semua() (DATABASE_URL, deterministik,
    TANPA LLM) - mengembalikan hanya domain yang diizinkan role_title saat ini."""
    ai = _buat_atomic_intent("placeholder")
    aid = AtomicIntentDomains(
        atomic_intent=ai, domains=domains, status=StatusEksekusi.BERHASIL
    )
    hasil = periksa_otorisasi_semua([aid], role_title)
    return [d.domain for d in hasil[0].domain_decisions if d.diizinkan]


# --- Skenario 1: gop_margin (Front Office Staff) ----------------------------
#
# Reuse skenario nyata evals/7.11-sambungan-retriever/payloads/E01.json -
# domain teridentifikasi Domain Gate (LLM) DI-FIX ke hasil historis yang
# sudah terbukti benar (Keputusan 1, decisions.md), bukan dipanggil ulang.


def test_gop_margin_financial_ditolak_view_reservation_tetap_benar():
    """Front Office Staff (hanya domain reservation diizinkan) tanya
    gop_margin - domain teridentifikasi [reservation, financial,
    properties_ref] (hasil historis Domain Gate M2.1, di-fix di sini).
    Zero-leakage: financial DITOLAK otorisasi NYATA, TAPI kandidat view
    tetap ditemukan dari domain reservation yang diizinkan - financial
    TIDAK PERNAH muncul sebagai kandidat."""
    role_title = "Front Office Staff"
    domain_teridentifikasi = [
        Domain.RESERVATION,
        Domain.FINANCIAL,
        Domain.PROPERTIES_REF,
    ]

    domain_diizinkan = _domain_diizinkan(role_title, domain_teridentifikasi)
    assert Domain.FINANCIAL not in domain_diizinkan
    assert Domain.RESERVATION in domain_diizinkan

    kandidat, perlu_fallback = cari_bm25(
        "Bagaimana hubungan antara deviasi harga dan gop_margin properti di Bali?",
        domain_diizinkan,
    )
    assert perlu_fallback is False, (
        "BM25 harus cukup sendiri (fallback embedding = panggilan LLM)"
    )
    assert not any(k.domain == Domain.FINANCIAL for k in kandidat), (
        "KEBOCORAN: kandidat dari domain financial yang ditolak muncul di hasil pencarian"
    )
    assert any(k.view_name == "v_reservation_gop_impact_monthly" for k in kandidat), (
        "view reservation yang seharusnya tetap ditemukan malah hilang"
    )
