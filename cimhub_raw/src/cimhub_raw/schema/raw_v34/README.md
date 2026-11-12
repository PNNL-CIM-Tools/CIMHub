# RAW v34 LinkML schema

LinkML classes for the PSS/E RAW version 34 record layout: one YAML module per record type under `classes/`,
shared types in `types/common_types.yaml`, and `main.yaml` importing them all. `raw34_schema.py` is generated from
`main.yaml` with `gen-python`; regenerate it after any YAML change.

`composite_id.py` assigns the natural key of record types that need more than one field (a load is bus + ID).
The reader uses it, and the exporter must use the same function, so both directions build identical IDs.

Used by `cimhub_raw.raw34_reader.Raw34Reader` (RAW file → `GraphModel` of these records) and
`cimhub_raw.raw34_writer.Raw34Writer` (the reverse). Seeded unchanged from CIMHub_2_0 on 2026-11-08; the R0
schema changes are in `.development/RAW_REWRITE_PLAN.md` §3.3 and §4.1.
