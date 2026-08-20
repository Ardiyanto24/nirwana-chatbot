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

`TraceRow`/`SpanRow` (Milestone 5.2) genuinely MEMBUAT tabel yang sebelumnya
cuma "dipesan secara konsep" di atas - field PERSIS kontrak Bagian 4
rancangan-observability-ai-chatbot.md, tidak boleh didesain ulang di sini.
Dikonsumsi PIC 5 (Next.js `dashboard/`, repo terpisah) via connection Node
read-only TERPISAH dari DATABASE_URL Python (least-privilege, lihat
milestones/5.2-skema-data-koneksi-nextjs-supabase/decisions.md Keputusan 9)
- kedua model ini sendiri TETAP didefinisikan di sini (Python) karena PIC 6
(custom exporter Go) belum ada, dan M5.2 perlu SQLModel.metadata.create_all()
untuk membuat tabelnya pertama kali (lihat seed_sample_trace.py).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
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


class EmployeeRow(SQLModel, table=True):
    """Salinan direktori karyawan (Milestone 2.4) - HANYA dipakai sebagai
    fixture test yang realistis untuk Verification Gate (employee_id/
    role_title/property_id nyata, bukan karangan). Logic produksi
    verifikasi_gate() TIDAK PERNAH query tabel ini - employee_id caller
    sudah tersedia sejak TurnPayload (M1.2). Diseed dari
    employees_deduped.csv, lihat milestones/2.4-verification-gate/
    decisions.md Keputusan 2 dan 8.

    hire_date disimpan str polos (bukan tipe date) - satu baris CSV
    sumber berformat DD/MM/YYYY sementara baris lain YYYY-MM-DD, field
    ini tidak dipakai logic apa pun sehingga normalisasi paksa tidak
    sepadan (Keputusan 8)."""

    __tablename__ = "employees"

    id: int | None = Field(default=None, primary_key=True)
    employee_id: str = Field(unique=True, index=True)
    property_id: str
    property_name: str
    full_name: str
    role_title: str = Field(index=True)
    department: str
    access_level: str
    hire_date: str
    status: str


class PromptEvalRunRow(SQLModel, table=True):
    """Hasil reliability testing (Promptfoo) per skenario - Manajemen Prompt
    Fase 2, append-only, payload penuh. Disimpan di Supabase (bukan git)
    supaya repo tidak membengkak seiring iterasi prompt berkelanjutan yang
    berjalan terus-menerus (beda dari evals/ yang sekali per milestone).
    Lihat rancangan-manajemen-prompt.md Bagian 6."""

    __tablename__ = "prompt_eval_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prompt_id: str = Field(index=True)
    prompt_version: int
    git_commit_hash: str
    scenario_id: str
    input_payload: dict = Field(sa_column=Column(JSON))
    output_payload: dict = Field(sa_column=Column(JSON))
    verdict: str
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationTurnRow(SQLModel, table=True):
    """Riwayat percakapan per turn (Milestone 7.18) - untuk kebutuhan
    APLIKASI (frontend menampilkan riwayat sesi, analitik/audit masa
    depan), BUKAN kebutuhan internal AI seperti Session Memory
    (SessionMemoryPackageRow, granular per atomic-intent). Satu baris =
    satu turn selesai diproses. Mirror bentuk PromptEvalRunRow (UUID PK
    + created_at), BUKAN SessionMemoryPackageRow (int PK sintetis tanpa
    timestamp) - lihat milestones/7.18-database-percakapan/decisions.md
    Keputusan 3.

    `narasi` = TurnResponse.narasi (versi yang user GENUINELY terima,
    termasuk kalau sudah diganti pesan generik saat terverifikasi=False,
    M7.17) - BUKAN HasilNarasi.narasi mentah. `status` = hasil
    tentukan_status_keseluruhan_turn() (src/orchestration/
    riwayat_percakapan.py) - nilai StatusEksekusi kalau seluruh item
    paket_narasi seragam, atau "campuran" kalau tidak (lihat Keputusan
    2 di file yang sama)."""

    __tablename__ = "conversation_turns"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: str = Field(index=True)
    turn_index: int
    pertanyaan: str
    narasi: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TraceRow(SQLModel, table=True):
    """Satu baris per trace (= satu turn user) - Milestone 5.2. Skema PERSIS
    kontrak Bagian 4 rancangan-observability-ai-chatbot.md, dikonsumsi
    dashboard publik Next.js (repo terpisah `dashboard/`) via koneksi
    read-only. `status` mengikuti taksonomi StatusEksekusi project
    (berhasil/sebagian/ditolak_otorisasi/gagal_teknis/terblokir_ketergantungan)
    tapi disimpan str polos (bukan Enum native Postgres), konsisten pola
    SessionMemoryPackageRow. `role_title` untuk analisis distribusi, BUKAN
    identitas personal - lihat decisions.md M5.2."""

    __tablename__ = "traces"

    trace_id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    turn_index: int
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    ended_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    status: str | None = None
    role_title: str | None = None


class SpanRow(SQLModel, table=True):
    """Satu baris per span (banyak per trace) - Milestone 5.2. Skema PERSIS
    kontrak Bagian 4 rancangan-observability-ai-chatbot.md. `parent_span_id`
    null untuk span akar (`invoke_agent`, M7.6-7.16) - dashboard Next.js
    membangun tree hierarkis dari kolom ini (decisions.md M5.2 Keputusan 6).
    Index eksplisit pada `trace_id` (Postgres tidak otomatis mengindeks
    kolom FK di sisi child, decisions.md M5.2 Keputusan 5)."""

    __tablename__ = "spans"

    span_id: str = Field(primary_key=True)
    trace_id: str = Field(foreign_key="traces.trace_id", index=True)
    parent_span_id: str | None = Field(default=None, foreign_key="spans.span_id", index=True)
    layer_name: str
    operation_name: str | None = None
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    ended_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    duration_ms: int | None = None
    error_type: str | None = None
    attributes: dict = Field(default_factory=dict, sa_column=Column(JSONB))
