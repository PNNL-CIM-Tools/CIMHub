"""Record helpers the RAW mappers share."""

from __future__ import annotations

from cimhub_core.cimtbl import Field, fill_defaults, schema_defaults


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
