#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
uv run ruff check beyond_ui tests tools examples
uv run python -m compileall -q beyond_ui
uv run python tools/check_custom_parity.py
