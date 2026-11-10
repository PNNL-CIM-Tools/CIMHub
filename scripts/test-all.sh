#!/usr/bin/env bash
# Run every package's tests, one pytest process per package.
#
# One process each because cimtables sets the CIM profile and the model scope
# process-wide, so suites must not share an interpreter.
#
# Usage:
#   scripts/test-all.sh              # every package
#   scripts/test-all.sh core opendss # only the named packages
#   scripts/test-all.sh -- -x -q     # extra args go to pytest
#   PYTEST=venv/bin/pytest scripts/test-all.sh  # another runner
#
# Exits non-zero if any package fails, after running all of them.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

# PYTEST overrides the runner: release.yml tests the built wheels in their own venv.
read -ra RUNNER <<< "${PYTEST:-uv run pytest}"

PYTEST_ARGS=()
PACKAGES=()
seen_marker=0
for arg in "$@"; do
    if [[ "$arg" == "--" ]]; then seen_marker=1; continue; fi
    if [[ "$seen_marker" -eq 1 ]]; then PYTEST_ARGS+=("$arg"); else PACKAGES+=("$arg"); fi
done

TEST_DIRS=()
if [[ "${#PACKAGES[@]}" -eq 0 ]]; then
    for d in cimhub_*/tests; do
        compgen -G "$d/test_*.py" > /dev/null 2>&1 && TEST_DIRS+=("$d")
    done
else
    for p in "${PACKAGES[@]}"; do
        d="cimhub_${p#cimhub_}/tests"
        if [[ ! -d "$d" ]]; then echo "error: no tests directory $d" >&2; exit 2; fi
        TEST_DIRS+=("$d")
    done
fi

FAILED=()
for d in "${TEST_DIRS[@]}"; do
    echo "== $d"
    "${RUNNER[@]}" "$d" "${PYTEST_ARGS[@]+"${PYTEST_ARGS[@]}"}" || FAILED+=("$d")
done

if [[ "${#FAILED[@]}" -eq 0 ]]; then
    echo "all ${#TEST_DIRS[@]} suites passed"
    exit 0
fi
echo "${#FAILED[@]} of ${#TEST_DIRS[@]} suites failed:"
printf '  %s\n' "${FAILED[@]}"
exit 1
