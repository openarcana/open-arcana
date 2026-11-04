import { METHODS, humanize, hydrate, dateLabel, filteredRows, countryCounts, timelineClusters, csvExport, sortedRows } from './lib.mjs';

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const SVG = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs = {}, text = '') => {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, String(v));
  if (text) el.textContent = text;
  return el;
};
const defaults = { q: '', country: '', method: '', history: '', status: '', type: '', review: '', from: '', to: '', undated: true, sort: 'newest' };
let state = { ...defaults }, rows = [], countries = [], payload, selected = [], limit = 12;
const tip = $('tooltip');
const allYears = () => rows.filter(r => r.yearNumber !== null).map(r => r.yearNumber);
const nameOf = code => countries.find(c => c.id === code)?.name || code;
const safeURL = value => {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : ''; }
  catch { return ''; }
};
const link = (url, label, className = '') => {
  const href = safeURL(url);
  return href ? `<a class="${className}" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>` : '';
};
function showTip(text, element, event) {
  tip.textContent = text; tip.hidden = false;
  const box = element.getBoundingClientRect();
  const x = event?.clientX ?? box.left + box.width / 2, y = event?.clientY ?? box.top;
  tip.style.left = `${Math.max(10, Math.min(x + 13, innerWidth - tip.offsetWidth - 12))}px`;
  tip.style.top = `${Math.max(10, Math.min(y + 14, innerHeight - tip.offsetHeight - 12))}px`;
}
function interactive(el, text, action) {
  el.addEventListener('pointerenter', e => showTip(text, el, e));
  el.addEventListener('pointermove', e => showTip(text, el, e));
  el.addEventListener('pointerleave', () => { tip.hidden = true; });
  el.addEventListener('focus', () => showTip(text, el));
  el.addEventListener('blur', () => { tip.hidden = true; });
  el.addEventListener('click', () => { tip.hidden = true; action(); });
  el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tip.hidden = true; action(); } });
}
function readURL() {
  const params = new URLSearchParams(location.search);
  state = { ...defaults };
  state.q = (params.get('q') || '').slice(0, 300);
  for (const field of ['country', 'method', 'history', 'status', 'type', 'review', 'sort']) {
    if ([...$(field).options].some(o => o.value === params.get(field))) state[field] = params.get(field);
  }
  for (const field of ['from', 'to']) if (/^-?\d{1,4}$/.test(params.get(field) || '')) state[field] = params.get(field);
  if (state.from && state.to && Number(state.from) > Number(state.to)) [state.from, state.to] = [state.to, state.from];
  state.undated = params.get('undated') !== '0';
  return params.get('record');
}
function saveURL(record = '') {
  const p = new URLSearchParams();
  for (const [key, value] of Object.entries(state)) {
    if (key === 'undated') { if (!value) p.set(key, '0'); }
    else if (value && value !== defaults[key]) p.set(key, value);
  }
  if (record) p.set('record', record);
  history.replaceState(null, '', `${location.pathname}${p.size ? `?${p}` : ''}${location.hash}`);
}
function syncControls() {
  for (const field of ['country', 'method', 'history', 'status', 'type', 'review', 'sort', 'from', 'to']) $(field).value = state[field];
  $('search').value = state.q;
  $('undated').checked = state.undated;
  const custom = $('window').querySelector('[value="custom"]');
  if (custom) custom.remove();
  if (!state.from && !state.to) $('window').value = 'full';
  else if (!state.to && ['1500', '1800', '1900', '1950'].includes(state.from)) $('window').value = state.from;
  else { $('window').add(new Option('Custom range', 'custom')); $('window').value = 'custom'; }
  if (state.status || state.type || state.review) {
    $('advanced-filters').hidden = false; $('more-filters').setAttribute('aria-expanded', 'true');
  }
}
function change(key, value) { state[key] = value; limit = 12; saveURL(); render(); }
function mapView() {
  const base = filteredRows(rows, state), counts = countryCounts(base), max = Math.max(1, ...counts.values());
  const root = svg('svg', { viewBox: '0 0 960 445', role: 'group', 'aria-label': 'Country associations. The country index provides the same selection.' });
  const project = ([lon, lat]) => [(lon + 180) * 960 / 360, (85 - lat) * 445 / 145];
  const grid = svg('g', { class: 'graticule', 'aria-hidden': 'true' });
  for (let lon = -120; lon <= 120; lon += 60) { const [x] = project([lon, 0]); grid.append(svg('path', { d: `M${x} 15V430` })); }
  for (const lat of [-30, 0, 30, 60]) { const [, y] = project([0, lat]); grid.append(svg('path', { d: `M5 ${y}H955` })); }
  root.append(grid);
  for (const country of countries) {
    const polygons = country.geometry.type === 'Polygon' ? [country.geometry.coordinates] : country.geometry.coordinates;
    const d = polygons.map(poly => poly.map(ring => ring.map((point, i) => `${i ? 'L' : 'M'}${project(point).map(n => n.toFixed(2)).join(',')}`).join('') + 'Z').join('')).join('');
    const n = counts.get(country.id) || 0, active = state.country === country.id;
    const path = svg('path', { d, class: `country${n ? ' has-records' : ''}${active ? ' selected' : ''}`, 'fill-rule': 'evenodd', 'data-country': country.id });
    if (n) {
      const fraction = Math.sqrt(n / max), light = 83 - fraction * 53;
      path.style.fill = `hsl(103 ${14 + fraction * 10}% ${light}%)`;
      path.setAttribute('tabindex', '0'); path.setAttribute('role', 'button'); path.setAttribute('aria-pressed', String(active));
      path.setAttribute('aria-label', `${country.name}: ${n} disclosure${n === 1 ? '' : 's'}; ${active ? 'clear selection' : 'filter country'}`);
      interactive(path, `${country.name}\n${n} disclosure record${n === 1 ? '' : 's'}`, () => change('country', active ? '' : country.id));
    } else {
      path.setAttribute('aria-hidden', 'true');
      path.addEventListener('pointerenter', e => showTip(`${country.name}\nNo mapped records in this view`, path, e));
      path.addEventListener('pointerleave', () => { tip.hidden = true; });
    }
    root.append(path);
  }
  for (const [label, lon, lat] of [['NORTH AMERICA', -105, 33], ['SOUTH AMERICA', -60, -16], ['EUROPE', 15, 54], ['AFRICA', 20, 6], ['ASIA', 85, 42], ['OCEANIA', 133, -30]]) {
    const [x, y] = project([lon, lat]); root.append(svg('text', { x, y, class: 'map-label', 'text-anchor': 'middle', 'aria-hidden': 'true' }, label));
  }
  $('world-map').replaceChildren(root);
  const index = [...counts].sort((a, b) => b[1] - a[1] || nameOf(a[0]).localeCompare(nameOf(b[0])));
  $('country-list').innerHTML = index.length ? index.map(([code, count]) => `<button type="button" class="country-row${state.country === code ? ' active' : ''}" data-country="${esc(code)}" aria-pressed="${state.country === code}"><span>${esc(nameOf(code))}<span class="bar" style="width:${Math.max(4, count / max * 100)}%"></span></span><span class="count">${count}</span></button>`).join('') : '<p class="map-footnote">No country associations in this selection.</p>';
  $('country-list').querySelectorAll('button').forEach(b => b.addEventListener('click', () => change('country', state.country === b.dataset.country ? '' : b.dataset.country)));
  const unmapped = base.filter(r => !r.countries.length).length;
  $('unmapped').textContent = `${unmapped} worldwide / regional-only records ↗`;
  $('unmapped').setAttribute('aria-pressed', String(state.country === 'unassigned'));
}
function timelineView(current) {
  const selectionYears = filteredRows(rows, state, 'year').filter(r => r.yearNumber !== null).map(r => r.yearNumber);
  const years = selectionYears.length ? selectionYears : allYears(), min = Math.min(...years), max = Math.max(...years);
  let start = state.from === '' ? min : Number(state.from), end = state.to === '' ? max : Number(state.to);
  if (end < start) { if (state.from === '') start = end - 1; else end = start + 1; }
  if (end === start) { start -= 1; end += 1; }
  const w = 1120, left = 177, right = 27, top = 30, lane = 33, bottom = top + Object.keys(METHODS).length * lane;
  const x = year => left + (year - start) / (end - start) * (w - left - right);
  const root = svg('svg', { viewBox: `0 0 ${w} ${bottom + 39}`, role: 'group', 'aria-label': `Disclosure timeline, ${start} to ${end}. Use the From year and To year inputs for keyboard date selection.` });
  const defs = svg('defs'), clip = svg('clipPath', { id: 'plot-clip' });
  clip.append(svg('rect', { x: left - 12, y: top - 15, width: w - left - right + 24, height: bottom - top + 15 })); defs.append(clip); root.append(defs);
  const span = end - start, step = span > 1400 ? 250 : span > 600 ? 100 : span > 240 ? 50 : span > 110 ? 20 : span > 50 ? 10 : span > 20 ? 5 : span > 10 ? 2 : 1;
  const ticks = new Set([start, end]);
  for (let year = Math.ceil(start / step) * step; year < end; year += step) if (year - start > span * .045 && end - year > span * .045) ticks.add(year);
  for (const year of [...ticks].sort((a, b) => a - b)) {
    root.append(svg('line', { x1: x(year), x2: x(year), y1: top - 17, y2: bottom, class: 'plot-grid' }));
    root.append(svg('text', { x: x(year), y: bottom + 24, class: 'tick-label', 'text-anchor': 'middle' }, year < 0 ? `${Math.abs(year)} BCE` : year < 1000 ? `${year} CE` : String(year)));
  }
  const methods = Object.keys(METHODS);
  for (const [i, method] of methods.entries()) {
    const y = top + i * lane;
    root.append(svg('line', { x1: left, x2: w - right, y1: y, y2: y, class: 'lane-rule' }));
    const label = svg('text', { x: 0, y: y + 4, class: 'method-label', tabindex: '0', role: 'button', 'aria-label': `Filter ${METHODS[method].plural}`, 'aria-pressed': String(state.method === method) }, METHODS[method].plural);
    interactive(label, `Select ${METHODS[method].plural.toLowerCase()}`, () => change('method', state.method === method ? '' : method)); root.append(label);
  }
  const marks = svg('g', { 'clip-path': 'url(#plot-clip)' });
  for (const group of timelineClusters(current, (end - start) / (w - left - right) * 18)) {
    const { records, year, method } = group, y = top + methods.indexOf(method) * lane, radius = Math.min(11, 4.2 + Math.sqrt(records.length - 1) * 2.3);
    const label = group.start === group.end ? dateLabel(records[0]) : `${group.start}–${group.end}`;
    if (group.start !== group.end) marks.append(svg('line', { x1: x(group.start), x2: x(group.end), y1: y, y2: y, stroke: METHODS[method].color, 'stroke-width': 2.5, opacity: .6, 'aria-hidden': 'true' }));
    const mark = svg('circle', { cx: x(year), cy: y, r: radius, fill: METHODS[method].color, class: 'timeline-mark', tabindex: '0', role: 'button',
      'aria-label': `${label}: ${records.length} ${METHODS[method].plural.toLowerCase()} disclosure record${records.length === 1 ? '' : 's'}` });
    interactive(mark, `${label} · ${METHODS[method].plural}\n${records.length > 1 ? `${records.length} disclosures — inspect or zoom` : records[0].item.name}`, () => records.length === 1 ? openRecord(records[0]) : openGroup(group));
    marks.append(mark);
    if (records.length > 1) marks.append(svg('text', { x: x(year), y: y + 3, class: 'mark-count' }, String(records.length)));
  }
  root.append(marks);
  let brushStart = null, rect = null;
  const coordinate = e => { const point = root.createSVGPoint(); point.x = e.clientX; point.y = e.clientY; return point.matrixTransform(root.getScreenCTM().inverse()); };
  root.addEventListener('pointerdown', e => {
    const p = coordinate(e);
    if (e.button !== 0 || p.x < left || p.x > w - right || p.y < top - 15 || p.y > bottom || e.target.closest('[role="button"]')) return;
    brushStart = p.x; root.setPointerCapture(e.pointerId);
    rect = svg('rect', { x: p.x, y: top - 15, width: 0, height: bottom - top + 15, class: 'brush' }); root.append(rect);
  });
  root.addEventListener('pointermove', e => {
    if (brushStart === null) return;
    const xx = Math.max(left, Math.min(w - right, coordinate(e).x));
    rect.setAttribute('x', Math.min(xx, brushStart)); rect.setAttribute('width', Math.abs(xx - brushStart));
  });
  const finishBrush = e => {
    if (brushStart === null) return;
    const xx = Math.max(left, Math.min(w - right, coordinate(e).x)), first = brushStart; brushStart = null;
    rect?.remove(); rect = null;
    if (Math.abs(xx - first) < 8) return;
    const yearAt = xx => Math.round(start + (xx - left) / (w - left - right) * (end - start));
    state.from = String(yearAt(Math.min(xx, first))); state.to = String(yearAt(Math.max(xx, first)));
    limit = 12; saveURL(); render();
  };
  root.addEventListener('pointerup', finishBrush);
  root.addEventListener('pointercancel', () => { brushStart = null; rect?.remove(); });
  $('timeline').replaceChildren(root);
  const undated = current.filter(r => r.yearNumber === null).length;
  $('date-summary').textContent = `${current.length - undated} dated records shown${undated ? ` · ${undated} undated records in the list` : ''}`;
  $('undated-count').textContent = `(${filteredRows(rows, state, 'year').filter(r => r.yearNumber === null).length})`;
}
function methodBadge(method) {
  return `<span class="method-badge"><i class="method-dot" style="background:${METHODS[method]?.color || '#777'}"></i>${esc(METHODS[method]?.label || humanize(method))}</span>`;
}
function renderList() {
  const ordered = sortedRows(selected, state.sort), visible = ordered.slice(0, limit);
  $('record-count').textContent = `(${ordered.length})`;
  $('record-list').innerHTML = visible.length ? visible.map(r => `<button class="record-row" type="button" data-record="${esc(r.id)}" aria-label="Open ${esc(r.id)}: ${esc(r.item.name)}"><span class="record-date">${esc(dateLabel(r))}<small>${esc(r.extent.toUpperCase())}</small></span><span><span class="record-title">${esc(r.item.name)}</span><span class="record-context">${esc(r.tradition.name)} · ${esc(r.countries.length ? r.countries.map(nameOf).join(', ') : r.tradition.region)}</span></span><span class="record-meta">${methodBadge(r.disclosure_method)}<br>${r.review_status === 'reviewed' ? 'Reviewed against source' : esc(humanize(r.review_status))} · ${esc(r.id)}</span><span class="record-arrow" aria-hidden="true">↗</span></button>`).join('') : '<div class="empty-state"><strong>No records match this selection.</strong>Try a wider date range, another country, or reset the filters.</div>';
  $('record-list').querySelectorAll('[data-record]').forEach(b => b.addEventListener('click', () => openRecord(rows.find(r => r.id === b.dataset.record))));
  $('show-more').hidden = limit >= ordered.length;
  $('show-more').textContent = `Show ${Math.min(12, ordered.length - limit)} more records ↓`;
  $('download').disabled = !selected.length;
}
function activeChips() {
  const labels = { country: 'Country', method: 'Disclosure', history: 'Context', status: 'Status', type: 'Material', review: 'Review' };
  const chips = [];
  if (state.q) chips.push(['q', `Search: ${state.q}`]);
  for (const [key, label] of Object.entries(labels)) if (state[key]) chips.push([key, `${label}: ${$(key).selectedOptions[0]?.textContent || state[key]}`]);
  if (state.from || state.to) chips.push(['years', `${state.from || 'Earliest'}–${state.to || 'Latest'}`]);
  if (!state.undated) chips.push(['undated', 'Dated records only']);
  $('active-filters').innerHTML = chips.map(([key, text]) => `<button class="filter-chip" type="button" data-clear="${key}" aria-label="Remove ${esc(text)}">${esc(text)}<span aria-hidden="true">×</span></button>`).join('');
  $('active-filters').querySelectorAll('button').forEach(b => b.addEventListener('click', () => {
    const key = b.dataset.clear;
    if (key === 'years') { state.from = ''; state.to = ''; }
    else state[key] = defaults[key];
    limit = 12; saveURL(); render();
  }));
  $('reset').disabled = !chips.length;
}
function render() {
  tip.hidden = true; syncControls(); selected = filteredRows(rows, state);
  const traditions = new Set(selected.map(r => r.tradition.id)).size, items = new Set(selected.map(r => r.item.id)).size;
  $('selection-summary').innerHTML = `<strong>${selected.length}</strong> of ${rows.length} disclosures <span aria-hidden="true">·</span> ${items} restricted item${items === 1 ? '' : 's'} <span aria-hidden="true">·</span> ${traditions} tradition${traditions === 1 ? '' : 's'}`;
  activeChips(); mapView(); timelineView(selected); renderList();
}
function presentDialog() { tip.hidden = true; if (!$('record-dialog').open) $('record-dialog').showModal(); }
function openGroup(group) {
  const period = group.start === group.end ? String(group.start) : `${group.start}–${group.end}`;
  $('detail-id').textContent = `${period} / ${METHODS[group.method].plural.toUpperCase()}`;
  $('record-detail').innerHTML = `<h2 id="detail-title">${group.records.length} disclosures · ${period}</h2>${group.start !== group.end ? '<button id="zoom-group" type="button" class="small-button">Zoom to these years ↗</button>' : ''}<div class="group-list">${group.records.map(r => `<button type="button" data-record="${r.id}">${esc(r.item.name)}<span class="record-context">${esc(dateLabel(r))} · ${esc(r.tradition.name)} · ${r.id}</span></button>`).join('')}</div>`;
  $('record-detail').querySelectorAll('[data-record]').forEach(b => b.addEventListener('click', () => openRecord(rows.find(r => r.id === b.dataset.record))));
  $('zoom-group')?.addEventListener('click', () => {
    state.from = String(group.start); state.to = String(group.end); limit = 12; saveURL(); render();
    $('record-dialog').close(); $('timeline-heading').scrollIntoView({ block: 'start', behavior: 'smooth' });
  });
  presentDialog();
}
function sourceLinks(source) {
  const prefixes = { doi: 'https://doi.org/', ia: 'https://archive.org/details/', ol: 'https://openlibrary.org/works/', isbn: 'https://openlibrary.org/isbn/', oclc: 'https://search.worldcat.org/title/', wikidata: 'https://www.wikidata.org/wiki/', courtlistener: 'https://www.courtlistener.com/opinion/' };
  return (source.identifiers || '').split(';').filter(Boolean).map(identifier => {
    const i = identifier.indexOf(':'), prefix = identifier.slice(0, i), value = identifier.slice(i + 1);
    return prefixes[prefix] ? link(prefixes[prefix] + encodeURIComponent(value), identifier, 'source-link') : esc(identifier);
  }).join(' · ');
}
function openRecord(row) {
  if (!row) return;
  const { item, tradition, source } = row;
  const provisional = item.current_status !== 'unknown' && !(item.status_as_of && item.status_claim_ids);
  $('detail-id').textContent = `${row.id} / ${item.id}`;
  const claimHTML = row.claims.map(c => `<article class="claim"><small>${esc(humanize(c.claim_type))} · ${esc(humanize(c.claim_support))} · ${esc(humanize(c.review_status))}</small><p>${esc(c.statement)}</p><small>${esc(c.period)}${c.period ? ' · ' : ''}${esc(c.locators || 'No exact locator recorded')}</small><details><summary>Sources and assessment</summary><p>Supporting sources: ${esc(c.supporting_source_ids || 'None recorded')}<br>Contradicting sources: ${esc(c.contradicting_source_ids || 'None recorded')}<br>Counted independent: ${esc(c.independent_source_ids || 'None recorded')}</p><p>${esc(c.verification_notes || 'No assessment note recorded.')}</p></details></article>`).join('');
  $('record-detail').innerHTML = `<div class="dialog-dateline">${esc(dateLabel(row))} · ${methodBadge(row.disclosure_method)}</div><h2 id="detail-title">${esc(item.name)}</h2><p class="dialog-dateline">${esc(tradition.name)}<br>${esc(tradition.region)}</p><div class="detail-tags"><span class="detail-tag">${esc(humanize(item.secrecy_type))}</span><span class="detail-tag">${esc(humanize(row.extent))} disclosure</span><span class="detail-tag">${row.review_status === 'reviewed' ? 'Reviewed against source' : esc(humanize(row.review_status))}</span></div><p class="detail-lead">${esc(item.description)}</p><div class="detail-grid"><div><h3>Access & transmission</h3><p>${esc(item.restricted_to)}</p><p>${esc(humanize(item.restriction_mechanism.split(';').join(', ')))}</p><p class="evidence-note">Stated reason: ${esc(item.stated_reason || 'Not recorded')}</p></div><div><h3>Recorded practice status</h3><p>${esc(humanize(item.current_status))}${item.status_as_of ? ` · as of ${esc(item.status_as_of)}` : ''}</p>${provisional ? '<p class="provisional">Provisional: no dated status evidence is linked.</p>' : ''}<p class="evidence-note">${esc(tradition.founded ? `Tradition origins: ${tradition.founded}` : 'Tradition origins undated.')}</p><p class="evidence-note">${esc(tradition.geography.basis)}</p></div></div><section class="detail-section"><h3>What this disclosure covers</h3><p>${esc(row.coverage || 'Exact coverage has not been specified.')}</p>${row.notes ? `<p class="evidence-note">${esc(row.notes)}</p>` : ''}<p class="evidence-note">Date precision: ${esc(humanize(row.date_precision))}. A disclosure date does not establish a practice date.</p></section><section class="detail-section"><h3>The source</h3><p class="source-title">${esc(source.title)}</p><p>${esc(source.author)} · ${esc(source.original_year || 'Publication date unknown')}${source.edition_year ? ` · edition ${esc(source.edition_year)}` : ''}</p><p class="evidence-note">Source authenticity: ${esc(humanize(source.source_authenticity))} · ${esc(humanize(source.source_type))}</p>${link(source.url, 'Open source / recovery route', 'source-link')}<div>${sourceLinks(source)}</div>${source.verification_notes ? `<p>${esc(source.verification_notes)}</p>` : ''}${source.notes ? `<p class="evidence-note">${esc(source.notes)}</p>` : ''}<p class="evidence-note">Provenance: ${esc(source.provenance.split(';').map(humanize).join(' → '))} · Rights: ${esc(humanize(source.rights))}</p></section>${row.artifacts.length ? `<section class="detail-section"><h3>Files & recordings · ${row.artifacts.length}</h3>${row.artifacts.map(a => `<details><summary>${esc(humanize(a.artifact_kind))} · ${esc(humanize(a.inspection_status))} inspection</summary><p>${esc(a.inspected_parts)}</p><p class="evidence-note">${esc(a.notes)}</p>${link(a.url, 'Open artifact', 'source-link')}${a.sha256 ? `<p class="snapshot">SHA-256: ${esc(a.sha256)}</p>` : ''}${a.ipfs_cid ? `<p class="snapshot">IPFS: ${esc(a.ipfs_cid)}</p>` : ''}${a.btih ? `<p class="snapshot">BitTorrent info-hash: ${esc(a.btih)}</p>` : ''}</details>`).join('')}</section>` : ''}${row.claims.length ? `<section class="detail-section"><h3>Claims about this item · ${row.claims.length}</h3><p class="evidence-note">Claims may cite other sources for the same item. Support and counterevidence remain separate.</p>${claimHTML}</section>` : ''}${item.notes ? `<section class="detail-section"><h3>Item notes</h3><p>${esc(item.notes)}</p></section>` : ''}`;
  saveURL(row.id); presentDialog(); $('record-dialog').scrollTop = 0;
}
function applyYears() {
  const from = $('from').value, to = $('to').value;
  const valid = v => v === '' || /^-?\d{1,4}$/.test(v);
  $('from').setCustomValidity(valid(from) && valid(to) && !(from && to && Number(from) > Number(to)) ? '' : 'Enter whole years, with the From year no later than the To year.');
  if (!$('from').reportValidity()) return;
  state.from = from; state.to = to; limit = 12; saveURL(); render();
}
function bind() {
  $('filters').addEventListener('submit', e => e.preventDefault());
  let searchTimer;
  $('search').addEventListener('input', e => { clearTimeout(searchTimer); searchTimer = setTimeout(() => change('q', e.target.value.trim()), 130); });
  for (const field of ['country', 'method', 'history', 'status', 'type', 'review']) $(field).addEventListener('change', e => change(field, e.target.value));
  $('sort').addEventListener('change', e => { state.sort = e.target.value; saveURL(); renderList(); });
  $('more-filters').addEventListener('click', () => { const open = $('advanced-filters').hidden; $('advanced-filters').hidden = !open; $('more-filters').setAttribute('aria-expanded', String(open)); });
  $('unmapped').addEventListener('click', () => change('country', state.country === 'unassigned' ? '' : 'unassigned'));
  $('reset').addEventListener('click', () => { state = { ...defaults }; limit = 12; saveURL(); render(); });
  $('window').addEventListener('change', e => { state.from = e.target.value === 'full' ? '' : e.target.value; state.to = ''; limit = 12; saveURL(); render(); });
  $('undated').addEventListener('change', e => change('undated', e.target.checked));
  $('apply-years').addEventListener('click', applyYears);
  for (const field of ['from', 'to']) $(field).addEventListener('keydown', e => { if (e.key === 'Enter') applyYears(); });
  $('show-more').addEventListener('click', () => { limit += 12; renderList(); });
  $('share').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(location.href); $('share').textContent = 'Link copied ✓'; $('announcement').textContent = 'Link to this view copied.'; }
    catch { $('share').textContent = 'Copy the address bar URL'; }
    setTimeout(() => { $('share').textContent = 'Copy view link ↗'; }, 2500);
  });
  $('download').addEventListener('click', () => {
    const blob = new Blob(['\ufeff', csvExport(sortedRows(selected, state.sort))], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'open-arcana-selection.csv'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelectorAll('[data-about]').forEach(b => b.addEventListener('click', () => $('about-dialog').showModal()));
  document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => b.closest('dialog').close()));
  $('record-dialog').addEventListener('close', () => saveURL());
  for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', e => {
    const rect = dialog.getBoundingClientRect();
    if (e.target === dialog && (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom)) dialog.close();
  });
  addEventListener('popstate', () => { const record = readURL(); limit = 12; render(); if (record) openRecord(rows.find(r => r.id === record)); });
}
async function start() {
  try {
    const responses = await Promise.all([fetch('./data.json', { cache: 'no-cache' }), fetch('./assets/world.json')]);
    if (responses.some(r => !r.ok)) throw new Error('Could not load the catalogue');
    const [data, world] = await Promise.all(responses.map(r => r.json()));
    payload = data; rows = hydrate(payload); countries = world.countries;
    $('total-disclosures').textContent = String(rows.length); $('total-items').textContent = String(payload.counts.restricted_items); $('total-traditions').textContent = String(payload.counts.traditions);
    $('version').textContent = `v${payload.dataset.version}`;
    $('snapshot').textContent = `Dataset ${payload.dataset.version} · snapshot ${payload.dataset.snapshot_sha256}`;
    const assigned = [...new Set(rows.flatMap(r => r.countries))].sort((a, b) => nameOf(a).localeCompare(nameOf(b)));
    for (const code of assigned) $('country').add(new Option(nameOf(code), code));
    $('country').add(new Option('Worldwide / regional only', 'unassigned'));
    for (const [method, info] of Object.entries(METHODS)) $('method').add(new Option(info.plural, method));
    for (const type of [...new Set(rows.map(r => r.item.secrecy_type))].sort()) $('type').add(new Option(humanize(type), type));
    const record = readURL(); bind(); $('loading').hidden = true; $('explorer').hidden = false; render();
    if (record) openRecord(rows.find(r => r.id === record));
  } catch (error) {
    $('loading').innerHTML = 'The archive could not be loaded. <a href="https://github.com/openarcana/open-arcana/blob/main/CATALOG.md">Read the catalogue on GitHub ↗</a>';
    console.error(error);
  }
}
start();
