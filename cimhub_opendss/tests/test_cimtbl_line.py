"""Atom tests: OpenDSS Line (+ Fuse, Recloser, SwtControl) -> line.cimtbl -> cim18v17, with the engine as the oracle
for ratings, length, z and b, and switch states."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl.line import CONTROLS, FIELDS, NATIVE_CLASS, map_line

from conftest import ENGINE_DECKS, compile_deck, deck

ATOMS = Path(__file__).parent / "atoms" / "line"
CASES = ["codes", "geometry"]
CIRCUIT = "Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=200000 MVAsc1=210000\n"


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _map(native):
    site = dss_to_cimtbl.site(native)
    return map_line(native, site.buses, site.feeder, base_frequency=site.base_frequency)


def _read(tmp_path, text: str):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    return DssReader(path).read_all()


@pytest.mark.parametrize("native_class, fields", [(NATIVE_CLASS, FIELDS), *CONTROLS])
def test_classification_is_complete(native_class, fields):
    check_fields(fields, native_class)


@pytest.mark.parametrize("case", CASES)
def test_matches_golden(case):
    assert_matches_golden(_map(DssReader(ATOMS / f"{case}.dss").read_all()), ATOMS / f"{case}.cimtbl")


def test_codes_bind():
    network = dss_to_cim(DssReader(ATOMS / "codes.dss").read_all(), name="atom")
    cim = network.cim
    switches = {sw.name: sw for cls in (cim.Fuse, cim.Recloser, cim.LoadBreakSwitch)
                for sw in network.graph[cls].values()}
    assert {name: type(sw).__name__ for name, sw in switches.items()} == {
        "fuse1": "Fuse", "rec1": "Recloser", "sw1": "LoadBreakSwitch", "tie": "LoadBreakSwitch",
        "sect": "LoadBreakSwitch"}
    assert float(switches["fuse1"].ratedCurrent.to("A")) == 100
    assert {name for name, sw in switches.items() if sw.open} == {"tie", "sect"}
    l2 = next(seg for seg in network.graph[cim.ACLineSegment].values() if seg.name == "l2")
    limits = {limit.OperationalLimitType.durationKind.value: float(limit.normalValue.to("A"))
              for limit in network.graph[cim.CurrentLimit].values() if limit.OperationalLimitSet.Equipment is l2}
    assert limits == {"normal": 200, "emergency": 345}
    assert l2.PerLengthImpedance.mRID == "lc_mtx603" and float(l2.length.to("ft")) == pytest.approx(500)


def test_geometry_binds():
    network = dss_to_cim(DssReader(ATOMS / "geometry.dss").read_all(), name="atom")
    segments = {seg.name: seg for seg in network.graph[network.cim.ACLineSegment].values()}
    assert segments["g601"].WireConfiguration.mRID == "wc_601"
    assert float(segments["g_m"].length.to("m")) == pytest.approx(100)
    synthesized = segments["s510"].WireConfiguration
    assert synthesized.WireSpacing.mRID == "spc_510" and len(synthesized.WireSequence) == 2


@pytest.mark.parametrize("text, message", [
    ("New Line.a bus1=sourcebus.1.2 bus2=b.2.1 phases=2 r1=0.1 x1=0.2\n", "transposition"),
    ("New Linecode.c nphases=3 r1=0.1 x1=0.2 units=km\nNew Line.a bus1=sourcebus bus2=b linecode=c r1=0.2\n",
     "linecode and inline"),
    ("New Linecode.c nphases=3 r1=0.1 x1=0.2 units=km\nNew Line.a bus1=sourcebus.1 bus2=b.1 linecode=c phases=1\n",
     "DSS-10"),
    ("New Line.a bus1=sourcebus bus2=b r1=0.1 x1=0.2\nNew Fuse.f MonitoredObj=Line.a\n", "not Switch=y"),
    ("New Line.a bus1=sourcebus bus2=b r1=0.1 x1=0.2\nOpen Line.a\n", "not Switch=y"),
    ("New Line.a bus1=sourcebus bus2=b switch=y\nNew Fuse.f MonitoredObj=Line.a\nNew Recloser.r MonitoredObj=Line.a\n",
     "a Fuse and a Recloser"),
    ("New Line.a bus1=sourcebus bus2=b switch=y\nNew SwtControl.s SwitchedObj=Line.a State=closed\nOpen Line.a\n",
     "State is closed"),
    ("New Line.a bus1=sourcebus bus2=b switch=y\nNew SwtControl.s SwitchedObj=Line.a State=open\n"
     "New SwtControl.t SwitchedObj=Line.a State=closed\n", "disagree on State"),
    ("New Line.a bus1=sourcebus bus2=b r1=0.1 x1=0.2 Rg=0.01\n", "Rg not mapped"),
    ("New Line.a bus1=sourcebus bus2=b r1=0.1 x1=0.2 Seasons=2 Ratings=[400 300]\n", "Seasons, Ratings not mapped"),
    ("New Line.a bus1=sourcebus bus2=b switch=y\nNew Fuse.f MonitoredObj=Transformer.t\n", "only a Line"),
])
def test_unmapped_lines_fail_fast(tmp_path, text, message):
    with pytest.raises(ValueError, match=message):
        _map(_read(tmp_path, text))


def _matrix(segment) -> tuple[dict[str, list[list[float]]], float | None] | None:
    """The segment's r, x (ohm/m) and b (nS/m) as full matrices, and the template's frequency; ``None`` by
    geometry."""
    template = segment.PerLengthImpedance
    if template is None:
        return None
    frequency = float(template.calculatedFrequency.to("Hz")) if template.calculatedFrequency is not None else None
    if type(template).__name__ == "PerLengthSequenceImpedance":
        values = {"r": (template.r, template.r0, "ohm/m"), "x": (template.x, template.x0, "ohm/m"),
                  "b": (template.bch, template.b0ch, "nS/m")}
        matrices = {}
        for name, (positive, zero, unit) in values.items():
            positive = float(positive.to(unit)) if positive is not None else 0.0
            zero = float(zero.to(unit)) if zero is not None else 0.0
            self_value, mutual = (2 * positive + zero) / 3, (zero - positive) / 3
            matrices[name] = [[self_value if i == j else mutual for j in range(3)] for i in range(3)]
        return matrices, frequency
    order = template.conductorCount
    matrices = {name: [[0.0] * order for _ in range(order)] for name in "rxb"}
    for data in template.PhaseImpedanceData:
        for name, unit in (("r", "ohm/m"), ("x", "ohm/m"), ("b", "nS/m")):
            value = getattr(data, name)
            value = float(value.to(unit)) if value is not None else 0.0
            matrices[name][data.row - 1][data.column - 1] = matrices[name][data.column - 1][data.row - 1] = value
    return matrices, frequency


def _engine_line_differences(network) -> list[str]:
    """Every difference between the mapped lines and the engine's (the deck compiled and solved): ratings
    (DSS's 400/600 A where nothing is mapped), z and b totals by code or inline values, and switch states."""
    cim = network.cim
    dss.Solution.Solve()
    limits = {(limit.OperationalLimitSet.Equipment.mRID, limit.OperationalLimitType.mRID): float(limit.normalValue.to("A"))
              for limit in network.graph.get(cim.CurrentLimit, {}).values()}
    differences = []
    for segment in network.graph[cim.ACLineSegment].values():
        dss.Lines.Name(segment.name)
        for limit_type, engine, default in (("olt_normal", dss.Lines.NormAmps(), 400.0),
                                            ("olt_emergency", dss.Lines.EmergAmps(), 600.0)):
            if not math.isclose(limits.get((segment.mRID, limit_type), default), engine, rel_tol=1e-9):
                differences.append(f"{segment.name} {limit_type}: {limits.get((segment.mRID, limit_type))} vs {engine}")
        mapped = _matrix(segment)
        if mapped is None:
            continue
        matrices, frequency = mapped
        length, engine_length, order = float(segment.length.to("m")), dss.Lines.Length(), dss.Lines.Phases()
        engine = {"r": dss.Lines.RMatrix(), "x": dss.Lines.XMatrix(), "b": dss.Lines.CMatrix()}
        scale = {"r": 1.0, "x": 1.0, "b": 2 * math.pi * (frequency or dss.Solution.Frequency())}
        for name in "rxb":
            for i in range(order):
                for j in range(order):
                    ours, theirs = matrices[name][i][j] * length, engine[name][i * order + j] * engine_length * scale[name]
                    if not math.isclose(ours, theirs, rel_tol=1e-6, abs_tol=1e-9):
                        differences.append(f"{segment.name} {name}{i + 1}{j + 1}: {ours:.6g} vs {theirs:.6g}")
    for cls in (cim.LoadBreakSwitch, cim.Fuse, cim.Recloser):
        for switch in network.graph.get(cls, {}).values():
            dss.Circuit.SetActiveElement(f"Line.{switch.name}")
            if bool(switch.open) != (dss.CktElement.IsOpen(1, 0) or dss.CktElement.IsOpen(2, 0)):
                differences.append(f"{switch.name} open: {switch.open}")
    return differences


@pytest.mark.parametrize("case", CASES)
def test_atoms_match_the_engine(case):
    network = dss_to_cim(DssReader(ATOMS / f"{case}.dss").read_all(), name="atom")
    compile_deck(ATOMS / f"{case}.dss")
    assert _engine_line_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_lines_match_the_engine(relative):
    path = deck(relative)
    native = DssReader(path).read_all()
    try:
        network = dss_to_cim(native, name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: line phases differ from the code's (DSS-10, deferred)")
        raise
    compile_deck(path)
    assert _engine_line_differences(network) == []
