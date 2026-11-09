"""What an exporter module does with each field of its GDM classes (``EXPORT_MAPPING.md#layout``).

The export mirror of the importer's ``FIELDS``: every field is listed, so nothing is dropped unnoticed, and the
spec's tables are generated from it (``slots_table``).
"""

from __future__ import annotations

from typing import NamedTuple

#: ``written``: from a getter or the CIM structure; ``rule``: a CIM ``None`` or shape GDM needs, by a written rule;
#: ``fill``: a required field CIM cannot hold, a named constant in ``fills.py`` (decision X4); ``unset``: left at
#: GDM's default.
KINDS = ("written", "rule", "fill", "unset")


class Slot(NamedTuple):
    kind: str
    note: str = ""


def check_slots(slots: dict[str, Slot], gdm_class: type) -> None:
    """Every field of ``gdm_class`` is listed, no other, each with a known kind."""
    expected = set(gdm_class.model_fields)
    missing, extra = expected - slots.keys(), slots.keys() - expected
    if missing or extra:
        raise ValueError(f"{gdm_class.__name__} SLOTS: missing {sorted(missing)}, not fields {sorted(extra)}")
    bad = {name: slot.kind for name, slot in slots.items() if slot.kind not in KINDS}
    if bad:
        raise ValueError(f"{gdm_class.__name__} SLOTS: unknown kinds {bad}")


def slots_table(slots: dict[str, Slot]) -> str:
    """The spec's markdown table of ``slots``."""
    rows = ["| GDM field | kind | from / why |", "|---|---|---|"]
    rows += [f"| {name} | {slot.kind} | {slot.note} |" for name, slot in slots.items()]
    return "\n".join(rows)


UUID = Slot("unset", "GDM makes a fresh one; the importer never copies it either")
