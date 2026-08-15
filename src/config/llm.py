"""Konfigurasi provider LLM (OpenRouter) untuk pemanggilan model AI proyek.

Provider dipilih user untuk Milestone 1.3 (pemanggilan LLM pertama proyek):
OpenRouter. Model dipilih per-langkah (boleh beda kalau kebutuhannya beda,
lihat CLAUDE.md "Status Saat Ini") - konstanta diisolasi di sini supaya
gampang diganti tanpa menyentuh logic layer.

- OPENROUTER_MODEL: DeepSeek V4 Flash 0731, dipakai turn_dependency.py (M1.3),
  eksplisit untuk keperluan testing (lihat
  milestones/1.3-pemetaan-ketergantungan-turn/decisions.md).
- OPENROUTER_MODEL_REWRITE: Qwen3-32B, dipakai rewrite.py (M1.4) - dipilih
  atas bukti benchmark Bahasa Indonesia langsung (SEA-HELM), lihat
  milestones/1.4-rewrite-mandiri/decisions.md Keputusan 1.
- OPENROUTER_MODEL_DECOMPOSITION: Qwen3-32B (reuse M1.4), dipakai
  klasifikasi.py+pemecahan.py (M1.6, Langkah 4-5) - konstanta terisolasi
  sendiri meski nilainya kebetulan sama dengan OPENROUTER_MODEL_REWRITE
  (preseden Keputusan 9 M1.4: satu konstanta per konsumen, hindari coupling
  tak sengaja). Lihat milestones/1.6-decomposition/decisions.md Keputusan 1.
- OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI: DeepSeek V4 Pro, dipakai
  verifikasi.py (M1.6, Langkah 6) - model berbeda dari Langkah 4-5 untuk
  keragaman peran verifier independen, lihat
  milestones/1.6-decomposition/decisions.md Keputusan 2.
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_MODEL_REWRITE = "qwen/qwen3-32b"
OPENROUTER_MODEL_DECOMPOSITION = "qwen/qwen3-32b"
OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI = "deepseek/deepseek-v4-pro"

load_dotenv()


def get_openrouter_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY tidak diset. Salin .env.example ke .env dan isi "
            "nilai asli (dapatkan dari https://openrouter.ai/keys)."
        )
    return OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
