"""Verification Gate (Milestone 2.4): empat pemeriksaan berlapis sebelum
request dikirim ke chatbot_api - sepenuhnya deterministik, TANPA LLM
(ruang kesalahan tertutup, lihat decisions.md).

Cek 1 (bentuk request statis): domain dijamin valid oleh tipe `Domain`
Pydantic itu sendiri - yang diperiksa di sini murni view_name terdaftar
di domain yang dinyatakan, dan limit tidak melebihi batas chatbot_api.
"""

from src.layers.verification_gate.katalog_view import DAFTAR_VIEW_PER_DOMAIN
from src.observability.tracing import get_tracer
from src.schemas.cakupan_individu import ConstraintCakupanIndividu
from src.schemas.verification_gate import HasilVerifikasiGate, QueryEngineRequest

LIMIT_MAKSIMUM = 1000
_TRACER_NAME = "verification_gate.verifikasi_gate"


def verifikasi_bentuk_request_statis(request: QueryEngineRequest) -> tuple[bool, str | None]:
    """Cek 1: view_name terdaftar di domain yang dinyatakan, limit (kalau
    ada) tidak melebihi batas chatbot_api (1000, api-chatbot.md)."""
    view_valid = DAFTAR_VIEW_PER_DOMAIN.get(request.domain, frozenset())
    if request.view_name not in view_valid:
        return False, (
            f"view_name '{request.view_name}' tidak terdaftar di domain "
            f"'{request.domain.value}'"
        )

    limit = request.params.get("limit")
    if limit is not None and limit > LIMIT_MAKSIMUM:
        return False, f"limit {limit} melebihi batas maksimum {LIMIT_MAKSIMUM}"

    return True, None


def verifikasi_kepatuhan_sumber(
    request: QueryEngineRequest, view_name_tervalidasi_retriever: str
) -> tuple[bool, str | None]:
    """Cek 2: view_name yang akan dikirim benar-benar sama dengan yang
    divalidasi Retriever (M3.1-3.3) - diterima sebagai parameter, BUKAN
    query M3.x langsung (belum dibangun)."""
    if request.view_name != view_name_tervalidasi_retriever:
        return False, (
            f"view_name request ('{request.view_name}') tidak sesuai dengan "
            f"view_name yang divalidasi Retriever ('{view_name_tervalidasi_retriever}')"
        )
    return True, None


def tegakkan_constraint_cakupan_individu(
    request: QueryEngineRequest, constraint: ConstraintCakupanIndividu, employee_id: str
) -> tuple[QueryEngineRequest, bool]:
    """Cek 3: kalau constraint.terdeteksi=True dan params["employee_id"]
    belum sama dengan employee_id caller, TIMPA PAKSA (bukan tolak) -
    lihat decisions.md Keputusan 1 (konvensi employee_id, PROVISIONAL).
    Mengembalikan (request_terkoreksi, terkoreksi)."""
    if not constraint.terdeteksi:
        return request, False

    if request.params.get("employee_id") == employee_id:
        return request, False

    params_terkoreksi = dict(request.params)
    params_terkoreksi["employee_id"] = employee_id
    return request.model_copy(update={"params": params_terkoreksi}), True


def verifikasi_kelengkapan_penegakan(
    request: QueryEngineRequest, constraint: ConstraintCakupanIndividu, employee_id: str
) -> tuple[bool, str | None]:
    """Cek 4: re-cek hasil cek 3 benar-benar konsisten - defensif,
    menangkap bug internal kalau tegakkan_constraint_cakupan_individu()
    gagal menerapkan koreksinya sendiri."""
    if not constraint.terdeteksi:
        return True, None

    if request.params.get("employee_id") != employee_id:
        return False, (
            "constraint cakupan-individu terdeteksi tapi params['employee_id'] "
            f"({request.params.get('employee_id')!r}) tidak sama dengan employee_id "
            f"caller ({employee_id!r}) setelah penegakan"
        )
    return True, None


def _tolak(span, check_name: str, alasan: str, terkoreksi: bool = False) -> HasilVerifikasiGate:
    span.set_attribute("verification.check_name", check_name)
    span.set_attribute("error.type", "gagal_teknis")
    return HasilVerifikasiGate(
        request_final=None, lolos=False, terkoreksi=terkoreksi, alasan_penolakan=alasan
    )


def verifikasi_gate(
    request: QueryEngineRequest,
    constraint: ConstraintCakupanIndividu,
    employee_id: str,
    view_name_tervalidasi_retriever: str,
) -> HasilVerifikasiGate:
    """Orkestrator: cek 1->2 (early-exit tolak kalau gagal salah satu),
    lalu cek 3->4 kalau lolos keduanya. Span verification_gate.check per
    cek (verification.check_name, error.type bila gagal), span pembungkus
    verification_gate.verifikasi_gate."""
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("verification_gate.verifikasi_gate") as span_wrap:
        with tracer.start_as_current_span("verification_gate.check") as span:
            lolos, alasan = verifikasi_bentuk_request_statis(request)
            span.set_attribute("verification.check_name", "bentuk_request_statis")
            if not lolos:
                hasil = _tolak(span, "bentuk_request_statis", alasan)
                span_wrap.set_attribute("verification_gate.lolos", False)
                return hasil

        with tracer.start_as_current_span("verification_gate.check") as span:
            lolos, alasan = verifikasi_kepatuhan_sumber(request, view_name_tervalidasi_retriever)
            span.set_attribute("verification.check_name", "kepatuhan_sumber")
            if not lolos:
                hasil = _tolak(span, "kepatuhan_sumber", alasan)
                span_wrap.set_attribute("verification_gate.lolos", False)
                return hasil

        with tracer.start_as_current_span("verification_gate.check") as span:
            span.set_attribute("verification.check_name", "constraint_cakupan_individu")
            request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
                request, constraint, employee_id
            )
            span.set_attribute("verification.terkoreksi", terkoreksi)

        with tracer.start_as_current_span("verification_gate.check") as span:
            lolos, alasan = verifikasi_kelengkapan_penegakan(
                request_terkoreksi, constraint, employee_id
            )
            span.set_attribute("verification.check_name", "kelengkapan_penegakan")
            if not lolos:
                hasil = _tolak(span, "kelengkapan_penegakan", alasan, terkoreksi=terkoreksi)
                span_wrap.set_attribute("verification_gate.lolos", False)
                return hasil

        span_wrap.set_attribute("verification_gate.lolos", True)
        span_wrap.set_attribute("verification_gate.terkoreksi", terkoreksi)
        return HasilVerifikasiGate(
            request_final=request_terkoreksi, lolos=True, terkoreksi=terkoreksi
        )
