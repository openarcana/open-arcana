"""Validate the Open Arcana CSVs against datapackage.json and build exports.

Usage: python3 scripts/build.py [--check | --check-exports]

--check validates; --check-exports also verifies generated files. Neither writes
project outputs. With no flags, writes to exports/:
  open-arcana.sqlite   all tables, relational
  disclosures.jsonl    one denormalized record per disclosure (AI-friendly)
  claims.jsonl         one record per claim, with its sources inlined
  *.parquet            one per table, only if pyarrow is installed
  quality.json         evidence gaps and review counts (not a truth score)
  manifest.json        dataset version and canonical-input hashes
  SHA256SUMS           checksums of every export
and CATALOG.md and QUALITY.md at the repository root.
"""
import argparse
import csv
import hashlib
import html
import json
import re
import sqlite3
import sys
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit

from quality import build_quality, record_issues, write_quality_markdown

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "datapackage.json"


def resource_path(resource, descriptor):
    """The builder reads local files inside the package, including through symlinks."""
    value = resource["path"]
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or "\\" in value or urlsplit(value).scheme
            or any(p in ("", ".", "..") or p.startswith(".") for p in value.split("/"))):
        raise ValueError(f"{resource['name']}: resource path must be a relative child of the descriptor")
    resolved = (descriptor.parent / value).resolve()
    if not resolved.is_relative_to(descriptor.parent.resolve()):
        raise ValueError(f"{resource['name']}: resource path resolves outside the package")
    return resolved


def load(descriptor=None):
    descriptor = descriptor or SCHEMA
    package = json.loads(descriptor.read_text(encoding="utf-8"))
    tables = {}
    for res in package["resources"]:
        path = resource_path(res, descriptor)
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, strict=True)
            expected = [field["name"] for field in res["schema"]["fields"]]
            if reader.fieldnames != expected:
                raise ValueError(f"{res['name']}: columns {reader.fieldnames} != {expected}")
            tables[res["name"]] = list(reader)
    return package, tables


def is_web_url(value):
    try:
        parsed = urlsplit(value)
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None
                and not any(c.isspace() or ord(c) < 32 or c in "<>\\" for c in value)
                and (parsed.port is None or 0 < parsed.port < 65536))
    except ValueError:
        return False


def validate(package, tables):
    errors = []
    # Reject malformed rows before traversing their relationships.
    for res in package["resources"]:
        name = res["name"]
        expected = [f["name"] for f in res["schema"]["fields"]]
        if name not in tables:
            errors.append(f"{name}: missing table")
            continue
        for i, row in enumerate(tables[name], start=2):
            if list(row) != expected or any(not isinstance(v, str) for v in row.values()):
                errors.append(f"{name}.csv record {i}: malformed row; expected {len(expected)} string cells")
    if errors:
        return errors

    for res in package["resources"]:
        name, schema = res["name"], res["schema"]
        rows = tables[name]
        seen = set()
        for i, row in enumerate(rows, start=2):  # line 1 is the header
            where = f"{name}.csv line {i}"
            key = row[schema["primaryKey"]]
            if key in seen:
                errors.append(f"{where}: duplicate id {key}")
            seen.add(key)

            for field in schema["fields"]:
                value = row[field["name"]].strip()
                if value != row[field["name"]]:
                    errors.append(f"{where}: {field['name']} has leading or trailing whitespace")
                c = field.get("constraints", {})
                if c.get("required") and not value:
                    errors.append(f"{where}: {field['name']} is required")
                if not value:
                    continue
                if "pattern" in c and not re.fullmatch(c["pattern"], value):
                    errors.append(f"{where}: {field['name']}={value!r} does not match {c['pattern']}")
                if "enum" in c and value not in c["enum"]:
                    errors.append(f"{where}: {field['name']}={value!r} not in {c['enum']}")
                if "openarcana:enumList" in field:
                    for part in value.split(";"):
                        if part not in field["openarcana:enumList"]:
                            errors.append(f"{where}: {field['name']} item {part!r} is not an allowed list value")

        keys = [(fk, False) for fk in schema.get("foreignKeys", [])]
        keys += [(fk, True) for fk in schema.get("openarcana:listForeignKeys", [])]
        for fk, is_list in keys:
            ref = fk["reference"]
            targets = {r[ref["fields"]] for r in tables[ref["resource"]]}
            for i, row in enumerate(rows, start=2):
                raw = row[fk["fields"]]
                values = split(raw) if is_list else [raw]
                if is_list and raw:
                    if any(not part or part != part.strip() for part in raw.split(";")):
                        errors.append(f"{name}.csv line {i}: {fk['fields']} has an empty or padded list entry")
                    if len(values) != len(set(values)):
                        errors.append(f"{name}.csv line {i}: {fk['fields']} has duplicate source/claim ids")
                for value in values:
                    if value not in targets:
                        errors.append(f"{name}.csv line {i}: {fk['fields']}={value!r} not found in {ref['resource']}")

    for i, c in enumerate(tables.get("claims", []), start=2):
        where = f"claims.csv line {i}"
        supporting, contradicting = split(c["supporting_source_ids"]), split(c["contradicting_source_ids"])
        independent = set(split(c["independent_source_ids"]))
        if not supporting and not contradicting:
            errors.append(f"{where}: every claim needs at least one source, including insufficient claims")
        if not independent.issubset(supporting):
            errors.append(f"{where}: independent_source_ids must be a subset of supporting_source_ids")
        if set(supporting) & set(contradicting):
            errors.append(f"{where}: a source cannot both support and contradict a claim")
        if contradicting and c["claim_support"] != "contradicted":
            errors.append(f"{where}: contradicting sources require contradicted claim_support")
        if len(independent) >= 2 and c["claim_support"] == "single_source":
            errors.append(f"{where}: single_source cannot declare two independent supporting sources")
        if c["claim_support"] == "independently_corroborated":
            if len(independent) < 2:
                errors.append(f"{where}: independently_corroborated needs two or more distinct independent_source_ids")
            if contradicting:
                errors.append(f"{where}: independently_corroborated cannot have contradicting sources")
            if c["review_status"] != "reviewed" or not c["verification_notes"] or not c["locators"]:
                errors.append(f"{where}: independently_corroborated needs review, locators and an independence assessment")
        if c["claim_support"] == "single_source" and not supporting:
            errors.append(f"{where}: single_source needs a supporting source")
        if c["claim_support"] == "contradicted" and not contradicting:
            errors.append(f"{where}: contradicted needs a contradicting source")
        if c["claim_type"] == "suppression" and not c["suppression_method"]:
            errors.append(f"{where}: suppression claims need a suppression_method")
        if c["claim_type"] != "suppression" and c["suppression_method"]:
            errors.append(f"{where}: suppression_method is only for suppression claims")
        if c["claim_type"] == "current_practice" and not c["period"]:
            errors.append(f"{where}: current_practice needs a period; it must not imply undated present-day practice")

    for i, s in enumerate(tables.get("sources", []), start=2):
        if s["url"] and not is_web_url(s["url"]):
            errors.append(f"sources.csv line {i}: url must be an absolute HTTP(S) URL without credentials")
        if s["source_authenticity"] != "unassessed" and not s["verification_notes"]:
            errors.append(f"sources.csv line {i}: assessed authenticity needs verification_notes")

    for i, artifact in enumerate(tables.get("source_artifacts", []), start=2):
        where = f"source_artifacts.csv line {i}"
        if artifact["url"] and not is_web_url(artifact["url"]):
            errors.append(f"{where}: url must be an absolute HTTP(S) URL without credentials")
        if not any(artifact[field] for field in ("url", "ipfs_cid", "btih", "sha256")):
            errors.append(f"{where}: an artifact needs a URL or content identifier")
        if bool(artifact["sha256"]) != bool(artifact["size_bytes"]):
            errors.append(f"{where}: a captured sha256 and size_bytes must be supplied together")
        try:
            date.fromisoformat(artifact["accessed_on"])
        except ValueError:
            errors.append(f"{where}: accessed_on is not a valid calendar date")

    claims = {c["id"]: c for c in tables.get("claims", [])}
    for i, item in enumerate(tables.get("restricted_items", []), start=2):
        where = f"restricted_items.csv line {i}"
        if bool(item["status_as_of"]) != bool(item["status_claim_ids"]):
            errors.append(f"{where}: status_as_of and status_claim_ids must be supplied together")
        if item["status_as_of"]:
            try:
                date.fromisoformat(item["status_as_of"])
            except ValueError:
                errors.append(f"{where}: status_as_of is not a valid calendar date")
        for claim_id in split(item["status_claim_ids"]):
            c = claims.get(claim_id)
            if not c:
                continue  # Already reported by the list foreign-key check.
            expected_type = {"practiced": "current_practice", "modified": "change", "discontinued": "change"}.get(item["current_status"])
            if (c["item_id"] != item["id"] or c["review_status"] != "reviewed"
                    or c["claim_support"] not in ("single_source", "independently_corroborated")
                    or not c["period"] or c["claim_type"] != expected_type):
                errors.append(f"{where}: {claim_id} must be a reviewed, supported, dated status claim for this item")
    return errors


def split(value):
    return [v for v in value.split(";") if v]


def sources_with_artifacts(tables):
    artifacts = {}
    for artifact in tables.get("source_artifacts", []):
        artifacts.setdefault(artifact["source_id"], []).append(artifact)
    return {source["id"]: {**source, "artifacts": artifacts.get(source["id"], [])}
            for source in tables["sources"]}


def denormalize(tables, dataset=None, quality=None):
    traditions = {r["id"]: r for r in tables["traditions"]}
    items = {r["id"]: r for r in tables["restricted_items"]}
    sources = sources_with_artifacts(tables)
    for d in tables["disclosures"]:
        item = items[d["item_id"]]
        yield {
            **d,
            "item": item,
            "tradition": traditions[item["tradition_id"]],
            "source": sources[d["source_id"]],
            "dataset": dataset or {},
            "quality_issues": record_issues(quality, "disclosures", d["id"], item, [d["source_id"]]),
        }


def denormalize_claims(tables, dataset=None, quality=None):
    traditions = {r["id"]: r for r in tables["traditions"]}
    items = {r["id"]: r for r in tables["restricted_items"]}
    sources = sources_with_artifacts(tables)
    for c in tables["claims"]:
        yield {
            **c,
            "item": items[c["item_id"]],
            "tradition": traditions[items[c["item_id"]]["tradition_id"]],
            "supporting_sources": [sources[s] for s in split(c["supporting_source_ids"])],
            "contradicting_sources": [sources[s] for s in split(c["contradicting_source_ids"])],
            "dataset": dataset or {},
            "quality_issues": record_issues(quality, "claims", c["id"], items[c["item_id"]],
                                            split(c["supporting_source_ids"]) + split(c["contradicting_source_ids"])),
        }


ID_URLS = {
    "wikidata": "https://www.wikidata.org/wiki/{}",
    "ol": "https://openlibrary.org/works/{}",
    "ia": "https://archive.org/details/{}",
    "oclc": "https://search.worldcat.org/title/{}",
    "isbn": "https://openlibrary.org/isbn/{}",
    "doi": "https://doi.org/{}",
    "courtlistener": "https://www.courtlistener.com/opinion/{}/",
}
ID_LABELS = {
    "wikidata": "Wikidata", "ol": "Open Library", "ia": "Internet Archive",
    "oclc": "WorldCat", "isbn": "ISBN", "doi": "DOI", "courtlistener": "CourtListener",
}


def md(text):
    """Escape a CSV value for a Markdown table cell or inline text."""
    text = html.escape(text, quote=False)
    for char in ("\\", "|", "*", "_", "[", "]", "`"):
        text = text.replace(char, "\\" + char)
    return text.replace("\r\n", "\n").replace("\n", "<br>")


def identifier_url(prefix, value):
    return ID_URLS[prefix].format(quote(value, safe="/" if prefix == "doi" else ""))


def link_url(url):
    return quote(url, safe=":/?&=%+#@;,~!$'*")


def words(value):
    """Turn a vocabulary value (or ;-list of them) into readable text."""
    return ", ".join(v.replace("_", " ") for v in value.split(";")) if value else ""


def source_links(source):
    """Links for a source's identifiers, plus its url unless an identifier already points there."""
    links, urls = [], set()
    for pair in filter(None, source["identifiers"].split(";")):
        prefix, value = pair.split(":", 1)
        url = identifier_url(prefix, value)
        urls.add(url.rstrip("/"))
        links.append(f"[{ID_LABELS[prefix]} {md(value)}]({link_url(url)})")
    url = source["url"]
    if url and url.rstrip("/") not in urls:
        links.insert(0, f"[{md(urlsplit(url).netloc)}]({link_url(url)})")
    return links


def read_url(source):
    """A source or catalogue link; a bibliographic link does not guarantee a readable copy."""
    if source["url"]:
        return source["url"]
    for pair in filter(None, source["identifiers"].split(";")):
        prefix, value = pair.split(":", 1)
        if prefix != "wikidata":
            return identifier_url(prefix, value)
    return ""


def cite(source):
    """A source's title linked to its catalogue entry, followed by a direct link to a copy if there is one."""
    url = read_url(source)
    link = f" ([{md(urlsplit(url).netloc.removeprefix('www.'))}]({link_url(url)}))" if url else " (no link recorded)"
    return f"[{md(source['title'])}](#{anchor(source['id'])}){link}"


def anchor(record_id):
    return record_id.lower()


def write_catalog(tables, path):
    """Write a human-readable Markdown catalogue, with every identifier as a link."""
    sources = {r["id"]: r for r in tables["sources"]}
    items_by_trad, disc_by_item, disc_by_src, claims_by_item, claims_by_src = {}, {}, {}, {}, {}
    for item in tables["restricted_items"]:
        items_by_trad.setdefault(item["tradition_id"], []).append(item)
    for d in tables["disclosures"]:
        disc_by_item.setdefault(d["item_id"], []).append(d)
        disc_by_src.setdefault(d["source_id"], []).append(d)
    for c in tables["claims"]:
        claims_by_item.setdefault(c["item_id"], []).append(c)
        for sid in split(c["supporting_source_ids"]) + split(c["contradicting_source_ids"]):
            claims_by_src.setdefault(sid, []).append(c)
    items = {r["id"]: r for r in tables["restricted_items"]}
    source_artifacts = sources_with_artifacts(tables)

    out = [
        "# Open Arcana catalogue",
        "",
        "<!-- Generated by scripts/build.py from data/*.csv. Do not edit by hand. -->",
        "",
        "> Generated from [`data/`](data/) by `scripts/build.py`. Edit the CSVs, not this file. "
        "Records marked *unreviewed* have not been checked yet.",
        "",
        f"{len(tables['traditions'])} traditions · {len(tables['restricted_items'])} restricted items · "
        f"{len(tables['disclosures'])} disclosures · {len(tables['claims'])} claims · {len(tables['sources'])} sources",
        "",
        "Review means a record was checked, not that it is true. Source authenticity and claim support "
        "are separate assessments. See the [evidence and review backlog](QUALITY.md).",
        "",
        "## Traditions",
        "",
    ]
    for t in tables["traditions"]:
        n = len(items_by_trad.get(t["id"], []))
        out.append(f"- [{md(t['name'])}](#{anchor(t['id'])}) ({n} item{'s' * (n != 1)})")
    out += ["- [Sources](#sources)", ""]

    for t in tables["traditions"]:
        out += [f'<a id="{anchor(t["id"])}"></a>', "", f"## {md(t['name'])}", ""]
        meta = [f"`{t['id']}`", words(t["tradition_type"]), f"founded {md(t['founded'])}",
                md(t["region"]), t["status"]]
        if t["wikidata"]:
            meta.append(f"[Wikidata `{t['wikidata']}`]({ID_URLS['wikidata'].format(t['wikidata'])})")
        out += [" · ".join(m for m in meta if m), ""]
        if t["notes"]:
            out += [md(t["notes"]), ""]

        for item in items_by_trad.get(t["id"], []):
            out += [f'<a id="{anchor(item["id"])}"></a>', "", f"### {md(item['name'])}", ""]
            out += [
                f"`{item['id']}` · {words(item['secrecy_type'])} · recorded status: {item['current_status']}",
                "",
                md(item["description"]),
                "",
                f"- **Restricted to:** {md(item['restricted_to'])}",
                f"- **How:** {words(item['restriction_mechanism'])}",
                f"- **Stated reason:** {md(item['stated_reason'])}",
            ]
            if item["status_as_of"]:
                out.append(f"- **Status evidence as of:** {item['status_as_of']} · claims "
                           + ", ".join(f"`{claim_id}`" for claim_id in split(item["status_claim_ids"]))
                           + ". This does not establish present-day practice.")
            elif item["current_status"] != "unknown":
                out.append("- **Status evidence:** provisional; no dated status claims linked.")
            if item["notes"]:
                out.append(f"- **Notes:** {md(item['notes'])}")
            out.append("")

            discs = sorted(disc_by_item.get(item["id"], []), key=lambda d: (d["year"], d["id"]))
            if not discs:
                out += ["*No disclosure recorded yet.*", ""]
            else:
                out += [
                    "| Year | Method | Extent | Coverage | Source | Source authenticity | Review | Notes |",
                    "|---|---|---|---|---|---|---|---|",
                ]
            for d in discs:
                s = sources[d["source_id"]]
                year = ("c. " if d["date_precision"] == "circa" else "") + d["year"]
                out.append(
                    f"| {year} | {words(d['disclosure_method'])} | {d['extent']} | {md(d['coverage'])} "
                    f"| {cite(s)} | {s['source_authenticity']} | {d['review_status']} | {md(d['notes'])} |"
                )
            if discs:
                out.append("")

            claims = claims_by_item.get(item["id"], [])
            if claims:
                out += ["**Claims**", ""]
            for c in claims:
                period = f" ({md(c['period'])})" if c["period"] else ""
                method = f" ({words(c['suppression_method'])})" if c["suppression_method"] else ""
                review = f" · {c['review_status']}"
                out.append(f"- `{c['id']}` *{words(c['claim_type'])}*{method} · **{words(c['claim_support'])}**{review}: "
                           f"{md(c['statement'])}{period}")
                for label, field in (("Supported by", "supporting_source_ids"), ("Contradicted by", "contradicting_source_ids")):
                    ids = split(c[field])
                    if ids:
                        out.append(f"  - {label}: " + " · ".join(
                            cite(sources[i]) for i in ids))
                if c["locators"]:
                    out.append(f"  - Where: {md(c['locators'])}")
                if c["independent_source_ids"]:
                    out.append("  - Counted as independent: " + ", ".join(
                        f"`{sid}`" for sid in split(c["independent_source_ids"])))
                if c["verification_notes"]:
                    out.append(f"  - Assessment: {md(c['verification_notes'])}")
            if claims:
                out.append("")

    out += ["## Sources", ""]
    for s in tables["sources"]:
        out += [f'<a id="{anchor(s["id"])}"></a>', "", f"### {md(s['title'])}", ""]
        out += [
            " · ".join(filter(None, [f"`{s['id']}`", md(s["author"]), md(s["original_year"]), words(s["source_type"])])),
            "",
            f"- **Provenance:** {' → '.join(words(p) for p in split(s['provenance']))}",
            f"- **Authenticity:** {s['source_authenticity']}",
        ]
        if s["verification_notes"]:
            out.append(f"- **Verification:** {md(s['verification_notes'])}")
        out.append(f"- **Rights:** {words(s['rights'])}")
        if s["edition_year"]:
            out.append(f"- **Linked copy:** {s['edition_year']} edition")
        links = source_links(s)
        if links:
            out.append("- **Links:** " + " · ".join(links))
        if s["content_hash"]:
            out.append(f"- **Archived copy hash:** `{s['content_hash']}`")
        if s["notes"]:
            out.append(f"- **Notes:** {md(s['notes'])}")
        for artifact in source_artifacts[s["id"]]["artifacts"]:
            location = f"[open]({link_url(artifact['url'])})" if artifact["url"] else "no HTTP link recorded"
            out.append(f"- **Artifact `{artifact['id']}`:** {words(artifact['artifact_kind'])}; "
                       f"{artifact['inspection_status']}; {location}; inspected {artifact['accessed_on']}")
            out.append(f"  - Inspected: {md(artifact['inspected_parts'])}")
            for field in ("media_type", "member_path", "size_bytes", "sha256", "ipfs_cid", "btih"):
                if artifact[field]:
                    out.append(f"  - {field}: {md(artifact[field])}")
            out.append(f"  - Notes: {md(artifact['notes'])}")
        cited = sorted({d["item_id"] for d in disc_by_src.get(s["id"], [])})
        if cited:
            out.append("- **Discloses:** " + " · ".join(
                f"[{md(items[i]['name'])}](#{anchor(i)})" for i in cited))
        claimed = sorted({c["id"] for c in claims_by_src.get(s["id"], [])})
        if claimed:
            out.append("- **Cited in claims:** " + " · ".join(f"`{c}`" for c in claimed))
        out.append("")

    path.write_text("\n".join(out), encoding="utf-8")


def write_sqlite(package, tables, path, dataset=None):
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    for res in package["resources"]:
        cols = [f["name"] for f in res["schema"]["fields"]]
        pk = res["schema"]["primaryKey"]
        fks = "".join(
            f", FOREIGN KEY ({fk['fields']}) REFERENCES {fk['reference']['resource']}({fk['reference']['fields']})"
            for fk in res["schema"].get("foreignKeys", [])
        )
        db.execute(
            f"CREATE TABLE {res['name']} ("
            + ", ".join(f"{c} TEXT{' PRIMARY KEY' if c == pk else ''}" for c in cols)
            + fks + ")"
        )
        db.executemany(
            f"INSERT INTO {res['name']} VALUES ({', '.join('?' * len(cols))})",
            [[row[c] for c in cols] for row in tables[res["name"]]],
        )
    db.execute("CREATE TABLE claim_sources (claim_id TEXT REFERENCES claims(id), "
               "source_id TEXT REFERENCES sources(id), role TEXT CHECK(role IN ('supporting', 'contradicting')), "
               "counted_independent INTEGER NOT NULL CHECK(counted_independent IN (0, 1)), "
               "PRIMARY KEY (claim_id, source_id, role))")
    for c in tables["claims"]:
        independent = set(split(c["independent_source_ids"]))
        for role in ("supporting", "contradicting"):
            db.executemany("INSERT INTO claim_sources VALUES (?, ?, ?, ?)",
                           [(c["id"], sid, role, int(sid in independent))
                            for sid in split(c[f"{role}_source_ids"])])
    db.execute("CREATE TABLE item_status_claims (item_id TEXT REFERENCES restricted_items(id), "
               "claim_id TEXT REFERENCES claims(id), PRIMARY KEY (item_id, claim_id))")
    db.executemany("INSERT INTO item_status_claims VALUES (?, ?)",
                   [(item["id"], cid) for item in tables["restricted_items"]
                    for cid in split(item["status_claim_ids"])])
    db.execute("CREATE TABLE dataset_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.executemany("INSERT INTO dataset_metadata VALUES (?, ?)",
                   [(key, json.dumps(value, ensure_ascii=False)) for key, value in (dataset or {}).items()])
    db.commit()
    db.close()


def write_parquet(package, tables, exports):
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("pyarrow not installed: skipping Parquet")
        # A previously generated file must not silently describe an older snapshot.
        for name in tables:
            (exports / f"{name}.parquet").unlink(missing_ok=True)
        return []
    names = []
    for resource in package["resources"]:
        name, rows = resource["name"], tables[resource["name"]]
        arrow_schema = pa.schema([(f["name"], pa.string()) for f in resource["schema"]["fields"]])
        pq.write_table(pa.Table.from_pylist(rows, schema=arrow_schema), exports / f"{name}.parquet")
        names.append(f"{name}.parquet")
    return names


def snapshot(package, descriptor=None):
    descriptor = descriptor or SCHEMA
    inputs = {descriptor.name: hashlib.sha256(descriptor.read_bytes()).hexdigest()}
    for res in package["resources"]:
        inputs[res["path"]] = hashlib.sha256(resource_path(res, descriptor).read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dataset = {"name": package["name"], "version": package["version"],
               "metadata_license": "CC0-1.0", "snapshot_sha256": digest}
    return dataset, inputs


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_outputs(package, tables, output_root, dataset, inputs, parquet=True):
    exports = output_root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    quality = build_quality(tables, dataset)
    write_sqlite(package, tables, exports / "open-arcana.sqlite", dataset)
    for name, records in (("disclosures", denormalize(tables, dataset, quality)),
                          ("claims", denormalize_claims(tables, dataset, quality))):
        with (exports / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_json(exports / "quality.json", quality)
    write_json(exports / "manifest.json", {"dataset": dataset, "canonical_inputs": inputs,
                                           "counts": quality["counts"],
                                           "source_text_rights": "Separate from metadata; see each source and SOURCE_POLICY.md."})
    write_catalog(tables, output_root / "CATALOG.md")
    write_quality_markdown(quality, output_root / "QUALITY.md")
    names = ["open-arcana.sqlite", "disclosures.jsonl", "claims.jsonl", "quality.json", "manifest.json"]
    if parquet:
        names += write_parquet(package, tables, exports)
    sums = [f"{hashlib.sha256((exports / name).read_bytes()).hexdigest()}  {name}" for name in sorted(names)]
    (exports / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return names


def sqlite_contents(path):
    """Compare logical contents: SQLite library versions can change file-header bytes."""
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("SQLite foreign-key check failed")
        schema = db.execute("SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name").fetchall()
        rows = {name: db.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                for name, _ in db.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table'")}
        return schema, rows
    finally:
        db.close()


def check_exports(package, tables, dataset, inputs, output_root):
    errors = []
    with tempfile.TemporaryDirectory(prefix="openarcana-check-") as directory:
        expected_root = Path(directory)
        names = write_outputs(package, tables, expected_root, dataset, inputs, parquet=False)
        for name in names + ["CATALOG.md", "QUALITY.md"]:
            relative = Path(name) if name.endswith(".md") else Path("exports") / name
            actual, expected = output_root / relative, expected_root / relative
            if not actual.is_file():
                errors.append(f"missing generated file: {relative}")
            elif name == "open-arcana.sqlite":
                try:
                    if sqlite_contents(actual) != sqlite_contents(expected):
                        errors.append(f"stale generated file: {relative}")
                except (sqlite3.Error, ValueError) as error:
                    errors.append(f"{relative}: {error}")
            elif actual.read_bytes() != expected.read_bytes():
                errors.append(f"stale generated file: {relative}")

        optional = [f"{name}.parquet" for name in tables if (output_root / "exports" / f"{name}.parquet").is_file()]
        if optional:
            try:
                import pyarrow.parquet as pq
            except ImportError:
                errors.append("pyarrow is needed to verify the existing optional Parquet exports")
            else:
                for name in optional:
                    if pq.read_table(output_root / "exports" / name).to_pylist() != tables[Path(name).stem]:
                        errors.append(f"stale generated file: exports/{name}")
        checksum_file = output_root / "exports" / "SHA256SUMS"
        try:
            sums = {}
            for line in checksum_file.read_text(encoding="utf-8").splitlines():
                digest, name = line.split("  ", 1)
                if name in sums or name not in names + optional or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError("unexpected filename, duplicate or invalid digest")
                sums[name] = digest
                path = output_root / "exports" / name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    errors.append(f"checksum mismatch: exports/{name}")
            if set(sums) != set(names + optional):
                errors.append("SHA256SUMS does not cover every generated export")
        except (OSError, ValueError) as error:
            errors.append(f"SHA256SUMS: {error}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="validate without writing")
    modes.add_argument("--check-exports", action="store_true", help="also verify generated files and checksums without writing")
    args = parser.parse_args()
    try:
        package, tables = load()
    except (OSError, ValueError, csv.Error) as error:
        sys.exit(f"ERROR {error}")
    errors = validate(package, tables)
    for e in errors:
        print("ERROR", e)
    counts = ", ".join(f"{len(rows)} {name}" for name, rows in tables.items())
    if errors:
        sys.exit(f"{len(errors)} validation error(s) ({counts})")
    print(f"valid: {counts}")
    dataset, inputs = snapshot(package)
    quality = build_quality(tables, dataset)
    print(f"evidence backlog: {len(quality['issues'])} recorded gaps/qualifications across "
          f"{len(quality['issue_counts'])} checks (see QUALITY.md; not validation failures)")
    if args.check:
        return
    if args.check_exports:
        errors = check_exports(package, tables, dataset, inputs, ROOT)
        for error in errors:
            print("ERROR", error)
        if errors:
            sys.exit(f"{len(errors)} generated-file error(s); run python3 scripts/build.py")
        print("generated files and checksums match canonical inputs")
    else:
        names = write_outputs(package, tables, ROOT, dataset, inputs)
        print(f"wrote {len(names)} export(s) to exports/")


if __name__ == "__main__":
    main()
