"""Read-only provenance checks. Network observations never upgrade evidence labels.

python3 scripts/osint.py --check
python3 scripts/osint.py --live --output research/osint/2026-11-04.json
python3 scripts/osint.py --live --resume --output research/osint/2026-11-04.json

Only public HTTP(S) endpoints are requested. Bodies are bounded samples, not
recovered works; cookies, credentials, JavaScript and meta refresh are not used.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
import threading
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

import build

HEADERS = {'content-type', 'content-length', 'content-range', 'content-disposition',
           'content-encoding', 'etag', 'last-modified', 'location', 'link', 'date', 'server', 'x-robots-tag'}
MAX_BODY = 524288
JSON_BODY = 2097152
MAX_REDIRECTS = 8
_locks, _last_request, _lock = {}, {}, threading.Lock()
AUDITOR_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def isbn_valid(value):
    value = re.sub(r'[- ]', '', value).upper()
    if re.fullmatch(r'\d{9}[\dX]', value):
        return sum((10 - i) * (10 if c == 'X' else int(c)) for i, c in enumerate(value)) % 11 == 0
    return bool(re.fullmatch(r'97[89]\d{10}', value)) and sum(
        int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(value)) % 10 == 0


def canonical_url(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query, ''))


def public_url(url):
    """Validate each actual redirect hop, not just the input URL."""
    if not build.is_web_url(url):
        raise ValueError('not an HTTP(S) URL without credentials')
    p = urlsplit(url)
    if p.port not in (None, 80, 443):
        raise ValueError('nonstandard web port not requested by this auditor')
    addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == 'https' else 80),
                                   type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('non-public destination')


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts, self.meta, self.links = [], defaultdict(list), []
        self.in_title = False
        self.title_complete = False
        self.anchors, self.anchor = [], None

    def handle_starttag(self, tag, attrs):
        a = {str(k).lower(): v for k, v in attrs if v is not None}
        if tag == 'title' and not self.title_complete:
            self.in_title = True
        elif tag == 'meta':
            name = a.get('name', a.get('property', a.get('http-equiv', ''))).lower()
            if name and 'content' in a and len(self.meta[name]) < 12:
                self.meta[name].append(a['content'][:1200])
        elif tag == 'link' and a.get('rel', '').lower() in ('canonical', 'alternate'):
            self.links.append({k: a[k][:1200] for k in ('rel', 'href', 'type', 'hreflang') if k in a})
        elif tag == 'a' and a.get('href') and len(self.anchors) < 200:
            self.anchor = {'href': a['href'][:1200], 'label': ''}
            self.anchors.append(self.anchor)

    def handle_endtag(self, tag):
        if tag == 'title' and self.in_title:
            self.in_title = False
            self.title_complete = True
        elif tag == 'a':
            self.anchor = None

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.anchor is not None:
            self.anchor['label'] = (self.anchor['label'] + data)[:400]


def text_values(value):
    if value is None:
        return []
    return [str(v)[:1200] for v in (value if isinstance(value, list) else [value])]


def bibliographic_metadata(body, content_type, url):
    """Keep provider dates labelled; HTTP/upload dates are not publication dates."""
    text = body.decode('utf-8', errors='replace')
    result = {}
    if 'json' in content_type or text.lstrip().startswith('{'):
        try:
            obj = json.loads(text)
        except (ValueError, TypeError):
            return {'parse_error': 'JSON not complete/parseable in the bounded response'}
        if not isinstance(obj, dict):
            return {'parse_error': 'JSON object expected'}
        p = urlsplit(url)
        if p.hostname == 'archive.org' and p.path.startswith('/metadata/'):
            md = obj.get('metadata', {})
            result = {'provider': 'internet_archive', 'titles': text_values(md.get('title')),
                      'authors': text_values(md.get('creator')), 'publication_dates': text_values(md.get('date')),
                      'identifiers': text_values(md.get('identifier')), 'media_types': text_values(md.get('mediatype')),
                      'provider_upload_dates': text_values(md.get('addeddate')) + text_values(md.get('publicdate')),
                      'access_restricted': md.get('access-restricted-item'), 'files_count': obj.get('files_count'),
                      'metadata_present': bool(md)}
            result['files'] = [{k: f[k] for k in ('name', 'size', 'sha1', 'md5', 'format') if k in f}
                               for f in obj.get('files', []) if f.get('name', '').lower().endswith(
                                   ('.pdf', '.wav', '.mp3', '.mp4', '_djvu.txt', '.torrent'))]
        elif p.hostname == 'api.crossref.org':
            md = obj.get('message', {})
            dates = []
            for key in ('published', 'published-print', 'published-online'):
                for parts in md.get(key, {}).get('date-parts', []):
                    dates.append({'field': key, 'value': '-'.join(map(str, parts))})
            result = {'provider': 'crossref', 'titles': text_values(md.get('title')),
                      'authors': [' '.join(filter(None, [a.get('given'), a.get('family')])) for a in md.get('author', [])],
                      'publication_dates': dates, 'identifiers': text_values(md.get('DOI')),
                      'work_type': md.get('type'), 'publisher': md.get('publisher'),
                      'relation': md.get('relation'), 'updates': md.get('update-to', [])}
        elif p.hostname == 'openlibrary.org':
            result = {'provider': 'open_library', 'titles': text_values(obj.get('title')),
                      'publication_dates': text_values(obj.get('publish_date', obj.get('first_publish_date'))),
                      'identifiers': text_values(obj.get('key')), 'authors': obj.get('authors', []),
                      'isbn_10': obj.get('isbn_10', []), 'isbn_13': obj.get('isbn_13', []),
                      'metadata_present': bool(obj.get('title'))}
        elif 'entities' in obj:
            entities = obj.get('entities', {})
            result = {'provider': 'wikidata', 'entities': {
                k: {'label_en': v.get('labels', {}).get('en', {}).get('value'),
                    'description_en': v.get('descriptions', {}).get('en', {}).get('value'),
                    'modified': v.get('modified'), 'lastrevid': v.get('lastrevid'),
                    'aliases_en': [a.get('value') for a in v.get('aliases', {}).get('en', [])]}
                for k, v in entities.items()}}
        return result
    if 'html' in content_type or '<html' in text[:2000].lower() or '<!doctype html' in text[:2000].lower():
        parser = MetadataParser()
        parser.feed(text)
        wanted = ('citation_', 'dc.', 'dcterms.', 'og:', 'article:', 'date', 'author', 'refresh', 'robots')
        result = {'page_title': ' '.join(''.join(parser.title_parts).split())[:1200],
                  'meta': {k: v for k, v in parser.meta.items() if k.startswith(wanted)},
                  'declared_links': parser.links[:30],
                  'outbound_links': [{'href': urljoin(url, a['href']), 'label': ' '.join(a['label'].split())}
                                     for a in parser.anchors
                                     if build.is_web_url(urljoin(url, a['href']))]}
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url, timeout=12, guard=public_url, opener=None):
    opener = opener or build_opener(NoRedirect())
    result = {'requested_url': url, 'checked_at': now(), 'method': 'GET', 'hops': [], 'flags': [],
              'auditor_sha256': AUDITOR_SHA256, 'metadata_parser': 'first-title-and-anchors-v3'}
    visited = set()
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if canonical_url(current) in visited:
            result['error'] = 'redirect_loop'
            break
        visited.add(canonical_url(current))
        try:
            guard(current)
            host = urlsplit(current).hostname
            with _lock:
                host_lock = _locks.setdefault(host, threading.Lock())
            with host_lock:
                delay = 1.1 if host == 'openlibrary.org' else 0.2
                time.sleep(max(0, delay - (time.monotonic() - _last_request.get(host, 0))))
                _last_request[host] = time.monotonic()
                request = Request(build.link_url(current), headers={
                    'User-Agent': 'OpenArcanaSourceAudit/1.0 (public metadata research)',
                    'Accept': 'application/json,text/html,application/pdf,*/*;q=0.5',
                    'Accept-Encoding': 'identity'})
                try:
                    response = opener.open(request, timeout=timeout)
                except HTTPError as e:
                    response = e
                with response:
                    status = response.status
                    headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in HEADERS}
                    result['hops'].append({'url': current, 'status': status, 'headers': headers})
                    if status in (301, 302, 303, 307, 308) and headers.get('location'):
                        destination = urljoin(current, headers['location'])
                        if urlsplit(current).scheme == 'https' and urlsplit(destination).scheme == 'http':
                            result['flags'].append('https_to_http_redirect')
                        current = destination
                        continue
                    cap = JSON_BODY if ('json' in headers.get('content-type', '')
                                       or '/metadata/' in current or current.endswith('.json')) else MAX_BODY
                    body = response.read(cap + 1)
                    truncated = len(body) > cap
                    body = body[:cap]
                    result.update(final_url=current, status=status, body_sample_bytes=len(body),
                                  body_sample_sha256=hashlib.sha256(body).hexdigest(), body_truncated=truncated,
                                  content_type=headers.get('content-type', '').split(';')[0].lower(),
                                  metadata=bibliographic_metadata(body, headers.get('content-type', ''), current))
                    result['body_signature'] = ('pdf' if body.startswith(b'%PDF-') else
                                                'html' if re.search(br'<(?:!doctype html|html)[\s>]', body[:3000], re.I) else
                                                'json' if body.lstrip().startswith((b'{', b'[')) else 'other')
                    if status in (401, 403, 429):
                        result['flags'].append('access_limited')
                    title = result['metadata'].get('page_title', '').lower()
                    if access_page(title):
                        result['flags'].append('interstitial_or_access_page')
                    if status == 202:
                        result['flags'].append('nonfinal_http_status')
                    if status >= 400:
                        result['flags'].append('http_error')
                    if result['metadata'].get('metadata_present') is False:
                        result['flags'].append('provider_metadata_missing')
                    if result['metadata'].get('parse_error'):
                        result['flags'].append('metadata_parse_incomplete')
                    break
        except (ValueError, OSError, URLError) as e:
            result.update(final_url=current, error=f'{type(e).__name__}: {str(e)[:300]}')
            break
    else:
        result['error'] = 'redirect_limit'
    result.setdefault('final_url', current)
    return result


def targets(tables):
    found = {}

    def add(url, table, ident, field, identifier=None, purpose='recorded_link'):
        if url:
            ref = {'table': table, 'id': ident, 'field': field, 'purpose': purpose}
            if identifier:
                ref['identifier'] = identifier
            found.setdefault(url, []).append(ref)

    for s in tables['sources']:
        add(s['url'], 'sources', s['id'], 'url')
        for pair in build.split(s['identifiers']):
            prefix, value = pair.split(':', 1)
            add(build.identifier_url(prefix, value), 'sources', s['id'], 'identifiers', pair, 'identifier_link')
            api = None
            if prefix == 'ia':
                api = 'https://archive.org/metadata/' + quote(value, safe='')
            elif prefix == 'ol':
                api = 'https://openlibrary.org/works/' + quote(value, safe='') + '.json'
            elif prefix == 'doi':
                api = 'https://api.crossref.org/works/' + quote(value, safe='')
            elif prefix == 'isbn':
                api = 'https://openlibrary.org/isbn/' + re.sub(r'[- ]', '', value) + '.json'
            elif prefix == 'wikidata':
                api = 'https://www.wikidata.org/wiki/Special:EntityData/' + value + '.json'
            add(api, 'sources', s['id'], 'identifiers', pair, 'provider_metadata')
    for a in tables['source_artifacts']:
        add(a['url'], 'source_artifacts', a['id'], 'url')
    for t in tables['traditions']:
        if t['wikidata']:
            add(build.ID_URLS['wikidata'].format(t['wikidata']), 'traditions', t['id'], 'wikidata', t['wikidata'], 'identifier_link')
            add('https://www.wikidata.org/wiki/Special:EntityData/' + t['wikidata'] + '.json',
                'traditions', t['id'], 'wikidata', t['wikidata'], 'provider_metadata')
    return found


def normalized_title(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.lower()) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'\w+', value))


def title_similarity(expected, resolved):
    a, b = normalized_title(expected), normalized_title(resolved)
    if not a or not b:
        return 0
    # Catalogues expand short titles and may describe a container, not its part.
    # This is triage, never a positive authenticity or independence judgement.
    if a in b or b in a:
        return 1
    words = set(a.split()) - {'the', 'a', 'an', 'of', 'and', 'in', 'to', 'or', 'by'}
    overlap = len(words & set(b.split())) / len(words) if words else 0
    return max(SequenceMatcher(None, a, b).ratio(), overlap)


def access_page(title):
    return any(x in title.lower() for x in ('just a moment', 'access denied', 'robot check',
                                            'captcha', 'sign in', 'human verification', 'verification required'))


def display_title(probe):
    md = probe.get('metadata', {})
    if md.get('page_title'):
        return md['page_title']
    for key in ('citation_title', 'og:title', 'dc.title'):
        if md.get('meta', {}).get(key):
            return md['meta'][key][0]
    return '; '.join(md.get('titles', [])) or md.get('title_elements_text', '')[:250]


def static_findings(tables):
    issues, groups = [], defaultdict(list)
    for s in tables['sources']:
        if not s['url'] and not s['identifiers']:
            issues.append({'code': 'source_without_recovery_route', 'records': [s['id']], 'detail': 'No URL or external identifier; title alone is not a recovered source.'})
        for pair in build.split(s['identifiers']):
            prefix, value = pair.split(':', 1)
            if prefix == 'isbn' and not isbn_valid(value):
                issues.append({'code': 'invalid_isbn_checksum', 'records': [s['id']], 'detail': pair})
            key = re.sub(r'[- ]', '', value).upper() if prefix == 'isbn' else value.lower() if prefix == 'doi' else value
            groups[(prefix, key)].append(s['id'])
        if s['url']:
            groups[('url', canonical_url(s['url']))].append(s['id'])
    for identity, ids in groups.items():
        if len(set(ids)) > 1:
            issues.append({'code': 'shared_source_identity', 'records': sorted(set(ids)), 'detail': ':'.join(identity)})
    return issues


def live_findings(tables, requested, probes):
    issues = []
    sources = {s['id']: s for s in tables['sources']}
    traditions = {t['id']: t for t in tables.get('traditions', [])}
    artifacts = {a['id']: a for a in tables['source_artifacts']}
    destinations = defaultdict(set)
    for url, refs in requested.items():
        probe = probes.get(url)
        if not probe:
            continue
        ids = sorted({r['id'] for r in refs})
        for flag in probe.get('flags', []):
            issues.append({'code': flag, 'records': ids, 'url': url, 'detail': str(probe.get('status', ''))})
        # Reassess cached observations without pretending they were requested again.
        if access_page(display_title(probe)) and 'interstitial_or_access_page' not in probe.get('flags', []):
            issues.append({'code': 'interstitial_or_access_page', 'records': ids, 'url': url, 'detail': display_title(probe)})
        if probe.get('status') == 202 and 'nonfinal_http_status' not in probe.get('flags', []):
            issues.append({'code': 'nonfinal_http_status', 'records': ids, 'url': url, 'detail': '202 does not establish a delivered work'})
        if probe.get('error'):
            issues.append({'code': 'request_unresolved', 'records': ids, 'url': url, 'detail': probe['error']})
        if probe.get('status', 999) >= 400 or probe.get('error'):
            continue
        for r in refs:
            if r['table'] == 'source_artifacts':
                a = artifacts[r['id']]
                if a['media_type'] == 'application/pdf' and probe.get('body_signature') == 'html':
                    issues.append({'code': 'pdf_url_returned_html', 'records': [a['id']], 'url': url, 'detail': probe.get('metadata', {}).get('page_title', '')})
                headers = probe.get('hops', [{}])[-1].get('headers', {})
                length = headers.get('content-length', '')
                if (a.get('size_bytes') and length.isdigit() and probe.get('status') == 200
                        and probe.get('content_type') == a.get('media_type')
                        and headers.get('content-encoding', 'identity') == 'identity'
                        and int(length) != int(a['size_bytes'])):
                    issues.append({'code': 'artifact_size_review', 'records': [a['id']], 'url': url,
                                   'detail': {'captured_size': a['size_bytes'], 'server_length': length}})
            elif r['table'] == 'sources':
                if r['purpose'] != 'provider_metadata':
                    destinations[canonical_url(probe['final_url'])].add(r['id'])
                else:
                    titles = probe.get('metadata', {}).get('titles', [])
                    if titles:
                        scores = [title_similarity(sources[r['id']]['title'], t) for t in titles]
                        if max(scores) < 0.45:
                            issues.append({'code': 'provider_title_review', 'records': [r['id']], 'url': url,
                                           'detail': {'recorded': sources[r['id']]['title'], 'resolved': titles}})
                    dates = probe.get('metadata', {}).get('publication_dates', [])
                    years = {year for d in dates for year in re.findall(
                        r'(?<!\d)\d{4}(?!\d)', str(d.get('value', '') if isinstance(d, dict) else d))}
                    source = sources[r['id']]
                    expected_years = {year for value in (source['original_year'], source['edition_year'])
                                      for year in re.findall(r'(?<!\d)\d{4}(?!\d)', value)}
                    if expected_years and years and not expected_years & years:
                        issues.append({'code': 'provider_date_review', 'records': [r['id']], 'url': url,
                                       'detail': {'recorded_years': sorted(expected_years), 'provider_dates': dates,
                                                  'qualification': 'May be another edition, original composition or cataloguing difference.'}})
            elif r['table'] == 'traditions' and r['purpose'] == 'provider_metadata':
                for entity in probe.get('metadata', {}).get('entities', {}).values():
                    labels = [entity.get('label_en')] + entity.get('aliases_en', [])
                    labels = [x for x in labels if x]
                    if labels and max(title_similarity(traditions[r['id']]['name'], x) for x in labels) < 0.45:
                        issues.append({'code': 'provider_subject_review', 'records': [r['id']], 'url': url,
                                       'detail': {'recorded': traditions[r['id']]['name'], 'provider_labels': labels}})
    for destination, ids in destinations.items():
        if len(ids) > 1:
            issues.append({'code': 'shared_final_destination', 'records': sorted(ids), 'url': destination,
                           'detail': 'Shared landing page may indicate a collection, redirect or dependence; human review required.'})
    return issues


def capture_checks(tables, roots):
    """Rehash only explicitly supplied task directories; do not scan user files."""
    expected_sizes = {int(a['size_bytes']) for a in tables['source_artifacts'] if a['sha256']}
    source_hashes = {s['content_hash'].removeprefix('sha256:') for s in tables['sources'] if s['content_hash']}
    found = defaultdict(list)
    source_found = defaultdict(list)
    for root in roots:
        for path in sorted(Path(root).rglob('*')):
            if (path.is_file() and not path.is_symlink() and (path.stat().st_size in expected_sizes
                    or source_hashes and path.suffix.lower() in ('.pdf', '.html', '.txt', '.json', '.wav', '.mp3', '.torrent'))):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                found[(digest, path.stat().st_size)].append(str(path.resolve()))
                if digest in source_hashes:
                    source_found[digest].append(str(path.resolve()))
    checks = [{'table': 'source_artifacts', 'record_id': a['id'], 'artifact_id': a['id'],
             'recorded_sha256': a['sha256'], 'recorded_size_bytes': a['size_bytes'],
             'matching_local_files': found.get((a['sha256'], int(a['size_bytes'])), []),
             'result': 'matched' if found.get((a['sha256'], int(a['size_bytes']))) else 'not_found_in_supplied_directories'}
            for a in tables['source_artifacts'] if a['sha256']]
    checks += [{'table': 'sources', 'record_id': s['id'], 'recorded_sha256': s['content_hash'],
                'matching_local_files': source_found.get(s['content_hash'].removeprefix('sha256:'), []),
                'result': 'matched' if source_found.get(s['content_hash'].removeprefix('sha256:')) else 'not_found_in_supplied_directories'}
               for s in tables['sources'] if s['content_hash']]
    return checks


def needs_retry(probe):
    """Only an explicit retry requests an already observed target again."""
    return bool(probe.get('error') or probe.get('status', 0) >= 400 or probe.get('status') == 202
                or set(probe.get('flags', [])) & {'interstitial_or_access_page',
                    'provider_metadata_missing', 'metadata_parse_incomplete'})


def retain_observation(previous, observed):
    """Keep prior receipts intact when a new attempt becomes the current result."""
    if not previous:
        return observed
    history = list(previous.get('previous_observations', []))
    history.append({k: v for k, v in previous.items() if k != 'previous_observations'})
    return {**observed, 'previous_observations': history}


def host_observations(requested, probes):
    groups = defaultdict(list)
    for url, probe in probes.items():
        if url in requested and not probe.get('request_skipped'):
            groups[urlsplit(url).hostname].append((url, probe))
    return [{'host': host, 'targets_observed': len(rows),
             'unresolved_targets': sum(bool(p.get('error')) for _, p in rows),
             'http_statuses': dict(sorted(Counter(str(p.get('status', 'unresolved')) for _, p in rows).items())),
             'record_ids': sorted({r['id'] for url, _ in rows for r in requested[url]}),
             'errors': dict(Counter(p['error'] for _, p in rows if p.get('error')))}
            for host, rows in sorted(groups.items())]


SEARCH_ROLES = {'exact_copy', 'edited_transcription', 'collection_index', 'finding_aid',
                'bibliographic_record', 'context', 'lead'}
SEARCH_OUTCOMES = {'inspected', 'metadata_only', 'access_limited', 'not_found', 'unavailable', 'not_searched'}


def search_observations(tables, paths=None):
    """Discovery receipts are observations, never automatic evidence promotions."""
    paths = paths if paths is not None else sorted((build.ROOT / 'research/searches').glob('*.jsonl'))
    records, errors, seen = [], [], set()
    source_ids = {s['id'] for s in tables['sources']}
    artifacts = {a['id']: a for a in tables.get('source_artifacts', [])}
    required = {'id', 'observed_at', 'source_ids', 'question', 'channel', 'tool', 'query',
                'urls', 'role', 'outcome', 'inspected_parts', 'limits'}
    for path in paths:
        for line_no, line in enumerate(Path(path).read_text().splitlines(), 1):
            where = f'{Path(path).name}:{line_no}'
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or not required <= row.keys():
                    raise ValueError('missing discovery receipt fields')
                if not isinstance(row['id'], str) or not row['id'] or row['id'] in seen:
                    raise ValueError('missing or duplicate observation ID')
                if (not isinstance(row['source_ids'], list) or not row['source_ids']
                        or not all(isinstance(s, str) and s in source_ids for s in row['source_ids'])):
                    raise ValueError('source_ids must refer to canonical sources')
                if (not isinstance(row['urls'], list)
                        or not all(isinstance(u, str) and build.is_web_url(u) for u in row['urls'])):
                    raise ValueError('urls must be public-form HTTP(S) references without credentials')
                if row['role'] not in SEARCH_ROLES or row['outcome'] not in SEARCH_OUTCOMES:
                    raise ValueError('unknown recovery role or outcome')
                artifact_ids = row.get('artifact_ids', [])
                if (not isinstance(artifact_ids, list) or not all(isinstance(a, str) and a in artifacts
                        and artifacts[a]['source_id'] in row['source_ids'] for a in artifact_ids)):
                    raise ValueError('artifact_ids must identify artifacts of the cited sources')
                for key in required - {'source_ids', 'urls'}:
                    if not isinstance(row[key], str) or not row[key].strip():
                        raise ValueError(f'{key} must be nonempty text')
                stamp = datetime.fromisoformat(row['observed_at'])
                if stamp.tzinfo is None:
                    raise ValueError('observed_at must include a timezone')
                if row['outcome'] == 'inspected' and not (row['urls'] or artifact_ids):
                    raise ValueError('inspected receipt needs an identifiable reference')
                seen.add(row['id'])
                records.append(row)
            except (ValueError, TypeError, KeyError) as e:
                errors.append(f'{where}: {e}')
    return records, errors


def report(package, tables, probes, captures=None, export_errors=None):
    requested = targets(tables)
    active = {u: probes[u] for u in requested if u in probes and not probes[u].get('request_skipped')}
    dataset, inputs = build.snapshot(package)
    quality = build.build_quality(tables, dataset)
    search_paths = sorted((build.ROOT / 'research/searches').glob('*.jsonl'))
    searches, search_errors = search_observations(tables, search_paths)
    return {'audit_version': 3, 'generated_at': now(), 'dataset': dataset,
            'auditor_sha256': AUDITOR_SHA256,
            'canonical_inputs': inputs, 'record_counts': {k: len(v) for k, v in tables.items()},
            'records': {k: [r['id'] for r in v] for k, v in tables.items()},
            'validation_errors': build.validate(package, tables) + search_errors, 'targets': requested,
            'generated_exports': {'checked': export_errors is not None, 'errors': export_errors or []},
            'evidence_backlog': {'issue_counts': quality['issue_counts'], 'issues': quality['issues']},
            'coverage': {'unique_targets': len(requested), 'targets_observed': len(active),
                         'targets_unobserved': sorted(set(requested) - set(active)),
                         'targets_skipped': [u for u in requested if probes.get(u, {}).get('request_skipped')],
                         'http_statuses': dict(sorted(Counter(str(p.get('status', 'unresolved')) for p in active.values()).items())),
                         'redirected_targets': sum(any(h['status'] in (301, 302, 303, 307, 308)
                                                      for h in p.get('hops', [])) for p in active.values())},
            'findings': static_findings(tables) + live_findings(tables, requested, active),
            'host_observations': host_observations(requested, active),
            'search_observations': searches,
            'search_log_inputs': [{'path': str(p.relative_to(build.ROOT)),
                                   'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                                  for p in search_paths],
            'probes': probes, 'local_capture_checks': captures or [],
            'limitations': ['All canonical records are structurally inventoried; this is not a fresh content review of every assertion.',
                           'HTTP availability, metadata agreement, source identity and claim truth are different questions.',
                           'Response hashes identify bounded body samples; they must never replace artifact SHA-256 values.',
                           'HTTP dates, upload dates, provider publication dates and first disclosure dates are separate.',
                           'A blocked request is an access limit, not evidence of censorship or a false source.',
                           'Canonical links, meta refresh, outbound link labels, aliases and shared destinations are leads, not independent corroboration.',
                           'Host-level failures can affect many targets; neither URL nor error counts measure affected works or truth.',
                           'Discovery roles describe inspected copies, indexes, finding aids or leads; an index is not its advertised payload.',
                           'Cached probes retain their own checked_at times. No authentication or access challenge is bypassed.']}


def markdown(data):
    out = ['# OSINT source and implementation audit', '', 'Generated by `scripts/osint.py`; edit canonical inputs or rerun the audit.', '',
           f"Audit generated: {data['generated_at']}. Dataset snapshot: `{data['dataset']['snapshot_sha256']}`.", '',
           'All records are inventoried below; network observations do not verify all underlying content.', '',
           '| Table | Records |', '|---|---:|']
    out += [f'| {k} | {v} |' for k, v in data['record_counts'].items()]
    c = data['coverage']
    out += ['', f"Observed {c['targets_observed']} of {c['unique_targets']} distinct recorded/identifier/metadata URLs; "
            f"{c['redirected_targets']} targets have observed redirects.", '', '## Findings requiring interpretation', '',
            '| Check | Findings |', '|---|---:|']
    out += [f'| {k} | {v} |' for k, v in sorted(Counter(x['code'] for x in data['findings']).items())]
    out += ['', 'Counts above are findings, not distinct affected records or a truth score.', '',
            '## Unresolved requests grouped by host', '', '| Host | Unresolved targets | Observed targets |', '|---|---:|---:|']
    out += [f"| {build.md(h['host'])} | {h['unresolved_targets']} | {h['targets_observed']} |"
            for h in data['host_observations'] if h['unresolved_targets']]
    out += ['', 'The grouping identifies shared access failures; it does not diagnose their cause.', '',
            '## Discovery and recovery observations', '',
            '| Observation | Sources | Channel | Role | Outcome | Inspected parts and limits |', '|---|---|---|---|---|---|']
    out += [f"| {build.md(s['id'])} | {', '.join(s['source_ids'])} | {build.md(s['channel'])} | "
            f"{s['role']} | {s['outcome']} | {build.md(s['inspected_parts'])}<br>{build.md(s['limits'])} |"
            for s in data['search_observations']]
    out += ['', 'Query strings, URLs, tools and observation times are retained in JSON and the discovery log. '
            'Browser observations do not invent HTTP status codes.', '', '## Source receipts', '',
            '| URL | Record references | Result | Final destination / title |', '|---|---|---|---|']
    for url, refs in data['targets'].items():
        p = data['probes'].get(url, {})
        summary = display_title(p) or p.get('error', '')
        destination = p.get('final_url', '')
        out.append(f"| [URL]({build.link_url(url)}) | {', '.join(sorted({r['id'] for r in refs}))} | "
                   f"{p.get('status', 'not requested' if p.get('request_skipped') else 'unobserved' if not p else 'unresolved')} | {build.md(destination)}<br>{build.md(summary)} |")
    out += ['', '## Limits', ''] + ['- ' + x for x in data['limitations']]
    out += ['', 'Exact hops, selected response headers, metadata, sample-byte hashes, timestamps and per-record findings are in the adjacent JSON.', '']
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Offline structural and identifier checks; no network or writes')
    parser.add_argument('--live', action='store_true', help='Request public targets; prefer provider APIs over catalogue HTML')
    parser.add_argument('--resume', action='store_true', help='Reuse timestamped observations already in the output')
    parser.add_argument('--retry-unresolved', action='store_true', help='With --live --resume, retry failed/access-limited targets and retain prior receipts')
    parser.add_argument('--only-host', action='append', default=[], help='Limit live requests to this exact hostname; may be repeated')
    parser.add_argument('--output', type=Path, default=build.ROOT / 'research/osint/audit.json')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--captures', type=Path, nargs='+', default=[], help='Explicit task directories to rehash; no other files are scanned')
    args = parser.parse_args()
    package, tables = build.load()
    errors = build.validate(package, tables)
    if errors:
        raise SystemExit('\n'.join(errors))
    searches, search_errors = search_observations(tables)
    if search_errors:
        raise SystemExit('\n'.join(search_errors))
    findings = static_findings(tables)
    if args.check:
        print(f"OSINT offline: {sum(map(len, tables.values()))} records; {len(targets(tables))} URL targets; "
              f"{len(findings)} qualifications; {len(searches)} discovery receipts; no network requests")
        return int(any(x['code'] == 'invalid_isbn_checksum' for x in findings))
    if args.workers < 1 or args.workers > 12:
        parser.error('--workers must be between 1 and 12')
    if args.retry_unresolved and not (args.live and args.resume):
        parser.error('--retry-unresolved requires --live --resume')
    if args.only_host and not args.live:
        parser.error('--only-host requires --live')
    probes = {}
    if args.resume and args.output.exists():
        previous = json.loads(args.output.read_text())
        probes = previous['probes']
        # Preserve legacy extraction as such: v1 also collected nested SVG titles.
        for probe in probes.values():
            probe.setdefault('auditor_sha256', previous['auditor_sha256'])
            if 'metadata_parser' not in probe:
                probe['metadata_parser'] = 'all-title-elements-v1'
                md = probe.get('metadata', {})
                if 'page_title' in md:
                    md['title_elements_text'] = md.pop('page_title')
    requested = targets(tables)
    if args.live:
        missing = [u for u in requested if (u not in probes or args.retry_unresolved and needs_retry(probes[u]))
                   and (not args.only_host or urlsplit(u).hostname in args.only_host)]
        for url in list(missing):
            if (urlsplit(url).hostname == 'openlibrary.org' and not urlsplit(url).path.endswith('.json')
                    and all(r['purpose'] == 'identifier_link' for r in requested[url])):
                # Retain an earlier HTML failure as the current observation;
                # only the provider API is retried, without erasing that failure.
                if url in probes:
                    missing.remove(url)
                    continue
                probes[url] = {'requested_url': url, 'recorded_at': now(), 'method': None,
                               'request_skipped': 'Provider API preferred; catalogue HTML is inventoried, not bulk requested.',
                               'hops': [], 'auditor_sha256': AUDITOR_SHA256}
                missing.remove(url)
        print(f'Checking {len(missing)} URLs; reusing {len(set(probes) & set(requested))} timestamped receipts', flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch, u): u for u in missing}
            for i, future in enumerate(as_completed(futures), 1):
                url = futures[future]
                try:
                    observed = future.result()
                except Exception as e:
                    observed = {'requested_url': url, 'checked_at': now(), 'hops': [],
                                   'error': f'Unexpected {type(e).__name__}: {str(e)[:300]}'}
                probes[url] = retain_observation(probes.get(url), observed)
                if i % 10 == 0 or i == len(missing):
                    print(f'Observed {i}/{len(missing)} new targets', flush=True)
                    args.output.write_text(json.dumps(report(package, tables, probes), ensure_ascii=False, indent=2) + '\n')
    dataset, inputs = build.snapshot(package)
    export_errors = build.check_exports(package, tables, dataset, inputs, build.ROOT)
    data = report(package, tables, probes, capture_checks(tables, args.captures) if args.captures else None, export_errors)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    args.output.with_suffix('.md').write_text(markdown(data))
    print(f"Wrote {args.output}: {data['coverage']['targets_observed']}/{data['coverage']['unique_targets']} targets observed")
    return 0


if __name__ == '__main__':
    sys.exit(main())
