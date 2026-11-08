"""The topology walk on DSS models: the ``Network`` builder, and bus voltages against the engine (DSS-1)."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimtopology.core import BusSystem, Connection, System, walk
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer.topology import dss_network
from cimhub_opendss.schema import opendss_schema as schema

from conftest import ENGINE_DECKS, deck

FEEDER = Path(__file__).parent / "atoms" / "topology" / "feeder.dss"
THREE, SINGLE, SPLIT = System.THREE_PHASE, System.SINGLE_PHASE, System.SPLIT_PHASE

#: Decks the engine cannot compile here: they only have to walk.
WALK_ONLY_DECKS = ["EPRI/K1/Master.dss", "EPRI/M1/Master.dss"]
#: The engine's kVBase is phase-to-neutral; a split-phase bus's is s1 (or s2) to N.
_LN_PER_SYSTEM_KV = {THREE: 1 / math.sqrt(3), SINGLE: 1.0, SPLIT: 0.5}


def _walk(path: Path) -> dict[str, BusSystem]:
    return walk(dss_network(DssReader(path).read_all()))


def test_feeder_systems():
    buses = _walk(FEEDER)
    assert buses["src"] == BusSystem(69.0, THREE)  # the 66 kV winding is within the nameplate tolerance
    assert buses["f1"] == BusSystem(12.47, THREE)  # 13.09 kV substation secondary, 7.2 kV coils agree on 12.47
    assert buses["f3"] == buses["l1"] == BusSystem(12.47, THREE)  # regulator bank, series reactor, lateral line
    assert buses["l2"] == BusSystem(12.47, THREE)  # one regulator keeps the system
    assert buses["x1"] == BusSystem(0.24, SINGLE)
    assert buses["house"] == BusSystem(0.24, SPLIT)
    assert buses["m1"] == BusSystem(0.48, THREE)


def test_xfmrcode_supplies_the_windings():
    network = dss_network(DssReader(FEEDER).read_all())
    [ct] = [unit for unit in network.transformers if unit.name == "transformer.ct"]
    assert [(coil.bus, coil.kv, coil.connection) for coil in ct.coils] == [
        ("f3", 7.2, Connection.PHASE_NEUTRAL), ("house", 0.12, Connection.HALF), ("house", 0.12, Connection.HALF)]


def test_scalar_kv_without_wdg_raises():
    native = type("Native", (), {"list_by_class": staticmethod(lambda cls: [
        schema.Transformer(name="t", phases=1, buses=["a.1", "b.1"], kV=7.2)] if cls is schema.Transformer else [])})()
    with pytest.raises(ValueError, match="Transformer t: kV is set without wdg= or an array"):
        dss_network(native)


def _against_engine(path: Path) -> tuple[dict, set[str]]:
    """Buses whose voltage differs from the engine's, and buses the engine squashes.

    ``CalcVoltageBases`` snaps every bus to the nearest of the deck's ``voltagebases``, so it can only
    agree where the walk's voltage is one of them; elsewhere (a 240 V 2-wire service on a deck listing
    0.208 and 0.48) the engine squashes, and the bus is listed as such instead.
    """
    buses = _walk(path)
    dss.Text.Command("Clear")
    dss.Text.Command(f"Compile [{path.resolve()}]")
    bases_ln = [kv / math.sqrt(3) for kv in dss.Settings.VoltageBases()]
    differ, squashed = {}, set()
    for name in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(name)
        ours = buses[name.lower()]
        ours_ln = ours.kv * _LN_PER_SYSTEM_KV[ours.system]
        if math.isclose(ours_ln, dss.Bus.kVBase(), rel_tol=0.01):
            continue
        if any(math.isclose(ours_ln, base, rel_tol=0.01) for base in bases_ln):
            differ[name] = (ours, dss.Bus.kVBase())
        else:
            squashed.add(name.lower())
    return differ, squashed


def test_engine_squashes_the_service():
    differ, squashed = _against_engine(FEEDER)
    assert not differ and squashed == {"x1"}  # 0.24 kV is not in voltagebases; the engine gives 0.277 kV LN


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_bus_voltages_match_the_engine(relative):
    differ, _ = _against_engine(deck(relative))
    assert not differ, f"{len(differ)} buses differ, e.g. {list(differ.items())[:3]}"


@pytest.mark.parametrize("relative", WALK_ONLY_DECKS)
def test_deck_walks(relative):
    network = dss_network(DssReader(deck(relative)).read_all())
    buses = walk(network)
    assert {branch.bus1 for branch in network.branches} <= set(buses)
