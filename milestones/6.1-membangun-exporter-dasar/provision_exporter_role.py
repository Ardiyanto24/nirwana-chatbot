"""Provisioning role Postgres write-only untuk kredensial exporter Go
(Milestone 6.1, decisions.md Keputusan Jenis B "Kredensial Postgres
write-only BARU") - GRANT INSERT+SELECT ke traces+spans, PLUS UPDATE
KHUSUS ke traces (bukan spans), terpisah dari DATABASE_URL Python
(read-write penuh) dan nirwana_dashboard_reader (read-only, M5.2). SELECT
dibutuhkan exporter untuk cek trace_id existing sebelum INSERT (lihat
strategi buffering Checkpoint 7) - bukan untuk baca data lain.

UPDATE pada traces ditemukan wajib lewat verifikasi nyata Checkpoint 8
(E2E test asli, `permission denied for table traces (SQLSTATE 42501)`
saat pgx menjalankan `INSERT ... ON CONFLICT (trace_id) DO UPDATE ...`) -
Postgres mewajibkan privilege UPDATE untuk cabang ON CONFLICT DO UPDATE
UPSERT, bukan cuma INSERT untuk cabang insert murni (dikonfirmasi INSERT
polos berhasil via psycopg terpisah, DO UPDATE yang gagal). spans TIDAK
butuh UPDATE - `spanInsertArgs()` pakai ON CONFLICT DO NOTHING (span_id
unik, data tidak pernah berubah setelah diekspor).

Mirror persis pola milestones/5.2-.../provision_readonly_role.py. Skrip
sekali-pakai (BUKAN bagian runtime permanen src/). Password role BARU
dibaca dari env var NEW_EXPORTER_ROLE_PASSWORD (bukan argumen CLI/hardcode)
supaya tidak muncul di shell history/git - password itu sendiri TIDAK
PERNAH di-print.

Jalankan dari root repo:
  NEW_EXPORTER_ROLE_PASSWORD=<password> uv run python milestones/6.1-membangun-exporter-dasar/provision_exporter_role.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from src.config.database import get_engine

ROLE_NAME = "nirwana_exporter_writer"


def main() -> None:
    password = os.environ.get("NEW_EXPORTER_ROLE_PASSWORD")
    if not password:
        raise RuntimeError("Set env var NEW_EXPORTER_ROLE_PASSWORD dulu.")
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
        conn.execute(
            text(f"GRANT SELECT, INSERT ON public.traces, public.spans TO {ROLE_NAME}")
        )
        conn.execute(text(f"GRANT UPDATE ON public.traces TO {ROLE_NAME}"))

    print(
        f"Role {ROLE_NAME}: dibuat/diperbarui, GRANT SELECT+INSERT ke traces+spans "
        "dan UPDATE ke traces selesai."
    )


if __name__ == "__main__":
    main()
