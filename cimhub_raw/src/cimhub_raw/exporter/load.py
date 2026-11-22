"""ConformLoad, NonConformLoad, EnergyConsumer (+ its response and load group) -> Load (``EXPORT_MAPPING.md#load``).

PL..YQ are the load at 1 pu voltage split by its ZIP fractions, the inverse of the importer's ``load_p_q`` and
``zip_mix``. AREA is the load's group's ControlArea; ZONE its bus's (E2-1: a SubLoadArea has no link to a zone).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.load import get_load_response, get_phase_loads
from cimhub_core.getters.load_schedule import log_dropped_schedules
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_raw.exporter.bus import bus_zone
from cimhub_raw.exporter.identity import keyed_ids, terminal_buses
from cimhub_raw.importer.cimtbl.load import PREFIX

NATIVE_CLASS = schema.LoadRecord
CIM_CLASSES = (cim.EnergyConsumer, cim.ConformLoad, cim.NonConformLoad)
SCALE = {cim.ConformLoad: 1, cim.NonConformLoad: 0}  # a plain EnergyConsumer: blank (PSS/E: 1)
ID_WIDTH = 2

_P = "p (get_phase_loads total, MW) x the {} fraction (get_load_response)"
_Q = "q (get_phase_loads total, Mvar) x the {} fraction (get_load_response)"
_NO_HOME = Slot("unset", "no CIM home")
SLOTS = {NATIVE_CLASS: {
    "bus_number": Slot("written", "I: the terminal's busNumber"),
    "load_id": Slot("written", "ID: the ld_<I>_<ID> key, else the next free (X2)"),
    "status": Slot("rule", "STATUS: 0 when inService is false, else 1"),
    "area": Slot("written", "AREA: LoadGroup -> SubLoadArea -> LoadArea -> ControlArea; blank without a group"),
    "zone": Slot("written", "ZONE: its bus's (E2-1; a SubLoadArea has no link to a zone, CIM 18 gap)"),
    "constant_real_power": Slot("written", "PL: " + _P.format("constant power")),
    "constant_imag_power": Slot("written", "QL: " + _Q.format("constant power")),
    "constant_current_real_power": Slot("written", "IP: " + _P.format("constant current")),
    "constant_current_imag_power": Slot("written", "IQ: " + _Q.format("constant current")),
    "constant_admittance_real_power": Slot("written", "YP: " + _P.format("constant impedance")),
    "constant_admittance_imag_power": Slot("written", "YQ: -(" + _Q.format("constant impedance") + "), RAW's sign"),
    "owner": Slot("unset", "ownership is an asset concept (CIM 18 gap)"),
    "scale": Slot("written", "SCALE by class: ConformLoad 1, NonConformLoad 0, EnergyConsumer blank"),
    "interruptible": _NO_HOME,
    "dgenp": _NO_HOME,
    "dgenq": _NO_HOME,
    "dgenf": _NO_HOME,
}}


def export(context) -> list[schema.LoadRecord]:
    """One Load per EnergyConsumer, by key."""
    loads = [(load, terminal_buses(load, context)) for load in context.objects(*CIM_CLASSES)]
    log_dropped_schedules([load for load, _ in loads], "RAW")  # a static case: no time series
    ids = keyed_ids([(load, PREFIX, buses) for load, buses in loads], ID_WIDTH)
    records = []
    for load, (bus,) in loads:
        power = get_phase_loads(load, "MW", "MVAr").total
        response = get_load_response(load)
        if response.exponential:
            raise ValueError(f"{describe(load)}: an exponent load response; a RAW load is ZIP only")
        [node] = get_terminal_nodes(load, topological=True)
        records.append(schema.LoadRecord(
            bus_number=bus, load_id=ids[load], status=0 if get_in_service(load, which="actual") is False else 1,
            area=_area(load, context), zone=bus_zone(node, context),
            constant_real_power=power.p * response.p_power, constant_imag_power=power.q * response.q_power,
            constant_current_real_power=power.p * response.p_current,
            constant_current_imag_power=power.q * response.q_current,
            constant_admittance_real_power=power.p * response.p_impedance,
            constant_admittance_imag_power=0.0 - power.q * response.q_impedance,
            scale=SCALE.get(type(load))))
    return sorted(records, key=lambda record: (record.bus_number, record.load_id))


def _area(load, context) -> int | None:
    """The number of the ControlArea of the load's group; None without a group. A broken chain raises."""
    group = getattr(load, "LoadGroup", None)
    if group is None:
        return None
    sub_area = group.SubLoadArea
    load_area = None if sub_area is None else sub_area.LoadArea
    control_area = None if load_area is None else load_area.ControlArea
    if control_area is None:
        raise ValueError(f"{describe(load)}: its {describe(group)} reaches no ControlArea through SubLoadArea -> "
                         "LoadArea")
    return context.area_numbers[control_area]
