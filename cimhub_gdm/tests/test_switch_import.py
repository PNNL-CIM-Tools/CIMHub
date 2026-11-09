"""Switching devices → Switch subclasses by equipment class (tests/atoms/switch)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import switch
from gdm.distribution.components import (
    MatrixImpedanceFuse,
    MatrixImpedanceRecloser,
    MatrixImpedanceSwitch,
    SequenceImpedanceSwitch,
)
from gdm.distribution.controllers import DistributionSwitchController
from gdm.distribution.enums import Phase
from gdm.distribution.equipment import (
    CircuitBreakerEquipment,
    DisconnectorEquipment,
    EarthingSwitchEquipment,
    MatrixImpedanceFuseEquipment,
    MatrixImpedanceRecloserEquipment,
    MatrixImpedanceSwitchEquipment,
    SequenceImpedanceSwitchEquipment,
)
from gdm.quantities import Current

from cimhub_gdm import gdm_to_cim


def _system():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_switches(system)
    return system


def test_switches_match_golden():
    gdm_atoms.assert_import_matches(_system(), gdm_atoms.ATOMS / "switch" / "switches.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (switch.FIELDS_MatrixImpedanceSwitch, MatrixImpedanceSwitch),
    (switch.FIELDS_SequenceImpedanceSwitch, SequenceImpedanceSwitch),
    (switch.FIELDS_MatrixImpedanceFuse, MatrixImpedanceFuse),
    (switch.FIELDS_MatrixImpedanceRecloser, MatrixImpedanceRecloser),
    (switch.FIELDS_MatrixImpedanceSwitchEquipment, MatrixImpedanceSwitchEquipment),
    (switch.FIELDS_SequenceImpedanceSwitchEquipment, SequenceImpedanceSwitchEquipment),
    (switch.FIELDS_CircuitBreakerEquipment, CircuitBreakerEquipment),
    (switch.FIELDS_DisconnectorEquipment, DisconnectorEquipment),
    (switch.FIELDS_MatrixImpedanceFuseEquipment, MatrixImpedanceFuseEquipment),
    (switch.FIELDS_MatrixImpedanceRecloserEquipment, MatrixImpedanceRecloserEquipment),
    (switch.FIELDS_DistributionSwitchController, DistributionSwitchController),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


def _one_switch(**changes):
    """The shell plus switch ``s`` (b1-b3, ABC, closed), with ``changes`` applied."""
    system = gdm_atoms.shell_system()
    b1, b3 = gdm_atoms.bus(system, "b1"), gdm_atoms.bus(system, "b3")
    equipment = MatrixImpedanceSwitchEquipment(name="s_eq", ampacity=Current(400, "ampere"),
                                               **gdm_atoms._matrices(3))
    fields = dict(name="s", buses=[b1, b3], phases=gdm_atoms.ABC, is_closed=[True] * 3,
                  length=gdm_atoms.Distance(1, "meter"), equipment=equipment, feeder=gdm_atoms.feeder(system, "atom"))
    fields.update(changes)
    system.add_component(MatrixImpedanceSwitch(**fields))
    return system


def test_earthing_switch_is_pending_on_the_ground_disconnector_builder():
    equipment = EarthingSwitchEquipment(name="e_eq", ampacity=Current(400, "ampere"), **gdm_atoms._matrices(3))
    with pytest.raises(ValueError, match="EarthingSwitchEquipment x1: pending, the GroundDisconnector builder"):
        gdm_to_cim(_one_switch(equipment=equipment))


def test_switch_out_of_service_raises():
    with pytest.raises(ValueError, match="in_service=False"):
        gdm_to_cim(_one_switch(in_service=False))


def test_parallel_conductors_raise():
    equipment = MatrixImpedanceSwitchEquipment(name="p_eq", ampacity=Current(400, "ampere"), **gdm_atoms._matrices(4))
    system = _one_switch(conductor_phases=[Phase.A, Phase.B, Phase.C, Phase.C], is_closed=[True] * 4,
                         equipment=equipment)
    with pytest.raises(ValueError, match="parallel conductors"):
        gdm_to_cim(system)
