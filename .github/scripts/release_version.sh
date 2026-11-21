#!/usr/bin/env bash
# Print the release a run publishes for one package as key=value lines (name, version, tag, previous_tag) for
# $GITHUB_OUTPUT, and write the version to the package's pyproject.toml for the build.
# Run from the CIMHub checkout: release_version.sh develop|main <package dir>
#
# Each package releases on its own: its pyproject.toml holds its next release target X.Y.Z. The published
# version is derived from what that package has already released (on PyPI and its <name>-v* git tags) and
# is never committed, so nothing pushes to the protected branches:
#
#   develop  the next free alpha of the target: 2.1.0a1 released -> 2.1.0a2
#   main     the target itself: 2.1.0
#
# Once the target is released, both branches move on to the next patch (2.1.1a1, 2.1.1).
# Bump the target in the package's pyproject.toml for a minor or major release.
set -euo pipefail

branch=$1
package=$2
if [[ $branch != develop && $branch != main ]]; then
    echo "::error::Releases run from develop or main, not $branch" >&2
    exit 1
fi

# Read from pyproject.toml itself: `uv version --frozen` reports the lockfile's version, and without
# --frozen it would re-lock against the sibling checkouts, which CI does not have.
project_field() {
    python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"][sys.argv[2]])' \
        "$package/pyproject.toml" "$1"
}

name=$(project_field name)
name=${name//_/-}  # the PyPI (normalized) name: cimhub_core -> cimhub-core
target=$(project_field version)
if [[ ! $target =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "::error::$package/pyproject.toml version must be the next release target X.Y.Z, got $target" >&2
    exit 1
fi

response=$(curl --silent --write-out '\n%{http_code}' "https://pypi.org/pypi/$name/json")
status=${response##*$'\n'}
case $status in
    200) pypi=$(jq -r '.releases | keys[]' <<< "${response%$'\n'*}") ;;
    404) pypi="" ;;  # the project's first release
    *) echo "::error::PyPI answered $status for $name" >&2; exit 1 ;;
esac
# Tags cover a release this workflow made moments ago that PyPI's JSON API does not show yet
released=$(printf '%s\n' "$pypi"; git tag --list "$name-v*" | sed "s/^$name-v//")

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

uv version --directory "$package" "$version" --frozen > /dev/null
echo "name=$name"
echo "version=$version"
echo "tag=$name-v$version"
# The release notes start here, so they list only this package's changes
echo "previous_tag=$(git tag --list "$name-v*" --sort=-creatordate | sed -n 1p)"
