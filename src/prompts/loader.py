"""Loader untuk system prompt tersimpan sebagai file (Manajemen Prompt Fase 2).

Baca file `src/prompts/<path>.md` sesuai `id` (dot-separated -> path relatif
ke folder ini), parse frontmatter YAML + body Jinja2. Hasil parse di-cache
(`@lru_cache`, mirror pola `load_valid_roles()`/`load_role_permissions()`) -
file tidak berubah selama proses hidup, cuma dibaca sekali; `.render()`
tetap dipanggil ulang tiap request dengan variabel yang berbeda. Kontrak
lengkap: docs/01-architecture/rancangan-manajemen-prompt.md.
"""

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml
from jinja2 import Template

_PROMPTS_ROOT = Path(__file__).parent


class PromptNotFoundError(Exception):
    """Prompt dengan `id` yang diberikan tidak ditemukan di src/prompts/."""


@dataclass(frozen=True)
class PromptTemplate:
    id: str
    version: int
    milestone: str
    _jinja_template: Template = field(repr=False, compare=False)
    model_compat: list[str] = field(default_factory=list)
    description: str = ""

    def render(self, **kwargs) -> str:
        return self._jinja_template.render(**kwargs)


def _id_to_path(prompt_id: str) -> Path:
    return (_PROMPTS_ROOT / Path(*prompt_id.split("."))).with_suffix(".md")


def _split_frontmatter(raw: str) -> tuple[str, str]:
    parts = raw.split("---", 2)
    if len(parts) != 3:
        raise ValueError(
            "File prompt harus diawali frontmatter YAML (diapit '---' di baris sendiri)"
        )
    return parts[1], parts[2].strip("\n")


@cache
def load_prompt(prompt_id: str) -> PromptTemplate:
    path = _id_to_path(prompt_id)
    if not path.is_file():
        raise PromptNotFoundError(f"Prompt '{prompt_id}' tidak ditemukan di {path}")

    frontmatter_raw, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    meta = yaml.safe_load(frontmatter_raw)

    return PromptTemplate(
        id=meta["id"],
        version=meta["version"],
        milestone=str(meta.get("milestone", "")),
        model_compat=meta.get("model_compat", []),
        description=meta.get("description", ""),
        # trim_blocks+lstrip_blocks: baris {% for %}/{% endfor %} sendiri tidak
        # ikut menyisakan baris kosong di output - perlu supaya prompt yang
        # py loop (mis. domain_gate) tetap byte-identik dengan versi hardcode
        # f-string lama, bukan cuma "kelihatan mirip".
        _jinja_template=Template(body, trim_blocks=True, lstrip_blocks=True),
    )
