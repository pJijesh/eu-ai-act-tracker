import copy
import json
from datetime import date
from pathlib import Path

import pytest

from aiact_tracker import data
from aiact_tracker.data import DataError, load, validate

ROOT = Path(__file__).resolve().parent.parent


def test_bundled_data_loads_and_is_valid():
    ds = load()
    assert len(ds.milestones) == 12
    assert validate(ds) == []


def test_milestones_are_sorted_by_date():
    ds = load()
    dates = [m.date for m in ds.milestones]
    assert dates == sorted(dates)


def test_key_dates_match_the_sources_read():
    ds = {m.id: m.date for m in load().milestones}
    assert ds["entry-into-force"] == date(2024, 8, 1)
    assert ds["prohibitions-and-literacy"] == date(2025, 2, 2)
    assert ds["gpai-and-governance"] == date(2025, 8, 2)
    assert ds["general-application"] == date(2026, 8, 2)
    assert ds["art-50-2-legacy"] == date(2026, 12, 2)
    assert ds["new-prohibitions"] == date(2026, 12, 2)
    assert ds["annex-iii"] == date(2027, 12, 2)
    assert ds["annex-i"] == date(2028, 8, 2)
    assert ds["large-scale-it-legacy"] == date(2030, 12, 31)


def _copy_dataset(tmp_path, mutate_m=None, mutate_o=None):
    m = json.loads((ROOT / "data" / "milestones.json").read_text(encoding="utf-8"))
    o = json.loads((ROOT / "data" / "obligations.json").read_text(encoding="utf-8"))
    if mutate_m:
        mutate_m(m)
    if mutate_o:
        mutate_o(o)
    (tmp_path / "milestones.json").write_text(json.dumps(m), encoding="utf-8")
    (tmp_path / "obligations.json").write_text(json.dumps(o), encoding="utf-8")
    return tmp_path


def test_unknown_source_is_rejected(tmp_path):
    d = _copy_dataset(tmp_path, lambda m: m["milestones"][0].update(sources=["nope"]))
    with pytest.raises(DataError, match="unknown source"):
        load(d)


def test_missing_sources_are_rejected(tmp_path):
    d = _copy_dataset(tmp_path, lambda m: m["milestones"][0].update(sources=[]))
    with pytest.raises(DataError, match="no sources"):
        load(d)


def test_unknown_role_is_rejected(tmp_path):
    d = _copy_dataset(tmp_path, lambda m: m["milestones"][0].update(applies_to=["wizard"]))
    with pytest.raises(DataError, match="unknown role"):
        load(d)


def test_bad_omnibus_value_is_rejected(tmp_path):
    d = _copy_dataset(tmp_path, lambda m: m["milestones"][0].update(omnibus="maybe"))
    with pytest.raises(DataError, match="omnibus"):
        load(d)


def test_duplicate_ids_are_rejected(tmp_path):
    def dup(m):
        m["milestones"].append(copy.deepcopy(m["milestones"][0]))
    with pytest.raises(DataError, match="duplicate milestone"):
        load(_copy_dataset(tmp_path, dup))


def test_non_https_source_is_rejected(tmp_path):
    def bad(m):
        m["sources"]["eurlex-2024-1689"]["url"] = "http://example.invalid"
    with pytest.raises(DataError, match="https"):
        load(_copy_dataset(tmp_path, bad))


def test_obligation_must_point_at_a_real_milestone(tmp_path):
    d = _copy_dataset(tmp_path, mutate_o=lambda o: o["obligations"][0].update({"from": "missing"}))
    with pytest.raises(DataError, match="unknown milestone"):
        load(d)


def test_every_role_has_at_least_one_milestone():
    ds = load()
    for role in data.ROLES:
        assert any(role in m.applies_to for m in ds.milestones), role


def test_fine_tiers_present():
    tiers = {t["id"]: t["max_fine"] for t in load().tiers}
    assert "35 million" in tiers["prohibited"] and "7%" in tiers["prohibited"]
    assert "15 million" in tiers["operator-obligations"] and "3%" in tiers["operator-obligations"]
    assert "7.5 million" in tiers["incorrect-information"] and "1%" in tiers["incorrect-information"]
