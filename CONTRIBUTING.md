# Contributing

Thanks for taking an interest. This is a small, sourced reference: standard library only, deterministic output, and neutral practitioner wording. Changes should keep it that way.

## Ground rules

1. **Every date needs a source.** Add the source to the `sources` map in `data/milestones.json` and reference it from the milestone. Prefer the Official Journal on EUR-Lex; the consolidated text in a named tool is acceptable if you say so.
2. **Say what you checked.** In your pull request, quote the article and paragraph the change rests on and when you read it.
3. **Not legal advice.** Describe what the Regulation says. Do not advise on whether a particular system or organisation is caught.
4. **Standard library only** for the `aiact_tracker` package. Test tooling is fine under the `dev` extra.
5. **Deterministic output.** Generated files must be byte-identical for the same data. Do not read the clock in anything that is committed.
6. **No real data.** There is nothing here about any organisation or person, and nothing should be added.
7. **British English, plain tone, no long dashes.** A test fails if an em dash or en dash appears in any text file.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

## Changing a date or an entry

Edit `data/milestones.json` or `data/obligations.json`, then regenerate and check:

```bash
aiact build
aiact check
python -m pytest -q
```

Update the "Last verified" line in the README and add an entry under Unreleased in `CHANGELOG.md`.

## Reporting a changed date

If you think a date has moved, open a "Correction" issue with a link to the official page. A pointer to the article is enough; the fix can be made from there.
