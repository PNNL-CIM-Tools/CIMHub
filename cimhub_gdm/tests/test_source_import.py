"""DistributionVoltageSource → EnergySource (tests/atoms/source)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import source
from gdm.systems.distribution.components import DistributionVoltageSource
from gdm.systems.distribution.equipment import PhaseVoltageSourceEquipment, VoltageSourceEquipment
from gdm.quantities import Voltage

from cimhub_gdm import gdm_to_cim

GOLDEN = gdm_atoms.ATOMS / "source" / "balanced_3ph.cimtbl"


def _system(angles=(0.0, 120.0, 240.0)):
    system = gdm_atoms.shell_system()
    gdm_atoms.add_source(system, angles)
    return system


def test_balanced_source_matches_golden():
    gdm_atoms.assert_import_matches(_system(), GOLDEN)


def test_opendss_angle_convention_gives_the_same_source():
    gdm_atoms.assert_import_matches(_system((0.0, -120.0, -240.0)), GOLDEN)


def test_wrapped_angles_are_accepted():
    gdm_atoms.assert_import_matches(_system((0.0, 120.0, -120.0)), GOLDEN)


def test_angles_not_120_degrees_apart_raise():
    with pytest.raises(ValueError, match="not 120° apart"):
        gdm_to_cim(_system((0.0, 90.0, 180.0)))


def test_unequal_phase_voltages_raise():
    system = _system()
    phase_b = system.get_component(DistributionVoltageSource, "src").equipment.sources[1]
    phase_b.voltage = Voltage(2.5, "kilovolt")
    with pytest.raises(ValueError, match="voltage differs by phase"):
        gdm_to_cim(system)


def test_fields_are_classified():
    check_fields(source.FIELDS_DistributionVoltageSource, DistributionVoltageSource)
    check_fields(source.FIELDS_VoltageSourceEquipment, VoltageSourceEquipment)
    check_fields(source.FIELDS_PhaseVoltageSourceEquipment, PhaseVoltageSourceEquipment)
