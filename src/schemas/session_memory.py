"""Skema paket Session Memory (Milestone 1.5), bentuk publik yang dikembalikan
`retrieve_session_memory()` dan diterima `store_session_memory()`.

9 field sudah dikunci penuh di arsitektur-ai-chatbot-rbac.md SS7 - bukan
keputusan desain, murni implementasi kontrak. `sumber` sengaja `str` bebas
(bukan Enum) karena nilainya bisa dinamis ("session_memory (turn N)"), beda
dari `label_bentuk_jawaban`/`status` yang genuinely tertutup.

Pydantic murni, TANPA table=True - dipisah dari row DB (src/db/models.py)
supaya tidak ada objek ORM "terlepas sesi" bocor ke business logic, mirror
pola RewriteResult/TurnDependencyResult. Lihat decisions.md Keputusan 8.
"""

from enum import Enum

from pydantic import BaseModel


class LabelBentukJawaban(str, Enum):
    NILAI_TUNGGAL = "nilai_tunggal"
    TREN = "tren"
    PERBANDINGAN = "perbandingan"
    PERINGKAT = "peringkat"
    KOMPOSISI = "komposisi"


class StatusEksekusi(str, Enum):
    BERHASIL = "berhasil"
    SEBAGIAN = "sebagian"
    DITOLAK_OTORISASI = "ditolak_otorisasi"
    GAGAL_TEKNIS = "gagal_teknis"
    TERBLOKIR_KETERGANTUNGAN = "terblokir_ketergantungan"


class SessionMemoryPackage(BaseModel):
    atomic_intent_id: str
    session_id: str
    turn_index: int
    teks_kebutuhan: str
    label_bentuk_jawaban: LabelBentukJawaban
    nilai_hasil: dict
    catatan_interpretasi: list[str]
    status: StatusEksekusi
    sumber: str
