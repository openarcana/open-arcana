# Cloudflare hosting verification, 4 November 2026

The existing explorer was deployed to [Cloudflare Workers Static Assets](https://open-arcana.cor-ling.workers.dev/) with Wrangler 4.157.0. The deployment uses the existing Python static-site builder and no application backend, database or runtime credentials. The GitHub Pages copy remains available so existing shared links continue to work.

The initial published version ID was `58ce92a4-31ca-4b21-b111-f7e9220c7c3f`. An HTTPS fetch of the deployed `data.json` returned the canonical snapshot `fd755a0cc0c78cf43dac965d39908085b13b246532d888525645150e391f8e45`, with 108 disclosures, 63 items, 47 traditions, 118 sources, 265 claims and 46 artifacts.

An actual request to `/open-arcana/?method=leak&history=origins_before_1900` returned HTTP 301 with Location `/?method=leak&history=origins_before_1900`. The migration preserves those selection parameters. The current `.workers.dev` address requires no dedicated domain; a future custom domain can be attached to the same Worker.

The deployment dry run succeeded before upload. All 50 Python tests, eight JavaScript tests and canonical export checks passed with the deployment configuration present. No canonical dataset record was changed by the hosting transition. Cloudflare login credentials were neither published nor copied into GitHub secrets.

Cloudflare Workers Builds was connected to `openarcana/open-arcana`, production branch `main`, with repository-only GitHub App access approved by the owner. Preview builds are disabled. The saved build command runs the same Python tests, export check, static build and JavaScript tests documented in the README; deployment uses pinned Wrangler 4.157.0 and an existing Cloudflare build token. The repository connection does not depend on the local CLI login, whose permissions do not include Workers Builds configuration.

Browser verification on the Cloudflare host showed all 108 disclosures. Selecting Japan produced five disclosures across three items and two traditions, with `?country=JP` in the URL. Following the old repository-prefixed path preserved both disclosure-type and historical-context parameters at the root and returned three leak records for traditions founded before 1900. Opening DISC-0088 preserved its partial-disclosure label, unassessed source authenticity and provisional practice-status note.

The first Git-triggered build, `c0701391-04a5-4adb-9e57-bc70936beaef` for commit `136f627817514c277d85d823b465bfdfd9b4282b`, correctly stopped before deployment because Cloudflare's Python 3.13.3 lacked `_sqlite3`. Selecting Python 3.12 did not fix the image: retry `6ab4fe8b-97ca-42fe-9857-1b5761df3ea5` compiled Python 3.12.16 but also lacked `_sqlite3`. The CI helper therefore uses uv's complete managed Python distribution for both checks and deployment, without changing the data builder or removing checks.

The final helper passed locally with managed Python 3.12.16 and SQLite 3.53.1: all 50 Python tests, offline OSINT receipts, canonical exports and eight JavaScript tests. The saved Cloudflare commands are `sh scripts/cloudflare.sh build` and `sh scripts/cloudflare.sh deploy`; the unsuccessful `PYTHON_VERSION` override was removed. Tool files and caches are isolated from the static output, and Python executable installation into the user's global binary directory is disabled.
