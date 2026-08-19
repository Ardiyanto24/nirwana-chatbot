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
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.rewrite import RewriteResult
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)
from src.schemas.turn_dependency import TurnDependencyResult
from src.schemas.turn_payload import TurnPayload

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

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert hasil.payload is payload_asli
    assert hasil.ketergantungan is ketergantungan_asli
    assert hasil.rewrite is rewrite_asli
    assert hasil.session_memory is None
    assert hasil.decomposition is _DECOMPOSITION_DUMMY
    assert hasil.matches == _MATCHES_DUMMY
    assert hasil.domain_gate == _DOMAIN_GATE_DUMMY
    assert hasil.otorisasi == _OTORISASI_DUMMY


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

    hasil = proses_turn(_RAW_VALID_TURN1)

    assert diterima_otorisasi["domain_gate_result"] is domain_gate_asli
    assert diterima_otorisasi["role_title"] == payload_asli.role_title == "CEO"
    assert hasil.otorisasi == _OTORISASI_DUMMY
