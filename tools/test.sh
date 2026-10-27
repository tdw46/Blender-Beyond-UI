#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
uv run python -m unittest discover -s tests
