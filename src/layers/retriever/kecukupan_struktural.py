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

from src.layers.retriever.grain_view import KarakteristikGrain
from src.schemas.session_memory import LabelBentukJawaban

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
