"""Penyimpanan dan Pengambilan Session Memory (Milestone 1.5, Langkah 3b
Context Resolution).

Murni pengambilan/penyimpanan data terstruktur - TIDAK ada pemanggilan LLM
sama sekali (beda total dari turn_dependency.py/rewrite.py). Berjalan
independen dari Milestone 1.4, hasilnya ditahan sampai dipakai Milestone 1.7.

Store DAN retrieve dua-duanya dibangun di sini (forced by Output M1.5
sendiri) meski peran resmi M1.5 di pipeline cuma retrieve ("Langkah 3b -
Tarik Data") - store dibutuhkan sebagai utilitas pendukung supaya milestone
ini bisa diuji end-to-end. Pemanggil produksi sisi store (Execution, M4.5)
baru datang belakangan. Lihat decisions.md Keputusan 4.
"""

from sqlmodel import Session

from src.config.database import get_engine
from src.db.models import SessionMemoryPackageRow
from src.schemas.session_memory import SessionMemoryPackage


def store_session_memory(package: SessionMemoryPackage) -> None:
    # mode="json" memastikan LabelBentukJawaban/StatusEksekusi (StrEnum)
    # diserialisasi ke .value ("nilai_tunggal") - bukan objek Enum itu sendiri.
    row = SessionMemoryPackageRow(**package.model_dump(mode="json"))
    with Session(get_engine()) as session:
        session.add(row)
        session.commit()
