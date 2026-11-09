"""PSS/E RAW v34 writer: a ``GraphModel`` of RAW record dataclasses -> a ``.raw`` file.

Usage::

    from cimhub_raw.raw34_reader import Raw34Reader
    from cimhub_raw.raw34_writer import Raw34Writer

    Raw34Writer().write(Raw34Reader("input.raw").read_all(), "output.raw")

The writer is the reader's mirror and walks the same layout (``record_layout``):

- Fields are written by position. A ``None`` field is written blank (two commas in a row), and trailing
  blank fields are left off, so the writer writes back only what was read. Nothing is defaulted.
- A float keeps its value: the schema's ``precision`` is used when it reads back the same number, otherwise
  the shortest exact form (``repr``). A string is padded to its ``width`` and quoted as the schema says.
- Records come out in the model's insertion order, which is the file order for a model the reader built.
- The two title lines are written verbatim, always two.
- Bus references are written as numbers, never as extended names.
- Phase-2 record types (VSC DC, impedance correction, multi-terminal DC, GNE) raise ``NotImplementedError``,
  as in the reader.
"""

from __future__ import annotations

from pathlib import Path

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core import GraphModel
from cimhub_core.base import FormatWriter
from cimhub_raw.raw34_reader import PHASE_2_SECTIONS, SECTIONS, SYSTEM_WIDE_KEYWORDS
from cimhub_raw.record_layout import Slot, line_count, record_lines, terminal_slots

__all__ = ["Raw34Writer", "format_field"]

SUBSTATION_PARTS = ("SUBSTATION NODE", "SUBSTATION SWITCHING DEVICE", "SUBSTATION TERMINAL")


def format_field(slot: Slot, value) -> str:
    """One field's text; ``None`` is blank."""
    if value is None:
        return ""
    if slot.value_type == "int":
        return str(int(value))
    if slot.value_type == "float":
        value = float(value)
        precision = slot.annotations.get("precision")
        if precision is not None:
            text = f"{value:.{int(precision)}f}"
            if float(text) == value:
                return text
        return repr(value)
    text = str(value)
    width = slot.annotations.get("width")
    if width:
        text = text.ljust(int(width))
    if slot.annotations.get("quote"):
        quote = slot.annotations.get("quote_char", "'")
        text = f"{quote}{text}{quote}"
    return text


def format_line(slots: tuple[Slot, ...], record: object) -> str:
    """One record line: its fields by position, blank for ``None``, trailing blanks left off."""
    fields: list[str] = []
    for slot in slots:
        value = getattr(record, slot.name)
        if slot.count == 1:
            fields.append(format_field(slot, value))
            continue
        values = list(value or [])
        if len(values) > slot.count:
            raise ValueError(f"{type(record).__name__}.{slot.name}: {len(values)} values for {slot.count} fields")
        fields.extend(format_field(slot, item) for item in values + [None] * (slot.count - len(values)))
    while fields and fields[-1] == "":
        fields.pop()
    return ",".join(fields)


def format_record(record: object) -> list[str]:
    """Every line of one record."""
    record_class = type(record)
    layout = record_lines(record_class)
    first_line = {slot.name: getattr(record, slot.name) for slot in layout[0]}
    return [format_line(layout[index], record) for index in range(line_count(record_class, first_line))]


class Raw34Writer(FormatWriter):
    """Write a ``GraphModel`` of RAW v34 records to a ``.raw`` file."""

    def write(self, model: GraphModel, destination: str) -> None:
        """Write every record of ``model`` to the file ``destination``."""
        Path(destination).write_text("\n".join(self.lines(model)) + "\n", encoding="utf-8")

    def serialize(self, obj) -> str:
        """One record as RAW text (several lines for a multi-line record)."""
        return "\n".join(format_record(obj))

    def lines(self, model: GraphModel) -> list[str]:
        """The whole file, line by line."""
        case = model.first(schema.CaseIdentificationRecord)
        if case is None:
            raise ValueError("the model has no CaseIdentificationRecord")
        lines = self._case_lines(case)
        previous = "SYSTEM-WIDE"
        for section, record_class in SECTIONS:
            records = list(model.iter_by_class(record_class))
            if records and section in PHASE_2_SECTIONS:
                raise NotImplementedError(
                    f"{len(records)} {record_class.__name__}(s): writing the {section} section is phase-2 work")
            lines.append(f"0 / END OF {previous} DATA, BEGIN {section} DATA")
            for record in records:
                lines.extend(format_record(record))
            previous = section
        lines.append(f"0 / END OF {previous} DATA, BEGIN SUBSTATION DATA")
        lines.extend(self._substation_lines(model))
        lines.append("0 / END OF SUBSTATION DATA")
        lines.append("Q")
        return lines

    @staticmethod
    def _case_lines(case: schema.CaseIdentificationRecord) -> list[str]:
        titles = list(case.titles or [])
        if len(titles) > 2:
            raise ValueError(f"the case has {len(titles)} title lines; RAW has two")
        lines = [format_line(record_lines(schema.CaseIdentificationRecord)[0], case)]
        lines.extend(titles + [""] * (2 - len(titles)))
        for keyword in SYSTEM_WIDE_KEYWORDS:
            text = getattr(case, keyword.lower())
            if text:
                lines.append(text)
        rating_slots = record_lines(schema.RatingRecord)[0]
        for rating in case.ratings or []:
            lines.append("RATING," + format_line(rating_slots, rating))
        return lines

    @staticmethod
    def _substation_lines(model: GraphModel) -> list[str]:
        parts_by_substation: dict[int, tuple[list, list, list]] = {}
        for substation in model.iter_by_class(schema.SubstationRecord):
            parts_by_substation[substation.substation_number] = ([], [], [])
        for index, part_class in enumerate((schema.SubstationNodeRecord, schema.StationSwitchingDeviceRecord,
                                            schema.EquipmentTerminalRecord)):
            for record in model.iter_by_class(part_class):
                if record.substation_number not in parts_by_substation:
                    raise ValueError(f"{part_class.__name__} {record.ID}: no substation {record.substation_number}")
                parts_by_substation[record.substation_number][index].append(record)
        lines: list[str] = []
        for substation in model.iter_by_class(schema.SubstationRecord):
            nodes, switches, terminals = parts_by_substation[substation.substation_number]
            lines.extend(format_record(substation))
            lines.extend(line for record in nodes for line in format_record(record))
            lines.append(f"0 / END OF {SUBSTATION_PARTS[0]} DATA, BEGIN {SUBSTATION_PARTS[1]} DATA")
            lines.extend(line for record in switches for line in format_record(record))
            lines.append(f"0 / END OF {SUBSTATION_PARTS[1]} DATA, BEGIN {SUBSTATION_PARTS[2]} DATA")
            for terminal in terminals:
                lines.append(format_line(terminal_slots(str(terminal.terminal_type).upper()), terminal))
            lines.append(f"0 / END OF {SUBSTATION_PARTS[2]} DATA")
        return lines
