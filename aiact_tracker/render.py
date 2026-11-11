"""Render the dataset as Markdown and as an iCalendar file."""

from __future__ import annotations

from datetime import date, timedelta

from .data import Dataset, Milestone, ROLE_LABELS

OMNIBUS_LABELS = {
    "unchanged": "",
    "amended": "amended by the Omnibus",
    "moved": "moved by the Omnibus",
    "new": "added by the Omnibus",
}


def long_date(d: date) -> str:
    return f"{d.day} {d.strftime('%B %Y')}"


def status(m: Milestone, as_of: date) -> str:
    if m.date <= as_of:
        return "in force"
    days = (m.date - as_of).days
    return f"in {days} days"


def milestone_rows(dataset: Dataset, as_of: date, role: str | None = None) -> list[Milestone]:
    rows = list(dataset.milestones)
    if role:
        rows = [m for m in rows if role in m.applies_to]
    return rows


def markdown_table(dataset: Dataset, as_of: date, role: str | None = None) -> str:
    lines = [
        "| Date | Status | What applies | Articles | Omnibus |",
        "| --- | --- | --- | --- | --- |",
    ]
    for m in milestone_rows(dataset, as_of, role):
        arts = ", ".join(m.articles)
        lines.append(
            f"| {long_date(m.date)} | {status(m, as_of)} | {m.title} | {arts} | "
            f"{OMNIBUS_LABELS[m.omnibus] or 'no change'} |"
        )
    return "\n".join(lines)


def timeline_markdown(dataset: Dataset) -> str:
    as_of = dataset.as_of
    out = [
        "# EU AI Act timeline",
        "",
        f"Status as of {long_date(as_of)}. Generated from `data/milestones.json`; do not edit by hand.",
        "",
    ]
    for m in dataset.milestones:
        out.append(f"## {long_date(m.date)}: {m.title}")
        out.append("")
        out.append(f"Status: {status(m, as_of)}.")
        out.append("")
        out.append(m.summary)
        out.append("")
        out.append("Applies to: " + ", ".join(ROLE_LABELS[r] for r in m.applies_to) + ".")
        out.append("")
        out.append("Articles: " + ", ".join(m.articles) + ".")
        out.append("")
        label = OMNIBUS_LABELS[m.omnibus]
        if label:
            out.append(f"Digital Omnibus: {label}.")
            out.append("")
        out.append("Sources: " + "; ".join(
            f"[{dataset.sources[s]['title']}]({dataset.sources[s]['url']})" for s in m.sources
        ))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def obligations_markdown(dataset: Dataset, role: str) -> str:
    by_id = {m.id: m for m in dataset.milestones}
    rows = [o for o in dataset.obligations if o.role in (role, "all")]
    lines = ["| Obligation | Articles | Applies from | What it means |", "| --- | --- | --- | --- |"]
    for o in sorted(rows, key=lambda o: (by_id[o.milestone].date, o.id)):
        lines.append(
            f"| {o.title} | {', '.join(o.articles)} | {long_date(by_id[o.milestone].date)} | {o.summary} |"
        )
    return "\n".join(lines)


def _fold(line: str) -> str:
    """Fold a content line at 75 octets as RFC 5545 asks."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts: list[str] = []
    current = ""
    for ch in line:
        limit = 75 if not parts else 74
        if len((current + ch).encode("utf-8")) > limit:
            parts.append(current)
            current = ch
        else:
            current += ch
    parts.append(current)
    return "\r\n ".join(parts)


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def ics(dataset: Dataset) -> str:
    """Build an all-day-event calendar. The stamp comes from the data's as_of date, so output is stable."""
    stamp = dataset.as_of.strftime("%Y%m%d") + "T000000Z"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//eu-ai-act-tracker//EN",
        "CALSCALE:GREGORIAN",
        "X-WR-CALNAME:EU AI Act milestones",
    ]
    for m in dataset.milestones:
        end = m.date + timedelta(days=1)
        desc = f"{m.summary} Articles: {', '.join(m.articles)}. Source: {dataset.sources[m.sources[0]]['url']}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{m.id}@eu-ai-act-tracker",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{m.date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
            f"SUMMARY:{_escape(m.title)}",
            f"DESCRIPTION:{_escape(desc)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
