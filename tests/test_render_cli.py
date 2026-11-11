from datetime import date

from aiact_tracker import cli, render
from aiact_tracker.data import load

import pytest


def test_status_uses_the_given_date():
    ds = load()
    first = ds.milestones[0]
    assert render.status(first, date(2026, 11, 11)) == "in force"
    last = ds.milestones[-1]
    assert render.status(last, date(2030, 12, 30)) == "in 1 days"


def test_table_for_role_filters_rows():
    ds = load()
    full = render.markdown_table(ds, ds.as_of)
    gpai = render.markdown_table(ds, ds.as_of, "gpai_provider")
    assert gpai.count("\n") < full.count("\n")
    assert "General-purpose AI models placed on the market before" in gpai
    assert "High-risk obligations apply to Annex III" not in gpai


def test_timeline_has_every_milestone_and_a_source_link():
    ds = load()
    text = render.timeline_markdown(ds)
    for m in ds.milestones:
        assert m.title in text
    assert "https://eur-lex.europa.eu/eli/reg/2024/1689/oj" in text


def test_ics_is_well_formed_and_stable():
    ds = load()
    a, b = render.ics(ds), render.ics(ds)
    assert a == b
    assert a.startswith("BEGIN:VCALENDAR\r\n") and a.endswith("END:VCALENDAR\r\n")
    assert a.count("BEGIN:VEVENT") == a.count("END:VEVENT") == len(ds.milestones)
    for line in a.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


def test_ics_unfolds_to_the_original_text():
    ds = load()
    unfolded = render.ics(ds).replace("\r\n ", "")
    assert "DTSTART;VALUE=DATE:20261202" in unfolded
    assert "Articles: 113." in unfolded


def test_ics_escapes_special_characters():
    assert render._escape("a;b,c\nd\\e") == "a\\;b\\,c\\nd\\\\e"


def test_fold_keeps_multibyte_characters_whole():
    line = "X:" + "é" * 100
    folded = render._fold(line)
    assert folded.replace("\r\n ", "") == line
    for part in folded.split("\r\n"):
        part.encode("utf-8").decode("utf-8")
        assert len(part.encode("utf-8")) <= 75


def test_obligations_table_for_role_includes_all_role_rows():
    text = render.obligations_markdown(load(), "deployer")
    assert "Support AI literacy" in text
    assert "Use high-risk systems as instructed" in text
    assert "Document the model and respect copyright" not in text


def test_next_command(capsys):
    assert cli.main(["next", "--as-of", "2026-11-11"]) == 0
    out = capsys.readouterr().out
    assert "2026-12-02" in out and "in 21 days" in out


def test_next_all_for_role(capsys):
    assert cli.main(["next", "--role", "gpai_provider", "--all", "--as-of", "2026-11-11"]) == 0
    out = capsys.readouterr().out
    assert "2027-08-02" in out and "2027-12-02" not in out


def test_next_after_last_milestone(capsys):
    assert cli.main(["next", "--as-of", "2031-01-01"]) == 0
    assert "No later milestones" in capsys.readouterr().out


def test_by_role_command(capsys):
    assert cli.main(["by-role", "deployer"]) == 0
    out = capsys.readouterr().out
    assert "Deployer of an AI system" in out and "Obligation" in out


def test_bad_role_is_rejected():
    with pytest.raises(SystemExit):
        cli.main(["by-role", "wizard"])


def test_bad_date_is_rejected():
    with pytest.raises(SystemExit):
        cli.main(["next", "--as-of", "11/11/2026"])


def test_build_then_check_round_trip(tmp_path, capsys):
    (tmp_path / "README.md").write_text("x\n<!-- timeline:start -->\n<!-- timeline:end -->\n", encoding="utf-8")
    assert cli.main(["check", "--root", str(tmp_path)]) == 1
    assert cli.main(["build", "--root", str(tmp_path)]) == 0
    assert cli.main(["check", "--root", str(tmp_path)]) == 0
    (tmp_path / "docs" / "timeline.md").write_text("stale", encoding="utf-8")
    assert cli.main(["check", "--root", str(tmp_path)]) == 1


def test_committed_generated_files_are_current():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    assert cli.main(["check", "--root", str(root)]) == 0
