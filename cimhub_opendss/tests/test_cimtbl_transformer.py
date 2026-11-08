"""Atom tests: OpenDSS Transformer (inline) -> transformer.cimtbl -> cim18v17."""

from __future__ import annotations

import math
from pathlib import Path

import cimtables
import pytest

from cimhub_core.cimtbl import check_fields, cimtbl_to_cim
from cimhub_core.cimtbl_testing import assert_matches_golden, atom_documents, cim_scope
from cimtopology.core import BusSystem, System
from cimhub_opendss.importer.cimtbl.transformer import (FIELDS, NATIVE_CLASS, map_transformer, parse_bus,
                                                       winding_nodes)
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.schema import opendss_schema as schema

ATOMS = Path(__file__).parent / "atoms" / "transformer"
CASES = ["xfm1", "sub3", "reg1", "service", "center_tap"]

#: What the topology walk would give for every atom bus.
THREE, SINGLE, SPLIT = System.THREE_PHASE, System.SINGLE_PHASE, System.SPLIT_PHASE
BUSES = {
    "xf1": BusSystem(4.16, THREE), "634": BusSystem(0.48, THREE),
    "sourcebus": BusSystem(115.0, THREE), "650": BusSystem(4.16, THREE), "650z": BusSystem(13.2, THREE),
    "brkr": BusSystem(4.16, THREE), "rg60": BusSystem(4.16, THREE),
    "b13552": BusSystem(12.47, THREE), "x_b13552-a": BusSystem(0.24, SINGLE),
    "n1": BusSystem(4.16, THREE), "house": BusSystem(0.24, SPLIT),
}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _map(case: str):
    return map_transformer(DssReader(ATOMS / f"{case}.dss").read_all(), BUSES, "fdr_atom")


def _bind(case: str):
    return cimtbl_to_cim(atom_documents(_map(case)), network=cimtables.load_model(ATOMS / "prereq.cimtbl"))


def _native(*transformers):
    return type("Native", (), {"list_by_class": staticmethod(lambda cls: list(transformers))})()


def _by_mrid(network, class_name: str) -> dict:
    return {obj.mRID: obj for obj in network.graph[getattr(network.cim, class_name)].values()}


def test_classification_is_complete():
    check_fields(FIELDS, NATIVE_CLASS)


def test_parse_bus_and_default_nodes():
    assert parse_bus("650.1.2.3.4") == ("650", (1, 2, 3, 4))
    assert parse_bus("XF1") == ("xf1", ())
    assert winding_nodes((), 3, True, name="t") == (1, 2, 3, 0)
    assert winding_nodes((), 3, False, name="t") == (1, 2, 3)
    assert winding_nodes((1,), 1, True, name="t") == (1, 0)
    assert winding_nodes((0, 2), 1, True, name="t") == (0, 2)


@pytest.mark.parametrize("case", CASES)
def test_matches_golden(case):
    assert_matches_golden(_map(case), ATOMS / f"{case}.cimtbl")


def test_three_phase_by_balanced_ends():
    network = _bind("xfm1")
    ends = _by_mrid(network, "PowerTransformerEnd")
    # %R on the end's own rating: 0.55 % x 4.16 kV^2 / 500 kVA
    assert float(ends["xf_xfm1_1"].r.to("ohm")) == pytest.approx(0.0055 * 4160**2 / 500e3)
    assert str(ends["xf_xfm1_2"].Terminal.phases) == "PhaseCode.ABCN"
    [mesh] = _by_mrid(network, "TransformerMeshImpedance").values()
    assert float(mesh.x.to("ohm")) == pytest.approx(0.02 * 4160**2 / 500e3)


def test_neutral_impedance_on_its_winding():
    ends = _by_mrid(_bind("sub3"), "PowerTransformerEnd")
    assert ends["xf_sub3_1"].connectionKind.name == "D" and str(ends["xf_sub3_1"].Terminal.phases) == "PhaseCode.ABC"
    assert float(ends["xf_sub3_2"].xground.to("ohm")) == pytest.approx(0.4)
    assert ends["xf_sub3_3"].xground is None and ends["xf_sub3_3"].grounded


def test_regulator_coil_on_a_three_phase_system():
    coils = _by_mrid(_bind("reg1"), "TransformerWinding")
    # phase-to-neutral coil on a 3-phase system: ratedU = 2.4 x sqrt(3); %R = %LoadLoss / 2
    assert float(coils["xf_reg1_wdg_2"].ratedU.to("kV")) == pytest.approx(2.4 * math.sqrt(3))
    assert float(coils["xf_reg1_wdg_2"].baseU.to("kV")) == pytest.approx(2.4)
    assert float(coils["xf_reg1_wdg_1"].r.to("ohm")) == pytest.approx(0.00005 * 2400**2 / 1666e3)


def test_service_secondary_is_a_single_phase_system():
    network = _bind("service")
    coils = _by_mrid(network, "TransformerWinding")
    assert float(coils["xf_b13552-1a_wdg_1"].ratedU.to("kV")) == pytest.approx(7.2 * math.sqrt(3))
    assert float(coils["xf_b13552-1a_wdg_2"].ratedU.to("kV")) == pytest.approx(0.24)
    ends = _by_mrid(network, "PowerTransformerEnd")
    assert ends["xf_b13552-1a_2"].BaseVoltage.mRID == "bv_240v"
    [tank] = _by_mrid(network, "TransformerTank").values()
    assert float(tank.noLoadLoss.to("kW")) == pytest.approx(0.2423 / 100 * 40)


def test_center_tap_by_phase_ends():
    network = _bind("center_tap")
    phase_ends = _by_mrid(network, "TransformerPhaseEnd")
    assert [(e.endNumber, e.sequenceNumber, e.phase.name) for e in sorted(phase_ends.values(),
                                                                         key=lambda e: e.sequenceNumber)] == [
        (1, 1, "A"), (1, 2, "B"), (2, 3, "s1"), (2, 4, "s2"), (2, 5, "N")]
    coils = _by_mrid(network, "TransformerWinding")
    half = coils["xf_ct_ab_wdg_3"]
    assert (half.FromTransformerEnd.mRID, half.ToTransformerEnd.mRID) == ("xf_ct_ab_2_N", "xf_ct_ab_2_s2")
    assert float(half.ratedU.to("kV")) == pytest.approx(0.24) and float(half.baseU.to("kV")) == pytest.approx(0.12)
    assert float(half.ratedS.to("kVA")) == pytest.approx(2.5) and float(half.baseS.to("kVA")) == pytest.approx(5)
    ends = _by_mrid(network, "PowerTransformerEnd")
    assert str(ends["xf_ct_ab_2"].Terminal.phases) == "PhaseCode.s12N" and ends["xf_ct_ab_2"].connectionKind.name == "I"
    mesh = _by_mrid(network, "TransformerMeshImpedance")["xf_ct_ab_mesh_23"]
    assert float(mesh.x.to("ohm")) == pytest.approx(0.0136 * 120**2 / 5e3)


def test_defaults_are_listed():
    [table, *_] = _map("reg1").statements
    assert table.rows[0].comment == "defaulted: conns=wye"


def _xf(**slots):
    base = dict(name="t", phases=1, buses=["a.1", "b.1"], kVs=[7.2, 0.24], kVAs=[25, 25])
    return schema.Transformer(**{**base, **slots})


@pytest.mark.parametrize(("slots", "message"), [
    (dict(XfmrCode="ct5"), "t: XfmrCode=ct5 instances wait for the lug template"),
    (dict(phases=2), "t: phases=2; only 1 and 3 are mapped"),
    (dict(kV=7.2), "t: kV is set without wdg= or an array"),
    (dict(taps=[1.0, 1.05]), r"t: taps=\[1.0, 1.05\] need a RatioTapChanger"),
    (dict(kVAs=[25, 50]), r"t: kVAs=\[25.0, 50.0\]; each coil's %R"),
    (dict(pct_Rs=[0.5, 0.5], pct_loadloss=2.0), "t: pct_Rs=.* and pct_loadloss=2.0 disagree"),
    (dict(XHL=2.0, X12=3.0), r"t: XHL and X12 disagree \(\[2.0, 3.0\]\)"),
    (dict(buses=["a.1", "c.1"]), r"t: no bus voltage for \['c'\]"),
    (dict(buses=["a.1", "a.2"]), r"t: windings \[1, 2\] share bus a but are not a split-phase secondary"),
    (dict(windings=3, buses=["a.1", "b.1", "b.1"], kVs=[7.2, 0.12, 0.12], kVAs=[25, 25, 25]),
     r"t: windings \[2, 3\] share bus b but are not a split-phase secondary"),
    (dict(phases=3, buses=["a.2.3.1", "b"], kVs=[12.47, 0.48]), r"t: bus a phase nodes \(2, 3, 1\)"),
])
def test_unmapped_transformers_fail_fast(slots, message):
    with pytest.raises(ValueError, match=message):
        map_transformer(_native(_xf(**slots)), {"a": BUSES["b13552"], "b": BUSES["x_b13552-a"]}, "fdr_atom")
