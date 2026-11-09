"""Small, explicit GDM systems for the atom tests (TEST_DESIGN.md). Nothing here comes from ditto or GDM JSON.

``shell_system()`` holds what ``tests/atoms/prereqs/shell.cimtbl`` describes; each family adds its components to it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from gdm.distribution import DistributionSystem
from gdm.distribution.common import TimeCurrentCurve
from gdm.distribution.components import (DistributionBus, DistributionFeeder, DistributionSubstation,
                                         DistributionVoltageSource, MatrixImpedanceFuse, MatrixImpedanceRecloser,
                                         MatrixImpedanceSwitch, SequenceImpedanceSwitch)
from gdm.distribution.controllers import DistributionRecloserController, DistributionSwitchController
from gdm.distribution.enums import Phase, VoltageTypes
from gdm.distribution.equipment import (CircuitBreakerEquipment, DisconnectorEquipment, MatrixImpedanceFuseEquipment,
                                        MatrixImpedanceRecloserEquipment, MatrixImpedanceSwitchEquipment,
                                        PhaseVoltageSourceEquipment, SequenceImpedanceSwitchEquipment,
                                        VoltageSourceEquipment)
from gdm.quantities import (Angle, CapacitancePULength, Current, Distance, Reactance, ReactancePULength, Resistance,
                            ResistancePULength, Voltage)
from infrasys.quantities import Time

import cimtables
from cimtables.diff import diff_models

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


