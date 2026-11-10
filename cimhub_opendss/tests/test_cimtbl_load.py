"""Atom tests: OpenDSS Load -> load.cimtbl -> cim18v17, with the engine as the oracle for p, q and the model."""

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
from cimhub_opendss.importer.cimtbl import load

from conftest import ENGINE_DECKS, compile_deck, deck
from test_dss_to_cimtbl import assert_base_voltages_agree

ATOMS = Path(__file__).parent / "atoms" / "load"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n"
           "New XfmrCode.ct phases=1 windings=3 kVs=[2.4 0.12 0.12] kVAs=[25 25 25]\n"
           "New Transformer.ct XfmrCode=ct buses=[b1.2 house.1.0 house.0.2]\n")
#: The engine's model code of each LoadResponse.
ENGINE_MODEL = {"zip_constant_pq": 1, "zip_constant_z": 2, "zip_constant_i": 5}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def loads():
    return DssReader(ATOMS / "loads.dss").read_all()


def test_classification_is_complete():
    check_fields(load.FIELDS, load.NATIVE_CLASS)


def test_matches_golden(loads):
    site = dss_to_cimtbl.site(loads)
    assert_matches_golden(load.map_load(loads, site.buses, site.feeder), ATOMS / "loads.cimtbl")


def test_derived_power():
    assert load.reactive_power(10, 0.9) == pytest.approx(4.8432210)
    assert load.reactive_power(10, -0.9) == pytest.approx(-4.8432210)
    assert load.reactive_power(10, 1.0) == 0
    assert load.power_from_kva(313, 0.9) == pytest.approx((281.7, 136.4335), rel=1e-6)
    assert load.exponential_mrid(0.8, 3.0) == "exp_0.8_3"


def test_loads_bind(loads):
    network = dss_to_cim(loads, name="atom")
    assert_base_voltages_agree(network)
    by_name = {consumer.name: consumer for consumer in network.graph[network.cim.EnergyConsumer].values()}
    assert len(by_name) == 9
    house = by_name["house"]
    assert house.Terminals[0].phases.value == "s12" and house.phaseConnection.value == "Y"
    assert house.BaseVoltage is house.Terminals[0].ConnectivityNode.BaseVoltage
    assert by_name["leg2"].Terminals[0].phases.value == "s2" and by_name["leg2"].customerCount == 3
    response = by_name["cvr1"].LoadResponse
    assert response.exponentModel and response.pVoltageExponent == 0.8 and response.qVoltageExponent == 3
    assert by_name["ca"].LoadResponse.mRID == "zip_constant_i" and by_name["ca"].Terminals[0].phases.value == "AC"
    assert by_name["off"].normallyInService is False


@pytest.mark.parametrize("text, message", [
    ("New Load.x bus1=b1.1 phases=1 kV=4.16 kW=10\n", "phase voltage is 2.40178"),
    ("New Load.x bus1=b1 kW=10 kVA=20\n", "kW with kVA"),
    ("New Load.x bus1=b1 kW=10 xfkVA=20\n", "xfkVA/allocationfactor not mapped"),
    ("New Load.x bus1=b1 kV=4.16 kW=10 model=3\n", "model ConstantPQuadQ is not mapped"),
    ("New Load.x bus1=b1 kV=4.16 kW=10 Rneut=5\n", "Rneut"),
    ("New Load.x bus1=b1.1.4 phases=1 kV=2.4 kW=10\n", "wye neutral on node 4"),
    ("New Load.x bus1=house phases=3 kV=0.208 kW=10\n", "3-phase device on split-phase bus house"),
    ("New Load.x bus1=nowhere kW=10\n", "the topology walk did not reach it"),
])
def test_unmapped_loads_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=message):
        load.map_load(native, site.buses, site.feeder)


def _engine_load_differences(network) -> list[str]:
    differences = []
    for consumer in network.graph.get(network.cim.EnergyConsumer, {}).values():
        dss.Loads.Name(consumer.name)
        response = consumer.LoadResponse
        ours = {"kW": float(consumer.p.to("kW")), "kvar": float(consumer.q.to("kVAr")),
                "model": 4 if response.exponentModel else ENGINE_MODEL[response.mRID],
                "NumCust": consumer.customerCount, "delta": consumer.phaseConnection.value == "D"}
        theirs = {"kW": dss.Loads.kW(), "kvar": dss.Loads.kvar(), "model": dss.Loads.Model(),
                  "NumCust": dss.Loads.NumCust(), "delta": dss.Loads.IsDelta()}
        if response.exponentModel:
            ours |= {"CVRwatts": response.pVoltageExponent, "CVRvars": response.qVoltageExponent}
            theirs |= {"CVRwatts": dss.Loads.CVRwatts(), "CVRvars": dss.Loads.CVRvars()}
        for key, value in ours.items():
            if not math.isclose(value, theirs[key], rel_tol=1e-9, abs_tol=1e-9):
                differences.append(f"{consumer.name} {key}: {value} vs {theirs[key]}")
    return differences


def test_atom_matches_the_engine(loads):
    network = dss_to_cim(loads, name="atom")
    compile_deck(ATOMS / "loads.dss")
    assert _engine_load_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_loads_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the loads ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_load_differences(network) == []
