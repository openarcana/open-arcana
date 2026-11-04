# Cloudflare hosting verification, 4 November 2026

The existing explorer was deployed to [Cloudflare Workers Static Assets](https://open-arcana.cor-ling.workers.dev/) with Wrangler 4.157.0. The deployment uses the existing Python static-site builder and no application backend, database or runtime credentials. The GitHub Pages copy remains available so existing shared links continue to work.

The initial published version ID was `58ce92a4-31ca-4b21-b111-f7e9220c7c3f`. An HTTPS fetch of the deployed `data.json` returned the canonical snapshot `fd755a0cc0c78cf43dac965d39908085b13b246532d888525645150e391f8e45`, with 108 disclosures, 63 items, 47 traditions, 118 sources, 265 claims and 46 artifacts.

An actual request to `/open-arcana/?method=leak&history=origins_before_1900` returned HTTP 301 with Location `/?method=leak&history=origins_before_1900`. The migration preserves those selection parameters. The current `.workers.dev` address requires no dedicated domain; a future custom domain can be attached to the same Worker.

The deployment dry run succeeded before upload. All 50 Python tests, eight JavaScript tests and canonical export checks passed with the deployment configuration present. No canonical dataset record was changed by the hosting transition. Cloudflare login credentials were neither published nor copied into GitHub secrets.
