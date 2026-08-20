"""Riwayat Percakapan (Milestone 7.18) - lapisan penyimpanan BARU di
samping Session Memory, untuk kebutuhan APLIKASI (frontend menampilkan
riwayat sesi, analitik/audit masa depan) - BUKAN kebutuhan internal AI.
Concern PIC 7 sendiri (sejajar `src/layers/`, bukan salah satu 9 layer
arsitektur), mirror preseden `wave.py` (M7.14)/`paket_narasi.py` (M7.15).

`tentukan_status_keseluruhan_turn()`: murni deterministik, TANPA I/O -
agregasi status seluruh item `KeadaanTurn.paket_narasi` jadi SATU status
turn. "campuran" SENGAJA nilai baru (bukan reuse StatusEksekusi.SEBAGIAN
existing yang artinya "data basi" di level atomic-intent) - lihat
milestones/7.18-database-percakapan/decisions.md Keputusan 2.

`simpan_riwayat_turn()`: mirror POLA `store_session_memory()` PERSIS
(src/layers/context_resolution/session_memory.py) - tangkap Exception,
tandai error.type=gagal_teknis pada span, RAISE ulang apa adanya. Caller
(`src/main.py::_simpan_riwayat_percakapan_aman()`) yang BARU menerapkan
kebijakan "tangkap dan lanjutkan" - SATU-SATUNYA titik di seluruh
project dengan pola itu, forced literal KK2 M7.18. Lihat decisions.md
Keputusan 4-5.
"""

from sqlmodel import Session

from src.config.database import get_engine
from src.db.models import ConversationTurnRow
from src.observability.tracing import get_tracer
from src.schemas.session_memory import SessionMemoryPackage

_TRACER_NAME = "orchestration.riwayat_percakapan"


def tentukan_status_keseluruhan_turn(paket_narasi: list[SessionMemoryPackage]) -> str:
    if not paket_narasi:
        return "tidak_ada_kebutuhan"

    status_unik = {paket.status for paket in paket_narasi}
    if len(status_unik) == 1:
        return next(iter(status_unik)).value

    return "campuran"


def simpan_riwayat_turn(
    session_id: str, turn_index: int, pertanyaan: str, narasi: str, status: str
) -> None:
    row = ConversationTurnRow(
        session_id=session_id,
        turn_index=turn_index,
        pertanyaan=pertanyaan,
        narasi=narasi,
        status=status,
    )

    tracer = get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("riwayat.simpan") as span:
        span.set_attribute("session.id", session_id)
        span.set_attribute("turn.index", turn_index)
        span.set_attribute("riwayat.status", status)

        try:
            with Session(get_engine()) as session:
                session.add(row)
                session.commit()
        except Exception:
            span.set_attribute("error.type", "gagal_teknis")
            raise
