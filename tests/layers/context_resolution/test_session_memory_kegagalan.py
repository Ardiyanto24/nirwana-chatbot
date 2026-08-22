"""Test suite skenario kegagalan `store_session_memory()` (Milestone 4.3
Checkpoint 2) dan `retrieve_session_memory()` (Milestone 1.5, addendum
ditemukan+diperbaiki Milestone 7.7 2026-08-18) - span `memory.store`/
`memory.retrieve` harus mencatat `error.type=gagal_teknis` saat DB gagal,
LALU exception tetap di-raise ulang (bukan ditelan).

Murni mocked (Session/get_engine di-monkeypatch) - SENGAJA dipisah dari
test_session_memory.py (yang di-skip otomatis tanpa `DATABASE_URL`) supaya
test ini tetap jalan tanpa koneksi database nyata.

Lihat milestones/1.5-tarik-session-memory/decisions.md Addendum dan
milestones/7.7-sambungan-percabangan-paralel-rewrite-tarik-memory/
decisions.md Keputusan 6.
"""

import uuid

import pytest

from src.layers.context_resolution import session_memory as modul
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)


def _buat_package() -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=str(uuid.uuid4()),
        session_id="test-kegagalan",
        turn_index=1,
        teks_kebutuhan="okupansi Bali bulan lalu",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": []},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


class _SpanRekam:
    def __init__(self):
        self.atribut: dict = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, key, value):
        self.atribut[key] = value


class _TracerRekam:
    def __init__(self):
        self.span = _SpanRekam()

    def start_as_current_span(self, nama):
        return self.span


class _SessionGagal:
    """Mirror context manager sqlmodel.Session, tapi commit() selalu
    melempar exception - simulasi DB tidak terjangkau."""

    def __init__(self, engine):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def add(self, row):
        pass

    def commit(self):
        raise RuntimeError("simulasi DB tidak terjangkau")


def test_kegagalan_db_menghasilkan_error_type_lalu_raise_ulang(monkeypatch):
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)
    monkeypatch.setattr(modul, "Session", _SessionGagal)
    monkeypatch.setattr(modul, "get_engine", lambda: None)

    with pytest.raises(RuntimeError, match="simulasi DB tidak terjangkau"):
        modul.store_session_memory(_buat_package())

    assert tracer_rekam.span.atribut["error.type"] == "gagal_teknis"


def test_kegagalan_db_atribut_session_turn_atomic_intent_tetap_tercatat(monkeypatch):
    """Atribut identitas span harus tercatat SEBELUM percobaan commit
    gagal - supaya trace tetap bisa dikorelasikan ke atomic intent mana
    yang gagal disimpan, meski operasinya sendiri gagal."""
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)
    monkeypatch.setattr(modul, "Session", _SessionGagal)
    monkeypatch.setattr(modul, "get_engine", lambda: None)

    package = _buat_package()
    with pytest.raises(RuntimeError):
        modul.store_session_memory(package)

    assert tracer_rekam.span.atribut["session.id"] == package.session_id
    assert tracer_rekam.span.atribut["turn.index"] == package.turn_index
    assert tracer_rekam.span.atribut["atomic_intent_id"] == package.atomic_intent_id


class _SessionExecGagal:
    """Mirror _SessionGagal, tapi exec() (dipakai retrieve, bukan
    commit()/add() yang dipakai store) yang melempar exception - simulasi
    DB tidak terjangkau saat query SELECT."""

    def __init__(self, engine):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def exec(self, statement):
        raise RuntimeError("simulasi DB tidak terjangkau")


def test_kegagalan_db_saat_retrieve_menghasilkan_error_type_lalu_raise_ulang(
    monkeypatch,
):
    """Addendum Milestone 7.7: retrieve_session_memory() sebelumnya TIDAK
    punya try/except sama sekali di sekitar query DB - diperbaiki mirror
    persis pola store_session_memory() di atas."""
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)
    monkeypatch.setattr(modul, "Session", _SessionExecGagal)
    monkeypatch.setattr(modul, "get_engine", lambda: None)

    with pytest.raises(RuntimeError, match="simulasi DB tidak terjangkau"):
        modul.retrieve_session_memory("test-kegagalan", 1)

    assert tracer_rekam.span.atribut["error.type"] == "gagal_teknis"
    assert tracer_rekam.span.atribut["session.id"] == "test-kegagalan"
    assert tracer_rekam.span.atribut["turn.index"] == 1
