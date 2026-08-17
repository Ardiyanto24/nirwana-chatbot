"""Test corpus definisi lengkap 67 view (Milestone 3.2) - cross-check
terhadap dokumen sumber via regex independen (parse ulang dari
docs/03-domain-source/katalog-data-chatbot.md), bukan len()/perbandingan
terhadap dirinya sendiri - supaya bukan pengujian sirkular, deteksi drift
transkripsi. Mirror pola tests/layers/retriever/test_korpus_view.py (M3.1),
tapi regex lebih kompleks: panjang blok variabel (bukan satu baris), header
kadang py teks tambahan setelah backtick penutup (mis. "`guests_contact_view`
(domain `guests_pii`)"), dan boundary blok berhenti di header `####`
berikutnya, header `##` (baik domain baru maupun `## Catatan Lintas-Domain`),
atau akhir dokumen."""

import re
from pathlib import Path

from src.config.katalog_view import DAFTAR_VIEW_PER_DOMAIN
from src.layers.retriever.definisi_view import CATATAN_LINTAS_DOMAIN, DEFINISI_LENGKAP_VIEW

_KATALOG_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "03-domain-source"
    / "katalog-data-chatbot.md"
)

_VIEW_PATTERN = re.compile(
    r"^#### `([^`]+)`[^\n]*\n(.*?)(?=\n#### `|\n## |\Z)",
    re.MULTILINE | re.DOTALL,
)


def _dokumen_teks() -> str:
    return _KATALOG_PATH.read_text(encoding="utf-8")


def _body_sebelum_catatan_lintas_domain(teks: str) -> str:
    idx = teks.index("## Catatan Lintas-Domain")
    return teks[:idx]


def _parse_definisi_dari_dokumen() -> dict[str, str]:
    body = _body_sebelum_catatan_lintas_domain(_dokumen_teks())
    hasil = {}
    for m in _VIEW_PATTERN.finditer(body):
        blok = re.sub(r"\n+---\s*$", "", m.group(2)).strip()
        hasil[m.group(1)] = blok
    return hasil


def _parse_catatan_lintas_domain_dari_dokumen() -> str:
    teks = _dokumen_teks()
    idx_catatan = teks.index("## Catatan Lintas-Domain")
    idx_referensi = teks.index("## Referensi")
    blok = teks[idx_catatan:idx_referensi]
    return re.sub(r"\n+---\s*$", "", blok).strip()


def test_definisi_sama_persis_dengan_dokumen_sumber():
    dari_dokumen = _parse_definisi_dari_dokumen()
    assert dari_dokumen == DEFINISI_LENGKAP_VIEW


def test_regex_menemukan_67_entri_di_dokumen():
    """Prasyarat test di atas - kalau regex sendiri gagal menemukan 67
    entri, perbandingan == di atas bisa 'lolos' secara keliru karena
    dua-duanya sama-sama kosong/parsial."""
    assert len(_parse_definisi_dari_dokumen()) == 67


def test_definisi_67_entri():
    assert len(DEFINISI_LENGKAP_VIEW) == 67


def test_bijektif_dengan_daftar_view_per_domain():
    seluruh_view_katalog = {
        v for views in DAFTAR_VIEW_PER_DOMAIN.values() for v in views
    }
    assert set(DEFINISI_LENGKAP_VIEW.keys()) == seluruh_view_katalog


def test_catatan_lintas_domain_sama_persis_dengan_dokumen_sumber():
    assert _parse_catatan_lintas_domain_dari_dokumen() == CATATAN_LINTAS_DOMAIN


def test_kolom_turunan_marker_tertangkap():
    """Prasyarat KK1 sumber M3.2: kolom turunan (mis. sla_threshold_hours,
    hasil hitung bukan native) adalah salah satu bentuk jebakan grain inti
    yang wajib bisa dinilai LLM - kalau tidak tertangkap transkripsi, model
    tidak akan pernah punya sinyal untuk mendeteksinya."""
    assert "Kolom turunan" in DEFINISI_LENGKAP_VIEW["v_maintenance_ticket_daily"]


def test_snapshot_trap_tertangkap():
    """Prasyarat KK1 sumber M3.2: v_hr_turnover_snapshot py jebakan grain
    yang folded ke teks Fungsi ("snapshot, tidak ada tren historis"), bukan
    section Catatan terpisah - transkripsi verbatim wajib menangkapnya."""
    assert (
        "snapshot, tidak ada tren historis"
        in DEFINISI_LENGKAP_VIEW["v_hr_turnover_snapshot"]
    )


def test_catatan_lintas_domain_mengandung_jebakan_kolom_join():
    """Butir 5 Catatan Lintas-Domain - daftar eksplisit view dengan kolom
    property_id hasil join, bukan native - jebakan inti KK1 sumber M3.2."""
    assert "di-join dari" in CATATAN_LINTAS_DOMAIN
    assert "v_lookup_fnb_inventory" in CATATAN_LINTAS_DOMAIN
