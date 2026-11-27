# Testing

How this package is tested, and how to add a test. The shared helpers (`cim_scope`, `atom_documents`,
`assert_matches_golden`, `record_diff`) and the general test types are on the core site's
[Testing](https://pnnl-cim-tools.github.io/CIMHub/core/developer/testing/) page; this page is what is specific to
OpenDSS. The engine is OpenDSS itself, run in process through `opendssdirect`, and it is the oracle wherever a quantity
can be computed by both sides.

## Running the tests

```bash
uv sync
scripts/test-all.sh opendss                 # this package, one pytest process
scripts/test-all.sh opendss -- -x -q        # arguments after -- go to pytest
scripts/test-all.sh cross_format            # the root cross-format tests, which also import this spoke
uv run pytest cimhub_opendss/tests/test_cimtbl_linecode.py                                  # one file
uv run pytest cimhub_opendss/tests/test_cimtbl_linecode.py::test_classification_is_complete # one test
uv run pytest cimhub_opendss/tests -k "linecode and golden"                                 # by keyword
```

A default run collects about 860 tests, runs 777 of them in seconds and skips 83 (at the time of writing). Those are the whole-deck tests, skipped with
`whole-deck test; pass --roundtrip to run`:

```bash
CIMHUB_DSS_DECKS=/path/to/decks scripts/test-all.sh opendss -- --roundtrip
```

Never run one pytest over the whole repository: cimtables sets the CIM profile and the model scope process-wide.
Every test that loads `.cimtbl` runs inside `cim_scope()`: each such test file defines an autouse `_cim_scope`
fixture that does `with cim_scope(): yield`, which puts back the profile and model scope that cimtables sets.

## Layout

All paths are under
[`cimhub_opendss/tests/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_opendss/tests).

| Path | Holds |
|---|---|
| `atoms/<table>/` | One small deck per case (`<case>.dss`) and its reviewed golden (`<case>.cimtbl`), by DSS table (`linecode`, `line`, `transformer`, ...). `atoms/<table>/export/<case>.dss` is the exporter's golden for the same atom. Prerequisite `.cimtbl` files (`prereq.cimtbl`) and shared ones (`atoms/circuit/substation.cimtbl`) bind first. |
| `decks/` | Public decks vendored for the reader, sweep and whole-deck tests (`IEEE/`, `EPRI/`); `decks/README.md` records each origin and license. |
| `goldens/IEEE13_CDPSM/` | The whole artifact directory of the reference deck: the master and every part. |
| `conftest.py` | `deck(relative)`, `compile_deck(path)`, `ENGINE_DECKS`, the `--roundtrip` option, `limits()`. |
| `engine_compare.py` | Comparing two decks in the engine: `assert_same_engine_state`, `assert_same_power_flow`, `assert_same_settings`, `assert_same_coordinates`. |
| `export_atoms.py` | `export_atom`, `export_network`, `bus_names`, `assert_matches_dss_golden`: an atom through import and export. |
| `test_*.py` | The tests, named below. |

An atom is three or four lines taken from a public deck, with a comment naming where from. Add a case to an existing
table's directory rather than a new directory, unless the DSS class is new.

## Test types

Every test checks one hop, so a failure points at one place.

| Test | Files | Asserts |
|---|---|---|
| classification (I3) | `test_classification_is_complete` in the `test_cimtbl_<table>.py` of each mapper (`test_cimtbl_catalogs.py` for the wire, spacing and geometry classes); `test_slots_are_complete` in `test_export_framework.py` | `check_fields(FIELDS, NATIVE_CLASS)` and `check_slots(SLOTS, NATIVE_CLASS)`: the classification covers every slot of the class, and no more. |
| import | `test_cimtbl_<table>.py`: `test_matches_golden` | An atom through `DssReader` and the mapper gives text equal to its golden `.cimtbl` (`assert_matches_golden`). A failure lists the record differences. |
| bind | the same files: `test_binds_under_cim18v17` and the like | The golden, with its prerequisites, binds under cim18v17 (`cimtbl_to_cim(atom_documents(...))`), key values are right in SI (`.to("ohm/km")`), and the engine computes the same ratings, impedances, powers or settings from the atom. Each fail-fast rule has a test: `pytest.raises(ValueError, match=...)`. |
| export | `test_export_<area>.py` (`buscoords`, `circuit`, `der`, `device_shape`, `injection`, `line`, `loadshape`, `transformer`, `vsource`); `test_export_framework.py` for naming, `bus_ref`, options and `SLOTS` | An atom through import and export (`export_atom`): the written deck equals its golden in `atoms/<table>/export/` (`assert_matches_dss_golden`), and the engine solves it the way it solves the original (`assert_same_engine_state`), under each `name_source` (`name`, `mrid`, `uri`). |
| round trip | `test_export_decks.py`, `test_cimtbl_sweep.py`, `test_dss_to_cimtbl.py`, `test_dss_writer.py` | Whole decks. Power flow parity after import and export (`assert_same_power_flow`), coordinates, idempotence (a second pass is a fixed point), the reader and writer round trip, and `SWEEP_STOPS`. |
| cross-format | `tests/cross_format/` at the repository root | The same equipment from two spokes: this spoke's import against another's, matched by topology and compared in SI. Never in a spoke's own `tests/`. |

The reader, writer, name map, schema and topology have tests of their own: `test_dss_reader.py` (name mapping,
tokenizing, types, arrays),
`test_dss_reader_rules.py` (the command semantics and every fail-fast rule of `DssReader`), `test_dss_writer.py` (a deck
read, written and read again is the same model, and the engine solves both the same), `test_dss_name_map.py` (class
and property names resolved as the engine resolves them), `test_schema_types.py` (each slot's type against the
engine's property schema) and `test_topology_walk.py` (the
`Network` builder and bus voltages against the engine). `test_cimtbl_<table>.py` exists for each mapper: `buscoords`,
`capacitor` (with `CapControl`), `catalogs`, `der`, `device_shape`, `generator`, `geometry`, `line`, `linecode`, `load`,
`loadshape`, `reactor`, `regcontrol`, `transformer`, `vsource`, `wire` and `xfmrcode`.

### Goldens

A golden is reviewed text, not a snapshot to accept. To change one on purpose:

```bash
CIMHUB_UPDATE_GOLDENS=1 scripts/test-all.sh opendss
git diff cimhub_opendss/tests
```

Read the diff before committing: a changed value is a changed mapping, and `CIMTBL_MAPPING.md` must say so. The
variable is read in one place, `cimhub_core.cimtbl_testing`, and a golden is rewritten only when it is exactly `1`. The
exporter's deck goldens go through the same helper.

### The engine comparison

`engine_compare.py` compiles two decks in `opendssdirect` and compares what the engine builds, not the text.
`assert_same_engine_state(original, written)` checks, per element, its buses and YPrim, then the solved node voltages,
with controls off and a tight tolerance (a relative `1e-8` plus `10 uV`), so both decks converge to one answer. The
keyword arguments name each expected difference: `by_element=False` and `bus_names` for an export under another name
source, `yprim_differs` for a switch's invented impedance, `added` for a control only the written deck has, and
`exported=False` for a deck the writer wrote back as read (otherwise the original's fuse and recloser controls are
compared as disabled).
`assert_same_power_flow(original, written)` solves both with controls off at the original's settings and compares every
node within 0.1 % of its bus's base. It returns which of `UNTRANSCRIBED` (earth model, the load voltage limits, `ppm`,
`taps`, capacitor `states`) the written deck had otherwise, and the test asserts that set equals the one its `PARITY`
table lists for the deck.

`conftest.py` fixes two things about the engine for every test: `AllowChangeDir(False)` (a `Compile` would otherwise
change the process's directory, and the next one segfaults once a temporary directory is gone) and `AllowEditor(False)`
(a `Show` or `FileEdit` in a deck would block on an editor). `compile_deck` resets `defaultbasefreq` to 60 because
`Set defaultbasefreq` outlives `Clear`.

## Decks and the sweep

The vendored decks (`decks/README.md` lists each one's origin and license) cover the IEEE 13, 37 and 123 node feeders,
the IEEE 4-bus transformer decks, the 13-node CIM variants and the EPRI K1 and M1 feeders. The large decks (EPRI J1,
IEEE 8500, 9500, 123 with PV and the like) stay out of git.

`test_cimtbl_sweep.py` is the sweep: every deck in `SWEEP_STOPS` either maps and binds with every piece of equipment's
`BaseVoltage` equal to that of the nodes it touches (`assert_base_voltages_agree`, defined in `test_dss_to_cimtbl.py`), or stops with the error its row
names. An unlisted stop fails, and so does a listed stop that now binds, so the table in `CIMTBL_MAPPING.md` stays true.
`test_export_decks.py` then takes every binding deck through export and back.

## Environment variables, options and skips

| Name | Read by | Effect |
|---|---|---|
| `CIMHUB_UPDATE_GOLDENS=1` | `cimhub_core.cimtbl_testing` | Golden comparisons rewrite the golden instead of comparing. |
| `CIMHUB_DSS_DECKS` | `tests/conftest.py` (`deck()`); `tests/cross_format/test_dss_to_glm.py` | A directory with the layout of `decks/` (`IEEE/IEEE8500/Master.dss`). A deck that is not vendored is read from there; without it the test skips with `not vendored; set CIMHUB_DSS_DECKS to run it`. |
| `--roundtrip` (option), `roundtrip` (marker) | `tests/conftest.py`; the marker is registered in the root `pyproject.toml` | Runs the slow whole-deck tests. Without the option they skip with `whole-deck test; pass --roundtrip to run`. |
| `CIMHUB_NAME_SOURCE` | `cimhub_core.names` | The exporter's default `name_source`. Most tests pass `name_source` explicitly; unset it when a test that does not fails on a name. |
| `CIMG_CIM_PROFILE` | cimgraph; restored by `cim_scope()` | The CIM profile cimtables sets process-wide. |

What skips, and why:

- `roundtrip` tests: whole decks, slow, and some need decks that are not vendored. Every skip in a default run is of
  this kind.
- A deck that is not vendored and `CIMHUB_DSS_DECKS` unset (the cross-format test of IEEE 8500).
- Decks the engine cannot compile here, which `ENGINE_DECKS` leaves out: EPRI K1 and M1 `Redirect` files with the wrong
  file-name case for a case-sensitive file system. The reader resolves names case-insensitively; the engine does not, so
  only the reader and mapper tests use them.
