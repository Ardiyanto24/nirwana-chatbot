"""Penyimpanan dan Pengambilan Session Memory (Milestone 1.5, Langkah 3b
Context Resolution).

Murni pengambilan/penyimpanan data terstruktur - TIDAK ada pemanggilan LLM
sama sekali (beda total dari turn_dependency.py/rewrite.py). Berjalan
independen dari Milestone 1.4, hasilnya ditahan sampai dipakai Milestone 1.7.

Store DAN retrieve dua-duanya dibangun di sini (forced by Output M1.5
sendiri) meski peran resmi M1.5 di pipeline cuma retrieve ("Langkah 3b -
Tarik Data") - store dibutuhkan sebagai utilitas pendukung supaya milestone
ini bisa diuji end-to-end. Pemanggil produksi sisi store (Execution, M4.3
- "Membangun Penyimpanan Paket ke Session Memory") baru datang belakangan.
Lihat decisions.md Keputusan 4.
"""

from sqlmodel import Session, select

from src.config.database import get_engine
from src.db.models import SessionMemoryPackageRow
from src.observability.tracing import get_tracer
from src.schemas.session_memory import SessionMemoryPackage

_TRACER_NAME = "context_resolution.session_memory"


def store_session_memory(package: SessionMemoryPackage) -> None:
    # mode="json" memastikan LabelBentukJawaban/StatusEksekusi (StrEnum)
    # diserialisasi ke .value ("nilai_tunggal") - bukan objek Enum itu sendiri.
    row = SessionMemoryPackageRow(**package.model_dump(mode="json"))
    with Session(get_engine()) as session:
        session.add(row)
        session.commit()


def retrieve_session_memory(session_id: str, turn_index: int) -> list[SessionMemoryPackage]:
    """Kembalikan seluruh paket Session Memory milik {session_id, turn_index}.
    List kosong (BUKAN exception) kalau turn belum pernah ada/tidak py data -
    forced by Kriteria Keberhasilan sumber."""
    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("memory.retrieve") as span:
        span.set_attribute("session.id", session_id)
        span.set_attribute("turn.index", turn_index)

        with Session(get_engine()) as session:
            statement = select(SessionMemoryPackageRow).where(
                SessionMemoryPackageRow.session_id == session_id,
                SessionMemoryPackageRow.turn_index == turn_index,
            )
            rows = session.exec(statement).all()

        span.set_attribute("memory.packages_found", len(rows))
        return [
            SessionMemoryPackage.model_validate(row.model_dump()) for row in rows
        ]
