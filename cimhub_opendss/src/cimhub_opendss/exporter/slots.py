"""What an exporter module does with each slot of its DSS class (``EXPORT_MAPPING.md#layout``).

The export mirror of the importer's ``FIELDS``: every schema slot is listed, so nothing is dropped unnoticed, and
the spec's tables are generated from it (``slots_table``).
"""

from __future__ import annotations

from dataclasses import fields
from typing import NamedTuple

#: ``written``: from a getter; ``rule``: a CIM ``None`` DSS needs (decision E4); ``unset``: CIM cannot hold it, the
#: engine default applies; ``not mapped``: a form of the same data that is not written.
KINDS = ("written", "rule", "unset", "not mapped")


class Slot(NamedTuple):
    kind: str
    note: str = ""


def check_slots(slots: dict[str, Slot], native_class: type) -> None:
    """Every slot of ``native_class`` is listed, no other, each with a known kind."""
    expected = {f.name for f in fields(native_class)}
    missing, extra = expected - slots.keys(), slots.keys() - expected
    if missing or extra:
        raise ValueError(f"{native_class.__name__} SLOTS: missing {sorted(missing)}, not slots {sorted(extra)}")
    bad = {name: slot.kind for name, slot in slots.items() if slot.kind not in KINDS}
    if bad:
        raise ValueError(f"{native_class.__name__} SLOTS: unknown kinds {bad}")


def slots_table(slots: dict[str, Slot]) -> str:
    """The spec's markdown table of ``slots``."""
    rows = ["| DSS slot | kind | from / why |", "|---|---|---|"]
    rows += [f"| {name} | {slot.kind} | {slot.note} |" for name, slot in slots.items()]
    return "\n".join(rows)
