"""Export atoms and decks: Load, Capacitor and CapControl (EXPORT_MAPPING.md S6d), checked against the original
deck in the engine."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl_testing import cim_scope
from cimhub_opendss import DssImporter, DssReader
from cimhub_core.getters.phase_power import PhasePower
from cimhub_opendss.exporter.cim_to_dss import DssExporter, cim_to_dss
from cimhub_opendss.exporter.injection import equal_phases
from cimhub_opendss.schema import opendss_schema as schema

from conftest import deck
from engine_compare import _engine_state, assert_same_engine_state, assert_same_settings, engine_settings
from export_atoms import assert_matches_dss_golden, bus_names, export_atom, export_network

ATOMS = Path(__file__).parent / "atoms"
#: atom -> elements whose YPrim differs: house's kV=0.208 comes back as the bus's 0.2078 (CIM has no load rating, S4-2)
CASES = {
    "load/loads": {"load.house"},
    "capacitor/caps": set(),
}
#: the engine properties the importer maps, per class (kV is the bus's: compared to 1 %, as the importer checks it)
SETTINGS = {
    "Load": ("phases", "conn", "kW", "kvar", "model", "CVRwatts", "CVRvars", "NumCust", "enabled", "kV"),
    "Capacitor": ("phases", "conn", "kvar", "kv", "states", "enabled"),
    "CapControl": ("element", "terminal", "capacitor", "type", "PTratio", "CTratio", "ONsetting", "OFFsetting",
                   "Delay", "PTPhase", "enabled"),
}
KV_TOLERANCE = 0.01
#: whole decks whose every class is exported by S6d -> elements whose node order differs: IEEE37's reg1c is a coil
#: C -> B, which an AutoTransformerEnd's PhaseCode holds as BC (both windings reverse together: the same coil)
DECKS = {
    "IEEE/IEEE13_original/IEEE13Nodeckt.dss": set(),
    "IEEE/IEEE123/IEEE123Master.dss": set(),
    "IEEE/IEEE37/ieee37.dss": {"transformer.reg1c", "regcontrol.creg1c"},
    "IEEE/IEEE13_assets/IEEE13_Assets.dss": set(),
}


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


def _settings(path: Path, *, states: bool = True) -> dict[str, dict[str, object]]:
    """Every Load, Capacitor and CapControl's mapped engine properties; ``states=False`` leaves out a capacitor's
    states (a deck that solves when compiled switches them)."""
    properties = {kind: tuple(p for p in names if states or p != "states") for kind, names in SETTINGS.items()}
    return engine_settings(path, properties)


def _assert_same_settings(expected: dict, actual: dict) -> None:
    assert_same_settings(expected, actual, tolerance={"kV": KV_TOLERANCE})


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
    _assert_same_settings(_settings(atom), _settings(export_atom(atom, tmp_path, name_source="name")))


# whole decks ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("relative", DECKS)
def test_deck_exports_the_same_elements_and_settings(relative, tmp_path):
    """Every element on the same buses, and every load, capacitor and control set alike. YPrim and voltages wait for
    S6f: these decks solve with controls on when compiled, which moves taps and switches capacitors."""
    original = deck(relative)
    written = tmp_path / original.name
    cim_to_dss(_network(original), written, name_source="name")
    elements, _ = _engine_state(original)
    written_elements, _ = _engine_state(written)
    assert written_elements.keys() == elements.keys()
    reordered = {name for name in elements if written_elements[name][0] != elements[name][0]}
    assert reordered == DECKS[relative]
    _assert_same_settings(_settings(original, states=False), _settings(written, states=False))


# loads ---------------------------------------------------------------------------------------------------------


def test_load_kv_is_the_buses():
    loads = _records("load/loads", schema.Load)
    assert loads["cvr1"].kV == pytest.approx(4.16 / 3 ** 0.5, rel=1e-12)  # 1-phase wye: LN
    assert (loads["z"].kV, loads["pq"].kV) == (4.16, 4.16)  # delta, 3-phase: LL
    assert loads["leg2"].kV == pytest.approx(0.12)  # a split-phase leg: half the 240 V coil
    assert loads["house"].kV == pytest.approx(0.12 * 3 ** 0.5)  # two legs: the engine's sqrt 3 rule


def test_one_phase_delta_is_written_in_branch_order():
    loads = _records("load/loads", schema.Load)
    assert (loads["ca"].bus1, loads["z"].bus1, loads["ca"].phases) == ("b1.3.1", "b1.2.3", 1)


def test_unequal_phases_give_one_load_per_phase():
    network = _network(ATOMS / "load" / "loads.dss")
    consumer = _object(network, cim.EnergyConsumer, "ld_pq")
    consumer.customerCount = 4
    for phase, p in ((cim.SinglePhaseKind.A, 400.0), (cim.SinglePhaseKind.B, 385.0), (cim.SinglePhaseKind.C, 370.0)):
        child = cim.EnergyConsumerPhase(mRID=f"ld_pq_{phase.value}", phase=phase, EnergyConsumer=consumer,
                                        p=cim.ActivePower(p, "kW"), q=cim.ReactivePower(220.0, "kVAr"))
        consumer.EnergyConsumerPhase.append(child)
    loads = {str(r.name): r for r in _model(network).list_by_class(schema.Load) if str(r.name).startswith("pq")}
    assert {name: (r.bus1, r.phases, r.kW, r.NumCust) for name, r in loads.items()} == {
        "pq_a": ("b1.1", 1, 400.0, 4), "pq_b": ("b1.2", 1, 385.0, 0), "pq_c": ("b1.3", 1, 370.0, 0)}
    assert loads["pq_a"].kV == pytest.approx(4.16 / 3 ** 0.5)


def test_phases_a_rounding_error_apart_at_zero_are_equal():
    """rel_tol alone never matches 0 against 1e-12, so phases also agree within 1e-9 (kW, kVAr)."""
    A, B = cim.SinglePhaseKind.A, cim.SinglePhaseKind.B
    assert equal_phases({A: PhasePower(10.0, 0.0), B: PhasePower(10.0, 1e-12)})
    assert not equal_phases({A: PhasePower(10.0, 0.0), B: PhasePower(10.0, 1e-6)})


def test_mixed_zip_fractions_raise():
    network = _network(ATOMS / "load" / "loads.dss")
    response = _object(network, cim.EnergyConsumer, "ld_z").LoadResponse
    response.pConstantImpedance, response.pConstantPower = 0.5, 0.5
    with pytest.raises(ValueError, match=r"ZIP fractions .* are no one DSS model"):
        _model(network)


def test_ungrounded_wye_load_raises():
    network = _network(ATOMS / "load" / "loads.dss")
    _object(network, cim.EnergyConsumer, "ld_pq").grounded = False
    with pytest.raises(ValueError, match="a wye with grounded False"):
        _model(network)


# capacitors and controls ---------------------------------------------------------------------------------------


def test_open_bank_is_states_0():
    capacitors = _records("capacitor/caps", schema.Capacitor)
    assert (capacitors["open"].states, capacitors["c3"].states, capacitors["c3"].kvar) == ([0], [1], [600.0])


def test_two_sections_raise():
    network = _network(ATOMS / "capacitor" / "caps.dss")
    _object(network, cim.LinearShuntCompensator, "cap_c3").maximumSections = 2
    with pytest.raises(ValueError, match="maximumSections 2; one section is mapped"):
        _model(network)


def test_on_off_are_rebuilt_on_the_relays_side():
    controls = _records("capacitor/caps", schema.Capcontrol)
    assert {name: (c.type, c.ONsetting, c.OFFsetting) for name, c in controls.items()} == {
        "kvar": ("kvar", 150.0, -225.0), "volt": ("voltage", 115.0, 125.0), "own": ("voltage", 1950.0, 2500.0),
        "time": ("time", 8.0, 19.0)}
    assert (controls["volt"].element, controls["volt"].terminal, controls["kvar"].element) == \
        ("Line.l2", 2, "Line.capsw")


def test_control_without_deadband_raises():
    network = _network(ATOMS / "capacitor" / "caps.dss")
    _object(network, cim.RegulatingControl, "cc_volt").targetDeadband = None
    with pytest.raises(ValueError, match="targetDeadband is unset"):
        _model(network)


def test_voltage_control_without_pt_ratio_raises():
    network = _network(ATOMS / "capacitor" / "caps.dss")
    _object(network, cim.RegulatingControl, "cc_volt").ptRatio = None
    with pytest.raises(ValueError, match="ptRatio is unset"):
        _model(network)


def test_disabled_control_without_target_raises():
    """The getter lets a disabled control go without a target, but its CapControl still writes ON and OFF."""
    network = _network(ATOMS / "capacitor" / "caps.dss")
    control = _object(network, cim.RegulatingControl, "cc_volt")
    control.targetValue, control.enabled = None, False
    with pytest.raises(ValueError, match="targetValue is unset; a CapControl needs ON and OFF"):
        _model(network)


@pytest.mark.parametrize("control, attribute", [("cc_volt", "ptRatio"), ("cc_volt", "ctRatio")])
@pytest.mark.parametrize("ratio", [0.0, -20.0])
def test_control_with_a_ratio_of_zero_or_less_raises(control, attribute, ratio):
    """A negative ratio flips ON and OFF on the relay's side, so the engine switches the bank the wrong way."""
    network = _network(ATOMS / "capacitor" / "caps.dss")
    regulating = _object(network, cim.RegulatingControl, control)
    if attribute == "ctRatio":
        regulating.mode = cim.RegulatingControlModeKind.currentFlow
    setattr(regulating, attribute, ratio)
    with pytest.raises(ValueError, match=rf"{attribute} {ratio}; a CapControl's relay ratio is positive"):
        _model(network)


def test_control_in_another_mode_raises():
    network = _network(ATOMS / "capacitor" / "caps.dss")
    _object(network, cim.RegulatingControl, "cc_volt").mode = cim.RegulatingControlModeKind.powerFactor
    with pytest.raises(ValueError, match="mode powerFactor; a CapControl is"):
        _model(network)


def test_control_of_no_shunt_raises():
    network = _network(ATOMS / "capacitor" / "caps.dss")
    network.add_to_graph(cim.RegulatingControl(mRID="cc_spare", mode=cim.RegulatingControlModeKind.voltage))
    with pytest.raises(ValueError, match=r"regulates \[\]; a CapControl has one LinearShuntCompensator"):
        _model(network)
