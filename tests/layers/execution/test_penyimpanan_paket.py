"""Test suite Penyusunan dan Penyimpanan Paket Session Memory (Milestone
4.3) - src/layers/execution/penyimpanan_paket.py. `store_session_memory`
di-monkeypatch (isolasi dari DB nyata) - round-trip Supabase sungguhan
ada di test_penyimpanan_paket_integrasi.py (Checkpoint 5)."""

import uuid

import pytest

from src.layers.execution import penyimpanan_paket as modul
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.execution import HasilEksekusiAtomicIntent
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest

_VIEW_TERDAFTAR = "v_lookup_maintenance_tickets"  # punya catatan utk room_id


def _buat_atomic_intent() -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan="tiket maintenance bulan ini",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _patch_store(monkeypatch):
    dipanggil: dict = {}

    def _fake_store(package):
        dipanggil["package"] = package

    monkeypatch.setattr(modul, "store_session_memory", _fake_store)
    return dipanggil


# --- _bungkus_nilai_hasil ----------------------------------------------


def test_bungkus_list_jadi_rows():
    assert modul._bungkus_nilai_hasil([{"a": 1}, {"a": 2}]) == {"rows": [{"a": 1}, {"a": 2}]}


def test_bungkus_none_jadi_rows_kosong():
    assert modul._bungkus_nilai_hasil(None) == {"rows": []}


def test_bungkus_list_kosong_jadi_rows_kosong():
    assert modul._bungkus_nilai_hasil([]) == {"rows": []}


# --- _catatan_interpretasi_untuk_hasil ----------------------------------


def test_catatan_kolom_null_terdaftar_katalog_menghasilkan_catatan():
    nilai_hasil = [{"ticket_id": "T1", "room_id": None, "property_id": "P01"}]
    catatan = modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, nilai_hasil)
    assert len(catatan) == 1
    assert "fasilitas umum" in catatan[0]


def test_catatan_kolom_null_tidak_terdaftar_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"ticket_id": "T1", "kolom_tidak_dikenal": None}]
    catatan = modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, nilai_hasil)
    assert catatan == []


def test_catatan_kolom_terdaftar_tapi_tidak_null_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"ticket_id": "T1", "room_id": "R101"}]
    catatan = modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, nilai_hasil)
    assert catatan == []


def test_catatan_view_name_none_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"room_id": None}]
    assert modul._catatan_interpretasi_untuk_hasil(None, nilai_hasil) == []


def test_catatan_view_tidak_terdaftar_katalog_tidak_menghasilkan_apa_apa():
    nilai_hasil = [{"kolom_apapun": None}]
    assert modul._catatan_interpretasi_untuk_hasil("v_view_lain_yang_tidak_ada_di_katalog", nilai_hasil) == []


def test_catatan_nilai_hasil_kosong_tidak_menghasilkan_apa_apa():
    assert modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, []) == []
    assert modul._catatan_interpretasi_untuk_hasil(_VIEW_TERDAFTAR, None) == []


# --- _catatan_kualitas_data (Revisit 2026-08-17, Keputusan 9) -----------


def test_catatan_kualitas_sebagian_flagged():
    catatan = modul._catatan_kualitas_data(StatusEksekusi.SEBAGIAN, "flagged", None)
    assert len(catatan) == 1
    assert "flagged" in catatan[0]
    assert "perlu perhatian" in catatan[0]


def test_catatan_kualitas_sebagian_stale():
    catatan = modul._catatan_kualitas_data(StatusEksekusi.SEBAGIAN, "ok", "2020-01-01T00:00:00+00:00")
    assert len(catatan) == 1
    assert "2020-01-01T00:00:00+00:00" in catatan[0]
    assert "ambang kesegaran" in catatan[0]


def test_catatan_kualitas_sebagian_flagged_dan_stale_prioritas_flagged():
    catatan = modul._catatan_kualitas_data(StatusEksekusi.SEBAGIAN, "flagged", "2020-01-01T00:00:00+00:00")
    assert len(catatan) == 1
    assert "flagged" in catatan[0]


def test_catatan_kualitas_berhasil_tidak_diketahui():
    catatan = modul._catatan_kualitas_data(StatusEksekusi.BERHASIL, None, None)
    assert len(catatan) == 1
    assert "belum diketahui" in catatan[0]


def test_catatan_kualitas_berhasil_ok_tidak_ada_catatan():
    """Kualitas dikonfirmasi ok - tidak perlu catatan apa pun (tidak
    mengotori catatan_interpretasi dengan 'semua baik-baik saja')."""
    assert modul._catatan_kualitas_data(StatusEksekusi.BERHASIL, "ok", "2026-08-17T00:00:00+00:00") == []


def test_catatan_kualitas_gagal_teknis_tidak_menghasilkan_apa_apa():
    assert modul._catatan_kualitas_data(StatusEksekusi.GAGAL_TEKNIS, None, None) == []


# --- susun_dan_simpan_paket (orkestrator) -------------------------------


def test_orkestrator_berhasil_lengkap(monkeypatch):
    dipanggil = _patch_store(monkeypatch)
    ai = _buat_atomic_intent()
    nilai_hasil = [{"ticket_id": "T1", "room_id": None, "property_id": "P01"}]

    # data_quality_status="ok" - fokus test ini murni catatan nullable-
    # bermakna, bukan catatan kualitas data (diuji terpisah di atas dan
    # di test_orkestrator_catatan_nullable_dan_kualitas_digabung_bukan_menimpa).
    hasil = modul.susun_dan_simpan_paket(
        ai,
        "sess-1",
        3,
        StatusEksekusi.BERHASIL,
        view_name=_VIEW_TERDAFTAR,
        nilai_hasil=nilai_hasil,
        data_quality_status="ok",
    )

    assert hasil.atomic_intent_id == ai.atomic_intent_id
    assert hasil.session_id == "sess-1"
    assert hasil.turn_index == 3
    assert hasil.teks_kebutuhan == ai.teks_kebutuhan
    assert hasil.label_bentuk_jawaban == ai.label_bentuk_jawaban
    assert hasil.nilai_hasil == {"rows": nilai_hasil}
    assert len(hasil.catatan_interpretasi) == 1
    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.sumber == "eksekusi_baru"
    assert dipanggil["package"] == hasil


def test_orkestrator_gagal_teknis_tanpa_nilai_hasil(monkeypatch):
    dipanggil = _patch_store(monkeypatch)
    ai = _buat_atomic_intent()

    hasil = modul.susun_dan_simpan_paket(ai, "sess-1", 1, StatusEksekusi.GAGAL_TEKNIS)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.nilai_hasil == {"rows": []}
    assert hasil.catatan_interpretasi == []
    assert dipanggil["package"] == hasil


def test_orkestrator_sumber_selalu_eksekusi_baru(monkeypatch):
    _patch_store(monkeypatch)
    hasil = modul.susun_dan_simpan_paket(
        _buat_atomic_intent(), "sess-1", 1, StatusEksekusi.BERHASIL, nilai_hasil=[]
    )
    assert hasil.sumber == "eksekusi_baru"


def test_orkestrator_sebagian_dengan_catatan_kualitas(monkeypatch):
    dipanggil = _patch_store(monkeypatch)
    ai = _buat_atomic_intent()

    hasil = modul.susun_dan_simpan_paket(
        ai,
        "sess-1",
        1,
        StatusEksekusi.SEBAGIAN,
        nilai_hasil=[{"a": 1}],
        data_quality_status="flagged",
    )

    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert len(hasil.catatan_interpretasi) == 1
    assert "flagged" in hasil.catatan_interpretasi[0]
    assert dipanggil["package"] == hasil


def test_orkestrator_catatan_nullable_dan_kualitas_digabung_bukan_menimpa(monkeypatch):
    """Skenario gabungan: hasil punya kolom null terdaftar katalog
    nullable-bermakna DAN kualitas data tidak diketahui sekaligus - dua
    catatan harus muncul bersamaan, bukan salah satu menimpa yang lain."""
    _patch_store(monkeypatch)
    ai = _buat_atomic_intent()
    nilai_hasil = [{"ticket_id": "T1", "room_id": None, "property_id": "P01"}]

    hasil = modul.susun_dan_simpan_paket(
        ai,
        "sess-1",
        1,
        StatusEksekusi.BERHASIL,
        view_name=_VIEW_TERDAFTAR,
        nilai_hasil=nilai_hasil,
        data_quality_status=None,
    )

    assert len(hasil.catatan_interpretasi) == 2
    assert any("fasilitas umum" in c for c in hasil.catatan_interpretasi)
    assert any("belum diketahui" in c for c in hasil.catatan_interpretasi)


def test_orkestrator_exception_store_diteruskan_apa_adanya(monkeypatch):
    def _fake_store_gagal(package):
        raise RuntimeError("simulasi DB gagal")

    monkeypatch.setattr(modul, "store_session_memory", _fake_store_gagal)

    with pytest.raises(RuntimeError, match="simulasi DB gagal"):
        modul.susun_dan_simpan_paket(_buat_atomic_intent(), "sess-1", 1, StatusEksekusi.BERHASIL)


# --- susun_dan_simpan_paket_semua() (Milestone 7.15) ------------------------


def _buat_hasil_eksekusi(
    atomic_intent: AtomicIntent,
    status: StatusEksekusi = StatusEksekusi.BERHASIL,
    nilai_hasil=None,
    kegagalan_alasan: str | None = None,
) -> HasilEksekusiAtomicIntent:
    if status == StatusEksekusi.GAGAL_TEKNIS:
        return HasilEksekusiAtomicIntent(
            atomic_intent=atomic_intent,
            status=status,
            nilai_hasil=None,
            kegagalan_alasan=kegagalan_alasan or "simulasi gagal",
        )
    return HasilEksekusiAtomicIntent(
        atomic_intent=atomic_intent, status=status, nilai_hasil=nilai_hasil or [{"a": 1}]
    )


def _buat_vg_entry(atomic_intent: AtomicIntent, view_name: str) -> tuple[AtomicIntent, HasilVerifikasiGate]:
    request = QueryEngineRequest(domain=Domain.FACILITY, view_name=view_name, params={})
    return atomic_intent, HasilVerifikasiGate(request_final=request, lolos=True, terkoreksi=False)


def test_susun_dan_simpan_paket_semua_list_kosong_hasil_kosong(monkeypatch):
    _patch_store(monkeypatch)
    assert modul.susun_dan_simpan_paket_semua([], [], "sess-1", 1) == []


def test_susun_dan_simpan_paket_semua_argumen_benar_per_item(monkeypatch):
    dipanggil = _patch_store(monkeypatch)
    ai = _buat_atomic_intent()
    eksekusi = _buat_hasil_eksekusi(ai, StatusEksekusi.BERHASIL, nilai_hasil=[{"x": 1}])
    vg_result = [_buat_vg_entry(ai, _VIEW_TERDAFTAR)]

    hasil = modul.susun_dan_simpan_paket_semua([eksekusi], vg_result, "sess-1", 7)

    assert len(hasil) == 1
    paket = hasil[0]
    assert paket.atomic_intent_id == ai.atomic_intent_id
    assert paket.session_id == "sess-1"
    assert paket.turn_index == 7
    assert paket.status == StatusEksekusi.BERHASIL
    assert paket.sumber == "eksekusi_baru"
    assert dipanggil["package"] == paket


def test_susun_dan_simpan_paket_semua_status_diteruskan_apa_adanya(monkeypatch):
    _patch_store(monkeypatch)
    ai_berhasil = _buat_atomic_intent()
    ai_sebagian = _buat_atomic_intent()
    ai_gagal = _buat_atomic_intent()

    eksekusi = [
        _buat_hasil_eksekusi(ai_berhasil, StatusEksekusi.BERHASIL),
        _buat_hasil_eksekusi(ai_sebagian, StatusEksekusi.SEBAGIAN),
        _buat_hasil_eksekusi(ai_gagal, StatusEksekusi.GAGAL_TEKNIS),
    ]
    vg_result = [
        _buat_vg_entry(ai_berhasil, "v_a"),
        _buat_vg_entry(ai_sebagian, "v_b"),
        _buat_vg_entry(ai_gagal, "v_c"),
    ]

    hasil = modul.susun_dan_simpan_paket_semua(eksekusi, vg_result, "sess-1", 1)

    assert len(hasil) == 3
    statuses = {p.atomic_intent_id: p.status for p in hasil}
    assert statuses[ai_berhasil.atomic_intent_id] == StatusEksekusi.BERHASIL
    assert statuses[ai_sebagian.atomic_intent_id] == StatusEksekusi.SEBAGIAN
    assert statuses[ai_gagal.atomic_intent_id] == StatusEksekusi.GAGAL_TEKNIS
    # GAGAL_TEKNIS -> nilai_hasil dibungkus {"rows": []} (Keputusan 1 M4.3)
    assert hasil[2].nilai_hasil == {"rows": []}


def test_susun_dan_simpan_paket_semua_multi_item_view_name_tidak_tertukar(monkeypatch):
    """Dua item, urutan `verification_gate_result` SENGAJA dibalik dari
    urutan `execution_result` - memata-matai `susun_dan_simpan_paket()`
    langsung untuk membuktikan `view_name` yang diteruskan PERSIS benar
    per `atomic_intent_id` (lookup dict), bukan kebetulan sejajar by
    index."""
    dipanggil = []

    def _spy(atomic_intent, session_id, turn_index, status, view_name=None, **kw):
        dipanggil.append((atomic_intent.atomic_intent_id, view_name))
        return modul.SessionMemoryPackage(
            atomic_intent_id=atomic_intent.atomic_intent_id,
            session_id=session_id,
            turn_index=turn_index,
            teks_kebutuhan=atomic_intent.teks_kebutuhan,
            label_bentuk_jawaban=atomic_intent.label_bentuk_jawaban,
            nilai_hasil={"rows": []},
            catatan_interpretasi=[],
            status=status,
            sumber="eksekusi_baru",
        )

    monkeypatch.setattr(modul, "susun_dan_simpan_paket", _spy)

    ai1 = _buat_atomic_intent()
    ai2 = _buat_atomic_intent()
    eksekusi = [_buat_hasil_eksekusi(ai1), _buat_hasil_eksekusi(ai2)]
    vg_result_dibalik = [_buat_vg_entry(ai2, "v_untuk_ai2"), _buat_vg_entry(ai1, "v_untuk_ai1")]

    modul.susun_dan_simpan_paket_semua(eksekusi, vg_result_dibalik, "sess-1", 1)

    by_id = dict(dipanggil)
    assert by_id[ai1.atomic_intent_id] == "v_untuk_ai1"
    assert by_id[ai2.atomic_intent_id] == "v_untuk_ai2"
