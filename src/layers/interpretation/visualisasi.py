"""Penyusunan Data Visualisasi (Milestone 4.5, Interpretation Langkah 15).

Transformasi struktur data MURNI, TANPA model AI (forced Lingkup M4.5
sumber, decisions.md Keputusan 7) - mengubah `nilai_hasil["rows"]`
(bentuk generik hasil `chatbot_api`) jadi bentuk siap-konsumsi frontend
sesuai `label_bentuk_jawaban`.

Skema `DataVisualisasi` (decisions.md Keputusan 8-9): label
`nilai_tunggal` -> field `nilai_tunggal` (scalar); 4 label lain
(`tren`/`perbandingan`/`peringkat`/`komposisi`) -> field `deret` (list
apa adanya dari `rows`). Perluasan `deret` ke 3 label selain `tren`
PROVISIONAL (docs/keputusan-tertunda.md #4).

Ekstraksi scalar untuk `nilai_tunggal` HANYA kalau baris tunggal +
kolom tunggal (tidak ambigu) - kasus ambigu (>1 baris atau >1 kolom)
fallback ke `deret` (jujur soal keterbatasan, TIDAK menebak kolom mana
yang "nilai"-nya - lihat plan Risiko & Mitigasi).
"""

from src.schemas.interpretation import DataVisualisasi
from src.schemas.session_memory import LabelBentukJawaban, SessionMemoryPackage


def susun_data_visualisasi(package: SessionMemoryPackage) -> DataVisualisasi:
    rows = package.nilai_hasil.get("rows", [])

    if package.label_bentuk_jawaban == LabelBentukJawaban.NILAI_TUNGGAL:
        if len(rows) == 1 and isinstance(rows[0], dict) and len(rows[0]) == 1:
            nilai = next(iter(rows[0].values()))
            return DataVisualisasi(
                atomic_intent_id=package.atomic_intent_id,
                label_bentuk_jawaban=package.label_bentuk_jawaban,
                nilai_tunggal=nilai,
                deret=None,
            )
        # Ambigu (bukan 1 baris x 1 kolom) - fallback aman ke deret,
        # tidak menebak kolom mana yang jadi "nilai" tunggalnya.
        return DataVisualisasi(
            atomic_intent_id=package.atomic_intent_id,
            label_bentuk_jawaban=package.label_bentuk_jawaban,
            nilai_tunggal=None,
            deret=rows,
        )

    return DataVisualisasi(
        atomic_intent_id=package.atomic_intent_id,
        label_bentuk_jawaban=package.label_bentuk_jawaban,
        nilai_tunggal=None,
        deret=rows,
    )


def susun_data_visualisasi_semua(
    packages: list[SessionMemoryPackage],
) -> list[DataVisualisasi]:
    return [susun_data_visualisasi(p) for p in packages]
