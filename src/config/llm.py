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
- OPENROUTER_MODEL_MATCHING: Qwen3-32B (reuse M1.4/M1.6), dipakai
  matching.py (M1.7) - tanpa verifier independen kedua (Keputusan 2 M1.7),
  argumen keragaman model M1.6 Langkah 6 tidak berlaku. Konstanta terisolasi
  sendiri meski nilainya kebetulan sama, lihat
  milestones/1.7-pencocokan-atomic-intent/decisions.md Keputusan 3 dan 9.
- OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI: Qwen3-32B (reuse), dipakai
  identifikasi.py (M2.1, Domain Gate) untuk identifikasi domain awal.
- OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA: DeepSeek V4 Pro (reuse
  pola M1.6 Langkah 6), dipakai verifikasi_titik_buta.py (M2.1) dengan
  reasoning="high" - model berbeda dari identifikasi awal untuk keragaman
  peran verifier independen, karena risiko M2.1 asimetris ke arah domain
  terlewat (beda dari M1.7 yang asimetris ke arah aman). Lihat
  milestones/2.1-identifikasi-domain/decisions.md Keputusan 7 dan 9.

Timeout eksplisit (90 detik, max_retries=1) ditambahkan di
get_openrouter_client() saat eksekusi eval Milestone 2.1 (Checkpoint 10)
- ditemukan panggilan yang hang sangat lama tanpa exception di titik
acak sepanjang beberapa kali percobaan nyata (root cause pasti TIDAK
berhasil diisolasi penuh dalam waktu yang wajar - dicatat sebagai
keterbatasan operasional, lihat logs.md Checkpoint 10 dan
docs/keterbatasan-diterima.md). Batas atas per panggilan sekarang
~90s x (1+max_retries) = ~180s terburuk, gagal ke jalur fallback aman
(gagal=True) yang SUDAH ada di tiap layer, bukan berpotensi hang tanpa
batas. Perubahan murni menambah batas atas (tidak mengubah perilaku
panggilan yang selesai normal), berlaku untuk SELURUH konsumen fungsi
ini (M1.3-M1.7 turut terdampak, bukan cakupan sengaja diperluas).
"""

import os

from dotenv import load_dotenv
from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_MODEL_REWRITE = "qwen/qwen3-32b"
OPENROUTER_MODEL_DECOMPOSITION = "qwen/qwen3-32b"
OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI = "deepseek/deepseek-v4-pro"
OPENROUTER_MODEL_MATCHING = "qwen/qwen3-32b"
OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI = "qwen/qwen3-32b"
OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA = "deepseek/deepseek-v4-pro"

load_dotenv()


def get_openrouter_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY tidak diset. Salin .env.example ke .env dan isi "
            "nilai asli (dapatkan dari https://openrouter.ai/keys)."
        )
    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=90.0,
        max_retries=1,
    )
