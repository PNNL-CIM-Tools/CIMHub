"""DistributionReactor → SeriesCompensator (tests/atoms/reactor)."""

import gdm_atoms
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import reactor
from gdm.distribution.components import DistributionReactor
from gdm.distribution.equipment import ReactorEquipment


def reactor_system():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_reactors(system)
    return system


def test_reactors_match_golden():
    gdm_atoms.assert_import_matches(reactor_system(), gdm_atoms.ATOMS / "reactor" / "reactors.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (reactor.FIELDS_DistributionReactor, DistributionReactor),
    (reactor.FIELDS_ReactorEquipment, ReactorEquipment),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)
