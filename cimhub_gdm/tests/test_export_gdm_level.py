"""The exported system against the atom system it was imported from (EXPORT_PLAN.md §4, the GDM-level check).

Each expected difference is a loss the plan lists:
- CIM holds a line-to-line BaseVoltage, exported line to ground (X6).
- A bus has the phases of its terminals (none when nothing is on it).
- An object has one container.
- A source has one angle (positive sequence) and line-to-line voltages.
- A switch class comes from its CIM class (a geometry switch is a LoadBreakSwitch).
- A DER's inverter and panel values with no CIM home are fills, untranscribed on import.
- A capacitor's rating, state and controllers are held as CIM holds them.
- A transformer's taps are its catalog's, and its couplings 0-based (X3, for ditto).
- A regulator is one GDM regulator per CIM unit, and its impedance a fill (X3).
"""

from uuid import uuid4

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

#: The lines put phases on b1-b3 and come back as they went, geometry included. b6 and b7 are their ABCN buses, rated
#: line to ground as every bus. gsw is a LoadBreakSwitch in CIM, so it comes back a MatrixImpedanceSwitch.
LINE_DIFFERENCES = [
    *_without(SHELL_DIFFERENCES, *ON_B1_TO_B3),
    *(line for bus in ("b6", "b7") for line in (f"DistributionBus {bus}.rated_voltage: 4.16 kV -> {LG_FROM_4P16}",
                                                 f"DistributionBus {bus}.substation: atom -> None",
                                                 f"DistributionBus {bus}.voltage_type: line-to-line -> line-to-ground")),
    "GeometrySwitch gsw: not exported",
    "MatrixImpedanceSwitch gsw: only in the export",
]
#: The switches alone: the matrix and sequence lines' differences without b6 and b7.
MATRIX_LINE_DIFFERENCES = _without(SHELL_DIFFERENCES, *ON_B1_TO_B3)

#: tie's CIM class is a LoadBreakSwitch, so it comes back a MatrixImpedanceSwitch.
SWITCH_DIFFERENCES = [
    *MATRIX_LINE_DIFFERENCES,
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
    *MATRIX_LINE_DIFFERENCES,
    "DistributionCapacitor cd.equipment.rated_voltage: 2.4018 kV -> 4.16004 kV",
    "DistributionCapacitor cd.equipment.voltage_type: line-to-ground -> line-to-line",
    "DistributionCapacitor cd.state: [True, True, True] -> [True]",
    "DistributionCapacitor off.equipment.phase_capacitors[0].num_banks_on: 1 -> 0",
    "DistributionCapacitor vc.controllers: [, , ] -> [vc]",
]

#: The transformers put an N on b2, b4 and b5 (t_dy's and t3w's ABCN, the center tap's s1 s2 N) and come back with
#: their taps on the catalog: t_ln's instance tap moves to ln1. ln1's 1-based couplings come back 0-based, and dy's
#: vector group has no neutral mark (CIM holds the connections, not the group).
TRANSFORMER_DIFFERENCES = [
    *_without(SHELL_DIFFERENCES, *(f"DistributionBus {bus}.phases: [A, B, C] -> []" for bus in ("b1", "b2", "b4")),
              "DistributionBus b5.phases: [S1, S2] -> []", "DistributionBus b5.rated_voltage: 0.12 kV -> 0.138564 kV"),
    "DistributionBus b2.phases: [A, B, C] -> [A, B, C, N]",
    "DistributionBus b4.phases: [A, B, C] -> [A, B, C, N]",
    "DistributionBus b5.phases: [S1, S2] -> [S1, S2, N]",
    "DistributionBus b8.rated_voltage: 0.24 kV -> 0.138564 kV",
    "DistributionBus b8.voltage_type: line-to-line -> line-to-ground",
    "DistributionTransformer t_ln.tap_positions[1][0]: 1.025 -> 1.0",
    "DistributionTransformerEquipment ln1.coupling_sequences[0][0]: 1 -> 0",
    "DistributionTransformerEquipment ln1.coupling_sequences[0][1]: 2 -> 1",
    "DistributionTransformerEquipment ln1.windings[1].tap_positions[0]: 1.0 -> 1.025",
    "PowerTransformerEquipment dy.vector_group: Dyn1 -> Dy1",
]

#: Each regulator unit is a GDM regulator: the rb bank comes back as rb_a, rb_b, rb_c, each 1-phase on its share of
#: reg3. CIM holds no regulator impedance, so it is the fill (r 0.01 %, x 0.01 %; reg1666's matched it). The <phase> N
#: ends put an N on b1 and b3.
REGULATOR_DIFFERENCES = [
    *_without(SHELL_DIFFERENCES, *(f"DistributionBus {bus}.phases: [A, B, C] -> []" for bus in ("b1", "b3"))),
    "DistributionBus b1.phases: [A, B, C] -> [A, B, C, N]",
    "DistributionBus b3.phases: [A, B, C] -> [A, B, C, N]",
    "DistributionRegulator rb: not exported",
    *(f"DistributionRegulator rb_{phase}: only in the export" for phase in "abc"),
    "DistributionTransformerEquipment reg1666.pct_full_load_loss: 0.0 -> 0.01",
    "DistributionTransformerEquipment reg3.pct_full_load_loss: 0.0 -> 0.01",
    *(line for winding in (0, 1) for line in (
        f"DistributionTransformerEquipment reg3.windings[{winding}].num_phases: 3 -> 1",
        f"DistributionTransformerEquipment reg3.windings[{winding}].rated_power: 5000 kva -> 1666.67 kva",
        f"DistributionTransformerEquipment reg3.windings[{winding}].resistance: 0.001 -> 0.005",
        f"DistributionTransformerEquipment reg3.windings[{winding}].tap_positions: [1.0, 1.0, 1.0] -> [1.0]")),
]

#: The DER put their phases on b2 (primary on C), b4 and b5. Irradiance and the inverter and panel values CIM has no
#: home for are fills, which the importer leaves untranscribed.
DER_DIFFERENCES = [
    *_without(SHELL_DIFFERENCES, *(f"DistributionBus {bus}.phases: [A, B, C] -> []" for bus in ("b2", "b4")),
              "DistributionBus b5.phases: [S1, S2] -> []", "DistributionBus b5.rated_voltage: 0.12 kV -> 0.138564 kV"),
    "DistributionBus b2.phases: [A, B, C] -> [C]",
]

FAMILIES = (gdm_atoms.add_source, gdm_atoms.add_switches, gdm_atoms.add_lines, gdm_atoms.add_loads,
            gdm_atoms.add_capacitors, gdm_atoms.add_transformers, gdm_atoms.add_regulators, gdm_atoms.add_der)


def _export(system):
    network = gdm_atoms.type_limit_durations(gdm_to_cim(system))
    return GdmExporter().to_model(network, name_source="name", system_name=system.name)


def _system(*families):
    system = gdm_atoms.shell_system()
    for add_family in families:
        add_family(system)
    return system


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


def test_transformer_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_transformers)
    assert gdm_differences(system, _export(system)) == sorted(TRANSFORMER_DIFFERENCES)


def test_regulator_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_regulators)
    assert gdm_differences(system, _export(system)) == sorted(REGULATOR_DIFFERENCES)


def test_der_differences_are_the_listed_losses():
    system = _system(gdm_atoms.add_der)
    assert gdm_differences(system, _export(system)) == sorted(DER_DIFFERENCES)


def test_a_catalog_splits_by_tap():
    """Two transformers on one catalog at different taps: the second tap is <catalog>_2 (X3)."""
    system = _system(gdm_atoms.add_transformers)
    t_ln = system.get_component(gdm_atoms.DistributionTransformer, "t_ln")
    system.add_component(t_ln.model_copy(update={"name": "t_ln2", "uuid": uuid4(), "tap_positions": None}))
    exported = _export(system)
    taps = {name: (exported.get_component(gdm_atoms.DistributionTransformer, name).equipment.name,
                   exported.get_component(gdm_atoms.DistributionTransformer, name).equipment.windings[1].tap_positions)
            for name in ("t_ln", "t_ln2")}
    assert taps == {"t_ln": ("ln1", [1.025]), "t_ln2": ("ln1_2", [1.0])}


def test_lines_reimport_unchanged():
    """The CIM fixed point for every line kind, geometry included."""
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
    exported = _export(_system(*FAMILIES))
    assert gdm_differences(exported, _export(exported)) == []


def test_json_round_trip(tmp_path):
    exported = _export(_system(*FAMILIES))
    path = tmp_path / "export.json"
    write_gdm(exported, str(path))
    assert gdm_differences(exported, read_gdm(str(path))) == []


def test_the_golden_and_the_built_model_export_alike():
    """Exporting the loaded golden and the built model give the same system: the exporter reads only CIM."""
    golden = gdm_atoms.ATOMS / "capacitor" / "capacitors.cimtbl"
    from_golden = GdmExporter().to_model(cimtables.load_model(golden), name_source="name", system_name="atom")
    assert gdm_differences(_export(_system(gdm_atoms.add_capacitors)), from_golden) == []
