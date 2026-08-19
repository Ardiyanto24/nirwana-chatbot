"""Pemeriksaan Kecukupan Struktural (Milestone 3.3, langkah PENUTUP tiga
langkah Retriever). Mencocokkan `label_bentuk_jawaban` (M1.6, dibawa
lewat `AtomicIntent`) terhadap grain kandidat `view_name` yang sudah
dinyatakan cocok maknanya di Milestone 3.2 (`HasilKecocokanMakna`, label
`ditemukan`/`sebagian`), lalu memfinalkan SATU `view_name`.

Mekanisme HYBRID (dikonfirmasi user lewat `AskUserQuestion`, lihat
decisions.md Keputusan 1) - mirror pola BM25->embedding fallback M3.1
sendiri: rule table deterministik tri-state (`_evaluasi_deterministik`,
di bawah) sebagai jalur utama; SATU panggilan LLM konservatif (bukan
generate-verify penuh, Keputusan 5) HANYA untuk kandidat yang rule
table-nya menghasilkan `tidak_pasti`, dibatch per kebutuhan atomik
(Keputusan 7). User memilih hybrid secara eksplisit menolak
deterministik-murni karena taksonomi 5 `label_bentuk_jawaban` sekarang
diperkirakan akan bertambah kompleks ke depan - rule table karena itu
WAJIB fail-safe ke `tidak_pasti` (bukan menebak) untuk label yang tidak
dikenali (Keputusan 6), supaya mekanisme genuinely forward-compatible.
"""

import json

from openai import APIError
from pydantic import BaseModel, ValidationError

from src.config.llm import OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL, get_openrouter_client
from src.layers.retriever.definisi_view import DEFINISI_LENGKAP_VIEW
from src.layers.retriever.grain_view import GRAIN_STRUKTURAL_VIEW, KarakteristikGrain
from src.layers.retriever.kecocokan_makna import nilai_kecocokan_makna_atomic_intent
from src.layers.retriever.retriever import (
    _atribut_span_dari_hasil,
    _kumpulkan_kandidat,
)
from src.layers.retriever.retriever import _TRACER_NAME as _RETRIEVER_TRACER_NAME
from src.observability.genai_semconv import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_REQUEST_MODEL,
    GEN_AI_USAGE_INPUT_TOKENS,
    GEN_AI_USAGE_OUTPUT_TOKENS,
    PROMPT_ID,
    PROMPT_VERSION,
)
from src.observability.tracing import get_tracer
from src.prompts.loader import load_prompt
from src.schemas.cakupan_individu import AtomicIntentConstraint
from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain
from src.schemas.retriever import (
    HasilKecocokanMakna,
    HasilKecukupanStruktural,
    KecocokanKandidat,
    KecukupanKandidat,
    LabelKecocokanMakna,
    SumberKeputusanKecukupan,
)
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi

_TRACER_NAME = "retriever.kecukupan_struktural"
_PROMPT_ID_FALLBACK = "retriever.kecukupan_struktural_fallback"

_KecukupanRuleResult = tuple[str, str]
"""('cukup' | 'tidak_cukup' | 'tidak_pasti', alasan)."""


def _evaluasi_deterministik(
    label_bentuk_jawaban: LabelBentukJawaban, grain: KarakteristikGrain
) -> _KecukupanRuleResult:
    """Rule table murni Python, TANPA LLM. `nilai_tunggal` selalu cukup
    (bisa diambil dari grain apa pun). `tren` bergantung
    `punya_time_series`. `perbandingan`/`peringkat`/`komposisi`
    bergantung `punya_dimensi_pembanding` (pola sama untuk ketiganya -
    semua butuh grain yang menghasilkan >1 baris comparable dalam satu
    query, mirip cukup untuk membedakan tiga bentuk jawaban ini secara
    struktural). Label yang tidak dikenal rule table -> `tidak_pasti`
    (fail-safe eksplisit, bukan exception/tebakan - Keputusan 6)."""
    if label_bentuk_jawaban == LabelBentukJawaban.NILAI_TUNGGAL:
        return "cukup", "nilai_tunggal selalu bisa diambil dari grain apa pun"

    if label_bentuk_jawaban == LabelBentukJawaban.TREN:
        sinyal = grain.punya_time_series
        if sinyal == "ya":
            return "cukup", "grain punya dimensi waktu berulang, cukup untuk tren"
        if sinyal == "tidak":
            return (
                "tidak_cukup",
                "grain tidak punya dimensi waktu berulang (snapshot/statis), tidak cukup untuk tren",
            )
        return "tidak_pasti", "sinyal punya_time_series ambigu untuk grain ini"

    if label_bentuk_jawaban in (
        LabelBentukJawaban.PERBANDINGAN,
        LabelBentukJawaban.PERINGKAT,
        LabelBentukJawaban.KOMPOSISI,
    ):
        sinyal = grain.punya_dimensi_pembanding
        if sinyal == "ya":
            return (
                "cukup",
                f"grain punya dimensi pembanding, cukup untuk {label_bentuk_jawaban.value}",
            )
        if sinyal == "tidak":
            return (
                "tidak_cukup",
                f"grain tidak punya dimensi pembanding, tidak cukup untuk {label_bentuk_jawaban.value}",
            )
        return "tidak_pasti", "sinyal punya_dimensi_pembanding ambigu untuk grain ini"

    return (
        "tidak_pasti",
        f"label_bentuk_jawaban {label_bentuk_jawaban!r} tidak dikenal rule table - fail-safe ke LLM",
    )


# --- Fallback LLM (satu panggilan konservatif, batch per kebutuhan atomik) ---


def _render_system_prompt_fallback() -> str:
    return load_prompt(_PROMPT_ID_FALLBACK).render()


class _RawKecukupanEntry(BaseModel):
    view_name: str
    cukup: bool
    alasan: str


class _RawKecukupanResult(BaseModel):
    penilaian: list[_RawKecukupanEntry]


def _build_user_prompt_fallback(
    atomic_intent: AtomicIntent, kandidat_tidak_pasti: list[KecocokanKandidat]
) -> str:
    lines = [
        f"Kebutuhan: {atomic_intent.teks_kebutuhan} "
        f"(bentuk jawaban: {atomic_intent.label_bentuk_jawaban.value})",
        "\nDaftar kandidat yang grain-nya ambigu, beserta definisi lengkapnya:",
    ]
    for kk in kandidat_tidak_pasti:
        definisi = DEFINISI_LENGKAP_VIEW.get(kk.kandidat.view_name, "(definisi tidak ditemukan)")
        lines.append(f"\n### {kk.kandidat.view_name}\n{definisi}")
    return "\n".join(lines)


def _call_llm_fallback(atomic_intent: AtomicIntent, kandidat_tidak_pasti: list[KecocokanKandidat]):
    """Panggilan mentah ke OpenRouter, tanpa span/parsing - dipisah supaya
    bisa dipakai ulang oleh skrip eval (`evals/`), mirror pola kecocokan_makna.py."""
    client = get_openrouter_client()
    return client.chat.completions.create(
        model=OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL,
        messages=[
            {"role": "system", "content": _render_system_prompt_fallback()},
            {"role": "user", "content": _build_user_prompt_fallback(atomic_intent, kandidat_tidak_pasti)},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


def _default_aman_semua(
    kandidat_tidak_pasti: list[KecocokanKandidat], alasan: str
) -> list[KecukupanKandidat]:
    """Default aman kalau LLM fallback gagal teknis total (mirror pola
    aman M1.7) - SELURUH kandidat batch itu jadi cukup=False, BUKAN
    exception yang memblokir pemanggil. Salah bilang tidak_cukup aman
    (decisions.md Keputusan 5)."""
    return [
        KecukupanKandidat(
            kandidat=kk.kandidat,
            kecocokan_label=kk.label,
            cukup=False,
            alasan=alasan,
            sumber_keputusan=SumberKeputusanKecukupan.LLM,
        )
        for kk in kandidat_tidak_pasti
    ]


def _parse_fallback(
    raw_content: str, kandidat_tidak_pasti: list[KecocokanKandidat]
) -> tuple[list[KecukupanKandidat], bool]:
    """Parse hasil LLM fallback. gagal=True HANYA kalau seluruh respons
    tidak bisa diparse sama sekali (JSON rusak/skema salah total) -
    caller lalu menerapkan default aman ke SELURUH batch. Kandidat yang
    hilang dari respons yang SEBAGIAN valid diberi default aman
    cukup=False individual (bukan menggagalkan seluruh batch)."""
    try:
        data = json.loads(raw_content)
        raw_result = _RawKecukupanResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        return [], True

    by_view_name = {entry.view_name: entry for entry in raw_result.penilaian}
    hasil: list[KecukupanKandidat] = []

    for kk in kandidat_tidak_pasti:
        entry = by_view_name.get(kk.kandidat.view_name)
        if entry is None:
            hasil.append(
                KecukupanKandidat(
                    kandidat=kk.kandidat,
                    kecocokan_label=kk.label,
                    cukup=False,
                    alasan="fallback_anomaly: kandidat tidak muncul di respons LLM, default aman tidak_cukup",
                    sumber_keputusan=SumberKeputusanKecukupan.LLM,
                )
            )
            continue

        hasil.append(
            KecukupanKandidat(
                kandidat=kk.kandidat,
                kecocokan_label=kk.label,
                cukup=bool(entry.cukup),
                alasan=entry.alasan,
                sumber_keputusan=SumberKeputusanKecukupan.LLM,
            )
        )

    return hasil, False


def _evaluasi_llm_fallback(
    atomic_intent: AtomicIntent, kandidat_tidak_pasti: list[KecocokanKandidat]
) -> list[KecukupanKandidat]:
    """SATU panggilan batch (bukan generate-verify penuh, decisions.md
    Keputusan 5) untuk seluruh kandidat `tidak_pasti` satu kebutuhan
    atomik sekaligus (Keputusan 7). Span `"chat"` HANYA dibuka kalau ada
    kandidat untuk dievaluasi (Keputusan 8)."""
    if not kandidat_tidak_pasti:
        return []

    tracer = get_tracer(_TRACER_NAME)
    prompt = load_prompt(_PROMPT_ID_FALLBACK)
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, "chat")
        span.set_attribute(GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL)
        span.set_attribute(PROMPT_ID, prompt.id)
        span.set_attribute(PROMPT_VERSION, prompt.version)

        try:
            response = _call_llm_fallback(atomic_intent, kandidat_tidak_pasti)
        except APIError as exc:
            span.set_attribute(
                "retriever.kecukupan_struktural.fallback_forced_default_reason", f"api_error: {exc}"
            )
            return _default_aman_semua(kandidat_tidak_pasti, f"fallback_teknis: api_error {exc}")

        if response.usage is not None:
            span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, response.usage.prompt_tokens)
            span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, response.usage.completion_tokens)

        if not response.choices:
            span.set_attribute(
                "retriever.kecukupan_struktural.fallback_forced_default_reason", "empty_choices"
            )
            return _default_aman_semua(kandidat_tidak_pasti, "fallback_teknis: empty_choices")

        raw_content = response.choices[0].message.content or ""
        hasil, gagal = _parse_fallback(raw_content, kandidat_tidak_pasti)

        if gagal:
            span.set_attribute(
                "retriever.kecukupan_struktural.fallback_forced_default_reason", "parse_error_total"
            )
            return _default_aman_semua(kandidat_tidak_pasti, "fallback_teknis: parse_error_total")

        span.set_attribute(
            "retriever.kecukupan_struktural.fallback_cukup_count",
            sum(1 for k in hasil if k.cukup),
        )
        return hasil


# --- Orkestrator per kebutuhan atomik + tie-break ---------------------------

_URUTAN_LABEL_KECOCOKAN = {
    LabelKecocokanMakna.DITEMUKAN: 0,
    LabelKecocokanMakna.SEBAGIAN: 1,
}


def _pilih_view_name_final(kecukupan: list[KecukupanKandidat]) -> str | None:
    """Tie-break decisions.md Keputusan 2 (dikonfirmasi user, sepakat
    rekomendasi): di antara kandidat `cukup=True`, prioritaskan label M3.2
    DITEMUKAN atas SEBAGIAN; dalam label sama, pilih skor `KandidatView`
    (M3.1) tertinggi. `None` kalau tidak ada kandidat cukup sama sekali."""
    kandidat_cukup = [k for k in kecukupan if k.cukup]
    if not kandidat_cukup:
        return None

    terpilih = min(
        kandidat_cukup,
        key=lambda k: (_URUTAN_LABEL_KECOCOKAN.get(k.kecocokan_label, 99), -k.kandidat.skor),
    )
    return terpilih.kandidat.view_name


def evaluasi_kecukupan_struktural_atomic_intent(
    hasil_kecocokan: HasilKecocokanMakna,
) -> HasilKecukupanStruktural:
    """Untuk SATU kebutuhan atomik (`HasilKecocokanMakna`, output M3.2):
    filter kandidat label ditemukan/sebagian (exclude tidak_ditemukan,
    Keputusan 3); jalankan `_evaluasi_deterministik` per kandidat;
    kumpulkan yang tidak_pasti, panggil `_evaluasi_llm_fallback` SEKALI
    (batch, Keputusan 7); gabungkan seluruh `KecukupanKandidat`; terapkan
    tie-break untuk memfinalkan `view_name_final`. `status` selalu
    BERHASIL (Keputusan 9 - mekanisme ini tidak pernah gagal teknis di
    level kebutuhan-atomik)."""
    kandidat_dievaluasi = [
        kk
        for kk in hasil_kecocokan.kecocokan
        if kk.label in (LabelKecocokanMakna.DITEMUKAN, LabelKecocokanMakna.SEBAGIAN)
    ]

    hasil_deterministik: list[KecukupanKandidat] = []
    kandidat_tidak_pasti: list[KecocokanKandidat] = []

    for kk in kandidat_dievaluasi:
        grain = GRAIN_STRUKTURAL_VIEW.get(kk.kandidat.view_name)
        if grain is None:
            # Tidak pernah terjadi di jalur normal (67 view bijektif dengan
            # taksonomi, dibuktikan test_grain_view.py) - fail-safe ke LLM
            # kalau genuinely terjadi, bukan exception yang memblokir.
            kandidat_tidak_pasti.append(kk)
            continue

        rule_hasil, alasan = _evaluasi_deterministik(
            hasil_kecocokan.atomic_intent.label_bentuk_jawaban, grain
        )
        if rule_hasil == "tidak_pasti":
            kandidat_tidak_pasti.append(kk)
        else:
            hasil_deterministik.append(
                KecukupanKandidat(
                    kandidat=kk.kandidat,
                    kecocokan_label=kk.label,
                    cukup=(rule_hasil == "cukup"),
                    alasan=alasan,
                    sumber_keputusan=SumberKeputusanKecukupan.DETERMINISTIK,
                )
            )

    hasil_fallback = _evaluasi_llm_fallback(hasil_kecocokan.atomic_intent, kandidat_tidak_pasti)

    seluruh_kecukupan = hasil_deterministik + hasil_fallback
    view_name_final = _pilih_view_name_final(seluruh_kecukupan)

    return HasilKecukupanStruktural(
        atomic_intent=hasil_kecocokan.atomic_intent,
        kecukupan=seluruh_kecukupan,
        view_name_final=view_name_final,
        status=StatusEksekusi.BERHASIL,
    )


# --- Orkestrator penutup pipeline Retriever (M3.1 -> M3.2 -> M3.3) ---------


def proses_retrieval_atomic_intent(
    atomic_intent: AtomicIntent, domain_diizinkan: list[Domain]
) -> HasilKecukupanStruktural:
    """Closing piece tiga langkah Retriever (M3.1-3.3, decisions.md
    Keputusan 4) - membuka span `retriever.cari_kandidat_view` (nama
    SAMA dengan wrapper standalone M3.1 `cari_kandidat_view()`) yang
    MEMBUNGKUS `_kumpulkan_kandidat()` (M3.1 pure) -> `nilai_kecocokan_
    makna_atomic_intent()` (M3.2, span `chat` anak) ->
    `evaluasi_kecukupan_struktural_atomic_intent()` (M3.3, span `chat`
    anak kondisional) sekaligus, lalu mengisi `retrieval.selected_view`
    SEBELUM span ditutup - memenuhi KK3 M3.3 secara literal (atribut ada
    di span `retriever.cari_kandidat_view` yang sama, bukan span baru)."""
    tracer = get_tracer(_RETRIEVER_TRACER_NAME)

    with tracer.start_as_current_span("retriever.cari_kandidat_view") as span:
        hasil_pencarian = _kumpulkan_kandidat(atomic_intent, domain_diizinkan)
        for key, value in _atribut_span_dari_hasil(hasil_pencarian).items():
            span.set_attribute(key, value)

        hasil_kecocokan = nilai_kecocokan_makna_atomic_intent(hasil_pencarian)
        hasil_kecukupan = evaluasi_kecukupan_struktural_atomic_intent(hasil_kecocokan)

        span.set_attribute("retrieval.selected_view", hasil_kecukupan.view_name_final or "")

        return hasil_kecukupan


# --- Orkestrator batch (M7.11): daftar AtomicIntentConstraint -> daftar HasilKecukupanStruktural ---


def proses_retrieval_semua(
    daftar_constraint: list[AtomicIntentConstraint],
) -> list[HasilKecukupanStruktural]:
    """Untuk seluruh `AtomicIntentConstraint` (M2.3, hasil rantai Domain
    Gate: identifikasi -> otorisasi -> cakupan-individu) dalam satu turn,
    jalankan pipeline Retriever (M3.1-3.3) satu per satu lewat
    `proses_retrieval_atomic_intent()` - mirror struktur
    `domain_gate.identifikasi_domain_semua()`/`domain_gate.periksa_
    otorisasi_semua()`/`domain_gate.deteksi_constraint_semua()`. Ditambah
    Milestone 7.11 (layer Retriever M3.1-3.3 sendiri belum py fungsi
    batch level-list, hanya per-item - lihat
    milestones/7.11-sambungan-retriever/decisions.md Keputusan 3).

    `domain_diizinkan` per item di-derive dari `domain_decisions` (filter
    `diizinkan=True`) - item dengan SELURUH domain ditolak tetap diproses
    apa adanya (`domain_diizinkan=[]`), TIDAK di-skip: `proses_retrieval_
    atomic_intent()` sudah terbukti aman menangani domain kosong (0
    kandidat -> `view_name_final=None`, `status=BERHASIL`, tidak crash) -
    lihat decisions.md Keputusan 7."""
    tracer = get_tracer(_RETRIEVER_TRACER_NAME)
    with tracer.start_as_current_span("retriever.proses_semua") as span:
        span.set_attribute("intent.count", len(daftar_constraint))

        hasil = [
            proses_retrieval_atomic_intent(
                item.atomic_intent,
                [keputusan.domain for keputusan in item.domain_decisions if keputusan.diizinkan],
            )
            for item in daftar_constraint
        ]

        return hasil
