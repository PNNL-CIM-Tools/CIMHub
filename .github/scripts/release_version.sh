#!/usr/bin/env bash
# Print the version a release run publishes, and write it to each package's pyproject.toml for the build.
# Run from the CIMHub checkout: release_version.sh develop|main <package dir>...
#
# The released packages move in lockstep: every pyproject.toml holds the same next release target X.Y.Z.
# The published version is derived from what is already released (cimhub-core on PyPI and the v* git tags)
# and is never committed, so nothing pushes to the protected branches:
#
#   develop  the next free alpha of the target: 3.0.0a1 released -> 3.0.0a2
#   main     the target itself: 3.0.0
#
# Once the target is released, both branches move on to the next patch (3.0.1a1, 3.0.1).
# Bump the target in every package in one PR for a minor or major release.
set -euo pipefail

branch=$1
shift
if [[ $branch != develop && $branch != main ]]; then
    echo "::error::Releases run from develop or main, not $branch" >&2
    exit 1
fi

# Read from pyproject.toml itself: `uv version --frozen` reports the lockfile's version, and without
# --frozen it would re-lock against the sibling checkouts, which CI does not have.
package_version() {
    python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["version"])' \
        "$1/pyproject.toml"
}

target=$(package_version "$1")
if [[ ! $target =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "::error::$1/pyproject.toml version must be the next release target X.Y.Z, got $target" >&2
    exit 1
fi
for package in "$@"; do
    if [[ $(package_version "$package") != "$target" ]]; then
        echo "::error::$package/pyproject.toml is at $(package_version "$package"), $1 at $target; they release together" >&2
        exit 1
    fi
done

# Tags cover a release this workflow made moments ago that PyPI's JSON API does not show yet
pypi=$(curl --silent --fail https://pypi.org/pypi/cimhub-core/json | jq -r '.releases | keys[]')
released=$(printf '%s\n' "$pypi"; git tag --list 'v*' | sed 's/^v//')

while grep --quiet --line-regexp --fixed-strings "$target" <<< "$released"; do
    IFS=. read -r major minor patch <<< "$target"
    target="$major.$minor.$(( patch + 1 ))"
done

if [[ $branch == main ]]; then
    version=$target
else
    last_alpha=$(grep --extended-regexp "^${target//./\\.}a[0-9]+$" <<< "$released" \
                 | sed 's/.*a//' | sort --numeric-sort | tail -1 || true)
    version="${target}a$(( ${last_alpha:-0} + 1 ))"
fi

for package in "$@"; do
    uv version --directory "$package" "$version" --frozen > /dev/null
done
echo "$version"
