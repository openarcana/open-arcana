export const METHODS = {
  leak: { label: 'Leak', plural: 'Leaks', color: '#a55138' },
  exposure_publication: { label: 'Published exposure', plural: 'Published exposures', color: '#92734c' },
  defector_testimony: { label: 'Former-member account', plural: 'Former-member accounts', color: '#816687' },
  court_record: { label: 'Court record', plural: 'Court records', color: '#4d6880' },
  academic_research: { label: 'Research', plural: 'Research', color: '#3b6556' },
  voluntary_release: { label: 'Voluntary release', plural: 'Voluntary releases', color: '#6b7744' },
  journalism: { label: 'Journalism', plural: 'Journalism', color: '#567b7c' },
  investigative_report: { label: 'Investigation report', plural: 'Investigation reports', color: '#986648' },
  reconstruction: { label: 'Reconstruction', plural: 'Reconstructions', color: '#77726b' },
};
export const humanize = value => String(value || 'Unknown').replaceAll('_', ' ').replace(/^./, s => s.toUpperCase());
export const normalize = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
export function numericYear(value) {
  return /^-?\d+$/.test(String(value).trim()) ? Number(value) : null;
}
export function dateLabel(record) {
  if (record.yearNumber === null) return 'Undated';
  const year = record.yearNumber < 0 ? `${Math.abs(record.yearNumber)} BCE` : record.yearNumber < 1000 ? `${record.yearNumber} CE` : String(record.yearNumber);
  return `${record.date_precision === 'circa' ? 'c. ' : ''}${year}`;
}
export function hydrate(payload) {
  const tables = payload.tables;
  const index = table => new Map(table.map(r => [r.id, r]));
  const traditions = index(tables.traditions), items = index(tables.restricted_items), sources = index(tables.sources);
  return tables.disclosures.map(d => {
    const item = items.get(d.item_id), tradition = traditions.get(item.tradition_id), source = sources.get(d.source_id);
    const claims = tables.claims.filter(c => c.item_id === item.id);
    const artifacts = tables.source_artifacts.filter(a => a.source_id === source.id);
    const row = { ...d, item, tradition, source, claims, artifacts, yearNumber: numericYear(d.year),
      countries: tradition.geography.countries, originEra: tradition.origin_era };
    row.searchText = normalize([d.id, d.coverage, d.notes, item.name, item.description, item.secrecy_type,
      tradition.name, tradition.region, source.title, source.author, ...claims.map(c => c.statement)].join(' '));
    return row;
  });
}
export function matches(row, filters, ignore = '') {
  if (ignore !== 'country' && filters.country && !(filters.country === 'unassigned' ? row.countries.length === 0 : row.countries.includes(filters.country))) return false;
  if (filters.method && row.disclosure_method !== filters.method) return false;
  if (filters.status && row.item.current_status !== filters.status) return false;
  if (filters.type && row.item.secrecy_type !== filters.type) return false;
  if (filters.review && row.review_status !== filters.review) return false;
  if (filters.history === 'origins_before_1900' && row.originEra !== 'before_1900') return false;
  if (filters.history === 'origins_since_1900' && row.originEra !== 'since_1900') return false;
  if (filters.history === 'origins_undated' && row.originEra !== 'undated') return false;
  const sourceYear = numericYear(row.source.original_year);
  if (filters.history === 'sources_before_1900' && (sourceYear === null || sourceYear >= 1900)) return false;
  if (filters.history === 'sources_since_1900' && (sourceYear === null || sourceYear < 1900)) return false;
  if (filters.q && !normalize(filters.q).split(/\s+/).every(t => row.searchText.includes(t))) return false;
  if (ignore !== 'year') {
    if (row.yearNumber === null) return filters.undated !== false;
    if (filters.from !== '' && filters.from != null && row.yearNumber < Number(filters.from)) return false;
    if (filters.to !== '' && filters.to != null && row.yearNumber > Number(filters.to)) return false;
  }
  return true;
}
export function filteredRows(rows, filters, ignore = '') { return rows.filter(r => matches(r, filters, ignore)); }
export function countryCounts(rows) {
  const counts = new Map();
  for (const row of rows) for (const code of new Set(row.countries)) counts.set(code, (counts.get(code) || 0) + 1);
  return counts;
}
export function timelineGroups(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (row.yearNumber === null) continue;
    const key = `${row.disclosure_method}:${row.yearNumber}`;
    if (!groups.has(key)) groups.set(key, { year: row.yearNumber, method: row.disclosure_method, records: [] });
    groups.get(key).records.push(row);
  }
  return [...groups.values()].sort((a, b) => a.year - b.year);
}
export function timelineClusters(rows, yearSpan) {
  const clusters = [];
  for (const method of Object.keys(METHODS)) {
    let current;
    for (const group of timelineGroups(rows).filter(g => g.method === method)) {
      if (!current || group.year - current.start > yearSpan) {
        current = { start: group.year, end: group.year, year: group.year, method, records: [] };
        clusters.push(current);
      }
      current.end = group.year;
      current.year = (current.start + current.end) / 2;
      current.records.push(...group.records);
    }
  }
  return clusters;
}
export function csvExport(rows) {
  const fields = ['id', 'year', 'date_precision', 'disclosure_method', 'extent', 'review_status', 'item',
    'tradition', 'country_associations', 'recorded_region', 'recorded_practice_status', 'status_as_of',
    'status_is_provisional', 'source', 'source_authenticity', 'source_url', 'coverage', 'notes'];
  const cell = v => {
    let text = String(v ?? '');
    if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  return [fields, ...rows.map(r => [r.id, r.year, r.date_precision, r.disclosure_method, r.extent, r.review_status,
    r.item.name, r.tradition.name, r.countries.join(';'), r.tradition.region, r.item.current_status,
    r.item.status_as_of, r.item.current_status !== 'unknown' && !(r.item.status_as_of && r.item.status_claim_ids),
    r.source.title, r.source.source_authenticity, r.source.url, r.coverage, r.notes])].map(r => r.map(cell).join(',')).join('\r\n');
}
export function sortedRows(rows, order) {
  return [...rows].sort((a, b) => {
    if (order === 'tradition') return a.tradition.name.localeCompare(b.tradition.name) || (a.yearNumber ?? Infinity) - (b.yearNumber ?? Infinity);
    if (a.yearNumber === null) return b.yearNumber === null ? a.id.localeCompare(b.id) : 1;
    if (b.yearNumber === null) return -1;
    return (order === 'oldest' ? 1 : -1) * (a.yearNumber - b.yearNumber) || a.id.localeCompare(b.id);
  });
}
