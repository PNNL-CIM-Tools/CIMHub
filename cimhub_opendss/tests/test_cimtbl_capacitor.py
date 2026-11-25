"""Atom tests: OpenDSS Capacitor + CapControl -> capacitor.cimtbl + capcontrol.cimtbl -> cim18v17, with the engine
as the oracle for the banks and the control settings."""

from __future__ import annotations

import math
from pathlib import Path

import opendssdirect as dss
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden, cim_scope
from cimhub_core.getters.control import get_regulating_control
from cimhub_opendss import dss_to_cim
from cimhub_opendss.dss_reader import DssReader
from cimhub_opendss.importer import dss_to_cimtbl
from cimhub_opendss.importer.cimtbl import capacitor, capcontrol

from conftest import ENGINE_DECKS, compile_deck, deck
from test_dss_to_cimtbl import assert_base_voltages_agree

ATOMS = Path(__file__).parent / "atoms" / "capacitor"
CIRCUIT = ("Clear\nNew Circuit.atom basekv=4.16 bus1=sourcebus pu=1.0 MVAsc3=20000 MVAsc1=21000\n"
           "New Line.l1 bus1=sourcebus bus2=b1 phases=3 r1=0.1 x1=0.2 r0=0.3 x0=0.6 length=1 units=kft\n"
           "New Transformer.t phases=3 buses=[b1 b9] kVs=[4.16 0.48] kVAs=[500 500]\n"
           "New Capacitor.c bus1=b1 kvar=600 kv=4.16\n")
#: The engine's CapControl mode codes.
ENGINE_MODE = {"currentFlow": 0, "voltage": 1, "reactivePower": 2, "timeScheduled": 3}


@pytest.fixture(autouse=True)
def _cim_scope():
    with cim_scope():
        yield


@pytest.fixture(scope="module")
def caps():
    return DssReader(ATOMS / "caps.dss").read_all()


def test_classification_is_complete():
    check_fields(capacitor.FIELDS, capacitor.NATIVE_CLASS)
    check_fields(capcontrol.FIELDS, capcontrol.NATIVE_CLASS)


def test_matches_golden(caps):
    site = dss_to_cimtbl.site(caps)
    assert_matches_golden(capacitor.map_capacitor(caps, site.buses, site.feeder), ATOMS / "caps.cimtbl")
    assert_matches_golden(capcontrol.map_capcontrol(caps, site.buses), ATOMS / "caps_capcontrol.cimtbl")


def test_derived_settings():
    assert capacitor.b_per_section(600, 4.16) == pytest.approx(34.6709, rel=1e-5)  # mS
    assert capcontrol.control_mode("volt", name="c") == "voltage"
    assert capcontrol.on_off_target(115, 125, "voltage", ptratio=20, ctratio=60, name="c") == (2400, 200)
    assert capcontrol.on_off_target(150, -225, "reactivePower", ptratio=1, ctratio=1, name="c") == (-37.5, 375)
    assert capcontrol.on_off_target(300, 200, "currentFlow", ptratio=60, ctratio=60, name="c") == (15000, 6000)
    assert capcontrol.on_off_target(8, 19, "timeScheduled", ptratio=60, ctratio=60, name="c") == (13.5, 11)
    with pytest.raises(ValueError, match="ON 125 is not below OFF 115"):
        capcontrol.on_off_target(125, 115, "voltage", ptratio=1, ctratio=1, name="c")


def test_controls_bind(caps):
    network = dss_to_cim(caps, name="atom")
    assert_base_voltages_agree(network)
    banks = {bank.name: bank for bank in network.graph[network.cim.LinearShuntCompensator].values()}
    assert len(banks) == 5 and banks["open"].sections == 0 and banks["cd"].phaseConnection.value == "D"
    assert float(banks["c3"].bPerSection.to("S")) == pytest.approx(600e3 / 4160 ** 2)  # the mS column, in SI
    own = banks["own"].RegulatingControl
    assert own.Terminal is banks["own"].Terminals[0] and float(banks["own"].aVRDelay.to("s")) == 300
    assert banks["own"].RegulatingControl.RegulatingCondEq == [banks["own"]]
    assert banks["c1"].RegulatingControl.Terminal.mRID == "ln_l2_T2"
    assert banks["c1"].RegulatingControl.monitoredPhase.value == "C"
    assert banks["c3"].RegulatingControl.Terminal.mRID == "sw_capsw_T1"
    assert banks["open"].RegulatingControl is None
    kvar = next(bank for bank in banks.values() if bank.RegulatingControl and bank.RegulatingControl.name == "kvar")
    assert get_regulating_control(kvar.RegulatingControl).target == pytest.approx(-37500)  # VAr, in SI


@pytest.mark.parametrize("text, message", [
    ("New Capacitor.x bus1=b1 kvar=[300 300]\n", "2 steps"),
    ("New Capacitor.x bus1=b1 bus2=b1.4.4.4\n", "bus2"),
    ("New Capacitor.x bus1=b1 R=[1]\n", "R not mapped"),
    ("New CapControl.x capacitor=c element=line.l1 type=pf\n", "type=pf is not mapped"),
    ("New CapControl.x capacitor=c element=line.l1 type=voltage on=125 off=115\n", "ON 125.0 is not below"),
    ("New CapControl.x capacitor=c element=transformer.t\n", "only a Line or a Capacitor terminal"),
    ("New CapControl.x capacitor=c element=line.l1\nNew CapControl.y capacitor=c element=line.l1\n",
     "controlled by CapControls x and y"),
    ("New CapControl.x capacitor=nothing element=line.l1\n", "capacitor=nothing is no Capacitor"),
    ("New CapControl.x capacitor=c element=line.l1 PTPhase=4\n", "PTPhase=4"),
    ("New CapControl.x capacitor=c element=line.l1 PTPhase=AVG\n", "PTPhase=AVG is not mapped"),
])
def test_unmapped_banks_and_controls_fail_fast(tmp_path, text, message):
    path = tmp_path / "deck.dss"
    path.write_text(CIRCUIT + text)
    native = DssReader(path).read_all()
    site = dss_to_cimtbl.site(native)
    with pytest.raises(ValueError, match=message):
        capacitor.map_capacitor(native, site.buses, site.feeder)
        capcontrol.map_capcontrol(native, site.buses)


#: The unit a control's settings are read in (through targetValueUnitMultiplier), by mode.
SETTING_UNIT = {"voltage": "V", "currentFlow": "A", "reactivePower": "kVAr", "timeScheduled": None}


def _on_off(control) -> tuple[float, float]:
    """The DSS ON and OFF settings rebuilt from a control's target, deadband and mode (the exporter's inverse)."""
    mode = control.mode.value
    settings = get_regulating_control(control, SETTING_UNIT[mode])
    low, high = settings.target - settings.deadband / 2, settings.target + settings.deadband / 2
    on, off = (high, low) if mode in ("currentFlow", "reactivePower") else (low, high)
    scale = {"voltage": control.ptRatio, "currentFlow": control.ctRatio}.get(mode, 1.0)
    return on / scale, off / scale


def _engine_differences(network, *, states: bool) -> list[str]:
    """Every difference between the banks and controls and the engine's. ``states`` compares the closed steps
    too: a deck that solves when compiled switches them."""
    differences = []

    def check(label: str, ours: float, theirs: float) -> None:
        if not math.isclose(ours, theirs, rel_tol=1e-9, abs_tol=1e-9):
            differences.append(f"{label}: {ours} vs {theirs}")

    for bank in network.graph.get(network.cim.LinearShuntCompensator, {}).values():
        dss.Capacitors.Name(bank.name)
        check(f"{bank.name} kvar", float(bank.nomQ.to("kVAr")), dss.Capacitors.kvar())
        check(f"{bank.name} kV", float(bank.nomU.to("kV")), dss.Capacitors.kV())
        check(f"{bank.name} delta", bank.phaseConnection.value == "D", dss.Capacitors.IsDelta())
        check(f"{bank.name} steps", bank.maximumSections, dss.Capacitors.NumSteps())
        if states:
            check(f"{bank.name} states", bank.sections, sum(dss.Capacitors.States()))
        control = bank.RegulatingControl
        if control is None:
            continue
        dss.CapControls.Name(control.name)
        on, off = _on_off(control)
        check(f"{control.name} mode", ENGINE_MODE[control.mode.value], dss.CapControls.Mode())
        check(f"{control.name} ON", on, dss.CapControls.ONSetting())
        check(f"{control.name} OFF", off, dss.CapControls.OFFSetting())
        check(f"{control.name} PTratio", control.ptRatio, dss.CapControls.PTRatio())
        check(f"{control.name} CTratio", control.ctRatio, dss.CapControls.CTRatio())
        check(f"{control.name} Delay", float(bank.aVRDelay.to("s")), dss.CapControls.Delay())
        check(f"{control.name} terminal", control.Terminal.sequenceNumber, dss.CapControls.MonitoredTerm())
        element = control.Terminal.ConductingEquipment
        kind = "capacitor" if isinstance(element, network.cim.LinearShuntCompensator) else "line"
        if f"{kind}.{element.name}".lower() != dss.CapControls.MonitoredObj().lower():
            differences.append(f"{control.name} element: {kind}.{element.name} vs {dss.CapControls.MonitoredObj()}")
    return differences


def test_atom_matches_the_engine(caps):
    network = dss_to_cim(caps, name="atom")
    compile_deck(ATOMS / "caps.dss")
    assert _engine_differences(network, states=True) == []


@pytest.mark.parametrize("relative", ENGINE_DECKS)
def test_banks_match_the_engine(relative):
    path = deck(relative)
    try:
        network = dss_to_cim(DssReader(path).read_all(), name="deck")
    except ValueError as error:
        if "DSS-10" in str(error):
            pytest.skip(f"{relative}: stops before the capacitors ({str(error)[:80]})")
        raise
    compile_deck(path)
    assert _engine_differences(network, states=False) == []
