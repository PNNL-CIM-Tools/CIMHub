# Testing

How CIMHub is tested, and how to add a test. The rules for Claude Code live in the
[`atom-tests` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/atom-tests/SKILL.md);
this page is the human guide. Units follow [Units](units.md), the shape of a package follows
[Architecture](architecture.md), the converter entry points are on [Converter API](converter-api.md), and the
helpers a mapper test calls are on [The .cimtbl import contract](cimtbl.md).

## Running the tests

```bash
uv sync
scripts/test-all.sh                    # every package with tests, one pytest process each, then cross_format
scripts/test-all.sh core opendss       # only the named packages (cimhub_ prefix optional)
scripts/test-all.sh cross_format       # only the root tier-4 tests in tests/cross_format
scripts/test-all.sh opendss -- -x -q   # arguments after -- go to pytest
uv run pytest cimhub_opendss/tests/test_cimtbl_linecode.py   # one file
```

Never run one pytest over the whole repo. cimtables sets the CIM profile and the model scope process-wide, so each
package's suite needs its own interpreter. For the same reason `tests/` directories have no `__init__.py`.
[`scripts/test-all.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/test-all.sh) runs each suite
in turn, prints `all N suites passed` or lists the failed ones, and exits non-zero if any failed. A name that has
no `tests/` directory is an error (exit 2).

`PYTEST` replaces the runner. The default is `uv run pytest`. To test installed wheels in another environment:

```bash
PYTEST=venv/bin/pytest scripts/test-all.sh
```

Before a commit, also run
[`scripts/leak-gate.sh`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/scripts/leak-gate.sh). It must print
`leak-gate: clean` (see [Fixture provenance](#fixture-provenance)).

### Markers, options and environment variables

| name | where | effect |
|---|---|---|
| `roundtrip` (marker) | registered in the root `pyproject.toml`; used by `cimhub_opendss` and `cimhub_gridlabd` | Whole-deck tests that need large models or are slow. |
| `--roundtrip` (option) | `tests/conftest.py` of `cimhub_opendss` and `cimhub_gridlabd` | Runs the `roundtrip` tests. Without it they are skipped (`whole-deck test; pass --roundtrip to run` in OpenDSS). |
| `CIMHUB_UPDATE_GOLDENS=1` | `cimhub_core.cimtbl_testing` | Golden comparisons rewrite the golden instead of comparing. See [Reviewing a golden diff](#reviewing-a-golden-diff). |
| `CIMHUB_DSS_DECKS` | `cimhub_opendss/tests/conftest.py`, `tests/cross_format/test_dss_to_glm.py` | A directory with the same layout as `cimhub_opendss/tests/decks/` (for example `IEEE/IEEE8500/Master.dss`). Decks that are not vendored are read from here; without it their tests skip. |
| `CIMHUB_GLM_DECKS` | `cimhub_gridlabd/tests/conftest.py` | The same for GridLAB-D decks that are not vendored in `cimhub_gridlabd/tests/decks/`. |
| `CIMHUB_GDMLOADER=1` | `cimhub_gdm/tests/test_ditto_sweep.py` | Adds the gdmloader systems to the GDM sweep. Opt-in because it downloads. |

Run the whole-deck tests like this:

```bash
CIMHUB_DSS_DECKS=/path/to/decks scripts/test-all.sh opendss -- --roundtrip
```

`CIMHUB_UPDATE_GOLDENS` is read in two places. `cimtbl_testing` rewrites a golden only when it is exactly `1`. The
OpenDSS exporter's deck goldens (`cimhub_opendss/tests/export_atoms.py`) rewrite on any non-empty value, so set
it to `1` in both cases.

## Test tiers

Every test checks one hop of the pipeline. A failure then points at one place.

```text
native file -> reader -> mapper -> .cimtbl text -> cimtables -> CIM -> getters -> exporter -> native file
              |__________ tier 1 ___________|
                                      |___ tier 1b ___|
                                                      |____________ tier 2 ____________|
              |______________________________ tier 3 ______________________________|
```

| tier | what runs | what it asserts |
|---|---|---|
| 1 importer | native atom, reader, mapper, formatted text | The text equals the reviewed golden `.cimtbl`. A failure shows a record diff. |
| 1b bind | golden (plus prerequisites), cimtables | The golden binds under cim18v17, and key values are right in SI (`.to(unit)`). |
| 2 exporter | golden (plus prerequisites), CIM, exporter | The exported native records equal the native atom, field by field, minus the fields the spec lists as untranscribed. Where a native atom would not round trip byte for byte (GridLAB-D), the exported deck is read back and imported again, and the two CIM models are equal under `cimtables.diff_models` except for the listed differences. |
| 3 round trip | a whole reference model through import and export | Power flow or the re-imported artifacts agree. Expected differences are listed in the spoke's spec. |
| 4 cross-format | the same equipment from two spokes' goldens | Equal in SI within a tolerance, matched by topology, never by mRID. Lives in the root `tests/cross_format/`. |
| spec | `check_fields(FIELDS, NATIVE_CLASS)` | The field classification covers every slot of the native class (invariant I3). |

Tier 4 needs two formats. It lives at the repo root, never inside a spoke, and uses only public model pairs. It
binds the committed golden directories of both spokes with cimtables alone (no reader, no engine) and compares
through the core getters.

### What exists today

| package | tier 1, 1b, spec | tier 2 | tier 3 | other |
|---|---|---|---|---|
| `cimhub_core` | not applicable | not applicable | not applicable | Unit tests of `cimtbl`, `cimtbl_testing`, `getters/`, `derived/`, `shapes/` (every shape loads), names, time points and `GraphModel`. |
| `cimhub_opendss` | `test_cimtbl_<native_table>.py`, one per table, with atoms | `test_export_*.py`, atoms in `atoms/*/export/` | `test_export_decks.py`: power-flow parity in the OpenDSS engine, bus coordinates, idempotence | Reader and writer tests, `test_topology_walk.py`, and `test_cimtbl_sweep.py`, which maps and binds every deck. |
| `cimhub_gridlabd` | `test_cimtbl_<native_table>.py` with atoms in `tests/atoms/` | `test_export_atoms.py`, `test_export_players.py`, `test_export_schedules.py` | `test_export_decks.py` | Reader and writer tests, `test_topology_walk.py`, `test_cimtbl_sweep.py`. |
| `cimhub_raw` | `test_raw_to_cimtbl.py` against `tests/goldens/` and `tests/atoms/` | `test_cim_to_raw.py` (atoms) | `test_cim_to_raw.py` (whole cases) | `test_raw34_reader.py`, `test_phase2_stubs.py`. |
| `cimhub_gdm` | `test_<family>_import.py` against `.cimtbl` goldens (GDM has no native file, see below) | `test_export_*.py` | `test_export_round_trip.py` (golden, export, re-import, same golden) and `test_xml_round_trip.py` | `test_ditto_sweep.py`, `test_reference_import.py`. |
| root `tests/cross_format/` | | | | Tier 4: `test_ieee13_glm_vs_dss.py`, `test_dss_to_glm.py`, `test_glm_to_dss.py`, `test_glm_player_to_dss.py`, `test_glm_schedule_elsewhere.py`. |

GDM is builder-native: there is no native file and no artifact. Its atoms are small systems built in Python
(`cimhub_gdm/tests/gdm_atoms.py`), and the comparison is at CIM level with `cimtables.diff_models`. The details are in
[`cimhub_gdm/docs/TEST_DESIGN.md`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_gdm/docs/TEST_DESIGN.md).

## Atoms and goldens

An atom is a pair of text files: a minimal native file that the real reader parses, and the `.cimtbl` golden the
mapper must produce from it. There are no Python factories for CIM objects. CIM objects in tests come from `.cimtbl`
text that cimtables loads.

```text
cimhub_<fmt>/tests/atoms/<native_table>/<case>.<ext>      # native atom (.dss, .glm, .raw, ...)
cimhub_<fmt>/tests/atoms/<native_table>/<case>.cimtbl     # golden, reviewed by a human
cimhub_<fmt>/tests/atoms/<native_table>/prereq.cimtbl     # context the atom references but does not declare
cimhub_<fmt>/tests/test_cimtbl_<native_table>.py          # tiers 1, 1b, spec and mapper unit tests
```

Example:
[`cimhub_opendss/tests/atoms/linecode/mtx601.dss`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/linecode/mtx601.dss)
and
[`mtx601.cimtbl`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/atoms/linecode/mtx601.cimtbl),
tested by
[`test_cimtbl_linecode.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/test_cimtbl_linecode.py).

Some conventions:

- A native atom has one record, or the few that a structural field needs. Name the case after the record (`mtx601`).
- Whole-model goldens, one `.cimtbl` file per native table, live in `tests/goldens/<model>/`
  (`cimhub_raw/tests/goldens/IEEE14/`, `cimhub_opendss/tests/goldens/IEEE13_CDPSM/`).
- An atom that references objects it does not declare (a BaseVoltage, a Feeder, a template) binds onto a network
  loaded from a prerequisite: `cimtbl_to_cim(atom_documents(document), network=cimtables.load_model(prereq))`. A
  prerequisite that one table needs sits beside its atoms as `prereq.cimtbl` (see `atoms/transformer/prereq.cimtbl`
  in `cimhub_opendss`).
- Mapper inputs that come from another step, such as the topology walk's bus systems, are passed explicitly in the
  test, so each atom tests one mapper.

### Helpers

`cimhub_core.cimtbl_testing` (source:
[`cimtbl_testing.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_core/src/cimhub_core/cimtbl_testing.py)):

| helper | does |
|---|---|
| `cim_scope()` | Context manager that restores `CIMG_CIM_PROFILE`, the model scope and the cached CIM profile after a load. |
| `atom_documents(*parts, name="atom")` | A master (`Profile = cim18v17`) that imports `parts` in order. Empty parts (no statements) are left out. Returns a `DocumentSet`. |
| `assert_matches_golden(document, golden_path)` | Text equality of `format_document(document)` with the golden. With `CIMHUB_UPDATE_GOLDENS=1` it rewrites the golden. |
| `assert_text_matches_golden(text, golden_path)` | The same for text you already have: a written artifact file, or a native file an exporter wrote. A `.cimtbl` golden's failure lists records, any other golden's a unified diff. |
| `record_diff(expected, actual)` | Record-level differences: `expected X, got Y`, `missing ...`, `extra ...`. Ignores comments, column order and padding. Empty when the records agree. |
| `UPDATE_GOLDENS` | The name of the environment variable, `"CIMHUB_UPDATE_GOLDENS"`. |

From `cimhub_core.cimtbl`: `check_fields` and `cimtbl_to_cim`. From cimtables: `load_model`, `load`, `diff_models`.

Every test that loads `.cimtbl` runs inside `cim_scope()`, because `load_model` sets the profile and model scope for
the whole process. The usual form is an autouse fixture, as in `cimhub_gdm/tests/conftest.py`:

```python
@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield
```

### Reviewing a golden diff

A golden is reviewed text. Never edit one by hand to make a test pass, and never commit a regenerated golden you have
not read.

```bash
CIMHUB_UPDATE_GOLDENS=1 uv run pytest cimhub_opendss/tests/test_cimtbl_linecode.py
git diff cimhub_opendss/tests/atoms
```

Then read every changed row against the native atom and the spoke's `docs/CIMTBL_MAPPING.md`. A change you cannot
explain is a mapper bug.

When a comparison fails, the message names records, not lines of text:

```text
ohm1.cimtbl differs from the mapper output (CIMHUB_UPDATE_GOLDENS=1 rewrites it):
  PhaseImpedanceData lc_ohm1_11.r (ohm/km): expected '0.6', got '0.5'
```

Records match by mRID, else `identifier`, else `path`, else position in the class. If the records match and only
comments or layout differ, the message says `the records match; comments or layout differ:` and shows the first
40 lines of a unified diff.

One limit: an `Update` row has the same key as the object it updates (`BaseVoltage a`), so the two share one entry in
the comparison and the later row replaces the earlier one. A changed value in the earlier row is then hidden. The
test still fails (the text differs), but the message says the records match and shows a unified diff. If only one
side has the `Update` row, the columns of the earlier row are reported as `<no column>`. When either message appears
on a file with `Update` rows, diff the files with `git diff`.

## Adding an atom test (OpenDSS walkthrough)

This adds a one-phase LineCode case. Put the files beside the others in
`cimhub_opendss/tests/atoms/linecode/` and the test in `cimhub_opendss/tests/test_cimtbl_linecode.py`.

**1. Write the native atom.** Use real OpenDSS text, in the units the deck uses. `ohm1.dss`:

```text
New Circuit.t basekv=12.47
New Linecode.ohm1 nphases=1 r1=0.5 x1=0.25 r0=1.5 x0=0.75 C1=10 C0=5 units=km baseFreq=60
New Line.l1 bus1=sourcebus.1 bus2=b1.1 phases=1 linecode=ohm1 length=1 units=km
```

**2. Write the test.** It does not need the golden yet:

```python
ATOMS = Path(__file__).parent / "atoms" / "linecode"

@pytest.fixture(scope="module")
def ohm1():
    return map_linecode(DssReader(ATOMS / "ohm1.dss").read_all(), base_frequency=60.0)

def test_matches_golden(ohm1):                                    # tier 1
    assert_matches_golden(ohm1, ATOMS / "ohm1.cimtbl")

def test_binds_under_cim18v17(ohm1):                              # tier 1b
    network = cimtbl_to_cim(atom_documents(ohm1))
    [data] = network.graph[network.cim.PhaseImpedanceData].values()
    assert float(data.r.to("ohm/km")) == pytest.approx(0.5)       # verbatim from the deck
    assert float(data.x.to("ohm/km")) == pytest.approx(0.25)
```

The imports, the autouse `cim_scope` fixture and the `test_classification_is_complete` spec test are already in the
file. A new test file needs all three; `scaffold_mapper` in `cimhub_core.scaffold` writes the spec test.

Check expected values against the deck, or against a formula written in the test. Do not copy numbers the mapper
printed.

**3. Generate the golden, then read it.**

```bash
CIMHUB_UPDATE_GOLDENS=1 uv run pytest cimhub_opendss/tests/test_cimtbl_linecode.py -k ohm1
cat cimhub_opendss/tests/atoms/linecode/ohm1.cimtbl
```

The golden has one `PerLengthPhaseImpedance` row (`lc_ohm1`, `conductorCount` 1, `isTemplate` true), one
`PhaseImpedanceData` row with `r (ohm/km)` 0.5 and `x (ohm/km)` 0.25, and the `WireConfiguration` `lc_ohm1_wc` that
holds the template. The unit sits in the column header, and the values are the deck's, copied. The `b (nS/km)`
column is derived: `C1` of 10 nF at 60 Hz gives `3769.9111843077517`, by `b_from_c`. The row comment says the
matrix came from a one-phase sequence code and that the line does not use `r0`, `x0` and `C0`. Check each row against
the atom and the LineCode section of
[`cimhub_opendss/docs/CIMTBL_MAPPING.md`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/docs/CIMTBL_MAPPING.md).

**4. Run it without the variable.**

```bash
uv run pytest cimhub_opendss/tests/test_cimtbl_linecode.py -k ohm1
```

**5. Cover the rest.** One test per fail-fast rule in the spec, using `pytest.raises(ValueError, match=...)` and a
record built from the schema class (`schema.Linecode(name=..., ...)`). One unit test for each derived or structural
helper (`b_from_c`, `lower_triangle`). For a new native table, the checklist in the skill's
[reference](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/atom-tests/reference.md) applies.

For a tier 2 test, load the golden and its prerequisites with `cimtables.load_model` and `cimtables.load`, run the
exporter, read the native atom with the reader, and compare each class slot by slot. Skip fields by name, from the
spec's untranscribed list, never with a loose tolerance. The exporter's `SLOTS` dict
([`export_slots`](cimtbl.md#export-slots)) lists every slot, and `check_slots` tests that it is complete.
[`cimhub_opendss/tests/test_export_line.py`](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/cimhub_opendss/tests/test_export_line.py)
is a working example. The recipes for tiers 2 to 4 are in the skill's
[reference](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/atom-tests/reference.md).

### Native engine tests

OpenDSS tests compare against the engine (`opendssdirect`), which is a test oracle only. `Compile` changes the
process working directory, and a deleted temporary directory then makes the next `Compile` crash.
`cimhub_opendss/tests/conftest.py` calls `opendssdirect.Basic.AllowChangeDir(False)` for this reason; use its
`compile_deck` helper instead of calling `Compile` yourself. The helper also puts `defaultbasefreq` back to 60 Hz,
because `Clear` does not.

## Fixture provenance

The repo is meant to be public, so every fixture needs a public origin.

- Atoms and decks come from public models: IEEE test feeders, EPRI test circuits, NREL and University of Washington
  cases. A model from a utility or vendor never goes in an atom.
- Every fixture directory has a `README.md` with the origin, the license or terms, and any local edits. See
  `cimhub_opendss/tests/decks/README.md`, `cimhub_gridlabd/tests/decks/README.md` and
  `cimhub_raw/tests/cases/README.md`.
- A file over 10 MB does not go in git. `scripts/leak-gate.sh` fails on it. Large models are read from a directory
  named by an environment variable (`CIMHUB_DSS_DECKS`, `CIMHUB_GLM_DECKS`), and their tests skip when it is unset.
- Tests do not import vendor spokes, and no test names a path outside the repo. The gate also fails on a
  path into a user's home directory anywhere in the tree, so keep local paths out of docs and comments too.

The full rules are in the
[`split-readiness` skill](https://github.com/PNNL-CIM-Tools/CIMHub/blob/develop/.claude/skills/split-readiness/SKILL.md).
Run `scripts/leak-gate.sh` before every commit.
