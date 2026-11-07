#!/usr/bin/env bash
# Split-readiness gate: this repo must stay publishable at every commit.
# Fails on (1) imports of private spokes, (2) path references to private spokes or
# local checkouts, (3) files over 10 MB. See the split-readiness skill.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

PRIVATE='powersimulator|cyme|synergi|powerworld|pscad|arcgis|bmopf|repair|s223'
EXCLUDE=(--exclude-dir=.git --exclude-dir=.venv --exclude-dir=__pycache__ --exclude=uv.lock --exclude=leak-gate.sh)
status=0

if grep -rnIE "(from|import) +cimhub_($PRIVATE)" "${EXCLUDE[@]}" .; then
    echo "leak-gate: import of a private spoke" >&2; status=1
fi
if grep -rnIE "cimhub_($PRIVATE)/|/home/[a-z0-9_]+/" "${EXCLUDE[@]}" .; then
    echo "leak-gate: path into a private spoke or a local checkout" >&2; status=1
fi
big=$(find . -path ./.git -prune -o -path ./.venv -prune -o -type f -size +10M -print)
if [[ -n "$big" ]]; then
    echo "$big"; echo "leak-gate: files over 10 MB (move them to the golden store)" >&2; status=1
fi
[[ $status -eq 0 ]] && echo "leak-gate: clean"
exit $status
