"""Bus, zone and area numbers and RAW names (``EXPORT_MAPPING.md#identity-and-names-x2``).

A number comes from the importer's key: ``TopologicalNode.busNumber`` for a bus, the mRID ``srgn_<n>`` / ``ca_<n>``
for a zone or area. A zone or area whose mRID is not of that form gets the next number above the largest taken
(the one fallback, logged with a count). A device's ID (CKT, load ID, ...) comes from the mRID
``<prefix><buses>_<ID>`` when its buses are the device's own, in order; otherwise it is the next free ``1``, ``2``,
... on those buses (the one fallback, logged with a count). A NAME equal to the importer's blank-NAME key is written
blank.
"""

from __future__ import annotations

import logging
import re

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.terminals import get_terminal_nodes

_log = logging.getLogger(__name__)


def bus_numbers(nodes) -> dict[cim.TopologicalNode, int]:
    """Each numbered node's ``busNumber``. A node without one is internal to a device (R3b, P2b) and is left out; a
    number used twice, or no numbered node at all, raises."""
    numbers: dict[cim.TopologicalNode, int] = {}
    holder: dict[int, cim.TopologicalNode] = {}
    for node in nodes:
        if node.busNumber is None:
            continue
        if node.busNumber in holder:
            raise ValueError(f"bus number {node.busNumber} is on {describe(holder[node.busNumber])} and "
                             f"{describe(node)}")
        holder[node.busNumber] = node
        numbers[node] = node.busNumber
    if not numbers:
        raise ValueError("no TopologicalNode has a busNumber: numbering a model from another format is not done yet")
    return numbers


def keyed_numbers(objects, prefix: str) -> dict:
    """Each object's number from its mRID ``<prefix><n>``; the others get the next numbers above the largest, in
    mRID order. Two mRIDs giving one number raise."""
    pattern = re.compile(rf"{re.escape(prefix)}(\d+)")
    numbers: dict = {}
    holder: dict[int, object] = {}
    unkeyed = []
    for obj in sorted(objects, key=lambda item: item.mRID):
        match = pattern.fullmatch(obj.mRID)
        if match is None:
            unkeyed.append(obj)
            continue
        number = int(match.group(1))
        if number in holder:
            raise ValueError(f"{describe(holder[number])} and {describe(obj)} both give number {number}")
        holder[number] = obj
        numbers[obj] = number
    following = max(holder, default=0) + 1
    for offset, obj in enumerate(unkeyed):
        numbers[obj] = following + offset
    if unkeyed:
        _log.info("%d %s(s) without a %s<n> mRID numbered from %d", len(unkeyed), type(unkeyed[0]).__name__, prefix,
                  following)
    return numbers


def terminal_buses(device, context) -> tuple[int, ...]:
    """The bus number at each of the device's terminals, in ``sequenceNumber`` order. A terminal on a node with no
    number raises."""
    buses = []
    for node in get_terminal_nodes(device, topological=True):
        if node not in context.bus_numbers:
            raise ValueError(f"{describe(device)}: its terminal is on {describe(node)}, which has no busNumber")
        buses.append(context.bus_numbers[node])
    return tuple(buses)


def keyed_ids(devices, width: int, fallback_prefix: str = "") -> dict:
    """Each device's ID, for ``devices`` given as ``(device, mRID prefix, buses in order)``. The ID is the rest of
    the mRID ``<prefix><bus>_<bus>_..._<ID>`` when it fits ``width``; otherwise the next free
    ``<fallback_prefix>1``, ``2``, ... among the devices on the same buses in any order (PSS/E's key). Two devices
    with one key raise."""
    ids: dict = {}
    holder: dict[tuple, object] = {}
    unkeyed = []
    for device, prefix, buses in sorted(devices, key=lambda item: item[0].mRID):
        stem = prefix + "".join(f"{bus}_" for bus in buses)
        rest = device.mRID[len(stem):] if device.mRID.startswith(stem) else ""
        if not 0 < len(rest) <= width:
            unkeyed.append((device, buses))
            continue
        key = (tuple(sorted(buses)), rest)
        if key in holder:
            raise ValueError(f"{describe(holder[key])} and {describe(device)} both have buses {key[0]} and ID "
                             f"{rest!r}")
        holder[key], ids[device] = device, rest
    for device, buses in unkeyed:
        group = tuple(sorted(buses))
        number = 1
        while (group, f"{fallback_prefix}{number}") in holder:
            number += 1
        ids[device] = f"{fallback_prefix}{number}"
        holder[(group, ids[device])] = device
    if unkeyed:
        _log.info("%d %s(s) without a keyed mRID take the next free ID on their buses", len(unkeyed),
                  type(unkeyed[0][0]).__name__)
    return ids


def raw_name(obj, key: str, width: int) -> str | None:
    """``obj.name`` as a RAW NAME: blank (``None``) when unset or equal to ``key`` (the importer's blank-NAME form).
    A name longer than ``width`` raises."""
    name = obj.name
    if not name or name == key:
        return None
    if len(name) > width:
        raise ValueError(f"{describe(obj)}: name {name!r} is longer than RAW's {width} characters")
    return name
