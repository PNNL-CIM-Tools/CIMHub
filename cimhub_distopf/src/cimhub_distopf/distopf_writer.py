"""CSV writer for distOPF native file format.

Writes one CSV per record class, with columns, order, and number formatting
taken from the LinkML schema annotations (see
:func:`cimhub_distopf.common.csv_columns`).

Usage::

    from cimhub_distopf.distopf_reader import DistopfReader
    from cimhub_distopf.distopf_writer import DistopfWriter

    model = DistopfReader("path/to/case").read_all()
    DistopfWriter().write(model, "path/to/output/dir")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cimhub_core import GraphModel
from cimhub_core.base import FormatWriter
from cimhub_core.serialization import format_by_spec

from cimhub_distopf.csv_layout import CSV_FILES, csv_columns

__all__ = ["DistopfWriter"]


class DistopfWriter(FormatWriter):
    """Write distOPF records to one CSV file per record class."""

    def write(self, model: GraphModel, destination: str) -> None:
        """Write every record in *model* to CSV files in *destination* (created if absent)."""
        dest = Path(destination)
        dest.mkdir(parents=True, exist_ok=True)

        for cls, instances in model.graph.items():
            if not instances:
                continue
            header = ",".join(column for _, column, _ in csv_columns(cls))
            with open(dest / CSV_FILES[cls], "w", encoding="utf-8", newline="") as fh:
                fh.write(header + "\n")
                for obj in instances.values():
                    fh.write(self.serialize(obj) + "\n")

    def serialize(self, obj: Any) -> str:
        """Serialize one record to a CSV row matching its class's header."""
        return ",".join(
            format_by_spec(getattr(obj, field), annot) for field, _, annot in csv_columns(type(obj))
        )
