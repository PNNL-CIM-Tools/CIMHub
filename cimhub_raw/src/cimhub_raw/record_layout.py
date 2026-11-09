"""The positional layout of a RAW record, read from the LinkML schema annotations.

A RAW record is a sequence of fields on one or more lines. The schema gives each attribute its line
(``line_number``, default 1), its position on that line (``order``), its value type, and for a fixed-size
list (the 12 RATEs) a ``count``. Reader and writer both walk this layout, so the two directions cannot
disagree about where a field sits.

Attributes without an ``order`` (the composite ``ID``) and reader-filled ``structural`` attributes (a node's
``substation_number``) are not fields of the record text and are left out.
"""

from __future__ import annotations

from functools import cache
from typing import NamedTuple

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.serialization import get_schema_annotations


class Slot(NamedTuple):
    """One field position (or, with ``count`` > 1, a run of positions) of a record line."""

    name: str
    value_type: str  # 'int', 'float' or 'string'
    count: int  # 1 for a scalar; the list length for a fixed-size list (RATE1..RATE12)
    annotations: dict


@cache
def record_lines(record_class: type) -> tuple[tuple[Slot, ...], ...]:
    """The record's lines, each a tuple of its slots in field order."""
    annotations = get_schema_annotations(record_class)
    if not annotations:
        raise ValueError(f"{record_class.__name__}: no schema annotations found")
    by_line: dict[int, list[tuple[int, Slot]]] = {}
    for name, annotation in annotations.items():
        if 'order' not in annotation or annotation.get('structural'):
            continue
        count = int(annotation.get('count', 1)) if annotation.get('multivalued') else 1
        slot = Slot(name, annotation.get('value_type', 'string'), count, annotation)
        by_line.setdefault(int(annotation.get('line_number', 1)), []).append((int(annotation['order']), slot))
    lines = []
    for line_number in sorted(by_line):
        slots = sorted(by_line[line_number], key=lambda pair: pair[0])
        orders = [order for order, _ in slots]
        if len(set(orders)) != len(orders):
            raise ValueError(f"{record_class.__name__} line {line_number}: two fields share an order ({orders})")
        lines.append(tuple(slot for _, slot in slots))
    return tuple(lines)


def line_count(record_class: type, first_line: dict) -> int:
    """How many lines a record has, given the values of its first line.

    A transformer has a fifth line only when it has a third winding (K is set and nonzero); every other
    record has all the lines of its layout.
    """
    lines = len(record_lines(record_class))
    if record_class is schema.TransformerRecord and not first_line.get('k'):
        return lines - 1
    return lines


#: Equipment terminal records (substation data) have one field list per equipment form, chosen by TYP.
TERMINAL_FORMS: dict[str, tuple[str, ...]] = {
    **{typ: ('bus_number', 'node_number', 'terminal_type', 'identifier') for typ in 'LFMIDVNA'},
    'S': ('bus_number', 'node_number', 'terminal_type'),
    'B': ('bus_number', 'node_number', 'terminal_type', 'j_bus', 'identifier'),
    '2': ('bus_number', 'node_number', 'terminal_type', 'j_bus', 'identifier'),
    '3': ('bus_number', 'node_number', 'terminal_type', 'j_bus', 'k_bus', 'identifier'),
}


def terminal_slots(terminal_type: str) -> tuple[Slot, ...]:
    """The slots of an equipment terminal record of form ``terminal_type``."""
    if terminal_type not in TERMINAL_FORMS:
        raise ValueError(f"equipment terminal type {terminal_type!r} is not one of {sorted(TERMINAL_FORMS)}")
    by_name = {slot.name: slot for slot in record_lines(schema.EquipmentTerminalRecord)[0]}
    return tuple(by_name[name] for name in TERMINAL_FORMS[terminal_type])
