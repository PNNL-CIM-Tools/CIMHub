# Testing

How this package is tested, and how to add a test. The shared helpers (`cim_scope`, `atom_documents`,
`assert_matches_golden`, `assert_text_matches_golden`, `record_diff`) and the general test types are on the core site's
[Testing](https://pnnl-cim-tools.github.io/CIMHub/core/developer/testing/) page; this page is what is specific to RAW.
There is no power-flow engine for RAW in the tests, so no solver is an oracle: the checks are the golden `.cimtbl`
text, the bound CIM read through the core getters, and the round trips.

## Running the tests

```bash
uv sync
scripts/test-all.sh raw                      # this package, one pytest process
scripts/test-all.sh raw -- -x -q             # arguments after -- go to pytest
uv run pytest cimhub_raw/tests/test_raw34_reader.py                              # one file
uv run pytest cimhub_raw/tests/test_raw34_reader.py::test_tokenize               # one test
uv run pytest cimhub_raw/tests -k "golden"                                       # by keyword
```

A run collects 368 tests and runs all of them in about twenty seconds; nothing skips. Never run one pytest over the
whole repository: cimtables sets the CIM profile and the model scope process-wide. The two test files that bind CIM
have an autouse fixture, `_cim_scope`, that does `with cim_scope(): yield`, which puts back the profile and model scope
cimtables sets. A new test file that binds needs the same fixture. There is no `conftest.py`.

## Layout

All paths are under
[`cimhub_raw/tests/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_raw/tests).

| Path | Holds |
|---|---|
| `test_raw34_reader.py` | 48 tests: the tokenizer, the record counts of the three public cases, read, write and read again on every case and atom (`test_read_write_read_is_lossless`), defaults and padding, extended bus names, and each reader error (`Raw34ParseError` with its message: REV, duplicate key, unknown extended name, too many fields, a value that does not convert, a missing terminator, an unknown system-wide record, the `Q` record, a phase-2 section). |
| `test_raw_to_cimtbl.py` | 218 tests: the importer. `check_fields` for every mapper, the goldens, the order of the parts, the bound networks (`test_binds` counts the substations, buses, busbars, limits and voltages of IEEE14, WECC240, IEEE118 and two node-breaker atoms), values in SI through the core getters, the derived functions (`ka_from_rating`, `ratio_tap`, `block_sections`, ...), the atoms of each group and the fail-fast rules of each mapper (`pytest.raises(...)` on a record changed to something outside the spec). |
| `test_cim_to_raw.py` | 96 tests: the exporter. `test_round_trip` imports and exports every fixture and compares it with the original record by record and slot by slot; `test_written_case_reads_back` writes and reads the export; `test_slots_are_complete` runs `check_slots`; the rest are the fail-fast rules of each exporter module (`test_e1_...` to `test_e4_...`). |
| `test_phase2_stubs.py` | 6 tests: the three stub mappers (`multi_terminal_dc`, `gne_device`, `induction_machine`) return an empty document when the case has none of the records and raise `NotImplementedError` (`phase 2`) when it has one. |
| `cases/` | The public cases, with a `README.md` that records each one's origin, terms and local edits. |
| `atoms/<group>/` | Hand-built cases and a `README.md` per group. |
| `goldens/` | The reviewed `.cimtbl` text. |

## Cases and atoms

`cases/` holds three public RAW v34 cases; only cases with a documented public origin live there.

| Case | What it is | Used for |
|---|---|---|
| `IEEE14/IEEE_14_bus.raw` | The IEEE 14-bus case. | The goldens, the round trip, the examples on these pages. |
| `IEEE118/IEEE118_all_hydro_25_clean_4_subs.raw` | The IEEE 118-bus case with four node-breaker substations (buses 8, 37, 49 and 100). | The SUBSTATION and equipment terminal goldens, the main-and-transfer bus checks. |
| `WECC240/240busWECC_2018_PSS.raw` | A reduced 240-bus WECC case. | The values in SI, ratings, transformers, tie flows, the round trip. |

An atom is a small RAW file a person built by hand (or generated from another atom by a script) to cover what the
public cases lack. Each is synthetic, and its group's `README.md` lists it with its content. The groups are `area`
(ties, transfers, an untraceable bus), `branch` (line shunts, mixed base voltages, switches, a multi-section line),
`dc` (two-terminal DC line, VSC DC lines and a FACTS device), `generator` (generator forms, renewable forms, a step-up),
`load`, `shunt` (fixed shunts, switched shunts, a plant and a FACTS shunt), `substation` (the two-bus node-breaker atom
and one holding every equipment form) and `transformer` (the two- and three-winding forms, the tap-changer and
impedance table forms). 18 atoms in all.

Every `.raw` under `atoms/*/` and `cases/*/` is a fixture of `test_round_trip`. A new atom is picked up there with no
edit, and its differences from the original (the defaults RAW applies, a record the export adds) are listed in
`EXPECTED` with the reason. An atom has no `.cimtbl` golden of its own: its tests read values from the bound network.
Add an atom to the group of the table it covers, not to a new directory, unless the table is new.

## Test types

| Type | Where | What it checks |
|---|---|---|
| Classification | `test_classification_is_complete` and its substation-part variants | `check_fields(FIELDS, NATIVE_CLASS)`: every slot of the record is classified, and no stale entry. |
| Golden | `test_master_matches_golden`, `test_part_matches_golden`, `test_ieee118_part_matches_golden` | The `.cimtbl` text of the master and of each IEEE14 part, and of IEEE118's substation and equipment terminal documents. |
| Bound network | `test_binds`, the `test_wecc240_*` and `test_<group>_atom` tests | The importer's output binds under cim18v17 (`BusBranchModel`); counts, mRIDs and values in SI checked through the objects. |
| Row comments | `test_*_comments`, `test_r1b_comments` | The `defaulted:` and `untranscribed:` comments a row carries. |
| Derived value | `test_kv_from_per_unit`, `test_ratio_tap`, `test_phase_tap`, ... | The functions in `importer/cimtbl/derived.py`, each with its inverse. |
| Fail fast | `test_a_..._raises`, `test_..._outside_r<n>_raises` | A record changed to something outside the spec raises with a message that names it. |
| Reader and writer | `test_raw34_reader.py` | Lossless read, write and read. |
| Round trip | `test_round_trip`, `test_written_case_reads_back` | RAW to CIM to RAW. |

### Goldens

`assert_matches_golden(document, path)` compares a document's text with the file, record by record, so a diff names the
row and column that changed. The goldens are under `goldens/`:

| Directory | Files |
|---|---|
| `goldens/IEEE14/` | The master `IEEE14.cimtbl` and the parts `zone`, `area_interchange`, `bus`, `branch`, `load`, `fixed_shunt`, `generator` and `transformer`. |
| `goldens/IEEE118/` | `substation.cimtbl` and `equipment_terminal.cimtbl`: the node-breaker documents. |

`CIMHUB_UPDATE_GOLDENS=1` rewrites the golden instead of comparing:

```bash
CIMHUB_UPDATE_GOLDENS=1 scripts/test-all.sh raw -- -k golden
git diff cimhub_raw/tests/goldens                  # review every change before it is committed
```

### The round trip

`test_round_trip` reads a fixture, imports it with `raw_to_cim`, exports it with `export_tables` over the landed
modules (`LANDED`), and compares the two models by `(record class, key, slot)`. It skips slots the exporter marks
`unset`, fills blanks on both sides from the schema's defaults before comparing (`IMPORT_DEFAULTS` adds the defaults the
importer applies), and treats floats as equal within a relative tolerance of 1e-9. The set of differences must equal
`EXPECTED[stem]` plus the generic ones (`_metered_off_a_tie`, `_own_bus_swreg`, `_own_bus_ireg`, `_nominal_zero`: a
field PSS/E reads one way and CIM keeps another). A new difference fails the test, and so does an expected one that has
gone, so the list stays true.

## Environment variables, options and skips

| Name | Read by | Effect |
|---|---|---|
| `CIMHUB_UPDATE_GOLDENS=1` | `cimhub_core.cimtbl_testing` | Golden comparisons rewrite the golden instead of comparing. |
| `CIMG_CIM_PROFILE` | cimgraph; restored by `cim_scope()` | The CIM profile cimtables sets process-wide; the tests do not set it. |

No test in this package reads any other environment variable, defines a pytest option or marker, or skips. The
`CIMHUB_RAW_SWEEP_DIR` sweep over cases that are not committed is planned and does not exist
(`cases/README.md`).
