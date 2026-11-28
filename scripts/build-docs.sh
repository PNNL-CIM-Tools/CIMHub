#!/usr/bin/env bash
# Build the CIMHub docs: the landing site (mkdocs.yml) into site/, and each package's site
# (cimhub_<pkg>/mkdocs.yml) into site/<pkg>/, which is how GitHub Pages serves them.
#
#   scripts/build-docs.sh               # every site, --strict (what CI runs)
#   scripts/build-docs.sh core          # one package's site
#   scripts/build-docs.sh core --serve  # preview one site at http://127.0.0.1:8000
#
# The tools run through uvx (docs/requirements.txt), so nothing here touches the workspace's uv.lock.
# A spoke's schema reference is generated from its LinkML schema first; it is never committed.
set -euo pipefail
cd "$(dirname "$0")/.."

# Packages whose site has moved to the shared template (mkdocs.base.yml); add each one as it migrates.
SITES=(core opendss gridlabd raw)

# The LinkML root schema of each spoke that has a schema reference.
declare -A SCHEMA=(
    [opendss]=src/cimhub_opendss/schema/linkml/opendss.yaml
    [gridlabd]=src/cimhub_gridlabd/schema/linkml/main.yaml
    [raw]=src/cimhub_raw/schema/raw_v34/main.yaml
)

MKDOCS=(uvx --python 3.13 --with-requirements docs/requirements.txt mkdocs)

generate_schema_reference() {
    local package=$1
    local schema=${SCHEMA[$package]:-}
    [[ -z $schema ]] && return 0
    rm -rf "cimhub_$package/docs/schema"
    uvx --python 3.13 --from linkml gen-doc -d "cimhub_$package/docs/schema" "cimhub_$package/$schema"
}

if [[ $# -ge 1 ]]; then
    package=$1
    [[ -f cimhub_$package/mkdocs.yml ]] || { echo "no site: cimhub_$package/mkdocs.yml" >&2; exit 1; }
    generate_schema_reference "$package"
    if [[ ${2:-} == --serve ]]; then
        exec "${MKDOCS[@]}" serve -f "cimhub_$package/mkdocs.yml"
    fi
    exec "${MKDOCS[@]}" build --strict -f "cimhub_$package/mkdocs.yml" -d "$PWD/site/$package"
fi

rm -rf site
"${MKDOCS[@]}" build --strict -f mkdocs.yml -d "$PWD/site"
for package in "${SITES[@]}"; do
    generate_schema_reference "$package"
    "${MKDOCS[@]}" build --strict -f "cimhub_$package/mkdocs.yml" -d "$PWD/site/$package"
done
