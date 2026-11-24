# Testing

How this package is tested, and how to add a test. The shared helpers (`cim_scope`, `atom_documents`,
`assert_matches_golden`, `assert_text_matches_golden`, `record_diff`) and the general test types are on the core site's
[Testing](https://pnnl-cim-tools.github.io/CIMHub/core/developer/testing/) page; this page is what is specific to
GridLAB-D. The engine is GridLAB-D 6.0 itself, run in process through the `gridlabd` wheel (a test dependency only),
and it is the oracle wherever a quantity can be computed by both sides.

## Running the tests

```bash
uv sync
scripts/test-all.sh gridlabd                 # this package, one pytest process
scripts/test-all.sh gridlabd -- -x -q        # arguments after -- go to pytest
scripts/test-all.sh cross_format             # the root cross-format tests, which also import this spoke
uv run pytest cimhub_gridlabd/tests/test_cimtbl_series_reactor.py                       # one file
uv run pytest cimhub_gridlabd/tests/test_cimtbl_series_reactor.py::test_atom_golden     # one test
uv run pytest cimhub_gridlabd/tests -k "reactor and golden"                             # by keyword
```

A default run collects 410 tests, runs 340 of them in about ten seconds and skips 70 (at the time of writing). The
skips are the decks that are not vendored (see below):

```bash
CIMHUB_GLM_DECKS=/path/to/decks scripts/test-all.sh gridlabd -- --roundtrip
```

Never run one pytest over the whole repository: cimtables sets the CIM profile and the model scope process-wide.
Every test that loads `.cimtbl` runs inside `cim_scope()`: `conftest.py` has a `scope` fixture that does
`with cim_scope(): yield`, which puts back the profile and model scope that cimtables sets. A test that binds takes
`scope` as an argument.

## Layout

All paths are under
[`cimhub_gridlabd/tests/`](https://github.com/PNNL-CIM-Tools/CIMHub/tree/develop/cimhub_gridlabd/tests).

| Path | Holds |
|---|---|
| `atoms/<table>/` | One small deck per case (`<case>.glm`), its reviewed import golden (`<case>.<table>.cimtbl`, one per artifact file the case writes) and its exported deck (`<case>.exported.glm`, and `<name>.exported.player` for a player's tape). An atom includes the atoms it builds on (`series_reactor.glm` includes `../line/line.glm`, which includes the catalog). |
| `decks/` | Public decks vendored for the reader, sweep and whole-deck tests (`IEEE/`, `PNNL/`); `decks/README.md` records each origin and license, and the known deck defects. |
| `goldens/IEEE13_cdpsm/` | The whole artifact directory of the reference deck (the master and every part), and the exported deck `IEEE13_cdpsm.exported.glm`. |
| `conftest.py` | `deck(relative)`, `defines(relative)`, `deck_params`, `BIND_STOPS`, the `scope` fixture, the `--roundtrip` option. |
| `gridlabd_engine.py` | The oracle: `solve(path)`, `worst_difference`, `run_file`, `engine_messages`. |
| `test_*.py` | The tests, named below. |

An atom is a few objects taken from a public deck, with a comment naming where from. Add a case to an existing table's
directory rather than a new directory, unless the GLM class is new. The transformer forms no GLM deck holds are an atom
written as CIM, `atoms/transformer/forms.cimtbl`, which the export tests read.

## Test types

Every test checks one hop, so a failure points at one place.

| Test | Files | Asserts |
|---|---|---|
| classification (I3) | `test_every_slot_is_classified` (or the like) in each `test_cimtbl_<table>.py`; `test_slots_cover_every_schema_slot` in `test_export_framework.py` | `check_fields(FIELDS, NATIVE_CLASS)` and `check_slots(SLOTS, NATIVE_CLASS)`: the classification covers every slot of the class, and no more. |
| import | `test_cimtbl_<table>.py`: `bus`, `capacitor`, `catalog`, `inverter`, `line`, `load`, `player`, `regulator`, `schedule`, `series_reactor`, `transformer` | An atom through `GlmReader` and the mapper gives text equal to its golden `.cimtbl` (`assert_matches_golden`). A failure lists the record differences. |
| bind | the same files: `test_atom_binds` and the like | The golden, with the objects it names, binds under cim18v17 (`glm_to_cim`), key values are right through the core getters in SI, GridLAB-D's own numbers (power per phase, taps, per unit impedance) agree where the engine can compute them, and each fail-fast rule has a test: `pytest.raises(ValueError, match=...)`. |
| orchestrator | `test_glm_to_cimtbl.py`, `test_topology_walk.py` | The master, the base frequency, the expression guard, the feeder head, and the `Network` the walk is built from, with the bus voltages it gives. |
| sweep | `test_cimtbl_sweep.py` | Every deck in `ALL_DECKS` either maps and binds, with each slice's engine check run on the network (`assert_binds_as_gridlabd_runs_it`), or stops with the error its row in `BIND_STOPS` names. The IEEE13_cdpsm artifact directory equals its golden file for file. |
| export | `test_export_atoms.py`, `test_export_framework.py`, `test_export_players.py`, `test_export_schedules.py` | Each atom through import, export, write, read and import again: the two CIM models are equal (`cimtables.diff_models`, in SI) except for the differences the spec lists (`EXPECTED`, `UNUSED`), and the written deck equals its golden. `test_export_framework.py` checks `SLOTS`, the names and the pure rules; the players and schedules tests solve the exported deck in GridLAB-D at each instant. |
| export on decks | `test_export_decks.py` | The Java-export decks (IEEE 13 cdpsm and assets, IEEE 123) are exported, written and solved in GridLAB-D. Their bus voltages equal the original's within `PARITY_REL` (1e-4); a second export of the export is the same text; the IEEE 13 export is its golden. |
| reader and writer | `test_glm_reader.py`, `test_glm_writer.py` | One test per rule of the reader, every deck reads (or stops with its listed error); the writer's value formats, class order and a read-back round trip. |
| cross-format | `tests/cross_format/` at the repository root | The same equipment from two spokes, matched by topology and compared in SI. Never in a spoke's own `tests/`. |

The cross-format files that involve this spoke are `test_ieee13_glm_vs_dss.py` (the IEEE 13 GLM import against the DSS
import of the same model, from the committed goldens, with no engine), `test_glm_to_dss.py` (the transformer forms the
GLM importer writes, exported to DSS and solved in OpenDSS), `test_glm_player_to_dss.py` and
`test_glm_schedule_elsewhere.py` (a player or schedule in the DSS and GDM spokes) and `test_dss_to_glm.py` (DSS decks
through CIM to GLM, solved in GridLAB-D against OpenDSS's own solution).

### Goldens

A golden is reviewed text, not a snapshot to accept. To change one on purpose:

```bash
CIMHUB_UPDATE_GOLDENS=1 scripts/test-all.sh gridlabd
git diff cimhub_gridlabd/tests
```

Read the diff before committing: a changed value is a changed mapping, and `CIMTBL_MAPPING.md` (or
`EXPORT_MAPPING.md`) must say so. The variable is read in one place, `cimhub_core.cimtbl_testing`, and a golden is
rewritten only when it is exactly `1`. The exported-deck goldens go through the same helper
(`assert_text_matches_golden`). The slot tables in `EXPORT_MAPPING.md` are not goldens: edit them by hand from
`spec_tables()`.

### The GridLAB-D oracle

`gridlabd_engine.py` loads a deck into the `gridlabd` wheel and reads the bus voltages of every node, meter, load and
substation class (`solve`). `worst_difference(original, exported)` is the largest relative difference over the buses
both hold. The wheel has quirks, which the module records: it has no command line, a failed load is reported only as
"failed to load model file" (`engine_messages` reruns the deck in process to print GridLAB-D's own message), and polar
text is read as rectangular unless `complex_output_format` is `RECT`.

The Java-export decks drive their loads by `ieeezipload.value*K`, which needs GridAPPS-D's run file: `run_file(body,
vsource)` writes it beside the deck, with the `class player { double value; }` declaration, a tape player named
`ieeezipload`, one power flow at one instant and `#define VSOURCE=...`.

## Decks and the sweep

The vendored decks (`decks/README.md` lists each one's origin and license) are the IEEE 13 cdpsm, assets and houses
exports, IEEE 123, two PNNL taxonomy feeders and GridAPPS-D's zip load schedule. `conftest.ALL_DECKS` lists those and
the others that stay out of git (IEEE 123 transactive and the rest of the PNNL taxonomy); `VENDORED_DECKS` lists the
ones in the tree.

`conftest.defines(relative)` gives a deck the macros it needs. The Java exports use `${VSOURCE}` without defining it,
so each is read with `defines={"VSOURCE": ...}`: `66395.28` (115 kV / sqrt 3) by default and `2401.78` for IEEE 123,
whose substation is a 4.16 kV bus (`conftest.VSOURCE`).

`BIND_STOPS` lists the decks that stop before binding, each with the start of its error. A deck that stops with a
different error fails, and so does a listed deck that now binds, so the table stays true. `test_every_deck_reads` and
`test_every_deck_walks` have their own stop tables (the deck defects in `decks/README.md`).

## Environment variables, options and skips

| Name | Read by | Effect |
|---|---|---|
| `CIMHUB_UPDATE_GOLDENS=1` | `cimhub_core.cimtbl_testing` | Golden comparisons rewrite the golden instead of comparing. |
| `CIMHUB_GLM_DECKS` | `tests/conftest.py` (`deck()`) | A directory with the layout of `decks/` (`PNNL/orig_R5-12.47-3.glm`). A deck that is not vendored is read from there; without it the test skips with `not vendored; set CIMHUB_GLM_DECKS to run it`. |
| `CIMHUB_GLM_UTILITY_DECKS` | `tests/conftest.py` (`utility_deck_params()`) | A directory of a utility's own decks, which never enter git. The sweep binds every non-empty `*.glm` in it, and each must bind. Unset, that test skips with `set CIMHUB_GLM_UTILITY_DECKS`. |
| `CIMHUB_DSS_DECKS` | `tests/cross_format/test_dss_to_glm.py` | A directory with the DSS spoke's deck layout, for the decks not vendored (IEEE 8500). |
| `--roundtrip` (option), `roundtrip` (marker) | `tests/conftest.py`; the marker is registered in the root `pyproject.toml` | Runs the tests on the decks that are not vendored. Without it they skip with `external deck; pass --roundtrip (and set CIMHUB_GLM_DECKS) to run it`. |
| `CIMHUB_NAME_SOURCE` | `cimhub_core.names` | The exporter's default `name_source`. Most tests pass `name_source` explicitly; unset it when a test that does not fails on a name. |
| `CIMG_CIM_PROFILE` | cimgraph; restored by `cim_scope()` | The CIM profile cimtables sets process-wide. |

What skips, and why. A default run skips 70 tests, all in four places:

- `test_cimtbl_sweep.py`: 23 decks that are not vendored, and the utility decks when `CIMHUB_GLM_UTILITY_DECKS` is
  unset (1).
- `test_glm_reader.py::test_every_deck_reads` and `test_topology_walk.py::test_every_deck_walks`: the same 23 decks
  each.

Nothing skips for a missing engine: the `gridlabd` wheel is a test dependency, so the oracle tests always run.
