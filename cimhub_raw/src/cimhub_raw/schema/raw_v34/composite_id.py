"""Composite identifiers for PSS/E RAW v34 records.

``GraphModel`` keys a record on its schema ``identifier: true`` field, else on ``record.ID``. Most RAW
records have a natural key of several fields (a load is its bus and its load ID, since one bus can carry
several loads), which one schema field cannot express, so ``assign_composite_id`` sets ``record.ID``.

The key is the fields' values joined with ``_``, trimmed (PSS/E compares IDs without their padding). A key
field the file leaves blank takes its ``raw_default`` (a load ID defaults to ``1``), so the same record has
the same key however it was written. This is the only place the reader applies a default.

Reader and exporter both use this module, so the key that later seeds an mRID is identical in both
directions.
"""

from __future__ import annotations

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.serialization import get_schema_annotations

KEY_FIELDS: dict[type, tuple[str, ...]] = {
    schema.LoadRecord: ("bus_number", "load_id"),
    schema.FixedShuntRecord: ("bus_number", "shunt_id"),
    schema.GeneratorRecord: ("bus_number", "gen_id"),
    schema.BranchRecord: ("from_bus_number", "to_bus_number", "circuit"),
    schema.SwitchRecord: ("from_bus_number", "to_bus_number", "circuit"),
    schema.TransformerRecord: ("i", "j", "k", "circuit"),
    schema.SwitchedShuntRecord: ("bus_number",),
    schema.FactsDeviceRecord: ("name",),
    schema.InductionMachineRecord: ("bus_id", "name"),
    schema.InterareaTransferRecord: ("from_area", "to_area", "transfer_id"),
    schema.MultiSectionLineRecord: ("i", "j", "line_id"),
    schema.SubstationNodeRecord: ("substation_number", "node_number"),
    schema.StationSwitchingDeviceRecord: ("substation_number", "from_node", "to_node", "circuit"),
    schema.EquipmentTerminalRecord: (
        "substation_number", "bus_number", "terminal_type", "j_bus", "k_bus", "identifier"),
}


def _key_text(record: object, field: str) -> str:
    """The trimmed text of one key field; a blank field takes its ``raw_default``."""
    value = getattr(record, field)
    if value is None:
        value = get_schema_annotations(type(record)).get(field, {}).get("raw_default")
    if value is None:
        return ""
    return str(value).strip()


def assign_composite_id(record: object) -> None:
    """Set ``record.ID`` for a record type with a composite key; no-op for the others."""
    if isinstance(record, schema.CaseIdentificationRecord):
        record.ID = "CASE"  # one per file
        return
    fields = KEY_FIELDS.get(type(record))
    if fields is not None:
        record.ID = "_".join(_key_text(record, field) for field in fields)
