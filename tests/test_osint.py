"""Offline regressions for misleading metadata, redirects and copy identity."""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import osint
import build


class Response(io.BytesIO):
    def __init__(self, body=b'', status=200, headers=None):
        super().__init__(body)
        self.status, self.headers = status, headers or {'Content-Type': 'text/html'}


class Opener:
    def __init__(self, responses):
        self.responses, self.urls = list(responses), []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return self.responses.pop(0)


class MetadataTests(unittest.TestCase):
    def test_svg_titles_do_not_pollute_the_page_title(self):
        md = osint.bibliographic_metadata(
            b'<html><head><title>Actual work</title></head><body><svg><title>Menu icon</title></svg></body>',
            'text/html', 'https://example.org/')
        self.assertEqual(md['page_title'], 'Actual work')

    def test_canonical_and_refresh_are_recorded_without_following(self):
        md = osint.bibliographic_metadata(
            b'<html><head><meta http-equiv="refresh" content="0;url=http://127.0.0.1/">'
            b'<link rel="canonical" href="https://example.org/work"><meta name="citation_author" content="A">'
            b'<meta name="citation_author" content="B"></head></html>', 'text/html', 'https://example.org/')
        self.assertEqual(md['meta']['citation_author'], ['A', 'B'])
        self.assertIn('refresh', md['meta'])
        self.assertEqual(md['declared_links'][0]['href'], 'https://example.org/work')

    def test_document_labels_and_actual_destinations_remain_separate(self):
        md = osint.bibliographic_metadata(
            b'<html><a href="https://other.example/">OT III <b>Course</b></a>'
            b'<a href="summary.html">Summary</a><a href="javascript:alert(1)">Run</a></html>',
            'text/html', 'https://example.org/index.html')
        self.assertEqual(md['outbound_links'], [
            {'href': 'https://other.example/', 'label': 'OT III Course'},
            {'href': 'https://example.org/summary.html', 'label': 'Summary'}])
        self.assertNotIn('source_authenticity', md)

    def test_provider_upload_date_is_not_publication_date(self):
        body = json.dumps({'metadata': {'title': 'Work', 'date': '1904', 'publicdate': '2026-11-04'}}).encode()
        md = osint.bibliographic_metadata(body, 'application/json', 'https://archive.org/metadata/example')
        self.assertEqual(md['publication_dates'], ['1904'])
        self.assertEqual(md['provider_upload_dates'], ['2026-11-04'])

    def test_empty_archive_metadata_is_not_a_found_source(self):
        p = osint.fetch('https://archive.org/metadata/missing', guard=lambda u: None,
                        opener=Opener([Response(b'{}', headers={'Content-Type': 'application/json'})]))
        self.assertEqual(p['status'], 200)
        self.assertIn('provider_metadata_missing', p['flags'])

    def test_short_titles_can_match_longer_catalogue_titles(self):
        self.assertGreaterEqual(osint.title_similarity('Masonry Dissected', 'Masonry dissected: being a universal and genuine description'), 0.45)
        self.assertLess(osint.title_similarity('Masonry Dissected', 'A handbook of tropical medicine'), 0.45)

    def test_isbn_checksum_and_hyphen_normalization(self):
        for value in ['978-1-105-02179-4', '091552032X']:
            self.assertTrue(osint.isbn_valid(value))
        for value in ['9781105021795', '0915520320', 'nonsense']:
            self.assertFalse(osint.isbn_valid(value))

    def test_original_and_edition_dates_do_not_create_false_conflicts(self):
        url = 'https://example.org/metadata'
        refs = {url: [{'table': 'sources', 'id': 'SRC-1', 'purpose': 'provider_metadata'}]}
        for original, edition, resolved, conflict in [('2024', '2026', '2024-8-27', False),
                                                      ('195', '1919', '[1919]', False),
                                                      ('1900', '', '2001', True)]:
            with self.subTest(resolved=resolved):
                tables = {'sources': [{'id': 'SRC-1', 'title': 'Work', 'original_year': original,
                                       'edition_year': edition}], 'source_artifacts': []}
                probe = {'status': 200, 'final_url': url, 'metadata': {'titles': ['Work'],
                         'publication_dates': [{'field': 'published', 'value': resolved}]}}
                codes = {f['code'] for f in osint.live_findings(tables, refs, {url: probe})}
                self.assertEqual('provider_date_review' in codes, conflict)


class ProbeTests(unittest.TestCase):
    def test_retry_retains_each_original_receipt_without_nested_history(self):
        old = {'checked_at': '2026-11-04T10:00:00+00:00', 'error': 'connection refused', 'hops': []}
        original = copy.deepcopy(old)
        new = {'checked_at': '2026-11-04T11:00:00+00:00', 'status': 200, 'hops': []}
        retry = osint.retain_observation(old, new)
        self.assertEqual(old, original)
        self.assertEqual(retry['previous_observations'], [old])
        self.assertEqual(retry['status'], 200)
        again = osint.retain_observation(retry, {'error': 'timeout'})
        self.assertEqual(len(again['previous_observations']), 2)
        self.assertNotIn('previous_observations', again['previous_observations'][1])

    def test_retry_includes_access_pages_but_not_successful_metadata(self):
        for probe in [{'error': 'DNS'}, {'status': 403}, {'status': 202},
                      {'status': 200, 'flags': ['interstitial_or_access_page']}]:
            self.assertTrue(osint.needs_retry(probe))
        self.assertFalse(osint.needs_retry({'status': 200, 'metadata': {'titles': ['Work']}}))

    def test_many_failed_urls_are_grouped_as_one_host_observation(self):
        urls = ['https://example.org/a', 'https://example.org/b']
        refs = {u: [{'id': 'SRC-1'}] for u in urls}
        groups = osint.host_observations(refs, {u: {'error': 'connection refused'} for u in urls})
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['unresolved_targets'], 2)
        self.assertEqual(groups[0]['record_ids'], ['SRC-1'])

    def test_redirect_hops_are_logged_and_loop_is_bounded(self):
        opener = Opener([Response(status=302, headers={'Location': '/next'}),
                         Response(status=301, headers={'Location': '/start'})])
        p = osint.fetch('https://example.org/start', guard=lambda u: None, opener=opener)
        self.assertEqual(p['error'], 'redirect_loop')
        self.assertEqual([h['status'] for h in p['hops']], [302, 301])
        self.assertEqual(len(opener.urls), 2)

    def test_redirect_to_private_address_is_not_requested(self):
        opener = Opener([Response(status=302, headers={'Location': 'http://127.0.0.1/private'})])
        def resolve(host, port, **kwargs):
            address = '127.0.0.1' if host == '127.0.0.1' else '93.184.216.34'
            return [(2, 1, 6, '', (address, port))]
        with patch('osint.socket.getaddrinfo', side_effect=resolve):
            p = osint.fetch('https://example.org/start', opener=opener)
        self.assertIn('non-public', p['error'])
        self.assertEqual(len(opener.urls), 1)

    def test_sample_hash_cannot_masquerade_as_artifact_hash(self):
        payload = b'%PDF-' + b'a' * 100
        with patch('osint.MAX_BODY', 16):
            p = osint.fetch('https://example.org/file.pdf', guard=lambda u: None,
                            opener=Opener([Response(payload, headers={'Content-Type': 'application/pdf'})]))
        self.assertTrue(p['body_truncated'])
        self.assertEqual(p['body_sample_bytes'], 16)
        self.assertEqual(p['body_sample_sha256'], hashlib.sha256(payload[:16]).hexdigest())
        self.assertNotIn('sha256', p)
        self.assertNotIn('size_bytes', p)

    def test_http_200_verification_page_remains_an_access_limit(self):
        p = osint.fetch('https://example.org/work', guard=lambda u: None,
                        opener=Opener([Response(b'<html><title>Human Verification | Library</title></html>')]))
        self.assertIn('interstitial_or_access_page', p['flags'])

    def test_pdf_url_returning_html_is_flagged(self):
        url = 'https://example.org/file.pdf'
        tables = {'sources': [], 'source_artifacts': [{'id': 'ARTF-1', 'media_type': 'application/pdf'}]}
        refs = {url: [{'table': 'source_artifacts', 'id': 'ARTF-1'}]}
        p = osint.fetch(url, guard=lambda u: None, opener=Opener([Response(b'<html><title>Not the PDF</title></html>')]))
        self.assertIn('pdf_url_returned_html', {x['code'] for x in osint.live_findings(tables, refs, {url: p})})

    def test_audit_preserves_record_coverage_and_evidence_labels(self):
        package, tables = build.load()
        original = copy.deepcopy(tables)
        data = osint.report(package, tables, {})
        self.assertEqual(data['records'], {name: [r['id'] for r in rows] for name, rows in tables.items()})
        self.assertEqual(tables, original)
        self.assertEqual(data['coverage']['targets_observed'], 0)
        self.assertGreater(data['coverage']['unique_targets'], 0)


class DiscoveryTests(unittest.TestCase):
    def test_distributed_artifact_can_be_logged_without_an_http_mirror(self):
        row = {'id': 'SEARCH-IPFS', 'observed_at': '2026-11-04T12:00:00+00:00',
               'source_ids': ['SRC-1'], 'artifact_ids': ['ARTF-1'],
               'question': 'Inspect a content-addressed copy', 'channel': 'distributed', 'tool': 'file_inspection',
               'query': 'Known artifact identifier', 'urls': [], 'role': 'exact_copy', 'outcome': 'inspected',
               'inspected_parts': 'Selected pages of the identified artifact',
               'limits': 'The artifact retains its own capture and authenticity assessment'}
        tables = {'sources': [{'id': 'SRC-1'}], 'source_artifacts': [
            {'id': 'ARTF-1', 'source_id': 'SRC-1', 'ipfs_cid': 'bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku'}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'search.jsonl'
            path.write_text(json.dumps(row) + '\n')
            records, errors = osint.search_observations(tables, [path])
            self.assertEqual(records, [row])
            self.assertFalse(errors)
            tables['source_artifacts'][0]['source_id'] = 'SRC-OTHER'
            self.assertIn('artifacts of the cited sources', osint.search_observations(tables, [path])[1][0])

    def test_search_receipts_validate_source_identity_and_recovery_role(self):
        row = {'id': 'SEARCH-1', 'observed_at': '2026-11-04T12:00:00+00:00', 'source_ids': ['SRC-1'],
               'question': 'Locate the exact manuscript', 'channel': 'library', 'tool': 'local_browser',
               'query': 'Known catalogue URL', 'urls': ['https://example.org/record'],
               'role': 'bibliographic_record', 'outcome': 'metadata_only',
               'inspected_parts': 'Title and shelfmark', 'limits': 'No manuscript pages inspected'}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'searches.jsonl'
            path.write_text(json.dumps(row) + '\n')
            records, errors = osint.search_observations({'sources': [{'id': 'SRC-1'}]}, [path])
            self.assertEqual(records, [row])
            self.assertFalse(errors)
            row['source_ids'] = ['SRC-MISSING']
            path.write_text(json.dumps(row) + '\n')
            self.assertIn('canonical sources', osint.search_observations({'sources': [{'id': 'SRC-1'}]}, [path])[1][0])
            row['source_ids'], row['role'] = ['SRC-1'], 'verified_secret'
            path.write_text(json.dumps(row) + '\n')
            self.assertIn('unknown recovery role', osint.search_observations({'sources': [{'id': 'SRC-1'}]}, [path])[1][0])


if __name__ == '__main__':
    unittest.main()
