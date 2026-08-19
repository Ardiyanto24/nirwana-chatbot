"""Test orkestrator lintas-layer PIC 7 Level 2 -
src/orchestration/turn_pipeline.py. Cakupan SEMPIT (decisions.md M7.6
Keputusan 8, dipertahankan M7.7 Keputusan 7, M7.8 Keputusan 6, M7.9
Keputusan 7, M7.10 Keputusan 7, M7.11 Keputusan 9): hanya kejadian yang
TIDAK butuh LLM/DB/Jaeger nyata (short-circuit deterministik + wiring
identity mocked + kegagalan teknis salah satu cabang paralel + argumen
yang diterima Decomposition + konversi None/list-kosong ke Pencocokan +
argumen yang diterima Domain Gate + argumen yang diterima Pemeriksaan
Otorisasi). Kejadian yang butuh eksekusi nyata (LLM/DB sungguhan, bukti
span/konten/status match/intent.count) ada di evals/7.6-.../,
evals/7.7-.../, evals/7.8-.../, evals/7.9-.../, evals/7.10-.../,
evals/7.11-.../ - lihat rancangan.md/audit.md di folder masing-masing.
"""

import pydantic
import pytest

import src.orchestration.turn_pipeline as turn_pipeline_module
from src.orchestration.turn_pipeline import proses_turn
from src.schemas.decomposition import (
    AtomicIntent,
    DecompositionResult,
    KlasifikasiKebutuhan,
    LabelBentukJawaban as LabelBentukJawabanDecomposition,
    RelasiKebutuhan,
)
from src.schemas.authorization import AtomicIntentAuthorization, DomainAuthorization
from src.schemas.cakupan_individu import AtomicIntentConstraint, ConstraintCakupanIndividu
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.interpretation import HasilNarasi, HasilVerifikasiNarasi
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.query_engine import HasilPenyusunanRequest, HasilVerifikasiBentukRequest
from src.schemas.retriever import HasilKecukupanStruktural
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest

_DECOMPOSITION_DUMMY = DecompositionResult(
    klasifikasi=KlasifikasiKebutuhan.TUNGGAL,
    atomic_intents=[],
    verifikasi_valid=True,
    verifikasi_alasan=None,
    retry_count=0,
)

_MATCHES_DUMMY = []

_DOMAIN_GATE_DUMMY = []

_OTORISASI_DUMMY = []

_CAKUPAN_INDIVIDU_DUMMY = []

_RETRIEVER_DUMMY = []

_QUERY_ENGINE_DUMMY = []

_VERIFICATION_GATE_DUMMY = []

_EXECUTION_DUMMY = []

_PAKET_DARI_EKSEKUSI_DUMMY = []

_PAKET_NARASI_DUMMY = []

_INTERPRETATION_DUMMY = (
    HasilNarasi(narasi="narasi dummy"),
    HasilVerifikasiNarasi(
        narasi="narasi dummy", status=StatusEksekusi.BERHASIL, lolos=True, alasan=None
    ),
    None,
)

_RAW_VALID_TURN1 = {
    "session_id": "sess-test",
    "turn_index": 1,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Berapa occupancy bulan ini?",
}

_RAW_VALID_TURN2 = {
    "session_id": "sess-test",
    "turn_index": 2,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Bandingkan dengan bulan lalu",
    "history": [
        {"turn_index": 1, "question": "Berapa occupancy April?", "answer": "78%"}
    ],
}

# Kejadian E03: history tidak cocok turn_index (turn_index=2 tapi history
# kosong) -> pydantic.ValidationError, forced by model_validator
# TurnPayload.history_matches_turn_index().
_RAW_GAGAL_VALIDASI = {
    "session_id": "sess-test",
    "turn_index": 2,
    "role_title": "CEO",
    "employee_id": "emp-1",
    "question": "Bandingkan dengan bulan lalu",
    "history": [],
}


def _paket_dummy(atomic_intent_id: str) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent_id,
        session_id="sess-test",
        turn_index=1,
        teks_kebutuhan="teks",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": [{"nilai": 1}]},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


def test_orkestrator_short_circuit_validasi_gagal_ketergantungan_tidak_dipanggil(
    monkeypatch,
):
    """Kejadian E03: payload gagal validasi Input Layer -> ValidationError
    menjalar, detect_turn_dependency() TIDAK PERNAH terpanggil."""

    def _gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "detect_turn_dependency TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", _gagal_kalau_terpanggil
    )

    def _decompose_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "decompose_question TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", _decompose_gagal_kalau_terpanggil
    )

    def _match_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "match_and_archive TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", _match_gagal_kalau_terpanggil
    )

    def _domain_gate_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "identifikasi_domain_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", _domain_gate_gagal_kalau_terpanggil
    )

    def _otorisasi_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "periksa_otorisasi_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "periksa_otorisasi_semua", _otorisasi_gagal_kalau_terpanggil
    )

    def _cakupan_individu_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "deteksi_constraint_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        _cakupan_individu_gagal_kalau_terpanggil,
    )

    def _retriever_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "proses_retrieval_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "proses_retrieval_semua", _retriever_gagal_kalau_terpanggil
    )

    def _query_engine_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "susun_dan_verifikasi_request_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        _query_engine_gagal_kalau_terpanggil,
    )

    def _verification_gate_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "verifikasi_gate_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "verifikasi_gate_semua", _verification_gate_gagal_kalau_terpanggil
    )

    def _wave_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "kelompokkan_wave TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "kelompokkan_wave", _wave_gagal_kalau_terpanggil
    )

    def _execution_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "eksekusi_atomic_intent_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "eksekusi_atomic_intent_semua", _execution_gagal_kalau_terpanggil
    )

    def _simpan_paket_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "susun_dan_simpan_paket_semua TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "susun_dan_simpan_paket_semua", _simpan_paket_gagal_kalau_terpanggil
    )

    def _paket_narasi_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "susun_paket_narasi TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "susun_paket_narasi", _paket_narasi_gagal_kalau_terpanggil
    )

    def _narasi_gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "susun_dan_verifikasi_narasi TIDAK BOLEH terpanggil saat validasi Input Layer gagal"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "susun_dan_verifikasi_narasi", _narasi_gagal_kalau_terpanggil
    )

    with pytest.raises(pydantic.ValidationError):
        proses_turn(_RAW_GAGAL_VALIDASI)


def test_orkestrator_wiring_keadaan_turn_berisi_objek_identik(monkeypatch):
    """Payload valid, tanpa referensi -> KeadaanTurn berisi objek PERSIS
    (identity) dari tiap langkah, bukan rekonstruksi. retrieve_session_
    memory TIDAK dipanggil (is_dependent=False)."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )

    def _gagal_kalau_terpanggil(*args, **kwargs):
        raise AssertionError(
            "retrieve_session_memory TIDAK BOLEH terpanggil saat tidak ada referensi terdeteksi"
        )

    monkeypatch.setattr(
        turn_pipeline_module, "retrieve_session_memory", _gagal_kalau_terpanggil
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert hasil.payload is payload_asli
    assert hasil.ketergantungan is ketergantungan_asli
    assert hasil.rewrite is rewrite_asli
    assert hasil.session_memory is None
    assert hasil.decomposition is _DECOMPOSITION_DUMMY
    assert hasil.matches == _MATCHES_DUMMY
    assert hasil.domain_gate == _DOMAIN_GATE_DUMMY
    assert hasil.otorisasi == _OTORISASI_DUMMY
    assert hasil.cakupan_individu == _CAKUPAN_INDIVIDU_DUMMY
    assert hasil.retriever == _RETRIEVER_DUMMY
    assert hasil.query_engine == _QUERY_ENGINE_DUMMY
    assert hasil.verification_gate == _VERIFICATION_GATE_DUMMY
    assert hasil.execution == []
    assert hasil.paket_narasi == _PAKET_NARASI_DUMMY
    assert hasil.interpretation == _INTERPRETATION_DUMMY


def test_orkestrator_referensi_terdeteksi_kedua_cabang_terpanggil_argumen_benar(
    monkeypatch,
):
    """Referensi terdeteksi -> rewrite_to_standalone DAN retrieve_session_
    memory sama-sama terpanggil, dengan argumen yang benar (session_id dari
    payload, turn_index dari referenced_turn_index)."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN2)
    ketergantungan_asli = TurnDependencyResult(is_dependent=True, referenced_turn_index=1)
    rewrite_asli = RewriteResult(rewritten_question="pertanyaan mandiri")
    paket_asli = [_paket_dummy("a1")]

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )

    diterima_rewrite = {}

    def _rekam_rewrite(payload):
        diterima_rewrite["payload"] = payload
        return rewrite_asli

    diterima_memory = {}

    def _rekam_memory(session_id, turn_index):
        diterima_memory["session_id"] = session_id
        diterima_memory["turn_index"] = turn_index
        return paket_asli

    monkeypatch.setattr(turn_pipeline_module, "rewrite_to_standalone", _rekam_rewrite)
    monkeypatch.setattr(turn_pipeline_module, "retrieve_session_memory", _rekam_memory)
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN2)

    assert diterima_rewrite["payload"] is payload_asli
    assert diterima_memory["session_id"] == payload_asli.session_id
    assert diterima_memory["turn_index"] == 1
    assert hasil.rewrite is rewrite_asli
    assert hasil.decomposition is _DECOMPOSITION_DUMMY
    assert hasil.matches == _MATCHES_DUMMY
    assert hasil.domain_gate == _DOMAIN_GATE_DUMMY
    # KeadaanTurn membungkus `list[SessionMemoryPackage]` lewat Pydantic -
    # container list-nya sendiri direkonstruksi (bukan identity check valid),
    # tapi tiap elemen di dalamnya tetap objek PERSIS (fast-path Pydantic
    # v2 untuk instance BaseModel yang sudah tervalidasi, tidak dibuat ulang).
    assert len(hasil.session_memory) == 1
    assert hasil.session_memory[0] is paket_asli[0]


def test_orkestrator_kegagalan_teknis_satu_cabang_menjalar_cabang_lain_tetap_selesai(
    monkeypatch,
):
    """Tarik Memory gagal teknis -> exception menjalar keluar proses_turn(),
    TAPI cabang Rewrite tetap terpanggil/selesai (membuktikan ThreadPoolExecutor
    menunggu kedua thread selesai lewat shutdown(wait=True) sebelum exception
    benar-benar menjalar ke pemanggil - bukan cabang lain dibatalkan paksa)."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN2)
    ketergantungan_asli = TurnDependencyResult(is_dependent=True, referenced_turn_index=1)

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )

    rewrite_terpanggil = {"n": 0}

    def _rewrite_spy(payload):
        rewrite_terpanggil["n"] += 1
        return RewriteResult(rewritten_question=payload.question)

    def _memory_gagal(session_id, turn_index):
        raise RuntimeError("simulasi DB tidak terjangkau")

    monkeypatch.setattr(turn_pipeline_module, "rewrite_to_standalone", _rewrite_spy)
    monkeypatch.setattr(turn_pipeline_module, "retrieve_session_memory", _memory_gagal)

    with pytest.raises(RuntimeError, match="simulasi DB tidak terjangkau"):
        proses_turn(_RAW_VALID_TURN2)

    assert rewrite_terpanggil["n"] == 1, "cabang Rewrite tetap harus selesai dipanggil"


def test_orkestrator_decompose_menerima_rewritten_question_bukan_payload_question(
    monkeypatch,
):
    """Kejadian inti M7.8: decompose_question() WAJIB dipanggil dengan
    rewrite.rewritten_question (hasil Rewrite), BUKAN payload.question asli.
    payload.question dan rewritten_question sengaja dibuat teks BERBEDA supaya
    kalau kode keliru memakai payload.question, test gagal jelas - bukan
    kebetulan lolos karena kedua teks kebetulan sama."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question="TEKS HASIL REWRITE BERBEDA TOTAL")

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )

    diterima_decompose = {}

    def _rekam_decompose(question):
        diterima_decompose["question"] = question
        return _DECOMPOSITION_DUMMY

    monkeypatch.setattr(turn_pipeline_module, "decompose_question", _rekam_decompose)
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_decompose["question"] == "TEKS HASIL REWRITE BERBEDA TOTAL"
    assert diterima_decompose["question"] != payload_asli.question
    assert hasil.decomposition is _DECOMPOSITION_DUMMY


def test_orkestrator_match_menerima_list_kosong_saat_session_memory_none(monkeypatch):
    """Kejadian E01 M7.9: tanpa referensi terdeteksi -> session_memory=None
    di KeadaanTurn, TAPI match_and_archive() WAJIB tetap menerima `[]`
    (bukan None) sebagai candidates - konversi `session_memory_result or []`
    forced signature match_and_archive() yang menerima list, bukan Optional."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )

    diterima_match = {}

    def _rekam_match(atomic_intents, candidates, session_id, turn_index):
        diterima_match["candidates"] = candidates
        return _MATCHES_DUMMY

    monkeypatch.setattr(turn_pipeline_module, "match_and_archive", _rekam_match)
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert hasil.session_memory is None
    assert diterima_match["candidates"] == []
    assert hasil.matches == _MATCHES_DUMMY


def test_orkestrator_match_menerima_list_kosong_saat_session_memory_kosong(monkeypatch):
    """Kejadian E02 M7.9: referensi terdeteksi TAPI Tarik Memory genuinely
    tidak menemukan data -> session_memory=[] (bukan None) di KeadaanTurn,
    match_and_archive() tetap menerima `[]` yang SAMA - origin beda (E01
    tidak dipanggil sama sekali, E02 dipanggil lalu kosong) tapi hasil
    konversi ke Pencocokan konsisten."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN2)
    ketergantungan_asli = TurnDependencyResult(is_dependent=True, referenced_turn_index=1)
    rewrite_asli = RewriteResult(rewritten_question="pertanyaan mandiri")

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "retrieve_session_memory", lambda session_id, turn_index: []
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )

    diterima_match = {}

    def _rekam_match(atomic_intents, candidates, session_id, turn_index):
        diterima_match["candidates"] = candidates
        return _MATCHES_DUMMY

    monkeypatch.setattr(turn_pipeline_module, "match_and_archive", _rekam_match)
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN2)

    assert hasil.session_memory == []
    assert diterima_match["candidates"] == []
    assert hasil.matches == _MATCHES_DUMMY


def test_orkestrator_domain_gate_menerima_matches_apa_adanya_tanpa_filter(monkeypatch):
    """Kejadian inti M7.10: identifikasi_domain_semua() WAJIB menerima
    `matches` PERSIS (identity check) hasil match_and_archive() - orkestrator
    TIDAK ikut memfilter status=perlu_eksekusi (itu tanggung jawab INTERNAL
    identifikasi_domain_semua() sendiri, sudah ada sejak M2.1, lihat
    decisions.md Keputusan 1)."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    atomic_intent_asli = AtomicIntent(
        atomic_intent_id="ai-1",
        teks_kebutuhan="teks kebutuhan",
        label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )
    matches_asli = [
        AtomicIntentMatch(
            atomic_intent=atomic_intent_asli, status=MatchStatus.PERLU_EKSEKUSI, paket=None
        )
    ]

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: matches_asli
    )

    diterima_domain_gate = {}

    def _rekam_domain_gate(matches):
        diterima_domain_gate["matches"] = matches
        return _DOMAIN_GATE_DUMMY

    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", _rekam_domain_gate
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_domain_gate["matches"] is matches_asli
    assert hasil.domain_gate == _DOMAIN_GATE_DUMMY


def test_orkestrator_otorisasi_menerima_domain_gate_result_dan_role_title_benar(
    monkeypatch,
):
    """Kejadian inti M7.11 (Checkpoint 2-3): periksa_otorisasi_semua() WAJIB
    menerima `domain_gate_result` PERSIS (identity check) hasil
    identifikasi_domain_semua(), DAN `payload.role_title` yang benar - gap
    wiring M2.2 yang belum pernah tersambung sebelumnya (lihat decisions.md
    Keputusan 1+4-5). role_title sengaja diambil dari payload turn 1
    (bukan konstanta terpisah) supaya test membuktikan nilai itu genuinely
    mengalir dari TurnPayload, bukan kebetulan cocok dengan default."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    domain_gate_asli = [
        AtomicIntentDomains(
            atomic_intent=AtomicIntent(
                atomic_intent_id="ai-1",
                teks_kebutuhan="teks kebutuhan",
                label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
                bergantung_pada=None,
            ),
            domains=[Domain.RESERVATION],
            status=StatusEksekusi.BERHASIL,
        )
    ]

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: domain_gate_asli
    )

    diterima_otorisasi = {}

    def _rekam_otorisasi(domain_gate_result, role_title):
        diterima_otorisasi["domain_gate_result"] = domain_gate_result
        diterima_otorisasi["role_title"] = role_title
        return _OTORISASI_DUMMY

    monkeypatch.setattr(turn_pipeline_module, "periksa_otorisasi_semua", _rekam_otorisasi)
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_otorisasi["domain_gate_result"] is domain_gate_asli
    assert diterima_otorisasi["role_title"] == payload_asli.role_title == "CEO"
    assert hasil.otorisasi == _OTORISASI_DUMMY


def test_orkestrator_cakupan_individu_menerima_otorisasi_result_dan_role_title_benar(
    monkeypatch,
):
    """Kejadian inti M7.11 (Checkpoint 4-5): deteksi_constraint_semua() WAJIB
    menerima `otorisasi_result` PERSIS (identity check) hasil
    periksa_otorisasi_semua(), DAN `payload.role_title` yang benar - gap
    wiring M2.3 yang belum pernah tersambung sebelumnya (lihat decisions.md
    Keputusan 2+4). role_title diambil dari payload turn 1 sama seperti
    test sambungan Otorisasi, konsisten membuktikan nilai genuinely mengalir
    dari TurnPayload di tiap titik rantai, bukan konstanta kebetulan cocok."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    otorisasi_asli = [
        AtomicIntentAuthorization(
            atomic_intent=AtomicIntent(
                atomic_intent_id="ai-1",
                teks_kebutuhan="teks kebutuhan",
                label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
                bergantung_pada=None,
            ),
            domain_decisions=[DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
        )
    ]

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: otorisasi_asli,
    )

    diterima_cakupan_individu = {}

    def _rekam_cakupan_individu(otorisasi_result, role_title):
        diterima_cakupan_individu["otorisasi_result"] = otorisasi_result
        diterima_cakupan_individu["role_title"] = role_title
        return _CAKUPAN_INDIVIDU_DUMMY

    monkeypatch.setattr(
        turn_pipeline_module, "deteksi_constraint_semua", _rekam_cakupan_individu
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_cakupan_individu["otorisasi_result"] is otorisasi_asli
    assert diterima_cakupan_individu["role_title"] == payload_asli.role_title == "CEO"
    assert hasil.cakupan_individu == _CAKUPAN_INDIVIDU_DUMMY


def test_orkestrator_retriever_menerima_cakupan_individu_result_persis(monkeypatch):
    """Kejadian inti M7.11 (Checkpoint 7-8, Sambungan 6 resmi):
    proses_retrieval_semua() WAJIB menerima `cakupan_individu_result`
    PERSIS (identity check) hasil deteksi_constraint_semua() - titik
    penutup rantai Domain Gate lengkap (M2.1->M2.2->M2.3) mengalir ke
    Retriever (lihat decisions.md Keputusan 3-4)."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    cakupan_individu_asli = [
        AtomicIntentConstraint(
            atomic_intent=AtomicIntent(
                atomic_intent_id="ai-1",
                teks_kebutuhan="teks kebutuhan",
                label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
                bergantung_pada=None,
            ),
            domain_decisions=[DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
            constraint=ConstraintCakupanIndividu(terdeteksi=False),
        )
    ]

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: cakupan_individu_asli,
    )

    diterima_retriever = {}

    def _rekam_retriever(cakupan_individu_result):
        diterima_retriever["cakupan_individu_result"] = cakupan_individu_result
        return _RETRIEVER_DUMMY

    monkeypatch.setattr(turn_pipeline_module, "proses_retrieval_semua", _rekam_retriever)
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_retriever["cakupan_individu_result"] is cakupan_individu_asli
    assert hasil.retriever == _RETRIEVER_DUMMY


def test_orkestrator_query_engine_menerima_retriever_result_persis(monkeypatch):
    """Kejadian inti M7.12 (Sambungan 7 resmi): susun_dan_verifikasi_
    request_semua() WAJIB menerima `retriever_result` PERSIS (identity
    check) hasil proses_retrieval_semua() - titik penutup rantai
    Retriever mengalir ke Query Engine (lihat decisions.md)."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )

    retriever_asli = [
        HasilKecukupanStruktural(
            atomic_intent=AtomicIntent(
                atomic_intent_id="ai-1",
                teks_kebutuhan="teks kebutuhan",
                label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
                bergantung_pada=None,
            ),
            kecukupan=[],
            view_name_final=None,
            status=StatusEksekusi.BERHASIL,
        )
    ]
    monkeypatch.setattr(
        turn_pipeline_module, "proses_retrieval_semua", lambda cakupan_individu_result: retriever_asli
    )

    diterima_query_engine = {}

    def _rekam_query_engine(retriever_result):
        diterima_query_engine["retriever_result"] = retriever_result
        return _QUERY_ENGINE_DUMMY

    monkeypatch.setattr(
        turn_pipeline_module, "susun_dan_verifikasi_request_semua", _rekam_query_engine
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_query_engine["retriever_result"] is retriever_asli
    assert hasil.query_engine == _QUERY_ENGINE_DUMMY


def test_orkestrator_verification_gate_menerima_query_engine_retriever_cakupan_individu_employee_id_persis(
    monkeypatch,
):
    """Kejadian inti M7.13 (Sambungan 8 resmi), DIPERBARUI M7.14: sejak
    M7.14, verifikasi_gate_semua() dipanggil PER WAVE (bukan sekali
    borongan) - `query_engine_asli` karena itu WAJIB berisi minimal 1
    item (bukan `[]` seperti versi M7.13 asli), supaya kelompokkan_wave()
    (real, tidak dimock) menghasilkan minimal 1 wave dan verifikasi_gate_
    semua() genuinely terpanggil. Argumen yang diterima adalah WAVE-SLICE
    (list baru hasil kelompokkan_wave(), BUKAN `query_engine_asli` itu
    sendiri secara identity) - dicek via value equality + identity
    elemen di dalamnya, bukan identity container. `retriever_result`/
    `cakupan_individu_result`/`employee_id` TETAP diteruskan utuh
    (full-set, tidak di-slice per wave) - identity check tetap berlaku
    untuk ketiganya."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    monkeypatch.setattr(
        turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )

    cakupan_individu_asli = [
        AtomicIntentConstraint(
            atomic_intent=AtomicIntent(
                atomic_intent_id="ai-1",
                teks_kebutuhan="teks kebutuhan",
                label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
                bergantung_pada=None,
            ),
            domain_decisions=[DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
            constraint=ConstraintCakupanIndividu(terdeteksi=False),
        )
    ]
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: cakupan_individu_asli,
    )

    retriever_asli = [
        HasilKecukupanStruktural(
            atomic_intent=cakupan_individu_asli[0].atomic_intent,
            kecukupan=[],
            view_name_final=None,
            status=StatusEksekusi.BERHASIL,
        )
    ]
    monkeypatch.setattr(
        turn_pipeline_module, "proses_retrieval_semua", lambda cakupan_individu_result: retriever_asli
    )

    hasil_susun_asli = HasilPenyusunanRequest(
        atomic_intent=cakupan_individu_asli[0].atomic_intent,
        request=QueryEngineRequest(domain=Domain.RESERVATION, view_name="v_dummy", params={}),
        status=StatusEksekusi.BERHASIL,
    )
    hasil_verifikasi_asli = HasilVerifikasiBentukRequest(
        atomic_intent=cakupan_individu_asli[0].atomic_intent,
        request=hasil_susun_asli.request,
        status=StatusEksekusi.BERHASIL,
        lolos=True,
        alasan=None,
    )
    query_engine_asli = [(hasil_susun_asli, hasil_verifikasi_asli)]
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: query_engine_asli,
    )

    diterima_verification_gate = {}

    def _rekam_verification_gate(
        query_engine_result, retriever_result, cakupan_individu_result, employee_id
    ):
        diterima_verification_gate["query_engine_result"] = query_engine_result
        diterima_verification_gate["retriever_result"] = retriever_result
        diterima_verification_gate["cakupan_individu_result"] = cakupan_individu_result
        diterima_verification_gate["employee_id"] = employee_id
        return _VERIFICATION_GATE_DUMMY

    monkeypatch.setattr(
        turn_pipeline_module, "verifikasi_gate_semua", _rekam_verification_gate
    )

    diterima_execution = {}

    def _rekam_execution(verification_gate_wave, cakupan_individu_result, role_title, employee_id):
        diterima_execution["verification_gate_wave"] = verification_gate_wave
        diterima_execution["cakupan_individu_result"] = cakupan_individu_result
        diterima_execution["role_title"] = role_title
        diterima_execution["employee_id"] = employee_id
        return _EXECUTION_DUMMY

    monkeypatch.setattr(
        turn_pipeline_module, "eksekusi_atomic_intent_semua", _rekam_execution
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_verification_gate["query_engine_result"] == query_engine_asli
    assert diterima_verification_gate["query_engine_result"][0] is query_engine_asli[0]
    assert diterima_verification_gate["retriever_result"] is retriever_asli
    assert diterima_verification_gate["cakupan_individu_result"] is cakupan_individu_asli
    assert diterima_verification_gate["employee_id"] == payload_asli.employee_id == "emp-1"
    assert hasil.verification_gate == _VERIFICATION_GATE_DUMMY

    assert diterima_execution["verification_gate_wave"] is _VERIFICATION_GATE_DUMMY
    assert diterima_execution["cakupan_individu_result"] is cakupan_individu_asli
    assert diterima_execution["role_title"] == payload_asli.role_title == "CEO"
    assert diterima_execution["employee_id"] == payload_asli.employee_id == "emp-1"
    assert hasil.execution == _EXECUTION_DUMMY


def test_orkestrator_wave_kedua_menunggu_wave_pertama_selesai(monkeypatch):
    """Kejadian inti M7.14 (Sambungan 9 resmi): wave 2 (kebutuhan
    bergantung, "ai-b") TIDAK BOLEH terverifikasi/tereksekusi SEBELUM
    wave 1 (dependensinya, "ai-a") selesai KEDUANYA (verifikasi_gate_
    semua() DAN eksekusi_atomic_intent_semua()) - dibuktikan lewat
    urutan panggilan mock, deterministik, TANPA LLM/HTTP/Jaeger nyata
    (bukti span real-execution ada di evals/7.14-.../). Skenario mirror
    KK sumber M7.14 ("bandingkan X dengan Y yang butuh Y dulu"): ai-a
    independen, ai-b bergantung pada ai-a."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    atomic_intent_a = AtomicIntent(
        atomic_intent_id="ai-a",
        teks_kebutuhan="kebutuhan A (independen)",
        label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )
    atomic_intent_b = AtomicIntent(
        atomic_intent_id="ai-b",
        teks_kebutuhan="kebutuhan B (bergantung pada A)",
        label_bentuk_jawaban=LabelBentukJawabanDecomposition.PERBANDINGAN,
        relasi=RelasiKebutuhan.BERGANTUNG,
        bergantung_pada=["ai-a"],
    )

    cakupan_individu_asli = [
        AtomicIntentConstraint(
            atomic_intent=atomic_intent_a,
            domain_decisions=[DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
            constraint=ConstraintCakupanIndividu(terdeteksi=False),
        ),
        AtomicIntentConstraint(
            atomic_intent=atomic_intent_b,
            domain_decisions=[DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
            constraint=ConstraintCakupanIndividu(terdeteksi=False),
        ),
    ]
    retriever_asli = [
        HasilKecukupanStruktural(
            atomic_intent=atomic_intent_a, kecukupan=[], view_name_final=None,
            status=StatusEksekusi.BERHASIL,
        ),
        HasilKecukupanStruktural(
            atomic_intent=atomic_intent_b, kecukupan=[], view_name_final=None,
            status=StatusEksekusi.BERHASIL,
        ),
    ]

    def _buat_qe_item(atomic_intent):
        req = QueryEngineRequest(domain=Domain.RESERVATION, view_name="v_dummy", params={})
        hasil_susun = HasilPenyusunanRequest(
            atomic_intent=atomic_intent, request=req, status=StatusEksekusi.BERHASIL
        )
        hasil_verifikasi = HasilVerifikasiBentukRequest(
            atomic_intent=atomic_intent, request=req, status=StatusEksekusi.BERHASIL,
            lolos=True, alasan=None,
        )
        return hasil_susun, hasil_verifikasi

    query_engine_asli = [_buat_qe_item(atomic_intent_a), _buat_qe_item(atomic_intent_b)]

    monkeypatch.setattr(turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli)
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli)
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(turn_pipeline_module, "match_and_archive", lambda *a, **k: _MATCHES_DUMMY)
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: _OTORISASI_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: cakupan_individu_asli,
    )
    monkeypatch.setattr(
        turn_pipeline_module, "proses_retrieval_semua", lambda cakupan_individu_result: retriever_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: query_engine_asli,
    )

    urutan_panggilan = []

    def _fake_vg(wave, retriever_result, cakupan_individu_result, employee_id):
        ids = sorted(item[0].atomic_intent.atomic_intent_id for item in wave)
        urutan_panggilan.append(f"verifikasi_gate:{','.join(ids)}")
        return [
            (
                item[0].atomic_intent,
                HasilVerifikasiGate(request_final=None, lolos=False, terkoreksi=False, alasan_penolakan="dummy"),
            )
            for item in wave
        ]

    def _fake_exec(verification_gate_wave, cakupan_individu_result, role_title, employee_id):
        ids = sorted(atomic_intent.atomic_intent_id for atomic_intent, _ in verification_gate_wave)
        urutan_panggilan.append(f"eksekusi:{','.join(ids)}")
        return []

    monkeypatch.setattr(turn_pipeline_module, "verifikasi_gate_semua", _fake_vg)
    monkeypatch.setattr(turn_pipeline_module, "eksekusi_atomic_intent_semua", _fake_exec)
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_simpan_paket_semua",
        lambda execution_result, verification_gate_result, session_id, turn_index: (
            _PAKET_DARI_EKSEKUSI_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_paket_narasi",
        lambda matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index: (
            [],
            _PAKET_NARASI_DUMMY,
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_narasi",
        lambda atomic_intents, packages, session_id, turn_index: _INTERPRETATION_DUMMY,
    )

    proses_turn(_RAW_VALID_TURN1)

    assert urutan_panggilan == [
        "verifikasi_gate:ai-a",
        "eksekusi:ai-a",
        "verifikasi_gate:ai-b",
        "eksekusi:ai-b",
    ], (
        "wave 2 (ai-b) TIDAK BOLEH terverifikasi/tereksekusi sebelum wave 1 "
        "(ai-a) selesai keduanya - urutan panggilan membuktikan sekuensial"
    )


def test_orkestrator_paket_narasi_menerima_matches_otorisasi_paket_eksekusi_persis(
    monkeypatch,
):
    """Kejadian inti M7.15 (Sambungan 10 resmi, titik pertemuan kedua):
    susun_paket_narasi() WAJIB menerima `matches`/`otorisasi_result` PERSIS
    (identity check) dari hasil langkah masing-masing, DAN `paket_dari_
    eksekusi` PERSIS hasil `susun_dan_simpan_paket_semua()` (bukan
    `execution_result` mentah) - membuktikan rantai konversi genuinely
    tersambung. `susun_dan_verifikasi_narasi()` (M7.5) pada gilirannya
    WAJIB menerima hasil `susun_paket_narasi()` PERSIS."""
    payload_asli = TurnPayload.model_validate(_RAW_VALID_TURN1)
    ketergantungan_asli = TurnDependencyResult(is_dependent=False, referenced_turn_index=None)
    rewrite_asli = RewriteResult(rewritten_question=payload_asli.question)

    matches_asli = [
        AtomicIntentMatch(
            atomic_intent=AtomicIntent(
                atomic_intent_id="ai-1",
                teks_kebutuhan="teks kebutuhan",
                label_bentuk_jawaban=LabelBentukJawabanDecomposition.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
                bergantung_pada=None,
            ),
            status=MatchStatus.PERLU_EKSEKUSI,
            paket=None,
        )
    ]

    monkeypatch.setattr(turn_pipeline_module, "validate_turn_payload", lambda raw: payload_asli)
    monkeypatch.setattr(
        turn_pipeline_module, "detect_turn_dependency", lambda payload: ketergantungan_asli
    )
    monkeypatch.setattr(turn_pipeline_module, "rewrite_to_standalone", lambda payload: rewrite_asli)
    monkeypatch.setattr(
        turn_pipeline_module, "decompose_question", lambda question: _DECOMPOSITION_DUMMY
    )
    monkeypatch.setattr(
        turn_pipeline_module, "match_and_archive", lambda *a, **k: matches_asli
    )
    monkeypatch.setattr(
        turn_pipeline_module, "identifikasi_domain_semua", lambda matches: _DOMAIN_GATE_DUMMY
    )

    otorisasi_asli = [
        AtomicIntentAuthorization(
            atomic_intent=matches_asli[0].atomic_intent,
            domain_decisions=[DomainAuthorization(domain=Domain.RESERVATION, diizinkan=True)],
        )
    ]
    monkeypatch.setattr(
        turn_pipeline_module,
        "periksa_otorisasi_semua",
        lambda domain_gate_result, role_title: otorisasi_asli,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "deteksi_constraint_semua",
        lambda otorisasi_result, role_title: _CAKUPAN_INDIVIDU_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "proses_retrieval_semua",
        lambda cakupan_individu_result: _RETRIEVER_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "susun_dan_verifikasi_request_semua",
        lambda retriever_result: _QUERY_ENGINE_DUMMY,
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "verifikasi_gate_semua",
        lambda query_engine_result, retriever_result, cakupan_individu_result, employee_id: (
            _VERIFICATION_GATE_DUMMY
        ),
    )
    monkeypatch.setattr(
        turn_pipeline_module,
        "eksekusi_atomic_intent_semua",
        lambda verification_gate_wave, cakupan_individu_result, role_title, employee_id: (
            _EXECUTION_DUMMY
        ),
    )

    paket_dari_eksekusi_asli = [_paket_dummy("ai-eksekusi")]
    diterima_simpan_paket = {}

    def _rekam_simpan_paket(execution_result, verification_gate_result, session_id, turn_index):
        diterima_simpan_paket["execution_result"] = execution_result
        diterima_simpan_paket["verification_gate_result"] = verification_gate_result
        diterima_simpan_paket["session_id"] = session_id
        diterima_simpan_paket["turn_index"] = turn_index
        return paket_dari_eksekusi_asli

    monkeypatch.setattr(
        turn_pipeline_module, "susun_dan_simpan_paket_semua", _rekam_simpan_paket
    )

    atomic_intents_narasi_asli = [matches_asli[0].atomic_intent]
    paket_narasi_asli = [_paket_dummy("ai-narasi")]
    diterima_paket_narasi = {}

    def _rekam_paket_narasi(matches, paket_dari_eksekusi, otorisasi_result, session_id, turn_index):
        diterima_paket_narasi["matches"] = matches
        diterima_paket_narasi["paket_dari_eksekusi"] = paket_dari_eksekusi
        diterima_paket_narasi["otorisasi_result"] = otorisasi_result
        diterima_paket_narasi["session_id"] = session_id
        diterima_paket_narasi["turn_index"] = turn_index
        return atomic_intents_narasi_asli, paket_narasi_asli

    monkeypatch.setattr(turn_pipeline_module, "susun_paket_narasi", _rekam_paket_narasi)

    diterima_narasi = {}

    def _rekam_narasi(atomic_intents, packages, session_id, turn_index):
        diterima_narasi["atomic_intents"] = atomic_intents
        diterima_narasi["packages"] = packages
        diterima_narasi["session_id"] = session_id
        diterima_narasi["turn_index"] = turn_index
        return _INTERPRETATION_DUMMY

    monkeypatch.setattr(turn_pipeline_module, "susun_dan_verifikasi_narasi", _rekam_narasi)

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_simpan_paket["session_id"] == payload_asli.session_id
    assert diterima_simpan_paket["turn_index"] == payload_asli.turn_index

    assert diterima_paket_narasi["matches"] is matches_asli
    assert diterima_paket_narasi["paket_dari_eksekusi"] is paket_dari_eksekusi_asli
    assert diterima_paket_narasi["otorisasi_result"] is otorisasi_asli
    assert diterima_paket_narasi["session_id"] == payload_asli.session_id
    assert diterima_paket_narasi["turn_index"] == payload_asli.turn_index

    assert diterima_narasi["atomic_intents"] is atomic_intents_narasi_asli
    assert diterima_narasi["packages"] is paket_narasi_asli

    # KeadaanTurn membungkus list[SessionMemoryPackage] lewat Pydantic -
    # container list-nya sendiri direkonstruksi (mirror catatan test
    # test_orkestrator_referensi_terdeteksi_kedua_cabang_terpanggil_argumen_benar),
    # tapi elemen di dalamnya tetap objek PERSIS.
    assert len(hasil.paket_narasi) == 1
    assert hasil.paket_narasi[0] is paket_narasi_asli[0]
    assert hasil.interpretation == _INTERPRETATION_DUMMY
