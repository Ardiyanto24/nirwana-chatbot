"""Konfigurasi koneksi database (Supabase/Postgres) untuk proyek.

Database dipilih user untuk Milestone 1.5 (Tarik Session Memory) - Supabase,
project yang sama dengan rencana dashboard observability publik Milestone
5.x/6.x (lihat milestones/1.5-tarik-session-memory/decisions.md Keputusan 1).
Diakses lewat SQLModel (Keputusan 2) - engine SQLAlchemy standar, connection
string Postgres apa pun (termasuk Supabase) bekerja transparan.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import Engine
from sqlmodel import create_engine

load_dotenv()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL tidak diset. Salin .env.example ke .env dan isi "
            "connection string Postgres project Supabase (Project Settings > "
            "Database > Connection string)."
        )
    # SQLAlchemy default dialect utk skema "postgresql://"/"postgres://" adalah
    # psycopg2 (tidak diinstal - proyek ini pakai psycopg3, lihat Keputusan 2
    # decisions.md M1.5). Paksa dialect psycopg3 secara eksplisit.
    for prefix in ("postgresql://", "postgres://"):
        if database_url.startswith(prefix):
            database_url = "postgresql+psycopg://" + database_url[len(prefix) :]
            break
    return create_engine(database_url)
