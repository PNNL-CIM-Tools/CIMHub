"""DistributionLoad → EnergyConsumer (OPEN_DECISIONS 13; GDM_MAPPING.md §6, §16).

The EnergyConsumer holds the totals. A balanced three-phase load has no phases (``builder_phases``); any other load
gets an EnergyConsumerPhase per phase (per branch for delta: one child ``<ld>_BC`` on BC), and per-phase p and q only
when they differ by phase. The ZIP model is one
LoadResponseCharacteristic: the shared ``zip_constant_pq``/``_z``/``_i`` rows (DSS-7), an ``exp_<p>_<q>`` row, or one
row per other fraction tuple.
"""

from __future__ import annotations

from cimbuilder.object_builder import (
    EnergyConsumerBuilder,
    EnergyConsumerPhaseBuilder,
    LoadResponseCharacteristicBuilder,
)
from cimhub_core.cimtbl import Field, lookup
from gdm.distribution.enums import ConnectionType, Phase

from cimhub_gdm.importer.shared import (
    SHUNT_CONNECTION,
    UUID_FIELD,
    Naming,
    builder_phases,
    bus_base_voltage,
    bus_mrid,
    children_by_phase,
    container_mrid,
    name_field,
    object_mrid,
    phases_text,
    power_qty,
    require_in_service,
)

PREFIX = "ld_"

#: ZIP fractions (p: Z, I, P; q: Z, I, P) of the three shared LoadResponseCharacteristics (DSS-7).
SHARED_ZIP = {
    (0, 0, 1, 0, 0, 1): "zip_constant_pq",
    (1, 0, 0, 1, 0, 0): "zip_constant_z",
    (0, 1, 0, 0, 1, 0): "zip_constant_i",
}

FIELDS_DistributionLoad = {
    "uuid": UUID_FIELD,
    "name": name_field(PREFIX),
    "substation": Field("structural", note="EquipmentContainer when there is no feeder"),
    "feeder": Field("structural", note="EquipmentContainer"),
    "in_service": Field("structural", note="False raises: no CIM home"),
    "bus": Field("structural", note="node; BaseVoltage"),
    "phases": Field("structural", note="None for balanced ABC with equal phases, else an EnergyConsumerPhase each; "
                                       "N raises"),
    "equipment": Field("structural", note="inline"),
}
FIELDS_LoadEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline: no CIM object of its own"),
    "phase_loads": Field("structural", note="one per phase: summed into the totals; per phase when they differ"),
    "connection_type": Field("mapped", note="SHUNT_CONNECTION → phaseConnection, grounded"),
}
FIELDS_PhaseLoadEquipment = {
    "uuid": Field("untranscribed", note="inline: no CIM object of its own"),
    "name": Field("untranscribed", note="inline: no CIM object of its own"),
    "real_power": Field("copied", (("add_ssh", "p", None),), note="summed over phases; per phase when they differ"),
    "reactive_power": Field("copied", (("add_ssh", "q", None),), note="summed over phases; per phase when they differ"),
    "z_real": Field("mapped", note="pConstantImpedance of the LoadResponseCharacteristic"),
    "z_imag": Field("mapped", note="qConstantImpedance"),
    "i_real": Field("mapped", note="pConstantCurrent"),
    "i_imag": Field("mapped", note="qConstantCurrent"),
    "p_real": Field("mapped", note="pConstantPower"),
    "p_imag": Field("mapped", note="qConstantPower"),
    "num_customers": Field("copied", (("add_connectivity", "customerCount", None),),
                           note="the same on every phase, else raises"),
    "min_voltage_pu": Field("untranscribed", note="no home on LoadResponseCharacteristic (DSS Vminpu likewise)"),
    "max_voltage_pu": Field("untranscribed", note="no home on LoadResponseCharacteristic"),
    "cutoff_voltage_pu": Field("untranscribed", note="no home on LoadResponseCharacteristic"),
    "active_power_voltage_exponent": Field("mapped", note="with the reactive exponent: an exp_<p>_<q> row "
                                                          "(exponentModel), overriding the ZIP fractions"),
    "reactive_power_voltage_exponent": Field("mapped", note="see active_power_voltage_exponent (GDM sets both or "
                                                            "neither)"),
}


def add_load(network, load, naming: Naming) -> None:
    """An EnergyConsumer with the load's totals, connection and load model."""
    require_in_service(load)
    label = f"DistributionLoad {load.name!r}"
    equipment = load.equipment
    phase_loads = equipment.phase_loads  # GDM requires one per phase
    if Phase.N in load.phases:
        raise ValueError(f"{label}: a load on the neutral has no EnergyConsumerPhase")
    phase_connection, grounded = lookup(SHUNT_CONNECTION, ConnectionType(equipment.connection_type),
                                        slot="connection_type", record_id=load.name)
    first = phase_loads[0]
    differs = any(p.real_power != first.real_power or p.reactive_power != first.reactive_power for p in phase_loads)
    if differs and phase_connection == "D":
        # CIM gives a delta load per branch (one child on BC, <ld>_BC), GDM per phase: a 2-phase delta is one branch,
        # so its phase loads only sum; a 3-phase delta's phase loads have no branch to go to.
        if len(load.phases) != 2:
            raise ValueError(f"{label}: per-phase values of a 3-phase delta load differ; CIM holds a delta load per "
                             "branch, GDM per phase")
        differs = False

    builder = EnergyConsumerBuilder(network, network.container)
    consumer = builder.create(mRID=object_mrid(PREFIX, load, "EnergyConsumer", naming), name=load.name)
    _, _, consumer_phases = builder.add_connectivity(
        consumer,
        node=bus_mrid(load.bus, naming),
        phaseConnection=phase_connection,
        phases=phases_text(load.phases) if differs else builder_phases(load.phases),
        grounded=grounded,
        customerCount=customer_count(phase_loads, label),
        EquipmentContainer=container_mrid(load, naming),
        BaseVoltage=bus_base_voltage(load.bus),
    )
    builder.add_electrical(consumer, LoadResponse=load_response(network, phase_loads, label))
    builder.add_ssh(consumer,
                    p=power_qty(sum((p.real_power for p in phase_loads[1:]), first.real_power), "active", label=label),
                    q=power_qty(sum((p.reactive_power for p in phase_loads[1:]), first.reactive_power), "reactive",
                                label=label))
    if not differs:
        return
    phase_builder = EnergyConsumerPhaseBuilder(network, network.container)
    for child, phase_load in zip(children_by_phase(consumer.mRID, consumer_phases, load.phases), phase_loads):
        phase_builder.add_ssh(child, p=power_qty(phase_load.real_power, "active", label=label),
                              q=power_qty(phase_load.reactive_power, "reactive", label=label))


def customer_count(phase_loads, label: str) -> int | None:
    """The phases' ``num_customers``, which must be the same on every phase (unset on all is None)."""
    counts = {p.num_customers for p in phase_loads}
    if len(counts) > 1:
        raise ValueError(f"{label}: num_customers differs by phase ({sorted(counts, key=str)})")
    return counts.pop()


def response_key(phase_load) -> tuple:
    """``('exp', (p, q))`` when the voltage exponents are set (GDM sets both or neither), else
    ``('zip', (pZ, pI, pP, qZ, qI, qP))``."""
    if phase_load.active_power_voltage_exponent is not None:
        return "exp", (phase_load.active_power_voltage_exponent, phase_load.reactive_power_voltage_exponent)
    return "zip", (phase_load.z_real, phase_load.i_real, phase_load.p_real,
                   phase_load.z_imag, phase_load.i_imag, phase_load.p_imag)


def response_mrid(key: tuple) -> str:
    """``exp_0.8_3``, a shared ``zip_constant_*`` row, or ``zip_<pZ>_<pI>_<pP>_<qZ>_<qI>_<qP>``."""
    kind, values = key
    if kind == "exp":
        return "exp_" + "_".join(f"{v:g}" for v in values)
    return SHARED_ZIP.get(values) or "zip_" + "_".join(f"{v:g}" for v in values)


def load_response(network, phase_loads, label: str) -> str:
    """The mRID of the load's LoadResponseCharacteristic, created the first time it is named."""
    keys = {response_key(p) for p in phase_loads}
    if len(keys) > 1:
        raise ValueError(f"{label}: the load model differs by phase ({sorted(keys)}); CIM has one "
                         "LoadResponseCharacteristic per EnergyConsumer")
    key = keys.pop()
    response = response_mrid(key)
    if network.find_by_mRID(response) is not None:
        return response
    builder = LoadResponseCharacteristicBuilder(network, network.container)
    characteristic = builder.create(mRID=response)
    kind, values = key
    if kind == "exp":
        builder.add_electrical(characteristic, exponentModel=True, pVoltageExponent=values[0],
                               qVoltageExponent=values[1])
    else:
        p_z, p_i, p_p, q_z, q_i, q_p = values
        builder.add_electrical(characteristic, exponentModel=False, pConstantImpedance=p_z, pConstantCurrent=p_i,
                               pConstantPower=p_p, qConstantImpedance=q_z, qConstantCurrent=q_i,
                               qConstantPower=q_p)
    return response
