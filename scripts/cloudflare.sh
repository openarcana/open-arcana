#!/bin/sh
# Cloudflare's image can omit SQLite from its Python installation. Use a
# complete managed interpreter for CI, including Wrangler's custom build.
set -eu

case "${1:-}" in
  build|deploy) mode="$1" ;;
  *) printf 'Usage: sh scripts/cloudflare.sh build|deploy\n' >&2; exit 2 ;;
esac

cd "$(dirname "$0")/.."
tools_dir="${OPENARCANA_BUILD_TOOLS:-$PWD/.cloudflare-tools}"
python3 -m pip install --disable-pip-version-check --no-input \
  --target "$tools_dir" --cache-dir "$tools_dir/cache/pip" --upgrade 'uv==0.13.7'
export UV_PYTHON_INSTALL_DIR="$tools_dir/python"
export UV_PYTHON_INSTALL_BIN=0
export UV_CACHE_DIR="$tools_dir/cache/uv"
"$tools_dir/bin/uv" python install 3.12.16
python_path=$("$tools_dir/bin/uv" python find --managed-python 3.12.16)
PATH="$(dirname "$python_path"):$PATH"
export PATH
python3 -c 'import sqlite3, sys; print("Build Python:", sys.version.split()[0], "SQLite:", sqlite3.sqlite_version)'

case "$mode" in
  build)
    python3 -m unittest discover -s tests -q
    python3 scripts/osint.py --check
    python3 scripts/build.py --check-exports
    python3 scripts/build_site.py --output _site
    node --test tests/site.test.mjs
    ;;
  deploy)
    exec npx --yes wrangler@4.157.0 deploy
    ;;
esac
