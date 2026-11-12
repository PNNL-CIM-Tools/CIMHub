"""DistributionLoad → EnergyConsumer (tests/atoms/load, OPEN_DECISIONS 13)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import load
from gdm.systems.distribution.components import DistributionLoad
from gdm.systems.distribution.enums import ConnectionType, Phase
from gdm.systems.distribution.equipment import LoadEquipment, PhaseLoadEquipment
from gdm.quantities import ReactivePower

from cimhub_gdm import gdm_to_cim

ABC = gdm_atoms.ABC


def test_loads_match_golden():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_loads(system)
    gdm_atoms.assert_import_matches(system, gdm_atoms.ATOMS / "load" / "loads.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (load.FIELDS_DistributionLoad, DistributionLoad),
    (load.FIELDS_LoadEquipment, LoadEquipment),
    (load.FIELDS_PhaseLoadEquipment, PhaseLoadEquipment),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


@pytest.mark.parametrize("key, expected", [
    (("zip", (0, 0, 1, 0, 0, 1)), "zip_constant_pq"),
    (("zip", (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)), "zip_constant_z"),
    (("zip", (0, 1, 0, 0, 1, 0)), "zip_constant_i"),
    (("zip", (0.4, 0.3, 0.3, 0.5, 0, 0.5)), "zip_0.4_0.3_0.3_0.5_0_0.5"),
    (("exp", (1.0, 2.0)), "exp_1_2"),
])
def test_response_mrid(key, expected):
    assert load.response_mrid(key) == expected


def _system(name, bus, phases, phase_loads, connection=ConnectionType.STAR):
    system = gdm_atoms.shell_system()
    system.add_component(gdm_atoms.load(system, name, bus, phases, phase_loads, connection))
    return system


def test_unmapped_connection_raises():
    system = _system("x", "b1", ABC, [gdm_atoms.phase_load(1, 1) for _ in ABC], ConnectionType.OPEN_DELTA)
    with pytest.raises(ValueError, match="connection_type"):
        gdm_to_cim(system)


def test_load_model_differing_by_phase_raises():
    phase_loads = [gdm_atoms.phase_load(1, 1), gdm_atoms.phase_load(1, 1, gdm_atoms.Z_ONLY), gdm_atoms.phase_load(1, 1)]
    with pytest.raises(ValueError, match="load model differs by phase"):
        gdm_to_cim(_system("x", "b1", ABC, phase_loads))


def test_customers_differing_by_phase_raise():
    phase_loads = [gdm_atoms.phase_load(1, 1, customers=n) for n in (1, 2, 1)]
    with pytest.raises(ValueError, match="num_customers differs by phase"):
        gdm_to_cim(_system("x", "b1", ABC, phase_loads))


def test_unequal_three_phase_delta_raises():
    phase_loads = [gdm_atoms.phase_load(p, 1) for p in (1, 2, 3)]
    with pytest.raises(ValueError, match="3-phase delta load differ"):
        gdm_to_cim(_system("x", "b1", ABC, phase_loads, ConnectionType.DELTA))


def test_reactive_power_in_watts_raises():
    phase_load = gdm_atoms.phase_load(1, 1)
    phase_load.reactive_power = ReactivePower(1, "kilowatt")
    with pytest.raises(ValueError, match="not an reactive power unit"):
        gdm_to_cim(_system("x", "b1", [Phase.A], [phase_load]))
