"""Konfigurasi koneksi ke chatbot_api (sistem eksternal, HTTP) untuk
Milestone 4.1 (Execution, `src/layers/execution/pemanggilan_chatbot_api.py`)
dan Milestone 4.2 (`src/layers/execution/klasifikasi_respons.py`).

Pola env var + `RuntimeError` identik `get_engine()` (`database.py`)/
`get_openrouter_client()` (`llm.py`). Timeout default (30 detik) BUKAN
hasil kalibrasi empiris seperti timeout OpenRouter (`docs/keterbatasan-
diterima.md` #7) - diterapkan proaktif sebagai starting point sebelum
insiden serupa terjadi, lihat
milestones/4.1-membangun-pemanggilan-chatbot-api/decisions.md Keputusan 8.

Konstanta retry/revisi (M4.2) juga starting point non-empiris, mirror
alasan yang sama - lihat milestones/4.2-klasifikasi-respons-dan-
penanganan-kegagalan/decisions.md Keputusan 6. EXECUTION_MAX_RETRY_INFRA
mirror preseden numerik _MAX_ATTEMPTS=3 (decompose.py, M1.6 Keputusan 3):
1 percobaan awal + hingga 2 retry/revisi.
"""

import os

from dotenv import load_dotenv

CHATBOT_API_TIMEOUT_DETIK = 30.0
EXECUTION_MAX_RETRY_INFRA = 2
EXECUTION_RETRY_DELAY_DETIK = 1.0
EXECUTION_MAX_REVISI = 3

load_dotenv()


def get_chatbot_api_base_url() -> str:
    base_url = os.environ.get("CHATBOT_API_BASE_URL")
    if not base_url:
        raise RuntimeError(
            "CHATBOT_API_BASE_URL tidak diset. Salin .env.example ke .env dan "
            "isi alamat instance chatbot_api (mis. http://127.0.0.1:8000 untuk "
            "instance lokal)."
        )
    return base_url.rstrip("/")
