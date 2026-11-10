"""DistributionCapacitor → LinearShuntCompensator + RegulatingControl (tests/atoms/capacitor)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import capacitor
from gdm.systems.distribution.components import DistributionCapacitor
from gdm.systems.distribution.controllers import (
    ActivePowerCapacitorController,
    CurrentCapacitorController,
    DailyTimedCapacitorController,
    ReactivePowerCapacitorController,
    VoltageCapacitorController,
)
from gdm.systems.distribution.enums import ConnectionType, Phase
from gdm.systems.distribution.equipment import CapacitorEquipment, PhaseCapacitorEquipment
from gdm.quantities import Voltage

from cimhub_gdm import gdm_to_cim

ABC, LL, LG = gdm_atoms.ABC, gdm_atoms.LL, gdm_atoms.LG


def test_capacitors_match_golden():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_capacitors(system)
    gdm_atoms.assert_import_matches(system, gdm_atoms.ATOMS / "capacitor" / "capacitors.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (capacitor.FIELDS_DistributionCapacitor, DistributionCapacitor),
    (capacitor.FIELDS_CapacitorEquipment, CapacitorEquipment),
    (capacitor.FIELDS_PhaseCapacitorEquipment, PhaseCapacitorEquipment),
    (capacitor.FIELDS_VoltageCapacitorController, VoltageCapacitorController),
    (capacitor.FIELDS_CurrentCapacitorController, CurrentCapacitorController),
    (capacitor.FIELDS_ActivePowerCapacitorController, ActivePowerCapacitorController),
    (capacitor.FIELDS_ReactivePowerCapacitorController, ReactivePowerCapacitorController),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


def test_voltage_targets_are_on_the_primary_side():
    controller = VoltageCapacitorController(on_voltage=Voltage(115, "volt"), off_voltage=Voltage(125, "volt"),
                                            pt_ratio=20)
    assert capacitor.capacitor_targets(controller) == (2400.0, 200.0, {"ptRatio": 20})


@pytest.mark.parametrize("state, sections", [([True], 2), ([False], 0), ([True, True, True], 2)])
def test_switched_sections(state, sections):
    assert capacitor.switched_sections(state, ABC, 2, "x") == sections


@pytest.mark.parametrize("state", [[True, False, True], [True, True]])
def test_ambiguous_state_raises(state):
    with pytest.raises(ValueError, match="state"):
        capacitor.switched_sections(state, ABC, 1, "x")


def _system(cap):
    system = gdm_atoms.shell_system()
    system.add_component(cap(system))
    return system


def test_unequal_phase_capacitors_raise():
    def cap(system):
        built = gdm_atoms.capacitor(system, "x", "b1", ABC, 100, 4.16, LL)
        built.equipment.phase_capacitors[1].num_banks_on = 0
        return built

    with pytest.raises(ValueError, match="num_banks_on differs by phase"):
        gdm_to_cim(_system(cap))


def test_single_phase_wye_rated_line_to_line_raises():
    with pytest.raises(ValueError, match="expected line-to-ground"):
        gdm_to_cim(_system(lambda system: gdm_atoms.capacitor(system, "x", "b1", [Phase.A], 50, 4.16, LL)))


def test_unmapped_connection_raises():
    with pytest.raises(ValueError, match="connection_type"):
        gdm_to_cim(_system(lambda system: gdm_atoms.capacitor(system, "x", "b1", ABC, 50, 4.16, LL,
                                                              connection=ConnectionType.OPEN_STAR)))


def test_controllers_differing_by_phase_raise():
    def controller(on):
        return VoltageCapacitorController(on_voltage=Voltage(on, "volt"), off_voltage=Voltage(125, "volt"),
                                          pt_ratio=20)

    controllers = [controller(115), controller(116), controller(115)]
    with pytest.raises(ValueError, match="controllers differ by phase"):
        gdm_to_cim(_system(lambda system: gdm_atoms.capacitor(system, "x", "b1", ABC, 50, 4.16, LL,
                                                              controllers=controllers)))


def test_daily_timed_controller_is_pending():
    from datetime import time
    controllers = [DailyTimedCapacitorController(on_time=time(8), off_time=time(19))]
    with pytest.raises(ValueError, match="DailyTimedCapacitorController x1: pending, a schedule"):
        gdm_to_cim(_system(lambda system: gdm_atoms.capacitor(system, "x", "b1", ABC, 50, 4.16, LL,
                                                              controllers=controllers)))
