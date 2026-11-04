"""Check the explorer's derived geography, dates and source-data boundary."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import build_site


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


if __name__ == '__main__':
    unittest.main()
