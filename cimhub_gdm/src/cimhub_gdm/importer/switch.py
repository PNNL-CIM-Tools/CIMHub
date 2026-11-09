"""Switching devices → Switch subclasses; the CIM class comes from the GDM equipment class (OPEN_DECISIONS 14).

A switch has no impedance in CIM, so the equipment's matrices are untranscribed. Per-phase states that differ
become SwitchPhase ``open`` values (GDM_MAPPING.md §6).
"""

from __future__ import annotations

from cimbuilder.object_builder import (BreakerBuilder, DisconnectorBuilder, FuseBuilder, LoadBreakSwitchBuilder,
                                       RecloserBuilder, SwitchPhaseBuilder)
from cimhub_core.cimtbl import Field, lookup, mrid
from cimtables.units import Qty
from gdm.distribution.equipment import (CircuitBreakerEquipment, DisconnectorEquipment, MatrixImpedanceFuseEquipment,
                                        MatrixImpedanceRecloserEquipment, MatrixImpedanceSwitchEquipment,
                                        SequenceImpedanceSwitchEquipment)

from gdm.distribution.enums import Phase

from cimhub_gdm.importer.shared import (PHASE, builder_phases, bus_base_voltage, bus_mrid, container_mrid,
                                        phases_text, qty, require_in_service)

PREFIX = "sw_"

#: GDM equipment class → the builder of its CIM Switch subclass (OPEN_DECISIONS 14).
SWITCH_BUILDER = {
    MatrixImpedanceSwitchEquipment: LoadBreakSwitchBuilder,
    SequenceImpedanceSwitchEquipment: LoadBreakSwitchBuilder,
    CircuitBreakerEquipment: BreakerBuilder,
    DisconnectorEquipment: DisconnectorBuilder,
    MatrixImpedanceFuseEquipment: FuseBuilder,
    MatrixImpedanceRecloserEquipment: RecloserBuilder,
}

_INLINE = "inline: no CIM object of its own"
_NO_IMPEDANCE = "a switch has no impedance in CIM"

_SWITCH_FIELDS = {
    "uuid": Field("structural", note="never the mRID; only rehashed for an empty or clashing name (B18)"),
    "name": Field("copied", (("create", "mRID", None), ("create", "name", None)), note="mRID = sw_ + name"),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "buses": Field("structural", note="node1, node2; BaseVoltage from bus 1 (GDM requires equal bus voltages)"),
    "length": Field("untranscribed", note="a switch has no length in CIM"),
    "phases": Field("structural", note="builder_phases: None for balanced ABC with one state for every phase"),
    "is_closed": Field("structural", note="open = not closed; differing per phase → SwitchPhase open"),
    "equipment": Field("structural", note="its class selects the CIM class (SWITCH_BUILDER); inline"),
}

FIELDS_MatrixImpedanceSwitch = _SWITCH_FIELDS | {
    "conductor_phases": Field("structural", note="parallel conductors are not mapped: must be unset or = phases"),
}
FIELDS_SequenceImpedanceSwitch = dict(_SWITCH_FIELDS)
FIELDS_MatrixImpedanceFuse = dict(_SWITCH_FIELDS)
FIELDS_MatrixImpedanceRecloser = _SWITCH_FIELDS | {
    "controller": Field("untranscribed", note="no RecloseSequence in cim18v17 (OPEN_DECISIONS 12)"),
}

_MATRIX_EQUIPMENT_FIELDS = {
    "uuid": Field("untranscribed", note=_INLINE),
    "name": Field("untranscribed", note=_INLINE),
    "construction": Field("untranscribed", note=_NO_IMPEDANCE),
    "r_matrix": Field("untranscribed", note=_NO_IMPEDANCE),
    "x_matrix": Field("untranscribed", note=_NO_IMPEDANCE),
    "c_matrix": Field("untranscribed", note=_NO_IMPEDANCE),
    "ampacity": Field("copied", (("add_electrical", "ratedCurrent", None),)),
}
_CONTROLLER_FIELD = {"controller": Field("structural", note="DistributionSwitchController.normal_state → normalOpen")}

FIELDS_MatrixImpedanceSwitchEquipment = _MATRIX_EQUIPMENT_FIELDS | _CONTROLLER_FIELD
FIELDS_DisconnectorEquipment = _MATRIX_EQUIPMENT_FIELDS | _CONTROLLER_FIELD
FIELDS_CircuitBreakerEquipment = _MATRIX_EQUIPMENT_FIELDS | _CONTROLLER_FIELD | {
    "interrupting_current": Field("copied", (("add_electrical", "breakingCapacity", None),),
                                  note="in the unit interrupting_current_unit names"),
    "interrupting_current_unit": Field("structural", note="the unit of interrupting_current"),
    "trip_circuit_count": Field("untranscribed", note="no CIM home"),
}
FIELDS_MatrixImpedanceRecloserEquipment = dict(_MATRIX_EQUIPMENT_FIELDS)
FIELDS_MatrixImpedanceFuseEquipment = _MATRIX_EQUIPMENT_FIELDS | {
    "delay": Field("untranscribed", note="no FuseCharacteristicCurve in cim18v17 (OPEN_DECISIONS 12)"),
    "tcc_curve": Field("untranscribed", note="no FuseCharacteristicCurve in cim18v17 (OPEN_DECISIONS 12)"),
}
FIELDS_SequenceImpedanceSwitchEquipment = {
    "uuid": Field("untranscribed", note=_INLINE),
    "name": Field("untranscribed", note=_INLINE),
    "pos_seq_resistance": Field("untranscribed", note=_NO_IMPEDANCE),
    "zero_seq_resistance": Field("untranscribed", note=_NO_IMPEDANCE),
    "pos_seq_reactance": Field("untranscribed", note=_NO_IMPEDANCE),
    "zero_seq_reactance": Field("untranscribed", note=_NO_IMPEDANCE),
    "pos_seq_capacitance": Field("untranscribed", note=_NO_IMPEDANCE),
    "zero_seq_capacitance": Field("untranscribed", note=_NO_IMPEDANCE),
    "ampacity": Field("copied", (("add_electrical", "ratedCurrent", None),)),
} | _CONTROLLER_FIELD

FIELDS_DistributionSwitchController = {
    "uuid": Field("untranscribed", note=_INLINE),
    "name": Field("untranscribed", note=_INLINE),
    "delay": Field("untranscribed", note="no CIM home"),
    "normal_state": Field("mapped", note="'open' → normalOpen true, 'close' → false"),
    "is_locked": Field("untranscribed", note="no CIM home"),
}

NORMAL_OPEN = {"open": True, "close": False}


def add_switch(network, switch, system_name: str) -> None:
    """A Switch subclass between the switch's two buses, with its state and rating."""
    require_in_service(switch)
    equipment = switch.equipment
    builder_cls = lookup(SWITCH_BUILDER, type(equipment), slot="equipment", record_id=switch.name)
    if len(switch.buses) != 2:
        raise ValueError(f"{type(switch).__name__} {switch.name!r}: {len(switch.buses)} buses, expected 2")
    bus1, bus2 = switch.buses  # GDM's own validator requires equal bus voltages across a switch
    conductor_phases = getattr(switch, "conductor_phases", None)
    if conductor_phases is not None and list(conductor_phases) != list(switch.phases):
        raise ValueError(f"{type(switch).__name__} {switch.name!r}: conductor_phases {conductor_phases} differ "
                         f"from phases; parallel conductors are not mapped")
    closed = list(switch.is_closed)
    if len(closed) != len(switch.phases):  # parallel conductors already raised above
        raise ValueError(f"{type(switch).__name__} {switch.name!r}: {len(closed)} is_closed values for "
                         f"{len(switch.phases)} phases")
    mixed = len(set(closed)) > 1

    controller = getattr(equipment, "controller", None)
    if controller is not None:
        normal_open = lookup(NORMAL_OPEN, controller.normal_state, slot="normal_state", record_id=switch.name)
    else:
        normal_open = None if mixed else not closed[0]

    builder = builder_cls(network, network.container)
    cim_switch = builder.create(mRID=mrid(PREFIX, switch.name), name=switch.name)
    _, _, switch_phases = builder.add_connectivity(
        cim_switch,
        node1=bus_mrid(bus1),
        node2=bus_mrid(bus2),
        phases=phases_text(switch.phases) if mixed else builder_phases(switch.phases),
        normalOpen=normal_open,
        EquipmentContainer=container_mrid(switch, system_name),
        BaseVoltage=bus_base_voltage(bus1),
    )
    electrical = {"ratedCurrent": qty(equipment.ampacity)}
    if isinstance(equipment, CircuitBreakerEquipment) and equipment.interrupting_current is not None:
        electrical["breakingCapacity"] = Qty(float(equipment.interrupting_current),
                                             equipment.interrupting_current_unit)
    builder.add_electrical(cim_switch, **electrical)

    if not mixed:
        builder.add_ssh(cim_switch, open=not closed[0])
        return
    phase_builder = SwitchPhaseBuilder(network, network.container)
    by_mrid = {child.mRID: child for child in switch_phases}
    for phase, is_closed in zip(switch.phases, closed):
        token = PHASE[Phase(phase)]
        phase_builder.add_ssh(by_mrid[f"{cim_switch.mRID}_{token}"], open=not is_closed)
