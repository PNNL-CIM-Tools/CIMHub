# GridLAB-D Schema Generation

Generates LinkML schemas (and downstream Python dataclasses) from the GridLAB-D
C++ sources (a GridLAB-D checkout, BSD-3-Clause; not vendored).

## Pipeline

Three scripts, run in order, one module at a time:

1. `cpp_parser.py` — scans a `gridlab-d/<module>/` directory, extracts each
   class's `gl_publish_variable` block, parent class, and doc comment.
   Output: `extracted_<module>_classes.json`.

2. `property_parser.py` — parses the raw publish blocks into typed
   `ParsedProperty` records (name, C++ type, LinkML range, unit, description,
   enum values). Output: `parsed_<module>_classes.json`.

3. `linkml_generator.py` — emits one LinkML YAML per class into
   `linkml/<module>/`, merges collected enums into `linkml/types/common.yaml`,
   and appends module imports to `linkml/main.yaml`. Both `main.yaml` and
   `types/common.yaml` are updated idempotently, so rerunning for a new module
   does not disturb previously generated modules.

## Running for a module

Run from the repo root. `--source` points to the GridLAB-D checkout holding
`powerflow/`, `residential/`, `generators/`, etc.

```bash
MODULE=residential   # or powerflow, generators, ...

python cimhub_gridlabd/src/cimhub_gridlabd/schema/cpp_parser.py \
  --source <gridlab-d checkout> \
  --module $MODULE \
  --output cimhub_gridlabd/src/cimhub_gridlabd/schema/extracted_${MODULE}_classes.json

python cimhub_gridlabd/src/cimhub_gridlabd/schema/property_parser.py \
  --input  cimhub_gridlabd/src/cimhub_gridlabd/schema/extracted_${MODULE}_classes.json \
  --output cimhub_gridlabd/src/cimhub_gridlabd/schema/parsed_${MODULE}_classes.json

python cimhub_gridlabd/src/cimhub_gridlabd/schema/linkml_generator.py \
  --input  cimhub_gridlabd/src/cimhub_gridlabd/schema/parsed_${MODULE}_classes.json \
  --output cimhub_gridlabd/src/cimhub_gridlabd/schema/linkml \
  --module $MODULE
```

## Modules converted

- `powerflow` — 46 classes
- `generators` — 11 classes
- `residential` — 19 classes
- `tape` — 1 class (`player`)

## Downstream artifacts — the one schema pipeline

`linkml/main.yaml` (the C++-scraped LinkML tree, with `order`/`native_name`
serialization annotations) is the **single source of truth**. The converters and
writer import the generated dataclasses from `cimhub_gridlabd.schema.gridlabd`.

Regenerate the dataclasses after any LinkML change, from the repo root, and commit the YAML and the generated module
together:

```bash
scripts/gen-schema.sh gridlabd
```

The script runs `gen-python` through `uvx` on `linkml/main.yaml` and writes `gridlabd.py` (see the script for the
exact command; it passes `--no-generation-date` so the diff shows only what the YAML changed).

`gridlabd.py` is **generated — never hand-edit**. Any field fix goes in the LinkML
YAML, then regenerate.

Optional:

```bash
linkml-validate cimhub_gridlabd/src/cimhub_gridlabd/schema/linkml/main.yaml
gen-markdown    cimhub_gridlabd/src/cimhub_gridlabd/schema/linkml/main.yaml -d docs/
```
