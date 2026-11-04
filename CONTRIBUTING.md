# Contributing

You don't need to know git to help.

## Easiest: open an issue

Suggest a source, report an error, or describe a disclosure you know about. Include the source (title, author, year, link if any). We'll turn it into a record.

## Adding records directly

1. Edit the CSVs in `data/`. Use the next free id in each file (`TRAD-`, `ITEM-`, `SRC-`, `DISC-`, `CLM-` + 4 digits).
2. Use only the values listed in [`schema/datapackage.json`](schema/datapackage.json) for controlled fields.
3. Set `review_status` to `unreviewed` and `source_authenticity` to `unassessed`, unless you record the checks behind a different value in `verification_notes`. A maintainer will review it.
4. Run `python3 scripts/build.py --check` and fix any errors.
5. Open a pull request.

## Checking existing records

Every record starts as `unreviewed`. The most valuable work right now is taking an unreviewed disclosure, checking it against its source, and either confirming it or opening an issue with a correction. Next most valuable: assessing a source's authenticity, or adding claims, especially ones a second independent source can corroborate or contradict.

## Rules

Read [SOURCE_POLICY.md](SOURCE_POLICY.md). In short: cite a source for everything, write descriptions in your own words, treat every tradition by the same rules (past and present, any size or region), record how the material was obtained, and don't identify private members.

## Anonymity

You can contribute from a pseudonymous account. If you need stronger anonymity, ask in an issue (without details) and a private channel will be provided.
