"""Unit tests for `app.llm.prompt_loader.PromptLoader`."""

from pathlib import Path

import pytest

from app.llm.exceptions import PromptNotFoundError, PromptRenderError
from app.llm.models import PromptContext
from app.llm.prompt_loader import PromptLoader


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    (tmp_path / "greeting").mkdir()
    (tmp_path / "shared").mkdir()
    (tmp_path / "shared" / "footer.txt").write_text(
        "Best regards,\n{{sender_name}}", encoding="utf-8"
    )
    (tmp_path / "greeting" / "hello.txt").write_text(
        "Hello {{name}}, welcome to {{company}}.\n\n{{> shared/footer}}", encoding="utf-8"
    )
    (tmp_path / "greeting" / "circular_a.txt").write_text(
        "{{> greeting/circular_b}}", encoding="utf-8"
    )
    (tmp_path / "greeting" / "circular_b.txt").write_text(
        "{{> greeting/circular_a}}", encoding="utf-8"
    )
    return tmp_path


def test_load_reads_raw_template(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    raw = loader.load("greeting", "hello")
    assert "{{name}}" in raw
    assert "{{> shared/footer}}" in raw


def test_load_missing_template_raises(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    with pytest.raises(PromptNotFoundError):
        loader.load("greeting", "does_not_exist")


def test_render_substitutes_variables_and_partials(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    context = PromptContext(
        category="greeting",
        name="hello",
        variables={"name": "Jordan", "company": "Acme", "sender_name": "The Team"},
    )
    rendered = loader.render("greeting", "hello", context)
    assert rendered == "Hello Jordan, welcome to Acme.\n\nBest regards,\nThe Team"


def test_render_raises_on_missing_variable(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    context = PromptContext(category="greeting", name="hello", variables={"name": "Jordan"})
    with pytest.raises(PromptRenderError):
        loader.render("greeting", "hello", context)


def test_render_raises_on_circular_partial(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    context = PromptContext(category="greeting", name="circular_a", variables={})
    with pytest.raises(PromptRenderError):
        loader.render("greeting", "circular_a", context)


def test_placeholders_returns_sorted_unique_names(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    names = loader.placeholders("greeting", "hello")
    assert names == ["company", "name", "sender_name"]


def test_validate_template_matches_placeholders(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)
    assert loader.validate_template("greeting", "hello") == loader.placeholders("greeting", "hello")


def test_real_prompt_templates_render_without_missing_placeholders() -> None:
    loader = PromptLoader("prompts")
    names = loader.placeholders("resume", "summary_rewrite")
    context = PromptContext(
        category="resume",
        name="summary_rewrite",
        variables={
            "full_name": "Jordan Smith",
            "job_title": "Backend Engineer",
            "current_summary": "Experienced engineer.",
            "job_description": "Build APIs.",
        },
    )
    rendered = loader.render("resume", "summary_rewrite", context)
    assert set(names) == {"full_name", "job_title", "current_summary", "job_description"}
    assert "Jordan Smith" in rendered
