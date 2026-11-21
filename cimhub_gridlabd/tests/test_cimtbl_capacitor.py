"""S4a: capacitors: classification, the atom, GridLAB-D's VAr and switching through the core getters, fail fast; the
decks run in test_cimtbl_sweep.py."""
from __future__ import annotations

from pathlib import Path

import cimprofiles.cim18.cim18v17 as cim
import pytest

from cimhub_core.cimtbl import check_fields
from cimhub_core.cimtbl_testing import assert_matches_golden
from cimhub_core.getters.control import get_equipment_control
from cimhub_core.getters.shunt import get_shunt_reactive_power
from cimhub_gridlabd.glm_reader import GlmReader
from cimhub_gridlabd.importer.cimtbl import capacitor
from cimhub_gridlabd.importer.glm_to_cimtbl import GlmImporter, glm_to_cim
from cimhub_gridlabd.schema import gridlabd as schema

ATOM = Path(__file__).parent / "atoms" / "capacitor"
MODEL = "atom"


def read(path: Path, **kwargs):
    return GlmReader(path, **kwargs).read_all()


def capacitor_part(model, name: str):
    return next(part for part in GlmImporter(name).to_cimtbl(model).parts if part.name == "capacitor")


def test_every_slot_is_classified():
    check_fields(capacitor.FIELDS, schema.Capacitor)


def letters(text) -> str:
    return "".join(letter for letter in "ABC" if letter in str(text or ""))


def assert_gridlabd_capacitors(model, network) -> int:
    """Each connected phase's VAr at its rating is GridLAB-D's capacitor_X (Y = jQ / V^2, capacitor.cpp:394), its
    sections the switch state GridLAB-D starts with, and a control sits on exactly the pt_phase units (S4a-8)."""
    shunts = {str(shunt.mRID): shunt for shunt in network.list_by_class(cim.LinearShuntCompensator)}
    checked = 0
    for cap in model.list_by_class(schema.Capacitor):
        connected = letters(cap.phases_connected or cap.phases)
        automatic = str(cap.control) == "VOLT"
        per_phase = automatic and str(cap.control_level or "INDIVIDUAL") == "INDIVIDUAL"
        for letter in connected:
            name = f"cap_{cap.name}_{letter}" if per_phase else f"cap_{cap.name}"
            shunt = shunts[name]
            rated = get_shunt_reactive_power(shunt, sections="maximum", voltage="nominal")
            expected = float(cim.ReactivePower(float(getattr(cap, f"capacitor_{letter}")),
                                               model.unit(cap, f"capacitor_{letter}")).to("VAr"))
            assert rated.per_phase[cim.SinglePhaseKind(letter)] == pytest.approx(expected), (name, letter)
            closed = str(getattr(cap, f"switch{letter}") or "OPEN") == "CLOSED"
            assert shunt.sections == (1 if closed else 0), name
            control = get_equipment_control(shunt)
            controlled = automatic and (letter in letters(cap.pt_phase) or not per_phase)
            assert (control is not None) is controlled, name
            if controlled:
                assert control.control.target - control.control.deadband / 2 == pytest.approx(
                    float(cap.voltage_set_low))
            checked += 1
    return checked


# -- tier 1 / 1b: the atom ----------------------------------------------------------------------------------------

def test_atom_golden():
    assert_matches_golden(capacitor_part(read(ATOM / "capacitor.glm"), MODEL), ATOM / "capacitor.capacitor.cimtbl")


def test_atom_binds(scope):
    model = read(ATOM / "capacitor.glm")
    network = glm_to_cim(model, name=MODEL)
    assert assert_gridlabd_capacitors(model, network) == 10
    shunts = {str(shunt.mRID): shunt for shunt in network.list_by_class(cim.LinearShuntCompensator)}
    # INDIVIDUAL VOLT with pt_phase B: three units, A and C uncontrolled and OPEN (S4a-8), B's delay 15 + 30 s
    assert [get_equipment_control(shunts[f"cap_c_volt_{letter}"]) is None for letter in "ABC"] == [True, False, True]
    assert get_equipment_control(shunts["cap_c_volt_B"]).delay == pytest.approx(45.0)
    # a gang unit is rated line to line, so Q = b nomU^2 is its total
    assert get_shunt_reactive_power(shunts["cap_c_manual"], sections="actual", voltage="nominal").total == (
        pytest.approx(600000.0))


# -- fail fast -------------------------------------------------------------------------------------------------------

def raises(tmp_path, text: str, match: str):
    path = tmp_path / "model.glm"
    path.write_text(f'#include "{ATOM / "capacitor.glm"}"\n' + text)
    with pytest.raises(ValueError, match=match):
        GlmImporter(MODEL).to_cimtbl(read(path))


def _cap(body: str) -> str:
    return (f"object capacitor {{ name x; parent n2; phases ABCN; nominal_voltage 2401.78; capacitor_A 100; "
            f"capacitor_B 100; capacitor_C 100; {body} }}")


@pytest.mark.parametrize("control", ("VAR", "VARVOLT", "CURRENT"))
def test_other_controls_raise(tmp_path, control):
    raises(tmp_path, _cap(f"control {control};"), f"control {control}; MANUAL, VOLT are mapped")


def test_delta_raises(tmp_path):
    raises(tmp_path, _cap("phases_connected ABCD;"), "a delta capacitor is not mapped")


def test_remote_sense_raises(tmp_path):
    raises(tmp_path, _cap("remote_sense n3;"), "remote_sense n3; not mapped")


def test_gang_switch_states_that_differ_raise(tmp_path):
    raises(tmp_path, _cap("switchA CLOSED;"), r"switch states \['CLOSED', 'OPEN'\] differ")


def test_unbalanced_gang_unit_raises(tmp_path):
    raises(tmp_path, _cap("capacitor_C 200;"), "differ .* on a gang unit")


def test_volt_without_set_points_raises(tmp_path):
    raises(tmp_path, _cap("control VOLT; pt_phase B;"), "VOLT without voltage_set_low and voltage_set_high")


def test_pt_phase_not_connected_raises(tmp_path):
    raises(tmp_path, _cap("control VOLT; pt_phase C; phases_connected AB; voltage_set_low 1; voltage_set_high 2;"),
           "pt_phase C must name connected phases of AB")


def test_unrated_connected_phase_raises(tmp_path):
    raises(tmp_path, "object capacitor { name x; parent n5; phases AN; nominal_voltage 2401.78; }",
           "capacitor_A unset or 0 on a connected phase")
