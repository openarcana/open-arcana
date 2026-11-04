"""Validate the Open Arcana CSVs against schema/datapackage.json and build exports.

Usage: python3 scripts/build.py [--check]

--check only validates. Otherwise writes to exports/:
  open-arcana.sqlite   all tables, relational
  disclosures.jsonl    one denormalized record per disclosure (AI-friendly)
  *.parquet            one per table, only if pyarrow is installed
  SHA256SUMS           checksums of every export
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
                if row[fk["fields"]] not in targets:
                    errors.append(f"{name}.csv line {i}: {fk['fields']}={row[fk['fields']]!r} not found in {ref['resource']}")
    return errors


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


def write_sqlite(package, tables, path):
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
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
    write_parquet(tables)

    sums = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(EXPORTS.iterdir())
        if p.is_file() and p.name != "SHA256SUMS"
    ]
    (EXPORTS / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    print(f"wrote {len(sums)} export(s) to {EXPORTS.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
