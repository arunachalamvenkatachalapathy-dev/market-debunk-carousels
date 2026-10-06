"""Static guards that catch crashes before a scheduled run does."""
import ast
import pathlib
import py_compile

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {".git", "venv", ".venv", "v", "node_modules", "__pycache__"}
PY_FILES = sorted(p for p in ROOT.rglob("*.py") if not (set(p.relative_to(ROOT).parts) & SKIP))


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_python_compiles(path):
    py_compile.compile(str(path), doraise=True)


@pytest.mark.parametrize("path", PY_FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_literal_braces_in_fstrings(path):
    """An f-string such as f'{"myth":"..."}' raises ValueError at run time (this crashed every
    Tamil carousel run for days). Literal JSON braces inside f-strings must be doubled."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FormattedValue):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                problems.append(f"line {node.lineno}: literal string interpolated in f-string")
            spec = node.format_spec
            if spec is not None:
                for part in getattr(spec, "values", []):
                    if isinstance(part, ast.Constant) and isinstance(part.value, str) and ('"' in part.value or "'" in part.value):
                        problems.append(f"line {node.lineno}: quote characters inside an f-string format spec")
    assert not problems, f"{path.name}: " + "; ".join(problems)


WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_workflow_is_valid(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))
    assert triggers, "workflow has no triggers"
    assert "workflow_dispatch" in triggers
    if path.name != "tests.yml":
        assert "schedule" in triggers and triggers["schedule"][0].get("cron")
    assert data.get("jobs"), "workflow has no jobs"
    for job in data["jobs"].values():
        assert job.get("steps"), "job has no steps"


def test_requirements_present():
    reqs = (ROOT / "requirements.txt").read_text()
    for name in ("google-genai", "playwright", "Jinja2", "Pillow"):
        assert name.lower() in reqs.lower()


def test_templates_exist():
    assert (ROOT / "src/templates/carousel_slide.html").exists()
    assert (ROOT / "src/templates/carousel_slide.css").exists()


def test_config_has_no_hardcoded_secret_defaults():
    import re
    text = (ROOT / "src" / "config.py").read_text(encoding="utf-8")
    for m in re.finditer(r'os\.getenv\("([A-Z_]*(?:KEY|TOKEN|SECRET|_ID)[A-Z_]*)",\s*"([^"]{8,})"\)', text):
        raise AssertionError(f"{m.group(1)} has a hardcoded default; use a GitHub secret")
