"""Skrip seed sekali-jalan: DUA trace contoh tambahan untuk membuktikan KK1
(multi-wave) dan KK2 (span gagal) Milestone 5.3 — data sample M5.2
(`sample-...`, lihat seed_sample_trace.py) TIDAK cukup merepresentasikan
keduanya (semua error_type=null, hanya 1 span orchestration.wave).

TIDAK menyentuh/menghapus trace M5.2 existing (decisions.md M5.3 Keputusan
9) — murni INSERT baru, untuk uji regresi "1 trace lama + 2 trace baru
semua tampil" di Checkpoint 4.

Atribut span dikonfirmasi dari kode nyata, bukan dikarang bebas:
- wave.index/wave.intent_count: src/orchestration/turn_pipeline.py:234-237
- rbac.domain/rbac.decision/error.type=ditolak_otorisasi:
  src/layers/domain_gate/otorisasi.py:49-56
- error.type=gagal_teknis: src/layers/execution/klasifikasi_respons.py:197

Jalankan dari root repo: uv run python milestones/5.3-tampilan-waterfall-daftar-trace/seed_kk_scenarios.py
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session, SQLModel

from src.config.database import get_engine
from src.db.models import SpanRow, TraceRow

SessionMaker = Session


def _build_trace(
    trace_id: str,
    session_id: str,
    status: str,
    role_title: str,
    start: datetime,
    span_defs: list[tuple[str, str | None, str, str, int, int, str | None, dict]],
) -> tuple[TraceRow, list[SpanRow]]:
    span_id_map = {suffix: f"{trace_id}-{suffix}" for suffix, *_ in span_defs}
    total_ms = max(offset + dur for _, _, _, _, offset, dur, _, _ in span_defs)

    trace = TraceRow(
        trace_id=trace_id,
        session_id=session_id,
        turn_index=1,
        started_at=start,
        ended_at=start + timedelta(milliseconds=total_ms),
        status=status,
        role_title=role_title,
    )

    spans: list[SpanRow] = []
    for suffix, parent_suffix, layer_name, operation_name, offset_ms, duration_ms, error_type, extra_attrs in span_defs:
        started = start + timedelta(milliseconds=offset_ms)
        attributes = {"sample_data": True, "seeded_by": "milestone-5.3", **extra_attrs}
        spans.append(
            SpanRow(
                span_id=span_id_map[suffix],
                trace_id=trace_id,
                parent_span_id=span_id_map[parent_suffix] if parent_suffix else None,
                layer_name=layer_name,
                operation_name=operation_name,
                started_at=started,
                ended_at=started + timedelta(milliseconds=duration_ms),
                duration_ms=duration_ms,
                error_type=error_type,
                attributes=attributes,
            )
        )
    return trace, spans


def build_multiwave_trace() -> tuple[TraceRow, list[SpanRow]]:
    """KK1: turn dengan >1 atomic intent diproses di wave berbeda - DUA span
    orchestration.wave sibling di bawah invoke_agent (wave.index=1 dan 2),
    wave 2 mulai sesaat setelah wave 1 selesai (sequential, pola nyata
    M7.14). Seluruhnya berhasil (error_type=null semua)."""
    trace_id = "sample-mw-" + uuid.uuid4().hex[:10]
    start = datetime(2026, 8, 21, 9, 0, 0, tzinfo=timezone.utc)

    defs: list[tuple[str, str | None, str, str, int, int, str | None, dict]] = [
        ("root", None, "orchestration", "invoke_agent", 0, 38000, None, {}),
        ("input", "root", "input_layer", "input.validate", 5, 40, None, {}),
        ("turndep", "root", "context_resolution", "chat", 80, 1600, None, {}),
        ("rewrite", "root", "context_resolution", "chat", 1700, 2000, None, {}),
        ("decklas", "root", "decomposition", "chat", 3750, 1900, None, {}),
        ("decpec", "root", "decomposition", "chat", 5700, 2100, None, {}),
        ("decver", "root", "decomposition", "chat", 7850, 1500, None, {}),
        ("dgident", "root", "domain_gate", "domain_gate.identifikasi_semua", 9400, 4200, None, {}),
        ("dgident_c1", "dgident", "domain_gate", "chat", 9450, 2000, None, {}),
        ("dgident_c2", "dgident", "domain_gate", "chat", 11500, 2050, None, {}),
        ("dgotor", "root", "domain_gate", "domain_gate.periksa_otorisasi_semua", 13650, 90, None, {}),
        ("dgotor_c1", "dgotor", "domain_gate", "authorization.check", 13655, 80, None,
         {"rbac.domain": "reservation", "rbac.decision": "allow"}),
        ("retr", "root", "retriever", "retriever.proses_semua", 13780, 6200, None, {}),
        ("retr_cari", "retr", "retriever", "retriever.cari_kandidat_view", 13790, 6150, None, {}),
        ("retr_c1", "retr_cari", "retriever", "chat", 13800, 3000, None, {}),
        ("retr_c2", "retr_cari", "retriever", "chat", 16820, 3100, None, {}),
        ("qe", "root", "query_engine", "query_engine.susun_dan_verifikasi_request_semua", 20020, 2900, None, {}),
        ("qe_c1", "qe", "query_engine", "chat", 20030, 1400, None, {}),
        ("qe_c2", "qe", "query_engine", "chat", 21450, 1450, None, {}),
        # --- Wave 1: atomic intent pertama ---
        ("wave1", "root", "orchestration", "orchestration.wave", 22950, 2400, None,
         {"wave.index": 1, "wave.intent_count": 1}),
        ("wave1_vgate", "wave1", "verification_gate", "verification_gate.verifikasi_gate_semua", 22960, 12, None, {}),
        ("wave1_exec", "wave1", "execution", "execution.eksekusi_atomic_intent_semua", 22980, 2350, None, {}),
        # --- Wave 2: atomic intent kedua, dependen pada hasil wave 1 (M7.14 semantik) ---
        ("wave2", "root", "orchestration", "orchestration.wave", 25370, 2600, None,
         {"wave.index": 2, "wave.intent_count": 1}),
        ("wave2_vgate", "wave2", "verification_gate", "verification_gate.verifikasi_gate_semua", 25380, 10, None, {}),
        ("wave2_exec", "wave2", "execution", "execution.eksekusi_atomic_intent_semua", 25400, 2550, None, {}),
        ("execsave", "root", "execution", "execution.susun_dan_simpan_paket_semua", 27990, 10, None, {}),
        ("narpaket", "root", "orchestration", "orchestration.susun_paket_narasi", 28005, 5, None, {}),
        ("narasi", "root", "interpretation", "chat", 28030, 4900, None, {}),
        ("verkes", "root", "interpretation", "chat", 32960, 5000, None, {}),
    ]

    return _build_trace(
        trace_id=trace_id,
        session_id="sample-session-m5.3-multiwave",
        status="berhasil",
        role_title="General Manager",
        start=start,
        span_defs=defs,
    )


def build_failed_trace() -> tuple[TraceRow, list[SpanRow]]:
    """KK2: span berstatus gagal (error_type terisi) - mirror pola nyata
    skenario RBAC-denial gop_margin M5.1 (Front Office Staff vs domain
    financial): >=2 authorization.check dengan error.type=ditolak_otorisasi,
    ditambah 1 execution.eksekusi_atomic_intent_semua dengan
    error.type=gagal_teknis (jalur revisi 400 exhausted, pola nyata M7.14)."""
    trace_id = "sample-fail-" + uuid.uuid4().hex[:10]
    start = datetime(2026, 8, 21, 9, 30, 0, tzinfo=timezone.utc)

    defs: list[tuple[str, str | None, str, str, int, int, str | None, dict]] = [
        ("root", None, "orchestration", "invoke_agent", 0, 30000, None, {}),
        ("input", "root", "input_layer", "input.validate", 5, 40, None, {}),
        ("turndep", "root", "context_resolution", "chat", 80, 1500, None, {}),
        ("rewrite", "root", "context_resolution", "chat", 1600, 1900, None, {}),
        ("decklas", "root", "decomposition", "chat", 3550, 1800, None, {}),
        ("decpec", "root", "decomposition", "chat", 5400, 2000, None, {}),
        ("decver", "root", "decomposition", "chat", 7450, 1600, None, {}),
        ("dgident", "root", "domain_gate", "domain_gate.identifikasi_semua", 9100, 4000, None, {}),
        ("dgident_c1", "dgident", "domain_gate", "chat", 9150, 1900, None, {}),
        ("dgident_c2", "dgident", "domain_gate", "chat", 11100, 1950, None, {}),
        ("dgotor", "root", "domain_gate", "domain_gate.periksa_otorisasi_semua", 13150, 260, None, {}),
        # Dua domain DITOLAK (KK2 inti) + satu domain diizinkan, mirror
        # gop_margin M5.1: Front Office Staff bertanya gop_margin (financial,
        # ditolak) sambil menyentuh reservation (diizinkan).
        ("dgotor_c1", "dgotor", "domain_gate", "authorization.check", 13160, 80, "ditolak_otorisasi",
         {"rbac.domain": "financial", "rbac.decision": "deny"}),
        ("dgotor_c2", "dgotor", "domain_gate", "authorization.check", 13245, 75, None,
         {"rbac.domain": "reservation", "rbac.decision": "allow"}),
        ("dgotor_c3", "dgotor", "domain_gate", "authorization.check", 13325, 80, "ditolak_otorisasi",
         {"rbac.domain": "financial", "rbac.decision": "deny"}),
        ("retr", "root", "retriever", "retriever.proses_semua", 13420, 5800, None, {}),
        ("retr_cari", "retr", "retriever", "retriever.cari_kandidat_view", 13430, 5750, None, {}),
        ("retr_c1", "retr_cari", "retriever", "chat", 13440, 2800, None, {}),
        ("retr_c2", "retr_cari", "retriever", "chat", 16250, 2900, None, {}),
        ("qe", "root", "query_engine", "query_engine.susun_dan_verifikasi_request_semua", 19230, 2700, None, {}),
        ("qe_c1", "qe", "query_engine", "chat", 19240, 1300, None, {}),
        ("qe_c2", "qe", "query_engine", "chat", 20560, 1350, None, {}),
        ("wave1", "root", "orchestration", "orchestration.wave", 21940, 2500, None,
         {"wave.index": 1, "wave.intent_count": 1}),
        ("wave1_vgate", "wave1", "verification_gate", "verification_gate.verifikasi_gate_semua", 21950, 12, None, {}),
        # Jalur revisi 400 exhausted (pola nyata M7.14) - kegagalan teknis
        # SETELAH lolos verification gate, beda penyebab dari penolakan RBAC
        # di atas (KK2 sengaja mencakup DUA jenis error_type berbeda).
        ("wave1_exec", "wave1", "execution", "execution.eksekusi_atomic_intent_semua", 21970, 2450, "gagal_teknis",
         {"execution.kegagalan_alasan": "revisi_exhausted"}),
        ("execsave", "root", "execution", "execution.susun_dan_simpan_paket_semua", 24430, 10, None, {}),
        ("narpaket", "root", "orchestration", "orchestration.susun_paket_narasi", 24445, 5, None, {}),
        ("narasi", "root", "interpretation", "chat", 24470, 5100, None, {}),
    ]

    return _build_trace(
        trace_id=trace_id,
        session_id="sample-session-m5.3-failed",
        # Campuran (2 domain ditolak + 1 gagal teknis + sebagian lolos) -
        # "sebagian" paling merepresentasikan hasil campuran dibanding
        # memilih salah satu jenis kegagalan sebagai label tunggal.
        status="sebagian",
        role_title="Front Office Staff",
        start=start,
        span_defs=defs,
    )


def main() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    mw_trace, mw_spans = build_multiwave_trace()
    fail_trace, fail_spans = build_failed_trace()
    # trace_id sudah diset eksplisit (bukan auto-generated) - aman dibaca
    # sebelum session ditutup (hindari DetachedInstanceError expire_on_commit).
    mw_trace_id, fail_trace_id = mw_trace.trace_id, fail_trace.trace_id

    with Session(engine) as session:
        session.add(mw_trace)
        session.add(fail_trace)
        session.commit()

        session.add_all(mw_spans)
        session.add_all(fail_spans)
        session.commit()

    print(f"multiwave trace_id={mw_trace_id} ({len(mw_spans)} span, 2x orchestration.wave sibling)")
    print(f"failed    trace_id={fail_trace_id} ({len(fail_spans)} span, "
          f"{sum(1 for s in fail_spans if s.error_type)} span error_type terisi)")


if __name__ == "__main__":
    main()
