#!/usr/bin/env bash
# Copy the tradecraft Python package into web/api/_vendor/ so the
# Vercel Python Function can import it without going through PyPI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$WEB_DIR")"
SRC="$ROOT_DIR/src/tradecraft"
DEST="$WEB_DIR/api/_vendor/tradecraft"

if [ ! -d "$SRC" ]; then
  echo "ERROR: $SRC does not exist. Did you run this from the wrong place?"
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
cp -R "$SRC" "$DEST"

echo "Vendored tradecraft -> $DEST"
