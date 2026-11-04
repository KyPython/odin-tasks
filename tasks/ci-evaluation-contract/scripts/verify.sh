#!/usr/bin/env sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

python3 -m unittest discover -s tests -v
result=$(python3 -m grader.pipeline fixtures/valid/manifest.json)
test "$result" = "sample_001: 3"
printf '%s\n' "$result"
