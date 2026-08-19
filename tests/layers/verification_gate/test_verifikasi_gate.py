"""Test suite mekanisme Verification Gate (Milestone 2.4).

File ini dibangun bertahap lintas checkpoint (preseden pola M2.2/M2.3):
- Checkpoint 5 (Task 7-8): cek 1 (bentuk request statis).
- Checkpoint 6 (Task 9-10): cek 2 (kepatuhan sumber, KK2).
- Checkpoint 7 (Task 11-12): cek 3-4 (penegakan constraint, KK1).
- Checkpoint 8 (Task 13-14): orkestrator + KK1-3 end-to-end.
"""

import os
import uuid

import pytest

import src.layers.verification_gate.verifikasi_gate as verifikasi_gate_module
from src.config.employees import load_employees
from src.layers.verification_gate.verifikasi_gate import (
    tegakkan_constraint_cakupan_individu,
    verifikasi_bentuk_request_statis,
    verifikasi_gate,
    verifikasi_gate_semua,
    verifikasi_kelengkapan_penegakan,
    verifikasi_kepatuhan_sumber,
)
from src.schemas.cakupan_individu import AtomicIntentConstraint, ConstraintCakupanIndividu
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.retriever import HasilKecukupanStruktural
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest


def _buat_request(
    domain: Domain = Domain.FACILITY,
    view_name: str = "v_housekeeping_staff_daily",
    params: dict | None = None,
) -> QueryEngineRequest:
    return QueryEngineRequest(domain=domain, view_name=view_name, params=params or {})


# --- Cek 1: Bentuk Request Statis -------------------------------------------


def test_cek1_request_valid_lolos():
    lolos, alasan = verifikasi_bentuk_request_statis(_buat_request())
    assert lolos is True
    assert alasan is None


def test_cek1_view_name_tidak_ada_di_domain_manapun():
    request = _buat_request(view_name="v_view_karangan_tidak_ada")
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is False
    assert alasan is not None and "v_view_karangan_tidak_ada" in alasan


def test_cek1_view_name_ada_tapi_di_domain_lain():
    """v_hr_employee_monthly ada di domain hr, bukan facility."""
    request = _buat_request(domain=Domain.FACILITY, view_name="v_hr_employee_monthly")
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is False
    assert alasan is not None and "facility" in alasan


def test_cek1_limit_melebihi_1000():
    request = _buat_request(params={"limit": 1001})
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is False
    assert alasan is not None and "1001" in alasan


def test_cek1_limit_persis_1000_masih_lolos():
    request = _buat_request(params={"limit": 1000})
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is True


def test_cek1_tanpa_limit_lolos():
    request = _buat_request(params={"employee_id": "E0002"})
    lolos, alasan = verifikasi_bentuk_request_statis(request)
    assert lolos is True


# --- Cek 2: Kepatuhan Sumber (KK2) -------------------------------------------


def test_cek2_kk2_view_name_sengaja_tidak_cocok_ditolak():
    """KK2: view_name request SENGAJA dibuat tidak cocok dengan yang
    divalidasi Retriever - harus ditolak, alasan menyebut ketidaksesuaian."""
    request = _buat_request(view_name="v_housekeeping_staff_daily")
    lolos, alasan = verifikasi_kepatuhan_sumber(
        request, view_name_tervalidasi_retriever="v_maintenance_technician_daily"
    )
    assert lolos is False
    assert alasan is not None
    assert "v_housekeeping_staff_daily" in alasan
    assert "v_maintenance_technician_daily" in alasan


def test_cek2_view_name_cocok_lolos():
    request = _buat_request(view_name="v_housekeeping_staff_daily")
    lolos, alasan = verifikasi_kepatuhan_sumber(
        request, view_name_tervalidasi_retriever="v_housekeeping_staff_daily"
    )
    assert lolos is True
    assert alasan is None


# --- Cek 3-4: Penegakan Constraint + Kelengkapan (KK1) ----------------------


def test_kk1_constraint_terdeteksi_params_belum_benar_dikoreksi_paksa():
    """KK1: constraint terdeteksi, params BELUM menyertakan employee_id
    caller yang benar - harus DIKOREKSI PAKSA, bukan ditolak."""
    request = _buat_request(params={})
    constraint = ConstraintCakupanIndividu(terdeteksi=True, alasan="performa individu")

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request, constraint, employee_id="E0002"
    )

    assert terkoreksi is True
    assert request_terkoreksi.params["employee_id"] == "E0002"

    lolos, alasan = verifikasi_kelengkapan_penegakan(
        request_terkoreksi, constraint, employee_id="E0002"
    )
    assert lolos is True
    assert alasan is None


def test_kk1_constraint_terdeteksi_params_sudah_benar_tidak_dikoreksi_ulang():
    request = _buat_request(params={"employee_id": "E0002"})
    constraint = ConstraintCakupanIndividu(terdeteksi=True, alasan="performa individu")

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request, constraint, employee_id="E0002"
    )

    assert terkoreksi is False
    assert request_terkoreksi.params["employee_id"] == "E0002"


def test_constraint_tidak_terdeteksi_params_tidak_diubah_sama_sekali():
    request = _buat_request(params={"limit": 50})
    constraint = ConstraintCakupanIndividu(terdeteksi=False)

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request, constraint, employee_id="E0002"
    )

    assert terkoreksi is False
    assert request_terkoreksi.params == {"limit": 50}
    assert "employee_id" not in request_terkoreksi.params

    lolos, alasan = verifikasi_kelengkapan_penegakan(
        request_terkoreksi, constraint, employee_id="E0002"
    )
    assert lolos is True


# --- Orkestrator: KK1-3 End-to-End (fixture nyata tabel employees) ---------

pytestmark_db = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL tidak diset - skip test yang butuh koneksi database nyata",
)


def _ambil_employee(role_title: str):
    kandidat = [e for e in load_employees() if e.role_title == role_title]
    assert kandidat, f"Tidak ada fixture employee dengan role_title={role_title!r}"
    return kandidat[0]


@pytestmark_db
def test_orkestrator_kk1_constraint_terdeteksi_dikoreksi_paksa():
    """KK1: request membawa catatan constraint dari M2.3 tapi belum
    menyertakan filter yang sesuai - berhasil dikoreksi paksa, BUKAN
    ditolak."""
    employee = _ambil_employee("Housekeeping Staff")
    request = _buat_request(
        domain=Domain.FACILITY, view_name="v_housekeeping_staff_daily", params={}
    )
    constraint = ConstraintCakupanIndividu(terdeteksi=True, alasan="performa individu")

    hasil = verifikasi_gate(
        request,
        constraint,
        employee_id=employee.employee_id,
        view_name_tervalidasi_retriever="v_housekeeping_staff_daily",
    )

    assert hasil.lolos is True
    assert hasil.terkoreksi is True
    assert hasil.request_final is not None
    assert hasil.request_final.params["employee_id"] == employee.employee_id


@pytestmark_db
def test_orkestrator_kk2_view_name_tidak_sesuai_ditolak():
    """KK2: view_name request tidak sesuai dengan yang divalidasi
    Retriever - ditolak dengan alasan spesifik menyebut ketidaksesuaian."""
    employee = _ambil_employee("Maintenance Staff")
    request = _buat_request(
        domain=Domain.FACILITY, view_name="v_maintenance_technician_daily", params={}
    )
    constraint = ConstraintCakupanIndividu(terdeteksi=False)

    hasil = verifikasi_gate(
        request,
        constraint,
        employee_id=employee.employee_id,
        view_name_tervalidasi_retriever="v_lookup_maintenance_tickets",
    )

    assert hasil.lolos is False
    assert hasil.request_final is None
    assert hasil.alasan_penolakan is not None
    assert "v_maintenance_technician_daily" in hasil.alasan_penolakan
    assert "v_lookup_maintenance_tickets" in hasil.alasan_penolakan


@pytestmark_db
def test_orkestrator_kk3_request_sudah_benar_lolos_tanpa_perubahan():
    """KK3: request sudah benar sepenuhnya (tanpa pelanggaran struktural,
    constraint sudah ditegakkan dengan benar) - lolos TANPA perubahan
    apa pun."""
    employee = _ambil_employee("HR Staff")
    params_asli = {"limit": 50, "employee_id": employee.employee_id}
    request = _buat_request(
        domain=Domain.HR, view_name="v_hr_watchlist_monthly", params=params_asli
    )
    constraint = ConstraintCakupanIndividu(terdeteksi=True, alasan="performa individu")

    hasil = verifikasi_gate(
        request,
        constraint,
        employee_id=employee.employee_id,
        view_name_tervalidasi_retriever="v_hr_watchlist_monthly",
    )

    assert hasil.lolos is True
    assert hasil.terkoreksi is False
    assert hasil.request_final is not None
    assert hasil.request_final.params == params_asli


# --- verifikasi_gate_semua (orkestrator batch, Milestone 7.13) -------------


def _buat_atomic_intent(teks: str = "kebutuhan uji") -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )


def _buat_hasil_kecukupan(
    atomic_intent: AtomicIntent, view_name_final: str | None
) -> HasilKecukupanStruktural:
    from src.schemas.retriever import (
        KandidatView,
        KecukupanKandidat,
        LabelKecocokanMakna,
        SumberKeputusanKecukupan,
        SumberPencarian,
    )

    kecukupan = (
        [
            KecukupanKandidat(
                kandidat=KandidatView(
                    view_name=view_name_final,
                    domain=Domain.FACILITY,
                    skor=3.0,
                    sumber=SumberPencarian.BM25,
                ),
                kecocokan_label=LabelKecocokanMakna.DITEMUKAN,
                cukup=True,
                alasan="fixture test",
                sumber_keputusan=SumberKeputusanKecukupan.DETERMINISTIK,
            )
        ]
        if view_name_final is not None
        else []
    )
    return HasilKecukupanStruktural(
        atomic_intent=atomic_intent,
        kecukupan=kecukupan,
        view_name_final=view_name_final,
        status=StatusEksekusi.BERHASIL,
    )


def _buat_atomic_intent_constraint(
    atomic_intent: AtomicIntent, terdeteksi: bool
) -> AtomicIntentConstraint:
    return AtomicIntentConstraint(
        atomic_intent=atomic_intent,
        domain_decisions=[],
        constraint=ConstraintCakupanIndividu(
            terdeteksi=terdeteksi, alasan="fixture test" if terdeteksi else None
        ),
    )


def _buat_query_engine_entry(
    atomic_intent: AtomicIntent,
    view_name: str,
    lolos: bool | None = True,
    request: QueryEngineRequest | None = None,
) -> tuple[HasilPenyusunanRequest, HasilVerifikasiBentukRequest | None]:
    """`lolos=None` mensimulasikan hasil_verifikasi=None (M3.4 gagal total)."""
    req = request or _buat_request(view_name=view_name)
    hasil_susun = HasilPenyusunanRequest(
        atomic_intent=atomic_intent, request=req, status=StatusEksekusi.BERHASIL
    )
    if lolos is None:
        return hasil_susun, None
    hasil_verifikasi = HasilVerifikasiBentukRequest(
        atomic_intent=atomic_intent,
        request=req,
        status=StatusEksekusi.BERHASIL,
        lolos=lolos,
        alasan=None if lolos else "bentuk jawaban tidak cukup (fixture test)",
    )
    return hasil_susun, hasil_verifikasi


def test_verifikasi_gate_semua_dipanggil_dengan_argumen_benar(monkeypatch):
    """Kejadian inti M7.13 Checkpoint 2: verifikasi_gate() WAJIB menerima
    request (dari query_engine_result), constraint (dari cakupan_individu_
    result via .constraint), employee_id, dan view_name_final (dari
    retriever_result, BUKAN request.view_name) - PERSIS dari sumber yang
    benar (decisions.md Keputusan 5-7)."""
    atomic_intent = _buat_atomic_intent()
    request = _buat_request(view_name="v_housekeeping_staff_daily", params={"limit": 10})
    query_engine_entry = _buat_query_engine_entry(
        atomic_intent, "v_housekeeping_staff_daily", lolos=True, request=request
    )
    retriever_item = _buat_hasil_kecukupan(atomic_intent, "v_housekeeping_staff_daily")
    constraint_item = _buat_atomic_intent_constraint(atomic_intent, terdeteksi=True)

    diterima = {}

    def _rekam(req, constraint, employee_id, view_name_tervalidasi_retriever):
        diterima["request"] = req
        diterima["constraint"] = constraint
        diterima["employee_id"] = employee_id
        diterima["view_name_tervalidasi_retriever"] = view_name_tervalidasi_retriever
        return HasilVerifikasiGate(request_final=req, lolos=True, terkoreksi=False)

    monkeypatch.setattr(verifikasi_gate_module, "verifikasi_gate", _rekam)

    hasil = verifikasi_gate_semua(
        [query_engine_entry], [retriever_item], [constraint_item], employee_id="E0001"
    )

    assert diterima["request"] is request
    assert diterima["constraint"] is constraint_item.constraint
    assert diterima["employee_id"] == "E0001"
    assert diterima["view_name_tervalidasi_retriever"] == "v_housekeeping_staff_daily"
    assert len(hasil) == 1
    assert hasil[0][0] is atomic_intent


def test_verifikasi_gate_semua_skip_hasil_verifikasi_none(monkeypatch):
    """Item hasil_verifikasi=None (M3.4 gagal total) TIDAK BOLEH diteruskan
    ke verifikasi_gate() sama sekali (decisions.md Keputusan 4)."""
    atomic_intent = _buat_atomic_intent()
    query_engine_entry = _buat_query_engine_entry(atomic_intent, "v_x", lolos=None)
    retriever_item = _buat_hasil_kecukupan(atomic_intent, None)
    constraint_item = _buat_atomic_intent_constraint(atomic_intent, terdeteksi=False)

    def _gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError("verifikasi_gate TIDAK BOLEH terpanggil untuk hasil_verifikasi=None")

    monkeypatch.setattr(verifikasi_gate_module, "verifikasi_gate", _gagal_kalau_terpanggil)

    hasil = verifikasi_gate_semua(
        [query_engine_entry], [retriever_item], [constraint_item], employee_id="E0001"
    )

    assert hasil == []


def test_verifikasi_gate_semua_skip_lolos_false(monkeypatch):
    """Item lolos=False (M3.5 bilang bentuk jawaban tidak cukup) TIDAK
    BOLEH diteruskan ke verifikasi_gate() (decisions.md Keputusan 2)."""
    atomic_intent = _buat_atomic_intent()
    query_engine_entry = _buat_query_engine_entry(atomic_intent, "v_x", lolos=False)
    retriever_item = _buat_hasil_kecukupan(atomic_intent, "v_x")
    constraint_item = _buat_atomic_intent_constraint(atomic_intent, terdeteksi=False)

    def _gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError("verifikasi_gate TIDAK BOLEH terpanggil untuk item lolos=False")

    monkeypatch.setattr(verifikasi_gate_module, "verifikasi_gate", _gagal_kalau_terpanggil)

    hasil = verifikasi_gate_semua(
        [query_engine_entry], [retriever_item], [constraint_item], employee_id="E0001"
    )

    assert hasil == []


def test_verifikasi_gate_semua_multi_item_tidak_tertukar(monkeypatch):
    """Risiko utama fan-in 3 sumber: dua atomic intent BERBEDA dengan
    view_name/constraint BERBEDA - tiap item wajib menerima data dari
    sumber yang BENAR (dicocokkan via atomic_intent_id), bukan tertukar
    dengan item lain (decisions.md Keputusan 7)."""
    intent_a = _buat_atomic_intent("kebutuhan A")
    intent_b = _buat_atomic_intent("kebutuhan B")

    entry_a = _buat_query_engine_entry(intent_a, "v_housekeeping_staff_daily", lolos=True)
    entry_b = _buat_query_engine_entry(intent_b, "v_hr_watchlist_monthly", lolos=True)

    retriever_a = _buat_hasil_kecukupan(intent_a, "v_housekeeping_staff_daily")
    retriever_b = _buat_hasil_kecukupan(intent_b, "v_hr_watchlist_monthly")

    constraint_a = _buat_atomic_intent_constraint(intent_a, terdeteksi=True)
    constraint_b = _buat_atomic_intent_constraint(intent_b, terdeteksi=False)

    diterima_per_intent = {}

    def _rekam(req, constraint, employee_id, view_name_tervalidasi_retriever):
        diterima_per_intent[req.view_name] = {
            "constraint_terdeteksi": constraint.terdeteksi,
            "view_name_tervalidasi_retriever": view_name_tervalidasi_retriever,
        }
        return HasilVerifikasiGate(request_final=req, lolos=True, terkoreksi=False)

    monkeypatch.setattr(verifikasi_gate_module, "verifikasi_gate", _rekam)

    # Urutan list SENGAJA dibalik antar sumber (retriever B lebih dulu,
    # constraint B lebih dulu) untuk memastikan pencocokan murni via
    # atomic_intent_id, bukan kebetulan sejajar by index.
    hasil = verifikasi_gate_semua(
        [entry_a, entry_b],
        [retriever_b, retriever_a],
        [constraint_b, constraint_a],
        employee_id="E0001",
    )

    assert diterima_per_intent["v_housekeeping_staff_daily"]["constraint_terdeteksi"] is True
    assert (
        diterima_per_intent["v_housekeeping_staff_daily"]["view_name_tervalidasi_retriever"]
        == "v_housekeeping_staff_daily"
    )
    assert diterima_per_intent["v_hr_watchlist_monthly"]["constraint_terdeteksi"] is False
    assert (
        diterima_per_intent["v_hr_watchlist_monthly"]["view_name_tervalidasi_retriever"]
        == "v_hr_watchlist_monthly"
    )
    assert len(hasil) == 2


def test_verifikasi_gate_semua_urutan_dan_panjang_dipertahankan(monkeypatch):
    """Campuran: item lolos=True + item lolos=False + item hasil_verifikasi
    =None - hasil hanya berisi yang lolos=True, urutan dipertahankan."""
    intent_1 = _buat_atomic_intent("intent 1")
    intent_2 = _buat_atomic_intent("intent 2")
    intent_3 = _buat_atomic_intent("intent 3")

    entry_1 = _buat_query_engine_entry(intent_1, "v_a", lolos=True)
    entry_2 = _buat_query_engine_entry(intent_2, "v_b", lolos=False)
    entry_3 = _buat_query_engine_entry(intent_3, "v_c", lolos=None)

    retriever_items = [
        _buat_hasil_kecukupan(intent_1, "v_a"),
        _buat_hasil_kecukupan(intent_2, "v_b"),
        _buat_hasil_kecukupan(intent_3, None),
    ]
    constraint_items = [
        _buat_atomic_intent_constraint(intent_1, terdeteksi=False),
        _buat_atomic_intent_constraint(intent_2, terdeteksi=False),
        _buat_atomic_intent_constraint(intent_3, terdeteksi=False),
    ]

    monkeypatch.setattr(
        verifikasi_gate_module,
        "verifikasi_gate",
        lambda req, constraint, employee_id, view_name_tervalidasi_retriever: HasilVerifikasiGate(
            request_final=req, lolos=True, terkoreksi=False
        ),
    )

    hasil = verifikasi_gate_semua(
        [entry_1, entry_2, entry_3], retriever_items, constraint_items, employee_id="E0001"
    )

    assert len(hasil) == 1
    assert hasil[0][0] is intent_1


def test_verifikasi_gate_semua_list_kosong_hasil_kosong():
    """Input list kosong -> hasil list kosong, tanpa error."""
    assert verifikasi_gate_semua([], [], [], employee_id="E0001") == []
