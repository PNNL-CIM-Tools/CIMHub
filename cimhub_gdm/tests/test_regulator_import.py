"""DistributionRegulator → VoltageRegulator per phase + RatioTapChanger + TapChangerControl (tests/atoms/regulator)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import regulator
from gdm.systems.distribution.components import DistributionRegulator
from gdm.systems.distribution.controllers import RegulatorController
from gdm.systems.distribution.enums import Phase
from gdm.quantities import Voltage

from cimhub_gdm import gdm_to_cim


def test_regulators_match_golden():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_regulators(system)
    gdm_atoms.assert_import_matches(system, gdm_atoms.ATOMS / "regulator" / "regulators.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (regulator.FIELDS_DistributionRegulator, DistributionRegulator),
    (regulator.FIELDS_RegulatorController, RegulatorController),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


def test_targets_are_on_the_primary_side():
    system = gdm_atoms.shell_system()
    controller = gdm_atoms.regulator_controller(Phase.A, ldc=True, system=system)
    assert regulator.regulator_targets(controller) == (2440.0, 40.0, 2200.0, 2600.0)
    assert regulator.line_drop_ohm(controller.ldc_R, controller).value == pytest.approx(3 * 20 / 700)


def test_line_drop_without_ldc_is_none():
    system = gdm_atoms.shell_system()
    controller = gdm_atoms.regulator_controller(Phase.A, system=system)
    assert regulator.line_drop_ohm(Voltage(3, "volt"), controller) is None


def _regulators(change):
    system = gdm_atoms.shell_system()
    gdm_atoms.add_regulators(system)
    change(system.get_component(DistributionRegulator, "r1"), system)
    return system


def test_swapped_voltage_limits_raise():
    def change(r1, system):
        r1.controllers[0].min_v_limit = Voltage(132, "volt")
        r1.controllers[0].max_v_limit = Voltage(102, "volt")

    with pytest.raises(ValueError, match="min_v_limit .* is above max_v_limit"):
        gdm_to_cim(_regulators(change))


def test_controlled_bus_off_the_regulator_raises():
    def change(r1, system):
        r1.controllers[0].controlled_bus = gdm_atoms.bus(system, "b2")

    with pytest.raises(ValueError, match="controlled_bus 'b2' is not one of its buses"):
        gdm_to_cim(_regulators(change))


def test_controller_on_an_unregulated_phase_raises():
    def change(r1, system):
        r1.controllers[0].controlled_phase = Phase.B

    with pytest.raises(ValueError, match="controllers on \\['B'\\] for regulated phases \\['A'\\]"):
        gdm_to_cim(_regulators(change))
