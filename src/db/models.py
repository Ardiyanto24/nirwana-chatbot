"""Tabel SQLModel (persistence, table=True) - Milestone 1.5.

Dipisah dari src/schemas/session_memory.py (bentuk publik Pydantic murni)
supaya row DB tidak bocor sebagai objek ORM ke business logic. Lihat
decisions.md Keputusan 8.

Nama tabel (`session_memory_packages`, `roles`, `role_permissions`) sengaja
tidak bertabrakan dengan `traces`/`spans` yang sudah "dipesan" untuk skema
observability Milestone 5.x/6.x di project Supabase yang sama (Keputusan 1
dan 5). `role_permissions` (Milestone 2.2) adalah salinan Lapis-1 milik
proyek ini sendiri - BUKAN tabel produksi `mart_cleaned.role_permissions`,
lihat docstring `RolePermissionRow`.
"""

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class SessionMemoryPackageRow(SQLModel, table=True):
    __tablename__ = "session_memory_packages"

    # Primary key sintetik (auto-increment), BUKAN atomic_intent_id - Milestone
    # 1.7 nanti akan menyimpan ULANG paket yang sama (atomic_intent_id sama)
    # sebagai baris arsip baru di bawah turn yang berjalan (lihat Lingkup M1.7
    # rancangan-context-decomposition.md), jadi atomic_intent_id BUKAN unik
    # per baris.
    id: int | None = Field(default=None, primary_key=True)

    atomic_intent_id: str = Field(index=True)
    session_id: str = Field(index=True)
    turn_index: int = Field(index=True)
    teks_kebutuhan: str
    # label_bentuk_jawaban/status disimpan str polos (BUKAN kolom Enum native
    # Postgres) - SQLAlchemy Enum native default menyimpan .name member Python
    # ("NILAI_TUNGGAL"), bukan .value ("nilai_tunggal") yang dikunci arsitektur
    # SS7, kecuali dikonfigurasi values_callable eksplisit. Str polos + validasi
    # Enum di src/schemas/session_memory.py (Pydantic) lebih sederhana - tidak
    # perlu kelola tipe ENUM native Postgres tanpa Alembic (Keputusan 8).
    label_bentuk_jawaban: str
    nilai_hasil: dict = Field(sa_column=Column(JSON))
    catatan_interpretasi: list[str] = Field(sa_column=Column(JSON))
    status: str
    sumber: str


class RoleRow(SQLModel, table=True):
    __tablename__ = "roles"

    id: int | None = Field(default=None, primary_key=True)
    role_title: str = Field(unique=True, index=True)


class RolePermissionRow(SQLModel, table=True):
    """Salinan Lapis-1 (Milestone 2.2) atas matriks otorisasi 20 role x 10
    domain, di project Supabase milik proyek ini SENDIRI - BUKAN tabel
    `mart_cleaned.role_permissions` produksi (beda database, beda kredensial,
    beda tujuan; kredensial `chatbot_authz_reader` untuk tabel produksi itu
    eksklusif milik Milestone 4.4/Lapis 2). Satu baris = satu izin
    (role_title, domain) yang granted; ketiadaan baris = ditolak. Lihat
    decisions.md M2.2 Keputusan 1 dan 10."""

    __tablename__ = "role_permissions"

    id: int | None = Field(default=None, primary_key=True)
    role_title: str = Field(index=True)
    domain: str = Field(index=True)
