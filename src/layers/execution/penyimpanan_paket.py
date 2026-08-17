"""Penyusunan dan Penyimpanan Paket Session Memory (Milestone 4.3).
Konsumen `status`/`nilai_hasil` (biasanya dari `HasilEksekusiAtomicIntent`
M4.2, tapi diterima sebagai parameter eksplisit - lihat decisions.md
Keputusan 3, forced diagram arsitektur §5 yang menunjukkan "Simpan paket"
sebagai satu langkah membungkus SELURUH Fase 2, bukan spesifik Execution).

Menyusun `SessionMemoryPackage` sesuai skema M1.5, lalu menyimpannya
lewat `store_session_memory()` (M1.5, sudah ter-instrumentasi span
`memory.store` + penanganan kegagalan sejak Checkpoint 2 M4.3).

`nilai_hasil` list-of-row (bentuk nyata `chatbot_api`, bukti M4.1)
dibungkus `{"rows": [...]}` sebelum masuk field `nilai_hasil: dict`
(Keputusan 1). `catatan_interpretasi` murni dict lookup deterministik
terhadap `CATATAN_NULLABLE_BERMAKNA` (Checkpoint 3) - TANPA LLM, sesuai
Lingkup M4.3 sendiri ("pengetahuan yang ditempel", bukan digenerate).

Revisit (2026-08-17, Keputusan 9): `catatan_interpretasi` DIGABUNG dengan
catatan kualitas data (`data_quality_status`/`last_refreshed_at`, dari
`HasilEksekusiAtomicIntent` M4.2 Keputusan 11) - nada teks BERBEDA untuk
SEBAGIAN (terkonfirmasi `flagged`/stale) vs BERHASIL dengan kualitas
tidak diketahui (netral, TIDAK menyiratkan masalah).
"""

from typing import Any

from src.config.catatan_nullable_bermakna import CATATAN_NULLABLE_BERMAKNA
from src.config.chatbot_api import EXECUTION_DATA_STALENESS_THRESHOLD_JAM
from src.layers.context_resolution.session_memory import store_session_memory
from src.schemas.decomposition import AtomicIntent
from src.schemas.session_memory import SessionMemoryPackage, StatusEksekusi


def _bungkus_nilai_hasil(nilai_hasil: Any) -> dict:
    """List-of-row dibungkus {"rows": [...]} (Keputusan 1). None/tanpa
    hasil -> {"rows": []}. Bentuk lain yang tak terduga (bukan list,
    bukan None) tetap dibungkus defensif - SessionMemoryPackage.nilai_hasil
    (dict, wajib) tidak boleh gagal validasi karena bentuk hasil asli
    yang di luar dugaan."""
    if nilai_hasil is None:
        return {"rows": []}
    if isinstance(nilai_hasil, list):
        return {"rows": nilai_hasil}
    return {"rows": [nilai_hasil]}


def _catatan_interpretasi_untuk_hasil(view_name: str | None, nilai_hasil: Any) -> list[str]:
    """HANYA kolom yang (a) benar-benar None di baris hasil DAN (b)
    terdaftar CATATAN_NULLABLE_BERMAKNA[view_name] yang memicu catatan.
    Kolom null yang TIDAK terdaftar tidak memicu apa pun - jujur soal
    keterbatasan katalog subset (docs/keterbatasan-diterima.md #12),
    bukan menyamarkan tahu."""
    if not view_name or not isinstance(nilai_hasil, list) or not nilai_hasil:
        return []

    catatan_view = CATATAN_NULLABLE_BERMAKNA.get(view_name)
    if not catatan_view:
        return []

    kolom_null: set[str] = set()
    for baris in nilai_hasil:
        if not isinstance(baris, dict):
            continue
        for kolom, nilai in baris.items():
            if nilai is None and kolom in catatan_view:
                kolom_null.add(kolom)

    return [catatan_view[kolom] for kolom in sorted(kolom_null)]


def _catatan_kualitas_data(
    status: StatusEksekusi, data_quality_status: str | None, last_refreshed_at: str | None
) -> list[str]:
    """Revisit (Keputusan 9): nada BERBEDA untuk SEBAGIAN (terkonfirmasi)
    vs BERHASIL+kualitas tidak diketahui (netral) - kejujuran soal
    SEBERAPA yakin sistem terhadap sinyal ini, mirror alasan M4.2
    Keputusan 11 memisahkan kedua kasus itu di level status."""
    if status == StatusEksekusi.SEBAGIAN:
        if data_quality_status == "flagged":
            return [
                "Status kualitas data untuk hasil ini ditandai perlu perhatian "
                "oleh tim database engineering (data_quality_status=flagged)."
            ]
        if last_refreshed_at is not None:
            return [
                f"Data terakhir diperbarui {last_refreshed_at}, melewati ambang "
                f"kesegaran yang ditetapkan ({EXECUTION_DATA_STALENESS_THRESHOLD_JAM} jam)."
            ]
        return []
    if status == StatusEksekusi.BERHASIL and data_quality_status is None:
        return [
            "Status kualitas data untuk hasil ini belum diketahui/belum "
            "tercakup pengecekan otomatis tim database saat ini."
        ]
    return []


def susun_dan_simpan_paket(
    atomic_intent: AtomicIntent,
    session_id: str,
    turn_index: int,
    status: StatusEksekusi,
    view_name: str | None = None,
    nilai_hasil: Any = None,
    data_quality_status: str | None = None,
    last_refreshed_at: str | None = None,
) -> SessionMemoryPackage:
    """Orkestrator M4.3. `sumber` SELALU "eksekusi_baru" - M4.3 hanya
    menangani jalur ini, bukan `sumber` dari session memory turn lain
    (yang jadi tanggung jawab M1.7, sudah selesai). Exception dari
    `store_session_memory()` (Checkpoint 2) diteruskan apa adanya, TIDAK
    ditelan. `data_quality_status`/`last_refreshed_at` (Revisit,
    Keputusan 9) opsional - diteruskan dari `HasilEksekusiAtomicIntent`
    M4.2 kalau ada."""
    catatan = _catatan_interpretasi_untuk_hasil(view_name, nilai_hasil) + _catatan_kualitas_data(
        status, data_quality_status, last_refreshed_at
    )
    package = SessionMemoryPackage(
        atomic_intent_id=atomic_intent.atomic_intent_id,
        session_id=session_id,
        turn_index=turn_index,
        teks_kebutuhan=atomic_intent.teks_kebutuhan,
        label_bentuk_jawaban=atomic_intent.label_bentuk_jawaban,
        nilai_hasil=_bungkus_nilai_hasil(nilai_hasil),
        catatan_interpretasi=catatan,
        status=status,
        sumber="eksekusi_baru",
    )
    store_session_memory(package)
    return package
