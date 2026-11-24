# Atom tests: reference

Companion to [SKILL.md](SKILL.md).

## 1. Complete import, bind and classification tests (DSS LineCode)

```python
"""Atom tests: OpenDSS LineCode -> linecode.cimtbl -> cim18v17."""

from pathlib import Path

import pytest

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimhub_opendss.importer.cimtbl.linecode import FIELDS, NATIVE_CLASS, b_from_c, lower_triangle, map_linecode
from cimhub_opendss.schema import opendss_schema as schema

ATOMS = Path(__file__).parent / "atoms" / "linecode"
FEET_PER_MILE = 5280


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def mtx601():
    return map_linecode(DssReader(ATOMS / "mtx601.dss").read_all())


def _native(*codes):
    """A stand-in native graph for unit tests of single records."""
    return type("Native", (), {"list_by_class": staticmethod(lambda cls: list(codes))})()


def test_classification_is_complete():                       # classification test
    check_fields(FIELDS, NATIVE_CLASS)


def test_lower_triangle_and_full_matrix_agree():              # structural helper
    triangle = lower_triangle([1, 2, 3, 4, 5, 6], 3, name="t", slot="rmatrix")
    full = lower_triangle([1, 2, 4, 2, 3, 5, 4, 5, 6], 3, name="t", slot="rmatrix")
    assert triangle == full == {(1, 1): 1, (2, 1): 2, (2, 2): 3, (3, 1): 4, (3, 2): 5, (3, 3): 6}


def test_matches_golden(mtx601):                              # import test
    assert_matches_golden(mtx601, ATOMS / "mtx601.cimtbl")


def test_binds_under_cim18v17(mtx601):                        # bind test
    network = cimtbl_to_cim(atom_documents(mtx601))
    [impedance] = network.graph[network.cim.PerLengthPhaseImpedance].values()
    assert impedance.mRID == "lc_mtx601" and impedance.conductorCount == 3
    data = {(d.row, d.column): d for d in network.graph[network.cim.PhaseImpedanceData].values()}
    assert float(data[(2, 1)].r.to("ohm/mi")) == pytest.approx(0.1535)
    assert float(data[(1, 1)].x.to("ohm/ft")) * FEET_PER_MILE == pytest.approx(1.0179)


@pytest.mark.parametrize(("code", "message"), [                # one case per fail-fast rule
    (schema.Linecode(name="x", nphases=1, units="none", rmatrix=[0.1], xmatrix=[0.2]),
     "x: units='none' has no mapping"),
    (schema.Linecode(name="bare", nphases=3, units="ft"), "bare: sets no impedance"),
])
def test_ambiguous_or_unmapped_codes_fail_fast(code, message):
    with pytest.raises(ValueError, match=message):
        map_linecode(_native(code))
```

`DssReader` is the spoke's `FormatReader`; import it from the spoke's reader module.

## 2. Prerequisites

A prereq is ordinary `.cimtbl` holding what the atom references but does not declare:

```
# Prerequisites of the transformer atoms: the container and the BaseVoltages the topology walk would give.

Profile = cim18v17

Object Substation: mRID=sub_atom, name=atom
Object Feeder: mRID=fdr_atom, name=atom, NormalEnergizingSubstation=sub_atom

Table BaseVoltage: mRID, nominalVoltage (kV)
    bv_4p16kv,  4.16
    bv_480v,    0.48
```

```python
def _bind(case):
    return cimtbl_to_cim(atom_documents(_map(case)), network=cimtables.load_model(ATOMS / "prereq.cimtbl"))
```

- Context a whole spoke shares (a Feeder, common BaseVoltages, a two-node network) goes in
  `cimhub_<fmt>/tests/atoms/prereqs/` (GDM: `shell.cimtbl`).
- Prereq mRIDs follow the same prefix rules as artifacts (`fdr_`, `bv_`, `sub_`).
- Mapper inputs that come from another step (the topology walk's `BusSystem`s) are passed explicitly in the test
  (a `BUSES` dict), so the atom tests one mapper.

## 3. Export tests

Each spoke names its check on its testing page or spec. RAW compares records field by field
(`cimhub_raw/tests/test_cim_to_raw.py`); GridLAB-D and GDM import the export again and compare CIM with
`cimtables.diff_models` (`cimhub_gridlabd/tests/test_export_atoms.py`, `cimhub_gdm/tests/test_export_round_trip.py`);
OpenDSS compares a deck golden and the engine state (`cimhub_opendss/tests/test_export_line.py`). The field-by-field
form:

```python
def test_export_matches_native_atom():
    network = cimtables.load_model(PREREQS / "<prereq>.cimtbl")
    cimtables.load(ATOMS / "mtx601.cimtbl", network)
    exported = DssExporter().to_model(network)                    # FormatExporter.to_model -> SpokeGraphModel
    expected = DssReader(ATOMS / "mtx601.dss").read_all()
    skipped = {slot for slot, field in FIELDS.items() if field.kind == "untranscribed"}
    # compare each NATIVE_CLASS record slot by slot, except `skipped`
```

- The exporter reads CIM through the core getters (skill `export-getters`), so an export failure points at the getter
  or the spoke mapping, not at a file layout.
- Floats compare with `pytest.approx`; text compares exactly.
- A field the export cannot reproduce (a structural default) is listed in the spec's expected differences and
  skipped by name, never by a broad tolerance.

## 4. Round trip of a reference model

- `<fmt>_to_cim(<Fmt>Reader(path).read_all(), artifact_dir=tmp_path)` → `cim_to_<fmt>` → re-read with the native reader → compare.
- The reference model's artifact directory is committed as a golden (D6), so an importer change shows as a text diff.
- Expected differences from hand translations are listed in the spec; the test names them.

## 5. Cross-format

- Lives at the repo root, `tests/cross_format/`, never in a spoke. Uses only public model pairs.
- Loads two spokes' goldens for the same equipment and compares in SI within a tolerance.
- Matches by class + connected nodes, or by a small hand-written correspondence map per model pair. Never by mRID or
  UUID: the same transformer is `xf_xfm1` in one format and something else in another, and two `Model` scopes seed
  different UUIDs.
- Loading two models in one test: wrap each load in `cim_scope()`, or use the `model_scope` fixture pattern in
  CIM-Tables `tests/test_load_model.py`.

## 6. Reading a failure

`assert_matches_golden` reports records, not text:

```
mtx601.cimtbl differs from the mapper output (CIMHUB_UPDATE_GOLDENS=1 rewrites it):
  PhaseImpedanceData lc_mtx601_21.r (ohm/mi): expected '0.1535', got '0.153'
  missing PhaseImpedanceData lc_mtx601_33
```

Records are keyed by mRID, else `identifier`, else `path`, else position within the class. When the records match but
comments or layout differ, it prints the first lines of a unified diff instead.

## 7. Checklist for a new native table

- [ ] native atom file(s) from a public deck, one per shape the table can produce
- [ ] golden `.cimtbl` per atom, reviewed row by row against the spec
- [ ] `test_classification_is_complete`
- [ ] `test_matches_golden` per atom
- [ ] bind test per atom, with SI value checks on copied, derived and structural values
- [ ] unit tests for each derived and structural helper
- [ ] one fail-fast test per rule in the spec
- [ ] export test once the exporter half of the wave lands
