"""Loader tabel employees (Milestone 2.4) - HANYA dipakai test (fixture
realistis), TIDAK PERNAH dipanggil logic produksi verifikasi_gate().
Lihat src/db/models.py EmployeeRow, decisions.md Keputusan 2.

Mirror pola @lru_cache load_role_permissions() (src/config/
role_permissions.py, M2.2).
"""

from functools import lru_cache

from sqlmodel import Session, select

from src.config.database import get_engine
from src.db.models import EmployeeRow


@lru_cache(maxsize=1)
def load_employees() -> list[EmployeeRow]:
    with Session(get_engine()) as session:
        return list(session.exec(select(EmployeeRow)).all())
