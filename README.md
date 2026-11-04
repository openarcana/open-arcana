# Open Arcana

*Arcana aperta: opened secrets.*

An open, versioned, machine-readable dataset documenting **secrecy in religious, spiritual and esoteric traditions**: what is kept restricted, from whom, why, and when and how it became public.

Secret knowledge carries authority largely because it is hidden. Open Arcana makes it possible to look at that knowledge as it is: to study it, compare it across traditions, preserve it before it is lost, and let people, researchers and AI systems reason about it from every perspective, including the traditions' own.

> **Status: v0.2, seed data.** Most claims have been checked against their sources (`reviewed`), but nearly all rest on a single source and most sources' authenticity is still `unassessed`. Treat it as a starting point, not as verified fact.

## Browse

- **[CATALOG.md](CATALOG.md)**: every tradition, restricted item, disclosure and source on one page, with links to Wikidata, Open Library, Internet Archive and CourtListener.
- **[Open in Datasette Lite](https://lite.datasette.io/?url=https://raw.githubusercontent.com/openarcana/open-arcana/main/exports/open-arcana.sqlite)**: the SQLite export as searchable, filterable tables in your browser, with SQL.

## What it covers

Any form of secrecy, in any tradition, with no exemptions by size, region or type of group:

| `secrecy_type` | Examples |
|---|---|
| `initiatory_rite` | Degree ceremonies, initiations, oaths |
| `graded_doctrine` | Teachings released level by level |
| `restricted_scripture` | Texts reserved to a class of believers |
| `transmitted_technique` | Mantras, meditation methods, empowerments |
| `words_of_power` | Divine names, passwords, signs, grips |
| `closed_liturgy` | Worship closed to outsiders |
| `restricted_oral_knowledge` | Knowledge restricted by gender, age, clan or role |
| `hidden_cosmology` | Myths or cosmologies revealed only to insiders |
| `internal_governance` | Manuals and policies hidden from members |
| `institutional` | Finances, cover-ups, internal discipline |

## Data model

```
traditions ──< restricted_items ──< disclosures >── sources
                       │                              │
                       └──────< claims >──────────────┘
```

- **traditions**: orders, churches, movements, lineages
- **restricted_items**: anything a tradition keeps restricted, who it is restricted to, how (`oath`, `nda`, `fee`, `oral_only`...), and the tradition's own **stated reason**
- **disclosures**: each event in which an item became public: when, how (`exposure_publication`, `defector_testimony`, `court_record`, `leak`, `voluntary_release`...), and how much (`full`, `partial`, `summary`, `reference`, with a note on what is covered)
- **claims**: specific assertions about an item (what it contains, whether it was or still is practiced, how it changed), each with the sources that support or contradict it and a `claim_support` level
- **sources**: the evidence, with its provenance chain (`court_filing`, `defector_account`, `insider_leak`, `intrusion`...), an assessment of its authenticity, original and edition years, rights status, external identifiers (Wikidata, Open Library, Internet Archive, CourtListener...) and an optional content hash of an archived copy

Whether a source exists, whether it is authentic, and whether what it says is true are recorded separately: see [SOURCE_POLICY.md](SOURCE_POLICY.md#separate-questions). The full schema, with every controlled vocabulary, is in [`schema/datapackage.json`](schema/datapackage.json) ([Frictionless Data Package](https://datapackage.org/)).

## Download

| File | Use |
|---|---|
| `data/*.csv` | Spreadsheets, the canonical source |
| `exports/disclosures.jsonl` | AI pipelines: one self-contained record per disclosure |
| `exports/claims.jsonl` | AI pipelines: one record per claim, with its supporting and contradicting sources |
| `exports/open-arcana.sqlite` | SQL queries, or [open it in Datasette Lite](https://lite.datasette.io/?url=https://raw.githubusercontent.com/openarcana/open-arcana/main/exports/open-arcana.sqlite) |
| `CATALOG.md` | Reading: the whole dataset as one linked page |
| `exports/SHA256SUMS` | Verify your copy |

## Build

```bash
python3 scripts/build.py          # validate + export + CATALOG.md
python3 scripts/build.py --check  # validate only
```

Requires only Python 3. Parquet exports are written if `pyarrow` is installed.

## Principles

1. **One standard for every tradition.** Same evidence rules, same sourcing rules, whatever the country, size or status of the tradition, past or present. No exemptions and no special targets.
2. **Describe, don't judge.** The tradition's own reasons and interpretations are recorded alongside critics'. The dataset does not decide who is right.
3. **Evidence over sensation.** Every disclosure and claim points to a source. Authenticity and claim support are assessed separately, and unsourced claims are not accepted.
4. **Provenance, not gatekeeping.** No source is excluded for how it was obtained. Leaks, court files, defectors and dumps are all accepted; how material came to light is recorded and informs the assessment of its authenticity. Known fabrications are kept and labelled.
5. **Secrets, not members.** The dataset documents what traditions keep secret, not who privately belongs to them.
6. **Metadata is free, texts are separate.** The dataset's own records are CC0. Third-party texts keep their own rights and are referenced, not relicensed.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SOURCE_POLICY.md](SOURCE_POLICY.md).

## License

Everything in this repository is public domain:

- Dataset records and documentation: [CC0 1.0](LICENSE)
- Code in `scripts/`: [0BSD](scripts/LICENSE)

Use it for anything, including AI training, without asking. Works cited by the dataset belong to their own rights holders.

## Citing

Attribution is not required, but it helps the project grow. If you use Open Arcana in research or in a model, please cite it (see [CITATION.cff](CITATION.cff), or GitHub's "Cite this repository" button).
