"""Test suite skenario kegagalan `simpan_riwayat_turn()` (Milestone
7.18) - span `riwayat.simpan` harus mencatat `error.type=gagal_teknis`
saat DB gagal, LALU exception tetap di-raise ulang (mirror persis
`store_session_memory()`, lihat decisions.md Keputusan 4). Juga
mencakup test MURNI `tentukan_status_keseluruhan_turn()` (tanpa I/O,
tanpa DB sama sekali) - SENGAJA di file ini (bukan
test_riwayat_percakapan.py) supaya tidak ikut ter-skip tanpa
`DATABASE_URL`.

Murni mocked (Session/get_engine di-monkeypatch) - SENGAJA dipisah dari
test_riwayat_percakapan.py (yang di-skip otomatis tanpa `DATABASE_URL`)
supaya test ini tetap jalan tanpa koneksi database nyata.
"""

import uuid

import pytest

from src.orchestration import riwayat_percakapan as modul
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)


def _buat_paket(status: StatusEksekusi) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=str(uuid.uuid4()),
        session_id="test-kegagalan",
        turn_index=1,
        teks_kebutuhan="kebutuhan contoh",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": []},
        catatan_interpretasi=[],
        status=status,
        sumber="eksekusi_baru",
    )


# --- tentukan_status_keseluruhan_turn() (murni, tanpa DB) ---


def test_status_seragam_berhasil_menghasilkan_berhasil():
    paket_narasi = [
        _buat_paket(StatusEksekusi.BERHASIL),
        _buat_paket(StatusEksekusi.BERHASIL),
    ]
    assert modul.tentukan_status_keseluruhan_turn(paket_narasi) == "berhasil"


def test_status_seragam_gagal_teknis_menghasilkan_gagal_teknis():
    paket_narasi = [_buat_paket(StatusEksekusi.GAGAL_TEKNIS)]
    assert modul.tentukan_status_keseluruhan_turn(paket_narasi) == "gagal_teknis"


def test_status_campuran_menghasilkan_campuran():
    paket_narasi = [
        _buat_paket(StatusEksekusi.BERHASIL),
        _buat_paket(StatusEksekusi.GAGAL_TEKNIS),
    ]
    assert modul.tentukan_status_keseluruhan_turn(paket_narasi) == "campuran"


def test_status_campuran_tidak_tertukar_dengan_sebagian_existing():
    # "campuran" (status berbeda antar item) HARUS beda dari nilai
    # StatusEksekusi.SEBAGIAN existing (artinya "data basi" satu item),
    # meski salah satu item kebetulan SEBAGIAN.
    paket_narasi = [
        _buat_paket(StatusEksekusi.SEBAGIAN),
        _buat_paket(StatusEksekusi.BERHASIL),
    ]
    hasil = modul.tentukan_status_keseluruhan_turn(paket_narasi)
    assert hasil == "campuran"
    assert hasil != StatusEksekusi.SEBAGIAN.value


def test_status_list_kosong_menghasilkan_tidak_ada_kebutuhan():
    assert modul.tentukan_status_keseluruhan_turn([]) == "tidak_ada_kebutuhan"


# --- simpan_riwayat_turn() kegagalan DB ---


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
        modul.simpan_riwayat_turn(
            session_id="test-kegagalan",
            turn_index=1,
            pertanyaan="pertanyaan contoh",
            narasi="narasi contoh",
            status="berhasil",
        )

    assert tracer_rekam.span.atribut["error.type"] == "gagal_teknis"


def test_kegagalan_db_atribut_session_turn_status_tetap_tercatat(monkeypatch):
    """Atribut identitas span harus tercatat SEBELUM percobaan commit
    gagal - supaya trace tetap bisa dikorelasikan meski operasinya
    sendiri gagal (mirror pola session_memory.py)."""
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)
    monkeypatch.setattr(modul, "Session", _SessionGagal)
    monkeypatch.setattr(modul, "get_engine", lambda: None)

    with pytest.raises(RuntimeError):
        modul.simpan_riwayat_turn(
            session_id="test-kegagalan",
            turn_index=3,
            pertanyaan="pertanyaan contoh",
            narasi="narasi contoh",
            status="campuran",
        )

    assert tracer_rekam.span.atribut["session.id"] == "test-kegagalan"
    assert tracer_rekam.span.atribut["turn.index"] == 3
    assert tracer_rekam.span.atribut["riwayat.status"] == "campuran"
