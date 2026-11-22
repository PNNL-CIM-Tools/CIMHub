"""Lines and their catalogs → ACLineSegment, PerLengthImpedance, WireConfiguration (tests/atoms/line)."""

import gdm_atoms
import numpy as np
import pytest
from cimhub_core.cimtbl import check_fields
from cimhub_gdm.importer import line, switch
from gdm.systems.distribution.components import GeometryBranch, GeometrySwitch, MatrixImpedanceBranch, SequenceImpedanceBranch
from gdm.systems.distribution.equipment import (
    BareConductorEquipment,
    ConcentricCableEquipment,
    GeometryBranchEquipment,
    MatrixImpedanceBranchEquipment,
    SequenceImpedanceBranchEquipment,
)
from gdm.quantities import Distance

from cimhub_gdm import gdm_to_cim

GUID = "372a4dea-63f2-4737-bc0f-5549c04b3d54"


def _system():
    system = gdm_atoms.shell_system()
    gdm_atoms.add_lines(system)
    return system


def test_lines_match_golden():
    gdm_atoms.assert_import_matches(_system(), gdm_atoms.ATOMS / "line" / "lines.cimtbl")


@pytest.mark.parametrize("fields, cls", [
    (line.FIELDS_MatrixImpedanceBranch, MatrixImpedanceBranch),
    (line.FIELDS_SequenceImpedanceBranch, SequenceImpedanceBranch),
    (line.FIELDS_GeometryBranch, GeometryBranch),
    (switch.FIELDS_GeometrySwitch, GeometrySwitch),
    (line.FIELDS_MatrixImpedanceBranchEquipment, MatrixImpedanceBranchEquipment),
    (line.FIELDS_SequenceImpedanceBranchEquipment, SequenceImpedanceBranchEquipment),
    (line.FIELDS_GeometryBranchEquipment, GeometryBranchEquipment),
    (line.FIELDS_BareConductorEquipment, BareConductorEquipment),
    (line.FIELDS_ConcentricCableEquipment, ConcentricCableEquipment),
])
def test_fields_are_classified(fields, cls):
    check_fields(fields, cls)


def test_radius_is_half_the_diameter_in_its_unit():
    assert line.radius(Distance(0.927, "inch")) == Distance(0.4635, "inch")


def _one_line(equipment, phases=gdm_atoms.ABC, name="l"):
    system = gdm_atoms.shell_system()
    system.add_component(MatrixImpedanceBranch(
        name=name, buses=[gdm_atoms.bus(system, "b1"), gdm_atoms.bus(system, "b2")], phases=phases,
        length=Distance(1, "meter"), equipment=equipment, feeder=gdm_atoms.feeder(system, "atom")))
    return system


def test_asymmetric_matrix_raises():
    r = np.array(gdm_atoms.MTX601_R)
    r[0, 1] += 0.01
    equipment = gdm_atoms.matrix_catalog("bad", r, gdm_atoms.MTX601_X, gdm_atoms.MTX601_C, "mile", 730)
    with pytest.raises(ValueError, match="r_matrix is not symmetric"):
        gdm_to_cim(_one_line(equipment))


def test_geometry_conductor_count_must_match_the_phases():
    system = gdm_atoms.shell_system()
    wire = gdm_atoms.acsr_556()
    geometry = GeometryBranchEquipment(name="two", conductors=[wire, wire],
                                       horizontal_positions=Distance(np.array([0.0, 1.0]), "foot"),
                                       vertical_positions=Distance(np.array([28.0, 28.0]), "foot"))
    system.add_component(GeometryBranch(name="g", buses=[gdm_atoms.bus(system, "b1"), gdm_atoms.bus(system, "b2")],
                                        phases=gdm_atoms.ABC, length=Distance(1, "meter"), equipment=geometry,
                                        feeder=gdm_atoms.feeder(system, "atom")))
    with pytest.raises(ValueError, match="3 phases for 2 conductors"):
        gdm_to_cim(system)


def test_guid_catalog_name_is_rehashed_and_shared_by_its_lines():
    equipment = gdm_atoms.matrix_catalog(GUID, gdm_atoms.MTX601_R, gdm_atoms.MTX601_X, gdm_atoms.MTX601_C, "mile", 730)
    model = gdm_to_cim(_one_line(equipment))
    impedance = model.find_by_mRID("ln_l").WireConfiguration.PerLengthImpedance
    assert impedance.mRID != GUID and not impedance.mRID.startswith("lc_")
    assert impedance.name == GUID
    assert len(impedance.PhaseImpedanceData) == 6  # the lower triangle of the 3x3 matrix



@pytest.mark.parametrize("line_mrid, catalog", [("ln_mtx3", "mtx601"), ("ln_seq", "seq1")])
def test_a_catalog_is_a_template_its_lines_name_through_a_wire_configuration(line_mrid, catalog):
    """DSS-14: a shared catalog is an isTemplate impedance behind a WireConfiguration with no WireSpacing."""
    segment = gdm_to_cim(_system()).find_by_mRID(line_mrid)
    configuration = segment.WireConfiguration
    impedance = configuration.PerLengthImpedance
    assert segment.PerLengthImpedance is None
    assert configuration.mRID == f"lc_{catalog}_wc" and configuration.name == catalog
    assert configuration.WireSpacing is None
    assert impedance.mRID == f"lc_{catalog}" and impedance.isTemplate is True
    assert impedance.WireConfiguration is configuration  # the inverse side
