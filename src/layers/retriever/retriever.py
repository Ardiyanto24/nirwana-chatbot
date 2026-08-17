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


def cari_kandidat_view(
    atomic_intent: AtomicIntent, domain_diizinkan: list[Domain]
) -> HasilPencarianKandidat:
    tracer = get_tracer(_TRACER_NAME)

    with tracer.start_as_current_span("retriever.cari_kandidat_view") as span:
        kandidat_bm25, perlu_fallback = cari_bm25(
            atomic_intent.teks_kebutuhan, domain_diizinkan
        )

        if not perlu_fallback:
            span.set_attribute("retrieval.candidates_count", len(kandidat_bm25))
            span.set_attribute("retrieval.fallback_terpicu", False)
            span.set_attribute("retrieval.sumber_utama", "bm25")
            return HasilPencarianKandidat(
                atomic_intent=atomic_intent,
                domain_diizinkan=domain_diizinkan,
                kandidat=kandidat_bm25,
                fallback_terpicu=False,
                status=StatusEksekusi.BERHASIL,
            )

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

        span.set_attribute("retrieval.candidates_count", len(kandidat_gabungan))
        span.set_attribute("retrieval.fallback_terpicu", True)
        span.set_attribute(
            "retrieval.sumber_utama", "bm25" if gagal else "embedding_fallback"
        )

        return HasilPencarianKandidat(
            atomic_intent=atomic_intent,
            domain_diizinkan=domain_diizinkan,
            kandidat=kandidat_gabungan,
            fallback_terpicu=True,
            status=status,
        )
