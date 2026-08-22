"""Test taksonomi grain terstruktur (Milestone 3.3) - beda sifat dari
test_korpus_view.py/test_definisi_view.py (M3.1/M3.2): grain_view.py
adalah KLASIFIKASI/JUDGMENT (dibaca dari prosa baris "Sumber" katalog),
bukan transkripsi verbatim, jadi tidak ada drift-detection regex penuh
yang mungkin - verifikasi di sini adalah kelengkapan struktural
(bijektif, 67 entri) + spot-check kasus jelas dari katalog + bukti
jalur hybrid genuinely dipicu (minimal satu entri tidak_pasti)."""

from src.config.katalog_view import DAFTAR_VIEW_PER_DOMAIN
from src.layers.retriever.grain_view import GRAIN_STRUKTURAL_VIEW, KarakteristikGrain

_NILAI_VALID = {"ya", "tidak", "tidak_pasti"}


def test_bijektif_dengan_daftar_view_per_domain():
    seluruh_view_katalog = {
        v for views in DAFTAR_VIEW_PER_DOMAIN.values() for v in views
    }
    assert set(GRAIN_STRUKTURAL_VIEW.keys()) == seluruh_view_katalog


def test_grain_strukturral_67_entri():
    assert len(GRAIN_STRUKTURAL_VIEW) == 67


def test_seluruh_entri_bertipe_karakteristik_grain_dengan_nilai_valid():
    for view_name, grain in GRAIN_STRUKTURAL_VIEW.items():
        assert isinstance(grain, KarakteristikGrain), view_name
        assert grain.punya_time_series in _NILAI_VALID, view_name
        assert grain.punya_dimensi_pembanding in _NILAI_VALID, view_name
        assert grain.catatan, view_name


def test_spot_check_view_time_series_dan_pembanding_jelas():
    """v_reservation_room_type_daily: grain properti x tipe kamar x
    tanggal - contoh paling jelas dari katalog untuk kedua sinyal ya."""
    grain = GRAIN_STRUKTURAL_VIEW["v_reservation_room_type_daily"]
    assert grain.punya_time_series == "ya"
    assert grain.punya_dimensi_pembanding == "ya"


def test_spot_check_view_snapshot_tanpa_pernyataan_tren_historis_eksplisit_ambigu():
    """v_facility_room_status_daily/v_hr_headcount_status_daily bertanda
    '(snapshot)' di grain TAPI tanpa pernyataan eksplisit 'tidak ada tren
    historis' (beda dari v_hr_turnover_snapshot) - REVISI Checkpoint 7
    (eval Promptfoo menemukan model punya argumen masuk akal bahwa
    period_date berulang harian bisa membentuk tren state-per-hari).
    Diklasifikasi tidak_pasti (ambigu), bukan tidak (pasti) - dilempar ke
    fallback LLM, bukan ditebak deterministik. Lihat decisions.md
    Keputusan 1 addendum."""
    assert (
        GRAIN_STRUKTURAL_VIEW["v_facility_room_status_daily"].punya_time_series
        == "tidak_pasti"
    )
    assert (
        GRAIN_STRUKTURAL_VIEW["v_hr_headcount_status_daily"].punya_time_series
        == "tidak_pasti"
    )


def test_spot_check_view_snapshot_hr_turnover_pernyataan_eksplisit_tidak_ada_tren():
    """v_hr_turnover_snapshot TETAP tidak (pasti) - teks Fungsi katalog
    eksplisit menyatakan 'tidak ada tren historis (data sumber tidak
    punya tanggal resign)', beda dari dua view di atas yang tidak punya
    pernyataan serupa."""
    assert GRAIN_STRUKTURAL_VIEW["v_hr_turnover_snapshot"].punya_time_series == "tidak"


def test_spot_check_view_referensi_murni_tanpa_metrik():
    """v_properties_ref - tabel master (nama, region, tanggal buka)
    tanpa metrik bisnis apa pun, tidak relevan untuk tren/perbandingan."""
    grain = GRAIN_STRUKTURAL_VIEW["v_properties_ref"]
    assert grain.punya_time_series == "tidak"
    assert grain.punya_dimensi_pembanding == "tidak"


def test_spot_check_row_level_dengan_label_periode_eksplisit_dianggap_pasti():
    """v_lookup_payroll: row-level TAPI grain eksplisit '1 baris = 1
    karyawan x 1 bulan' (label entitas x periode jelas, mirror
    hr_employee_monthly) - beda dari row-level log event tanpa label
    periode yang diklasifikasi tidak_pasti."""
    grain = GRAIN_STRUKTURAL_VIEW["v_lookup_payroll"]
    assert grain.punya_time_series == "ya"
    assert grain.punya_dimensi_pembanding == "ya"


def test_minimal_satu_view_diklasifikasi_tidak_pasti_untuk_time_series():
    """Bukti jalur hybrid genuinely akan terpakai (bukan teori kosong) -
    kandidat row-level tanpa label periode eksplisit (mis. v_lookup_bookings,
    '1 baris = 1 reservasi') diklasifikasi ambigu, dilempar ke fallback LLM."""
    tidak_pasti = [
        v
        for v, g in GRAIN_STRUKTURAL_VIEW.items()
        if g.punya_time_series == "tidak_pasti"
    ]
    assert len(tidak_pasti) > 0
    assert "v_lookup_bookings" in tidak_pasti


def test_minimal_satu_view_diklasifikasi_tidak_pasti_untuk_dimensi_pembanding():
    tidak_pasti = [
        v
        for v, g in GRAIN_STRUKTURAL_VIEW.items()
        if g.punya_dimensi_pembanding == "tidak_pasti"
    ]
    assert len(tidak_pasti) > 0
