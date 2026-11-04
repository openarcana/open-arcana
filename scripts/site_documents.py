"""Publish crawlable evidence pages and machine access from validated exports."""
from collections import defaultdict
from html import escape
import hashlib
import json
from pathlib import Path
import shutil
from string import Template
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree as ET

import build

REPOSITORY = 'https://github.com/openarcana/open-arcana'
CC0 = 'https://creativecommons.org/publicdomain/zero/1.0/'
EXPORTS = ('manifest.json', 'quality.json', 'disclosures.jsonl', 'claims.jsonl',
           'open-arcana.sqlite', 'SHA256SUMS')


def site_url():
    value = json.loads((build.ROOT / 'site/config.json').read_text())['url']
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.path not in ('', '/') or parts.query or parts.fragment):
        raise ValueError('The site URL must be an HTTPS origin without credentials, path or query')
    return value.rstrip('/')


def human(value):
    return (value or 'Unknown').replace('_', ' ').capitalize()


def paragraph(value, css=''):
    return f'<p class="{css}">{escape(value or "Not recorded.")}</p>'


def facts(values):
    return '<dl class="document-facts">' + ''.join(
        f'<dt>{escape(label)}</dt><dd>{escape(value or "Not recorded")}</dd>'
        for label, value in values) + '</dl>'


def date_label(record):
    value = record['year']
    if not value:
        return 'Undated'
    year = int(value)
    label = f'{abs(year)} BCE' if year < 0 else str(year)
    return ('c. ' if record['date_precision'] == 'circa' else '') + label


def json_script(value):
    # Catalogue text is untrusted even inside a non-executable JSON script.
    encoded = json.dumps(value, ensure_ascii=False).replace('<', '\\u003c')
    return f'<script type="application/ld+json">{encoded}</script>'


def metadata(title, description, canonical, schema=None):
    values = {'og:type': 'website', 'og:site_name': 'Open Arcana',
              'og:title': title, 'og:description': description, 'og:url': canonical}
    tags = [f'<meta property="{key}" content="{escape(value, quote=True)}">'
            for key, value in values.items()]
    tags.append('<meta name="twitter:card" content="summary">')
    if schema:
        tags.append(json_script(schema))
    return '\n  '.join(tags)


def document(path, title, description, body, origin, schema=None, extra_head='', root_override=None):
    root = root_override or ('../' * len(path.strip('/').split('/')) if path.strip('/') else './')
    canonical = origin + '/' + path
    template = Template((Path(__file__).parent / 'templates/site-page.html').read_text())
    style_version = hashlib.sha256((build.ROOT / 'site/style.css').read_bytes()).hexdigest()[:12]
    return template.substitute(title=escape(title), description=escape(description, quote=True),
                               canonical=escape(canonical, quote=True), root=root,
                               style_version=style_version, body=body,
                               metadata=metadata(title, description, canonical, schema) + extra_head)


def dataset_schema(package, payload, origin):
    downloads = [(r['name'], r['path'], 'text/csv') for r in package['resources']]
    downloads += [('Disclosures with evidence qualifications', 'exports/disclosures.jsonl', 'application/x-ndjson'),
                  ('Claims with supporting and contradicting sources', 'exports/claims.jsonl', 'application/x-ndjson'),
                  ('Relational database', 'exports/open-arcana.sqlite', 'application/vnd.sqlite3'),
                  ('Explorer data and geography', 'data.json', 'application/json')]
    return {'@context': 'https://schema.org', '@type': 'Dataset',
            '@id': origin + '/dataset/#dataset', 'url': origin + '/dataset/',
            'name': 'Open Arcana: restricted rites, initiations, texts and teachings',
            'description': package['description'] + ' CC0 applies to catalogue metadata; cited works retain their own rights. Review, authenticity, claim support and practice status are separate assessments.',
            'version': payload['dataset']['version'],
            'identifier': 'sha256:' + payload['dataset']['snapshot_sha256'],
            'license': CC0, 'isAccessibleForFree': True, 'inLanguage': 'en',
            'keywords': 'religion, esotericism, initiation, ritual, secrecy, restricted knowledge, source verification',
            'creator': {'@type': 'Organization', 'name': 'Open Arcana', 'url': origin + '/', 'sameAs': REPOSITORY},
            'sameAs': REPOSITORY,
            'distribution': [{'@type': 'DataDownload', 'name': name, 'contentUrl': origin + '/' + path,
                              'encodingFormat': mime} for name, path, mime in downloads]}


def source_link(source):
    name = escape(source['title'])
    if source['url']:
        name = f'<a href="{escape(source["url"], quote=True)}" rel="noopener noreferrer">{name} ↗</a>'
    return name + f' <span class="evidence-note">({escape(source["id"])}; authenticity: {escape(human(source["source_authenticity"]))})</span>'


def claim_html(claim):
    body = f'<article class="document-claim" id="{escape(claim["id"])}"><h3>{escape(claim["id"])} · {escape(human(claim["claim_type"]))}</h3>'
    body += paragraph(claim['statement'])
    body += facts([('Claim support', human(claim['claim_support'])),
                   ('Record review', human(claim['review_status'])),
                   ('Period', claim['period']), ('Locators', claim['locators']),
                   ('Sources counted as independent', claim['independent_source_ids'])])
    if claim['suppression_method']:
        body += facts([('Suppression mechanism', claim['suppression_method'].replace(';', ', '))])
    for label, key in [('Supporting sources', 'supporting_sources'), ('Contradicting sources', 'contradicting_sources')]:
        body += f'<h4>{label}</h4><ul>' + ''.join(f'<li>{source_link(s)}</li>' for s in claim[key]) + '</ul>' if claim[key] else paragraph(f'{label}: none recorded.', 'evidence-note')
    body += paragraph(claim['verification_notes'], 'evidence-note') if claim['verification_notes'] else ''
    if claim['quality_issues']:
        body += '<ul class="evidence-note">' + ''.join(f'<li>{escape(q["record_id"])}: {escape(q["message"])}</li>' for q in claim['quality_issues']) + '</ul>'
    return body + '</article>'


def record_body(record, claims):
    item, tradition, source = record['item'], record['tradition'], record['source']
    body = f'<nav class="document-breadcrumb" aria-label="Breadcrumb"><a href="../../records/">Catalogue</a> / {escape(record["id"])}</nav>'
    body += f'<p class="section-number">{escape(record["id"])} / {escape(item["id"])}</p><h1>{escape(item["name"])}</h1>'
    body += paragraph(tradition['name'] + ' · ' + tradition['region'], 'document-lead')
    body += facts([('Disclosure date', date_label(record)), ('Date precision', human(record['date_precision'])),
                   ('Disclosure method', human(record['disclosure_method'])), ('Extent', human(record['extent'])),
                   ('Record review', human(record['review_status']))])
    body += f'<p class="document-actions"><a class="small-button" href="../../?q={quote(record["id"])}">View in explorer ↗</a><a href="index.json">This record as JSON</a></p>'
    body += '<section><h2>Restricted material and access</h2>' + paragraph(item['description'])
    body += facts([('Material type', human(item['secrecy_type'])), ('Restricted to', item['restricted_to']),
                   ('Restriction mechanism', item['restriction_mechanism'].replace(';', ', ')),
                   ('Stated reason', item['stated_reason']), ('Tradition origins', tradition['founded'])]) + '</section>'
    body += '<section><h2>Recorded practice status</h2>' + paragraph(human(item['current_status']))
    if item['current_status'] != 'unknown' and not (item['status_as_of'] and item['status_claim_ids']):
        body += paragraph('Provisional: no dated status evidence is linked.', 'provisional')
    body += facts([('Status as of', item['status_as_of']), ('Status claims', item['status_claim_ids'])])
    body += paragraph('Disclosure dates, source publication dates, tradition origins and dates of practice are separate.', 'evidence-note') + '</section>'
    body += '<section><h2>What this disclosure covers</h2>' + paragraph(record['coverage'])
    body += paragraph(record['notes'], 'evidence-note') if record['notes'] else ''
    body += '</section><section><h2>The source</h2><h3>' + source_link(source) + '</h3>'
    body += facts([('Author', source['author']), ('Original publication', source['original_year']),
                   ('Linked edition', source['edition_year']), ('Format', human(source['source_type'])),
                   ('Provenance', source['provenance'].replace(';', ' → ')), ('Rights of source work', human(source['rights'])),
                   ('Identifiers', source['identifiers']), ('Source content hash', source['content_hash'])])
    body += paragraph(source['verification_notes']) if source['verification_notes'] else ''
    body += paragraph(source['notes'], 'evidence-note') if source['notes'] else ''
    for artifact in source['artifacts']:
        body += '<article class="document-claim"><h3>File or recording · ' + escape(human(artifact['artifact_kind'])) + '</h3>'
        if artifact['url']:
            body += f'<p><a href="{escape(artifact["url"], quote=True)}">Open artifact / recovery route ↗</a></p>'
        body += facts([('Artifact ID', artifact['id']), ('Inspection', human(artifact['inspection_status'])),
                       ('Inspected parts', artifact['inspected_parts']), ('SHA-256', artifact['sha256']),
                       ('IPFS CID', artifact['ipfs_cid']), ('BitTorrent info-hash', artifact['btih'])])
        body += paragraph(artifact['notes'], 'evidence-note') if artifact['notes'] else ''
        body += '</article>'
    body += '</section><section><h2>Claims about this item</h2>'
    body += paragraph('These claims may cite other sources for the same restricted item. Supporting and contradicting evidence remain separate.', 'evidence-note')
    body += ''.join(claim_html(c) for c in claims) if claims else paragraph('No claims are recorded for this item.')
    body += '</section><section><h2>Evidence qualifications</h2><ul>'
    body += ''.join(f'<li><code>{escape(q["record_id"])} · {escape(q["code"])}</code>: {escape(q["message"])}</li>' for q in record['quality_issues'])
    body += '</ul>' + paragraph('Reviewed means checked against a source. It does not establish source authenticity, independent corroboration or present-day practice.', 'evidence-note') + '</section>'
    body += '<section><h2>Item notes</h2>' + paragraph(item['notes']) + '</section>' if item['notes'] else ''
    return body


def publish(destination, package, payload, origin):
    """Only validated, explicitly selected metadata and export files are published."""
    (destination / 'exports').mkdir(exist_ok=True)
    optional = tuple(r['name'] + '.parquet' for r in package['resources']
                     if (build.ROOT / 'exports' / (r['name'] + '.parquet')).is_file())
    for name in EXPORTS + optional:
        shutil.copyfile(build.ROOT / 'exports' / name, destination / 'exports' / name)
    for resource in package['resources']:
        path = Path(resource['path'])
        (destination / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(build.ROOT / path, destination / path)
    shutil.copyfile(build.ROOT / 'datapackage.json', destination / 'datapackage.json')
    records = [json.loads(line) for line in (build.ROOT / 'exports/disclosures.jsonl').read_text().splitlines()]
    # Remove obsolete generated records without touching unrelated output files.
    for old in (destination / 'records').glob('DISC-[0-9][0-9][0-9][0-9]'):
        for name in ('index.html', 'index.json'):
            (old / name).unlink(missing_ok=True)
        try:
            old.rmdir()
        except OSError:
            pass
    claims_by_item = defaultdict(list)
    for line in (build.ROOT / 'exports/claims.jsonl').read_text().splitlines():
        claim = json.loads(line)
        claims_by_item[claim['item_id']].append(claim)
    paths = ['', 'records/', 'dataset/']
    by_tradition = defaultdict(list)
    for record in records:
        path = 'records/' + record['id'] + '/'
        paths.append(path)
        target = destination / path
        target.mkdir(parents=True, exist_ok=True)
        claims = claims_by_item[record['item_id']]
        title = record['item']['name'] + ' · ' + record['id']
        description = f'{record["tradition"]["name"]}: {human(record["disclosure_method"])} ({date_label(record)}). {human(record["extent"])} disclosure; {human(record["review_status"])}. Source, coverage and evidence qualifications.'
        schema = {'@context': 'https://schema.org', '@type': 'WebPage', '@id': origin + '/' + path,
                  'url': origin + '/' + path, 'name': title, 'description': description,
                  'isPartOf': {'@type': 'WebSite', 'name': 'Open Arcana', 'url': origin + '/'},
                  'citation': {'@type': 'CreativeWork', 'name': record['source']['title']}}
        if record['source']['url']:
            schema['citation']['url'] = record['source']['url']
        html = document(path, title, description, record_body(record, claims), origin, schema,
                        '\n  <link rel="alternate" type="application/json" href="index.json" title="Record data">')
        (target / 'index.html').write_text(html)
        (target / 'index.json').write_text(json.dumps({**record, 'claims': claims}, ensure_ascii=False) + '\n')
        by_tradition[record['tradition']['name']].append(record)
    body = '<p class="section-number">THE SOURCE-LINKED CATALOGUE</p><h1>All disclosure records</h1>'
    body += paragraph(f'{len(records)} records of restricted rites, initiations, texts and teachings. Browse without JavaScript, open the evidence, or return to the interactive map.', 'document-lead')
    body += paragraph('This is an incomplete seed collection. Country associations follow a tradition’s recorded geography; they do not locate a leak or measure prevalence.', 'evidence-note')
    for name, entries in sorted(by_tradition.items()):
        body += f'<section><h2>{escape(name)}</h2><ul class="catalogue-list">'
        for r in entries:
            body += f'<li><a href="{r["id"]}/">{escape(r["item"]["name"])} · {r["id"]}</a><span>{escape(date_label(r))} · {escape(human(r["disclosure_method"]))} · {escape(human(r["extent"]))} · {escape(human(r["review_status"]))}</span></li>'
        body += '</ul></section>'
    (destination / 'records/index.html').write_text(document('records/', 'Catalogue of restricted knowledge',
        'Browse every Open Arcana disclosure record, with source coverage, authenticity assessments and evidence qualifications.', body, origin))
    schema = dataset_schema(package, payload, origin)
    body = '<p class="section-number">DATA AND EVIDENCE</p><h1>Use the Open Arcana dataset</h1>'
    body += paragraph(package['description'], 'document-lead')
    body += '<section><h2>Download and verify</h2><ul class="catalogue-list">'
    for download in schema['distribution']:
        relative = download['contentUrl'][len(origin) + 1:]
        body += f'<li><a href="../{escape(relative, quote=True)}">{escape(download["name"])}</a><span>{escape(download["encodingFormat"])}</span></li>'
    body += '</ul><p><a href="../datapackage.json">Data Package schema and controlled vocabularies</a> · <a href="../exports/manifest.json">Version and canonical-input hashes</a> · <a href="../exports/SHA256SUMS">Export checksums</a> · <a href="../exports/quality.json">Evidence backlog</a></p></section>'
    body += '<section><h2>Interpret the evidence</h2>' + paragraph('Record review, source authenticity, support for a particular claim, independence of sources and recorded practice status answer different questions. Preserve these fields, locators, coverage, dates and qualifications when importing, citing or training on records. A read automatic transcript does not establish that the audio was checked. An HTTP response does not authenticate a source.')
    body += paragraph('Unknown and disputed values are data, not blanks to fill by inference. Historical disclosures do not establish present-day practice, unchanged ritual forms or the beliefs of an entire community.') + '</section>'
    body += '<section><h2>Scope and reuse</h2>' + paragraph('This catalogue documents specific secret or restricted practices, initiations, texts, teachings and transmission rules. It is not a general collection of scandals or a representative census of world traditions.')
    body += f'<p>The catalogue’s own metadata is <a href="{CC0}">CC0 1.0</a>. Third-party source works, recordings and files retain their own rights; their links and metadata do not grant permission to reuse the underlying works. <a href="{REPOSITORY}/blob/main/SOURCE_POLICY.md">Read the source policy ↗</a>.</p></section>'
    body += facts([('Dataset version', payload['dataset']['version']), ('Canonical snapshot SHA-256', payload['dataset']['snapshot_sha256'])])
    (destination / 'dataset').mkdir(exist_ok=True)
    (destination / 'dataset/index.html').write_text(document('dataset/', 'Open dataset, downloads and evidence guide', package['description'], body, origin, schema))
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in paths:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = origin + '/' + path
    (destination / 'sitemap.xml').write_bytes(ET.tostring(sitemap, encoding='utf-8', xml_declaration=True))
    (destination / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {origin}/sitemap.xml\n')
    headers = f'/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Link: <{origin}/dataset/>; rel="describedby"\n'
    for pattern in ('/data.json', '/data/*', '/datapackage.json', '/exports/*', '/records/*/index.json'):
        headers += f'\n{pattern}\n  Access-Control-Allow-Origin: *\n'
    headers += '\n/exports/*.jsonl\n  Content-Type: application/x-ndjson; charset=utf-8\n'
    (destination / '_headers').write_text(headers)
    (destination / 'llms.txt').write_text(f'''# Open Arcana

> An open catalogue of restricted rites, initiations, texts, teachings and transmission rules, with source-level evidence qualifications.

## Read and retrieve
- [Catalogue with permanent record links]({origin}/records/): all {len(records)} disclosure records, readable without JavaScript. Each record has a linked index.json representation.
- [Data and evidence guide]({origin}/dataset/): scope, limitations, downloads and metadata license.
- [Disclosure JSONL]({origin}/exports/disclosures.jsonl): one self-contained record per disclosure.
- [Claim JSONL]({origin}/exports/claims.jsonl): supporting and contradicting sources, locators and assessments.
- [Schema]({origin}/datapackage.json): field definitions, controlled vocabularies and CSV resources.
- [Manifest]({origin}/exports/manifest.json): version, counts and canonical-input hashes.
- [Checksums]({origin}/exports/SHA256SUMS): hashes of the published exports.
- [Evidence backlog]({origin}/exports/quality.json): missing assessments and record-level qualifications.
- [Explorer data]({origin}/data.json): canonical tables plus conservative geography mappings.
- [Source policy]({REPOSITORY}/blob/main/SOURCE_POLICY.md): research and assessment methods.

## Interpretation and reuse
Record review, source authenticity, claim support, source independence and practice status are separate. Preserve coverage, locators, dates, contradictions and quality_issues. Unknown and provisional values must remain explicit. Publication dates do not establish practice dates or present-day status. Claims about an item may cite sources other than a selected disclosure. This seed collection is incomplete and does not measure prevalence.

The catalogue's own metadata is CC0 1.0. Cited works, audio, video and documents retain their own rights; an accessible link is not a reuse license for the source work.

Dataset version: {payload['dataset']['version']}
Canonical snapshot SHA-256: {payload['dataset']['snapshot_sha256']}
''')
    (destination / '404.html').write_text(document('404.html', 'Page not found', 'This archive page does not exist.',
        f'<h1>Page not found</h1><p>Browse the <a href="{origin}/records/">catalogue</a> or return to the <a href="{origin}/">explorer</a>.</p>', origin,
        extra_head='\n  <meta name="robots" content="noindex">', root_override=origin + '/'))
