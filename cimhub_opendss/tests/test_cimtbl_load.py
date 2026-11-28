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
    assert load.reactive_power("l", 10, 0.9) == pytest.approx(4.8432210)
    assert load.reactive_power("l", 10, -0.9) == pytest.approx(-4.8432210)
    assert load.reactive_power("l", -10, 0.9) == pytest.approx(-4.8432210)
    assert load.reactive_power("l", 10, 1.0) == 0
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
    ("New Load.x bus1=b1 kW=10 xfkVA=20\n", "xfkVA/allocationfactor not mapped"),
    ("New Load.x bus1=b1 kV=4.16 kW=10 model=3\n", "model ConstantPQuadQ is not mapped"),
    ("New Load.x bus1=b1 kV=4.16 kW=10 Rneut=5\n", "Rneut"),
    ("New Load.x bus1=b1.1.4 phases=1 kV=2.4 kW=10\n", "wye neutral on node 4"),
    ("New Load.x bus1=house phases=3 kV=0.208 kW=10\n", "3-phase device on split-phase bus house"),
    ("New Load.x bus1=nowhere kW=10\n", "the topology walk did not reach it"),
    ("New Load.x bus1=b1 kV=4.16 kVA=100 pf=0\n", "Load x: power factor 0"),  # the engine gives kvar NaN
    ("New Load.x bus1=b1 kV=4.16 kW=100 pf=1.2\n", "Load x: power factor 1.2"),  # the engine gives kvar NaN
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


def test_reactive_power_takes_the_sign_of_kw(tmp_path):
    """kvar = kW x tan(acos |pf|) x sign(pf), so a negative kW flips kvar (engine-checked)."""
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + "New Load.neg bus1=b1 kV=4.16 kW=-50 pf=0.9\n"
                    "New Load.negneg bus1=b1 kV=4.16 kW=-50 pf=-0.9\n")
    network = dss_to_cim(DssReader(path).read_all(), name="atom")
    compile_deck(path)
    assert _engine_load_differences(network) == []


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


@pytest.mark.parametrize("commands", [
    "New Load.x bus1=b1 kV=4.16 kVA=100 kW=50\n",  # engine: kW 50, kvar 26.9871 (kW last: kW with pf 0.88)
    "New Load.x bus1=b1 kV=4.16 kW=50 kVA=100\n",  # engine: kW 88, kvar 47.4974 (kVA last: kVA with pf 0.88)
    "New Load.x bus1=b1 kV=4.16 kVA=100 kW=50 kvar=30\n",  # engine: kW 50, kvar 30 (kvar last: kW with kvar)
    "New Load.x bus1=b1 kV=4.16 kVA=100 kvar=30 kW=50 pf=0.9\n",  # engine: kW 50, kvar 24.2161
    "New Load.x bus1=b1 kV=4.16 kvar=30 kVA=100 pf=0.9\n",  # engine: kW 90, kvar 43.589
    "New Load.x bus1=b1 kV=4.16 kW=50 kvar=30\nEdit Load.x pf=0.9\n",  # engine: kW 50, kvar 30 (pf keeps the pair)
    "New Load.x bus1=b1 kV=4.16 kVA=100\nEdit Load.x kW=50\n",  # engine: kW 50, kvar 26.9871
])
def test_last_of_kw_kvar_kva_picks_the_pair(tmp_path, commands):
    """The engine keeps a load spec type: the last of kW, kvar and kVA picks the pair it computes from, (kW, pf),
    (kW, kvar) or (kVA, pf), and pf never changes it (opendssdirect 0.9.4: ``kW=50 kvar=30 pf=0.9`` keeps kvar 30,
    ``kW=50 kVA=100`` gives kW 88 at pf 0.88, ``kVA=100 kW=50`` gives kW 50 and kvar 26.9871). EPRI's source agrees:
    Load.pas:634-637 (kW sets LoadSpecType 0), :638 (pf sets only PFChanged), :666-670 (kvar sets 1), :672 (kVA
    sets 2), and RecalcElementData (:1138-1160) computes from that pair."""
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + commands)
    network = dss_to_cim(DssReader(path).read_all(), name="atom")
    compile_deck(path)
    assert _engine_load_differences(network) == []


_LOAD = "New Load.x bus1=b1 kV=4.16 "


@pytest.mark.parametrize("commands", [
    _LOAD + "kVA=100 kvar=30\n",  # engine: kW 10 (the default), kvar 30
    _LOAD + "kVA=100\nEdit Load.x kvar=30\n",  # engine: kW 88 (kVA x pf, recomputed at the first command's end)
    _LOAD + "kW=50 kVA=100 kvar=30\n",  # engine: kW 50, kvar 30
    _LOAD + "kW=50 kVA=100\nEdit Load.x kvar=30\n",  # engine: kW 88, kvar 30
    _LOAD + "kvar=30 kVA=100\n",  # engine: kW 88, kvar 47.4974 (pf 0.88)
    _LOAD + "kvar=30\nEdit Load.x kVA=100\n",  # engine: kW 31.6228, kvar 94.8683 (the pf kvar implied)
    _LOAD + "kW=50 kvar=30 kW=100\n",  # engine: kvar 53.9743 (pf 0.88)
    _LOAD + "kW=50 kvar=30\nEdit Load.x kW=100\n",  # engine: kvar 60 (the pf kvar implied)
    _LOAD + "kW=-50 kvar=30\nEdit Load.x kW=100\n",  # engine: kvar 60 (pf takes the sign of kW x kvar)
    _LOAD + "kW=50 kvar=30\n~ kW=100\n",  # engine: kvar 60 (a ~ line is a command of its own)
    _LOAD + "kVA=100 kvar=30\nEdit Load.x pf=0.9\nEdit Load.x kW=50\n",  # engine: kvar 150 (pf 0.9 overwritten)
])
def test_each_command_recomputes_from_the_pair(tmp_path, commands):
    """The engine recomputes kW, kvar, pf and kVA from the pair once, at the end of each command (Load.pas:681
    calls RecalcElementData; :1138-1160 overwrite kW in spec 2 and pf in spec 1), so a later pair that reads one of
    them depends on where the commands end. The mapper replays the history command by command (opendssdirect
    0.9.4, values in the cases)."""
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + commands)
    network = dss_to_cim(DssReader(path).read_all(), name="atom")
    compile_deck(path)
    assert _engine_load_differences(network) == []


def test_load_power_replays_each_command():
    """The replay on its own, with values the engine gives (cases above): kVA=100 kvar=30 is 10 kW in one command
    and 88 kW across two."""
    defaults = {"kW": 10.0, "pf": 0.88}
    assert load.load_power("l", [[("kVA", 313.0), ("pf", 0.9)]], defaults) == pytest.approx((281.7, 136.4335))
    assert load.load_power("l", [[("kVA", 100.0), ("kvar", 30.0)]], defaults) == (10.0, 30.0)
    assert load.load_power("l", [[("kVA", 100.0)], [("kvar", 30.0)]], defaults) == pytest.approx((88.0, 30.0))
    assert load.load_power("l", [[("kW", 50.0), ("kvar", 30.0)], [("kW", 100.0)]], defaults) == pytest.approx(
        (100.0, 60.0))
