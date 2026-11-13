"""DistOPF CSV layout: which file holds each record class, and its columns.

Shared by the reader and the writer. The schema annotations are the single source of truth for the columns.
"""

from __future__ import annotations

from functools import cache

from cimhub_core.serialization import get_schema_annotations

from cimhub_distopf.schema.distopf import (
    BatteryRecord,
    BranchRecord,
    BusRecord,
    CapacitorRecord,
    GeneratorRecord,
    RegulatorRecord,
    ScheduleRecord,
)

__all__ = ["CSV_FILES", "csv_columns"]

# DistOPF CSV file for each record class, in read/write order.
CSV_FILES: dict[type, str] = {
    BusRecord: "bus_data.csv",
    BranchRecord: "branch_data.csv",
    GeneratorRecord: "gen_data.csv",
    CapacitorRecord: "cap_data.csv",
    BatteryRecord: "bat_data.csv",
    RegulatorRecord: "reg_data.csv",
    ScheduleRecord: "schedules.csv",
}


@cache
def csv_columns(record_cls: type) -> list[tuple[str, str, dict]]:
    """Return ``(field_name, column_name, annotations)`` for each CSV column, in column order.

    A field is a CSV column only if its schema slot has an ``order`` annotation (RegulatorRecord's synthetic
    ``id`` is not). The column name is the ``native_name`` annotation when present (``branch_type`` is written
    as ``type``).
    """
    annotations = get_schema_annotations(record_cls)
    columns = [
        (annot["order"], field, annot.get("native_name", field), annot)
        for field, annot in annotations.items()
        if "order" in annot
    ]
    return [(field, column, annot) for _, field, column, annot in sorted(columns, key=lambda c: c[0])]
