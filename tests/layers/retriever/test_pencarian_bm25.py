"""Test pencarian BM25 (Milestone 3.1) - KK1/KK2 sumber + trigger
boundary fallback. Deterministik, murni Python, tanpa network call."""

from src.layers.retriever.pencarian_bm25 import cari_bm25
from src.schemas.domain_gate import Domain
from src.schemas.retriever import SumberPencarian


def test_kk1_okupansi_bali_ditemukan():
    """KK1 sumber: kebutuhan yang jelas cocok dengan view tertentu
    menghasilkan kandidat yang mencakup view yang benar."""
    kandidat, perlu_fallback = cari_bm25(
        "okupansi Bali bulan ini", [Domain.RESERVATION]
    )
    view_names = [k.view_name for k in kandidat]
    assert "v_reservation_room_type_daily" in view_names
    assert perlu_fallback is False


def test_kk2_zero_leakage_domain_tidak_diizinkan():
    """KK2 sumber: kandidat terbatas domain yang diizinkan - tidak ada
    kandidat dari domain yang seharusnya ditolak, meski secara leksikal
    view itu paling relevan untuk query-nya."""
    kandidat, _ = cari_bm25("okupansi Bali bulan ini", [Domain.FNB])
    domains_muncul = {k.domain for k in kandidat}
    assert Domain.RESERVATION not in domains_muncul
    for k in kandidat:
        assert k.domain == Domain.FNB


def test_trigger_boundary_tanpa_overlap_leksikal():
    """Query tanpa overlap leksikal sama sekali terhadap korpus domain
    yang diizinkan wajib memicu fallback."""
    kandidat, perlu_fallback = cari_bm25("xyzzy qwerty asdf", [Domain.RESERVATION])
    assert kandidat == []
    assert perlu_fallback is True


def test_kandidat_terurut_skor_menurun():
    kandidat, _ = cari_bm25(
        "okupansi kamar dan revenue per tipe kamar", [Domain.RESERVATION]
    )
    skor_list = [k.skor for k in kandidat]
    assert skor_list == sorted(skor_list, reverse=True)


def test_sumber_selalu_bm25():
    kandidat, _ = cari_bm25("okupansi Bali bulan ini", [Domain.RESERVATION])
    assert all(k.sumber == SumberPencarian.BM25 for k in kandidat)


def test_domain_diizinkan_kosong_selalu_fallback():
    kandidat, perlu_fallback = cari_bm25("okupansi Bali bulan ini", [])
    assert kandidat == []
    assert perlu_fallback is True


def test_query_hanya_stopword_memicu_fallback():
    """Regresi Checkpoint 9: sebelum stopword filtering ditambahkan, query
    yang isinya murni kata fungsi umum ("yang", "dan", "di", "ini") akan
    kebetulan "cocok" hampir seluruh 67 view (kata-kata ini muncul di
    hampir semua teks Fungsi), membuat perlu_fallback SALAH-negatif
    (tidak pernah True padahal query ini secara semantik kosong makna).
    Dengan stopword filtering, tokenisasi query ini menghasilkan list
    kosong -> otomatis 0 kandidat -> fallback benar terpicu."""
    kandidat, perlu_fallback = cari_bm25(
        "yang ini itu dan di ke dari untuk dengan", [Domain.RESERVATION]
    )
    assert kandidat == []
    assert perlu_fallback is True


def test_typo_okupansi_memicu_fallback():
    """Skenario B3 evals/3.1-.../rancangan.md: typo memutus exact-match
    token BM25 sepenuhnya (tanpa kata bermakna lain yang overlap) ->
    fallback wajib terpicu. Regresi eksplisit karena ini kasus nyata yang
    ditemukan gagal terdeteksi sebelum stopword filtering ditambahkan."""
    kandidat, perlu_fallback = cari_bm25(
        "okupasi hotel minggu ini gimana", [Domain.RESERVATION]
    )
    assert kandidat == []
    assert perlu_fallback is True
