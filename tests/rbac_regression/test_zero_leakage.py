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
from src.layers.verification_gate.verifikasi_gate import (
    tegakkan_constraint_cakupan_individu,
)
from src.schemas.cakupan_individu import ConstraintCakupanIndividu
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import AtomicIntentDomains, Domain
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi
from src.schemas.verification_gate import QueryEngineRequest


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


# --- Skenario 2: F&B Staff, seluruh domain ditolak (edge case) -------------
#
# Reuse evals/7.11-sambungan-retriever/payloads/E03.json - domain_diizinkan
# kosong TOTAL, robustness: tidak boleh crash, view_name_final=None.


def test_fb_staff_seluruh_domain_ditolak_tidak_crash():
    """F&B Staff tanya GOP (murni financial) - domain_diizinkan jadi KOSONG
    TOTAL setelah otorisasi. Zero-leakage edge case: sistem TIDAK BOLEH
    crash pada domain_diizinkan=[] - harus genuinely 0 kandidat, bukan
    exception yang bisa bocorkan detail internal."""
    role_title = "F&B Staff"
    domain_teridentifikasi = [Domain.FINANCIAL]

    domain_diizinkan = _domain_diizinkan(role_title, domain_teridentifikasi)
    assert domain_diizinkan == []

    kandidat, perlu_fallback = cari_bm25(
        "Berapa besar laba operasi kotor (GOP) properti pada bulan ini?",
        domain_diizinkan,
    )
    assert kandidat == []
    assert perlu_fallback is True, (
        "domain_diizinkan kosong -> BM25 tidak temukan apa pun, fallback terpicu"
    )


# --- Skenario 3: HR Staff "Budi", koreksi paksa cakupan individu -----------
#
# Reuse evals/7.13-sambungan-verification-gate/payloads/E01.json - LLM
# (Cakupan Individu M2.3, DI-FIX di sini) mendeteksi kebutuhan performa
# individu, tapi params["employee_id"] hasil LLM BISA salah/dimanipulasi -
# Verification Gate (M2.4, deterministik) WAJIB menimpa paksa ke ID caller
# sungguhan, bukan sekadar menolak.


def test_budi_hr_staff_koreksi_paksa_employee_id():
    """HR Staff (employee_id="emp-eval") tanya performa individu "Budi" -
    constraint cakupan-individu terdeteksi (hasil historis M2.3, di-fix di
    sini). params["employee_id"] hasil LLM (bisa salah - contoh dipakai di
    sini: "emp-budi-salah") WAJIB ditimpa paksa ke ID caller sungguhan,
    bukan dipercaya apa adanya dari LLM."""
    constraint = ConstraintCakupanIndividu(
        terdeteksi=True,
        alasan="kebutuhan menyentuh kategori data performa individu staf",
    )
    request_dari_llm = QueryEngineRequest(
        domain=Domain.HR,
        view_name="v_hr_employee_performance_semester",
        params={
            "full_name": "Budi",
            "review_period": "2026-S2",
            "employee_id": "emp-budi-salah",
        },
    )

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request_dari_llm, constraint, employee_id="emp-eval"
    )

    assert terkoreksi is True
    assert request_terkoreksi.params["employee_id"] == "emp-eval", (
        "KEBOCORAN: employee_id tidak dipaksa ke ID caller sungguhan"
    )
    assert request_terkoreksi.params["full_name"] == "Budi", (
        "koreksi seharusnya cuma menimpa employee_id, field lain tetap apa adanya"
    )


# --- Skenario 4: Maintenance Staff "Andi", bukti kedua independen ---------
#
# Reuse evals/7.13-sambungan-verification-gate/payloads/E03.json - domain
# BEDA (facility, bukan hr) DAN dikombinasikan dengan domain_denied
# (employees_directory ditolak) - constraint cakupan-individu tetap
# terdeteksi+dikoreksi benar dari domain facility yang diizinkan.


def test_andi_maintenance_staff_domain_berbeda_koreksi_tetap_benar():
    """Maintenance Staff tanya jumlah tiket teknisi "Andi" - domain
    teridentifikasi [facility, employees_directory] (hasil historis M2.1),
    employees_directory DITOLAK otorisasi tapi facility diizinkan.
    Constraint cakupan-individu tetap terdeteksi (hasil historis M2.3, di-
    fix di sini) DARI domain facility yang diizinkan - koreksi paksa
    employee_id tetap benar meski salah satu domain sumbernya ditolak."""
    role_title = "Maintenance Staff"
    domain_teridentifikasi = [Domain.FACILITY, Domain.EMPLOYEES_DIRECTORY]

    domain_diizinkan = _domain_diizinkan(role_title, domain_teridentifikasi)
    assert Domain.EMPLOYEES_DIRECTORY not in domain_diizinkan
    assert Domain.FACILITY in domain_diizinkan

    constraint = ConstraintCakupanIndividu(
        terdeteksi=True,
        alasan="kebutuhan menyentuh kategori data performa individu staf",
    )
    request_dari_llm = QueryEngineRequest(
        domain=Domain.FACILITY,
        view_name="v_maintenance_technician_daily",
        params={
            "technician_name": "Andi",
            "period_date_from": "2026-08-01",
            "period_date_to": "2026-08-31",
            "employee_id": "emp-andi-salah",
        },
    )

    request_terkoreksi, terkoreksi = tegakkan_constraint_cakupan_individu(
        request_dari_llm, constraint, employee_id="emp-eval"
    )

    assert terkoreksi is True
    assert request_terkoreksi.params["employee_id"] == "emp-eval", (
        "KEBOCORAN: employee_id tidak dipaksa ke ID caller sungguhan"
    )
