"""Checks on the written material: no long dashes, working links, required files."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "build"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".toml", ".txt", ".ics", ".cff", ""}
LONG_DASHES = (chr(0x2014), chr(0x2013))


def text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        if any(part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES:
            yield path


def test_no_long_dashes_anywhere():
    bad = []
    for path in text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(d in text for d in LONG_DASHES):
            bad.append(str(path.relative_to(ROOT)))
    assert not bad, bad


def test_markdown_relative_links_resolve():
    link = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
    problems = []
    for path in ROOT.rglob("*.md"):
        if SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        for target in link.findall(path.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            target = target.split("#")[0]
            if target and not (path.parent / target).exists():
                problems.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not problems, problems


def test_required_files_exist():
    for name in ("README.md", "LICENSE", "CONTRIBUTING.md", ".gitignore", "pyproject.toml",
                 ".github/workflows/test.yml", "data/milestones.json", "data/obligations.json",
                 "docs/timeline.md", "dist/ai-act-timeline.ics"):
        assert (ROOT / name).is_file(), name


def test_licence_year_and_holder():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in text and "Copyright (c) 2026 Puliyappottammal Jijesh" in text


def test_readme_follows_the_house_structure():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.splitlines()[0] == "# eu-ai-act-tracker"
    order = ["**Problem:**", "**For:**", "**Demonstrates:**", "## What it does", "## Quick start",
             "## How it is built", "## Design choices", "## Limitations", "## Verification status",
             "## Roadmap", "## Licence"]
    positions = [readme.index(m) for m in order]
    assert positions == sorted(positions)
    assert "not legal advice" in readme.lower()
    assert "Last verified:" in readme


def test_readme_counts_match_the_data():
    import json
    m = json.loads((ROOT / "data" / "milestones.json").read_text(encoding="utf-8"))
    assert "twelve dates" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(m["milestones"]) == 12


def test_last_verified_matches_data_as_of():
    import json
    m = json.loads((ROOT / "data" / "milestones.json").read_text(encoding="utf-8"))
    y, mo, d = m["as_of"].split("-")
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
              "October", "November", "December"]
    expected = f"Last verified: {int(d)} {months[int(mo) - 1]} {y}"
    assert expected in (ROOT / "README.md").read_text(encoding="utf-8")
