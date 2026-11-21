"""Atom tests: OpenDSS LineCode -> linecode.cimtbl -> cim18v17 (rewrite plan Phase 1 exit slice)."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimhub_opendss.importer.cimtbl.linecode import (FIELDS, NATIVE_CLASS, b_from_c, gated_unit, lower_triangle,
                                                    map_linecode, susceptance, templates)
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.schema import opendss_schema as schema

ATOMS = Path(__file__).parent / "atoms" / "linecode"
FEET_PER_MILE = 5280


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def mtx601():
    return _map(DssReader(ATOMS / "mtx601.dss").read_all())


@pytest.fixture(scope="module")
def sequence():
    return _map(DssReader(ATOMS / "seq_3_1_0c.dss").read_all())


def _native(*codes, lines=()):
    by_class = {NATIVE_CLASS: list(codes), schema.Line: list(lines)}
    return type("Native", (), {"list_by_class": staticmethod(lambda cls: by_class.get(cls, []))})()


def _map(native):
    return map_linecode(native, base_frequency=60.0)


def test_classification_is_complete():
    check_fields(FIELDS, NATIVE_CLASS)


def test_b_from_c():
    assert b_from_c(3.4, 60.0) == pytest.approx(2 * math.pi * 60 * 3.4)
    assert b_from_c(0.0, 60.0) == 0.0


def test_susceptance_of_zero_needs_no_frequency():
    assert susceptance("0", None, name="buswork", slot="C1") == 0.0
    assert susceptance("3.4", "60", name="t", slot="C1") == pytest.approx(b_from_c(3.4, 60.0))
    with pytest.raises(ValueError, match="t: C1 needs baseFreq"):
        susceptance("3.4", None, name="t", slot="C1")


def test_lower_triangle_and_full_matrix_agree():
    triangle = lower_triangle([1, 2, 3, 4, 5, 6], 3, name="t", slot="rmatrix")
    full = lower_triangle([1, 2, 4, 2, 3, 5, 4, 5, 6], 3, name="t", slot="rmatrix")
    assert triangle == full == {(1, 1): 1, (2, 1): 2, (2, 2): 3, (3, 1): 4, (3, 2): 5, (3, 3): 6}
    with pytest.raises(ValueError, match="rmatrix has 4 values; nphases=3 needs 6"):
        lower_triangle([1, 2, 3, 4], 3, name="t", slot="rmatrix")


def test_matches_golden(mtx601):
    assert_matches_golden(mtx601, ATOMS / "mtx601.cimtbl")


def test_binds_under_cim18v17(mtx601):
    network = cimtbl_to_cim(atom_documents(mtx601))
    cim = network.cim
    [impedance] = network.graph[cim.PerLengthPhaseImpedance].values()
    assert impedance.mRID == "lc_mtx601" and impedance.conductorCount == 3

    data = {(d.row, d.column): d for d in network.graph[cim.PhaseImpedanceData].values()}
    assert sorted(data) == [(1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3)]
    # verbatim from the deck (IEEE13_CDPSM.dss), not the corrected off-diagonals of the hand translation
    assert float(data[(2, 1)].r.to("ohm/mi")) == pytest.approx(0.1535)
    assert float(data[(1, 1)].x.to("ohm/ft")) * FEET_PER_MILE == pytest.approx(1.0179)
    assert float(data[(3, 3)].b.to("S/mi")) == 0.0


def test_mrid_is_lowercased():
    code = schema.Linecode(name="MTX601", nphases=1, units="ft", rmatrix=[0.1], xmatrix=[0.2])
    [table, _, configurations] = _map(_native(code)).statements
    assert table.rows[0].cells[:2] == ["lc_mtx601", "MTX601"]
    assert configurations.rows[0].cells == ["lc_mtx601_wc", "MTX601", "lc_mtx601"]


def test_unmapped_units_fail_fast():
    code = schema.Linecode(name="x", nphases=1, units="furlong", rmatrix=[0.1], xmatrix=[0.2])
    with pytest.raises(ValueError, match="x: units='furlong' has no mapping"):
        _map(_native(code))


def test_sequence_matches_golden(sequence):
    assert_matches_golden(sequence, ATOMS / "seq_3_1_0c.cimtbl")


def test_sequence_binds_under_cim18v17(sequence):
    network = cimtbl_to_cim(atom_documents(sequence))
    [impedance] = network.graph[network.cim.PerLengthSequenceImpedance].values()
    assert impedance.mRID == "lc_3-1/0c_2/0cn_t"
    assert float(impedance.r.to("ohm/km")) == pytest.approx(0.3489)
    assert float(impedance.x0.to("ohm/km")) == pytest.approx(1.29612)
    # derived: b = 2 pi 60 Hz 10.4308823411236 nF/km
    assert float(impedance.bch.to("uS/km")) == pytest.approx(3.93235, rel=1e-6)


def test_sequence_b_is_copied_in_microsiemens():
    code = schema.Linecode(name="b", nphases=3, units="mi", r1=0.1, x1=0.3, B1="5.1", C0="0", baseFreq="60")
    [table, _] = _map(_native(code)).statements
    assert [(column.name, column.unit) for column in table.columns][-3:-1] == [("bch", "uS/mi"), ("b0ch", "nS/mi")]
    assert table.rows[0].cells[-3:-1] == ["5.1", "0.0"]


def test_sequence_codes_group_by_header():
    with_c = schema.Linecode(name="c", nphases=3, units="km", r1=0.1, C1="10", baseFreq="60")
    with_b = schema.Linecode(name="b", nphases=3, units="km", r1=0.1, B1="3.7")
    other_unit = schema.Linecode(name="m", nphases=3, units="mi", r1=0.1, C1="10", baseFreq="60")
    *tables, _ = _map(_native(with_c, with_b, other_unit, with_c)).statements
    assert [len(table.rows) for table in tables] == [2, 1, 1]


@pytest.mark.parametrize(("code", "message"), [
    (schema.Linecode(name="seq1", nphases=1, units="km", r1=0.1, x1=0.3, B1="2"), "seq1: B1/B0 on a 1-phase"),
    (schema.Linecode(name="cb", nphases=3, units="km", C1="10", B1="3.7"), "cb: sets both C1 and B1"),
    (schema.Linecode(name="both", nphases=1, units="ft", r1=0.1, rmatrix=[0.1], xmatrix=[0.2]),
     "both: sets both matrix and sequence"),
    (schema.Linecode(name="bare", nphases=3, units="ft"), "bare: sets no impedance"),
])
def test_ambiguous_or_unmapped_codes_fail_fast(code, message):
    with pytest.raises(ValueError, match=message):
        _map(_native(code))


# --- S2: units (DSS-3), base frequency (DSS-3b), 1- and 2-phase sequence codes (DSS-4) ---

def _sequence_code(name, **slots):
    return schema.Linecode(name=name, **{"nphases": 3, "r1": 0.1, "x1": 0.3, "r0": 0.3, "x0": 0.9, **slots})


def test_unitless_codes_take_their_lines_units_else_the_gate():
    by_code = templates(DssReader(ATOMS / "unitless.dss").read_all())
    assert [(t.mrid, t.unit) for t in by_code["single"]] == [("lc_single", "kft")]
    assert [(t.mrid, t.unit) for t in by_code["split"]] == [("lc_split_kft", "kft"), ("lc_split_mi", "mi")]
    [spare] = by_code["spare"]
    assert (spare.mrid, spare.unit) == ("lc_spare", "km") and spare.note.startswith("units inferred: km")


def test_unitless_matches_golden():
    assert_matches_golden(_map(DssReader(ATOMS / "unitless.dss").read_all()), ATOMS / "unitless.cimtbl")


@pytest.mark.parametrize("r1, unit", [(0.006, "km"), (9.9, "km"), (0.0002, "m"), (1e-5, "m")])
def test_the_magnitude_gate(r1, unit):
    assert gated_unit([_sequence_code("g", r1=r1)])[0] == unit


@pytest.mark.parametrize("r1", [10.0, 5e-6])
def test_a_median_outside_the_gate_raises(r1):
    with pytest.raises(ValueError, match="fits no length unit"):
        gated_unit([_sequence_code("g", r1=r1)])


def test_length_unit_overrides_the_gate():
    [template] = templates(_native(_sequence_code("g", r1=50.0)), length_unit="kft")["g"]
    assert template.unit == "kft" and template.note.startswith("units given: kft")


def test_lines_with_and_without_units_on_one_code_raise():
    lines = [schema.Line(name="a", bus1="x", linecode="g", units="kft"), schema.Line(name="b", bus1="x", linecode="G")]
    with pytest.raises(ValueError, match="its lines give units on some lines only"):
        templates(_native(_sequence_code("g"), lines=lines))


@pytest.mark.parametrize("frequency", [60.0, 50.0])
def test_a_code_with_c_and_no_basefreq_takes_the_decks(frequency):
    code = _sequence_code("c", units="km", C1="10", C0="5")
    [table, _] = map_linecode(_native(code), base_frequency=frequency).statements
    columns = [column.name for column in table.columns]
    row = table.rows[0]
    assert row.cells[columns.index("calculatedFrequency")] == repr(frequency)
    assert row.comment == f"defaulted: baseFreq={frequency!r}"
    assert float(row.cells[columns.index("bch")]) == pytest.approx(b_from_c(10, frequency))


def test_a_code_with_no_c_needs_no_frequency():
    [table, _] = _map(_native(_sequence_code("n", units="km"))).statements
    assert table.rows[0].comment is None


def test_short_sequence_matches_golden():
    assert_matches_golden(_map(DssReader(ATOMS / "short_sequence.dss").read_all()), ATOMS / "short_sequence.cimtbl")


def test_short_sequence_matrices_match_the_engine():
    """The engine's line matrices (per km, the lines' unit) equal the derived PhaseImpedanceData."""
    network = cimtbl_to_cim(atom_documents(_map(DssReader(ATOMS / "short_sequence.dss").read_all())))
    data = {}
    for d in network.graph[network.cim.PhaseImpedanceData].values():
        data.setdefault(d.PhaseImpedance.name.lower(), {})[(d.row, d.column)] = d
    dss.Text.Command("Clear")
    dss.Text.Command(f"Redirect [{(ATOMS / 'short_sequence.dss').resolve()}]")
    for line, code in (("one", "oh-1x_4cu_4cun"), ("two", "oh-2x_4cu_4cun")):
        dss.Lines.Name(line)
        order = dss.Lines.Phases()
        r, x, c = dss.Lines.RMatrix(), dss.Lines.XMatrix(), dss.Lines.CMatrix()
        for (row, column), d in data[code].items():
            k = (row - 1) * order + column - 1
            assert float(d.r.to("ohm/km")) == pytest.approx(r[k], rel=1e-9)
            assert float(d.x.to("ohm/km")) == pytest.approx(x[k], rel=1e-9)
            assert float(d.b.to("nS/km")) == pytest.approx(b_from_c(c[k], 60.0), rel=1e-9)
