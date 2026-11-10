"""Export atoms and decks: PVSystem, Storage, Generator and Reactor (EXPORT_MAPPING.md S6e), checked against the
original deck in the engine."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import opendssdirect as dss
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.schema import opendss_schema as schema

from conftest import compile_deck, deck
from engine_compare import assert_same_engine_state, assert_same_settings, engine_buses, engine_settings
from export_atoms import assert_matches_dss_golden, bus_names, export_atom, export_network

ATOMS = Path(__file__).parent / "atoms"
#: atom -> elements whose YPrim differs: the reactor atom's load kV=2.4 comes back as the bus's 2.40178 (S6d L1)
CASES = {
    "der/der": set(),
    "generator/gens": set(),
    "reactor/reactors": {"load.l3"},
}
#: the engine properties the importer maps, per class
SETTINGS = {
    "PVSystem": ("phases", "conn", "kVA", "Pmpp", "kv", "kvarMax", "kvarMaxAbs", "Vminpu", "enabled"),
    "Storage": ("phases", "conn", "kVA", "kv", "kWrated", "kWhrated", "kWhstored", "%reserve", "State", "kW",
                "%Discharge", "%Charge", "%EffCharge", "%EffDischarge", "%IdlingkW", "Vminpu", "enabled"),
    "Generator": ("phases", "conn", "kW", "kvar", "kVA", "kv", "model", "Vpu", "Maxkvar", "Minkvar", "enabled"),
    "Reactor": ("phases", "R", "X", "normamps", "emergamps", "enabled"),
}
#: (element, property) that come back otherwise, by design: a battery capped by its kVA keeps only the capped
#: output (its setpoint above kVA is not in CIM); and every model 7 Generator (CIM has no current limit; ``_differs``)
DIFFERS = frozenset({("storage.capped", "%Discharge")})
CURRENT_LIMITED = 7.0
#: whole decks with DER or reactors -> (elements whose node order differs, elements of a class the importer does not
#: map (DSS-11))
DECKS = {
    "IEEE/IEEE13_CDPSM/IEEE13_CDPSM.dss": (set(), {"relay.brkr1"}),
    "IEEE/IEEE123_PV/IEEE123Master_fixedVR.dss": (set(), {"energymeter.feeder"}),
    "IEEE/IEEE8500/Master.dss": (set(), set()),
    "PNNL/IEEE9500/Master-unbal-initial-config.dss": (set(), {"energymeter.m1", "energymeter.m2", "energymeter.m3"}),
    "UAF/ACEP_PSIL.dss": (set(), set()),
}
#: switch controls: a CIM Fuse or Recloser is the switch, so its DSS control comes back named by its line (S6b)
SWITCH_CONTROLS = ("Fuse", "Recloser", "SwtControl")


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


def _network(path: Path):
    return DssImporter(path.stem).to_cim(DssReader(path).read_all())


def _model(network):
    return DssExporter().to_model(network, name_source="name")


def _records(atom: str, native_class) -> dict:
    model = _model(_network(ATOMS / f"{atom}.dss"))
    return {str(record.name).lower(): record for record in model.list_by_class(native_class)}


def _object(network, cim_class, mrid):
    return next(obj for obj in network.graph[cim_class].values() if obj.mRID == mrid)


def _settings(path: Path) -> dict[str, dict[str, object]]:
    """Every mapped setting, and each PV's dispatch after Compile (``PVSystems.kW``/``kvar``: irradiance, pf and
    kvar may come back otherwise and give the same output)."""
    found = engine_settings(path, SETTINGS)
    for name in dss.PVsystems.AllNames():
        dss.PVsystems.Name(name)
        found[f"pvsystem.{name.lower()}"].update(dispatch_kw=dss.PVsystems.kW(), dispatch_kvar=dss.PVsystems.kvar())
    return found


# atoms ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES)
def test_export_matches_the_original_in_the_engine(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    written = export_atom(atom, tmp_path, name_source="name")
    assert_same_engine_state(atom, written, yprim_differs=frozenset(CASES[case]))


@pytest.mark.parametrize("case", CASES)
def test_export_under_mrid_and_uri_solves_the_same(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    for name_source in ("mrid", "uri"):
        written, network = export_network(atom, tmp_path, name_source=name_source)
        assert_same_engine_state(atom, written, by_element=False, bus_names=bus_names(network, name_source))


@pytest.mark.parametrize("case", CASES)
def test_export_matches_golden(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    written = export_atom(atom, tmp_path, name_source="mrid")
    assert_matches_dss_golden(written, atom.parent / "export" / f"{atom.stem}.dss")


@pytest.mark.parametrize("case", CASES)
def test_settings_match_the_engine(case, tmp_path):
    atom = ATOMS / f"{case}.dss"
    expected, actual = _settings(atom), _settings(export_atom(atom, tmp_path, name_source="name"))
    assert_same_settings(expected, actual, differs=_differs(expected))


# whole decks ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("relative", [relative if relative.startswith("IEEE/IEEE13_CDPSM") else
                                      pytest.param(relative, marks=pytest.mark.roundtrip) for relative in DECKS])
def test_deck_exports_the_same_elements_and_settings(relative, tmp_path):
    """Every element on the same buses after Compile, and every DER and reactor set alike. YPrim and voltages wait
    for S6f (IEEE9500 solves when compiled, and does not converge with controls off)."""
    original = deck(relative)
    written = tmp_path / original.name
    cim_to_dss(_network(original), written, name_source="name")
    reordered, not_mapped = DECKS[relative]
    renamed = _switch_control_names(original)
    buses = {renamed.get(name, name): value for name, value in engine_buses(original).items() if name not in not_mapped}
    written_buses = engine_buses(written)
    assert written_buses.keys() <= buses.keys()
    # E6: a switch closed in both states gets no SwtControl (IEEE9500 has one on every switch)
    assert all(name.startswith("swtcontrol.") for name in buses.keys() - written_buses.keys())
    assert {name for name in written_buses if written_buses[name] != buses[name]} == reordered
    expected = _settings(original)
    assert_same_settings(expected, _settings(written), differs=_differs(expected))


def _differs(settings: dict) -> frozenset[tuple[str, str]]:
    """``DIFFERS`` and the model of every model 7 Generator, which comes back as model 1."""
    limited = {(name, "model") for name, values in settings.items() if values.get("model") == CURRENT_LIMITED
               and name.startswith("generator.")}
    return DIFFERS | limited


def _switch_control_names(path: Path) -> dict[str, str]:
    """``{control: the name it comes back as}``: each Fuse, Recloser and SwtControl as ``<class>.<switched line>``
    (IEEE9500's ``Fuse.2002200004641085`` switches ``Line.2002200004641085_sw``)."""
    compile_deck(path)
    renamed = {}
    for name in dss.Circuit.AllElementNames():
        kind = name.split(".")[0]
        if kind in SWITCH_CONTROLS:
            dss.Circuit.SetActiveElement(name)
            line = dss.Properties.Value("SwitchedObj").split(".", 1)[-1]
            renamed[name.lower()] = f"{kind}.{line}".lower()
    return renamed


# inverters: several units, per phase -------------------------------------------------------------------------------


def _hybrid(pv_kw: float, battery_kw: float):
    """The der atom with a battery added behind PVSystem School's inverter (300 kVA, -240 kW): the PV unit's p and
    the battery's in the load sign."""
    network = _network(ATOMS / "der" / "der.dss")
    connection = _object(network, cim.PowerElectronicsConnection, "pv_school")
    pv = connection.PowerElectronicsUnit[0]
    pv.name, pv.p = "roof", cim.ActivePower(pv_kw, "kW")
    battery = cim.BatteryUnit(mRID="bank", name="bank", maxP=cim.ActivePower(100, "kW"),
                              minP=cim.ActivePower(-100, "kW"), ratedE=cim.RealEnergy(200, "kWh"),
                              storedE=cim.RealEnergy(100, "kWh"), minimumE=cim.RealEnergy(40, "kWh"),
                              p=cim.ActivePower(battery_kw, "kW"), PowerElectronicsConnection=connection,
                              batteryState=cim.BatteryStateKind.discharging if battery_kw < 0 else
                              cim.BatteryStateKind.charging)
    connection.PowerElectronicsUnit.append(battery)
    network.add_to_graph(battery)
    return network


def test_hybrid_inverter_is_one_device_per_unit(tmp_path):
    network = _hybrid(-200, -40)
    model = _model(network)
    pv = next(r for r in model.list_by_class(schema.Pvsystem) if r.name == "roof")
    bank = next(r for r in model.list_by_class(schema.Storage) if r.name == "bank")
    # shares by maxP: 300 / 400 and 100 / 400 of the 300 kVA inverter
    assert (pv.kVA, pv.Pmpp, pv.irradiance, pv.kvarMax) == pytest.approx((225, 300, 200 / 300, 225))
    assert (bank.kVA, bank.kWrated, bank.State, bank.pct_Discharge) == (pytest.approx(75), 100, "discharging", 40)
    written = tmp_path / "hybrid.dss"
    cim_to_dss(network, written, name_source="name")
    compile_deck(written)
    dss.PVsystems.Name("roof")
    dss.Circuit.SetActiveElement("Storage.bank")
    assert (dss.PVsystems.kW(), float(dss.Properties.Value("kW"))) == pytest.approx((200, 40))


def test_units_without_p_take_their_share_of_it():
    network = _network(ATOMS / "der" / "der.dss")
    connection = _object(network, cim.PowerElectronicsConnection, "pv_school")
    connection.PowerElectronicsUnit[0].name = "roof"
    carport = cim.PhotoVoltaicUnit(mRID="carport", name="carport", maxP=cim.ActivePower(100, "kW"),
                                   PowerElectronicsConnection=connection)
    connection.PowerElectronicsUnit.append(carport)
    network.add_to_graph(carport)
    pvs = {r.name: r for r in _model(network).list_by_class(schema.Pvsystem) if r.name in ("roof", "carport")}
    assert {name: (r.kVA, r.Pmpp, r.irradiance) for name, r in pvs.items()} == {
        "roof": pytest.approx((225, 300, 0.6)), "carport": pytest.approx((75, 100, 0.6))}


def test_unit_above_its_share_of_the_inverter_raises():
    # a DC-coupled PV feeding its battery: 300 kW out of the PV on a 225 kVA share, 240 kW net
    with pytest.raises(ValueError, match=r"gives 300 kW and 0 kvar, above its 225 kVA share of the inverter"):
        _model(_hybrid(-300, 60))


def test_unequal_phases_give_one_inverter_per_phase():
    network = _network(ATOMS / "der" / "der.dss")
    connection = _object(network, cim.PowerElectronicsConnection, "pv_school")
    for phase, p in ((cim.SinglePhaseKind.A, -100.0), (cim.SinglePhaseKind.B, -80.0), (cim.SinglePhaseKind.C, -60.0)):
        child = cim.PowerElectronicsConnectionPhase(mRID=f"pv_school_{phase.value}", phase=phase,
                                                    PowerElectronicsConnection=connection,
                                                    p=cim.ActivePower(p, "kW"), q=cim.ReactivePower(0, "kVAr"))
        connection.PowerElectronicsConnectionPhase.append(child)
    pvs = {r.name: r for r in _model(network).list_by_class(schema.Pvsystem) if r.name.startswith("School")}
    assert {name: (r.bus1, r.phases, r.kVA, r.Pmpp, r.irradiance) for name, r in pvs.items()} == {
        "School_a": ("b2.1", 1, 100, 100, 1.0), "School_b": ("b2.2", 1, 100, 100, 0.8),
        "School_c": ("b2.3", 1, 100, 100, 0.6)}
    assert pvs["School_a"].kv == pytest.approx(0.48 / 3 ** 0.5)


def test_unit_of_no_dss_class_raises():
    network = _network(ATOMS / "der" / "der.dss")
    connection = _object(network, cim.PowerElectronicsConnection, "pv_school")
    wind = cim.PowerElectronicsWindUnit(mRID="wind", maxP=cim.ActivePower(100, "kW"),
                                        PowerElectronicsConnection=connection)
    connection.PowerElectronicsUnit.append(wind)
    with pytest.raises(ValueError, match=r"units \[\"PowerElectronicsWindUnit 'wind'\"\] have no DSS class"):
        _model(network)


# batteries, machines, reactors -------------------------------------------------------------------------------------


def test_battery_in_an_unmapped_state_raises():
    network = _network(ATOMS / "der" / "der.dss")
    _object(network, cim.BatteryUnit, "storage_school_unit").batteryState = cim.BatteryStateKind.full
    with pytest.raises(ValueError, match="batteryState full; a Storage State is charging, discharging or waiting"):
        _model(network)


def test_battery_with_q_raises():
    network = _network(ATOMS / "der" / "der.dss")
    _object(network, cim.PowerElectronicsConnection, "storage_batidle").q = cim.ReactivePower(10, "kVAr")
    with pytest.raises(ValueError, match="q 10.0 kVAr; a Storage's kvar is not mapped"):
        _model(network)


def test_waiting_battery_draws_its_idling_loss():
    storages = _records("der/der", schema.Storage)
    assert (storages["batidle"].State, storages["batidle"].pct_IdlingkW, storages["batidle"].pct_Discharge) == \
        ("idling", pytest.approx(1.0), None)


def test_disabled_machine_control_is_model_1():
    network = _network(ATOMS / "generator" / "gens.dss")
    _object(network, cim.SynchronousMachine, "gen_steam").controlEnabled = False
    _object(network, cim.RegulatingControl, "gen_steam_ctrl").enabled = False
    steam = next(r for r in _model(network).list_by_class(schema.Generator) if r.name == "steam")
    assert (str(steam.model), steam.Vpu, steam.maxkvar) == ("ConstantPQ", None, None)


def test_machine_control_of_another_terminal_raises():
    network = _network(ATOMS / "generator" / "gens.dss")
    other = _object(network, cim.SynchronousMachine, "gen_pq").Terminals[0]
    _object(network, cim.RegulatingControl, "gen_steam_ctrl").Terminal = other
    with pytest.raises(ValueError, match="its control monitors another terminal"):
        _model(network)


def test_machine_without_earthing_raises():
    network = _network(ATOMS / "generator" / "gens.dss")
    _object(network, cim.SynchronousMachine, "gen_pq").earthing = None
    with pytest.raises(ValueError, match=r"earthing None; it is the Generator's conn \(S4b-5\)"):
        _model(network)


def test_coupled_reactor_raises():
    network = _network(ATOMS / "reactor" / "reactors.dss")
    _object(network, cim.SeriesCompensator, "rx_r1").x0 = cim.Reactance(6, "ohm")
    with pytest.raises(ValueError, match=r"\['x0'\] differ from r/x; a DSS Reactor has no mutual coupling"):
        _model(network)
