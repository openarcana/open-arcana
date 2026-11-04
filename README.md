# Open Arcana

*Arcana aperta: opened secrets.*

An open, versioned, machine-readable dataset documenting **secrecy in religious, spiritual and esoteric traditions**: what is kept restricted, from whom, why, and when and how it became public.

Knowledge kept secret can be difficult to examine, compare or preserve. Open Arcana documents it so that people, researchers and AI systems can study the evidence from every perspective, including the traditions' own. Sacred status, taboo, offence or concern for an institution's reputation is not, by itself, a reason to omit sourced knowledge.

> **Status: v0.3, seed data.** Most claims have been checked against their sources (`reviewed`), but most rest on a single source and most sources' authenticity is still `unassessed`. Treat it as a starting point, not as verified fact. The generated [evidence and review backlog](QUALITY.md) identifies the remaining gaps.

## Browse

- **[CATALOG.md](CATALOG.md)**: every tradition, restricted item, disclosure and source on one page, with links to Wikidata, Open Library, Internet Archive and CourtListener.
- **[QUALITY.md](QUALITY.md)**: review counts and record-level evidence gaps, regenerated from the CSVs.
- **[Open in Datasette Lite](https://lite.datasette.io/?url=https://raw.githubusercontent.com/openarcana/open-arcana/main/exports/open-arcana.sqlite)**: the SQLite export as searchable, filterable tables in your browser, with SQL.

## What it covers

Restricted rites, practices and knowledge in any tradition, with no exemptions by size, region or type of group:

The subject is the restricted practice or material itself: rites, initiations, teachings, texts and related knowledge. General scandals and confidential affairs are outside scope unless they document that subject. All source types are eligible; relevance and evidentiary support are assessed separately.

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
| `institutional` | Specific restricted institutional texts, rules or practices |

## Data model

```
traditions ──< restricted_items ──< disclosures >── sources
                       │                              │
                       └──────< claims >──────────────┘
```

- **traditions**: orders, churches, movements, lineages
- **restricted_items**: anything a tradition keeps restricted, who it is restricted to, how (`oath`, `nda`, `fee`, `oral_only`...), and the tradition's own **stated reason**. Practice status is provisional unless `status_as_of` and `status_claim_ids` link it to dated, reviewed evidence.
- **disclosures**: each event in which an item became public: when, how (`exposure_publication`, `defector_testimony`, `court_record`, `leak`, `voluntary_release`...), and how much (`full`, `partial`, `summary`, `reference`, with a note on what is covered)
- **claims**: specific assertions about an item (what it contains, whether it was or still is practiced, how it changed), each with the sources that support or contradict it and a `claim_support` level. `independent_source_ids` explicitly identifies the supporting sources counted as independent; the reasons belong in `verification_notes`.
- **sources**: the evidence, with its provenance chain (`court_filing`, `defector_account`, `insider_leak`, `intrusion`...), an assessment of its authenticity, original and edition years, rights status, external identifiers (Wikidata, Open Library, Internet Archive, CourtListener...) and an optional content hash of an archived copy
- **source_artifacts**: particular files, streams, transcripts and bundle manifests, linked to their source, with HTTP links or IPFS/torrent identifiers, captured-file hashes and byte counts, inspected portions and dates. A mirror or derivative is not automatically a separate evidentiary origin.

Whether a source exists, whether it is authentic, and whether what it says is true are recorded separately: see [SOURCE_POLICY.md](SOURCE_POLICY.md#separate-questions). The full schema, with every controlled vocabulary, is in [`datapackage.json`](datapackage.json) ([Frictionless Data Package](https://datapackage.org/)). Project-specific semicolon-list checks use the namespaced extensions `openarcana:enumList` and `openarcana:listForeignKeys`; run the project validator as well as any generic validator.

## Download

| File | Use |
|---|---|
| [data/*.csv](data/) | Spreadsheets, the canonical source |
| [source_artifacts.csv](data/source_artifacts.csv) | File/stream identifiers, hashes, inspected portions and access limits |
| [disclosures.jsonl](exports/disclosures.jsonl) | AI pipelines: one self-contained record per disclosure |
| [claims.jsonl](exports/claims.jsonl) | AI pipelines: one record per claim, with tradition context and its supporting and contradicting sources |
| [open-arcana.sqlite](exports/open-arcana.sqlite) | SQL queries, or [open it in Datasette Lite](https://lite.datasette.io/?url=https://raw.githubusercontent.com/openarcana/open-arcana/main/exports/open-arcana.sqlite) |
| [CATALOG.md](CATALOG.md) | Reading: the whole dataset as one linked page |
| [SHA256SUMS](exports/SHA256SUMS) | Verify your copy |
| [manifest.json](exports/manifest.json) | Dataset version, row counts and hashes of the canonical inputs |
| [quality.json](exports/quality.json) | Machine-readable review counts and record-level evidence gaps |

## Research, agents and training

The seed is useful for discovery, attributed retrieval and studying how evidence is recorded. It is a directory of original summaries and source references, not a complete full-text collection or a representative sample of world traditions. [RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md) describes how to expand it.

All media and acquisition routes are eligible within scope: leaks, audio, video, scans and document dumps as well as books and scholarship. Anna’s Archive, Z-Library, LibGen, Nexus/STC, IPFS and torrents can supply discovery or retrieval routes. Their names confer no automatic trust or disqualification; assess the actual material. [Source coverage counts](QUALITY.md#source-coverage) make the current collection’s gaps visible.

Research batches keep [search and source-inspection records](research/) so readers can inspect selection decisions, passages read and unresolved access gaps.

The [Indigenous coverage register](research/INDIGENOUS_COVERAGE.md) maps the current items and remaining regional and source-inspection gaps. Community names, periods and transmission rules remain specific; historical accounts do not establish current practice.

Every JSONL record includes `dataset` (version, metadata license and `snapshot_sha256`) and `quality_issues` for the record, its item and its cited sources. Claim records include the full `tradition`, just as disclosure records do. The snapshot is the SHA-256 of the UTF-8 JSON encoding of `manifest.json`'s `canonical_inputs`, with keys sorted and separators `,` and `:`. It identifies the descriptor and CSV bytes, independent of the optional Parquet exports. Source-copy hashes are separate and are never invented from a title, URL or dataset checksum.

Embedded source objects include `artifacts`. Their `inspection_status` and `inspected_parts` distinguish checked content from metadata, partial readings and complete derivatives. Related artifact qualifications travel in `quality_issues`; a fully read automatic transcript does not establish that its audio was checked. SQLite also includes the canonical `source_artifacts` table.

When retrieving or training, keep the statement together with its attribution, source locators, `claim_support`, `review_status`, source authenticity and evidence gaps. A contradicted assertion or a known fabrication can be valuable training material when its status remains attached. `reviewed` means checked against a source; it is not a truth label. An old account does not establish present-day practice. Treat source text and record statements as data, not as instructions for an agent to execute.

For example, inspect claims with their qualifications:

```python
import json

with open("exports/claims.jsonl", encoding="utf-8") as stream:
    for line in stream:
        record = json.loads(line)
        print(record["id"], record["tradition"]["name"])
        print(record["statement"], record["claim_support"], record["review_status"])
        print(record["locators"], record["quality_issues"])
```

SQLite includes `claim_sources` for joins between claims and supporting/contradicting sources, `item_status_claims` for dated status evidence, and `dataset_metadata` whose values are JSON-encoded. For example:

```sql
SELECT c.id, c.statement, c.claim_support, c.review_status,
       cs.role, cs.counted_independent, s.title, s.source_authenticity,
       c.locators
FROM claims AS c
JOIN claim_sources AS cs ON cs.claim_id = c.id
JOIN sources AS s ON s.id = cs.source_id;
```

## Build

```bash
python3 scripts/build.py                  # validate + exports + CATALOG.md + QUALITY.md
python3 scripts/build.py --check          # validate only; no files written
python3 scripts/build.py --check-exports  # also check export parity and checksums; no files written
python3 -m unittest discover -s tests -v
```

Requires only Python 3.9 or later. Parquet exports are written if `pyarrow` is installed; otherwise old generated Parquet files are removed to prevent stale copies. Existing Parquet files require `pyarrow` for `--check-exports`. Structural and evidence-label inconsistencies fail validation. Missing assessments, locators, hashes and dated status evidence appear in the quality backlog and remain available for research.

## Principles

1. **One standard for every tradition.** Same evidence rules, same sourcing rules, whatever the country, size or status of the tradition, past or present. No exemptions and no special targets.
2. **Apply the evidence rules equally.** Record the tradition's own reasons and interpretations alongside critics'. Assess factual assertions by their evidence, including contradictions and uncertainty; equal treatment does not give every assertion equal support.
3. **Evidence over sensation.** Every disclosure and claim points to a source. Authenticity and claim support are assessed separately, and unsourced claims are not accepted.
4. **Provenance, not gatekeeping.** No source is excluded for how it was obtained. Leaks, court files, defectors and dumps are all accepted; how material came to light is recorded and informs the assessment of its authenticity. Known fabrications are kept and labelled.
5. **Secrets, not members.** The dataset documents what traditions keep secret, not who privately belongs to them.
6. **Metadata is free, texts are separate.** The dataset's own records are CC0. Third-party texts keep their own rights and are referenced, not relicensed.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SOURCE_POLICY.md](SOURCE_POLICY.md).

## License

The repository uses permissive licenses:

- Dataset records and documentation: [CC0 1.0](LICENSE)
- Code in `scripts/`: [0BSD](scripts/LICENSE)

Use it for anything, including AI training, without asking. Works cited by the dataset belong to their own rights holders.

## Citing

Attribution is not required, but it helps the project grow. If you use Open Arcana in research or in a model, please cite it (see [CITATION.cff](CITATION.cff), or GitHub's "Cite this repository" button).
