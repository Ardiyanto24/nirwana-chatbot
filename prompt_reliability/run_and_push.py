"""Wrapper CI Milestone 8.4: jalankan SATU config Promptfoo lalu push hasilnya
ke `prompt_eval_runs` (Supabase), apa pun hasil eval-nya.

Dipanggil per config yang relevan dari job `prompt-eval` (`ci.yml`), satu
proses per config (loop bash di sisi CI) - lihat
`milestones/8.4-llm-eval-gate/decisions.md` Keputusan 4-6. `prompt_id`/
`model` di-extract dari config YAML itu sendiri, `prompt_version` dibaca
LIVE lewat `src.prompts.loader.load_prompt()` - TIDAK ada tabel hardcode
config->metadata di sisi CI yang bisa basi saat prompt di-bump versi.

Exit code mengikuti `npx promptfoo eval` apa adanya (Keputusan 3: gate 100%
lolos wajib, tanpa threshold custom) - push ke Supabase dilakukan SETELAH
eval selesai apa pun hasilnya (riwayat gagal juga bernilai diaudit), TIDAK
memengaruhi exit code yang dikembalikan ke caller.

Jalankan:
    uv run python prompt_reliability/run_and_push.py <path/ke/config.promptfooconfig.yaml>
"""

import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from push_results import push_results  # noqa: E402

from src.prompts.loader import load_prompt  # noqa: E402

_MAX_CONCURRENCY = "2"  # rendah - riwayat hang OpenRouter, keterbatasan-diterima.md #7


def _extract_prompt_id_dan_model(config_path: Path) -> tuple[str, str]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    provider_config = config["providers"][0]["config"]
    return provider_config["prompt_id"], provider_config["model"]


def run_and_push(config_path: Path) -> int:
    prompt_id, model = _extract_prompt_id_dan_model(config_path)
    version = load_prompt(prompt_id).version

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_path = Path(tmp.name)

    cmd = [
        "npx",
        "promptfoo",
        "eval",
        "-c",
        str(config_path),
        "--output",
        str(output_path),
        "--max-concurrency",
        _MAX_CONCURRENCY,
        "--no-progress-bar",
    ]
    result = subprocess.run(cmd, cwd=_HERE, shell=platform.system() == "Windows")

    if output_path.is_file() and output_path.stat().st_size > 0:
        n = push_results(output_path, prompt_id, version, model)
        print(f"[{prompt_id}] push {n} baris ke prompt_eval_runs")
    else:
        print(f"[{prompt_id}] TIDAK ada output eval - push dilewati", file=sys.stderr)

    return result.returncode


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: run_and_push.py <config.promptfooconfig.yaml>", file=sys.stderr)
        sys.exit(2)

    config_path = Path(sys.argv[1]).resolve()
    sys.exit(run_and_push(config_path))


if __name__ == "__main__":
    main()
