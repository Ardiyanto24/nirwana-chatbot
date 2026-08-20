"""Skrip seed sekali-jalan: buat tabel traces/spans (PERTAMA KALI di project
ini, PIC 6/custom exporter belum ada) + insert satu trace contoh realistis -
Milestone 5.2, decisions.md Keputusan 7 (lokasi+bentuk mirror
milestones/2.4-verification-gate/seed_employees.py).

Struktur trace meniru bentuk nyata M5.1 (milestones/5.1-membangun-dashboard-
grafana/logs.md, trace d13c84ac... 28 span) - root invoke_agent membungkus
9 layer, TERMASUK percabangan paralel Rewrite+Tarik Session Memory (M7.7)
supaya buildSpanTree() Next.js (M5.2 Checkpoint 5) diuji terhadap struktur
genuinely bercabang, bukan rantai linear.

Jalankan dari root repo: uv run python milestones/5.2-skema-data-koneksi-nextjs-supabase/seed_sample_trace.py
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session, SQLModel

from src.config.database import get_engine
from src.db.models import SpanRow, TraceRow

TRACE_ID = "sample-" + uuid.uuid4().hex[:12]
SESSION_ID = "sample-session-m5.2"
TRACE_START = datetime(2026, 8, 20, 10, 0, 0, tzinfo=timezone.utc)

# (span_id_suffix, parent_id_suffix atau None, layer_name, operation_name,
#  offset_ms dari TRACE_START, duration_ms)
# Offset overlap sengaja dipakai untuk pasangan rewrite/memory.retrieve
# (paralel nyata sejak M7.7) supaya struktur genuinely bercabang, bukan
# rantai linear kebetulan.
SPAN_DEFS: list[tuple[str, str | None, str, str, int, int]] = [
    ("root", None, "orchestration", "invoke_agent", 0, 42000),
    ("input", "root", "input_layer", "input.validate", 10, 45),
    ("turndep", "root", "context_resolution", "chat", 100, 1800),
    ("rewrite", "root", "context_resolution", "chat", 1950, 2200),
    ("memretr", "root", "context_resolution", "memory.retrieve", 1950, 900),
    ("decklas", "root", "decomposition", "chat", 4200, 2100),
    ("decpec", "root", "decomposition", "chat", 6350, 2400),
    ("decver", "root", "decomposition", "chat", 8800, 1600),
    ("dgident", "root", "domain_gate", "domain_gate.identifikasi_semua", 10450, 6200),
    ("dgident_c1", "dgident", "domain_gate", "chat", 10500, 3000),
    ("dgident_c2", "dgident", "domain_gate", "chat", 13550, 3050),
    ("dgotor", "root", "domain_gate", "domain_gate.periksa_otorisasi_semua", 16700, 120),
    ("dgotor_c1", "dgotor", "domain_gate", "authorization.check", 16710, 100),
    ("dgconstr", "root", "domain_gate", "domain_gate.deteksi_constraint_semua", 16850, 5),
    ("dgconstr_c1", "dgconstr", "domain_gate", "domain_gate.cakupan_individu.check", 16852, 2),
    ("retr", "root", "retriever", "retriever.proses_semua", 16900, 8500),
    ("retr_cari", "retr", "retriever", "retriever.cari_kandidat_view", 16910, 8450),
    ("retr_c1", "retr_cari", "retriever", "chat", 16920, 3900),
    ("retr_c2", "retr_cari", "retriever", "chat", 20850, 4450),
    ("qe", "root", "query_engine", "query_engine.susun_dan_verifikasi_request_semua", 25450, 3400),
    ("qe_c1", "qe", "query_engine", "chat", 25460, 1600),
    ("qe_c2", "qe", "query_engine", "chat", 27080, 1750),
    ("wave", "root", "orchestration", "orchestration.wave", 28900, 2100),
    ("vgate", "wave", "verification_gate", "verification_gate.verifikasi_gate_semua", 28910, 15),
    ("exec", "wave", "execution", "execution.eksekusi_atomic_intent_semua", 28930, 2050),
    ("execsave", "root", "execution", "execution.susun_dan_simpan_paket_semua", 31050, 8),
    ("narpaket", "root", "orchestration", "orchestration.susun_paket_narasi", 31070, 4),
    ("narasi", "root", "interpretation", "chat", 31100, 5600),
    ("verkes", "root", "interpretation", "chat", 36750, 5100),
]

SPAN_ID_MAP = {suffix: f"{TRACE_ID}-{suffix}" for suffix, *_ in SPAN_DEFS}


def build_rows() -> tuple[TraceRow, list[SpanRow]]:
    trace = TraceRow(
        trace_id=TRACE_ID,
        session_id=SESSION_ID,
        turn_index=1,
        started_at=TRACE_START,
        ended_at=TRACE_START + timedelta(milliseconds=42000),
        status="berhasil",
        role_title="General Manager",
    )

    spans: list[SpanRow] = []
    for suffix, parent_suffix, layer_name, operation_name, offset_ms, duration_ms in SPAN_DEFS:
        started = TRACE_START + timedelta(milliseconds=offset_ms)
        spans.append(
            SpanRow(
                span_id=SPAN_ID_MAP[suffix],
                trace_id=TRACE_ID,
                parent_span_id=SPAN_ID_MAP[parent_suffix] if parent_suffix else None,
                layer_name=layer_name,
                operation_name=operation_name,
                started_at=started,
                ended_at=started + timedelta(milliseconds=duration_ms),
                duration_ms=duration_ms,
                error_type=None,
                attributes={"sample_data": True, "seeded_by": "milestone-5.2"},
            )
        )
    return trace, spans


def main() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)

    trace, spans = build_rows()
    with Session(engine) as session:
        # Commit trace SEBELUM spans secara eksplisit (bukan digabung satu
        # commit) - FK constraint spans.trace_id butuh baris traces sudah
        # benar-benar ter-commit lebih dulu, bukan cuma ter-flush di unit of
        # work yang sama (lihat logs.md Checkpoint 2 - FK violation kalau
        # digabung satu commit).
        session.add(trace)
        session.commit()
        session.add_all(spans)
        session.commit()

    print(f"trace_id={TRACE_ID}")
    print(f"{len(spans)} span diinsert (root={SPAN_ID_MAP['root']}).")


if __name__ == "__main__":
    main()
