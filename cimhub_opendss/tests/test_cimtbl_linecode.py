"""Atom tests: OpenDSS LineCode -> linecode.cimtbl -> cim18v17 (rewrite plan Phase 1 exit slice)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimhub_opendss.importer.cimtbl.linecode import (FIELDS, NATIVE_CLASS, b_from_c, lower_triangle, map_linecode,
                                                    susceptance)
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
    return map_linecode(DssReader(ATOMS / "mtx601.dss").read_all())


@pytest.fixture(scope="module")
def sequence():
    return map_linecode(DssReader(ATOMS / "seq_3_1_0c.dss").read_all())


def _native(*codes):
    return type("Native", (), {"list_by_class": staticmethod(lambda cls: list(codes))})()


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
    [table, _] = map_linecode(_native(code)).statements
    assert table.rows[0].cells[:2] == ["lc_mtx601", "MTX601"]


def test_unmapped_units_fail_fast():
    code = schema.Linecode(name="x", nphases=1, units="none", rmatrix=[0.1], xmatrix=[0.2])
    with pytest.raises(ValueError, match="x: units='none' has no mapping"):
        map_linecode(_native(code))


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
    [table] = map_linecode(_native(code)).statements
    assert [(column.name, column.unit) for column in table.columns][-2:] == [("bch", "uS/mi"), ("b0ch", "nS/mi")]
    assert table.rows[0].cells[-2:] == ["5.1", "0.0"]


def test_sequence_codes_group_by_header():
    with_c = schema.Linecode(name="c", nphases=3, units="km", r1=0.1, C1="10", baseFreq="60")
    with_b = schema.Linecode(name="b", nphases=3, units="km", r1=0.1, B1="3.7")
    other_unit = schema.Linecode(name="m", nphases=3, units="mi", r1=0.1, C1="10", baseFreq="60")
    tables = map_linecode(_native(with_c, with_b, other_unit, with_c)).statements
    assert [len(table.rows) for table in tables] == [2, 1, 1]


@pytest.mark.parametrize(("code", "message"), [
    (schema.Linecode(name="seq1", nphases=1, units="km", r1=0.1, x1=0.3), "seq1: nphases=1 sequence codes"),
    (schema.Linecode(name="cb", nphases=3, units="km", C1="10", B1="3.7"), "cb: sets both C1 and B1"),
    (schema.Linecode(name="both", nphases=1, units="ft", r1=0.1, rmatrix=[0.1], xmatrix=[0.2]),
     "both: sets both matrix and sequence"),
    (schema.Linecode(name="bare", nphases=3, units="ft"), "bare: sets no impedance"),
])
def test_ambiguous_or_unmapped_codes_fail_fast(code, message):
    with pytest.raises(ValueError, match=message):
        map_linecode(_native(code))
