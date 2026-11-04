"""Inspectable evidence-gap checks; these do not grade the truth of a tradition."""
from collections import Counter


def build_quality(tables, dataset):
    issues = []

    def add(table, row, code, message):
        issues.append({"table": table, "record_id": row["id"], "code": code, "message": message})

    for source in tables["sources"]:
        authenticity = source["source_authenticity"]
        if authenticity != "verified":
            add("sources", source, "source_authenticity_" + authenticity,
                f"Source authenticity is {authenticity}; this is separate from the truth of its assertions.")
        if not source["content_hash"]:
            add("sources", source, "source_without_content_hash",
                "No source-level content_hash is recorded; linked artifact hashes may identify excerpts, derivatives or metadata instead.")
        if not source["url"] and not source["identifiers"]:
            add("sources", source, "source_without_link", "No URL or external identifier has been recorded.")
        if source["rights"] == "unknown":
            add("sources", source, "source_rights_unknown", "The source text's rights have not been established.")

    for table in ("claims", "disclosures"):
        for row in tables[table]:
            if row["review_status"] != "reviewed":
                add(table, row, "record_" + row["review_status"],
                    f"Record review status is {row['review_status']}; review is not proof of truth.")
    for claim in tables["claims"]:
        if not claim["locators"]:
            add("claims", claim, "claim_without_locator", "No page, section, exhibit or timestamp is recorded.")
        if not claim["verification_notes"]:
            add("claims", claim, "claim_without_assessment", "No explanation of the claim-support assessment is recorded.")
        if claim["claim_support"] in ("insufficient", "contradicted"):
            add("claims", claim, "claim_" + claim["claim_support"],
                f"Claim support is {claim['claim_support']}; retain that qualification when quoting or training.")
    for disclosure in tables["disclosures"]:
        if not disclosure["coverage"]:
            add("disclosures", disclosure, "disclosure_without_coverage",
                "The parts, version or edition covered by this disclosure have not been specified.")
    for artifact in tables.get("source_artifacts", []):
        if artifact["inspection_status"] != "complete":
            add("source_artifacts", artifact, "artifact_" + artifact["inspection_status"],
                f"Artifact inspection is {artifact['inspection_status']}; use only its recorded inspected portions.")
    artifact_hashes = {}
    for artifact in tables.get("source_artifacts", []):
        if artifact["sha256"]:
            artifact_hashes.setdefault(artifact["sha256"], []).append(artifact)
    for copies in artifact_hashes.values():
        if len({copy["source_id"] for copy in copies}) > 1:
            for artifact in copies:
                add("source_artifacts", artifact, "shared_artifact_bytes",
                    "The same captured bytes are linked to multiple source records; review their dependence and inspected portions before counting independent evidence.")
    for item in tables["restricted_items"]:
        if item["current_status"] != "unknown" and not (item["status_as_of"] and item["status_claim_ids"]):
            add("restricted_items", item, "status_without_dated_evidence",
                "The recorded practice status is provisional: no dated status claims are linked.")

    distributions = {}
    for table, fields in {
        "claims": ("claim_support", "review_status", "claim_type"),
        "disclosures": ("review_status", "extent"),
        "sources": ("source_authenticity", "rights", "source_type", "provenance"),
        "source_artifacts": ("artifact_kind", "inspection_status"),
        "restricted_items": ("current_status",),
        "traditions": ("region", "tradition_type"),
    }.items():
        distributions[table] = {
            field: dict(sorted(Counter(value for row in tables.get(table, [])
                                       for value in (row[field].split(";") if field == "provenance" else [row[field]])).items()))
            for field in fields
        }
    return {
        "dataset": dataset,
        "counts": {table: len(rows) for table, rows in tables.items()},
        "distributions": distributions,
        "issue_counts": dict(sorted(Counter(issue["code"] for issue in issues).items())),
        "issues": issues,
        "artifact_source_ids": {row["id"]: row["source_id"] for row in tables.get("source_artifacts", [])},
        "limitations": [
            "Checks identify recorded evidence gaps, not whether an assertion is true or false.",
            "Source independence and the fit between a status date and its evidence require human review.",
            "Dated practice evidence applies to its stated period, not automatically to the present day.",
            "The seed is a convenience collection, not a representative sample of traditions or secrecy.",
        ],
    }


def record_issues(quality, table, record_id, item, source_ids):
    """Keep qualifications for the record, its item and every cited source together."""
    if quality is None:
        return []
    related = {(table, record_id), ("restricted_items", item["id"])}
    related.update(("sources", source_id) for source_id in source_ids)
    related.update(("source_artifacts", artifact_id) for artifact_id, source_id
                   in quality.get("artifact_source_ids", {}).items() if source_id in source_ids)
    return [issue for issue in quality["issues"] if (issue["table"], issue["record_id"]) in related]


def write_quality_markdown(quality, path):
    # Only identifiers, controlled values and generated messages enter this report.
    lines = [
        "# Evidence and review backlog", "",
        "<!-- Generated by scripts/build.py. Do not edit by hand. -->", "",
        "These checks expose evidence gaps so that people and machines can account for them. "
        "They do not determine truth or make a source ineligible.", "",
        f"Dataset version: `{quality['dataset']['version']}`. "
        f"Canonical snapshot: `{quality['dataset']['snapshot_sha256']}`.", "",
        "Reproduce with `python3 scripts/build.py`. Machine-readable details: "
        "[`exports/quality.json`](exports/quality.json). "
        "Research priorities: [RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md).", "",
        "## Recorded evidence", "",
        "| Measure | Records |", "|---|---|",
    ]
    counts, dist = quality["counts"], quality["distributions"]

    def proportion(n, total):
        return f"{n}/{total} ({n / total:.1%})" if total else "No records"

    for label, n, total in (
        ("Reviewed claims", dist["claims"]["review_status"].get("reviewed", 0), counts["claims"]),
        ("Reviewed disclosures", dist["disclosures"]["review_status"].get("reviewed", 0), counts["disclosures"]),
        ("Claims labelled independently corroborated", dist["claims"]["claim_support"].get("independently_corroborated", 0), counts["claims"]),
        ("Claims labelled single-source", dist["claims"]["claim_support"].get("single_source", 0), counts["claims"]),
        ("Sources with unassessed authenticity", dist["sources"]["source_authenticity"].get("unassessed", 0), counts["sources"]),
        ("Sources without a source-level hash", quality["issue_counts"].get("source_without_content_hash", 0), counts["sources"]),
        ("Items with provisional undated status", quality["issue_counts"].get("status_without_dated_evidence", 0), counts["restricted_items"]),
    ):
        lines.append(f"| {label} | {proportion(n, total)} |")
    lines += ["", "Review status, source authenticity and claim support answer different questions. "
              "A single-source claim can be accurate; corroboration still needs a documented independence assessment.",
              "", "## Source coverage", "",
              "These are collection counts, not trust rankings or eligibility rules. "
              "Formats and provenance can overlap; no balance quota is implied.", ""]
    for label, values in (("Source format", dist["sources"]["source_type"]),
                          ("Provenance", dist["sources"]["provenance"]),
                          ("Artifact inspection", dist["source_artifacts"]["inspection_status"])):
        lines += [f"| {label} | Records |", "|---|---:|"]
        lines += [f"| `{value}` | {count} |" for value, count in values.items()]
        lines.append("")
    lines += ["## Work queue", "",
              "An ID can appear in several checks. Counts overlap and must not be added into an overall quality score.", ""]
    for code, count in quality["issue_counts"].items():
        matches = [issue for issue in quality["issues"] if issue["code"] == code]
        lines += [f"### `{code}` ({count})", "", matches[0]["message"], ""]
        # Link each record to the source CSV; don't assume Markdown claim anchors.
        for table in sorted({issue["table"] for issue in matches}):
            ids = ", ".join(f"`{issue['record_id']}`" for issue in matches if issue["table"] == table)
            lines += [f"[{table}](data/{table}.csv): {ids}", ""]
    lines += ["## Limits", ""]
    lines += [f"- {limit}" for limit in quality["limitations"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
