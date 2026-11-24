#!/usr/bin/env bash
# Regenerate each spoke's Python dataclasses from its LinkML schema (gen-python). Run it after any schema YAML
# change and commit the YAML and the generated module together; the module is never edited by hand.
#
#   scripts/gen-schema.sh            # every spoke with a schema
#   scripts/gen-schema.sh opendss    # one spoke
#
# linkml runs through uvx, so nothing here touches the workspace's uv.lock. --no-generation-date keeps the output
# the same from run to run, so the diff shows only what the YAML changed.
set -euo pipefail
cd "$(dirname "$0")/.."

# package -> "root schema YAML:generated module"
declare -A SCHEMA=(
    [opendss]=cimhub_opendss/src/cimhub_opendss/schema/linkml/opendss.yaml:cimhub_opendss/src/cimhub_opendss/schema/opendss_schema.py
    [gridlabd]=cimhub_gridlabd/src/cimhub_gridlabd/schema/linkml/main.yaml:cimhub_gridlabd/src/cimhub_gridlabd/schema/gridlabd.py
    [raw]=cimhub_raw/src/cimhub_raw/schema/raw_v34/main.yaml:cimhub_raw/src/cimhub_raw/schema/raw_v34/raw34_schema.py
)

packages=("$@")
[[ ${#packages[@]} -eq 0 ]] && packages=("${!SCHEMA[@]}")

for package in "${packages[@]}"; do
    entry=${SCHEMA[$package]:-}
    [[ -z $entry ]] && { echo "no schema for $package; known: ${!SCHEMA[*]}" >&2; exit 1; }
    schema=${entry%%:*}
    module=${entry##*:}
    generated=$(mktemp)
    uvx --python 3.13 --from linkml gen-python --no-generation-date "$schema" > "$generated"
    cat "$generated" > "$module"  # keeps the module's mode; mv would leave mktemp's 0600
    rm "$generated"
    echo "$module"
done
