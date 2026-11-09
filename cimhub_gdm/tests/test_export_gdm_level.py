"""The exported system against the atom system it was imported from (EXPORT_PLAN.md §4, the GDM-level check).

Each expected difference is a loss the plan lists:
- CIM holds a line-to-line BaseVoltage, exported line to ground (X6).
- A bus has the phases of its terminals (none when nothing is on it).
- An object has one container.
- A source has one angle (positive sequence) and line-to-line voltages.
- A switch class comes from its CIM class.
- A capacitor's rating, state and controllers are held as CIM holds them.
"""

import cimtables
import gdm_atoms
from cimtables.diff import diff_models
from gdm_compare import gdm_differences

from cimhub_gdm import GdmExporter, gdm_to_cim, read_gdm, write_gdm

LG_FROM_4P16 = "2.40178 kV"  # BaseVoltage 4.16 kV / sqrt(3)
ON_B1_TO_B3 = tuple(f"DistributionBus {bus}.phases: [A, B, C] -> []" for bus in ("b1", "b2", "b3"))

#: CIM keeps one container: a bus's Feeder, so its substation is not exported. A ConnectivityNode has no phases, so a
#: bus with nothing on it has none and is rated LL / sqrt(3), split phase or not. Every bus comes back line to ground.
SHELL_DIFFERENCES = [
    *(f"DistributionBus {bus}.phases: [A, B, C] -> []" for bus in ("b1", "b2", "b3", "b4")),
    *(f"DistributionBus {bus}.substation: atom -> None" for bus in ("b1", "b2", "b3", "b4", "b5")),
    *(f"DistributionBus {bus}.voltage_type: line-to-line -> line-to-ground" for bus in ("b1", "b3", "b4")),
    f"DistributionBus b1.rated_voltage: 4.16 kV -> {LG_FROM_4P16}",
    f"DistributionBus b2.rated_voltage: 2.4018 kV -> {LG_FROM_4P16}",  # rounded to 4.16 kV on import
    f"DistributionBus b3.rated_voltage: 4.16 kV -> {LG_FROM_4P16}",
    "DistributionBus b4.rated_voltage: 0.48 kV -> 0.277128 kV",
    "DistributionBus b5.phases: [S1, S2] -> []",
    "DistributionBus b5.rated_voltage: 0.12 kV -> 0.138564 kV",
]


def _without(lines, *removed):
    return [line for line in lines if line not in removed]


#: The source puts phases on b1. Its phase voltages come back line to line, and its angles in positive sequence
#: (ditto writes +120 degrees per phase, CIM holds only the first).
SOURCE_DIFFERENCES = [
    *_without(SHELL_DIFFERENCES, "DistributionBus b1.phases: [A, B, C] -> []"),
    "DistributionVoltageSource src.equipment.sources[1].angle: 120 deg -> -120 deg",
    "DistributionVoltageSource src.equipment.sources[2].angle: 240 deg -> 120 deg",
    *(f"DistributionVoltageSource src.equipment.sources[{i}].voltage: 2.4018 kV -> 4.16004 kV" for i in range(3)),
    *(f"DistributionVoltageSource src.equipment.sources[{i}].voltage_type: line-to-ground -> line-to-line"
      for i in range(3)),
]

#: The matrix and sequence lines put phases on b1-b3 and come back as they went.
LINE_DIFFERENCES = _without(SHELL_DIFFERENCES, *ON_B1_TO_B3)

#: tie's CIM class is a LoadBreakSwitch, so it comes back a MatrixImpedanceSwitch.
SWITCH_DIFFERENCES = [
    *LINE_DIFFERENCES,
    "MatrixImpedanceSwitch tie: only in the export",
    "SequenceImpedanceSwitch tie: not exported",
]

#: b3 has loads on A and B only. b5's split-phase loads put S1 S2 on it, so its 120 V leg comes back.
LOAD_DIFFERENCES = [
    *_without(SHELL_DIFFERENCES, *ON_B1_TO_B3, "DistributionBus b5.phases: [S1, S2] -> []",
              "DistributionBus b5.rated_voltage: 0.12 kV -> 0.138564 kV"),
    "DistributionBus b3.phases: [A, B, C] -> [A, B]",
]

#: cd is delta on ABC: nomU is line to line. CIM holds one state, the sections in (off's 0), and one control.
CAPACITOR_DIFFERENCES = [
    *LINE_DIFFERENCES,
    "DistributionCapacitor cd.equipment.rated_voltage: 2.4018 kV -> 4.16004 kV",
    "DistributionCapacitor cd.equipment.voltage_type: line-to-ground -> line-to-line",
    "DistributionCapacitor cd.state: [True, True, True] -> [True]",
    "DistributionCapacitor off.equipment.phase_capacitors[0].num_banks_on: 1 -> 0",
    "DistributionCapacitor vc.controllers: [, , ] -> [vc]",
]

X2_FAMILIES = (gdm_atoms.add_source, gdm_atoms.add_switches, gdm_atoms.add_lines, gdm_atoms.add_loads,
               gdm_atoms.add_capacitors)


def _export(system):
    network = gdm_atoms.type_limit_durations(gdm_to_cim(system))
    return GdmExporter().to_model(network, name_source="name", system_name=system.name)


def _system(*families):
    system = gdm_atoms.shell_system()
    for add_family in families:
        add_family(system)
    return gdm_atoms.without_geometry(system)


def test_shell_differences_are_the_listed_losses():
    system = gdm_atoms.shell_system()
    assert gdm_differences(system, _export(system)) == sorted(SHELL_DIFFERENCES)


def test_source_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_source)
    assert gdm_differences(system, _export(system)) == sorted(SOURCE_DIFFERENCES)


def test_switch_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_switches)
    assert gdm_differences(system, _export(system)) == sorted(SWITCH_DIFFERENCES)


def test_line_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_lines)
    assert gdm_differences(system, _export(system)) == sorted(LINE_DIFFERENCES)


def test_load_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_loads)
    assert gdm_differences(system, _export(system)) == sorted(LOAD_DIFFERENCES)


def test_capacitor_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_capacitors)
    assert gdm_differences(system, _export(system)) == sorted(CAPACITOR_DIFFERENCES)


def test_matrix_and_sequence_lines_reimport_unchanged():
    """The CIM fixed point for the lines X2 exports; the line golden also holds geometry (X4)."""
    system = _system(gdm_atoms.add_lines)
    assert diff_models(gdm_to_cim(system), gdm_to_cim(_export(system))) == []


def test_lines_share_one_catalog_per_ampacity():
    network = gdm_atoms.type_limit_durations(gdm_to_cim(_system(gdm_atoms.add_lines)))
    cim = network.cim
    mtx3b = next(line for line in network.graph[cim.ACLineSegment].values() if line.name == "mtx3b")
    [limit] = [value for limit_set in mtx3b.OperationalLimitSet for value in limit_set.OperationalLimitValue]
    limit.normalValue = cim.CurrentFlow(600, "A")
    exported = GdmExporter().to_model(network, name_source="name", system_name="atom")
    by_line = {line.name: (line.equipment.name, float(line.equipment.ampacity.to("ampere").magnitude))
               for line in exported.get_components(gdm_atoms.MatrixImpedanceBranch)}
    assert by_line == {"mtx3": ("mtx601", 730.0), "mtx3b": ("mtx601_2", 600.0), "mtx1": ("mtx1ph", 200.0)}


def test_a_second_export_changes_nothing():
    exported = _export(_system(*X2_FAMILIES))
    assert gdm_differences(exported, _export(exported)) == []


def test_json_round_trip(tmp_path):
    exported = _export(_system(*X2_FAMILIES))
    path = tmp_path / "x2.json"
    write_gdm(exported, str(path))
    assert gdm_differences(exported, read_gdm(str(path))) == []


def test_the_golden_and_the_built_model_export_alike():
    """Exporting the loaded golden and the built model give the same system: the exporter reads only CIM."""
    golden = gdm_atoms.ATOMS / "capacitor" / "capacitors.cimtbl"
    from_golden = GdmExporter().to_model(cimtables.load_model(golden), name_source="name", system_name="atom")
    assert gdm_differences(_export(_system(gdm_atoms.add_capacitors)), from_golden) == []
