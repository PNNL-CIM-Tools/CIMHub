"""The network shell: Feeders, Substations, BaseVoltages and ConnectivityNodes (tests/atoms/shell)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import bus, network
from gdm.systems.distribution import DistributionSystem
from gdm.systems.distribution.components import DistributionBus, DistributionFeeder, DistributionSubstation
from gdm.systems.distribution.enums import Phase, VoltageTypes
from gdm.quantities import Voltage

from cimhub_gdm import gdm_to_cim


def test_shell_only_matches_golden():
    gdm_atoms.assert_import_matches(gdm_atoms.shell_system(), gdm_atoms.ATOMS / "shell" / "shell_only.cimtbl")


def test_every_golden_master_has_the_shell_header():
    for golden in gdm_atoms.ATOMS.rglob("*.cimtbl"):
        if golden.parent.name in ("prereqs", "e2e"):  # e2e goldens are self-contained, with their own Model
            continue
        settings = "".join(line + "\n" for line in golden.read_text().splitlines()
                           if line.startswith(("Profile", "Authority", "Model")))
        assert settings == gdm_atoms.SHELL_MASTER_HEADER, golden


def test_fields_are_classified():
    check_fields(network.FIELDS_DistributionSubstation, DistributionSubstation)
    check_fields(network.FIELDS_DistributionFeeder, DistributionFeeder)
    check_fields(bus.FIELDS_DistributionBus, DistributionBus)


def _bare_system(name="sys"):
    system = DistributionSystem(name=name, auto_add_composed_components=True)
    system.add_component(DistributionBus(name="b", rated_voltage=Voltage(12.47, "kilovolt"),
                                         voltage_type=VoltageTypes.LINE_TO_LINE, phases=[Phase.A]))
    return system


def test_system_without_feeders_gets_the_system_feeder():
    model = gdm_to_cim(_bare_system())
    assert model.container.mRID == "fdr_sys"
    node = next(iter(model.graph[model.cim.ConnectivityNode].values()))
    assert node.ConnectivityNodeContainer.mRID == "fdr_sys"
    assert node.BaseVoltage.mRID == "bv_12p47kv"


def test_empty_system_name_raises():
    system = _bare_system()
    system.name = None
    with pytest.raises(ValueError, match="DistributionSystem.name is empty"):
        gdm_to_cim(system)


def test_feeder_listed_by_two_substations_raises():
    system = _bare_system()
    feeder = DistributionFeeder(name="f")
    system.add_components(DistributionSubstation(name="s1", feeders=[feeder]),
                          DistributionSubstation(name="s2", feeders=[feeder]))
    with pytest.raises(ValueError, match="listed by substations"):
        gdm_to_cim(system)


def test_bus_out_of_service_raises():
    system = _bare_system()
    system.get_component(DistributionBus, "b").in_service = False
    with pytest.raises(ValueError, match="in_service=False"):
        gdm_to_cim(system)
