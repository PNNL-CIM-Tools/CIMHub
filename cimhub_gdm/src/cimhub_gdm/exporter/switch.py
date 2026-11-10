"""Switching devices → MatrixImpedanceSwitch, Fuse and Recloser (``EXPORT_MAPPING.md#switches``, decision X5).

The importer's decision 14, inverted: the CIM class picks the GDM component and equipment class. A CIM switch is
ideal, so its matrices (OpenDSS's own 1 mΩ switch), length and protection are fills (X4). Each phase's state is its SwitchPhase ``open`` when set,
else the switch's. A normal state that differs from the actual one (or a mixed switch's normal state) becomes a
DistributionSwitchController, the inverse of the importer's rule.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters import describe, required_qty
from cimhub_core.getters.switch_state import get_switch_state
from cimhub_core.getters.terminals import get_conductor_phases, get_terminal_nodes
from cimtables.graph_write import get_qty
from gdm.systems.distribution.common import TimeCurrentCurve
from gdm.systems.distribution.components import MatrixImpedanceFuse, MatrixImpedanceRecloser, MatrixImpedanceSwitch
from gdm.systems.distribution.controllers import DistributionRecloserController, DistributionSwitchController
from gdm.systems.distribution.equipment import (
    CircuitBreakerEquipment,
    DisconnectorEquipment,
    EarthingSwitchEquipment,
    MatrixImpedanceFuseEquipment,
    MatrixImpedanceRecloserEquipment,
    MatrixImpedanceSwitchEquipment,
    RecloserControllerEquipment,
)
from infrasys.quantities import Current

from cimhub_gdm.exporter import fills
from cimhub_gdm.exporter.shared import ExportContext, containers, gdm_phases, in_service
from cimhub_gdm.exporter.slots import UUID, Slot

#: CIM class → (GDM component, GDM equipment); Sectionaliser and Jumper are not here and raise (X5).
SWITCH_CLASSES = {
    cim.LoadBreakSwitch: (MatrixImpedanceSwitch, MatrixImpedanceSwitchEquipment),
    cim.Breaker: (MatrixImpedanceSwitch, CircuitBreakerEquipment),
    cim.Disconnector: (MatrixImpedanceSwitch, DisconnectorEquipment),
    cim.GroundDisconnector: (MatrixImpedanceSwitch, EarthingSwitchEquipment),
    cim.Fuse: (MatrixImpedanceFuse, MatrixImpedanceFuseEquipment),
    cim.Recloser: (MatrixImpedanceRecloser, MatrixImpedanceRecloserEquipment),
}

CIM_CLASSES = tuple(SWITCH_CLASSES)

#: GDM equipment classes that hold a DistributionSwitchController.
WITH_CONTROLLER = (MatrixImpedanceSwitchEquipment, CircuitBreakerEquipment, DisconnectorEquipment,
                   EarthingSwitchEquipment)

NORMAL_STATE = {True: "open", False: "close"}  # normalOpen → normal_state

_SWITCH_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "Names (X2)"),
    "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
    "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
    "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
    "buses": Slot("written", "get_terminal_nodes"),
    "length": Slot("fill", "fills.SWITCH_LENGTH, 1 m: a switch has no length in CIM"),
    "phases": Slot("written", "get_conductor_phases"),
    "is_closed": Slot("rule", "per phase, not get_switch_state(which='actual') of its SwitchPhase when that is set, "
                              "else of the switch"),
    "equipment": Slot("written", "made for this switch; its class from the CIM class (SWITCH_CLASSES)"),
}

_EQUIPMENT_SLOTS = {
    "uuid": UUID,
    "name": Slot("written", "the switch's name (X2)"),
    "construction": Slot("unset", "untranscribed on import: no home on a CIM switch; GDM's default, overhead"),
    "r_matrix": Slot("fill", "fills.switch_matrices, 1 ohm/km diagonal: a CIM switch is ideal, and a zero matrix "
                             "is singular in OpenDSS"),
    "x_matrix": Slot("fill", "fills.switch_matrices, 1 ohm/km diagonal"),
    "c_matrix": Slot("fill", "fills.switch_matrices, zero"),
    "ampacity": Slot("written", "required_qty(ratedCurrent, 'A')"),
}
_CONTROLLER_SLOT = {
    "controller": Slot("rule", "a DistributionSwitchController when normalOpen is set and the switch is mixed or "
                               "its normal state differs from the actual one; else None"),
}

SLOTS = {
    MatrixImpedanceSwitch: _SWITCH_SLOTS | {
        "conductor_phases": Slot("unset", "CIM maps no parallel conductors (importer: must be unset or = phases)"),
    },
    MatrixImpedanceFuse: dict(_SWITCH_SLOTS),
    MatrixImpedanceRecloser: _SWITCH_SLOTS | {
        "controller": Slot("fill", "fills.recloser_controller, <recloser>_ctrl_placeholder: no RecloseSequence in "
                                   "cim18v17 (X5)"),
    },
    MatrixImpedanceSwitchEquipment: _EQUIPMENT_SLOTS | _CONTROLLER_SLOT,
    DisconnectorEquipment: _EQUIPMENT_SLOTS | _CONTROLLER_SLOT,
    EarthingSwitchEquipment: _EQUIPMENT_SLOTS | _CONTROLLER_SLOT,
    CircuitBreakerEquipment: _EQUIPMENT_SLOTS | _CONTROLLER_SLOT | {
        "interrupting_current": Slot("written", "get_qty(breakingCapacity, 'kA'); unset is None"),
        "interrupting_current_unit": Slot("rule", "always kiloampere, the unit interrupting_current is read in"),
        "trip_circuit_count": Slot("unset", "untranscribed on import: no CIM home; GDM's default, 1"),
    },
    MatrixImpedanceRecloserEquipment: dict(_EQUIPMENT_SLOTS),
    MatrixImpedanceFuseEquipment: _EQUIPMENT_SLOTS | {
        "delay": Slot("fill", "fills.FUSE_DELAY, 0 s: no FuseCharacteristicCurve in cim18v17"),
        "tcc_curve": Slot("fill", "fills.fuse_curve, <fuse>_tcc_placeholder: GDM's example curve (X5)"),
    },
    DistributionSwitchController: {
        "uuid": UUID,
        "name": Slot("written", "the switch's name (X2)"),
        "delay": Slot("fill", "fills.SWITCH_CONTROLLER_DELAY, 0 s: no CIM home"),
        "normal_state": Slot("written", "get_switch_state(which='normal'): open → 'open', closed → 'close'"),
        "is_locked": Slot("fill", "fills.SWITCH_CONTROLLER_LOCKED, False: no CIM home"),
    },
    TimeCurrentCurve: {
        "uuid": UUID,
        "name": Slot("written", "<fuse>_tcc_placeholder (X5)"),
        "curve_x": Slot("fill", "TimeCurrentCurve.example()"),
        "curve_y": Slot("fill", "TimeCurrentCurve.example()"),
    },
    DistributionRecloserController: {
        "uuid": UUID,
        "name": Slot("written", "<recloser>_ctrl_placeholder (X5)"),
        **{field: Slot("fill", "DistributionRecloserController.example()")
           for field in ("delay", "ground_delayed", "ground_fast", "phase_delayed", "phase_fast", "num_fast_ops",
                         "num_shots", "reclose_intervals", "reset_time")},
        "equipment": Slot("written", "the example's RecloserControllerEquipment, renamed"),
    },
    RecloserControllerEquipment: {
        "uuid": UUID,
        "name": Slot("written", "<recloser>_ctrl_placeholder, not the example's vendor model (X5)"),
    },
}


def export(switch: cim.Switch, context: ExportContext):
    component_class, equipment_class = SWITCH_CLASSES[type(switch)]
    names = context.names
    phases = get_conductor_phases(switch)
    is_open = phase_states(switch, phases)
    normal_open = None if switch.normalOpen is None else get_switch_state(switch, which="normal")
    mixed = len(set(is_open)) > 1

    equipment = {
        **names.part(switch, equipment_class),
        "ampacity": Current(required_qty(switch, "ratedCurrent", "A"), "ampere"),
        **context.fill(f"{equipment_class.__name__}.r_matrix, x_matrix, c_matrix", fills.switch_matrices(len(phases))),
    }
    if normal_open is not None and (mixed or normal_open != is_open[0]):
        if equipment_class not in WITH_CONTROLLER:
            raise ValueError(f"{describe(switch)}: its normal state differs from its actual one, and GDM "
                             f"{equipment_class.__name__} holds no switch controller")
        equipment["controller"] = DistributionSwitchController(
            **names.part(switch, DistributionSwitchController), normal_state=NORMAL_STATE[normal_open],
            delay=context.fill("DistributionSwitchController.delay", fills.SWITCH_CONTROLLER_DELAY),
            is_locked=context.fill("DistributionSwitchController.is_locked", fills.SWITCH_CONTROLLER_LOCKED))
    if equipment_class is CircuitBreakerEquipment:
        equipment |= {"interrupting_current": get_qty(switch, "breakingCapacity", "kA"),
                      "interrupting_current_unit": "kiloampere"}
    if equipment_class is MatrixImpedanceFuseEquipment:
        equipment |= {
            "delay": context.fill("MatrixImpedanceFuseEquipment.delay", fills.FUSE_DELAY),
            "tcc_curve": context.fill("MatrixImpedanceFuseEquipment.tcc_curve", fills.fuse_curve(
                names.part(switch, TimeCurrentCurve, suffix="_tcc_placeholder"))),
        }

    component = {}
    if component_class is MatrixImpedanceRecloser:
        component["controller"] = context.fill("MatrixImpedanceRecloser.controller", fills.recloser_controller(
            names, switch, suffix="_ctrl_placeholder"))
    node1, node2 = get_terminal_nodes(switch)
    return component_class(
        **names.own(switch),
        buses=[context.gdm(node1), context.gdm(node2)],
        phases=gdm_phases(phases, switch),
        is_closed=[not phase_open for phase_open in is_open],
        length=context.fill(f"{component_class.__name__}.length", fills.SWITCH_LENGTH),
        equipment=equipment_class(**equipment),
        in_service=in_service(switch),
        **component,
        **containers(switch.EquipmentContainer, context),
    )


def phase_states(switch: cim.Switch, phases) -> list[bool]:
    """Whether each conductor is open: its SwitchPhase's ``open`` when set (a mixed switch), else the switch's."""
    children = {child.phaseSide1: child for child in switch.SwitchPhase}
    states = []
    for phase in phases:
        child = children.get(phase)
        holder = child if child is not None and child.open is not None else switch
        states.append(get_switch_state(holder, which="actual"))
    return states

