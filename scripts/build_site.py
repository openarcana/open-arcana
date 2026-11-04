"""Build the static explorer from canonical records; no network or third-party runtime.

python3 scripts/build_site.py --output _site
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil

import build


def origin_era(value):
    """An origin classification, never a date for an individual practice."""
    if not value or value.lower() == 'unknown':
        return 'undated'
    if any(s in value.lower() for s in ('ancient', 'antiquity', 'bce', 'pre-columbian')):
        return 'before_1900'
    years = re.findall(r'(?<!\d)(1\d{3}|20\d{2})(?!\d)', value)
    if years:
        return 'before_1900' if min(map(int, years)) < 1900 else 'since_1900'
    centuries = re.findall(r'\b(\d{1,2})(?:st|nd|rd|th) century', value)
    if centuries:
        return 'before_1900' if min(map(int, centuries)) <= 19 else 'since_1900'
    return 'undated'


def make_payload():
    package, tables = build.load()
    errors = build.validate(package, tables)
    if errors:
        raise ValueError('\n'.join(errors))
    geography = json.loads((build.ROOT / 'site/geography.json').read_text())
    mappings = geography['traditions']
    ids = {t['id'] for t in tables['traditions']}
    if set(mappings) != ids:
        raise ValueError('Geography mappings must cover exactly the canonical traditions')
    world = json.loads((build.ROOT / 'site/assets/world.json').read_text())
    codes = {c['id'] for c in world['countries']}
    for key, row in mappings.items():
        if (not set(row['countries']) <= codes or len(set(row['countries'])) != len(row['countries'])
                or row['scope'] not in {'country', 'regional', 'worldwide', 'historical'} or not row['basis']):
            raise ValueError(f'Invalid geography mapping: {key}')
    dataset, inputs = build.snapshot(package)
    quality = build.build_quality(tables, dataset)
    for t in tables['traditions']:
        t['geography'] = mappings[t['id']]
        t['origin_era'] = origin_era(t['founded'])
    for name in ('restricted_items', 'disclosures', 'claims', 'sources', 'source_artifacts'):
        for row in tables[name]:
            row['quality_issues'] = [q for q in quality['issues'] if q['table'] == name and q['record_id'] == row['id']]
    return {'dataset': dataset, 'canonical_inputs': inputs, 'tables': tables,
            'geography_note': geography['description'],
            'geography_sha256': hashlib.sha256((build.ROOT / 'site/geography.json').read_bytes()).hexdigest(),
            'counts': {name: len(rows) for name, rows in tables.items()},
            'disclosure_methods': dict(Counter(r['disclosure_method'] for r in tables['disclosures']))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=build.ROOT / '_site')
    args = parser.parse_args()
    destination = args.output.resolve()
    source = build.ROOT / 'site'
    if destination == source or source.is_relative_to(destination) or destination.is_relative_to(source):
        parser.error('Output must be separate from the site source directory and its ancestors')
    payload = make_payload()
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    # Version the small browser assets so a new release cannot mix old filter
    # logic with a fresh page. No bundler or CDN runtime is required.
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    app = (source / 'app.js').read_text().replace("from './lib.mjs'", f"from './lib.mjs?v={digest(source / 'lib.mjs')}'")
    (destination / 'app.js').write_text(app)
    page = (source / 'index.html').read_text().replace('src="./app.js"', f'src="./app.js?v={digest(destination / "app.js")}"')
    page = page.replace('href="./style.css"', f'href="./style.css?v={digest(source / "style.css")}"')
    (destination / 'index.html').write_text(page)
    (destination / 'data.json').write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    (destination / '.nojekyll').touch()
    print(f"Built {destination}: {payload['counts']['disclosures']} disclosures, "
          f"{payload['counts']['restricted_items']} restricted items; snapshot {payload['dataset']['snapshot_sha256'][:12]}")


if __name__ == '__main__':
    main()
