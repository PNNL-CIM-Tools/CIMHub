"""CSV reader for distOPF native file format.

Parses one CSV file per record class into LinkML-generated dataclass
instances; columns are matched by name (see
:func:`cimhub_distopf.common.csv_columns`).

Usage::

    from cimhub_distopf.distopf_reader import DistopfReader
    import cimhub_distopf.schema.distopf as schema

    model = DistopfReader("path/to/csv/dir").read_all()
    buses = model.list_by_class(schema.BusRecord)
"""

from __future__ import annotations

import csv
import logging
from dataclasses import fields
from pathlib import Path

from cimhub_core.base import FormatReader
from cimhub_core.graph_model import GraphModel

from cimhub_distopf.csv_layout import CSV_FILES, csv_columns
from cimhub_distopf.schema.distopf import RegulatorRecord

__all__ = ["DistopfReader"]

_log = logging.getLogger(__name__)


class DistopfReader(FormatReader):
    """Parse a directory of distOPF CSV files into a GraphModel.

    Source is bound at construction; parsing is deferred to :meth:`read_all`.
    """

    def __init__(self, source: str | Path | None = None) -> None:
        """Bind *source*, the directory holding the distOPF CSV files."""
        self.source = source
        self._model: GraphModel | None = None

    def read_all(self) -> GraphModel:
        """Parse every distOPF CSV in the source directory (cached).

        Missing CSV files produce empty buckets.

        Raises:
            ValueError: If no source was bound at construction.
        """
        if self.source is None:
            raise ValueError(
                "DistopfReader.read_all() requires a source directory. "
                "Pass it to __init__: DistopfReader('/path/to/csv/dir').read_all()"
            )
        if self._model is None:
            model = GraphModel()
            for record_cls in CSV_FILES:
                for record in self.read(self.source, record_cls):
                    model.add_to_graph(record)
            _log.info("Read distOPF directory: %s", model)
            self._model = model
        return self._model

    def read(self, source: str | Path, record_cls: type) -> list:
        """Read the CSV for *record_cls* from *source*; [] if the file is absent.

        Empty cells are left out so the schema's ``ifabsent`` defaults apply.
        Columns the schema does not define are ignored with a warning.

        Raises:
            ValueError: If a row cannot be parsed (the message names the line).
        """
        file_path = Path(source) / CSV_FILES[record_cls]
        if not file_path.exists():
            return []

        column_to_field = {column: field for field, column, _ in csv_columns(record_cls)}
        field_types = {f.name: str(f.type).lower() for f in fields(record_cls)}

        records = []
        with open(file_path, "r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            ignored = [c for c in reader.fieldnames or [] if c not in column_to_field]
            if ignored:
                _log.warning("%s: ignoring columns not in the distOPF schema: %s", file_path.name, ignored)
            for line_num, row in enumerate(reader, start=2):
                kwargs = {}
                try:
                    for column, raw in row.items():
                        field = column_to_field.get(column)
                        value = (raw or "").strip()
                        if field is None or value == "" or value.lower() in ("none", "nan"):
                            continue
                        if "bool" in field_types[field]:
                            kwargs[field] = value.lower() in ("true", "t", "1", "yes")
                        elif "int" in field_types[field]:
                            kwargs[field] = int(float(value))  # accepts "365.0"
                        elif "float" in field_types[field]:
                            kwargs[field] = float(value)
                        else:
                            kwargs[field] = value
                    if record_cls is RegulatorRecord:
                        kwargs["id"] = f"{kwargs['fb']}_{kwargs['tb']}"
                    records.append(record_cls(**kwargs))
                except (KeyError, TypeError, ValueError) as e:
                    raise ValueError(f"Error reading {record_cls.__name__} at line {line_num} of {file_path.name}: {e}") from e
        return records
