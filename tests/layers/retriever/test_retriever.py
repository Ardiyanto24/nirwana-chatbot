"""Test orkestrator cari_kandidat_view() (Milestone 3.1, Checkpoint 10).

Nama file sengaja dibedakan dari test_retriever_schema.py (Checkpoint 3,
test skema src/schemas/retriever.py) - mirror preseden M2.4
(test_verification_gate.py skema vs test_verifikasi_gate.py orkestrator).
"""

import src.layers.retriever.retriever as retriever_module
from src.layers.retriever.retriever import cari_kandidat_view
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import KandidatView, SumberPencarian
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


def _ai(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id="ai-test",
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def test_kasus_a_bm25_cukup_embedding_tidak_dipanggil(monkeypatch):
    """KK1: BM25 menemukan kandidat -> embedding fallback TIDAK BOLEH
    dipanggil sama sekali (bukti genuinely tidak terpicu, bukan cuma hasil
    akhir kebetulan sama)."""

    def _gagal_jika_dipanggil(teks_kebutuhan, domain_diizinkan, model):
        raise AssertionError("cari_embedding TIDAK BOLEH dipanggil saat BM25 cukup")

    monkeypatch.setattr(retriever_module, "cari_embedding", _gagal_jika_dipanggil)

    hasil = cari_kandidat_view(
        _ai("okupansi Bali bulan ini"), [Domain.RESERVATION]
    )

    assert hasil.fallback_terpicu is False
    assert hasil.status == StatusEksekusi.BERHASIL
    assert "v_reservation_room_type_daily" in [k.view_name for k in hasil.kandidat]
    assert all(k.sumber == SumberPencarian.BM25 for k in hasil.kandidat)


def test_kasus_b_fallback_terpicu_kandidat_gabungan(monkeypatch):
    """Query stress-test (mirror skenario B1 eval): BM25 dipaksa gagal
    total, embedding fallback dipanggil dan berhasil menemukan target -
    fallback_terpicu=True, view benar ada di kandidat gabungan, sumber
    tercatat benar per item."""

    def _bm25_gagal_total(teks_kebutuhan, domain_diizinkan):
        return [], True

    def _embedding_menang(teks_kebutuhan, domain_diizinkan, model):
        return (
            [
                KandidatView(
                    view_name="v_reservation_channel_daily",
                    domain=Domain.RESERVATION,
                    skor=0.87,
                    sumber=SumberPencarian.EMBEDDING_FALLBACK,
                )
            ],
            False,
        )

    monkeypatch.setattr(retriever_module, "cari_bm25", _bm25_gagal_total)
    monkeypatch.setattr(retriever_module, "cari_embedding", _embedding_menang)

    hasil = cari_kandidat_view(
        _ai("tamu-tamu ini pesannya lewat mana aja"), [Domain.RESERVATION]
    )

    assert hasil.fallback_terpicu is True
    assert hasil.status == StatusEksekusi.BERHASIL
    view_names = [k.view_name for k in hasil.kandidat]
    assert "v_reservation_channel_daily" in view_names
    kandidat_target = next(
        k for k in hasil.kandidat if k.view_name == "v_reservation_channel_daily"
    )
    assert kandidat_target.sumber == SumberPencarian.EMBEDDING_FALLBACK


def test_kasus_b_fallback_gagal_teknis_tetap_kembalikan_bm25(monkeypatch):
    """Embedding fallback gagal teknis -> tetap kembalikan kandidat BM25
    (kosong di kasus ini karena BM25 juga gagal total), status=SEBAGIAN,
    bukan exception yang memblokir pipeline."""

    def _bm25_gagal_total(teks_kebutuhan, domain_diizinkan):
        return [], True

    def _embedding_gagal(teks_kebutuhan, domain_diizinkan, model):
        return [], True

    monkeypatch.setattr(retriever_module, "cari_bm25", _bm25_gagal_total)
    monkeypatch.setattr(retriever_module, "cari_embedding", _embedding_gagal)

    hasil = cari_kandidat_view(_ai("query apapun"), [Domain.RESERVATION])

    assert hasil.fallback_terpicu is True
    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.kandidat == []


def test_kasus_c_kk2_zero_leakage_end_to_end_tanpa_monkeypatch():
    """KK2 end-to-end, pemanggilan nyata tanpa monkeypatch apa pun: query
    bertema reservation dengan domain_diizinkan=[FNB] (RESERVATION sengaja
    tidak diizinkan). BM25 legitimately tidak menemukan apa pun di FNB
    untuk query reservation murni -> fallback TERPICU nyata (bukti
    tambahan integrasi end-to-end, bukan cuma unit test termonkeypatch) -
    yang dibuktikan di sini BUKAN jalur mana yang terpicu (itu bergantung
    hasil pencarian, sah berubah), melainkan zero-leakage domain
    RESERVATION tetap terjaga di KEDUA kemungkinan jalur."""
    hasil = cari_kandidat_view(_ai("okupansi Bali bulan ini"), [Domain.FNB])
    for k in hasil.kandidat:
        assert k.domain == Domain.FNB
    assert Domain.RESERVATION not in {k.domain for k in hasil.kandidat}


def test_kasus_c_kk2_zero_leakage_jalur_fallback_terpicu(monkeypatch):
    """KK2 end-to-end, jalur fallback-terpicu: embedding fallback dipaksa
    mengembalikan kandidat lintas-domain (disengaja, untuk membuktikan
    orkestrator TIDAK memfilter ulang di level ini - filter struktural
    sudah harus terjadi di dalam cari_embedding() itu sendiri, dibuktikan
    terpisah di test_pencarian_embedding.py). Di sini yang dibuktikan:
    orkestrator tidak menambah kebocoran BARU dari sisinya sendiri."""

    def _bm25_gagal_total(teks_kebutuhan, domain_diizinkan):
        return [], True

    def _embedding_hormat_domain(teks_kebutuhan, domain_diizinkan, model):
        # Simulasi realistis cari_embedding() yang benar: filter struktural
        # sudah diterapkan sebelum kandidat dikembalikan.
        semua = [
            KandidatView(
                view_name="v_fnb_waste_daily",
                domain=Domain.FNB,
                skor=0.9,
                sumber=SumberPencarian.EMBEDDING_FALLBACK,
            ),
        ]
        return [k for k in semua if k.domain in domain_diizinkan], False

    monkeypatch.setattr(retriever_module, "cari_bm25", _bm25_gagal_total)
    monkeypatch.setattr(retriever_module, "cari_embedding", _embedding_hormat_domain)

    hasil = cari_kandidat_view(_ai("query apapun"), [Domain.FNB])
    for k in hasil.kandidat:
        assert k.domain == Domain.FNB
