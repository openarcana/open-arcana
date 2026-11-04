"""Check the explorer's derived geography, dates and source-data boundary."""
import json
import copy
import hashlib
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import build_site
import site_documents


class PageMarkup(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.elements = []
        self.scripts = []
        self.script_data = []
        self.in_script = False
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.elements.append((tag, attrs))
        if tag in ('a', 'link') and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag in ('script', 'img') and 'src' in attrs:
            self.links.append(attrs['src'])
        if tag == 'script':
            self.scripts.append(attrs)
            self.in_script = True
            self.script_data.append('')

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False

    def handle_data(self, value):
        if self.in_script:
            self.script_data[-1] += value


class SiteDataTests(unittest.TestCase):
    def test_origins_do_not_invent_dates_for_undated_traditions(self):
        for value in ('', 'unknown', 'date unestablished'):
            self.assertEqual(build_site.origin_era(value), 'undated')
        for value in ('ancient', '6th century BCE', '8th century', '1830', '1870s'):
            self.assertEqual(build_site.origin_era(value), 'before_1900')
        for value in ('1954', 'c. 1904–1912', '20th century'):
            self.assertEqual(build_site.origin_era(value), 'since_1900')

    def test_site_preserves_canonical_grain_and_snapshot(self):
        package, tables = build.load()
        dataset, inputs = build.snapshot(package)
        payload = build_site.make_payload()
        self.assertEqual(payload['dataset'], dataset)
        self.assertEqual(payload['canonical_inputs'], inputs)
        self.assertEqual(payload['counts'], {k: len(v) for k, v in tables.items()})
        for name, rows in tables.items():
            for canonical, derived in zip(rows, payload['tables'][name]):
                self.assertEqual(canonical, {k: derived[k] for k in canonical})

    def test_broad_regions_are_not_assigned_to_every_modern_country(self):
        traditions = {t['id']: t for t in build_site.make_payload()['tables']['traditions']}
        for ident in ('TRAD-0001', 'TRAD-0006', 'TRAD-0009', 'TRAD-0017', 'TRAD-0027'):
            self.assertEqual(traditions[ident]['geography']['countries'], [])
        self.assertEqual(traditions['TRAD-0040']['geography']['countries'], ['AR', 'CL'])
        self.assertEqual(traditions['TRAD-0045']['origin_era'], 'undated')

    def test_review_and_provisional_status_qualifications_are_preserved(self):
        p = build_site.make_payload()['tables']
        item = next(i for i in p['restricted_items'] if i['id'] == 'ITEM-0001')
        self.assertIn('status_without_dated_evidence', [q['code'] for q in item['quality_issues']])
        self.assertTrue(any(s['source_authenticity'] == 'unassessed' for s in p['sources']))
        self.assertTrue(any(d['year'] == '' for d in p['disclosures']))


class PublishedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.destination = Path(cls.temp.name).resolve()
        build_site.write_site(cls.destination)
        cls.records = [json.loads(line) for line in (build.ROOT / 'exports/disclosures.jsonl').read_text().splitlines()]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_every_disclosure_has_crawlable_evidence_and_lossless_json(self):
        for record in self.records:
            folder = self.destination / 'records' / record['id']
            text = (folder / 'index.html').read_text()
            data = json.loads((folder / 'index.json').read_text())
            self.assertEqual({key: data[key] for key in record}, record)
            self.assertIn(escape(record['coverage'] or 'Not recorded.'), text)
            for qualification in record['quality_issues']:
                self.assertIn(escape(qualification['message']), text)
            self.assertTrue(all(s.get('type') == 'application/ld+json' for s in PageMarkup(text).scripts))
        partial = (self.destination / 'records/DISC-0088/index.html').read_text()
        self.assertIn('Provisional: no dated status evidence is linked.', partial)
        self.assertIn('authenticity: Unassessed', partial)
        self.assertIn('no full audio review', partial)

    def test_all_local_page_links_resolve_on_a_mirror_too(self):
        for page in self.destination.rglob('*.html'):
            for link in PageMarkup(page.read_text()).links:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = (page.parent / unquote(parsed.path)).resolve()
                self.assertTrue(target.is_relative_to(self.destination), (page, link))
                self.assertTrue(target.is_file() or (target / 'index.html').is_file(), (page, link))

    def test_sitemap_robot_permissions_and_dataset_distributions_are_consistent(self):
        origin = site_documents.site_url()
        urls = [node.text for node in ET.parse(self.destination / 'sitemap.xml').iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(len(urls), len(self.records) + 3)
        self.assertEqual(len(urls), len(set(urls)))
        robots = RobotFileParser()
        robots.parse((self.destination / 'robots.txt').read_text().splitlines())
        for url in urls:
            self.assertTrue(url.startswith(origin + '/'))
            self.assertTrue((self.destination / url[len(origin) + 1:] / 'index.html').is_file())
            for agent in ('Googlebot', 'bingbot', 'OAI-SearchBot', 'GPTBot', 'ClaudeBot'):
                self.assertTrue(robots.can_fetch(agent, url))
        schema = json.loads(PageMarkup((self.destination / 'dataset/index.html').read_text()).script_data[0])
        self.assertEqual(schema['@type'], 'Dataset')
        self.assertEqual(schema['license'], site_documents.CC0)
        self.assertIn('cited works retain their own rights', schema['description'])
        for download in schema['distribution']:
            self.assertTrue((self.destination / download['contentUrl'][len(origin) + 1:]).is_file())

    def test_published_exports_and_csvs_keep_their_bytes_and_checksums(self):
        for line in (self.destination / 'exports/SHA256SUMS').read_text().splitlines():
            digest, name = line.split('  ')
            self.assertEqual(hashlib.sha256((self.destination / 'exports' / name).read_bytes()).hexdigest(), digest)
        package, _ = build.load()
        for resource in package['resources']:
            path = Path(resource['path'])
            self.assertEqual((self.destination / path).read_bytes(), (build.ROOT / path).read_bytes())
        self.assertEqual((self.destination / 'datapackage.json').read_bytes(), (build.ROOT / 'datapackage.json').read_bytes())

    def test_source_text_cannot_break_html_or_structured_data(self):
        attack = '</script><script>alert("x")</script><img src=x onerror=alert(1)>'
        record = copy.deepcopy(self.records[0])
        record['item']['name'] = record['source']['title'] = attack
        page = site_documents.document('records/test/', attack, attack,
            site_documents.record_body(record, []), 'https://example.org', {'name': attack})
        parsed = PageMarkup(page)
        self.assertEqual(parsed.scripts, [{'type': 'application/ld+json'}])
        self.assertEqual(json.loads(parsed.script_data[0])['name'], attack)
        self.assertIn(escape(attack), page)
        self.assertFalse(any(name.startswith('on') for _, attrs in parsed.elements for name in attrs))
        self.assertFalse(any(tag == 'img' and attrs.get('src') == 'x' for tag, attrs in parsed.elements))

    def test_rebuild_removes_obsolete_generated_record_files_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            old = destination / 'records/DISC-9999'
            old.mkdir(parents=True)
            for name in ('index.html', 'index.json', 'unrelated.txt'):
                (old / name).write_text('old')
            build_site.write_site(destination)
            self.assertFalse((old / 'index.html').exists())
            self.assertFalse((old / 'index.json').exists())
            self.assertEqual((old / 'unrelated.txt').read_text(), 'old')


if __name__ == '__main__':
    unittest.main()
