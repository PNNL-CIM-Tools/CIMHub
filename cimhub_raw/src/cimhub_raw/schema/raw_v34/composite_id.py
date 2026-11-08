"""Composite identifier assignment for PSS/E RAW v34 records.

``GraphModel`` deduplicates on ``_get_identifier(obj)``, which prefers a
schema ``identifier: true`` field and otherwise falls back to ``obj.ID``.
Most RAW record types have a *composite* natural key (e.g. a load is keyed by
bus number **and** load id, since one bus can carry several loads), which a
single-field schema identifier cannot express. We therefore assign a composite
``.ID`` string here.

This is the single source of truth for those ID strings. Both the reader
(``raw34_reader``) and the exporter (``cim_to_raw``) import it, so the string
that seeds cimgraph's deterministic UUID is byte-identical on import and export
— any drift between the two silently breaks round-trips.
"""

from __future__ import annotations

import cimhub_raw.schema.raw_v34.raw34_schema as schema


def set_load_id(r: schema.LoadRecord) -> None:
    r.ID = f"{r.bus_number}_{r.load_id.strip()}"


def set_fixed_shunt_id(r: schema.FixedShuntRecord) -> None:
    r.ID = f"{r.bus_number}_{r.shunt_id.strip()}"


def set_generator_id(r: schema.GeneratorRecord) -> None:
    r.ID = f"{r.bus_number}_{r.gen_id.strip()}"


def set_branch_id(r: schema.BranchRecord) -> None:
    r.ID = f"{r.from_bus_number}_{r.to_bus_number}_{r.circuit.strip()}"


def set_switch_id(r: schema.SwitchRecord) -> None:
    r.ID = f"{r.from_bus_number}_{r.to_bus_number}_{r.circuit.strip()}"


def set_transformer_id(r: schema.TransformerRecord) -> None:
    r.ID = f"{r.i}_{r.j}_{r.k}_{r.circuit.strip()}"


def set_switched_shunt_id(r: schema.SwitchedShuntRecord) -> None:
    r.ID = f"{r.bus_number}"


def set_facts_id(r: schema.FactsDeviceRecord) -> None:
    r.ID = f"{r.ibus}_{str(r.name).strip()}"


def set_induction_id(r: schema.InductionMachineRecord) -> None:
    r.ID = f"{r.bus_id}_{str(r.name).strip()}"


def set_interarea_id(r: schema.InterareaTransferRecord) -> None:
    r.ID = f"{r.from_area}_{r.to_area}_{str(r.transfer_id).strip()}"


def set_multi_terminal_dc_id(r: schema.MultiTerminalDCRecord) -> None:
    r.ID = f"{str(r.name).strip()}"


def set_vsc_id(r: schema.VscDcRecord) -> None:
    # Two records (rectifier + inverter) share NAME per DC line; ibus differs.
    r.ID = f"{str(r.name).strip()}_{r.ibus}"


def set_case_id(r: schema.CaseIdentificationRecord) -> None:
    # Singleton per file.
    r.ID = "CASE"


# Dispatcher keyed on record type. Record types absent from this map carry a
# single-field ``identifier: true`` in the schema (bus, area, zone, owner,
# two-terminal DC, multi-section line, impedance correction) and need no
# composite ID — GraphModel keys them directly on that field.
_DISPATCH = {
    schema.LoadRecord: set_load_id,
    schema.FixedShuntRecord: set_fixed_shunt_id,
    schema.GeneratorRecord: set_generator_id,
    schema.BranchRecord: set_branch_id,
    schema.SwitchRecord: set_switch_id,
    schema.TransformerRecord: set_transformer_id,
    schema.SwitchedShuntRecord: set_switched_shunt_id,
    schema.FactsDeviceRecord: set_facts_id,
    schema.InductionMachineRecord: set_induction_id,
    schema.InterareaTransferRecord: set_interarea_id,
    schema.MultiTerminalDCRecord: set_multi_terminal_dc_id,
    schema.VscDcRecord: set_vsc_id,
    schema.CaseIdentificationRecord: set_case_id,
}


def assign_composite_id(record: object) -> None:
    """Assign ``record.ID`` if the record type needs a composite identifier.

    No-op for record types that carry a single-field schema identifier.
    """
    setter = _DISPATCH.get(type(record))
    if setter is not None:
        setter(record)
