# Contributing

You don't need to know git to help.

## Easiest: open an issue

Suggest a source, report an error, or describe a disclosure you know about. Include the source (title, author, year, link if any). We'll turn it into a record.

Identify the specific restricted rite, initiation, practice, teaching or text that it documents. General scandals do not qualify simply because participants wanted them kept secret.

## Adding records directly

1. Edit the CSVs in `data/`. Use the next free id in each file (`TRAD-`, `ITEM-`, `SRC-`, `DISC-`, `CLM-` + 4 digits).
2. Use only the values listed in [`datapackage.json`](datapackage.json) for controlled fields. Every claim, including an `insufficient` claim, must cite at least one source. List source ids once each.
3. Set `review_status` to `unreviewed` and `source_authenticity` to `unassessed`, unless you record the checks behind a different value in `verification_notes`. A maintainer will review it.
4. For `independently_corroborated`, list at least two distinct supporting ids in `independent_source_ids`, give source locators and explain their independence in `verification_notes`. A reviewed assessment is required. Separate publications or court cases do not by themselves establish independent origins. Keep contradicting evidence and choose a support label consistent with it.
5. Link a definite practice status to reviewed claims through `status_claim_ids` and give the date those claims establish in `status_as_of` (`YYYY-MM-DD`). An undated seed status remains provisional. Do not infer present-day practice from historical sources.
6. Run `python3 scripts/build.py --check` and `python3 -m unittest discover -s tests -v`. Fix errors, then run `python3 scripts/build.py` to regenerate the catalogue, quality backlog and exports. Verify with `python3 scripts/build.py --check-exports`.
7. Include the regenerated files in the pull request. Do not edit `CATALOG.md`, `QUALITY.md` or exports by hand.

For a captured file, stream or dump, add a linked `ARTF-` row to `data/source_artifacts.csv`. Record the actual format, URL or content identifier, inspected pages/timestamps/member paths, inspection date and limitations. Pair computed SHA-256 with the exact captured byte count. Keep a transcript or torrent manifest separate from its underlying recording or payload; do not mark the payload inspected from metadata alone. Source format, repository, anonymity and acquisition route do not make a record ineligible.

## Checking existing records

Every new disclosure or claim starts as `unreviewed`. The generated [quality backlog](QUALITY.md) lists records needing source inspection, precise coverage, locators, exact-copy hashes or dated status evidence. Record what you actually checked and distinguish it from reports of a source you have not read. Source hashes must identify the exact captured file; a hash proves file identity, not authenticity or truth.

For broader coverage and overlooked material, follow [RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md). In a research pull request, record the collections, queries, languages and dates searched, what was found, and any unresolved access or verification gaps. An unsuccessful search does not establish that no knowledge or practice exists.

Authorized scholarly access, including The Wikipedia Library, is welcome. Say whether you inspected the actual text, an abstract, a review or only catalogue metadata. Cite stable work URLs or identifiers; keep personal access links and account information out of the records. Summaries must remain your own wording, regardless of how you accessed the source.

## Rules

Read [SOURCE_POLICY.md](SOURCE_POLICY.md). In short: cite a source for everything, write descriptions in your own words, treat every tradition by the same rules (past and present, any size or region), and record how the material was obtained.

## Anonymity

You can contribute from a pseudonymous account. If you need stronger anonymity, ask in an issue (without details) and a private channel will be provided.
