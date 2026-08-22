"""Test suite VERIFIKASI NYATA Milestone 4.3 Checkpoint 5 - panggilan
database SUNGGUHAN ke Supabase (tidak di-mock), mirror pola
tests/layers/context_resolution/test_session_memory.py (M1.5).

KK1: paket yang disimpan susun_dan_simpan_paket() bisa ditarik kembali
retrieve_session_memory() (M1.5) dan isinya identik.
KK3: skenario nilai_hasil mengandung None di kolom katalog nullable-
bermakna (Checkpoint 3) tersimpan dengan catatan_interpretasi yang tepat.

Teardown eksplisit (mirror _cleanup() M1.5) supaya Supabase tidak kotor
sisa data uji. Di-skip otomatis kalau DATABASE_URL tidak tersedia.
"""

import os
import uuid

import pytest
from sqlmodel import Session, text

from src.config.database import get_engine
from src.layers.context_resolution.session_memory import retrieve_session_memory
from src.layers.execution.penyimpanan_paket import susun_dan_simpan_paket
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL tidak diset - skip test yang butuh koneksi database nyata",
)


def _cleanup(session_id: str) -> None:
    with Session(get_engine()) as session:
        session.exec(
            text(
                "DELETE FROM session_memory_packages WHERE session_id = :sid"
            ).bindparams(sid=session_id)
        )
        session.commit()


def _buat_atomic_intent(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def test_kk1_round_trip_identik():
    session_id = "test-m43-kk1"
    ai = _buat_atomic_intent("berapa tiket maintenance bulan ini")
    nilai_hasil = [{"ticket_id": "T1", "property_id": "P01", "room_id": "R101"}]

    try:
        disimpan = susun_dan_simpan_paket(
            ai,
            session_id,
            turn_index=1,
            status=StatusEksekusi.BERHASIL,
            view_name="v_lookup_maintenance_tickets",
            nilai_hasil=nilai_hasil,
        )

        hasil = retrieve_session_memory(session_id, 1)

        assert len(hasil) == 1
        assert hasil[0] == disimpan
    finally:
        _cleanup(session_id)


def test_kk3_nullable_bermakna_tersimpan_dengan_catatan_tepat():
    session_id = "test-m43-kk3"
    ai = _buat_atomic_intent("tiket maintenance yang kerusakannya di fasilitas umum")
    # room_id None -> fasilitas umum (bukan data hilang), sesuai katalog
    # nullable-bermakna Checkpoint 3.
    nilai_hasil = [{"ticket_id": "T2", "property_id": "P01", "room_id": None}]

    try:
        # data_quality_status="ok" (Revisit 2026-08-17) - fokus KK3 murni
        # catatan nullable-bermakna, bukan catatan kualitas data (fitur
        # terpisah, diuji tests/layers/execution/test_penyimpanan_paket.py).
        disimpan = susun_dan_simpan_paket(
            ai,
            session_id,
            turn_index=1,
            status=StatusEksekusi.BERHASIL,
            view_name="v_lookup_maintenance_tickets",
            nilai_hasil=nilai_hasil,
            data_quality_status="ok",
        )

        assert len(disimpan.catatan_interpretasi) == 1
        assert "fasilitas umum" in disimpan.catatan_interpretasi[0]

        hasil = retrieve_session_memory(session_id, 1)
        assert len(hasil) == 1
        assert hasil[0].catatan_interpretasi == disimpan.catatan_interpretasi
        assert hasil[0].nilai_hasil == {"rows": nilai_hasil}
    finally:
        _cleanup(session_id)


def test_kk2_kegagalan_db_nyata_error_type_pada_span_terlihat_di_kode():
    """Skenario DB gagal (kredensial/host salah) TIDAK dijalankan sebagai
    unit test otomatis di sini (akan merusak koneksi Session untuk test
    lain dalam proses yang sama) - sudah dibuktikan lewat mock in-process
    di test_session_memory_kegagalan.py (Checkpoint 2, 2/2 lolos).
    Verifikasi span NYATA di Jaeger (bagian visual KK2) dicatat manual di
    logs.md, bergantung Docker Collector aktif saat Checkpoint 5
    dikerjakan - lihat catatan Risiko & Mitigasi plan M4.3."""
    pytest.skip(
        "Kegagalan DB nyata sengaja tidak disimulasikan otomatis di sini "
        "(berisiko merusak koneksi test lain) - dibuktikan mock Checkpoint 2 "
        "+ verifikasi visual Jaeger manual dicatat di logs.md"
    )
