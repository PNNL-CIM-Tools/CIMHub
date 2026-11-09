"""Record helpers the RAW mappers share."""

from __future__ import annotations

from cimhub_core.cimtbl import Field, cell, fill_defaults, schema_defaults


def raw_defaults(native_cls: type) -> dict[str, object]:
    """The class's ``raw_default``s, less the blank-string ones: a blank NAME "defaulted" to blank says nothing,
    and the mapper's own rule for a blank name applies."""
    return {slot: value for slot, value in schema_defaults(native_cls, "raw_default").items() if value != ""}


def fill_keyed_defaults(fields: dict[str, Field], record, defaults: dict[str, object]):
    """``fill_defaults`` that keeps the reader's composite ``record.ID``, which ``dataclasses.replace`` drops
    (core request C6)."""
    filled, comment = fill_defaults(fields, record, defaults)
    filled.ID = record.ID
    return filled, comment


def listed_off_default(record, slots, defaults: dict[str, object]) -> str | None:
    """``untranscribed: a=1.0, b=2``: the ``slots`` CIM cannot hold whose value is not the default (a blank one, or
    one with no default, counts as unset), listed on the record's row; ``None`` when there are none."""
    values = [(slot, getattr(record, slot)) for slot in slots]
    off = [(slot, value) for slot, value in values if value not in (None, "") and value != defaults.get(slot, value)]
    if not off:
        return None
    return "untranscribed: " + ", ".join(f"{slot}={cell(value)}" for slot, value in off)
