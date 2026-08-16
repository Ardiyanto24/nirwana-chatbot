"""Provider Python generik untuk Promptfoo - dipakai seluruh config
`*.promptfooconfig.yaml` di bawah `prompt_reliability/` (satu implementasi,
bukan diduplikasi per prompt).

Reuse `src/prompts/loader.py` dan `src/config/llm.py` yang SAMA dipakai kode
produksi, supaya prompt yang diuji selalu identik dengan yang benar-benar
dikirim saat runtime - bukan salinan terpisah yang bisa drift.

Konfigurasi per prompt (lewat `config:` di YAML):
    prompt_id: id prompt di src/prompts/ (wajib)
    model: konstanta model OpenRouter (wajib)
    response_format: dict, opsional (mis. {"type": "json_object"})
    extra_body: dict, opsional (mis. {"reasoning": {"effort": "high"}})

Variabel per skenario (lewat `vars:` di tiap test case):
    user_prompt: teks user message persis seperti yang dihasilkan
        `_build_user_prompt()` call site terkait.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.llm import get_openrouter_client
from src.prompts.loader import load_prompt


def call_api(prompt, options, context):
    config = options.get("config", {})
    prompt_id = config["prompt_id"]
    model = config["model"]

    system_prompt = load_prompt(prompt_id).render()
    user_prompt = context["vars"]["user_prompt"]

    client = get_openrouter_client()
    kwargs = {}
    if "response_format" in config:
        kwargs["response_format"] = config["response_format"]
    if "extra_body" in config:
        kwargs["extra_body"] = config["extra_body"]

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        **kwargs,
    )

    output = response.choices[0].message.content or ""
    usage = response.usage

    return {
        "output": output,
        "tokenUsage": {
            "prompt": usage.prompt_tokens if usage else 0,
            "completion": usage.completion_tokens if usage else 0,
            "total": usage.total_tokens if usage else 0,
        },
    }
