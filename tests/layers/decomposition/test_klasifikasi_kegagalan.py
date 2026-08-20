"""Test suite skenario kegagalan teknis `klasifikasi_kebutuhan()`
(Milestone 1.6, addendum ditemukan Milestone 7.18 2026-08-20) - span
`chat` harus mencatat `decomposition.forced_fallback_reason` saat
`_call_llm()` mengembalikan `response.choices` kosong/`None` (respons
API 200 tapi malformed - BUKAN `openai.APIError`, jadi tidak tertangkap
`except APIError` yang sudah ada), LALU fungsi tetap mengembalikan
`_FALLBACK` (mirror pola fallback aman APIError yang sudah ada),
BUKAN melempar `TypeError`/`IndexError` yang tidak tertangani.

Murni mocked (`_call_llm` di-monkeypatch) - SENGAJA dipisah dari
test_decompose.py (yang murni LLM sungguhan), mirror pola
test_turn_dependency_kegagalan.py (M1.3).

Lihat milestones/1.6-decomposition/decisions.md Addendum dan
docs/keterbatasan-diterima.md #17 (titik "3 sub-langkah Decomposition
M1.6" - status: SEBAGIAN DIPERBAIKI, klasifikasi.py saja).
"""

from types import SimpleNamespace

import src.layers.decomposition.klasifikasi as modul
from src.layers.decomposition.klasifikasi import klasifikasi_kebutuhan
from src.schemas.decomposition import KlasifikasiKebutuhan


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


def test_choices_none_fallback_aman_tanpa_exception_menjalar(monkeypatch):
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)

    respons_malformed = SimpleNamespace(usage=None, choices=None)
    monkeypatch.setattr(modul, "_call_llm", lambda question: respons_malformed)

    result = klasifikasi_kebutuhan("Berapa occupancy rate bulan ini?")

    assert result == KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG
    reason = tracer_rekam.span.atribut["decomposition.forced_fallback_reason"]
    assert "empty_response" in reason


def test_choices_kosong_list_fallback_aman(monkeypatch):
    tracer_rekam = _TracerRekam()
    monkeypatch.setattr(modul, "get_tracer", lambda name: tracer_rekam)

    respons_malformed = SimpleNamespace(usage=None, choices=[])
    monkeypatch.setattr(modul, "_call_llm", lambda question: respons_malformed)

    result = klasifikasi_kebutuhan("Berapa occupancy rate bulan ini?")

    assert result == KlasifikasiKebutuhan.MAJEMUK_BERGANTUNG
    reason = tracer_rekam.span.atribut["decomposition.forced_fallback_reason"]
    assert "empty_response" in reason
