"""RAW Equipment terminal data -> ``equipment_terminal.cimtbl``: ``Update Table Terminal`` rows putting each named
equipment terminal on its substation node (R6). It comes last, once every equipment document has written its
Terminals; the equipment is matched against what those documents wrote.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#equipment-terminals``.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import permutations

from cimtables.document import Column, Document, Row, Table

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field
from cimhub_raw.importer.cimtbl import branch, fixed_shunt, generator, load, switch, switched_shunt, transformer
from cimhub_raw.importer.node_breaker import NodeBreaker, node_mrid

NATIVE_CLASS = schema.EquipmentTerminalRecord

#: TYP -> the equipment form. B and 2 are one form: a branch or a two-winding transformer.
FORMS = {"L": "load", "F": "fixed shunt", "M": "machine", "B": "branch", "2": "branch",
         "3": "three-winding transformer", "S": "switched shunt"}
#: TYP forms of phase-2 equipment, which raise
PHASE_2 = {"I": "induction machine", "D": "two-terminal DC line", "V": "VSC DC line", "N": "multi-terminal DC line",
           "A": "FACTS device"}
#: forms whose blank ID / CKT is '1'
KEYED = ("L", "F", "M", "I", "B", "2", "3")

FIELDS = {
    "substation_number": Field("structural", note="IS: the block whose node NI is meant (filled by the reader)"),
    "bus_number": Field("structural", note="I: which terminal of the equipment; node NI's bus must be I"),
    "node_number": Field("structural", note="NI: the Terminal's ConnectivityNode sub_s<IS>_n<NI> (an Update row); "
                                            "0: bus I has no node-breaker model, no row"),
    "terminal_type": Field("structural", note="TYP: the equipment form, L F M B/2 3 S; B and 2 are one form (a branch "
                                              "or a two-winding transformer); I D V N A raise (phase 2)"),
    "j_bus": Field("structural", note="J: the other end of a B / 2 / 3 key, in either order"),
    "k_bus": Field("structural", note="K: the third winding of a 3 key"),
    "identifier": Field("structural", note="ID / CKT: the rest of the key; blank: 1 for L F M I B 2 3 (defaulted)"),
}

_PROVENANCE = """PSS/E RAW Equipment terminal data -> each named Terminal on its ConnectivityNode (Update rows).
Source table: Equipment terminal (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#equipment-terminals"""


def written_equipment(parts: Iterable[Document]) -> set[str]:
    """The mRID of every row that defines an object (not an ``Update`` row) in ``parts``."""
    return {row.cells[0] for part in parts for statement in part.statements
            if isinstance(statement, Table) and not statement.update and statement.columns[0].name == "mRID"
            for row in statement.rows}


def _one(candidates: list[tuple[str, int]], written: set[str], what: str, record_id: str) -> tuple[str, int]:
    """The one written ``(equipment mRID, terminal)`` among ``candidates``; none or two raise."""
    found = [(equipment, terminal) for equipment, terminal in candidates if equipment in written]
    if len(found) != 1:
        names = ", ".join(equipment for equipment, _ in found)
        raise ValueError(f"{record_id}: {f'matches {names}' if found else f'names no {what}'}")
    return found[0]


def _branch_terminals(record, key: str, written: set[str], record_id: str) -> list[str]:
    """A branch end and its line shunt, or a two-winding transformer winding, at bus I."""
    candidates = []
    for first, second, terminal in ((record.bus_number, record.j_bus, 1), (record.j_bus, record.bus_number, 2)):
        pair = f"{first}_{second}_{key}"
        candidates += [(f"{branch.LINE_PREFIX}{pair}", terminal), (f"{branch.SERIES_CAPACITOR_PREFIX}{pair}", terminal),
                       (f"{transformer.PREFIX}{first}_{second}_0_{key}", terminal)]
    switches = [f"{switch.PREFIX}{a}_{b}_{key}" for a, b in ((record.bus_number, record.j_bus),
                                                               (record.j_bus, record.bus_number))]
    if not any(equipment in written for equipment, _ in candidates) and any(name in written for name in switches):
        raise ValueError(f"{record_id}: names a system switching device, which has no terminal-record form")
    equipment, terminal = _one(candidates, written, "branch or two-winding transformer", record_id)
    terminals = [f"{equipment}_T{terminal}"]
    if not equipment.startswith(transformer.PREFIX):
        shunt = f"{branch.SHUNT_PREFIX}{equipment.split('_', 1)[1]}_{'ij'[terminal - 1]}"
        if shunt in written:
            terminals.append(f"{shunt}_T1")
    return terminals


def _terminals(record, form: str, key: str | None, written: set[str], record_id: str) -> list[str]:
    """The Terminal mRIDs the record places: those its equipment's mapper wrote at bus I."""
    bus = record.bus_number
    if form == "load":
        return [f"{_one([(f'{load.PREFIX}{bus}_{key}', 1)], written, 'load', record_id)[0]}_T1"]
    if form == "fixed shunt":
        return [f"{_one([(f'{fixed_shunt.PREFIX}{bus}_{key}', 1)], written, 'fixed shunt', record_id)[0]}_T1"]
    if form == "machine":
        prefixes = (generator.MACHINE_PREFIXES[0], generator.CONVERTER_PREFIXES[0])
        machine = _one([(f"{prefix}{bus}_{key}", 1) for prefix in prefixes], written, "machine", record_id)[0]
        step_up = f"{machine}_xf"  # the machine sits on its internal node, behind its step-up (R3b-5)
        return [f"{step_up if step_up in written else machine}_T1"]
    if form == "branch":
        return _branch_terminals(record, key, written, record_id)
    if form == "three-winding transformer":
        buses = (bus, record.j_bus, record.k_bus)
        candidates = [(f"{transformer.PREFIX}{a}_{b}_{c}_{key}", (a, b, c).index(bus) + 1)
                      for a, b, c in permutations(buses)]
        equipment, winding = _one(candidates, written, "three-winding transformer", record_id)
        return [f"{equipment}_T{winding}"]
    blocks = sorted(name for name in written if name.startswith(f"{switched_shunt.PREFIX}{bus}_b"))
    if not blocks:
        raise ValueError(f"{record_id}: names no switched shunt")
    return [f"{name}_T1" for name in blocks]


def map_equipment_terminal(native, node_breaker: NodeBreaker, parts: Iterable[Document]) -> Document:
    """``parts``: every equipment document, already mapped."""
    records = sorted(native.list_by_class(NATIVE_CLASS),
                     key=lambda record: (record.substation_number, record.node_number, str(record.ID)))
    if not records:
        return Document(name="equipment_terminal", statements=[], profile=CIM_PROFILE)
    written = written_equipment(parts)
    placed: dict[str, str] = {}
    rows, unplaced = [], 0
    for record in records:
        record_id = f"equipment terminal {record.ID} (SUBSTATION block {record.substation_number})"
        if record.terminal_type in PHASE_2:
            raise NotImplementedError(f"{record_id}: TYP {record.terminal_type} ({PHASE_2[record.terminal_type]}, "
                                      "phase 2)")
        if record.terminal_type not in FORMS:
            raise ValueError(f"{record_id}: TYP {record.terminal_type!r} is no equipment form (known: "
                             f"{', '.join(list(FORMS) + list(PHASE_2))})")
        if not record.node_number:
            if record.bus_number in node_breaker.block_of_bus:
                raise ValueError(f"{record_id}: NI 0 (no node-breaker model), but bus {record.bus_number} has nodes "
                                 f"in block {node_breaker.block_of_bus[record.bus_number]}")
            unplaced += 1
            continue
        block, _ = node_breaker.node(record.bus_number, record.node_number, record_id)
        if block != record.substation_number:
            raise ValueError(f"{record_id}: bus {record.bus_number}'s nodes are in block {block}")
        defaulted = record.identifier in (None, "") and record.terminal_type in KEYED
        key = "1" if defaulted else record.identifier
        for terminal in _terminals(record, FORMS[record.terminal_type], key, written, record_id):
            if terminal in placed:
                raise ValueError(f"{record_id}: Terminal {terminal} is already placed by {placed[terminal]}")
            placed[terminal] = record_id
            rows.append(Row([terminal, node_mrid(block, record.node_number)],
                            comment="defaulted: identifier=1" if defaulted else None))

    comment = "each named equipment terminal on its node"
    if unplaced:
        comment += (f"; {unplaced} record{'s' if unplaced > 1 else ''} with NI 0 (no node-breaker model) "
                    f"place{'' if unplaced > 1 else 's'} nothing")
    statements = [Table("Terminal", [Column("mRID"), Column("ConnectivityNode")], rows, comment=comment,
                        update=True)] if rows else []
    document_comment = _PROVENANCE.format(count=len(records))
    if not rows:
        document_comment += f"\n{comment}"
    return Document(name="equipment_terminal", statements=statements, profile=CIM_PROFILE, comment=document_comment)
