"""Provisioning role Postgres read-only untuk kredensial Next.js (Milestone
5.2, decisions.md Keputusan 9) - GRANT SELECT saja ke traces/spans, terpisah
dari DATABASE_URL Python (yang punya akses read-write tabel lain).

Skrip sekali-pakai (BUKAN bagian runtime permanen src/), mirror lokasi
seed_role_permissions.py Milestone 2.2. Password role BARU dibaca dari env
var NEW_READONLY_ROLE_PASSWORD (bukan argumen CLI/hardcode) supaya tidak
muncul di shell history/git - password itu sendiri TIDAK PERNAH di-print.

Jalankan dari root repo:
  NEW_READONLY_ROLE_PASSWORD=<password> uv run python milestones/5.2-skema-data-koneksi-nextjs-supabase/provision_readonly_role.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from src.config.database import get_engine

ROLE_NAME = "nirwana_dashboard_reader"


def main() -> None:
    password = os.environ.get("NEW_READONLY_ROLE_PASSWORD")
    if not password:
        raise RuntimeError("Set env var NEW_READONLY_ROLE_PASSWORD dulu.")
    # Password digenerate via secrets.token_urlsafe() (alfanumerik+-_ saja,
    # tanpa quote/karakter SQL spesial) - bukan input pengguna, aman
    # diinterpolasi langsung ke DDL tanpa risiko injection.
    if any(c in password for c in "'\";\\"):
        raise RuntimeError("Password mengandung karakter tidak aman untuk DDL literal.")

    engine = get_engine()
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": ROLE_NAME}
        ).fetchone()
        if exists:
            print(f"Role {ROLE_NAME} sudah ada - ALTER PASSWORD + re-apply GRANT.")
            conn.execute(text(f"ALTER ROLE {ROLE_NAME} WITH LOGIN PASSWORD '{password}'"))
        else:
            conn.execute(text(f"CREATE ROLE {ROLE_NAME} WITH LOGIN PASSWORD '{password}'"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {ROLE_NAME}"))
        conn.execute(text(f"GRANT SELECT ON public.traces, public.spans TO {ROLE_NAME}"))

    print(f"Role {ROLE_NAME}: dibuat/diperbarui, GRANT SELECT ke traces+spans selesai.")


if __name__ == "__main__":
    main()
