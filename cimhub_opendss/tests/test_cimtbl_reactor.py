"""Atom tests: OpenDSS series Reactor -> reactor.cimtbl -> cim18v17, with the engine as the oracle for R, X, the
buses and the ratings."""

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
from cimhub_opendss.importer.cimtbl import reactor
from cimhub_opendss.importer.cimtbl.transformer import parse_bus

from conftest import ENGINE_DECKS, compile_deck, deck
from test_dss_to_cimtbl import assert_base_voltages_agree

ATOMS = Path(__file__).parent / "atoms" / "reactor"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n")


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def reactors():
    return DssReader(ATOMS / "reactors.dss").read_all()


def test_classification_is_complete():
    check_fields(reactor.FIELDS, reactor.NATIVE_CLASS)


def test_matches_golden(reactors):
    site = dss_to_cimtbl.site(reactors)
    assert_matches_golden(reactor.map_reactor(reactors, site.buses, site.feeder), ATOMS / "reactors.cimtbl")


def test_reactors_bind(reactors):
    network = dss_to_cim(reactors, name="atom")
    assert_base_voltages_agree(network)
    compensators = {item.name: item for item in network.graph[network.cim.SeriesCompensator].values()}
    hsb = compensators["HVMV_Sub_HSB"]
    assert [terminal.phases.value for terminal in hsb.Terminals] == ["ABC", "ABC"]
    assert float(hsb.x0.to("ohm")) == pytest.approx(14.798306633595042)
    limits = {limit.mRID: float(limit.normalValue.to("A")) for limit_set in hsb.OperationalLimitSet
              for limit in limit_set.OperationalLimitValue}
    assert limits == {"rx_hvmv_sub_hsb_norm": 400, "rx_hvmv_sub_hsb_emerg": 400}
    assert [terminal.phases.value for terminal in compensators["r1"].Terminals] == ["B", "B"]


@pytest.mark.parametrize("text, message", [
    ("New Reactor.x bus1=b1 X=5\n", "a shunt or neutral reactor"),
    ("New Reactor.x bus1=b1.4 bus2=b1.0 phases=1 X=0.5\n", "a shunt or neutral reactor"),
    ("New Reactor.x bus1=b1 bus2=b2 kvar=100 kv=4.16\n", "kvar not mapped"),
    ("New Reactor.x bus1=b1 bus2=b2 R=1\n", "X is unset"),
    ("New Reactor.x bus1=b1 bus2=b2 X=1 Parallel=yes\n", "Parallel not mapped"),
])
def test_unmapped_reactors_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=message):
        reactor.map_reactor(native, site.buses, site.feeder)


def _engine_differences(network) -> list[str]:
    differences = []

    def check(label: str, ours: float, theirs: float) -> None:
        if not math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-9):
            differences.append(f"{label}: {ours} vs {theirs}")

    for compensator in network.graph.get(network.cim.SeriesCompensator, {}).values():
        name = compensator.name
        dss.Reactors.Name(name)
        check(f"{name} R", float(compensator.r.to("ohm")), dss.Reactors.R())
        check(f"{name} X", float(compensator.x.to("ohm")), dss.Reactors.X())
        ours = [terminal.ConnectivityNode.mRID for terminal in compensator.Terminals]
        theirs = [parse_bus(dss.Reactors.Bus1())[0], parse_bus(dss.Reactors.Bus2())[0]]
        if ours != theirs:
            differences.append(f"{name} buses: {ours} vs {theirs}")
        dss.Circuit.SetActiveElement(f"Reactor.{name}")
        limits = {limit.mRID.rsplit("_", 1)[1]: float(limit.normalValue.to("A"))
                  for limit_set in compensator.OperationalLimitSet for limit in limit_set.OperationalLimitValue}
        for suffix, engine in (("norm", dss.CktElement.NormalAmps()), ("emerg", dss.CktElement.EmergAmps())):
            if suffix in limits:
                check(f"{name} {suffix}amps", limits[suffix], engine)
    return differences


def test_atom_matches_the_engine(reactors):
    network = dss_to_cim(reactors, name="atom")
    compile_deck(ATOMS / "reactors.dss")
    assert _engine_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_reactors_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the reactors ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_differences(network) == []
