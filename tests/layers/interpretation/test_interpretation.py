"""Test orkestrator Interpretation (Milestone 7.5) -
src/layers/interpretation/interpretation.py. Checkpoint 2: unit test dasar
(mocked, tanpa LLM sungguhan) untuk wiring. Checkpoint 3: test connectivity
Kriteria Keberhasilan sumber (LLM sungguhan) - lihat bagian bawah file.
"""

import os
import uuid
from unittest.mock import patch

import pytest

import src.layers.interpretation.interpretation as interpretation_module
from src.layers.interpretation.interpretation import susun_dan_verifikasi_narasi
from src.layers.interpretation.narasi import susun_narasi
from src.layers.interpretation.verifikasi_kesetiaan import (
    verifikasi_dan_susun_visualisasi,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.interpretation import (
    DataVisualisasi,
    HasilNarasi,
    HasilVerifikasiNarasi,
)
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)


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

    assert (
        diterima["narasi"] is hasil_narasi_sukses.narasi
    )  # identity, bukan rekonstruksi
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


# --- Checkpoint 3: test connectivity Kriteria Keberhasilan (LLM nyata) --


def _buat_atomic_intent_s01() -> list[AtomicIntent]:
    return [
        AtomicIntent(
            atomic_intent_id="09564b1d-5582-498c-b620-f87a8bbc8a30",
            teks_kebutuhan="Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
        ),
        AtomicIntent(
            atomic_intent_id="f8e76b28-6857-46f2-9a2e-712d938d1697",
            teks_kebutuhan="Revenue F&B April 2026 juga naik 8% dibanding bulan sebelumnya",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            relasi=RelasiKebutuhan.INDEPENDEN,
        ),
    ]


def _buat_paket_s01() -> list[SessionMemoryPackage]:
    return [
        SessionMemoryPackage(
            atomic_intent_id="09564b1d-5582-498c-b620-f87a8bbc8a30",
            session_id="eval-m45",
            turn_index=1,
            teks_kebutuhan="Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            nilai_hasil={"rows": [{"kenaikan_persen": 10}]},
            catatan_interpretasi=[],
            status=StatusEksekusi.BERHASIL,
            sumber="eksekusi_baru",
        ),
        SessionMemoryPackage(
            atomic_intent_id="f8e76b28-6857-46f2-9a2e-712d938d1697",
            session_id="eval-m45",
            turn_index=1,
            teks_kebutuhan="Revenue F&B April 2026 juga naik 8% dibanding bulan sebelumnya",
            label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
            nilai_hasil={"rows": [{"kenaikan_persen": 8}]},
            catatan_interpretasi=[],
            status=StatusEksekusi.BERHASIL,
            sumber="eksekusi_baru",
        ),
    ]


# Klaim kausal S01 (evals/4.5-verifikasi-kesetiaan-dan-visualisasi/payloads/S01.json)
_NARASI_KLAIM_KAUSAL_S01 = (
    "Occupancy rate April 2026 naik 10% dibanding bulan sebelumnya. "
    "Kenaikan ini MENYEBABKAN revenue F&B juga naik 8% pada periode yang sama."
)


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)
def test_konektivitas_jalur_normal_narasi_verifikasi_nyata():
    """Milestone 7.5: jalur bahagia sepenuhnya nyata - TANPA mock sama
    sekali, LLM sungguhan untuk kedua langkah, spy identity check di
    boundary Susun->Verifikasi, membuktikan wiring dasar bekerja end-to-
    end (beda dari test_konektivitas_klaim_sebab_akibat di bawah, yang
    forced memaksa langkah 1 - lihat decisions.md Keputusan 7)."""
    atomic_intent = _buat_atomic_intent("okupansi Bali bulan lalu 72%, naik dari 65%")
    paket = _buat_paket(atomic_intent.atomic_intent_id)

    narasi_returns = []

    def _rekam_susun(*args, **kwargs):
        hasil = susun_narasi(*args, **kwargs)
        narasi_returns.append(hasil)
        return hasil

    with (
        patch(
            "src.layers.interpretation.interpretation.susun_narasi",
            side_effect=_rekam_susun,
        ),
        patch(
            "src.layers.interpretation.interpretation.verifikasi_dan_susun_visualisasi",
            wraps=verifikasi_dan_susun_visualisasi,
        ) as spy_verifikasi,
    ):
        hasil_narasi, hasil_verifikasi, visualisasi = susun_dan_verifikasi_narasi(
            [atomic_intent], [paket], "s1", 1
        )

    assert hasil_narasi is narasi_returns[0]
    # Boundary: narasi yang diterima verifikasi harus string PERSIS dari susun() nyata.
    assert spy_verifikasi.call_args_list[0].args[0] is narasi_returns[0].narasi
    assert hasil_verifikasi.status == StatusEksekusi.BERHASIL


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)
def test_konektivitas_klaim_sebab_akibat_tertangkap_verifikasi_nyata():
    """Milestone 7.5: reuse skenario S01 Milestone 4.5 (klaim sebab-akibat
    tidak berdasar). Rule 5 prompt narasi.md secara eksplisit melarang LLM
    susun_narasi() mengarang klaim ini secara alami - susun_narasi() di-
    mock (return_value deterministik berisi teks S01) HANYA untuk langkah
    Susun (decisions.md Keputusan 7, dipilih user). verifikasi_dan_susun_
    visualisasi() TETAP panggilan LLM sungguhan, TIDAK dimock sama sekali -
    membuktikan verifikasi menangkap klaim kausal mengalir dari narasi
    (via susun_dan_verifikasi_narasi()) secara nyata."""
    atomic_intents = _buat_atomic_intent_s01()
    packages = _buat_paket_s01()
    narasi_dipaksa = HasilNarasi(narasi=_NARASI_KLAIM_KAUSAL_S01)

    with patch(
        "src.layers.interpretation.interpretation.susun_narasi",
        return_value=narasi_dipaksa,
    ):
        hasil_narasi, hasil_verifikasi, visualisasi = susun_dan_verifikasi_narasi(
            atomic_intents, packages, "eval-m45", 1
        )

    assert hasil_narasi is narasi_dipaksa
    assert hasil_verifikasi.lolos is False
    assert hasil_verifikasi.alasan is not None
    assert ("sebab" in hasil_verifikasi.alasan.lower()) or (
        "kausal" in hasil_verifikasi.alasan.lower()
    )
    assert visualisasi is None  # lolos=False -> visualisasi tidak dijalankan
