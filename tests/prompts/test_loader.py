from pathlib import Path

import pytest

from src.prompts import loader

_FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _use_fixtures_root(monkeypatch):
    monkeypatch.setattr(loader, "_PROMPTS_ROOT", _FIXTURES_ROOT)
    loader.load_prompt.cache_clear()


def test_load_prompt_parses_frontmatter():
    prompt = loader.load_prompt("dummy.test")

    assert prompt.id == "dummy.test"
    assert prompt.version == 3
    assert prompt.milestone == "0.0"
    assert prompt.model_compat == ["dummy-model"]


def test_render_with_feedback_includes_conditional_block():
    prompt = loader.load_prompt("dummy.test")

    rendered = prompt.render(subjek="X", feedback="perbaiki Y", daftar=["a", "b"])

    assert "Catatan revisi: perbaiki Y" in rendered


def test_render_without_feedback_omits_conditional_block():
    prompt = loader.load_prompt("dummy.test")

    rendered = prompt.render(subjek="X", daftar=["a", "b"])

    assert "Catatan revisi" not in rendered
    assert "- a" in rendered
    assert "- b" in rendered


def test_load_prompt_unknown_id_raises_explicit_error():
    with pytest.raises(loader.PromptNotFoundError):
        loader.load_prompt("tidak.ada")
