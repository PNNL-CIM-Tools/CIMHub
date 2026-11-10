"""Switch, Breaker, Disconnector between two buses (+ ratings) -> System switching device
(``EXPORT_MAPPING.md#system-switching-device``).

A switch on two ConnectivityNodes is a substation switching device of a node-breaker block (R6), exported by E5.
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe
from cimhub_core.getters.switch_state import get_switch_state
from cimhub_raw.exporter.area_trace import metered_terminal
from cimhub_raw.exporter.identity import keyed_ids, raw_name, terminal_buses
from cimhub_raw.exporter.ratings import device_ratings
from cimhub_raw.importer.cimtbl.switch import PREFIX, SWITCH_CLASS

NATIVE_CLASS = schema.SwitchRecord
CIM_CLASSES = (cim.Switch, cim.Breaker, cim.Disconnector)
STYPE = {getattr(cim, name): code for code, name in SWITCH_CLASS.items()}  # class -> STYPE, the importer's inverted
CIRCUIT_WIDTH = 2
NAME_WIDTH = 40
#: X and METERED have no default in the format, so they are written: X the substation switching device's default
#: reactance, METERED bus I off a tie
REACTANCE = 0.0001
METERED_OFF_TIE = 1

SLOTS = {NATIVE_CLASS: {
    "from_bus_number": Slot("written", "I: terminal 1's busNumber"),
    "to_bus_number": Slot("written", "J: terminal 2's busNumber"),
    "circuit": Slot("written", "CKT: the sw_<I>_<J>_<CKT> key, else the next free (X2)"),
    "x": Slot("rule", "X 0.0001: a Switch has no impedance, and the format gives X no default"),
    "ratings": Slot("written", "RATE1..RATE12: the olt_rate<n> limits (ratings.device_ratings)"),
    "status": Slot("written", "STATUS: get_switch_state actual, open 0"),
    "nstat": Slot("written", "NSTATUS: get_switch_state normal, open 0"),
    "metered_end": Slot("rule", "METERED: on a tie, the terminal holding its TieFlow pair (R5); else 1 (no "
                                "default in the format; RAW-22)"),
    "stype": Slot("written", "STYPE by class: Switch 1, Breaker 2, Disconnector 3"),
    "name": Slot("written", "NAME: name; blank when it is the key I_J_CKT"),
}}


def export(context) -> list[schema.SwitchRecord]:
    """One System switching device per bus-to-bus switch, by key."""
    devices = [(switch, terminal_buses(switch, context)) for switch in system_switches(context)]
    circuits = keyed_ids([(switch, PREFIX, buses) for switch, buses in devices], CIRCUIT_WIDTH)
    records = []
    for switch, (from_bus, to_bus) in devices:
        circuit = circuits[switch]
        records.append(schema.SwitchRecord(
            from_bus_number=from_bus, to_bus_number=to_bus, circuit=circuit, x=REACTANCE,
            ratings=device_ratings(switch),
            status=_status(switch, "actual"), nstat=_status(switch, "normal"),
            metered_end=metered_terminal(switch) or METERED_OFF_TIE, stype=STYPE[type(switch)],
            name=raw_name(switch, f"{from_bus}_{to_bus}_{circuit}", NAME_WIDTH)))
    return sorted(records, key=lambda record: (record.from_bus_number, record.to_bus_number, record.circuit))


def system_switches(context) -> list:
    """The switches with no ConnectivityNode on either terminal. One on a node at one terminal only raises."""
    found = []
    for switch in context.objects(*CIM_CLASSES):
        on_nodes = [terminal.ConnectivityNode is not None for terminal in switch.Terminals]
        if all(on_nodes):
            continue
        if any(on_nodes):
            raise ValueError(f"{describe(switch)}: a ConnectivityNode on one terminal only; a switch is between two "
                             "buses or two nodes of a node-breaker block")
        found.append(switch)
    return found


def _status(switch, which: str) -> int:
    return 0 if get_switch_state(switch, which=which) else 1
