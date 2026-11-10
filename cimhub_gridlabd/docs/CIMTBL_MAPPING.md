# GridLAB-D → `.cimtbl` mapping spec

**Status:** S0 (master) built 2026-11-09; each later section is written with its slice and approved before that
slice's code. Plan: `.development/GLM_REWRITE_PLAN.md`. Contract and format: the `cimtbl-import-contract`,
`cimtbl-shapes` and `cimtbl-mapping-spec` skills. Samples come from the vendored decks in `tests/decks/` (origins in
its README).

## Artifact files and order

The master imports the parts in `MAPPING_ORDER` (`importer/glm_to_cimtbl.py`), which follows the plan's section 2.
S0 has no parts yet.

## master

Mapper: `importer/glm_to_cimtbl.py` `map_master`. Test: `tests/test_glm_to_cimtbl.py`; golden
`tests/goldens/IEEE13_cdpsm/IEEE13_cdpsm.cimtbl`.

| row | from | rule |
|---|---|---|
| `Substation`, `Feeder` | the `name` the caller passes (D7) | mRIDs `sub_<name>`, `fdr_<name>`, source case |
| `BaseFrequency` | `module powerflow { nominal_frequency ...; }`, else `#set powerflow::nominal_frequency=...` | else GridLAB-D's 60 Hz, listed as `# defaulted` |
| `BaseVoltage` | the topology walk's distinct bus voltages (`cimtopology.core`), highest first | `nominal_kv` rounding; mRIDs `bv_12p47kv`, `bv_240v` |
| comment | every GLM type no mapper reads, with its count, including types the schema lacks (`recorder`) | GLM-14 |

Fail fast: an expression the reader kept (`LIGHTS*1.2`) on a record of a mapped class raises, naming the object, its
file and line and the slot (GLM-8). The walk raises on a coil that cannot sit on its island (a deck defect, listed
in `tests/decks/README.md`).
