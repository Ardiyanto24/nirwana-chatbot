"""Test whitelist parameter per-view (Milestone 3.4) - verifikasi
kelengkapan struktural (bijektif, 67 entri, tidak ada view yang gagal
parsing) + spot-check kasus konkret dari katalog data. Beda dari
drift-detection regex penuh (korpus M3.1/M3.2, transkripsi verbatim):
PARAM_WHITELIST_VIEW hasil DERIVASI (klasifikasi date-like vs bukan),
bukan transkripsi apa adanya, jadi diverifikasi lewat spot-check
terarah + jaminan struktural (nol view gagal parsing, nol parameter
terlarang bocor)."""

from src.config.katalog_view import DAFTAR_VIEW_PER_DOMAIN
from src.layers.query_engine.param_whitelist import (
    PARAM_GLOBAL,
    PARAM_TERLARANG,
    PARAM_WHITELIST_VIEW,
)


def test_bijektif_dengan_daftar_view_per_domain():
    seluruh_view_katalog = {
        v for views in DAFTAR_VIEW_PER_DOMAIN.values() for v in views
    }
    assert set(PARAM_WHITELIST_VIEW.keys()) == seluruh_view_katalog


def test_param_whitelist_view_67_entri():
    assert len(PARAM_WHITELIST_VIEW) == 67


def test_setiap_view_punya_lebih_dari_param_global_saja():
    """Bukti tidak ada view yang gagal parsing tabel kolom (kalau gagal,
    whitelist-nya cuma akan berisi limit/offset - PARAM_GLOBAL - tanpa
    satu pun kolom nyata)."""
    for view_name, whitelist in PARAM_WHITELIST_VIEW.items():
        assert len(whitelist) > len(PARAM_GLOBAL), (
            f"{view_name} sepertinya gagal parsing - whitelist cuma berisi param global"
        )


def test_param_global_selalu_ada_di_setiap_view():
    for whitelist in PARAM_WHITELIST_VIEW.values():
        assert whitelist >= PARAM_GLOBAL


def test_param_terlarang_tidak_pernah_bocor_ke_whitelist_manapun():
    for view_name, whitelist in PARAM_WHITELIST_VIEW.items():
        bocor = PARAM_TERLARANG & whitelist
        assert not bocor, f"{view_name} whitelist mengandung param terlarang: {bocor}"


def test_spot_check_v_reservation_room_type_daily():
    """Grain properti x tipe kamar x tanggal - kasus paling lengkap
    kolomnya, mencakup date-range dan kolom biasa."""
    whitelist = PARAM_WHITELIST_VIEW["v_reservation_room_type_daily"]
    assert "property_id" in whitelist
    assert "room_type_name" in whitelist
    assert "occupancy_rate" in whitelist
    # kolom tanggal -> exact + range
    assert "period_date" in whitelist
    assert "period_date_from" in whitelist
    assert "period_date_to" in whitelist


def test_spot_check_kolom_multi_per_baris_tabel_tertangkap():
    """v_reservation_channel_daily baris '| `property_id`, `property_name`,
    `region` |' - satu baris tabel mendaftar 3 kolom sekaligus."""
    whitelist = PARAM_WHITELIST_VIEW["v_reservation_channel_daily"]
    assert {"property_id", "property_name", "region"} <= whitelist


def test_spot_check_kolom_pisah_garis_miring_tertangkap():
    """v_reservation_property_daily baris '| `avg_lead_time_days` /
    `median_lead_time_days` |' - dipisah garis miring, bukan koma."""
    whitelist = PARAM_WHITELIST_VIEW["v_reservation_property_daily"]
    assert {"avg_lead_time_days", "median_lead_time_days"} <= whitelist


def test_spot_check_view_tanpa_property_id_konsisten_katalog():
    """v_financial_business_line_group_monthly eksplisit 'Tanpa property_id'
    di katalog - whitelist TIDAK boleh mengandungnya."""
    whitelist = PARAM_WHITELIST_VIEW["v_financial_business_line_group_monthly"]
    assert "property_id" not in whitelist


def test_spot_check_deskripsi_cell_tidak_ikut_terekstrak_sebagai_kolom():
    """v_maintenance_ticket_daily baris 'sla_threshold_hours' - sel
    Deskripsi memuat backtick lain (critical/high/medium/low) yang WAJIB
    tidak ikut jadi entri whitelist (bukan nama kolom, itu nilai enum
    dalam teks penjelasan)."""
    whitelist = PARAM_WHITELIST_VIEW["v_maintenance_ticket_daily"]
    assert "sla_threshold_hours" in whitelist
    for bukan_kolom in ("critical", "high", "medium", "low"):
        assert bukan_kolom not in whitelist


def test_spot_check_row_level_view_dengan_dua_kolom_tanggal():
    """v_lookup_bookings: check_in_date/check_out_date/booking_date -
    tiga kolom tanggal berbeda dalam satu view row-level."""
    whitelist = PARAM_WHITELIST_VIEW["v_lookup_bookings"]
    for kolom_tanggal in ("check_in_date", "check_out_date", "booking_date"):
        assert kolom_tanggal in whitelist
        assert f"{kolom_tanggal}_from" in whitelist
        assert f"{kolom_tanggal}_to" in whitelist


def test_spot_check_referensi_murni_property_ref():
    whitelist = PARAM_WHITELIST_VIEW["v_properties_ref"]
    assert "property_id" in whitelist
    assert "opening_date" in whitelist
    assert "opening_date_from" in whitelist
