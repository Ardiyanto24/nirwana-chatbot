"""Loader untuk daftar role_title yang dikenal sistem.

Dimigrasi ke database (tabel `roles`, Supabase) di Milestone 1.5 - lihat
milestones/1.5-tarik-session-memory/decisions.md Keputusan 3/9. `@lru_cache`
dipertahankan: query DB cuma sekali per siklus hidup proses (cold start),
BUKAN per-request - mitigasi sadar atas Input Layer yang sebelumnya murni
in-memory sekarang transitif bergantung pada koneksi database.
"""

from functools import lru_cache

from sqlmodel import Session, select

from src.config.database import get_engine
from src.db.models import RoleRow


@lru_cache(maxsize=1)
def load_valid_roles() -> frozenset[str]:
    with Session(get_engine()) as session:
        rows = session.exec(select(RoleRow.role_title)).all()
    return frozenset(rows)
