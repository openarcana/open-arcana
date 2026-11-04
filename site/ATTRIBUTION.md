# Explorer assets and data

The site is built from Open Arcana's canonical CSVs and preserves their snapshot identifier. Catalogue metadata and documentation are CC0. Cited source works retain their own rights. Original application code in this directory is licensed under 0BSD; see `LICENSE`.

The country map is derived from Natural Earth's 1:110m admin-0 country polygons:

- [Original GeoJSON](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson)
- [Public-domain license](https://github.com/nvkelso/natural-earth-vector/blob/master/LICENSE.md)

The upstream bytes were retrieved on 4 November 2026. Their SHA-256 is retained as `source_sha256` in `assets/world.json`. The derived file retains country names, identifiers, label positions and polygon geometry rounded to three decimal places; Antarctica is omitted. Modern outlines provide navigation, without establishing historical boundaries, disclosure locations or the prevalence of a practice.

`geography.json` documents every country association and each unassigned broad region. The presentation uses system fonts, original CSS and an original book mark; it requires no remote fonts, imagery or chart libraries.
