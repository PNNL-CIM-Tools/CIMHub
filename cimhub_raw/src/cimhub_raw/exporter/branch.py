"""ACLineSegment, SeriesCompensator (+ their line shunts and ratings) -> Non-transformer branch
(``EXPORT_MAPPING.md#e1-branch-series-capacitor-switch-multi-section-line-ratings``)."""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim
from cimtables.graph_write import get_qty

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.export_slots import Slot
from cimhub_core.getters import describe
from cimhub_core.getters.in_service import get_in_service
from cimhub_core.getters.line_impedance import get_line_sequence_impedance
from cimhub_core.getters.series_compensator import get_series_compensator
from cimhub_raw.exporter.area_trace import metered_terminal
from cimhub_raw.exporter.identity import keyed_ids, raw_name, terminal_buses
from cimhub_raw.exporter.ratings import device_ratings
from cimhub_raw.exporter.shunt_admittance import bus_base_admittance
from cimhub_raw.importer.cimtbl.branch import LINE_PREFIX, SERIES_CAPACITOR_PREFIX, SHUNT_PREFIX

NATIVE_CLASS = schema.BranchRecord
CIM_CLASSES = (cim.ACLineSegment, cim.SeriesCompensator)
PREFIX = {cim.ACLineSegment: LINE_PREFIX, cim.SeriesCompensator: SERIES_CAPACITOR_PREFIX}
CIRCUIT_WIDTH = 2
NAME_WIDTH = 40
END_TERMINAL = {"i": 1, "j": 2}  # a line shunt's end -> the branch terminal on its bus

_OWNER = Slot("unset", "ownership is an asset concept (CIM 18 gap)")
_SHUNT = "the line shunt cap_<key>_{end} (mRID key, E1-2): get_shunt_admittance {part} (pu on the bus base)"
SLOTS = {NATIVE_CLASS: {
    "from_bus_number": Slot("written", "I: terminal 1's busNumber"),
    "to_bus_number": Slot("written", "J: terminal 2's busNumber"),
    "r": Slot("written", "R: get_line_sequence_impedance / get_series_compensator r (pu)"),
    "x": Slot("written", "X: get_line_sequence_impedance / get_series_compensator x (pu)"),
    "circuit": Slot("written", "CKT: the ln_ / sc_<I>_<J>_<CKT> key, else the next free (X2)"),
    "b": Slot("written", "B: get_line_sequence_impedance b (pu); blank for a series capacitor"),
    "name": Slot("written", "NAME: name; blank when it is the key I_J_CKT"),
    "ratings": Slot("written", "RATE1..RATE12: the olt_rate<n> limits (ratings.device_ratings)"),
    "g_from": Slot("written", "GI: " + _SHUNT.format(end="i", part="g")),
    "b_from": Slot("written", "BI: " + _SHUNT.format(end="i", part="b")),
    "g_to": Slot("written", "GJ: " + _SHUNT.format(end="j", part="g")),
    "b_to": Slot("written", "BJ: " + _SHUNT.format(end="j", part="b")),
    "status": Slot("rule", "ST: 0 when inService is false, else 1"),
    "metered_end": Slot("written", "MET: on a tie, the terminal holding its TieFlow pair (R5); else blank (RAW-22)"),
    "length": Slot("written", "LEN: ACLineSegment.length (km); blank for a series capacitor (R1b-2)"),
    **{slot: _OWNER for slot in ("o1", "f1", "o2", "f2", "o3", "f3", "o4", "f4")},
}}


def export(context) -> list[schema.BranchRecord]:
    """One Branch per ACLineSegment and SeriesCompensator, by key."""
    base_power = context.network.base_power
    devices = [(device, terminal_buses(device, context)) for device in context.objects(*CIM_CLASSES)]
    circuits = keyed_ids([(device, PREFIX[type(device)], buses) for device, buses in devices], CIRCUIT_WIDTH)
    shunts = {claim: shunt for shunt, claim in line_shunts(context).items()}
    records = []
    for device, (from_bus, to_bus) in devices:
        circuit = circuits[device]
        in_service = get_in_service(device, which="actual") is not False
        if isinstance(device, cim.ACLineSegment):
            impedance = get_line_sequence_impedance(device, "pu", base_power=base_power)
            if impedance.g:
                raise ValueError(f"{describe(device)}: gch is set; RAW has no line conductance")
            r, x, b, length = impedance.r, impedance.x, impedance.b, get_qty(device, "length", "km")
        else:
            data = get_series_compensator(device, "pu", base_power=base_power)
            r, x, b, length = data.r, data.x, None, None
        from_g, from_b = _line_shunt(shunts.get((device, "i")), in_service, device, base_power)
        to_g, to_b = _line_shunt(shunts.get((device, "j")), in_service, device, base_power)
        records.append(schema.BranchRecord(
            from_bus_number=from_bus, to_bus_number=to_bus, r=r, x=x, circuit=circuit, b=b,
            name=raw_name(device, f"{from_bus}_{to_bus}_{circuit}", NAME_WIDTH), ratings=device_ratings(device),
            g_from=from_g, b_from=from_b, g_to=to_g, b_to=to_b, status=1 if in_service else 0,
            metered_end=metered_terminal(device), length=length))
    return sorted(records, key=lambda record: (record.from_bus_number, record.to_bus_number, record.circuit))


def line_shunts(context) -> dict[cim.LinearShuntCompensator, tuple[object, str]]:
    """The shunts that are a branch's line shunts (E1-2), each with ``(branch, end)``: the mRID
    ``cap_<key>_i`` / ``_j`` of a branch ``ln_`` / ``sc_<key>``, on that end's bus. E2 leaves these out."""
    branches = {device.mRID: device for device in context.objects(*CIM_CLASSES)}
    claimed = {}
    for shunt in context.objects(cim.LinearShuntCompensator):
        if not shunt.mRID.startswith(SHUNT_PREFIX):
            continue
        key, _, end = shunt.mRID.removeprefix(SHUNT_PREFIX).rpartition("_")
        if end not in END_TERMINAL:
            continue
        for prefix in PREFIX.values():
            branch = branches.get(prefix + key)
            if branch is not None and _same_node(shunt, branch, END_TERMINAL[end]):
                claimed[shunt] = (branch, end)
    return claimed


def _same_node(shunt, branch, sequence_number: int) -> bool:
    [branch_terminal] = [terminal for terminal in branch.Terminals if terminal.sequenceNumber == sequence_number]
    return shunt.Terminals[0].TopologicalNode is branch_terminal.TopologicalNode


def _line_shunt(shunt, branch_in_service: bool, branch, base_power) -> tuple[float | None, float | None]:
    """G and B of a line shunt in pu; blank without one. A shunt in or out of service apart from its line raises."""
    if shunt is None:
        return None, None
    if (get_in_service(shunt, which="actual") is not False) != branch_in_service:
        raise ValueError(f"{describe(shunt)}: in service {shunt.inService}, but its line {describe(branch)} is "
                         f"{'in' if branch_in_service else 'out of'} service; a line shunt switches with its line")
    admittance = bus_base_admittance(shunt, "actual", base_power)
    return admittance.g, admittance.b
