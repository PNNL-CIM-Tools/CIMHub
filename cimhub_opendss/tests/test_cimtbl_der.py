"""Atom tests: OpenDSS PVSystem + Storage -> pvsystem.cimtbl + storage.cimtbl -> cim18v17, with the engine as the
oracle for the dispatch (a PV's kW and kvar, a battery's kW and state) and the ratings."""

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
from cimhub_opendss.importer.cimtbl import injection, pvsystem, storage

from conftest import ENGINE_DECKS, compile_deck, deck
from test_dss_to_cimtbl import assert_base_voltages_agree

ATOMS = Path(__file__).parent / "atoms" / "der"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n"
           "New Transformer.t phases=3 buses=[b1 b2] kVs=[4.16 0.48] kVAs=[2000 2000] xhl=5\n")
#: The engine's state of each CIM BatteryStateKind.
ENGINE_STATE = {"charging": "charging", "discharging": "discharging", "waiting": "idling"}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def der():
    return DssReader(ATOMS / "der.dss").read_all()


def test_classification_is_complete():
    check_fields(pvsystem.FIELDS, pvsystem.NATIVE_CLASS)
    check_fields(storage.FIELDS, storage.NATIVE_CLASS)


def test_matches_golden(der):
    site = dss_to_cimtbl.site(der)
    assert_matches_golden(pvsystem.map_pvsystem(der, site.buses, site.feeder), ATOMS / "pvsystem.cimtbl")
    assert_matches_golden(storage.map_storage(der, site.buses, site.feeder), ATOMS / "storage.cimtbl")


def test_derived_dispatch():
    power = pvsystem.pv_power("pv", pmpp=10, irradiance=1, pct_pmpp=100, kva=10, pct_cutout=20, pf=0.9, kvar=None)
    assert power == pytest.approx((8.748898, 4.843221, False), rel=1e-6)
    assert pvsystem.pv_power("pv", pmpp=10, irradiance=0.1, pct_pmpp=100, kva=12, pct_cutout=20, pf=1, kvar=None).off
    # %Pmpp caps the panel's power; %Cutout is on the panel's power (both as the engine, probed)
    capped = pvsystem.pv_power("pv", pmpp=100, irradiance=0.5, pct_pmpp=10, kva=100, pct_cutout=20, pf=1, kvar=None)
    assert capped == pytest.approx((10, 0, False))
    assert pvsystem.pv_power("pv", pmpp=100, irradiance=1.2, pct_pmpp=150, kva=200, pct_cutout=20, pf=1,
                             kvar=None).kw == pytest.approx(120)
    assert injection.line_kv(2.4, injection.DeviceTerminal("b", "C", 1, False, None)) == pytest.approx(4.156922)
    assert storage.engine_state("charge", name="x") == "charging"
    common = dict(kw_rated=250, kva=250, pct_charge=100, pct_discharge=100, idling_kw=2.5, stored=500, minimum=150,
                  rated=500)
    assert storage.battery_dispatch("x", [("State", "charge"), ("kW", 150.0)], **common) == (
        "discharging", -150, "kW=150 after State=charging: discharging")
    assert storage.battery_dispatch("x", [("State", "charge"), ("kW", -0.0)], **common).state == "waiting"
    kept = [("kW", 40.0), ("State", "idling"), ("State", "discharging")]
    assert storage.battery_dispatch("x", kept, **common).kw == -40
    assert storage.battery_dispatch("x", [("kW", 40.0), ("State", "charging")], **common | {"stored": 200}).kw == 250
    with pytest.raises(ValueError, match="charging with 500 of 500 kWh stored"):
        storage.battery_dispatch("x", [("State", "charging")], **common)


def test_der_binds(der):
    network = dss_to_cim(der, name="atom")
    assert_base_voltages_agree(network)
    cim = network.cim
    connections = {pec.mRID: pec for pec in network.graph[cim.PowerElectronicsConnection].values()}
    assert len(connections) == 21
    assert float(connections["pv_school"].PowerElectronicsUnit[0].irradiance.to("kW/m**2")) == pytest.approx(0.8)
    assert float(connections["pv_pmppcap"].p.to("kW")) == pytest.approx(-6)
    house = connections["pv_house"]
    assert house.Terminals[0].phases.value == "s12" and float(house.p.to("kW")) == pytest.approx(-4)
    assert house.PowerElectronicsUnit[0].mRID == "pv_house_unit"
    assert connections["pv_dpv"].phaseConnection.value == "D"
    assert float(connections["pv_primary"].ratedU.to("kV")) == pytest.approx(2.4 * math.sqrt(3))
    ess = connections["storage_ess"].PowerElectronicsUnit[0]
    assert ess.batteryState.value == "discharging" and float(connections["storage_ess"].p.to("kW")) == -150
    assert connections["storage_school"].mRID != connections["pv_school"].mRID


@pytest.mark.parametrize("text, message", [
    ("New PVSystem.x bus1=b2 kv=0.48 Pmpp=10 model=2\n", "model=2 is not mapped"),
    ("New PVSystem.x bus1=b2 kv=0.48 Pmpp=10 EffCurve=eff\n", "EffCurve not mapped"),
    ("New PVSystem.x bus1=b2 kv=0.48 Pmpp=10 P-TCurve=pt\n", "P_TCurve not mapped"),
    ("New PVSystem.x bus1=b2 kv=0.48 Pmpp=10 kVA=12 WattPriority=yes\n", "WattPriority not mapped"),
    ("New Storage.x bus1=b2 kv=0.48 kWrated=100 kWhrated=200 State=charging\n", "charging with 200 of 200"),
    ("New Storage.x bus1=b2 kv=0.48 kWrated=100 kWhrated=200 %stored=10 State=discharging\n", "at or below"),
    ("New Storage.x bus1=b2 kv=0.48 kWrated=100 kWhrated=200 pf=0.9\n", "pf=0.9 not mapped"),
    ("New Storage.x bus1=b2 kv=0.48 kWrated=100 kWhrated=200 State=discharging %stored=60\n",
     "pct_stored is assigned after its last State or kW"),
    ("New Storage.x bus1=b2 kv=0.48 kWrated=100 kWhrated=200 DispMode=follow\n", "DispMode=follow"),
    ("New Storage.x phases=1 bus1=b2.1.2.3 kv=0.48 kWrated=100 kWhrated=200\n", "more nodes than its 2"),
])
def test_unmapped_der_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=message):
        pvsystem.map_pvsystem(native, site.buses, site.feeder)
        storage.map_storage(native, site.buses, site.feeder)


def _ask(query: str) -> str:
    dss.Text.Command(f"? {query}")
    return dss.Text.Result()


def _engine_kv(connection, unit_count: int) -> float:
    """The DSS kV back from ratedU (the exporter's inverse of injection.line_kv)."""
    kv = float(connection.ratedU.to("kV"))
    one_phase_wye = unit_count == 1 and connection.phaseConnection.value == "Y"
    return kv / math.sqrt(3) if one_phase_wye else kv


def _engine_differences(network) -> list[str]:
    """Every difference between the inverters and the engine's dispatch and ratings."""
    differences = []

    def check(label: str, ours: float, theirs: float) -> None:
        if not math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-9):
            differences.append(f"{label}: {ours} vs {theirs}")

    for connection in network.graph.get(network.cim.PowerElectronicsConnection, {}).values():
        unit = connection.PowerElectronicsUnit[0]
        name, count = connection.name, len(connection.PowerElectronicsConnectionPhase)
        if connection.mRID.startswith(pvsystem.PREFIX):
            dss.PVsystems.Name(name)
            check(f"{name} kW", -float(connection.p.to("kW")), dss.PVsystems.kW())
            check(f"{name} kvar", -float(connection.q.to("kVAr")), dss.PVsystems.kvar())
            check(f"{name} kVA", float(connection.ratedS.to("kVA")), dss.PVsystems.kVARated())
            check(f"{name} Pmpp", float(unit.maxP.to("kW")), dss.PVsystems.Pmpp())
            check(f"{name} irradiance", float(unit.irradiance.to("kW/m**2")), dss.PVsystems.Irradiance())
            check(f"{name} kV", _engine_kv(connection, count), float(_ask(f"pvsystem.{name}.kV")))
            continue
        element = f"storage.{name}"
        check(f"{name} kW", -float(connection.p.to("kW")), float(_ask(f"{element}.kW")))
        if ENGINE_STATE[unit.batteryState.value] != _ask(f"{element}.State").lower():
            differences.append(f"{name} state: {unit.batteryState.value} vs {_ask(f'{element}.State')}")
        check(f"{name} kVA", float(connection.ratedS.to("kVA")), float(_ask(f"{element}.kVA")))
        check(f"{name} kWrated", float(unit.maxP.to("kW")), float(_ask(f"{element}.kWrated")))
        check(f"{name} kWhrated", float(unit.ratedE.to("kWh")), float(_ask(f"{element}.kWhrated")))
        check(f"{name} kWhstored", float(unit.storedE.to("kWh")), float(_ask(f"{element}.kWhstored")))
        check(f"{name} kV", _engine_kv(connection, count), float(_ask(f"{element}.kV")))
    return differences


def test_atom_matches_the_engine(der):
    network = dss_to_cim(der, name="atom")
    compile_deck(ATOMS / "der.dss")
    assert _engine_differences(network) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_der_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the inverters ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_differences(network) == []


def test_a_negative_idling_loss_raises(tmp_path):
    """The engine takes a negative %IdlingkW (opendssdirect 0.9.4: ``kWrated=100 %IdlingkW=-2 State=idling``
    generates 2 kW while idling; Storage.pas:988 assigns it unchecked). An idling loss is a draw, and the exporter
    raises on a negative idlingP (decision 12), so the import raises too and the two directions agree."""
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + "New Storage.x bus1=b2 kv=0.48 kWrated=100 kWhrated=200 %IdlingkW=-2\n")
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=r"Storage x: %IdlingkW=-2 is negative"):
        storage.map_storage(native, site.buses, site.feeder)
