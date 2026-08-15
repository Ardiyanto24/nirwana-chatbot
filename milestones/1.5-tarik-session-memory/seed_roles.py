"""Skrip seed sekali-jalan: baca src/config/roles.yaml, insert ke tabel
`roles` (Supabase) - Milestone 1.5 Checkpoint 8.

Skrip sekali-pakai (BUKAN bagian runtime permanen src/) - dijalankan manual
satu kali untuk migrasi awal, lihat decisions.md Keputusan 3.

Jalankan dari root repo: uv run python milestones/1.5-tarik-session-memory/seed_roles.py
"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlmodel import Session

from src.config.database import get_engine
from src.db.models import RoleRow

ROLES_YAML = Path(__file__).resolve().parents[2] / "src" / "config" / "roles.yaml"


def main() -> None:
    with open(ROLES_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    role_titles = data["roles"]

    with Session(get_engine()) as session:
        for role_title in role_titles:
            session.add(RoleRow(role_title=role_title))
        session.commit()

    print(f"{len(role_titles)} role di-seed ke tabel roles.")


if __name__ == "__main__":
    main()
