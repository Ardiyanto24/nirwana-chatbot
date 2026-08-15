"""Test suite Decomposition (Milestone 1.6) - panggilan LLM NYATA (tidak
di-mock, konsisten prinsip verifikasi proyek), membuktikan kedua Kriteria
Keberhasilan sumber.

Di-skip otomatis kalau `OPENROUTER_API_KEY` tidak tersedia di environment.
"""

import os
import uuid

import pytest

from src.layers.decomposition.decompose import decompose_question
from src.layers.decomposition.verifikasi import verifikasi_pemecahan
from src.schemas.decomposition import AtomicIntent, PemecahanResult, RelasiKebutuhan
from src.schemas.session_memory import LabelBentukJawaban

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


def test_kelompok_a_majemuk_bergantung_relasi_benar():
    question = "Bandingkan revenue reservasi Maret 2026 dengan Februari 2026."
    result = decompose_question(question)

    assert len(result.atomic_intents) > 1

    dependent_intents = [
        ai for ai in result.atomic_intents if ai.relasi == RelasiKebutuhan.BERGANTUNG
    ]
    assert len(dependent_intents) >= 1, "harus ada minimal 1 kebutuhan berelasi bergantung"

    independent_ids = {
        ai.atomic_intent_id
        for ai in result.atomic_intents
        if ai.relasi == RelasiKebutuhan.INDEPENDEN
    }
    for dep in dependent_intents:
        assert dep.bergantung_pada, "kebutuhan bergantung wajib punya bergantung_pada terisi"
        assert set(dep.bergantung_pada).issubset(independent_ids), (
            "relasi bergantung harus merujuk ke kebutuhan independen yang benar-benar ada"
        )


def test_kelompok_b_verifikasi_menangkap_pemecahan_keliru():
    question = "Bandingkan revenue reservasi Maret 2026 dengan Februari 2026."
    # Pemecahan sengaja dibuat keliru: kebutuhan perbandingan dihilangkan
    # sama sekali, hanya menyisakan dua nilai independen - tidak ada yang
    # benar-benar menjawab "bandingkan". Dipanggil LANGSUNG ke
    # verifikasi_pemecahan(), tanpa lewat pecah_atomik() asli (skenario
    # terkontrol sesuai Kriteria Keberhasilan sumber).
    hasil_keliru = PemecahanResult(
        atomic_intents=[
            AtomicIntent(
                atomic_intent_id=str(uuid.uuid4()),
                teks_kebutuhan="Berapa revenue reservasi Maret 2026?",
                label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
            ),
            AtomicIntent(
                atomic_intent_id=str(uuid.uuid4()),
                teks_kebutuhan="Berapa revenue reservasi Februari 2026?",
                label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
                relasi=RelasiKebutuhan.INDEPENDEN,
            ),
        ]
    )

    verifikasi = verifikasi_pemecahan(question, hasil_keliru)

    assert verifikasi.valid is False
    assert verifikasi.alasan, "verifikasi invalid wajib menyertakan alasan spesifik"
