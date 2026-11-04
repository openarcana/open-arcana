import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { hydrate, filteredRows, countryCounts, timelineGroups, timelineClusters, csvExport, numericYear, sortedRows } from '../site/lib.mjs';

const payload = JSON.parse(readFileSync(new URL('../_site/data.json', import.meta.url)));
const rows = hydrate(payload);
const all = { country: '', method: '', history: '', status: '', type: '', review: '', q: '', from: '', to: '', undated: true };

test('every canonical disclosure remains one explorer row', () => {
  assert.equal(rows.length, payload.counts.disclosures);
  assert.equal(new Set(rows.map(r => r.id)).size, rows.length);
  assert.ok(rows.every(r => r.item && r.source && r.tradition));
});
test('leak and historical-origin filters intersect, without inferring discontinued practice', () => {
  const result = filteredRows(rows, { ...all, method: 'leak', history: 'origins_before_1900' });
  assert.equal(result.length, 3);
  assert.ok(result.every(r => r.disclosure_method === 'leak' && r.originEra === 'before_1900'));
  assert.equal(filteredRows(rows, { ...all, method: 'leak', history: 'origins_before_1900', status: 'discontinued' }).length, 0);
});
test('country selection and cross-border counts retain distinct disclosure grain', () => {
  const argentina = filteredRows(rows, { ...all, country: 'AR' });
  assert.equal(argentina.length, 2);
  assert.deepEqual(argentina.map(r => r.id), filteredRows(rows, { ...all, country: 'CL' }).map(r => r.id));
  assert.equal(countryCounts(argentina).get('AR'), 2);
  assert.equal(countryCounts(argentina).get('CL'), 2);
  assert.ok(filteredRows(rows, { ...all, country: 'unassigned' }).every(r => !r.countries.length));
});
test('inclusive date filtering preserves undated records only when selected', () => {
  assert.equal(numericYear(''), null); assert.equal(numericYear('c. 1900'), null); assert.equal(numericYear('195'), 195);
  const dated = filteredRows(rows, { ...all, from: '1900', to: '1999', undated: false });
  assert.ok(dated.every(r => r.yearNumber >= 1900 && r.yearNumber <= 1999));
  assert.equal(filteredRows(rows, { ...all, from: '1900', to: '1999' }).length - dated.length, 6);
  assert.equal(timelineGroups(rows).reduce((n, g) => n + g.records.length, 0), rows.length - 6);
});
test('query matches source and claim text with diacritic-insensitive terms', () => {
  const result = filteredRows(rows, { ...all, q: 'sami drum' });
  assert.ok(result.length > 0); assert.ok(result.every(r => r.tradition.id === 'TRAD-0029'));
  assert.equal(filteredRows(rows, { ...all, q: '<script>not-an-archive-term</script>' }).length, 0);
});
test('exports use the selected rows, carry qualifications and escape spreadsheet formulae', () => {
  const result = filteredRows(rows, { ...all, method: 'leak', history: 'origins_before_1900' });
  const csv = csvExport(result);
  assert.equal(csv.split('\r\n').length, result.length + 1);
  assert.ok(csv.includes('"source_authenticity"')); assert.ok(csv.includes('"status_is_provisional"'));
  assert.ok(result.every(r => csv.includes(r.id)));
  const malicious = { ...result[0], notes: '=HYPERLINK("https://example.com")' };
  assert.ok(csvExport([malicious]).includes("'=HYPERLINK"));
});
test('date sorting always keeps unknown dates separate from dated records', () => {
  for (const sort of ['newest', 'oldest']) {
    const result = sortedRows(rows, sort);
    assert.ok(result.slice(-6).every(r => r.yearNumber === null));
  }
});
test('timeline clustering preserves every dated record and its true date span', () => {
  const clusters = timelineClusters(rows, 35);
  assert.equal(clusters.flatMap(g => g.records).length, rows.filter(r => r.yearNumber !== null).length);
  assert.equal(new Set(clusters.flatMap(g => g.records.map(r => r.id))).size, rows.filter(r => r.yearNumber !== null).length);
  for (const group of clusters) {
    assert.ok(group.end - group.start <= 35);
    assert.ok(group.records.every(r => r.yearNumber >= group.start && r.yearNumber <= group.end && r.disclosure_method === group.method));
  }
});
