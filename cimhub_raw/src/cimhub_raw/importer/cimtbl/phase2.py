"""The shared body of the phase-2 stub mappers (RAW_REWRITE_PLAN.md §4.2).

A phase-2 table has no mapping yet. Its stub returns an empty document when the case has no records of the
table, so the table writes no part and no ``Import``, and raises when it has some, so a case that uses the table
fails at once and names it instead of losing those records.
"""

from __future__ import annotations

from cimtables.document import Document

from cimhub_core.cimtbl import CIM_PROFILE


def not_mapped_yet(native, native_class: type, table: str) -> Document:
    """An empty ``table`` document, or ``NotImplementedError`` if ``native`` holds a ``native_class`` record."""
    count = len(native.list_by_class(native_class))
    if count:
        raise NotImplementedError(
            f"RAW {native_class.__name__}: {count} record(s), but the table is phase 2 and not mapped yet "
            f"(.development/RAW_REWRITE_PLAN.md §4)"
        )
    return Document(name=table, statements=[], profile=CIM_PROFILE)
