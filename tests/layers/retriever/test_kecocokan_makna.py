"""Test suite orkestrator Kecocokan Makna (Milestone 3.2) -
src/layers/retriever/kecocokan_makna.py. Nama file dipisah dari
test_kecocokan_makna_schema.py (Checkpoint 3, test skema) - mirror
preseden test_retriever.py vs test_retriever_schema.py (M3.1).

Dibangun bertahap lintas checkpoint (preseden pola M2.2/M2.3):
- Checkpoint 7 (Task 12): Langkah 1 (generate) - pure-function _parse_generate
  + mocked _langkah_generate (get_openrouter_client di-monkeypatch, TANPA
  network call nyata - mirror test_pencarian_embedding.py M3.1).
- Checkpoint 8 (Task 14): Langkah 2 (verifikasi) - ditambahkan nanti.
- Checkpoint 9 (Task 16): nilai_kecocokan_makna_atomic_intent - ditambahkan nanti.
- Checkpoint 10 (Task 18): nilai_kecocokan_makna_semua - ditambahkan nanti.
"""

import json
import uuid

from openai import APIError

import src.layers.retriever.kecocokan_makna as kecocokan_makna_module
from src.layers.retriever.kecocokan_makna import (
    _langkah_generate,
    _langkah_verifikasi,
    _parse_generate,
    _parse_verifikasi,
    nilai_kecocokan_makna_atomic_intent,
)
from src.schemas.decomposition import AtomicIntent, RelasiKebutuhan
from src.schemas.domain_gate import Domain
from src.schemas.retriever import (
    HasilPencarianKandidat,
    KandidatView,
    KecocokanKandidat,
    LabelKecocokanMakna,
    SumberPencarian,
)
from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


def _buat_atomic_intent(teks: str = "okupansi per tipe kamar Bali bulan ini") -> AtomicIntent:
    return AtomicIntent(
        atomic_intent_id=str(uuid.uuid4()),
        teks_kebutuhan=teks,
        label_bentuk_jawaban=LabelBentukJawaban.NILAI_TUNGGAL,
        relasi=RelasiKebutuhan.INDEPENDEN,
        bergantung_pada=None,
    )


def _buat_kandidat(view_name: str, domain: Domain = Domain.RESERVATION) -> KandidatView:
    return KandidatView(view_name=view_name, domain=domain, skor=5.0, sumber=SumberPencarian.BM25)


def _buat_kecocokan(
    view_name: str,
    label: LabelKecocokanMakna,
    domain: Domain = Domain.RESERVATION,
    alasan: str = "penilaian awal",
) -> KecocokanKandidat:
    return KecocokanKandidat(kandidat=_buat_kandidat(view_name, domain), label=label, alasan=alasan)


def _buat_hasil_pencarian(kandidat: list[KandidatView]) -> HasilPencarianKandidat:
    return HasilPencarianKandidat(
        atomic_intent=_buat_atomic_intent(),
        domain_diizinkan=[Domain.RESERVATION],
        kandidat=kandidat,
        fallback_terpicu=False,
        status=StatusEksekusi.BERHASIL,
    )


# --- Pure-function: _parse_generate ------------------------------------------


def test_parse_generate_respons_valid_semua_kandidat_tercakup():
    kandidat = [
        _buat_kandidat("v_reservation_room_type_daily"),
        _buat_kandidat("v_reservation_property_daily"),
    ]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "grain per tipe kamar sesuai kebutuhan",
                },
                {
                    "view_name": "v_reservation_property_daily",
                    "label": "sebagian",
                    "alasan": "grain per properti, lebih kasar dari yang diminta",
                },
            ]
        }
    )
    hasil, gagal, alasan = _parse_generate(raw, kandidat)

    assert gagal is False
    assert alasan is None
    assert len(hasil) == 2
    assert hasil[0].label == LabelKecocokanMakna.DITEMUKAN
    assert hasil[1].label == LabelKecocokanMakna.SEBAGIAN


def test_parse_generate_json_rusak_dipaksa_gagal():
    kandidat = [_buat_kandidat("v_reservation_room_type_daily")]
    hasil, gagal, alasan = _parse_generate("bukan json valid", kandidat)

    assert gagal is True
    assert hasil == []
    assert alasan is not None and "parse_error" in alasan


def test_parse_generate_kandidat_hilang_dari_respons_default_aman_bukan_drop():
    """Jaminan struktural Keputusan 9: kandidat yang tidak muncul di respons
    LLM WAJIB tetap ada di keluaran (default SEBAGIAN), bukan hilang diam-diam."""
    kandidat = [
        _buat_kandidat("v_reservation_room_type_daily"),
        _buat_kandidat("v_reservation_property_daily"),
    ]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "cocok",
                }
            ]
        }
    )
    hasil, gagal, alasan = _parse_generate(raw, kandidat)

    assert gagal is False
    assert len(hasil) == 2  # jaminan struktural: tetap 2, bukan 1
    assert hasil[1].kandidat.view_name == "v_reservation_property_daily"
    assert hasil[1].label == LabelKecocokanMakna.SEBAGIAN
    assert "parse_anomaly" in hasil[1].alasan
    assert alasan is not None and "missing:v_reservation_property_daily" in alasan


def test_parse_generate_label_invalid_default_aman():
    kandidat = [_buat_kandidat("v_reservation_room_type_daily")]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "cocok_penuh",  # bukan salah satu 3 nilai valid
                    "alasan": "halusinasi label",
                }
            ]
        }
    )
    hasil, gagal, alasan = _parse_generate(raw, kandidat)

    assert gagal is False
    assert len(hasil) == 1
    assert hasil[0].label == LabelKecocokanMakna.SEBAGIAN
    assert "parse_anomaly" in hasil[0].alasan
    assert alasan is not None and "invalid_label" in alasan


def test_parse_generate_view_name_halusinasi_diabaikan_bukan_ditambahkan():
    """Entri LLM untuk view_name yang TIDAK ada di daftar kandidat asli
    diabaikan (bukan ditambahkan ke keluaran) - iterasi selalu dari daftar
    kandidat ground-truth, bukan dari respons LLM."""
    kandidat = [_buat_kandidat("v_reservation_room_type_daily")]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "cocok",
                },
                {
                    "view_name": "v_view_yang_tidak_ada",
                    "label": "ditemukan",
                    "alasan": "halusinasi",
                },
            ]
        }
    )
    hasil, gagal, alasan = _parse_generate(raw, kandidat)

    assert gagal is False
    assert len(hasil) == 1
    assert hasil[0].kandidat.view_name == "v_reservation_room_type_daily"


# --- _langkah_generate (mocked LLM, TANPA network call nyata) ----------------


class _FakeUsage:
    def __init__(self, prompt_tokens: int = 100, completion_tokens: int = 50):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content: str, choices: list | None = None):
        self.usage = _FakeUsage()
        self.choices = [_FakeChoice(content)] if choices is None else choices


def test_langkah_generate_sukses_normal(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "grain sesuai",
                }
            ]
        }
    )
    monkeypatch.setattr(
        kecocokan_makna_module, "_call_llm_generate", lambda hp: _FakeChatResponse(raw)
    )

    hasil, gagal = _langkah_generate(hasil_pencarian)

    assert gagal is False
    assert len(hasil) == 1
    assert hasil[0].label == LabelKecocokanMakna.DITEMUKAN


def test_langkah_generate_api_error_gagal_true_bukan_exception(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])

    def _raise_api_error(hp):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(kecocokan_makna_module, "_call_llm_generate", _raise_api_error)

    hasil, gagal = _langkah_generate(hasil_pencarian)

    assert gagal is True
    assert hasil == []


def test_langkah_generate_empty_choices_gagal_true(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])

    monkeypatch.setattr(
        kecocokan_makna_module,
        "_call_llm_generate",
        lambda hp: _FakeChatResponse("", choices=[]),
    )

    hasil, gagal = _langkah_generate(hasil_pencarian)

    assert gagal is True
    assert hasil == []


# --- Pure-function: _parse_verifikasi ----------------------------------------


def test_parse_verifikasi_koreksi_ditemukan_ke_sebagian():
    """Koreksi arah 1: Langkah 1 bilang ditemukan, Langkah 2 menurunkan
    ke sebagian (grain-mismatch yang terlewat Langkah 1)."""
    kandidat = [_buat_kandidat("v_reservation_property_daily")]
    hasil_awal = [_buat_kecocokan("v_reservation_property_daily", LabelKecocokanMakna.DITEMUKAN)]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_property_daily",
                    "label": "sebagian",
                    "alasan": "grain per properti, bukan per tipe kamar seperti dibutuhkan",
                }
            ]
        }
    )
    hasil, gagal, alasan = _parse_verifikasi(raw, kandidat, hasil_awal)

    assert gagal is False
    assert hasil[0].label == LabelKecocokanMakna.SEBAGIAN


def test_parse_verifikasi_koreksi_sebagian_ke_ditemukan():
    """Koreksi arah 2: Langkah 1 terlalu ragu (sebagian), Langkah 2
    menaikkan ke ditemukan (cocok penuh, keraguan awal tidak berdasar)."""
    kandidat = [_buat_kandidat("v_reservation_room_type_daily")]
    hasil_awal = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.SEBAGIAN)]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "grain, sumber, dan nama semuanya cocok - tidak ada alasan ragu",
                }
            ]
        }
    )
    hasil, gagal, alasan = _parse_verifikasi(raw, kandidat, hasil_awal)

    assert gagal is False
    assert hasil[0].label == LabelKecocokanMakna.DITEMUKAN


def test_parse_verifikasi_konfirmasi_label_tidak_berubah():
    kandidat = [_buat_kandidat("v_reservation_room_type_daily")]
    hasil_awal = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "sudah benar, dikonfirmasi",
                }
            ]
        }
    )
    hasil, gagal, alasan = _parse_verifikasi(raw, kandidat, hasil_awal)

    assert gagal is False
    assert hasil[0].label == LabelKecocokanMakna.DITEMUKAN


def test_parse_verifikasi_json_rusak_dipaksa_gagal():
    kandidat = [_buat_kandidat("v_reservation_room_type_daily")]
    hasil_awal = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]

    hasil, gagal, alasan = _parse_verifikasi("bukan json valid", kandidat, hasil_awal)

    assert gagal is True
    assert hasil == []
    assert alasan is not None and "parse_error" in alasan


def test_parse_verifikasi_kandidat_hilang_fallback_ke_hasil_awal():
    """Beda dari _parse_generate: kandidat yang hilang dari respons Langkah
    2 fallback ke label Langkah 1 kandidat itu (bukan default SEBAGIAN
    generik) - kita SUDAH punya penilaian nyata untuk itu."""
    kandidat = [
        _buat_kandidat("v_reservation_room_type_daily"),
        _buat_kandidat("v_reservation_property_daily"),
    ]
    hasil_awal = [
        _buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN),
        _buat_kecocokan(
            "v_reservation_property_daily", LabelKecocokanMakna.TIDAK_DITEMUKAN, alasan="grain salah"
        ),
    ]
    raw = json.dumps(
        {
            "penilaian": [
                {
                    "view_name": "v_reservation_room_type_daily",
                    "label": "ditemukan",
                    "alasan": "dikonfirmasi",
                }
            ]
        }
    )
    hasil, gagal, alasan = _parse_verifikasi(raw, kandidat, hasil_awal)

    assert gagal is False
    assert len(hasil) == 2
    assert hasil[1].label == LabelKecocokanMakna.TIDAK_DITEMUKAN
    assert hasil[1].alasan == "grain salah"  # persis alasan Langkah 1, bukan alasan baru
    assert alasan is not None and "missing:v_reservation_property_daily" in alasan


# --- _langkah_verifikasi (mocked LLM, TANPA network call nyata) -------------


def test_langkah_verifikasi_sukses_koreksi_dua_arah(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian(
        [
            _buat_kandidat("v_reservation_room_type_daily"),
            _buat_kandidat("v_reservation_property_daily"),
        ]
    )
    hasil_awal = [
        _buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.SEBAGIAN),
        _buat_kecocokan("v_reservation_property_daily", LabelKecocokanMakna.DITEMUKAN),
    ]
    raw = json.dumps(
        {
            "penilaian": [
                {"view_name": "v_reservation_room_type_daily", "label": "ditemukan", "alasan": "naik"},
                {"view_name": "v_reservation_property_daily", "label": "sebagian", "alasan": "turun"},
            ]
        }
    )
    monkeypatch.setattr(
        kecocokan_makna_module,
        "_call_llm_verifikasi",
        lambda hp, awal: _FakeChatResponse(raw),
    )

    hasil, gagal = _langkah_verifikasi(hasil_pencarian, hasil_awal)

    assert gagal is False
    assert hasil[0].label == LabelKecocokanMakna.DITEMUKAN
    assert hasil[1].label == LabelKecocokanMakna.SEBAGIAN


def test_langkah_verifikasi_api_error_gagal_true(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])
    hasil_awal = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]

    def _raise_api_error(hp, awal):
        raise APIError("simulasi kegagalan API", request=None, body=None)

    monkeypatch.setattr(kecocokan_makna_module, "_call_llm_verifikasi", _raise_api_error)

    hasil, gagal = _langkah_verifikasi(hasil_pencarian, hasil_awal)

    assert gagal is True
    assert hasil == []


# --- nilai_kecocokan_makna_atomic_intent (orkestrator single-item) ---------


def test_orkestrator_kandidat_kosong_nol_panggilan_llm(monkeypatch):
    """Jalur pintas Keputusan 10: HasilPencarianKandidat.kandidat=[] (M3.1
    genuinely tidak menemukan kandidat) -> BERHASIL+kecocokan=[], TANPA
    memanggil LLM sama sekali - dibuktikan monkeypatch raise (pola
    pembuktian pre-filter M2.3), bukan cuma dicek hasil akhirnya."""
    monkeypatch.setattr(
        kecocokan_makna_module,
        "_langkah_generate",
        lambda hp: (_ for _ in ()).throw(
            AssertionError("_langkah_generate TIDAK BOLEH dipanggil untuk kandidat kosong")
        ),
    )
    monkeypatch.setattr(
        kecocokan_makna_module,
        "_langkah_verifikasi",
        lambda hp, awal: (_ for _ in ()).throw(
            AssertionError("_langkah_verifikasi TIDAK BOLEH dipanggil untuk kandidat kosong")
        ),
    )

    hasil_pencarian = _buat_hasil_pencarian([])
    hasil = nilai_kecocokan_makna_atomic_intent(hasil_pencarian)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.kecocokan == []


def test_orkestrator_sukses_penuh_pakai_hasil_langkah_2(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])
    hasil_awal = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.SEBAGIAN)]
    hasil_final = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]

    monkeypatch.setattr(
        kecocokan_makna_module, "_langkah_generate", lambda hp: (hasil_awal, False)
    )
    monkeypatch.setattr(
        kecocokan_makna_module,
        "_langkah_verifikasi",
        lambda hp, awal: (hasil_final, False),
    )

    hasil = nilai_kecocokan_makna_atomic_intent(hasil_pencarian)

    assert hasil.status == StatusEksekusi.BERHASIL
    assert hasil.kecocokan == hasil_final  # hasil Langkah 2, BUKAN Langkah 1


def test_orkestrator_langkah_1_gagal_total_gagal_teknis(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])

    monkeypatch.setattr(kecocokan_makna_module, "_langkah_generate", lambda hp: ([], True))
    monkeypatch.setattr(
        kecocokan_makna_module,
        "_langkah_verifikasi",
        lambda hp, awal: (_ for _ in ()).throw(
            AssertionError("_langkah_verifikasi TIDAK BOLEH dipanggil kalau Langkah 1 gagal total")
        ),
    )

    hasil = nilai_kecocokan_makna_atomic_intent(hasil_pencarian)

    assert hasil.status == StatusEksekusi.GAGAL_TEKNIS
    assert hasil.kecocokan == []


def test_orkestrator_langkah_2_gagal_sebagian_hasil_langkah_1_dipertahankan(monkeypatch):
    hasil_pencarian = _buat_hasil_pencarian([_buat_kandidat("v_reservation_room_type_daily")])
    hasil_awal = [_buat_kecocokan("v_reservation_room_type_daily", LabelKecocokanMakna.DITEMUKAN)]

    monkeypatch.setattr(
        kecocokan_makna_module, "_langkah_generate", lambda hp: (hasil_awal, False)
    )
    monkeypatch.setattr(
        kecocokan_makna_module, "_langkah_verifikasi", lambda hp, awal: ([], True)
    )

    hasil = nilai_kecocokan_makna_atomic_intent(hasil_pencarian)

    assert hasil.status == StatusEksekusi.SEBAGIAN
    assert hasil.kecocokan == hasil_awal  # Langkah 1 dipertahankan utuh
