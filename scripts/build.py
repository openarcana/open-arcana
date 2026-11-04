"""Validate the Open Arcana CSVs against schema/datapackage.json and build exports.

Usage: python3 scripts/build.py [--check]

--check only validates. Otherwise writes to exports/:
  open-arcana.sqlite   all tables, relational
  disclosures.jsonl    one denormalized record per disclosure (AI-friendly)
  claims.jsonl         one record per claim, with its sources inlined
  *.parquet            one per table, only if pyarrow is installed
  SHA256SUMS           checksums of every export
and CATALOG.md at the repository root, a human-readable view of the data.
"""
import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "datapackage.json"
EXPORTS = ROOT / "exports"


def load():
    package = json.loads(SCHEMA.read_text(encoding="utf-8"))
    tables = {}
    for res in package["resources"]:
        path = (SCHEMA.parent / res["path"]).resolve()
        with path.open(newline="", encoding="utf-8") as f:
            tables[res["name"]] = list(csv.DictReader(f))
    return package, tables


def validate(package, tables):
    errors = []
    for res in package["resources"]:
        name, schema = res["name"], res["schema"]
        rows = tables[name]
        expected = [f["name"] for f in schema["fields"]]
        if rows and list(rows[0].keys()) != expected:
            errors.append(f"{name}: columns {list(rows[0].keys())} != {expected}")
            continue

        seen = set()
        for i, row in enumerate(rows, start=2):  # line 1 is the header
            where = f"{name}.csv line {i}"
            key = row[schema["primaryKey"]]
            if key in seen:
                errors.append(f"{where}: duplicate id {key}")
            seen.add(key)

            for field in schema["fields"]:
                value = row[field["name"]].strip()
                c = field.get("constraints", {})
                if c.get("required") and not value:
                    errors.append(f"{where}: {field['name']} is required")
                if not value:
                    continue
                if "pattern" in c and not re.fullmatch(c["pattern"], value):
                    errors.append(f"{where}: {field['name']}={value!r} does not match {c['pattern']}")
                if "enum" in c and value not in c["enum"]:
                    errors.append(f"{where}: {field['name']}={value!r} not in {c['enum']}")
                if "enum_list" in c:
                    for part in value.split(";"):
                        if part not in c["enum_list"]:
                            errors.append(f"{where}: {field['name']} item {part!r} not in {c['enum_list']}")

        for fk in schema.get("foreignKeys", []):
            ref = fk["reference"]
            targets = {r[ref["fields"]] for r in tables[ref["resource"]]}
            for i, row in enumerate(rows, start=2):
                values = split(row[fk["fields"]]) if fk.get("list") else [row[fk["fields"]]]
                for value in values:
                    if value not in targets:
                        errors.append(f"{name}.csv line {i}: {fk['fields']}={value!r} not found in {ref['resource']}")

    for i, c in enumerate(tables.get("claims", []), start=2):
        where = f"claims.csv line {i}"
        supporting, contradicting = split(c["supporting_source_ids"]), split(c["contradicting_source_ids"])
        if set(supporting) & set(contradicting):
            errors.append(f"{where}: a source cannot both support and contradict a claim")
        if c["claim_support"] == "independently_corroborated" and len(supporting) < 2:
            errors.append(f"{where}: independently_corroborated needs two or more supporting sources")
        if c["claim_support"] == "single_source" and not supporting:
            errors.append(f"{where}: single_source needs a supporting source")
        if c["claim_support"] == "contradicted" and not contradicting:
            errors.append(f"{where}: contradicted needs a contradicting source")
        if c["claim_type"] == "suppression" and not c["suppression_method"]:
            errors.append(f"{where}: suppression claims need a suppression_method")
        if c["claim_type"] != "suppression" and c["suppression_method"]:
            errors.append(f"{where}: suppression_method is only for suppression claims")
    return errors


def split(value):
    return [v for v in value.split(";") if v]


def denormalize(tables):
    traditions = {r["id"]: r for r in tables["traditions"]}
    items = {r["id"]: r for r in tables["restricted_items"]}
    sources = {r["id"]: r for r in tables["sources"]}
    for d in tables["disclosures"]:
        item = items[d["item_id"]]
        yield {
            **d,
            "item": item,
            "tradition": traditions[item["tradition_id"]],
            "source": sources[d["source_id"]],
        }


def denormalize_claims(tables):
    items = {r["id"]: r for r in tables["restricted_items"]}
    sources = {r["id"]: r for r in tables["sources"]}
    for c in tables["claims"]:
        yield {
            **c,
            "item": items[c["item_id"]],
            "supporting_sources": [sources[s] for s in split(c["supporting_source_ids"])],
            "contradicting_sources": [sources[s] for s in split(c["contradicting_source_ids"])],
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
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("*", "\\*").replace("_", "\\_")


def words(value):
    """Turn a vocabulary value (or ;-list of them) into readable text."""
    return ", ".join(v.replace("_", " ") for v in value.split(";")) if value else ""


def source_links(source):
    """Links for a source's identifiers, plus its url unless an identifier already points there."""
    links, urls = [], set()
    for pair in filter(None, source["identifiers"].split(";")):
        prefix, value = pair.split(":", 1)
        url = ID_URLS[prefix].format(value)
        urls.add(url.rstrip("/"))
        links.append(f"[{ID_LABELS[prefix]} `{value}`]({url})")
    url = source["url"]
    if url and not any(url.rstrip("/").startswith(u) for u in urls):
        links.insert(0, f"[{url.split('/')[2]}]({url})")
    return links


def read_url(source):
    """The best link to a readable copy: the source's url, else the first identifier that is not Wikidata."""
    if source["url"]:
        return source["url"]
    for pair in filter(None, source["identifiers"].split(";")):
        prefix, value = pair.split(":", 1)
        if prefix != "wikidata":
            return ID_URLS[prefix].format(value)
    return ""


def cite(source):
    """A source's title linked to its catalogue entry, followed by a direct link to a copy if there is one."""
    url = read_url(source)
    link = f" ([{url.split('/')[2].removeprefix('www.')}]({url}))" if url else " (no online copy)"
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
                f"`{item['id']}` · {words(item['secrecy_type'])} · currently {item['current_status']}",
                "",
                md(item["description"]),
                "",
                f"- **Restricted to:** {md(item['restricted_to'])}",
                f"- **How:** {words(item['restriction_mechanism'])}",
                f"- **Stated reason:** {md(item['stated_reason'])}",
            ]
            if item["notes"]:
                out.append(f"- **Notes:** {md(item['notes'])}")
            out.append("")

            discs = sorted(disc_by_item.get(item["id"], []), key=lambda d: (d["year"], d["id"]))
            if not discs:
                out += ["*No disclosure recorded yet.*", ""]
            else:
                out += [
                    "| Year | Method | Extent | Coverage | Source | Source authenticity | Notes |",
                    "|---|---|---|---|---|---|---|",
                ]
            for d in discs:
                s = sources[d["source_id"]]
                year = ("c. " if d["date_precision"] == "circa" else "") + d["year"]
                review = "" if d["review_status"] == "unreviewed" else f" ({d['review_status']})"
                out.append(
                    f"| {year} | {words(d['disclosure_method'])} | {d['extent']} | {md(d['coverage'])} "
                    f"| {cite(s)} | {s['source_authenticity']} | {md(d['notes'])}{review} |"
                )
            if discs:
                out.append("")

            claims = claims_by_item.get(item["id"], [])
            if claims:
                out += ["**Claims**", ""]
            for c in claims:
                period = f" ({md(c['period'])})" if c["period"] else ""
                method = f" ({words(c['suppression_method'])})" if c["suppression_method"] else ""
                review = "" if c["review_status"] == "unreviewed" else f" · {c['review_status']}"
                out.append(f"- `{c['id']}` *{words(c['claim_type'])}*{method} · **{words(c['claim_support'])}**{review}: "
                           f"{md(c['statement'])}{period}")
                for label, field in (("Supported by", "supporting_source_ids"), ("Contradicted by", "contradicting_source_ids")):
                    ids = split(c[field])
                    if ids:
                        out.append(f"  - {label}: " + " · ".join(
                            cite(sources[i]) for i in ids))
                if c["locators"]:
                    out.append(f"  - Where: {md(c['locators'])}")
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
        cited = sorted({d["item_id"] for d in disc_by_src.get(s["id"], [])})
        if cited:
            out.append("- **Discloses:** " + " · ".join(
                f"[{md(items[i]['name'])}](#{anchor(i)})" for i in cited))
        claimed = sorted({c["id"] for c in claims_by_src.get(s["id"], [])})
        if claimed:
            out.append("- **Cited in claims:** " + " · ".join(f"`{c}`" for c in claimed))
        out.append("")

    path.write_text("\n".join(out), encoding="utf-8")


def write_sqlite(package, tables, path):
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    for res in package["resources"]:
        cols = [f["name"] for f in res["schema"]["fields"]]
        pk = res["schema"]["primaryKey"]
        fks = "".join(
            f", FOREIGN KEY ({fk['fields']}) REFERENCES {fk['reference']['resource']}({fk['reference']['fields']})"
            for fk in res["schema"].get("foreignKeys", [])
            if not fk.get("list")
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
    db.commit()
    db.close()


def write_parquet(tables):
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        print("pyarrow not installed: skipping Parquet")
        return
    for name, rows in tables.items():
        pq.write_table(pa.Table.from_pylist(rows), EXPORTS / f"{name}.parquet")


def main():
    package, tables = load()
    errors = validate(package, tables)
    for e in errors:
        print("ERROR", e)
    counts = ", ".join(f"{len(rows)} {name}" for name, rows in tables.items())
    if errors:
        sys.exit(f"{len(errors)} validation error(s) ({counts})")
    print(f"valid: {counts}")
    if "--check" in sys.argv:
        return

    EXPORTS.mkdir(exist_ok=True)
    write_sqlite(package, tables, EXPORTS / "open-arcana.sqlite")
    with (EXPORTS / "disclosures.jsonl").open("w", encoding="utf-8") as f:
        for record in denormalize(tables):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (EXPORTS / "claims.jsonl").open("w", encoding="utf-8") as f:
        for record in denormalize_claims(tables):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    write_parquet(tables)
    write_catalog(tables, ROOT / "CATALOG.md")

    sums = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(EXPORTS.iterdir())
        if p.is_file() and p.name != "SHA256SUMS"
    ]
    (EXPORTS / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"wrote {len(sums)} export(s) to {EXPORTS.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
