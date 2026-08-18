"""Test orkestrator Interpretation (Milestone 7.5) -
src/layers/interpretation/interpretation.py. Checkpoint 2: unit test dasar
(mocked, tanpa LLM sungguhan) untuk wiring. Checkpoint 3: test connectivity
Kriteria Keberhasilan sumber (LLM sungguhan) - lihat bagian bawah file.
"""

import uuid

import src.layers.interpretation.interpretation as interpretation_module
from src.layers.interpretation.interpretation import susun_dan_verifikasi_narasi
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.interpretation import DataVisualisasi, HasilNarasi, HasilVerifikasiNarasi
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage, StatusEksekusi


def _buat_atomic_intent(teks: str = "okupansi Bali bulan lalu") -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
    )


def _buat_paket(atomic_intent_id: str) -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=atomic_intent_id,
        session_id="s1",
        turn_index=1,
        teks_kebutuhan="teks",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"rows": [{"nilai": 1}]},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


# --- Checkpoint 2: unit test dasar (mocked, tanpa LLM sungguhan) --------


def test_narasi_diteruskan_identik_ke_verifikasi(monkeypatch):
    """susun_narasi() sukses -> verifikasi_dan_susun_visualisasi() dipanggil
    dengan `hasil_narasi.narasi` (string PERSIS sama, bukan rekonstruksi)
    sebagai argumen pertama."""
    atomic_intent = _buat_atomic_intent()
    paket = _buat_paket(atomic_intent.atomic_intent_id)
    hasil_narasi_sukses = HasilNarasi(narasi="Okupansi Bali bulan lalu 72%.")

    monkeypatch.setattr(
        interpretation_module, "susun_narasi", lambda *a, **kw: hasil_narasi_sukses
    )

    diterima = {}
    hasil_verifikasi_sukses = HasilVerifikasiNarasi(
        narasi=hasil_narasi_sukses.narasi,
        status=StatusEksekusi.BERHASIL,
        lolos=True,
        alasan=None,
    )
    visualisasi_sukses = [
        DataVisualisasi(
            atomic_intent_id=atomic_intent.atomic_intent_id,
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            nilai_tunggal=72,
        )
    ]

    def _rekam_verifikasi(narasi, atomic_intents, packages, session_id, turn_index):
        diterima["narasi"] = narasi
        return hasil_verifikasi_sukses, visualisasi_sukses

    monkeypatch.setattr(
        interpretation_module, "verifikasi_dan_susun_visualisasi", _rekam_verifikasi
    )

    hasil_narasi, hasil_verifikasi, visualisasi = susun_dan_verifikasi_narasi(
        [atomic_intent], [paket], "s1", 1
    )

    assert diterima["narasi"] is hasil_narasi_sukses.narasi  # identity, bukan rekonstruksi
    assert hasil_narasi is hasil_narasi_sukses
    assert hasil_verifikasi is hasil_verifikasi_sukses
    assert visualisasi is visualisasi_sukses


def test_visualisasi_none_saat_verifikasi_tidak_lolos(monkeypatch):
    """Konsekuensi wiring: kalau verifikasi_dan_susun_visualisasi()
    mengembalikan visualisasi=None (lolos!=True), tuple akhir juga
    meneruskan None apa adanya - tanpa logic tambahan di orkestrator baru."""
    atomic_intent = _buat_atomic_intent()
    paket = _buat_paket(atomic_intent.atomic_intent_id)
    hasil_narasi_sukses = HasilNarasi(narasi="Klaim yang tidak lolos verifikasi.")

    monkeypatch.setattr(
        interpretation_module, "susun_narasi", lambda *a, **kw: hasil_narasi_sukses
    )

    hasil_verifikasi_gagal = HasilVerifikasiNarasi(
        narasi=hasil_narasi_sukses.narasi,
        status=StatusEksekusi.BERHASIL,
        lolos=False,
        alasan="klaim tidak berdasar",
    )

    monkeypatch.setattr(
        interpretation_module,
        "verifikasi_dan_susun_visualisasi",
        lambda *a, **kw: (hasil_verifikasi_gagal, None),
    )

    hasil_narasi, hasil_verifikasi, visualisasi = susun_dan_verifikasi_narasi(
        [atomic_intent], [paket], "s1", 1
    )

    assert hasil_verifikasi.lolos is False
    assert visualisasi is None
