"""Load and validate the bundled milestone and obligation data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROLES = ("provider", "deployer", "gpai_provider", "member_state")
ROLE_LABELS = {
    "provider": "Provider of an AI system",
    "deployer": "Deployer of an AI system",
    "gpai_provider": "Provider of a general-purpose AI model",
    "member_state": "Member State authority",
}
OMNIBUS_VALUES = ("unchanged", "amended", "moved", "new")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class DataError(ValueError):
    """Raised when the bundled data breaks a rule."""


@dataclass(frozen=True)
class Milestone:
    id: str
    date: date
    title: str
    summary: str
    articles: tuple[str, ...]
    applies_to: tuple[str, ...]
    omnibus: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class Obligation:
    id: str
    role: str
    title: str
    articles: tuple[str, ...]
    summary: str
    milestone: str


@dataclass(frozen=True)
class Dataset:
    as_of: date
    sources: dict
    milestones: tuple[Milestone, ...]
    obligations: tuple[Obligation, ...]
    tiers: tuple[dict, ...]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load(data_dir: Path | None = None) -> Dataset:
    """Read, validate and return the dataset."""
    base = Path(data_dir) if data_dir else DATA_DIR
    raw_m = _load_json(base / "milestones.json")
    raw_o = _load_json(base / "obligations.json")

    milestones = tuple(
        Milestone(
            id=m["id"],
            date=date.fromisoformat(m["date"]),
            title=m["title"],
            summary=m["summary"],
            articles=tuple(m["articles"]),
            applies_to=tuple(m["applies_to"]),
            omnibus=m["omnibus"],
            sources=tuple(m["sources"]),
        )
        for m in raw_m["milestones"]
    )
    obligations = tuple(
        Obligation(
            id=o["id"],
            role=o["role"],
            title=o["title"],
            articles=tuple(o["articles"]),
            summary=o["summary"],
            milestone=o["from"],
        )
        for o in raw_o["obligations"]
    )
    dataset = Dataset(
        as_of=date.fromisoformat(raw_m["as_of"]),
        sources=raw_m["sources"],
        milestones=tuple(sorted(milestones, key=lambda m: (m.date, m.id))),
        obligations=obligations,
        tiers=tuple(raw_o["tiers"]),
    )
    problems = validate(dataset)
    if problems:
        raise DataError("; ".join(problems))
    return dataset


def validate(dataset: Dataset) -> list[str]:
    """Return a list of problems; an empty list means the data is sound."""
    problems: list[str] = []
    ids = [m.id for m in dataset.milestones]
    if len(ids) != len(set(ids)):
        problems.append("duplicate milestone ids")
    for m in dataset.milestones:
        if not m.sources:
            problems.append(f"{m.id}: no sources")
        for s in m.sources:
            if s not in dataset.sources:
                problems.append(f"{m.id}: unknown source {s}")
        for r in m.applies_to:
            if r not in ROLES:
                problems.append(f"{m.id}: unknown role {r}")
        if m.omnibus not in OMNIBUS_VALUES:
            problems.append(f"{m.id}: bad omnibus value {m.omnibus}")
        if not m.articles:
            problems.append(f"{m.id}: no articles")
    known = set(ids)
    oids = [o.id for o in dataset.obligations]
    if len(oids) != len(set(oids)):
        problems.append("duplicate obligation ids")
    for o in dataset.obligations:
        if o.role != "all" and o.role not in ROLES:
            problems.append(f"{o.id}: unknown role {o.role}")
        if o.milestone not in known:
            problems.append(f"{o.id}: unknown milestone {o.milestone}")
    for key, src in dataset.sources.items():
        if not src.get("url", "").startswith("https://"):
            problems.append(f"source {key}: url must be https")
    return problems
