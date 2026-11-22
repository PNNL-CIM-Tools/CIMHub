"""EnergyConsumer → DistributionLoad (``EXPORT_MAPPING.md#loads``, decision X7).

GDM holds a load per phase: each phase gets its EnergyConsumerPhase p and q, else the total split evenly over the
phase conductors (``get_phase_loads``). Every phase gets the one LoadResponseCharacteristic: ZIP fractions as
stored, or voltage exponents with the constant-power fill for the fractions GDM still requires.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimhub_core.getters.load import get_load_response, get_phase_loads
from cimhub_core.getters.terminals import get_terminal_nodes
from gdm.quantities import ActivePower, ReactivePower
from gdm.systems.distribution.components import DistributionLoad
from gdm.systems.distribution.equipment import LoadEquipment, PhaseLoadEquipment

from cimhub_gdm.exporter import fills
from cimhub_gdm.exporter.shared import ExportContext, connection_type, containers, gdm_phases, in_service
from cimhub_gdm.exporter.slots import UUID, Slot

CIM_CLASSES = (cim.EnergyConsumer, cim.ConformLoad, cim.NonConformLoad)  # group schedules: time_series.py

_ZIP = "get_load_response, ZIP form; the exponent form writes fills.ZIP_UNDER_EXPONENTS (constant power)"
_UNTRANSCRIBED = "untranscribed on import: no home on LoadResponseCharacteristic"

SLOTS = {
    DistributionLoad: {
        "uuid": UUID,
        "name": Slot("written", "Names (X2)"),
        "substation": Slot("written", "the EquipmentContainer when it is a Substation or VoltageLevel (containers)"),
        "feeder": Slot("written", "the EquipmentContainer when it is a Feeder (containers)"),
        "in_service": Slot("rule", "get_in_service(which='actual'); unset is in service, GDM's default"),
        "bus": Slot("written", "the bus of get_terminal_nodes"),
        "phases": Slot("written", "get_phase_loads.phases: the phase conductors, no neutral"),
        "equipment": Slot("written", "a LoadEquipment made for this load"),
    },
    LoadEquipment: {
        "uuid": UUID,
        "name": Slot("written", "the load's name (X2)"),
        "phase_loads": Slot("written", "one PhaseLoadEquipment per phase conductor"),
        "connection_type": Slot("written", "phaseConnection: Y and Yn → STAR, D → DELTA; others raise"),
    },
    PhaseLoadEquipment: {
        "uuid": UUID,
        "name": Slot("written", "<load>_<phase> (X2)"),
        "real_power": Slot("written", "get_phase_loads.per_phase p (kW): EnergyConsumerPhase, else the even split"),
        "reactive_power": Slot("written", "get_phase_loads.per_phase q (kVAr)"),
        "z_real": Slot("written", f"pConstantImpedance ({_ZIP})"),
        "z_imag": Slot("written", "qConstantImpedance"),
        "i_real": Slot("written", "pConstantCurrent"),
        "i_imag": Slot("written", "qConstantCurrent"),
        "p_real": Slot("written", "pConstantPower"),
        "p_imag": Slot("written", "qConstantPower"),
        "num_customers": Slot("written", "EnergyConsumer.customerCount, the same on every phase; unset is None"),
        "min_voltage_pu": Slot("unset", _UNTRANSCRIBED),
        "max_voltage_pu": Slot("unset", _UNTRANSCRIBED),
        "cutoff_voltage_pu": Slot("unset", _UNTRANSCRIBED),
        "active_power_voltage_exponent": Slot("written", "get_load_response.p_exponent; None in the ZIP form"),
        "reactive_power_voltage_exponent": Slot("written", "get_load_response.q_exponent; None in the ZIP form"),
    },
}


def export(consumer: cim.EnergyConsumer, context: ExportContext) -> DistributionLoad:
    loads = get_phase_loads(consumer, "kW", "kVAr")
    names = context.names
    model = load_model(consumer, context)
    phases = gdm_phases(loads.phases, consumer)
    phase_loads = [
        PhaseLoadEquipment(**names.part(consumer, PhaseLoadEquipment, suffix=f"_{phase.value}"),
                           real_power=ActivePower(loads.per_phase[conductor].p, "kilowatt"),
                           reactive_power=ReactivePower(loads.per_phase[conductor].q, "kilovar"),
                           num_customers=consumer.customerCount, **model)
        for conductor, phase in zip(loads.phases, phases)
    ]
    [node] = get_terminal_nodes(consumer)
    return DistributionLoad(
        **names.own(consumer),
        bus=context.gdm(node),
        phases=phases,
        equipment=LoadEquipment(**names.part(consumer, LoadEquipment), phase_loads=phase_loads,
                                connection_type=connection_type(loads.connection, consumer)),
        in_service=in_service(consumer),
        **containers(consumer.EquipmentContainer, context),
    )


def load_model(consumer: cim.EnergyConsumer, context: ExportContext) -> dict:
    """The ZIP fractions and voltage exponents every phase of the load gets."""
    response = get_load_response(consumer)
    if response.exponential:
        z_real, i_real, p_real, z_imag, i_imag, p_imag = context.fill("PhaseLoadEquipment.z_real..p_imag",
                                                                      fills.ZIP_UNDER_EXPONENTS)
    else:
        z_real, i_real, p_real = response.p_impedance, response.p_current, response.p_power
        z_imag, i_imag, p_imag = response.q_impedance, response.q_current, response.q_power
    return {"z_real": z_real, "i_real": i_real, "p_real": p_real, "z_imag": z_imag, "i_imag": i_imag,
            "p_imag": p_imag, "active_power_voltage_exponent": response.p_exponent,
            "reactive_power_voltage_exponent": response.q_exponent}
