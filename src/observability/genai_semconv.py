"""Kunci versi konvensi atribut ``gen_ai.*`` yang dipakai di seluruh proyek.

Konvensi ini mengikuti OpenTelemetry GenAI Semantic Conventions, yang masih
berstatus pre-stable ("Development") dan sengaja dikunci eksplisit di sini
(bukan hanya disebut di dokumen) supaya PIC 2-4 tahu persis versi mana yang
diikuti - lihat rancangan-observability-ai-chatbot.md header dan Milestone 1.1
di rancangan-context-decomposition.md.

Temuan penting saat dikunci (2026-08-14): governance spesifikasi gen_ai.*
pindah dari repo utama open-telemetry/semantic-conventions ke repo terpisah
open-telemetry/semantic-conventions-genai sejak rilis semantic-conventions
v1.42.0 (2026-06-12). Repo baru itu belum punya release/tag resmi maupun paket
PyPI generated-code sendiri per tanggal pengecekan ini - dicatat sebagai
keterbatasan diterima di docs/keterbatasan-diterima.md, bukan diabaikan.

Nilai string atribut yang dipakai di modul ini (gen_ai.operation.name,
gen_ai.request.model, gen_ai.conversation.id, gen_ai.usage.input_tokens,
gen_ai.usage.output_tokens) dikonfirmasi identik antara paket Python yang
diinstal dan dokumentasi resmi repo baru per tanggal pengecekan - lihat
logs.md Checkpoint 3 untuk detail verifikasinya.
"""

from opentelemetry.semconv._incubating.attributes import (
    gen_ai_attributes as _gen_ai,
)

GENAI_SEMCONV_SPEC_STATUS = "development-prestable"
GENAI_SEMCONV_SPEC_SOURCE = (
    "open-telemetry/semantic-conventions-genai "
    "(governance pindah dari semantic-conventions v1.42.0, 2026-06-12)"
)
GENAI_SEMCONV_PYTHON_PACKAGE = "opentelemetry-semantic-conventions==0.65b0"

GEN_AI_OPERATION_NAME = _gen_ai.GEN_AI_OPERATION_NAME
GEN_AI_REQUEST_MODEL = _gen_ai.GEN_AI_REQUEST_MODEL
GEN_AI_CONVERSATION_ID = _gen_ai.GEN_AI_CONVERSATION_ID
GEN_AI_USAGE_INPUT_TOKENS = _gen_ai.GEN_AI_USAGE_INPUT_TOKENS
GEN_AI_USAGE_OUTPUT_TOKENS = _gen_ai.GEN_AI_USAGE_OUTPUT_TOKENS

# Project-custom, BUKAN dari paket resmi opentelemetry-semantic-conventions -
# identitas/versi prompt (Manajemen Prompt Fase 2) tidak ada di GenAI Semantic
# Conventions, jadi ditulis tangan tanpa prefix gen_ai., mengikuti pola atribut
# custom lain di kontrak span (rbac.domain, request.domain, dst.).
PROMPT_ID = "prompt.id"
PROMPT_VERSION = "prompt.version"
