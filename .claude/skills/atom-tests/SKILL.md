---
name: atom-tests
description: How CIMHub tests converters - atoms as native-file + golden `.cimtbl` text pairs under `cimhub_<fmt>/tests/atoms/<native_table>/`, shared prerequisites, the test types (import, bind, export, round trip, cross-format, classification, parity) and the `cimhub_core.cimtbl_testing` helpers. Use when adding or changing a mapper or exporter test, reviewing a golden diff, or regenerating goldens.
---

# Atom tests

An atom is a **text pair**: a minimal, complete native file the real reader parses, and the reviewed `.cimtbl` golden
the mapper must produce from it. There are no Python CIM factories: CIM objects in tests come from `.cimtbl` text
loaded by cimtables.

```
cimhub_<fmt>/tests/atoms/<native_table>/<case>.<ext>     # native atom: the real reader parses it
cimhub_<fmt>/tests/atoms/<native_table>/<case>.cimtbl    # golden artifact, reviewed by a human
cimhub_<fmt>/tests/test_cimtbl_<native_table>.py         # import, bind, classification + mapper unit tests
cimhub_<fmt>/tests/atoms/<native_table>/prereq.cimtbl    # context the atoms reference: container, BaseVoltages, nodes
```

Example: `cimhub_opendss/tests/atoms/linecode/mtx601.dss` + `mtx601.cimtbl`, tested by
`cimhub_opendss/tests/test_cimtbl_linecode.py`.

## Test types

| test | what runs | assertion |
|---|---|---|
| import | native atom → reader → mapper → formatted text | `assert_matches_golden(document, golden)`: text equals the golden; failure shows a record diff |
| bind | golden (+ prereqs) → cimtables | `cimtbl_to_cim(atom_documents(document))` binds under cim18v17; key values checked in SI via `.to(unit)` |
| export | atom → import → CIM → exporter → native | the export reproduces the atom, by the check the spoke names on its testing page or spec: RAW field by field against the atom, minus untranscribed fields; GridLAB-D and GDM import the export again and compare CIM with `cimtables.diff_models`, minus listed differences; OpenDSS a reviewed deck golden (`atoms/<table>/export/`, `assert_matches_dss_golden`) and both decks solved in the engine (`assert_same_engine_state`) |
| round trip | reference model native → artifacts → CIM → native | per spoke; expected differences listed in the spec |
| cross-format | the same equipment from two spokes' goldens → CIM | equal in SI within tolerance; root `tests/cross_format/`, public pairs only, matched by topology not mRID |
| classification | field classification | `check_fields(FIELDS, NATIVE_CLASS)` covers every LinkML slot (I3) |
| parity | builder keyword methods vs `.cimtbl` rows | lives in CIM-Builder, not here |

## Rules

1. **Native atoms are real files** the spoke's reader parses: one record (or the few a structural field needs),
   every field the case exercises, no padding. Name the case after the record (`mtx601`, `xfm1`).
2. **Goldens are reviewed text.** Write them with the mapper, then read every row against the native atom and the
   spec before committing. `CIMHUB_UPDATE_GOLDENS=1 uv run pytest ...` rewrites goldens; review the git diff.
3. **Every `.cimtbl` load runs inside `cim_scope()`,** as an autouse fixture. `load_model` sets the profile and model
   scope process-wide.
4. **Prerequisites are `.cimtbl`, not Python.** An atom that references objects it does not declare (a template, a
   BaseVoltage, a Feeder) binds onto a network loaded from prereqs:
   `cimtbl_to_cim(atom_documents(document), network=cimtables.load_model(prereq))`. A prereq sits next to its
   atoms as `prereq.cimtbl`; context a whole spoke shares goes in `cimhub_<fmt>/tests/atoms/prereqs/`.
5. **Assert values in SI or a named unit**, never against a raw CIMUnit: `float(data.r.to("ohm/mi")) == approx(0.1535)`.
6. **Expected derived values come from an independent formula** written in the test (`0.02 * 4160**2 / 500e3`), or
   from the named function's own unit test. Never paste numbers the mapper printed.
7. **One test per fail-fast rule** in the spec: `pytest.raises(ValueError, match="<record>: <slot>...")`. Unit-test
   fail-fast and edge cases with records built from the LinkML schema class (`schema.Linecode(name=..., ...)`); the
   golden pair stays the file-based case.
8. **Unit-test every derived and structural helper** (`b_from_c`, `lower_triangle`) on its own.
9. **CIM-level comparison** uses `cimtables.diff_models(expected, actual, rel_tol=1e-9) -> list[str]` (matches by
   class + mRID, or `identifier`); assert it returns `[]`. Builder-native spokes (GDM) test this way against a
   `.cimtbl` golden.
10. **Fixtures must have a public origin.** Atoms come from public decks (IEEE, EPRI test circuits). Mixed-spoke tests
    live only at the root `tests/cross_format/`.

## Helpers (`cimhub_core.cimtbl_testing`)

| helper | does |
|---|---|
| `cim_scope()` | context manager; restores `CIMG_CIM_PROFILE` and the cimgraph model scope after a load |
| `atom_documents(*parts, name="atom") -> DocumentSet` | a master (`Profile = cim18v17`) importing `parts` in order; empty parts left out |
| `assert_matches_golden(document, golden_path)` | text equality with the golden; with `CIMHUB_UPDATE_GOLDENS=1` it rewrites the golden instead |
| `record_diff(expected_text, actual_text) -> list[str]` | `Class key.column: expected X, got Y`, `missing ...`, `extra ...`; ignores comments, column order and padding |

From `cimhub_core.cimtbl`: `check_fields`, `cimtbl_to_cim`. From cimtables: `load_model`, `load`, `diff_models`.

## Skeleton

```python
@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield

@pytest.fixture(scope="module")
def mtx601():
    return map_linecode(DssReader(ATOMS / "mtx601.dss").read_all())

def test_classification_is_complete():
    check_fields(FIELDS, NATIVE_CLASS)

def test_matches_golden(mtx601):
    assert_matches_golden(mtx601, ATOMS / "mtx601.cimtbl")

def test_binds_under_cim18v17(mtx601):
    network = cimtbl_to_cim(atom_documents(mtx601))
    data = {(d.row, d.column): d for d in network.graph[network.cim.PhaseImpedanceData].values()}
    assert float(data[(2, 1)].r.to("ohm/mi")) == pytest.approx(0.1535)   # verbatim from the deck
```

`scaffold_mapper` writes the completeness test; add the rest. Full example, export, round-trip and cross-format recipes: [reference.md](reference.md).

## Anti-patterns

- Building atoms or prerequisites with `cim.X(...)`, `network.add_to_graph(...)` or factory functions.
- A golden regenerated and committed without reading the diff; a golden edited by hand to make a test pass.
- Comparing whole files with `==` in an ad hoc test instead of `assert_matches_golden` (no record diff on failure).
- `line.r == 0.1535` or `line.r.value` checks; skipping `cim_scope()`.
- Expected values copied from mapper output; one test asserting many unrelated things.
- A cross-format test inside a spoke package, or matching cross-format objects by mRID.
- Vendor or private model data in an atom.
