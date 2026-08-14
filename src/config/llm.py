"""Konfigurasi provider LLM (OpenRouter) untuk pemanggilan model AI proyek.

Provider dan model dipilih user untuk Milestone 1.3 (pemanggilan LLM pertama
proyek): OpenRouter, model DeepSeek V4 Flash 0731 - eksplisit untuk keperluan
testing (lihat milestones/1.3-pemetaan-ketergantungan-turn/decisions.md).
Konstanta diisolasi di sini supaya gampang diganti tanpa menyentuh logic layer.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash-0731"

load_dotenv()


def get_openrouter_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY tidak diset. Salin .env.example ke .env dan isi "
            "nilai asli (dapatkan dari https://openrouter.ai/keys)."
        )
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
