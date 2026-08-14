"""Loader untuk daftar role_title yang dikenal sistem (lihat roles.yaml)."""

from functools import lru_cache
from pathlib import Path

import yaml

_ROLES_FILE = Path(__file__).resolve().parent / "roles.yaml"


@lru_cache(maxsize=1)
def load_valid_roles() -> frozenset[str]:
    with open(_ROLES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return frozenset(data["roles"])
