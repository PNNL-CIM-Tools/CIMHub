"""PSS/E RAW v34 reader: a ``.raw`` file -> ``GraphModel`` of RAW record dataclasses.

Usage::

    from cimhub_raw.raw34_reader import Raw34Reader
    import cimhub_raw.schema.raw_v34.raw34_schema as schema

    model = Raw34Reader("case.raw").read_all()
    for bus in model.list_by_class(schema.BusRecord):
        print(bus.bus_number, bus.name, bus.base_voltage)

How the file is read (RAW v34.9 Data Formats Reference, chapter 1):

- **Sections are positional.** After the case identification and system-wide data, the sections come in
  the fixed v34 order (``SECTIONS``). Each one ends with a record whose first field is ``0``; the text after
  it (``/ END OF BUS DATA, BEGIN LOAD DATA``) is a comment. A ``Q`` record ends the data; every later
  section is then empty.
- **Fields** are separated by a comma or by blanks. Two commas in a row leave a field blank, and a record
  may stop early: a blank or missing field is ``None``. Defaults are not filled here. The mapper fills them
  from the schema's ``raw_default`` annotations and lists what it filled. The one exception is
  ``composite_id``, whose keys use the default of a blank ID.
- **Field positions** come from the schema annotations (``record_layout``), the same ones the writer uses.
- **Extended bus names.** A quoted value in an integer field is an extended bus name, ``'NAME        kV'``
  (the 12-character bus name, then its base kV). It is resolved to the bus number, so every bus reference
  in the model is a number. A leading ``-`` gives the negated number.
- **Fail fast.** A REV other than 34, an unknown system-wide keyword, more fields than the record has, a
  value that does not convert, an extended name that matches no bus or two, a duplicate key, and a missing
  section terminator all raise ``Raw34ParseError`` with the line number. A populated VSC DC, impedance
  correction, multi-terminal DC or GNE section raises ``NotImplementedError``: their layouts are phase-2
  work (``.development/RAW_REWRITE_PLAN.md`` §4).
"""

from __future__ import annotations

import math
from pathlib import Path

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core import GraphModel
from cimhub_core.base import FormatReader
from cimhub_core.graph_model import _get_identifier
from cimhub_raw.record_layout import Slot, line_count, record_lines, terminal_slots
from cimhub_raw.schema.raw_v34 import composite_id

__all__ = ["Raw34Reader", "Raw34ParseError", "SECTIONS", "tokenize"]

REVISION = 34

#: The v34 sections in file order: (name in the section comments, record class). The substation section
#: (nested blocks) follows them and is read by ``_read_substations``.
SECTIONS: tuple[tuple[str, type], ...] = (
    ("BUS", schema.BusRecord),
    ("LOAD", schema.LoadRecord),
    ("FIXED SHUNT", schema.FixedShuntRecord),
    ("GENERATOR", schema.GeneratorRecord),
    ("BRANCH", schema.BranchRecord),
    ("SYSTEM SWITCHING DEVICE", schema.SwitchRecord),
    ("TRANSFORMER", schema.TransformerRecord),
    ("AREA", schema.AreaInterchangeRecord),
    ("TWO-TERMINAL DC", schema.TwoTerminalDCRecord),
    ("VSC DC LINE", schema.VscDcRecord),
    ("IMPEDANCE CORRECTION", schema.ImpedanceCorrectionRecord),
    ("MULTI-TERMINAL DC", schema.MultiTerminalDCRecord),
    ("MULTI-SECTION LINE", schema.MultiSectionLineRecord),
    ("ZONE", schema.ZoneRecord),
    ("INTER-AREA TRANSFER", schema.InterareaTransferRecord),
    ("OWNER", schema.OwnerRecord),
    ("FACTS DEVICE", schema.FactsDeviceRecord),
    ("SWITCHED SHUNT", schema.SwitchedShuntRecord),
    ("GNE", schema.GneDeviceRecord),
    ("INDUCTION MACHINE", schema.InductionMachineRecord),
)

#: Sections whose record structure is phase-2 work; a populated one raises.
PHASE_2_SECTIONS = frozenset({"VSC DC LINE", "IMPEDANCE CORRECTION", "MULTI-TERMINAL DC", "GNE"})

#: System-wide data records kept as their text, by keyword (RATING records become RatingRecords).
SYSTEM_WIDE_KEYWORDS = ("GENERAL", "GAUSS", "NEWTON", "ADJUST", "TYSL", "SOLVER")


class Raw34ParseError(Exception):
    """A RAW file that this reader cannot read as v34, with the file and line."""

    def __init__(self, message: str, *, source: object, line_number: int | None = None, text: str | None = None):
        location = f"{source}:{line_number}" if line_number else str(source)
        detail = f"\n  {text.strip()}" if text else ""
        super().__init__(f"{location}: {message}{detail}")
        self.line_number = line_number


class Token(str):
    """One field's text; ``quoted`` says whether the file put it in quotes."""

    quoted: bool

    def __new__(cls, text: str, quoted: bool) -> "Token":
        token = super().__new__(cls, text)
        token.quoted = quoted
        return token


def tokenize(text: str) -> list[Token | None]:
    """The fields of one record line; ``None`` is a blank field (two commas in a row).

    Fields are separated by a comma or by blanks. A quoted field (``'...'`` or ``"..."``) may hold commas
    and blanks. An unquoted ``/`` starts a comment, which runs to the end of the line.
    """
    tokens: list[Token | None] = []
    position, length = 0, len(text)
    expecting_field = True  # at the start or after a comma, another comma means a blank field
    while True:
        while position < length and text[position] in " \t":
            position += 1
        if position >= length or text[position] == "/":
            return tokens
        character = text[position]
        if character == ",":
            if expecting_field:
                tokens.append(None)
            expecting_field = True
            position += 1
            continue
        if character in "'\"":
            end = text.find(character, position + 1)
            if end < 0:
                raise ValueError(f"unclosed quote at column {position + 1}")
            tokens.append(Token(text[position + 1:end], quoted=True))
            position = end + 1
        else:
            end = position
            while end < length and text[end] not in " \t,/":
                end += 1
            tokens.append(Token(text[position:end], quoted=False))
            position = end
        expecting_field = False


def _is_terminator(tokens: list[Token | None]) -> bool:
    """A section (or a part of a substation block) ends with a record whose first field is a bare ``0``."""
    return bool(tokens) and tokens[0] is not None and not tokens[0].quoted and tokens[0] == "0"


def _is_q(text: str) -> bool:
    return text.strip().upper() == "Q"


class Raw34Reader(FormatReader):
    """Read a PSS/E RAW v34 file into a ``GraphModel`` keyed ``graph[RecordClass][identifier]``."""

    def __init__(self, source: str | Path) -> None:
        """Bind ``source`` (a ``.raw`` file path) without reading it."""
        self.source = source
        self._model: GraphModel | None = None

    def read_all(self) -> GraphModel:
        """Read the bound file once; later calls return the same model."""
        if self._model is None:
            self._model = _FileReader(Path(self.source)).read()
        return self._model


class _FileReader:
    """One read of one file: its lines, the bus table for extended names, and the keys seen so far."""

    def __init__(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"RAW file not found: {path}")
        self.path = path
        self.lines = path.read_text(encoding="utf-8").splitlines()
        self.index = 0  # the next line to read
        self.model = GraphModel()
        self.first_line_of: dict[tuple[type, str], int] = {}
        self.buses_by_extended_name: dict[tuple[str, float], list[int]] = {}
        self.ended = False  # a Q record was read

    def error(self, message: str, line_number: int | None = None, text: str | None = None) -> Raw34ParseError:
        return Raw34ParseError(message, source=self.path, line_number=line_number, text=text)

    # -- lines -----------------------------------------------------------------------------------

    def _skip_comments(self) -> None:
        while self.index < len(self.lines) and self.lines[self.index].lstrip().startswith("@!"):
            self.index += 1

    def at_end(self) -> bool:
        self._skip_comments()
        return self.index >= len(self.lines)

    def next_line(self, *, verbatim: bool = False) -> tuple[int, str]:
        """The next line and its 1-based number; ``@!`` comment lines are skipped unless ``verbatim``."""
        if not verbatim:
            self._skip_comments()
        if self.index >= len(self.lines):
            raise self.error("the file ends inside a record")
        self.index += 1
        return self.index, self.lines[self.index - 1]

    # -- the file --------------------------------------------------------------------------------

    def read(self) -> GraphModel:
        line_number, case = self._read_case()
        self._add(case, line_number)
        for section, record_class in SECTIONS:
            records = self._read_section(section, record_class)
            if records and section in PHASE_2_SECTIONS:
                raise NotImplementedError(
                    f"{self.path}: the {section} section has {len(records)} record(s); its layout is phase-2 "
                    f"work (.development/RAW_REWRITE_PLAN.md §4)")
            for record_line, record in records:
                self._add(record, record_line)
            if record_class is schema.BusRecord:
                self._index_bus_names()
        self._read_substations()
        if not self.ended and not self.at_end():
            line_number, text = self.next_line()
            if not _is_q(text):
                raise self.error("data after the last section (expected Q)", line_number, text)
        return self.model

    def _add(self, record: object, line_number: int) -> None:
        composite_id.assign_composite_id(record)
        key = (type(record), _get_identifier(record))
        if key in self.first_line_of:
            raise self.error(f"duplicate {type(record).__name__} {key[1]!r} (first on line "
                             f"{self.first_line_of[key]})", line_number)
        self.first_line_of[key] = line_number
        self.model.add_to_graph(record)

    # -- case identification and system-wide data ------------------------------------------------

    def _read_case(self) -> tuple[int, schema.CaseIdentificationRecord]:
        line_number, text = self.next_line()
        values = self._values(schema.CaseIdentificationRecord, record_lines(schema.CaseIdentificationRecord)[0],
                              self._tokens(line_number, text), line_number, text)
        if values["revision"] != REVISION:
            raise self.error(f"REV is {values['revision']!r}; this reader reads RAW v{REVISION} only",
                             line_number, text)
        titles = [self.next_line(verbatim=True)[1], self.next_line(verbatim=True)[1]]
        system_wide: dict[str, str] = {}
        ratings: list[schema.RatingRecord] = []
        while True:
            record_line, record_text = self.next_line()
            tokens = self._tokens(record_line, record_text)
            if _is_terminator(tokens):
                break
            keyword = str(tokens[0] or "").upper() if tokens else ""
            if keyword == "RATING":
                ratings.append(self._record(schema.RatingRecord, record_lines(schema.RatingRecord)[0], tokens[1:],
                                            record_line, record_text))
            elif keyword in SYSTEM_WIDE_KEYWORDS:
                if keyword.lower() in system_wide:
                    raise self.error(f"a second {keyword} record", record_line, record_text)
                system_wide[keyword.lower()] = record_text.strip()
            else:
                raise self.error(f"unknown system-wide data record {keyword!r}", record_line, record_text)
        case = self._construct(schema.CaseIdentificationRecord,
                               {**values, **system_wide, "titles": titles, "ratings": ratings}, line_number)
        return line_number, case

    # -- sections --------------------------------------------------------------------------------

    def _next_record_tokens(self, where: str) -> tuple[int, str, list[Token | None]] | None:
        """The first line of the next record of ``where``, or ``None`` at its 0 record or at a Q record."""
        if self.at_end():
            raise self.error(f"the file ends inside {where} (no 0 record)")
        line_number, text = self.next_line()
        if _is_q(text):
            self.ended = True
            return None
        tokens = self._tokens(line_number, text)
        if not tokens:
            raise self.error(f"a blank line where a record of {where} or its 0 record belongs", line_number)
        if _is_terminator(tokens):
            return None
        return line_number, text, tokens

    def _read_section(self, section: str, record_class: type) -> list[tuple[int, object]]:
        """Every record of one section, each with the line it starts on."""
        records: list[tuple[int, object]] = []
        layout = record_lines(record_class)
        while not self.ended:
            first = self._next_record_tokens(f"the {section} section")
            if first is None:
                break
            line_number, text, tokens = first
            values = self._values(record_class, layout[0], tokens, line_number, text)
            for index in range(1, line_count(record_class, values)):
                next_number, next_text = self.next_line()
                if _is_q(next_text):
                    raise self.error(f"a Q record inside a {record_class.__name__}", next_number)
                values.update(self._values(record_class, layout[index], self._tokens(next_number, next_text),
                                           next_number, next_text))
            records.append((line_number, self._construct(record_class, values, line_number)))
        return records

    def _read_substations(self) -> None:
        """The SUBSTATION section: blocks of a substation record, then its nodes, switching devices and
        equipment terminals, each part ended by its own 0 record."""
        while not self.ended:
            first = self._next_record_tokens("the SUBSTATION section")
            if first is None:
                return
            line_number, text, tokens = first
            substation = self._record(schema.SubstationRecord, record_lines(schema.SubstationRecord)[0], tokens,
                                      line_number, text)
            self._add(substation, line_number)
            where = f"substation {substation.substation_number}"
            for part_class in (schema.SubstationNodeRecord, schema.StationSwitchingDeviceRecord,
                               schema.EquipmentTerminalRecord):
                for part_line, part_text, part_tokens in self._part(where):
                    if part_class is schema.EquipmentTerminalRecord:
                        slots = self._terminal_slots(part_tokens, part_line, part_text)
                    else:
                        slots = record_lines(part_class)[0]
                    values = self._values(part_class, slots, part_tokens, part_line, part_text)
                    values["substation_number"] = substation.substation_number
                    self._add(self._construct(part_class, values, part_line), part_line)

    def _part(self, where: str):
        """The records of one part of a substation block, up to its 0 record."""
        while True:
            if self.at_end():
                raise self.error(f"the file ends inside {where} (no 0 record)")
            line_number, text = self.next_line()
            tokens = self._tokens(line_number, text)
            if _is_terminator(tokens):
                return
            if not tokens:
                raise self.error(f"a blank line inside {where}", line_number)
            yield line_number, text, tokens

    def _terminal_slots(self, tokens, line_number: int, text: str) -> tuple[Slot, ...]:
        if len(tokens) < 3 or tokens[2] is None:
            raise self.error("an equipment terminal record without its type (third field)", line_number, text)
        try:
            return terminal_slots(str(tokens[2]).strip().upper())
        except ValueError as exc:
            raise self.error(str(exc), line_number, text) from exc

    # -- fields ----------------------------------------------------------------------------------

    def _tokens(self, line_number: int, text: str) -> list[Token | None]:
        try:
            return tokenize(text)
        except ValueError as exc:
            raise self.error(str(exc), line_number, text) from exc

    def _record(self, record_class: type, slots: tuple[Slot, ...], tokens, line_number: int, text: str):
        return self._construct(record_class, self._values(record_class, slots, tokens, line_number, text),
                               line_number)

    def _construct(self, record_class: type, values: dict, line_number: int):
        try:
            return record_class(**values)
        except (ValueError, TypeError) as exc:  # the dataclass's own checks, e.g. a required field left blank
            raise self.error(f"{record_class.__name__}: {exc}", line_number) from exc

    def _values(self, record_class: type, slots: tuple[Slot, ...], tokens, line_number: int, text: str) -> dict:
        """Slot name -> value for the tokens of one line; missing and blank fields are ``None``."""
        capacity = sum(slot.count for slot in slots)
        if len(tokens) > capacity:
            raise self.error(f"{record_class.__name__}: {len(tokens)} fields where the record has {capacity}",
                             line_number, text)
        values: dict = {}
        position = 0
        for slot in slots:
            chunk = tokens[position:position + slot.count]
            position += slot.count
            try:
                converted = [self._convert(slot, token) for token in chunk]
            except ValueError as exc:
                raise self.error(f"{record_class.__name__}.{slot.name}: {exc}", line_number, text) from exc
            if slot.count == 1:
                values[slot.name] = converted[0] if converted else None
            else:
                values[slot.name] = converted if any(value is not None for value in converted) else None
        return values

    def _convert(self, slot: Slot, token: Token | None):
        if token is None:
            return None
        if slot.value_type == "int":
            if token.quoted:
                return self._bus_number(token)
            number = float(token)
            if not number.is_integer():
                raise ValueError(f"{str(token)!r} is not an integer")
            return int(number)
        if slot.value_type == "float":
            if token.quoted:
                raise ValueError(f"{str(token)!r} is quoted where a number belongs")
            value = float(token)
            if not math.isfinite(value):
                raise ValueError(f"{str(token)!r} is not a finite number")
            return value
        return str(token).rstrip()

    # -- extended bus names ----------------------------------------------------------------------

    def _index_bus_names(self) -> None:
        for bus in self.model.list_by_class(schema.BusRecord):
            key = ((bus.name or "").rstrip(), float(bus.base_voltage or 0.0))
            self.buses_by_extended_name.setdefault(key, []).append(bus.bus_number)

    def _bus_number(self, token: Token) -> int:
        """The bus number of an extended bus name ``'NAME        kV'``; a leading ``-`` negates it."""
        text = str(token)
        sign = 1
        if text.startswith("-"):
            sign, text = -1, text[1:]
        if len(text) <= 12:
            raise ValueError(f"extended bus name {str(token)!r} has no base voltage after its 12-character name")
        name, kv_text = text[:12].rstrip(), text[12:].strip()
        try:
            kv = float(kv_text)
        except ValueError as exc:
            raise ValueError(f"extended bus name {str(token)!r}: {kv_text!r} is not a base voltage") from exc
        matches = [number for (bus_name, bus_kv), numbers in self.buses_by_extended_name.items()
                   if bus_name == name and math.isclose(bus_kv, kv, rel_tol=1e-6) for number in numbers]
        if len(matches) != 1:
            found = "no bus" if not matches else f"buses {matches}"
            raise ValueError(f"extended bus name {str(token)!r} matches {found}")
        return sign * matches[0]
