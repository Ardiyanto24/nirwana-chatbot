"""Skema Interpretation (Milestone 4.4-4.5): Penyusunan Narasi, Verifikasi
Kesetiaan Data, Penyusunan Data Visualisasi.

`HasilNarasi` (M4.4) sengaja hanya satu field (`narasi: str`) - beda dari
seluruh skema hasil LLM lain di project yang membungkus keputusan
TERSTRUKTUR (bool/enum/index). Output langkah ini adalah teks bebas
berbahasa natural itu sendiri, bukan keputusan yang diekstrak DARI teks -
tidak ada field tambahan yang genuinely dibutuhkan konsumen (Milestone 4.5
menilai teks narasi ini langsung, membandingkan ke paket sumber yang
sudah tersedia terpisah). Lihat milestones/4.4-.../decisions.md Keputusan 10.

`HasilVerifikasiNarasi` (M4.5) mencetak `HasilVerifikasiBentukRequest`
(M3.5, src/schemas/query_engine.py) - bentuk output yang diminta Lingkup
M4.5 sendiri ("mengembalikan keputusan lolos atau perlu revisi dengan
alasan spesifik") sama persis bentuknya dengan output M3.5. Lihat
milestones/4.5-.../decisions.md Keputusan 4.

`DataVisualisasi` (M4.5) - skema minimum yang diturunkan LANGSUNG dari
teks Kriteria Keberhasilan sumber M4.5: label `nilai_tunggal` -> field
`nilai_tunggal` (scalar) terisi; 4 label lain (`tren`/`perbandingan`/
`peringkat`/`komposisi`) -> field `deret` (list) terisi. Perluasan
`deret` ke 3 label selain `tren` bersifat penalaran-dianalogikan,
dicatat PROVISIONAL (docs/keputusan-tertunda.md #4). Lihat
milestones/4.5-.../decisions.md Keputusan 8-9.
"""

from pydantic import BaseModel, model_validator
from typing_extensions import Self

from src.schemas.session_memory import LabelBentukJawaban, StatusEksekusi


class HasilNarasi(BaseModel):
    narasi: str


class HasilVerifikasiNarasi(BaseModel):
    narasi: str
    status: StatusEksekusi
    lolos: bool | None
    alasan: str | None

    @model_validator(mode="after")
    def status_lolos_alasan_konsisten(self) -> Self:
        if self.status not in (StatusEksekusi.BERHASIL, StatusEksekusi.GAGAL_TEKNIS):
            raise ValueError(
                "status HasilVerifikasiNarasi hanya boleh berhasil/gagal_teknis "
                "- satu pemanggilan LLM, tanpa keputusan otorisasi/ketergantungan/batch"
            )
        if self.status == StatusEksekusi.GAGAL_TEKNIS:
            if self.lolos is not None or self.alasan is not None:
                raise ValueError("status=gagal_teknis wajib lolos=None dan alasan=None")
            return self

        if self.lolos is None:
            raise ValueError("status=berhasil wajib punya lolos (True/False)")
        if self.lolos and self.alasan is not None:
            raise ValueError("lolos=True tidak boleh punya alasan")
        if not self.lolos and self.alasan is None:
            raise ValueError("lolos=False wajib punya alasan")
        return self


class DataVisualisasi(BaseModel):
    atomic_intent_id: str
    label_bentuk_jawaban: LabelBentukJawaban
    nilai_tunggal: float | int | str | None = None
    deret: list[dict] | None = None

    @model_validator(mode="after")
    def bentuk_sesuai_label(self) -> Self:
        if self.label_bentuk_jawaban == LabelBentukJawaban.NILAI_TUNGGAL:
            if self.nilai_tunggal is None or self.deret is not None:
                raise ValueError(
                    "label=nilai_tunggal wajib field nilai_tunggal terisi, deret=None"
                )
        else:
            if self.deret is None or self.nilai_tunggal is not None:
                raise ValueError(
                    f"label={self.label_bentuk_jawaban.value} wajib field deret terisi, "
                    "nilai_tunggal=None"
                )
        return self
