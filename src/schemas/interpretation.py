"""Skema Interpretation (Milestone 4.4): Penyusunan Narasi.

`HasilNarasi` sengaja hanya satu field (`narasi: str`) - beda dari seluruh
skema hasil LLM lain di project yang membungkus keputusan TERSTRUKTUR
(bool/enum/index). Output langkah ini adalah teks bebas berbahasa natural
itu sendiri, bukan keputusan yang diekstrak DARI teks - tidak ada field
tambahan yang genuinely dibutuhkan konsumen (Milestone 4.5 menilai teks
narasi ini langsung, membandingkan ke paket sumber yang sudah tersedia
terpisah). Lihat decisions.md Keputusan 10.
"""

from pydantic import BaseModel


class HasilNarasi(BaseModel):
    narasi: str
