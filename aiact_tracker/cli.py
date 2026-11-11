"""Command line interface: aiact next | by-role | check | build."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import __version__, render
from .data import DataError, ROLES, ROLE_LABELS, load

README_START = "<!-- timeline:start -->"
README_END = "<!-- timeline:end -->"


def _parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not an ISO date (YYYY-MM-DD): {text}") from exc


def readme_block(dataset) -> str:
    return "\n".join(
        [
            README_START,
            render.markdown_table(dataset, dataset.as_of),
            README_END,
        ]
    )


def replace_block(text: str, block: str) -> str:
    start = text.index(README_START)
    end = text.index(README_END) + len(README_END)
    return text[:start] + block + text[end:]


def cmd_next(args) -> int:
    dataset = load()
    as_of = args.as_of or date.today()
    upcoming = [m for m in render.milestone_rows(dataset, as_of, args.role) if m.date > as_of]
    if not upcoming:
        print("No later milestones in the data.")
        return 0
    first = upcoming[0].date
    for m in upcoming:
        if m.date != first and not args.all:
            break
        print(f"{m.date.isoformat()}  {m.title}  (in {(m.date - as_of).days} days; Articles {', '.join(m.articles)})")
    return 0


def cmd_by_role(args) -> int:
    dataset = load()
    as_of = args.as_of or dataset.as_of
    print(f"{ROLE_LABELS[args.role]}\n")
    print(render.markdown_table(dataset, as_of, args.role))
    if args.role != "member_state":
        print()
        print(render.obligations_markdown(dataset, args.role))
    return 0


def cmd_check(args) -> int:
    try:
        dataset = load()
    except DataError as exc:
        print(f"data problem: {exc}", file=sys.stderr)
        return 1
    root = Path(args.root)
    problems = []
    timeline = root / "docs" / "timeline.md"
    calendar = root / "dist" / "ai-act-timeline.ics"
    readme = root / "README.md"
    if not timeline.exists() or timeline.read_text(encoding="utf-8") != render.timeline_markdown(dataset):
        problems.append("docs/timeline.md is out of date; run: aiact build")
    if not calendar.exists() or calendar.read_bytes() != render.ics(dataset).encode("utf-8"):
        problems.append("dist/ai-act-timeline.ics is out of date; run: aiact build")
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        if README_START in text and replace_block(text, readme_block(dataset)) != text:
            problems.append("README.md timeline block is out of date; run: aiact build")
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        return 1
    print(f"ok: {len(dataset.milestones)} milestones, data as of {dataset.as_of.isoformat()}")
    return 0


def cmd_build(args) -> int:
    dataset = load()
    root = Path(args.root)
    (root / "docs").mkdir(exist_ok=True)
    (root / "dist").mkdir(exist_ok=True)
    (root / "docs" / "timeline.md").write_text(render.timeline_markdown(dataset), encoding="utf-8")
    with (root / "dist" / "ai-act-timeline.ics").open("w", encoding="utf-8", newline="") as handle:
        handle.write(render.ics(dataset))
    readme = root / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        if README_START in text:
            readme.write_text(replace_block(text, readme_block(dataset)), encoding="utf-8")
    print("built docs/timeline.md, dist/ai-act-timeline.ics and the README block")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aiact", description="EU AI Act timeline and obligations by role.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_next = sub.add_parser("next", help="show the next milestone")
    p_next.add_argument("--role", choices=ROLES)
    p_next.add_argument("--as-of", type=_parse_date, help="date to measure from (default: today)")
    p_next.add_argument("--all", action="store_true", help="list every later milestone")
    p_next.set_defaults(func=cmd_next)

    p_role = sub.add_parser("by-role", help="milestones and obligations for one role")
    p_role.add_argument("role", choices=ROLES)
    p_role.add_argument("--as-of", type=_parse_date)
    p_role.set_defaults(func=cmd_by_role)

    p_check = sub.add_parser("check", help="validate the data and confirm generated files are current")
    p_check.add_argument("--root", default=".")
    p_check.set_defaults(func=cmd_check)

    p_build = sub.add_parser("build", help="regenerate docs/timeline.md, the calendar file and the README block")
    p_build.add_argument("--root", default=".")
    p_build.set_defaults(func=cmd_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except DataError as exc:
        print(f"data problem: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
