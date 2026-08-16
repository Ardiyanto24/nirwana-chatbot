"""Push hasil `promptfoo eval --output <file>.json` ke tabel prompt_eval_runs
(Supabase) - Manajemen Prompt Fase 2 Checkpoint 3.

Dijalankan manual setelah tiap `npx promptfoo eval`, mengikuti konvensi di
prompt_reliability/README.md. Parsing menyesuaikan skema output promptfoo
(`results.results[]`, tiap elemen py `vars`/`response`/`success`) - lihat
rancangan-manajemen-prompt.md Bagian 6 untuk skema tabel tujuan.

Jalankan:
    uv run python prompt_reliability/push_results.py <output.json> <prompt_id> <prompt_version> <model>
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session

from src.config.database import get_engine
from src.db.models import PromptEvalRunRow


def _current_git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def push_results(
    output_json_path: Path,
    prompt_id: str,
    prompt_version: int,
    model: str,
    git_commit_hash: str | None = None,
) -> int:
    """Parse `output_json_path` (skema `promptfoo eval --output`), insert satu
    `PromptEvalRunRow` per skenario. Mengembalikan jumlah baris yang diinsert."""
    data = json.loads(output_json_path.read_text(encoding="utf-8"))
    results = data["results"]["results"]
    commit_hash = git_commit_hash or _current_git_commit()

    rows = [
        PromptEvalRunRow(
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            git_commit_hash=commit_hash,
            scenario_id=str(
                result.get("description")
                or result.get("vars", {}).get("scenario_id")
                or "unknown"
            ),
            input_payload=result.get("vars", {}),
            output_payload={"output": result.get("response", {}).get("output")},
            verdict="lolos" if result.get("success") else "gagal",
            model=model,
        )
        for result in results
    ]

    with Session(get_engine()) as session:
        session.add_all(rows)
        session.commit()

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("prompt_id")
    parser.add_argument("prompt_version", type=int)
    parser.add_argument("model")
    parser.add_argument("--git-commit-hash", default=None)
    args = parser.parse_args()

    n = push_results(
        args.output_json,
        args.prompt_id,
        args.prompt_version,
        args.model,
        args.git_commit_hash,
    )
    print(f"Berhasil push {n} baris ke prompt_eval_runs")


if __name__ == "__main__":
    main()
