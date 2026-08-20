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
- OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI: DeepSeek V4 Flash 0731 (migrasi
  2026-08-20 dari DeepSeek V4 Pro 0423), dipakai verifikasi.py (M1.6,
  Langkah 6) - model berbeda dari Langkah 4-5 untuk keragaman peran
  verifier independen, lihat milestones/1.6-decomposition/decisions.md
  Keputusan 2. Migrasi biaya: risiko titik ini SIMETRIS/tersaring
  layer berikutnya (bukan asimetris/leak-RBAC), Intelligence Index nyaris
  setara dengan Pro 0813 (52 vs 53) - lihat Keputusan 16 (Addendum).
- OPENROUTER_MODEL_MATCHING: Qwen3-32B (reuse M1.4/M1.6), dipakai
  matching.py (M1.7) - tanpa verifier independen kedua (Keputusan 2 M1.7),
  argumen keragaman model M1.6 Langkah 6 tidak berlaku. Konstanta terisolasi
  sendiri meski nilainya kebetulan sama, lihat
  milestones/1.7-pencocokan-atomic-intent/decisions.md Keputusan 3 dan 9.
- OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI: Qwen3-32B (reuse), dipakai
  identifikasi.py (M2.1, Domain Gate) untuk identifikasi domain awal.
- OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA: DeepSeek V4 Pro 0813
  (migrasi 2026-08-20 dari versi preview 0423, reuse pola M1.6 Langkah 6),
  dipakai verifikasi_titik_buta.py (M2.1) dengan reasoning="high" - model
  berbeda dari identifikasi awal untuk keragaman peran verifier independen,
  karena risiko M2.1 asimetris ke arah domain terlewat (beda dari M1.7
  yang asimetris ke arah aman). Lihat
  milestones/2.1-identifikasi-domain/decisions.md Keputusan 7 dan 9.
  TETAP tier Pro (bukan turun ke Flash) karena risiko kebocoran RBAC -
  lihat Keputusan 13 (Addendum).
- OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI: Qwen3-32B (reuse nilai,
  konstanta terisolasi sendiri), dipakai deteksi_cakupan_individu.py
  (M2.3, Domain Gate) untuk deteksi awal constraint cakupan-individu.
- OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI: DeepSeek V4 Pro 0813
  (migrasi 2026-08-20 dari versi preview 0423, reuse nilai, pola sama M2.1
  Langkah 2), dipakai verifikasi_cakupan_individu.py (M2.3) dengan
  reasoning="high" - asimetri risiko M2.3 sama arah dengan M2.1
  (false-negative = constraint terlewat = potensi kebocoran). Lihat
  milestones/2.3-deteksi-cakupan-individu/decisions.md Keputusan 2 dan 8.
  TETAP tier Pro (bukan turun ke Flash) karena risiko kebocoran RBAC -
  lihat Keputusan 13 (Addendum).
- OPENROUTER_MODEL_RETRIEVER_EMBEDDING: text-embedding-3-small (OpenAI via
  OpenRouter), dipakai pencarian_embedding.py (M3.1, fallback cari_bm25()
  gagal menemukan kandidat) - dikunci Checkpoint 8 setelah eval nyata
  membandingkan 3 kandidat (Qwen3-Embedding-4B/8B, text-embedding-3-small):
  Qwen3-4B 0/5 recall (gagal total), Qwen3-8B dan text-embedding-3-small
  sama-sama 5/5, text-embedding-3-small unggul rank+latensi. Status
  PROVISIONAL (dicatat docs/keputusan-tertunda.md, bukan ditutup permanen
  seperti model chat/completion lain - instruksi eksplisit user). Lihat
  milestones/3.1-pengumpulan-kandidat-view/decisions.md Keputusan 2 dan
  evals/3.1-pengumpulan-kandidat-view/audit.md.
- OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE: Qwen3-32B (reuse), dipakai
  kecocokan_makna.py (M3.2, Langkah 1) untuk penilaian awal label
  ditemukan/sebagian/tidak_ditemukan per kandidat view.
- OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI: DeepSeek V4 Flash 0731
  (migrasi 2026-08-20 dari DeepSeek V4 Pro 0423, pola generate-verify
  M1.6 Langkah 6/M2.1/M2.3), dipakai kecocokan_makna.py (M3.2, Langkah 2)
  dengan reasoning="high" - berbeda dari M2.1/M2.3, hasil Langkah 2 di
  sini MENGGANTIKAN Langkah 1 (koreksi dua arah, bukan union aditif),
  karena risiko M3.2 simetris (KK1 dan KK2 sama-sama penting). Lihat
  milestones/3.2-kecocokan-makna/decisions.md Keputusan 1 dan 4. Migrasi
  biaya: risiko simetris (bukan leak-RBAC), Intelligence Index nyaris
  setara Pro 0813 (52 vs 53) - lihat Keputusan 15 (Addendum).
- OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL: Qwen3-32B (reuse, model chat/
  completion biasa - forced preseden M1.6/M2.1/M2.3/M3.2 Keputusan 4,
  tidak perlu perbandingan empiris baru), dipakai kecukupan_struktural.py
  (M3.3, fallback LLM) - SATU panggilan konservatif (bukan generate-verify
  penuh) untuk kandidat yang rule table deterministik menghasilkan
  tidak_pasti, karena risiko M3.3 asimetris (mirror M1.7, bukan simetris
  seperti M3.2). Lihat milestones/3.3-kecukupan-struktural/decisions.md
  Keputusan 5.
- OPENROUTER_MODEL_PENYUSUNAN_REQUEST: Qwen3-32B (reuse, model chat/
  completion biasa - forced preseden "satu konstanta per konsumen" M1.4
  Keputusan 9, tidak perlu perbandingan empiris baru), dipakai
  penyusunan_request.py (M3.4, Langkah 1 Query Engine) - SATU panggilan
  generate-only (ekstraksi parameter terstruktur), tanpa retry/verifier
  independen (M3.5 terpisah). Lihat
  milestones/3.4-penyusunan-request/decisions.md Keputusan 9 dan 10.
- OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST: DeepSeek V4 Flash 0731
  (migrasi 2026-08-20 dari DeepSeek V4 Pro 0423, pola generate-verify
  M1.6 Langkah 6/M2.1/M2.3/M3.2 Langkah 2), dipakai
  verifikasi_bentuk_request.py (M3.5, Langkah 2 Query Engine) dengan
  reasoning="high" - verifikasi independen SATU panggilan terhadap hasil
  M3.4, dipicu HANYA setelah pre-check kepatuhan sumber deterministik
  lolos. Lihat
  milestones/3.5-verifikasi-bentuk-request/decisions.md Keputusan 5.
  Migrasi biaya: cakupan verifikasi sudah dipersempit pre-check
  deterministik (bukan leak-RBAC), Intelligence Index nyaris setara Pro
  0813 (52 vs 53) - lihat Keputusan 14 (Addendum).
- OPENROUTER_MODEL_NARASI: Qwen3-32B (reuse, konstanta terisolasi sendiri
  mengikuti pola "satu konstanta per konsumen" M1.4 Keputusan 9), dipakai
  narasi.py (M4.4, Interpretation) untuk penyusunan narasi jawaban akhir -
  SATU panggilan generate-only (teks bebas, bukan ekstraksi terstruktur),
  tanpa retry/feedback internal (verifier independen M4.5 terpisah).
  Dikonfirmasi user (bukan perbandingan empiris baru) atas dasar benchmark
  SEA-HELM Bahasa Indonesia yang sama dipakai M1.4 (Rewrite) - tugas NLG
  serupa, beda dari mayoritas milestone lain yang murni ekstraksi/
  klasifikasi terstruktur. Lihat milestones/4.4-penyusunan-narasi/
  decisions.md Keputusan 1.
- OPENROUTER_MODEL_VERIFIKASI_KESETIAAN: DeepSeek V4 Pro 0813 (migrasi
  2026-08-20 dari versi preview 0423, reuse pola M1.6 Langkah 6/M2.1/
  M2.3/M3.2 Langkah 2/M3.5 Langkah 2), dipakai verifikasi_kesetiaan.py
  (M4.5, Interpretation) dengan reasoning="high" - verifikasi independen
  SATU panggilan terhadap narasi hasil M4.4, TANPA retry balik ke M4.4
  (mirror M3.5 - jalur revisi di luar cakupan). Sengaja TIDAK diajukan
  ulang ke user (beda M4.4) - tugas verifier tetap berbentuk sama
  (lolos/alasan) seperti 5 preseden sebelumnya. Lihat
  milestones/4.5-verifikasi-kesetiaan-dan-visualisasi/decisions.md
  Keputusan 1. TETAP tier Pro (bukan turun ke Flash) karena ini garda
  TERAKHIR sebelum narasi sampai ke user, tanpa verifikasi lain
  setelahnya - lihat Keputusan 15 (Addendum).

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
OPENROUTER_MODEL_DECOMPOSITION_VERIFIKASI = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_MODEL_MATCHING = "qwen/qwen3-32b"
OPENROUTER_MODEL_DOMAIN_IDENTIFIKASI = "qwen/qwen3-32b"
OPENROUTER_MODEL_DOMAIN_VERIFIKASI_TITIK_BUTA = "deepseek/deepseek-v4-pro-0813"
OPENROUTER_MODEL_CAKUPAN_INDIVIDU_IDENTIFIKASI = "qwen/qwen3-32b"
OPENROUTER_MODEL_CAKUPAN_INDIVIDU_VERIFIKASI = "deepseek/deepseek-v4-pro-0813"
OPENROUTER_MODEL_RETRIEVER_EMBEDDING = "openai/text-embedding-3-small"
OPENROUTER_MODEL_KECOCOKAN_MAKNA_GENERATE = "qwen/qwen3-32b"
OPENROUTER_MODEL_KECOCOKAN_MAKNA_VERIFIKASI = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_MODEL_KECUKUPAN_STRUKTURAL = "qwen/qwen3-32b"
OPENROUTER_MODEL_PENYUSUNAN_REQUEST = "qwen/qwen3-32b"
OPENROUTER_MODEL_VERIFIKASI_BENTUK_REQUEST = "deepseek/deepseek-v4-flash-0731"
OPENROUTER_MODEL_NARASI = "qwen/qwen3-32b"
OPENROUTER_MODEL_VERIFIKASI_KESETIAAN = "deepseek/deepseek-v4-pro-0813"

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
