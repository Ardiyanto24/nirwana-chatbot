"""Whitelist Parameter Query per View (Milestone 3.4) - diturunkan
PROGRAMATIK dari DEFINISI_LENGKAP_VIEW (M3.2, transkripsi tabel kolom
katalog data) untuk mengisi `params` `QueryEngineRequest` tanpa
mengarang nama parameter di luar kolom yang benar-benar ada di tiap
view.

Bahan pembangkit `docs/kontrak-parameter-chatbot-api-usulan.md` - lihat
milestones/3.4-penyusunan-request/decisions.md Keputusan 1: konvensi
PROVISIONAL, BELUM kontrak resmi `chatbot_api` (kode API + file
whitelist_<domain>.py sepenuhnya di luar repo ini), untuk direkonsiliasi
dengan tim pembangun API di akhir proyek.

Aturan derivasi per view:
- Parse tabel Markdown "| Kolom | Deskripsi |" di tiap entri
  DEFINISI_LENGKAP_VIEW, ekstrak seluruh nama kolom berformat backtick
  di SEL PERTAMA tiap baris tabel saja (bukan sel Deskripsi, yang sering
  memuat backtick lain seperti nilai enum) - satu baris kadang mendaftar
  >1 kolom sekaligus, dipisah koma atau garis miring, keduanya tertangkap
  karena regex mencari SELURUH nama berformat backtick di sel itu, bukan
  split by separator tertentu.
- Kolom yang namanya mengandung substring "date" (period_date,
  check_in_date, booking_date, transaction_datetime, reported_date,
  resolved_date, service_date, event_date, opening_date, registered_date
  - seluruhnya dikonfirmasi mengandung substring ini) menghasilkan TIGA
  entri whitelist: `<col>` (exact match satu tanggal), `<col>_from`,
  `<col>_to` (rentang).
- Kolom lain menghasilkan SATU entri exact-match `<col>`.
- `limit`/`offset` (parameter global dari `api-chatbot.md`, BUKAN
  turunan kolom) ditambahkan ke SETIAP view.
- `employee_id`/`role_title`/`domain`/`view_name` TIDAK PERNAH masuk
  whitelist manapun, bahkan kalau nama itu kebetulan muncul sebagai nama
  kolom di suatu view - `employee_id` sudah jadi tanggung jawab penuh
  Verification Gate (M2.4 Cek 3, ditimpa paksa kapan pun constraint
  cakupan-individu terdeteksi), `role_title` identity claim bukan filter
  data, `domain`/`view_name` sudah diturunkan kode di susun_request_
  atomic_intent() (bukan bagian `params`).
"""

import re

from src.layers.retriever.definisi_view import DEFINISI_LENGKAP_VIEW

_KOLOM_TABLE_HEADER = "| Kolom | Deskripsi |"
_BACKTICK_NAME = re.compile(r"`([a-z_][a-z0-9_]*)`")

PARAM_GLOBAL: frozenset[str] = frozenset({"limit", "offset"})
PARAM_TERLARANG: frozenset[str] = frozenset({"employee_id", "role_title", "domain", "view_name"})


def _ekstrak_nama_kolom(definisi: str) -> list[str]:
    """Parse tabel '| Kolom | Deskripsi |' di definisi satu view,
    kembalikan seluruh nama kolom (bisa >1 nama per baris tabel) sesuai
    urutan kemunculan, tanpa duplikat. HANYA memproses sel pertama tiap
    baris tabel - sel Deskripsi (sel kedua) sengaja diabaikan supaya
    nilai enum/nama tabel lain yang kebetulan berformat backtick di
    situ tidak salah tertangkap sebagai nama kolom."""
    baris = definisi.splitlines()
    try:
        idx_header = baris.index(_KOLOM_TABLE_HEADER)
    except ValueError:
        return []

    nama_kolom: list[str] = []
    dilihat: set[str] = set()
    # baris idx_header+1 adalah separator "|---|---|" - dilewati begitu
    # saja (mulai dari idx_header+2), tidak perlu divalidasi isinya.
    for baris_tabel in baris[idx_header + 2 :]:
        if not baris_tabel.startswith("|"):
            break  # tabel berakhir (baris kosong atau blockquote Catatan)
        sel = baris_tabel.split("|")
        if len(sel) < 2:
            break
        sel_nama_kolom = sel[1]
        for nama in _BACKTICK_NAME.findall(sel_nama_kolom):
            if nama not in dilihat:
                dilihat.add(nama)
                nama_kolom.append(nama)
    return nama_kolom


def _whitelist_dari_kolom(nama_kolom: list[str]) -> frozenset[str]:
    hasil: set[str] = set(PARAM_GLOBAL)
    for kolom in nama_kolom:
        if kolom in PARAM_TERLARANG:
            continue
        if "date" in kolom:
            hasil.add(kolom)
            hasil.add(f"{kolom}_from")
            hasil.add(f"{kolom}_to")
        else:
            hasil.add(kolom)
    return frozenset(hasil)


PARAM_WHITELIST_VIEW: dict[str, frozenset[str]] = {
    view_name: _whitelist_dari_kolom(_ekstrak_nama_kolom(definisi))
    for view_name, definisi in DEFINISI_LENGKAP_VIEW.items()
}
