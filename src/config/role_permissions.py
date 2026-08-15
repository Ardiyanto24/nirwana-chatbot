"""Loader untuk matriks otorisasi role x domain (Milestone 2.2).

Query tabel role_permissions (Supabase, salinan Lapis-1 milik proyek ini
sendiri - lihat src/db/models.py RolePermissionRow) sekali per siklus
hidup proses, mirror pola @lru_cache load_valid_roles() (src/config/
roles.py, M1.5).
"""

from functools import lru_cache

from sqlmodel import Session, select

from src.config.database import get_engine
from src.db.models import RolePermissionRow
from src.schemas.domain_gate import Domain


@lru_cache(maxsize=1)
def load_role_permissions() -> dict[str, frozenset[Domain]]:
    with Session(get_engine()) as session:
        rows = session.exec(
            select(RolePermissionRow.role_title, RolePermissionRow.domain)
        ).all()

    result: dict[str, set[Domain]] = {}
    for role_title, domain in rows:
        result.setdefault(role_title, set()).add(Domain(domain))
    return {role_title: frozenset(domains) for role_title, domains in result.items()}
