"""Small, explicit GDM systems for the atom tests (TEST_DESIGN.md). Nothing here comes from ditto or GDM JSON.

``shell_system()`` holds what ``tests/atoms/prereqs/shell.cimtbl`` describes; each family adds its components to it.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import cimtables
import numpy as np
from cimtables.diff import diff_models
from gdm.distribution import DistributionSystem
from gdm.distribution.common import SequencePair, TimeCurrentCurve
from gdm.distribution.components import (
    DistributionBattery,
    DistributionBus,
    DistributionCapacitor,
    DistributionFeeder,
    DistributionLoad,
    DistributionReactor,
    DistributionRegulator,
    DistributionSolar,
    DistributionSubstation,
    DistributionTransformer,
    DistributionVoltageSource,
    GeometryBranch,
    GeometrySwitch,
    MatrixImpedanceBranch,
    MatrixImpedanceFuse,
    MatrixImpedanceRecloser,
    MatrixImpedanceSwitch,
    SequenceImpedanceBranch,
    SequenceImpedanceSwitch,
)
from gdm.distribution.controllers import (
    ActivePowerCapacitorController,
    CurrentCapacitorController,
    DistributionRecloserController,
    DistributionSwitchController,
    ReactivePowerCapacitorController,
    RegulatorController,
    VoltageCapacitorController,
)
from gdm.distribution.enums import ConnectionType, Phase, VoltageTypes
from gdm.distribution.equipment import (
    BareConductorEquipment,
    BatteryEquipment,
    CapacitorEquipment,
    CircuitBreakerEquipment,
    ConcentricCableEquipment,
    DisconnectorEquipment,
    DistributionTransformerEquipment,
    GeometryBranchEquipment,
    InverterEquipment,
    LoadEquipment,
    MatrixImpedanceBranchEquipment,
    MatrixImpedanceFuseEquipment,
    MatrixImpedanceRecloserEquipment,
    MatrixImpedanceSwitchEquipment,
    PhaseCapacitorEquipment,
    PhaseLoadEquipment,
    PhaseVoltageSourceEquipment,
    PowerTransformerEquipment,
    ReactorEquipment,
    SequenceImpedanceBranchEquipment,
    SequenceImpedanceSwitchEquipment,
    SolarEquipment,
    VoltageSourceEquipment,
    WindingEquipment,
)
from gdm.quantities import (
    ActivePower,
    ApparentPower,
    Angle,
    CapacitancePULength,
    Current,
    Distance,
    EnergyDC,
    Irradiance,
    Reactance,
    ReactancePULength,
    ReactivePower,
    Resistance,
    ResistancePULength,
    Voltage,
)
from infrasys.quantities import Time

from cimhub_gdm import gdm_to_cim

ATOMS = Path(__file__).parent / "atoms"
SHELL_MASTER_HEADER = "Profile = cim18v17\nAuthority = https://github.com/PNNL-CIM-Tools/CIMHub\nModel = atom\n"

ABC = [Phase.A, Phase.B, Phase.C]
LL = VoltageTypes.LINE_TO_LINE
LG = VoltageTypes.LINE_TO_GROUND


def assert_import_matches(system, golden: Path) -> None:
    """Import ``system`` and compare it with the golden master object by object (TEST_DESIGN.md, atom flow)."""
    built = gdm_to_cim(system)
    expected = cimtables.load_model(golden)
    assert diff_models(expected, built) == []


def shell_system():
    """System ``atom``: substation ``atom`` feeding feeders ``atom`` and ``atom2``, and five buses on feeder ``atom``.

    | bus | rated | type | phases | BaseVoltage |
    |---|---|---|---|---|
    | b1 | 4.16 kV | LL | ABC | bv_4p16kv |
    | b2 | 2.4018 kV | LG | ABC | bv_4p16kv (2.4018 × √3 = 4.1600) |
    | b3 | 4.16 kV | LL | ABC | bv_4p16kv |
    | b4 | 0.48 kV | LL | ABC | bv_480v |
    | b5 | 0.12 kV | LG | S1 S2 | bv_240v (split-phase: 0.12 × 2) |
    """
    system = DistributionSystem(name="atom", auto_add_composed_components=True)
    feeder = DistributionFeeder(name="atom")
    feeder2 = DistributionFeeder(name="atom2")
    substation = DistributionSubstation(name="atom", feeders=[feeder, feeder2])
    system.add_components(feeder, feeder2, substation)
    rows = [
        ("b1", Voltage(4.16, "kilovolt"), LL, ABC),
        ("b2", Voltage(2.4018, "kilovolt"), LG, ABC),
        ("b3", Voltage(4.16, "kilovolt"), LL, ABC),
        ("b4", Voltage(0.48, "kilovolt"), LL, ABC),
        ("b5", Voltage(0.12, "kilovolt"), LG, [Phase.S1, Phase.S2]),
    ]
    for name, voltage, voltage_type, phases in rows:
        system.add_component(DistributionBus(name=name, rated_voltage=voltage, voltage_type=voltage_type,
                                             phases=phases, feeder=feeder, substation=substation))
    return system


def bus(system, name: str) -> DistributionBus:
    return system.get_component(DistributionBus, name)


def feeder(system, name: str) -> DistributionFeeder:
    return system.get_component(DistributionFeeder, name)


def phase_source(name: str, angle: float) -> PhaseVoltageSourceEquipment:
    return PhaseVoltageSourceEquipment(name=name, r0=Resistance(0.179604, "ohm"), r1=Resistance(0.160377, "ohm"),
                                       x0=Reactance(0.538811, "ohm"), x1=Reactance(0.641507, "ohm"),
                                       voltage=Voltage(2.4018, "kilovolt"), voltage_type=LG,
                                       angle=Angle(angle, "degree"))


def add_source(system, angles=(0.0, 120.0, 240.0)) -> DistributionVoltageSource:
    """Source ``src`` on b1: 2.4018 kV line-to-ground per phase, ditto-style angles (+120° per phase)."""
    equipment = VoltageSourceEquipment(name="vs", sources=[phase_source(f"vs_{p.value}", a)
                                                           for p, a in zip(ABC, angles)])
    source = DistributionVoltageSource(name="src", bus=bus(system, "b1"), phases=ABC, equipment=equipment,
                                       feeder=feeder(system, "atom"))
    system.add_component(source)
    return source


def _matrices(n: int) -> dict:
    """Per-length matrices of size n; a switch has no impedance in CIM, so the values are never read."""
    return {"r_matrix": ResistancePULength(np.eye(n) * 1e-4, "ohm / meter"),
            "x_matrix": ReactancePULength(np.eye(n) * 1e-4, "ohm / meter"),
            "c_matrix": CapacitancePULength(np.zeros((n, n)), "nanofarad / meter")}


def _sequence_equipment(name: str, ampacity) -> SequenceImpedanceSwitchEquipment:
    r, x, c = ResistancePULength(0.3, "ohm / mile"), ReactancePULength(0.6, "ohm / mile"), CapacitancePULength(
        10, "nanofarad / mile")
    return SequenceImpedanceSwitchEquipment(name=name, pos_seq_resistance=r, zero_seq_resistance=r,
                                            pos_seq_reactance=x, zero_seq_reactance=x, pos_seq_capacitance=c,
                                            zero_seq_capacitance=c, ampacity=ampacity)


def add_switches(system) -> None:
    """One switch of each mapped kind (tests/atoms/switch/switches.cimtbl).

    | name | GDM | buses | phases | state | equipment | CIM |
    |---|---|---|---|---|---|---|
    | lbs | MatrixImpedanceSwitch | b1-b2 | ABC | closed | MatrixImpedanceSwitchEquipment 400 A, controller normal_state=open | LoadBreakSwitch, normalOpen true |
    | brk | MatrixImpedanceSwitch | b2-b3 | ABC | closed | CircuitBreakerEquipment 600 A, 12.5 kiloampere | Breaker |
    | dis | MatrixImpedanceSwitch | b1-b3 | C | open | DisconnectorEquipment 200 A | Disconnector, phases C |
    | fus | MatrixImpedanceFuse | b1-b3 | B | closed | MatrixImpedanceFuseEquipment 65 A | Fuse, phases B |
    | rcl | MatrixImpedanceRecloser | b2-b3 | ABC | closed | MatrixImpedanceRecloserEquipment 300 A | Recloser |
    | tie | SequenceImpedanceSwitch | b1-b2 | ABC | open | SequenceImpedanceSwitchEquipment 400 A, feeder atom2 | LoadBreakSwitch in fdr_atom2 |
    | mix | MatrixImpedanceSwitch | b1-b3 | ABC | A closed, B open, C closed | MatrixImpedanceSwitchEquipment 400 A | LoadBreakSwitch + SwitchPhase |
    """
    atom, atom2 = feeder(system, "atom"), feeder(system, "atom2")
    b1, b2, b3 = bus(system, "b1"), bus(system, "b2"), bus(system, "b3")
    length = Distance(1, "meter")
    opened_normally = DistributionSwitchController(name="", delay=Time(0, "second"), normal_state="open",
                                                   is_locked=False)
    lbs_equipment = MatrixImpedanceSwitchEquipment(name="lbs_eq", ampacity=Current(400, "ampere"),
                                                   controller=opened_normally, **_matrices(3))
    breaker_equipment = CircuitBreakerEquipment(name="brk_eq", ampacity=Current(600, "ampere"),
                                                interrupting_current=12.5, interrupting_current_unit="kiloampere",
                                                **_matrices(3))
    tcc = TimeCurrentCurve(name="", curve_x=Current(np.array([100.0, 1000.0]), "ampere"),
                           curve_y=Time(np.array([1.0, 0.05]), "second"))
    system.add_components(
        MatrixImpedanceSwitch(name="lbs", buses=[b1, b2], phases=ABC, is_closed=[True] * 3, length=length,
                              equipment=lbs_equipment, feeder=atom),
        MatrixImpedanceSwitch(name="brk", buses=[b2, b3], phases=ABC, is_closed=[True] * 3, length=length,
                              equipment=breaker_equipment, feeder=atom),
        MatrixImpedanceSwitch(name="dis", buses=[b1, b3], phases=[Phase.C], is_closed=[False], length=length,
                              equipment=DisconnectorEquipment(name="dis_eq", ampacity=Current(200, "ampere"),
                                                              **_matrices(1)), feeder=atom),
        MatrixImpedanceFuse(name="fus", buses=[b1, b3], phases=[Phase.B], is_closed=[True], length=length,
                            equipment=MatrixImpedanceFuseEquipment(name="fus_eq", ampacity=Current(65, "ampere"),
                                                                   delay=Time(0, "second"), tcc_curve=tcc,
                                                                   **_matrices(1)), feeder=atom),
        MatrixImpedanceRecloser(name="rcl", buses=[b2, b3], phases=ABC, is_closed=[True] * 3, length=length,
                                equipment=MatrixImpedanceRecloserEquipment(name="rcl_eq",
                                                                           ampacity=Current(300, "ampere"),
                                                                           **_matrices(3)),
                                controller=DistributionRecloserController.example(), feeder=atom),
        SequenceImpedanceSwitch(name="tie", buses=[b1, b2], phases=ABC, is_closed=[False] * 3, length=length,
                                equipment=_sequence_equipment("tie_eq", Current(400, "ampere")), feeder=atom2),
        MatrixImpedanceSwitch(name="mix", buses=[b1, b3], phases=ABC, is_closed=[True, False, True], length=length,
                              equipment=MatrixImpedanceSwitchEquipment(name="mix_eq", ampacity=Current(400, "ampere"),
                                                                       **_matrices(3)), feeder=atom),
    )


# --- lines (tests/atoms/line/lines.cimtbl) -------------------------------------------------------------------------

#: IEEE13 configuration 601 (ohm/mile, nF/mile); c's off-diagonals are negative, as a Maxwell matrix's are.
MTX601_R = [[0.3465, 0.1560, 0.1580], [0.1560, 0.3375, 0.1535], [0.1580, 0.1535, 0.3414]]
MTX601_X = [[1.0179, 0.5017, 0.4236], [0.5017, 1.0478, 0.3849], [0.4236, 0.3849, 1.0348]]
MTX601_C = [[16.71, -5.294, -3.341], [-5.294, 15.81, -1.967], [-3.341, -1.967, 14.96]]


def matrix_catalog(name, r, x, c, length_unit, ampacity):
    return MatrixImpedanceBranchEquipment(
        name=name, r_matrix=ResistancePULength(np.array(r), f"ohm / {length_unit}"),
        x_matrix=ReactancePULength(np.array(x), f"ohm / {length_unit}"),
        c_matrix=CapacitancePULength(np.array(c), f"nanofarad / {length_unit}"), ampacity=Current(ampacity, "ampere"))


def acsr_556():
    return BareConductorEquipment(name="acsr_556", conductor_diameter=Distance(0.927, "inch"),
                                  conductor_gmr=Distance(0.0313, "foot"), ampacity=Current(730, "ampere"),
                                  emergency_ampacity=Current(1095, "ampere"),
                                  ac_resistance=ResistancePULength(0.1859, "ohm / mile"),
                                  dc_resistance=ResistancePULength(0.1803, "ohm / mile"))


def acsr_4_0():
    return BareConductorEquipment(name="acsr_4/0", conductor_diameter=Distance(0.563, "inch"),
                                  conductor_gmr=Distance(0.00814, "foot"), ampacity=Current(340, "ampere"),
                                  emergency_ampacity=Current(510, "ampere"),
                                  ac_resistance=ResistancePULength(0.592, "ohm / mile"),
                                  dc_resistance=ResistancePULength(0.556, "ohm / mile"))


def cn_250():
    return ConcentricCableEquipment(
        name="cn_250", strand_diameter=Distance(0.0641, "inch"), conductor_diameter=Distance(0.567, "inch"),
        cable_diameter=Distance(1.29, "inch"), insulation_thickness=Distance(0.22, "inch"),
        insulation_diameter=Distance(1.06, "inch"), ampacity=Current(260, "ampere"),
        conductor_gmr=Distance(0.0171, "foot"), strand_gmr=Distance(0.00208, "foot"),
        phase_ac_resistance=ResistancePULength(0.41, "ohm / mile"),
        strand_ac_resistance=ResistancePULength(14.8722, "ohm / mile"), num_neutral_strands=13,
        rated_voltage=Voltage(15, "kilovolt"))


def add_lines(system) -> None:
    """One line of each kind (tests/atoms/line/lines.cimtbl).

    | name | GDM | buses | phases | catalog | length |
    |---|---|---|---|---|---|
    | mtx3 | MatrixImpedanceBranch | b1-b2 | ABC | mtx601 (3x3, ohm/mile) | 2000 ft |
    | mtx3b | MatrixImpedanceBranch | b2-b3 | CAB | mtx601 again: built once | 500 ft |
    | mtx1 | MatrixImpedanceBranch | b2-b3 | C | mtx1ph (1x1, ohm/km) | 0.3 km |
    | seq | SequenceImpedanceBranch | b1-b3 | ABC | seq1 (ohm/km, nF/km) | 1 km |
    | geo | GeometryBranch | b6-b7 | ABCN | g601: acsr_556 x3 + acsr_4/0 | 300 m |
    | ug | GeometryBranch | b1-b2 | ABC | ug3: cn_250 x3 | 100 ft |
    | gsw | GeometrySwitch | b6-b7 | ABC, closed | g601 | 1 m |

    b6 and b7 are 4.16 kV line-to-line ABCN buses (a neutral conductor needs a bus with N).
    """
    atom = feeder(system, "atom")
    b1, b2, b3 = bus(system, "b1"), bus(system, "b2"), bus(system, "b3")
    b6, b7 = (DistributionBus(name=name, rated_voltage=Voltage(4.16, "kilovolt"), voltage_type=LL,
                              phases=ABC + [Phase.N], feeder=atom, substation=system.get_component(
                                  DistributionSubstation, "atom")) for name in ("b6", "b7"))
    mtx601 = matrix_catalog("mtx601", MTX601_R, MTX601_X, MTX601_C, "mile", 730)
    mtx1ph = matrix_catalog("mtx1ph", [[0.5]], [[0.9]], [[3.4]], "kilometer", 200)
    seq1 = SequenceImpedanceBranchEquipment(
        name="seq1", pos_seq_resistance=ResistancePULength(0.3, "ohm / kilometer"),
        zero_seq_resistance=ResistancePULength(0.6, "ohm / kilometer"),
        pos_seq_reactance=ReactancePULength(0.6, "ohm / kilometer"),
        zero_seq_reactance=ReactancePULength(1.8, "ohm / kilometer"),
        pos_seq_capacitance=CapacitancePULength(10, "nanofarad / kilometer"),
        zero_seq_capacitance=CapacitancePULength(4, "nanofarad / kilometer"), ampacity=Current(400, "ampere"))
    overhead, neutral, cable = acsr_556(), acsr_4_0(), cn_250()
    g601 = GeometryBranchEquipment(name="g601", conductors=[overhead, overhead, overhead, neutral],
                                   horizontal_positions=Distance(np.array([0.0, 2.5, 7.0, 4.0]), "foot"),
                                   vertical_positions=Distance(np.array([28.0, 28.0, 28.0, 24.0]), "foot"))
    ug3 = GeometryBranchEquipment(name="ug3", conductors=[cable, cable, cable],
                                  horizontal_positions=Distance(np.array([-0.5, 0.0, 0.5]), "foot"),
                                  vertical_positions=Distance(np.array([-4.0, -4.0, -4.0]), "foot"))
    system.add_components(
        MatrixImpedanceBranch(name="mtx3", buses=[b1, b2], phases=ABC, length=Distance(2000, "foot"),
                              equipment=mtx601, feeder=atom),
        MatrixImpedanceBranch(name="mtx3b", buses=[b2, b3], phases=[Phase.C, Phase.A, Phase.B],
                              length=Distance(500, "foot"), equipment=mtx601, feeder=atom),
        MatrixImpedanceBranch(name="mtx1", buses=[b2, b3], phases=[Phase.C], length=Distance(0.3, "kilometer"),
                              equipment=mtx1ph, feeder=atom),
        SequenceImpedanceBranch(name="seq", buses=[b1, b3], phases=ABC, length=Distance(1, "kilometer"),
                                equipment=seq1, feeder=atom),
        b6, b7,
        GeometryBranch(name="geo", buses=[b6, b7], phases=ABC + [Phase.N], length=Distance(300, "meter"),
                       equipment=g601, feeder=atom),
        GeometryBranch(name="ug", buses=[b1, b2], phases=ABC, length=Distance(100, "foot"), equipment=ug3,
                       feeder=atom),
        GeometrySwitch(name="gsw", buses=[b6, b7], phases=ABC, is_closed=[True] * 3,
                       length=Distance(1, "meter"), equipment=g601, feeder=atom),
    )


# --- loads (tests/atoms/load/loads.cimtbl) -------------------------------------------------------------------------

def phase_load(p_kw, q_kvar, zip_fractions=(0, 0, 1, 0, 0, 1), exponents=(None, None), customers=None):
    """A PhaseLoadEquipment: ``zip_fractions`` is (pZ, pI, pP, qZ, qI, qP)."""
    z_real, i_real, p_real, z_imag, i_imag, p_imag = zip_fractions
    return PhaseLoadEquipment(name="", real_power=ActivePower(p_kw, "kilowatt"),
                              reactive_power=ReactivePower(q_kvar, "kilovar"),
                              z_real=z_real, i_real=i_real, p_real=p_real, z_imag=z_imag, i_imag=i_imag,
                              p_imag=p_imag, num_customers=customers, active_power_voltage_exponent=exponents[0],
                              reactive_power_voltage_exponent=exponents[1])


def load(system, name, bus_name, phases, phase_loads, connection=ConnectionType.STAR) -> DistributionLoad:
    return DistributionLoad(name=name, bus=bus(system, bus_name), phases=phases,
                            equipment=LoadEquipment(name=f"{name}_eq", phase_loads=phase_loads,
                                                    connection_type=connection),
                            feeder=feeder(system, "atom"))


Z_ONLY, I_ONLY = (1, 0, 0, 1, 0, 0), (0, 1, 0, 0, 1, 0)


def add_loads(system) -> None:
    """One load of each phase and model form (tests/atoms/load/loads.cimtbl).

    | name | bus | phases | conn | per phase (kW, kvar) | model | CIM |
    |---|---|---|---|---|---|---|
    | bal | b1 | ABC | wye | 100, 50 each; 1 customer | constant PQ | totals, no phases |
    | unbal | b2 | ABC | wye | A 100, 50; B 200, 80; C 50, 20 | constant Z | totals + per-phase p, q |
    | one | b3 | B | wye | 50, 25 | constant I | phases B, no per-phase values |
    | tpx | b5 | S1 S2 | wye | 2.5, 1 each | constant PQ | phases s1s2 |
    | leg | b5 | S2 | wye | 2, 0.5; 3 customers | constant PQ | phases s2 |
    | dbc | b1 | B C | delta | 85, 40 each | constant PQ | one branch child ld_dbc_BC |
    | zip | b2 | ABC | wye | 100, 40 each | ZIP 0.4 0.3 0.3 / 0.5 0 0.5 | its own zip_ row |
    | cvr | b3 | A | wye | 100, 30 | exponents 0.8, 3 | exp_0.8_3 |
    """
    zip_fractions = (0.4, 0.3, 0.3, 0.5, 0, 0.5)
    system.add_components(
        load(system, "bal", "b1", ABC, [phase_load(100, 50, customers=1) for _ in ABC]),
        load(system, "unbal", "b2", ABC, [phase_load(100, 50, Z_ONLY), phase_load(200, 80, Z_ONLY),
                                          phase_load(50, 20, Z_ONLY)]),
        load(system, "one", "b3", [Phase.B], [phase_load(50, 25, I_ONLY)]),
        load(system, "tpx", "b5", [Phase.S1, Phase.S2], [phase_load(2.5, 1), phase_load(2.5, 1)]),
        load(system, "leg", "b5", [Phase.S2], [phase_load(2, 0.5, customers=3)]),
        load(system, "dbc", "b1", [Phase.B, Phase.C], [phase_load(85, 40), phase_load(85, 40)], ConnectionType.DELTA),
        load(system, "zip", "b2", ABC, [phase_load(100, 40, zip_fractions) for _ in ABC]),
        load(system, "cvr", "b3", [Phase.A], [phase_load(100, 30, exponents=(0.8, 3.0))]),
    )


# --- capacitors (tests/atoms/capacitor/capacitors.cimtbl) ----------------------------------------------------------

def capacitor(system, name, bus_name, phases, kvar, rated_voltage, voltage_type, *, banks=1, banks_on=1,
              connection=ConnectionType.STAR, state=(True,), controllers=()) -> DistributionCapacitor:
    """A capacitor with ``kvar`` on each phase."""
    equipment = CapacitorEquipment(
        name=f"{name}_eq", connection_type=connection, rated_voltage=Voltage(rated_voltage, "kilovolt"),
        voltage_type=voltage_type,
        phase_capacitors=[PhaseCapacitorEquipment(name="", rated_reactive_power=ReactivePower(kvar, "kilovar"),
                                                  num_banks=banks, num_banks_on=banks_on) for _ in phases])
    return DistributionCapacitor(name=name, bus=bus(system, bus_name), phases=phases, equipment=equipment,
                                 state=list(state), controllers=list(controllers), feeder=feeder(system, "atom"))


def add_capacitors(system) -> None:
    """Fixed and controlled capacitors (tests/atoms/capacitor/capacitors.cimtbl).

    | name | bus | phases | per phase | rating | banks (on) | state | controller |
    |---|---|---|---|---|---|---|---|
    | c3 | b1 | ABC | 200 kvar | 4.16 kV LL, wye | 1 (1) | on | none |
    | c1 | b2 | C | 100 kvar | 2.4 kV LG, wye | 1 (1) | on | none |
    | cd | b3 | ABC | 100 kvar | 2.4018 kV LG, delta | 2 (1) | on, per phase | none |
    | off | b1 | A | 50 kvar | 2.4 kV LG, wye | 1 (1) | off | none |
    | vc | b2 | ABC | 300 kvar | 4.16 kV LL | 1 (1) | on | voltage 115-125 V, PT 20, delay 15 s, one per phase |
    | qc | b3 | ABC | 200 kvar | 4.16 kV LL | 1 (1) | on | reactive power 150-225 kvar (GDM requires > 0) |
    | ic | b1 | ABC | 100 kvar | 4.16 kV LL | 1 (1) | on | current 50-100 A, CT 60 |
    | pc | b2 | ABC | 100 kvar | 4.16 kV LL | 1 (1) | on | active power 500-1000 kW |
    """
    def voltage_controller():
        return VoltageCapacitorController(on_voltage=Voltage(115, "volt"), off_voltage=Voltage(125, "volt"),
                                          pt_ratio=20, delay_on=Time(15, "second"), delay_off=Time(30, "second"))

    system.add_components(
        capacitor(system, "c3", "b1", ABC, 200, 4.16, LL),
        capacitor(system, "c1", "b2", [Phase.C], 100, 2.4, LG),
        capacitor(system, "cd", "b3", ABC, 100, 2.4018, LG, banks=2, connection=ConnectionType.DELTA,
                  state=(True, True, True)),
        capacitor(system, "off", "b1", [Phase.A], 50, 2.4, LG, state=(False,)),
        capacitor(system, "vc", "b2", ABC, 300, 4.16, LL, controllers=[voltage_controller() for _ in ABC]),
        capacitor(system, "qc", "b3", ABC, 200, 4.16, LL, controllers=[ReactivePowerCapacitorController(
            on_power=ReactivePower(150, "kilovar"), off_power=ReactivePower(225, "kilovar"))]),
        capacitor(system, "ic", "b1", ABC, 100, 4.16, LL, controllers=[CurrentCapacitorController(
            on_current=Current(50, "ampere"), off_current=Current(100, "ampere"), ct_ratio=60)]),
        capacitor(system, "pc", "b2", ABC, 100, 4.16, LL, controllers=[ActivePowerCapacitorController(
            on_power=ActivePower(500, "kilowatt"), off_power=ActivePower(1000, "kilowatt"))]),
    )


def winding(kv, voltage_type, kva, r_pct, connection=ConnectionType.STAR, phases=3, taps=None, grounded=False):
    """A WindingEquipment: 32 taps over 0.9-1.1 pu, ``taps`` per phase (default nominal), ungrounded unless asked."""
    return WindingEquipment(name="", resistance=r_pct, is_grounded=grounded, rated_voltage=Voltage(kv, "kilovolt"),
                            voltage_type=voltage_type, rated_power=ApparentPower(kva, "kilova"), num_phases=phases,
                            connection_type=connection, tap_positions=taps or [1.0] * phases, total_taps=32,
                            min_tap_pu=0.9, max_tap_pu=1.1)


def transformer_catalog(name, windings, pairs, reactances, *, no_load=0.0, full_load=0.0, magnetizing=None,
                        center_tap=False, cls=DistributionTransformerEquipment, **extra):
    return cls(name=name, mounting="POLE_MOUNT", pct_no_load_loss=no_load, pct_full_load_loss=full_load,
               windings=windings, coupling_sequences=[SequencePair(from_index=i, to_index=j) for i, j in pairs],
               winding_reactances=reactances, is_center_tapped=center_tap, magnetizing_current_pct=magnetizing,
               **extra)


def add_transformers(system) -> None:
    """One transformer of each catalog shape (GDM_MAPPING.md §18), ditto-style ratings (line-to-ground on a wye):

    | instance | catalog | windings (g = is_grounded) | buses, phases | taps |
    |---|---|---|---|---|
    | t_dy | dy (PowerTransformerEquipment, Dyn1, ONAN) | 75 kVA D 4.16 kV LL / Y g 0.27713 kV LG | b1 ABC, b4 ABCN | |
    | t3w | yyd | 1000 kVA Y 2.4018 LG / Y 0.27713 LG / D 0.24 LL | b2 ABC, b4 ABCN, b8 ABC | catalog winding 2 1.0125 |
    | t_ln | ln1 (1-based couplings) | 50 kVA Y g 2.4018 LG / Y g 0.27713 LG | b2 B, b4 B | instance winding 2 1.025 |
    | t_ll | ll1 | 100 kVA D 4.16 LL / D 0.48 LL | b1 AB, b4 AB | |
    | t_ct | ct25 (center tap) | 25 kVA Y g 2.4018 LG / g 0.12 / g 0.12 | b2 C, b5 S1 N, b5 N S2 | |
    """
    tertiary = DistributionBus(name="b8", rated_voltage=Voltage(0.24, "kilovolt"), voltage_type=LL, phases=ABC,
                              feeder=feeder(system, "atom"))
    system.add_component(tertiary)
    fdr = feeder(system, "atom")
    dy = transformer_catalog("dy", [winding(4.16, LL, 75, 0.87204, ConnectionType.DELTA),
                                    winding(0.27713, LG, 75, 0.87204, grounded=True)], [(0, 1)], [3.24],
                             no_load=0.6, full_load=1.74408, cls=PowerTransformerEquipment, vector_group="Dyn1",
                             cooling_class="ONAN", fluid_type="mineral_oil")
    yyd = transformer_catalog("yyd", [winding(2.4018, LG, 1000, 0.2),
                                      winding(0.27713, LG, 1000, 0.3, taps=[1.0125] * 3),
                                      winding(0.24, LL, 1000, 0.4, ConnectionType.DELTA)],
                              [(0, 1), (0, 2), (1, 2)], [6.0, 4.0, 3.0], no_load=0.1, full_load=0.5)
    ln1 = transformer_catalog("ln1", [winding(2.4018, LG, 50, 0.5, phases=1, grounded=True),
                                      winding(0.27713, LG, 50, 0.5, phases=1, grounded=True)],
                              [(1, 2)], [2.0], no_load=0.2, full_load=1.0)
    ll1 = transformer_catalog("ll1", [winding(4.16, LL, 100, 0.4, ConnectionType.DELTA, phases=1),
                                      winding(0.48, LL, 100, 0.4, ConnectionType.DELTA, phases=1)],
                              [(0, 1)], [2.5], full_load=0.8)
    ct25 = transformer_catalog("ct25", [winding(2.4018, LG, 25, 0.6, phases=1, grounded=True),
                                        winding(0.12, LG, 25, 1.2, phases=1, grounded=True),
                                        winding(0.12, LG, 25, 1.2, phases=1, grounded=True)],
                               [(0, 1), (0, 2), (1, 2)], [2.04, 2.04, 1.36], no_load=0.2, full_load=1.8,
                               magnetizing=0.5, center_tap=True)
    b = {name: bus(system, name) for name in ("b1", "b2", "b4", "b5", "b8")}
    rows = [
        ("t_dy", dy, ["b1", "b4"], [ABC, ABC + [Phase.N]], None),
        ("t3w", yyd, ["b2", "b4", "b8"], [ABC, ABC + [Phase.N], ABC], None),
        ("t_ln", ln1, ["b2", "b4"], [[Phase.B], [Phase.B]], [[1.0], [1.025]]),
        ("t_ll", ll1, ["b1", "b4"], [[Phase.A, Phase.B], [Phase.A, Phase.B]], None),
        ("t_ct", ct25, ["b2", "b5", "b5"], [[Phase.C], [Phase.S1, Phase.N], [Phase.N, Phase.S2]], None),
    ]
    for name, catalog, buses, phases, taps in rows:
        system.add_component(DistributionTransformer(name=name, buses=[b[n] for n in buses], winding_phases=phases,
                                                     tap_positions=taps, equipment=catalog, feeder=fdr))


def regulator_controller(phase, *, ldc=False, bus_name="b3", system=None):
    """A RegulatorController on the L side (winding 2): 122 V band 2 V on a PT of 20, limits 110-130 V."""
    return RegulatorController(
        name="", tapped_winding=2, delay=Time(30, "second"), v_setpoint=Voltage(122, "volt"),
        min_v_limit=Voltage(110, "volt"), max_v_limit=Voltage(130, "volt"), pt_ratio=20.0, use_ldc=ldc,
        is_reversible=False, ldc_R=Voltage(3, "volt") if ldc else None, ldc_X=Voltage(9, "volt") if ldc else None,
        ct_primary=Current(700, "ampere"), max_step=16, bandwidth=Voltage(2, "volt"),
        controlled_bus=bus(system, bus_name), controlled_phase=phase)


def add_regulators(system) -> None:
    """r1: one phase (A), line drop compensation, tap 1.0125 (step 2); rb: a bank of three, one controller each,
    taps 1.00625 / 1.0125 / 1.0 (steps 1, 2, 0). Both b1 → b3; GDM requires one controller per phase."""
    fdr = feeder(system, "atom")
    reg1666 = transformer_catalog("reg1666", [winding(2.4018, LG, 1666, 0.005, phases=1),
                                              winding(2.4018, LG, 1666, 0.005, phases=1)], [(0, 1)], [0.01])
    reg3 = transformer_catalog("reg3", [winding(2.4018, LG, 5000, 0.001), winding(2.4018, LG, 5000, 0.001)],
                               [(0, 1)], [0.01])
    buses = [bus(system, "b1"), bus(system, "b3")]
    rows = [
        ("r1", reg1666, [[Phase.A], [Phase.A]], [[1.0], [1.0125]],
         [regulator_controller(Phase.A, ldc=True, system=system)]),
        ("rb", reg3, [ABC, ABC], [[1.0] * 3, [1.00625, 1.0125, 1.0]],
         [regulator_controller(p, system=system) for p in ABC]),
    ]
    for name, catalog, phases, taps, controllers in rows:
        system.add_component(DistributionRegulator(name=name, buses=buses, winding_phases=phases, tap_positions=taps,
                                                   equipment=catalog, controllers=controllers, feeder=fdr))


def inverter(name: str, kva: float, **identity) -> InverterEquipment:
    """An inverter: only rated_apparent_power has a CIM home; the rest is untranscribed."""
    return InverterEquipment(name=name, **identity, rated_apparent_power=ApparentPower(kva, "kilova"), rise_limit=None,
                             fall_limit=None, cutout_percent=10, cutin_percent=10, dc_to_ac_efficiency=98)


#: The house PV's unnamed inverter: a fixed uuid, so its rehashed mRID (B18) is stable.
UNNAMED_INVERTER = UUID("00000000-0000-4000-8000-000000000006")


def add_der(system) -> None:
    """PV: roof and roof2 (3-phase on b4, sharing inverter inv33), house (split-phase on b5, an unnamed inverter),
    primary (phase C on b2, absorbing vars). Batteries: ess (3-phase on b4, discharging), home (split-phase on b5,
    charging)."""
    fdr = feeder(system, "atom")
    inv33 = inverter("inv33", 33)
    panel30 = SolarEquipment(name="panel30", rated_power=ActivePower(30, "kilowatt"), resistance=0.5, reactance=5,
                             rated_voltage=Voltage(0.48, "kilovolt"), voltage_type=LL)
    pv_rows = [
        ("roof", "b4", ABC, panel30, inv33, 25, 2),
        ("roof2", "b4", ABC, panel30, inv33, 30, 0),
        ("house", "b5", [Phase.S1, Phase.S2],
         SolarEquipment(name="panel5", rated_power=ActivePower(5, "kilowatt"), resistance=0.5, reactance=5,
                        rated_voltage=Voltage(0.12, "kilovolt"), voltage_type=LG),
         inverter("", 6, uuid=UNNAMED_INVERTER), 4, 0),
        ("primary", "b2", [Phase.C],
         SolarEquipment(name="panel120", rated_power=ActivePower(120, "kilowatt"), resistance=0.5, reactance=5,
                        rated_voltage=Voltage(2.4018, "kilovolt"), voltage_type=LG), inverter("inv120", 120), 100, -10),
    ]
    for name, bus_name, phases, equipment, inv, p_kw, q_kvar in pv_rows:
        system.add_component(DistributionSolar(
            name=name, bus=bus(system, bus_name), phases=phases, irradiance=Irradiance(0.9, "kilowatt/meter**2"),
            active_power=ActivePower(p_kw, "kilowatt"), reactive_power=ReactivePower(q_kvar, "kilovar"),
            inverter=inv, equipment=equipment, feeder=fdr))
    battery_rows = [
        ("ess", "b4", ABC, BatteryEquipment(name="bess500", rated_energy=EnergyDC(500, "kilowatthour"),
                                            rated_power=ActivePower(250, "kilowatt"), charging_efficiency=95,
                                            discharging_efficiency=94, idling_efficiency=99,
                                            rated_voltage=Voltage(0.48, "kilovolt"), voltage_type=LL),
         inverter("inv250", 250), 150),
        ("home", "b5", [Phase.S1, Phase.S2], BatteryEquipment(name="pw13", rated_energy=EnergyDC(13.5, "kilowatthour"),
                                                              rated_power=ActivePower(5, "kilowatt"),
                                                              charging_efficiency=90, discharging_efficiency=90,
                                                              idling_efficiency=99,
                                                              rated_voltage=Voltage(0.12, "kilovolt"),
                                                              voltage_type=LG),
         inverter("inv5", 5), -3),
    ]
    for name, bus_name, phases, equipment, inv, p_kw in battery_rows:
        system.add_component(DistributionBattery(
            name=name, bus=bus(system, bus_name), phases=phases, active_power=ActivePower(p_kw, "kilowatt"),
            reactive_power=ReactivePower(0, "kilovar"), inverter=inv, equipment=equipment, feeder=fdr))


def add_reactors(system) -> None:
    """rx3: 3-phase b1 → b3 (no Terminal phases); r1: phase B b1 → b3. length has no CIM home."""
    fdr = feeder(system, "atom")
    rows = [("rx3", ABC, 0.0, 14.8), ("r1", [Phase.B], 0.5, 2.0)]
    for name, phases, r_ohm, x_ohm in rows:
        system.add_component(DistributionReactor(
            name=name, buses=[bus(system, "b1"), bus(system, "b3")], length=Distance(1, "meter"), phases=phases,
            equipment=ReactorEquipment(name=f"{name}_eq", resistance=Resistance(r_ohm, "ohm"),
                                       reactance=Reactance(x_ohm, "ohm")),
            feeder=fdr))
