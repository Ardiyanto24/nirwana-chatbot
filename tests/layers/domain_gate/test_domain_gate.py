"""Test suite Orkestrator Identifikasi Domain (Milestone 2.1).

Satu test deterministik (filter PERLU_EKSEKUSI, NOL panggilan LLM kalau
semua entri SELESAI) + dua test panggilan LLM nyata (union domain benar,
filter campuran SELESAI/PERLU_EKSEKUSI). Konsisten pola test_matching.py
M1.7 yang juga py jalur pintas deterministik teruji tanpa LLM.

Catatan kejujuran verifikasi: cabang status GAGAL_TEKNIS/SEBAGIAN di
identifikasi_domain_atomic_intent() (Checkpoint 7) TIDAK diuji lewat
kegagalan API yang dipaksa - project tidak mock panggilan LLM sama sekali
(lihat test_identifikasi.py/test_verifikasi_titik_buta.py), dan kegagalan
API nyata tidak bisa dipicu deterministik on-demand. Cabang ini divalidasi
lewat review kode (pemetaan if/else 2 kondisi boolean langsung dari
`gagal` yang SUDAH teruji di level identifikasi.py/verifikasi_titik_buta.py
pure-function test) - bukan diklaim teruji end-to-end.
"""

import os
import uuid
from unittest.mock import patch

import pytest

from src.layers.domain_gate.domain_gate import (
    identifikasi_domain_atomic_intent,
    identifikasi_domain_semua,
)
from src.layers.domain_gate.identifikasi import identifikasi_domain
from src.layers.domain_gate.verifikasi_titik_buta import verifikasi_titik_buta
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.matching import AtomicIntentMatch, MatchStatus
from src.schemas.session_memory import (
    LabelBentukJawaban,
    SessionMemoryPackage,
    StatusEksekusi,
)


def _buat_atomic_intent(teks: str) -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )


def _buat_paket_selesai() -> SessionMemoryPackage:
    return SessionMemoryPackage(
        atomic_intent_id=str(uuid.uuid4()),
        session_id="test-session",
        turn_index=1,
        teks_kebutuhan="Berapa okupansi bulan lalu?",
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        nilai_hasil={"okupansi": 80},
        catatan_interpretasi=[],
        status=StatusEksekusi.BERHASIL,
        sumber="eksekusi_baru",
    )


# --- Deterministik, TANPA LLM -------------------------------------------------


def test_filter_perlu_eksekusi_kosong_kalau_semua_selesai():
    """Kalau seluruh AtomicIntentMatch berstatus SELESAI, hasil harus list
    kosong TANPA satu pun panggilan LLM (deterministik, tidak butuh
    OPENROUTER_API_KEY)."""
    match_selesai = AtomicIntentMatch(
        atomic_intent=_buat_atomic_intent("Berapa okupansi bulan lalu?"),
        status=MatchStatus.SELESAI,
        paket=_buat_paket_selesai(),
    )
    hasil = identifikasi_domain_semua([match_selesai])
    assert hasil == []


# --- Panggilan LLM nyata -----------------------------------------------------

pytestmark_llm = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY tidak diset - skip test yang butuh panggilan LLM nyata",
)


@pytestmark_llm
def test_kelompok_a_union_domain_berhasil():
    atomic_intent = _buat_atomic_intent(
        "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"
    )
    result = identifikasi_domain_atomic_intent(atomic_intent)
    assert result.status == StatusEksekusi.BERHASIL
    assert Domain.RESERVATION in result.domains
    assert Domain.FINANCIAL in result.domains
    # Union tidak boleh py duplikat.
    assert len(result.domains) == len(set(result.domains))


@pytestmark_llm
def test_kelompok_b_filter_campuran_selesai_dan_perlu_eksekusi():
    match_selesai = AtomicIntentMatch(
        atomic_intent=_buat_atomic_intent("Berapa okupansi bulan lalu?"),
        status=MatchStatus.SELESAI,
        paket=_buat_paket_selesai(),
    )
    match_perlu_eksekusi = AtomicIntentMatch(
        atomic_intent=_buat_atomic_intent("Berapa nationality mix tamu bulan ini?"),
        status=MatchStatus.PERLU_EKSEKUSI,
        paket=None,
    )
    hasil = identifikasi_domain_semua([match_selesai, match_perlu_eksekusi])
    assert len(hasil) == 1
    assert hasil[0].status == StatusEksekusi.BERHASIL
    assert Domain.GUESTS_PROFILE in hasil[0].domains


@pytestmark_llm
def test_konektivitas_identifikasi_verifikasi_titik_buta_skenario_gop_margin():
    """Milestone 7.3: buktikan hand-off NILAI PERSIS di titik sambung
    Identifikasi->Verifikasi Titik Buta - beda dari test_kelompok_a di atas
    yang hanya membuktikan hasil akhir union benar (RESERVATION+FINANCIAL
    ada), bukan argumen spesifik yang diterima verifikasi_titik_buta().
    Skenario gop_margin dipakai persis sama dengan test_kelompok_a (KK
    sumber M7.3 eksplisit merujuk skenario ini) - metrik turunan finansial
    yang berpotensi tidak tertangkap identifikasi domain awal, memicu
    Verifikasi Titik Buta menambahkan domain FINANCIAL yang terlewat.
    Spy (side_effect) merekam objek return identifikasi_domain() SAMBIL
    tetap memanggil LLM sungguhan, lalu memeriksa objek itu PERSIS (identity,
    bukan cuma equality) yang diterima verifikasi_titik_buta() sebagai
    domain_awal - membuktikan tidak ada rekonstruksi manual di antara
    kedua langkah."""
    atomic_intent = _buat_atomic_intent(
        "Bagaimana gop_margin properti Bali dipengaruhi deviasi harga bulan ini?"
    )

    identifikasi_returns = []

    def _rekam_identifikasi(*args, **kwargs):
        hasil = identifikasi_domain(*args, **kwargs)
        identifikasi_returns.append(hasil)
        return hasil

    with (
        patch(
            "src.layers.domain_gate.domain_gate.identifikasi_domain",
            side_effect=_rekam_identifikasi,
        ),
        patch(
            "src.layers.domain_gate.domain_gate.verifikasi_titik_buta",
            wraps=verifikasi_titik_buta,
        ) as spy_verifikasi,
    ):
        result = identifikasi_domain_atomic_intent(atomic_intent)

    # Boundary: argumen `domain_awal` yang diterima verifikasi_titik_buta()
    # harus list PERSIS (identity) yang dikembalikan identifikasi_domain().domains,
    # bukan rekonstruksi/salinan baru.
    hasil_identifikasi = identifikasi_returns[0]
    verifikasi_call_args = spy_verifikasi.call_args_list[0]
    assert verifikasi_call_args.args[1] is hasil_identifikasi.domains

    # Sanity: union akhir tetap mencakup domain yang genuinely bocor lewat
    # kolom turunan (sesuai KK sumber M7.3).
    assert result.status == StatusEksekusi.BERHASIL
    assert Domain.RESERVATION in result.domains
    assert Domain.FINANCIAL in result.domains
