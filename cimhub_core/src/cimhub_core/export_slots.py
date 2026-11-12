"""What an exporter module does with each slot of its native class: the export mirror of the importer's ``FIELDS``.

Every schema slot is listed, so nothing is dropped unnoticed, and each spoke's spec tables are generated from it
(``slots_table``). Shared by the DSS and RAW exporters (``EXPORT_MAPPING.md#layout`` in each).
"""

from __future__ import annotations

from dataclasses import fields
from typing import NamedTuple

#: ``written``: from a getter; ``rule``: a CIM ``None`` the format needs (DSS E4); ``unset``: CIM cannot hold it, the
#: format's default applies; ``not mapped``: a form of the same data that is not written.
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


def with_default(native_class: type, written: dict[str, Slot], other: Slot) -> dict[str, Slot]:
    """``written`` and every other slot of ``native_class`` as ``other``, in the schema's order."""
    return {f.name: written.get(f.name, other) for f in fields(native_class)}


def slots_table(slots: dict[str, Slot], format_name: str) -> str:
    """The spec's markdown table of ``slots``, headed ``<format_name> slot``."""
    rows = [f"| {format_name} slot | kind | from / why |", "|---|---|---|"]
    rows += [f"| {name} | {slot.kind} | {slot.note} |" for name, slot in slots.items()]
    return "\n".join(rows)
