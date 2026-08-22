"""Orkestrator Pengumpulan Kandidat View (Milestone 3.1): `cari_bm25()`
sebagai jalur utama, `cari_embedding()` sebagai fallback KONDISIONAL
(hanya dipanggil kalau `perlu_fallback=True`).

Span pembungkus `retriever.cari_kandidat_view` (tracer `retriever.
retriever`) dengan `retrieval.candidates_count` wajib (kontrak
`rancangan-observability-ai-chatbot.md` Bagian 2 baris 39) + atribut
tambahan `retrieval.fallback_terpicu`/`retrieval.sumber_utama`. Span anak
`retriever.pencarian_embedding_fallback` (`gen_ai.operation.name=
"embeddings"`, `gen_ai.request.model`) HANYA muncul kalau fallback
benar-benar terpicu - lihat decisions.md Keputusan 5 (filter struktural)
dan Keputusan 8 (retrieval.selected_view TIDAK diisi di sini, milik M3.3).

Direfactor Milestone 3.3 (Checkpoint 9, lihat milestones/3.3-kecukupan-
struktural/decisions.md Keputusan 4): logic murni diekstrak ke
`_kumpulkan_kandidat()` (TANPA span sendiri) supaya orkestrator penutup
pipeline M3.1-3.3 (`kecukupan_struktural.proses_retrieval_atomic_intent()`)
bisa membuka span `retriever.cari_kandidat_view` yang MEMBUNGKUS M3.1+
M3.2+M3.3 sekaligus, lalu mengisi `retrieval.selected_view` sebelum span
ditutup - memenuhi KK3 M3.3 secara literal (atribut itu ada di span
`retriever.cari_kandidat_view`, bukan span baru). `cari_kandidat_view()`
publik (fungsi ini) TIDAK berubah perilaku/signature/span sama sekali
untuk pemanggil standalone - tetap membuka span sendiri via wrapper tipis
di bawah, regresi test_retriever.py dijalankan penuh tanpa perubahan
assertion untuk membuktikannya.
"""

from src.config.llm import OPENROUTER_MODEL_RETRIEVER_EMBEDDING
from src.layers.retriever.pencarian_bm25 import cari_bm25
from src.layers.retriever.pencarian_embedding import cari_embedding
from src.observability.genai_semconv import GEN_AI_OPERATION_NAME, GEN_AI_REQUEST_MODEL
from src.observability.tracing import get_tracer
from src.schemas.decomposition import AtomicIntent
from src.schemas.domain_gate import Domain
from src.schemas.retriever import HasilPencarianKandidat, KandidatView
from src.schemas.session_memory import StatusEksekusi

_TRACER_NAME = "retriever.retriever"


def _union_kandidat(
    bm25: list[KandidatView], embedding: list[KandidatView]
) -> list[KandidatView]:
    """Gabung kandidat BM25+embedding, dedup by view_name - BM25
    diprioritaskan kalau sama (sumber asli dipertahankan). TIDAK diurutkan
    ulang lintas skor gabungan - skor BM25 dan cosine similarity embedding
    tidak sepadan diperbandingkan langsung (skala berbeda), masing-masing
    tetap terurut menurun di dalam kelompok sumbernya sendiri."""
    dilihat = {k.view_name for k in bm25}
    return list(bm25) + [k for k in embedding if k.view_name not in dilihat]


def _kumpulkan_kandidat(
    atomic_intent: AtomicIntent, domain_diizinkan: list[Domain]
) -> HasilPencarianKandidat:
    """Logic murni M3.1 (BM25 + fallback embedding kondisional), TANPA
    membuka span `retriever.cari_kandidat_view` sendiri - span anak
    `retriever.pencarian_embedding_fallback` TETAP dibuka di sini (masih
    milik tanggung jawab M3.1), otomatis jadi anak span apa pun yang
    sedang aktif di context pemanggil (span parent-child OTel via
    contextvars, tidak perlu diteruskan eksplisit)."""
    kandidat_bm25, perlu_fallback = cari_bm25(
        atomic_intent.teks_kebutuhan, domain_diizinkan
    )

    if not perlu_fallback:
        return HasilPencarianKandidat(
            atomic_intent=atomic_intent,
            domain_diizinkan=domain_diizinkan,
            kandidat=kandidat_bm25,
            fallback_terpicu=False,
            status=StatusEksekusi.BERHASIL,
        )

    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(
        "retriever.pencarian_embedding_fallback"
    ) as span_fallback:
        span_fallback.set_attribute(GEN_AI_OPERATION_NAME, "embeddings")
        span_fallback.set_attribute(
            GEN_AI_REQUEST_MODEL, OPENROUTER_MODEL_RETRIEVER_EMBEDDING
        )

        kandidat_embedding, gagal = cari_embedding(
            atomic_intent.teks_kebutuhan,
            domain_diizinkan,
            OPENROUTER_MODEL_RETRIEVER_EMBEDDING,
        )

        if gagal:
            span_fallback.set_attribute("error.type", "gagal_teknis")

    kandidat_gabungan = _union_kandidat(kandidat_bm25, kandidat_embedding)
    status = StatusEksekusi.SEBAGIAN if gagal else StatusEksekusi.BERHASIL

    return HasilPencarianKandidat(
        atomic_intent=atomic_intent,
        domain_diizinkan=domain_diizinkan,
        kandidat=kandidat_gabungan,
        fallback_terpicu=True,
        status=status,
    )


def _atribut_span_dari_hasil(hasil: HasilPencarianKandidat) -> dict:
    """Turunkan atribut span `retrieval.*` dari `HasilPencarianKandidat`
    - dipakai baik oleh wrapper standalone `cari_kandidat_view()` di
    bawah maupun orkestrator penutup pipeline M3.3
    (`kecukupan_struktural.proses_retrieval_atomic_intent()`), supaya
    logic derivasinya SATU tempat, tidak diduplikasi."""
    if not hasil.fallback_terpicu or hasil.status == StatusEksekusi.SEBAGIAN:
        sumber_utama = "bm25"
    else:
        sumber_utama = "embedding_fallback"

    return {
        "retrieval.candidates_count": len(hasil.kandidat),
        "retrieval.fallback_terpicu": hasil.fallback_terpicu,
        "retrieval.sumber_utama": sumber_utama,
    }


def cari_kandidat_view(
    atomic_intent: AtomicIntent, domain_diizinkan: list[Domain]
) -> HasilPencarianKandidat:
    """Entry point standalone M3.1 - wrapper tipis di atas
    `_kumpulkan_kandidat()`, membuka+menutup span `retriever.
    cari_kandidat_view` sendiri (perilaku/signature/atribut span IDENTIK
    dengan sebelum refactor Checkpoint 9 M3.3). Dipakai kalau kandidat
    view DIBUTUHKAN BERDIRI SENDIRI (mis. test M3.1) - jalur produksi
    penuh M3.1+M3.2+M3.3 lewat `kecukupan_struktural.
    proses_retrieval_atomic_intent()` yang membuka span bernama sama
    tapi membungkus ketiga langkah sekaligus."""
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("retriever.cari_kandidat_view") as span:
        hasil = _kumpulkan_kandidat(atomic_intent, domain_diizinkan)
        for key, value in _atribut_span_dari_hasil(hasil).items():
            span.set_attribute(key, value)
        return hasil
