"""raw RAW v34 File Reader

This module provides a FormatReader implementation for PSS/E RAW version 34
files. It parses complete RAW files into a ``cimhub_core.GraphModel`` keyed as
``graph[RecordClass][identifier]``, using the LinkML-generated schema.

Usage::

    from cimhub_raw.raw34_reader import Raw34Reader
    import cimhub_raw.schema.raw_v34.raw34_schema as schema

    graph = Raw34Reader("network.raw").read_all()

    # Access records
    for bus in graph.list_by_class(schema.BusRecord):
        print(f"{bus.name}: {bus.base_voltage} kV")

The source is bound at construction and parsed once, on the first ``read_all()``
call; the result is cached, so repeated calls are free.

Features:
    - Handles all 19 raw RAW v34 record types
    - Multi-line record support (transformers, DC lines, FACTS, etc.)
    - Clear error messages with line numbers
    - Robust parsing with defaults from schema
"""

from __future__ import annotations

import csv
import io
import logging
import re
from pathlib import Path
from typing import Any

from cimhub_core.base import FormatReader
from cimhub_core import GraphModel
import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_raw.schema.raw_v34 import composite_id

__all__ = ["Raw34Reader", "Raw34ParseError"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------

class Raw34ParseError(Exception):
    """Error parsing raw RAW v34 file."""

    def __init__(
        self,
        message: str,
        line_number: int = None,
        line_content: str = None,
        section: str = None
    ):
        """Initialize parse error with context.

        Args:
            message: Error description
            line_number: Line number where error occurred (1-based)
            line_content: Content of the line that caused the error
            section: Name of the section being parsed
        """
        self.line_number = line_number
        self.line_content = line_content
        self.section = section

        full_message = message
        if section:
            full_message = f"[{section}] {full_message}"
        if line_number:
            full_message += f" (line {line_number})"
        if line_content:
            full_message += f"\n  Content: {line_content.strip()}"

        super().__init__(full_message)


# ---------------------------------------------------------------------------
# Section Markers
# ---------------------------------------------------------------------------

SECTION_MAP = {
    'CASE': ('', '0 / END OF SYSTEM-WIDE DATA'),
    'BUS': ('BEGIN BUS DATA', '0 / END OF BUS DATA'),
    'LOAD': ('BEGIN LOAD DATA', '0 / END OF LOAD DATA'),
    'FIXED_SHUNT': ('BEGIN FIXED SHUNT DATA', '0 / END OF FIXED SHUNT DATA'),
    'GENERATOR': ('BEGIN GENERATOR DATA', '0 / END OF GENERATOR DATA'),
    'BRANCH': ('BEGIN BRANCH DATA', '0 / END OF BRANCH DATA'),
    'SWITCH': ('BEGIN SYSTEM SWITCHING DEVICE DATA', '0 / END OF SYSTEM SWITCHING DEVICE DATA'),
    'TRANSFORMER': ('BEGIN TRANSFORMER DATA', '0 / END OF TRANSFORMER DATA'),
    'AREA': ('BEGIN AREA DATA', '0 / END OF AREA DATA'),
    'TWO_TERM_DC': ('BEGIN TWO-TERMINAL DC DATA', '0 / END OF TWO-TERMINAL DC DATA'),
    'VSC_DC': ('BEGIN VSC DC LINE DATA', '0 / END OF VSC DC LINE DATA'),
    'IMPEDANCE': ('BEGIN IMPEDANCE CORRECTION DATA', '0 / END OF IMPEDANCE CORRECTION DATA'),
    'MULTI_TERM_DC': ('BEGIN MULTI-TERMINAL DC DATA', '0 / END OF MULTI-TERMINAL DC DATA'),
    'MULTI_SECTION': ('BEGIN MULTI-SECTION LINE DATA', '0 / END OF MULTI-SECTION LINE DATA'),
    'ZONE': ('BEGIN ZONE DATA', '0 / END OF ZONE DATA'),
    'INTERAREA': ('BEGIN INTER-AREA TRANSFER DATA', '0 / END OF INTER-AREA TRANSFER DATA'),
    'OWNER': ('BEGIN OWNER DATA', '0 / END OF OWNER DATA'),
    'FACTS': ('BEGIN FACTS DEVICE DATA', '0 / END OF FACTS DEVICE DATA'),
    'SWITCHED_SHUNT': ('BEGIN SWITCHED SHUNT DATA', '0 / END OF SWITCHED SHUNT DATA'),
    'GNE': ('BEGIN GNE DATA', '0 / END OF GNE DATA'),
    'INDUCTION': ('BEGIN INDUCTION MACHINE DATA', '0 / END OF INDUCTION MACHINE DATA'),
}


# Sections parsed after CASE, in file order. Each entry pairs the SECTION_MAP
# key with the name of the parser method and the schema class it produces.
SECTION_PARSERS: list[tuple[str, str, type]] = [
    ('BUS', '_parse_bus_records', schema.BusRecord),
    ('LOAD', '_parse_load_records', schema.LoadRecord),
    ('FIXED_SHUNT', '_parse_fixed_shunt_records', schema.FixedShuntRecord),
    ('GENERATOR', '_parse_generator_records', schema.GeneratorRecord),
    ('BRANCH', '_parse_branch_records', schema.BranchRecord),
    ('SWITCH', '_parse_switch_records', schema.SwitchRecord),
    ('TRANSFORMER', '_parse_transformer_records', schema.TransformerRecord),
    ('AREA', '_parse_area_interchange_records', schema.AreaInterchangeRecord),
    ('TWO_TERM_DC', '_parse_two_terminal_dc_records', schema.TwoTerminalDCRecord),
    ('VSC_DC', '_parse_vsc_dc_records', schema.VscDcRecord),
    ('IMPEDANCE', '_parse_impedance_correction_records', schema.ImpedanceCorrectionRecord),
    ('MULTI_TERM_DC', '_parse_multi_terminal_dc_records', schema.MultiTerminalDCRecord),
    ('MULTI_SECTION', '_parse_multi_section_line_records', schema.MultiSectionLineRecord),
    ('ZONE', '_parse_zone_records', schema.ZoneRecord),
    ('INTERAREA', '_parse_interarea_transfer_records', schema.InterareaTransferRecord),
    ('OWNER', '_parse_owner_records', schema.OwnerRecord),
    ('FACTS', '_parse_facts_device_records', schema.FactsDeviceRecord),
    ('SWITCHED_SHUNT', '_parse_switched_shunt_records', schema.SwitchedShuntRecord),
    ('GNE', '_parse_gne_device_records', schema.GneDeviceRecord),
    ('INDUCTION', '_parse_induction_machine_records', schema.InductionMachineRecord),
]


# ---------------------------------------------------------------------------
# Reader Implementation
# ---------------------------------------------------------------------------

class Raw34Reader(FormatReader):
    """Read raw RAW v34 files into a cimhub_core GraphModel.

    This reader implements the FormatReader interface from cimhub_core and
    parses all 19 record types defined in the raw RAW v34 specification.
    """

    def __init__(self, source: str | Path) -> None:
        """Bind *source* (a ``.raw`` file path) without parsing it."""
        self.source = source
        self._model: GraphModel | None = None
        # Parse position, kept for error context in Raw34ParseError.
        self.current_line = 0
        self.current_section = None
        # REV from the case record. Set before any section is parsed, because
        # the BRANCH layout differs between v33 and v34 (see
        # _parse_branch_records). None until the case record is read.
        self._revision: int | None = None

    def read_all(self) -> GraphModel:
        """Parse the bound RAW file and return a populated GraphModel.

        Parses all sections, assigns composite identifiers, and returns a
        GraphModel keyed as ``graph[RecordClass][identifier]``. Parsing happens
        once; the resulting graph is cached and returned as-is on later calls.

        Raises:
            FileNotFoundError: If the bound source doesn't exist
            Raw34ParseError: If file parsing fails
        """
        if self._model is None:
            self._model = self._parse()
        return self._model

    def _parse(self) -> GraphModel:
        """Read the bound source and build the graph. See :meth:`read_all`."""
        source_path = Path(self.source)
        if not source_path.exists():
            raise FileNotFoundError(f"File not found: {self.source}")

        if source_path.suffix.lower() != '.raw':
            logger.warning(f"File extension is {source_path.suffix}, expected .raw")

        # Read entire file
        with open(source_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        logger.info(f"Reading {self.source} ({len(lines)} lines)")

        graph = GraphModel()

        # Parse case record (required) and add it
        self.current_section = 'CASE'
        case_section = self._get_section_lines(lines, *SECTION_MAP['CASE'])
        case_record = self._parse_case_record(case_section)
        # Record the declared REV before parsing sections whose layout depends
        # on it. The IEEE-118 fixture declares REV 33.
        self._revision = int(case_record.revision) if case_record.revision else None
        composite_id.assign_composite_id(case_record)
        graph.add_to_graph(case_record)

        # Parse each section (all optional except case).
        for section_name, parser_name, record_cls in SECTION_PARSERS:
            self.current_section = section_name
            try:
                section_lines = self._get_section_lines(lines, *SECTION_MAP[section_name])
                records = getattr(self, parser_name)(section_lines)
            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing {section_name} section: {e}",
                    section=section_name
                ) from e

            # Assign composite IDs and add to the graph, guarding against a
            # silent dedup collision (add_to_graph is a no-op on key clash).
            before = graph.count(record_cls)
            for record in records:
                composite_id.assign_composite_id(record)
                graph.add_to_graph(record)
            added = graph.count(record_cls) - before
            if added != len(records):
                logger.warning(
                    f"  {section_name}: {len(records) - added} of {len(records)} "
                    f"{record_cls.__name__} records dropped by identifier collision"
                )
            logger.info(f"  {section_name}: {len(records)} records")

        return graph

    # -----------------------------------------------------------------------
    # Section Extraction
    # -----------------------------------------------------------------------

    def _get_section_lines(
        self,
        lines: list[str],
        begin_marker: str,
        end_marker: str
    ) -> list[tuple[int, str]]:
        """Extract lines for a specific section.

        Args:
            lines: All lines from the file
            begin_marker: Start marker (empty string for case record)
            end_marker: End marker

        Returns:
            List of (line_number, line_content) tuples, with comments removed
        """
        start_idx = -1
        end_idx = len(lines)

        # Find section boundaries
        if begin_marker == '':
            # Case record starts at beginning
            start_idx = 0
        else:
            # Look for BEGIN marker that comes AFTER an END marker (proper section transition)
            # This handles PowerWorld files with spurious BEGIN markers in the case section
            for i, line in enumerate(lines):
                # Check if this line has both END and BEGIN (proper transition)
                if begin_marker in line and ('END OF' in line or i == 0):
                    start_idx = i + 1  # Start after marker line
                    break
                # Also accept standalone BEGIN if it's not in the case section
                elif begin_marker in line and i > 0:
                    # Make sure we're past the system-wide data
                    prev_lines = lines[max(0, i-10):i]
                    has_end_system = any('END OF SYSTEM-WIDE DATA' in pl for pl in prev_lines)
                    if has_end_system:
                        start_idx = i + 1
                        break

        if start_idx == -1:
            # Section not found
            return []

        # Find end marker
        for i in range(start_idx, len(lines)):
            if end_marker in lines[i]:
                end_idx = i
                break

        # Extract lines, removing comments
        result = []
        for i in range(start_idx, end_idx):
            line = lines[i]

            # Skip lines that start with @ (comment)
            if line.strip().startswith('@'):
                continue

            # Remove inline comments (anything after /  )
            if ' / ' in line:
                line = line.split(' / ')[0]

            # Skip blank lines
            if not line.strip():
                continue

            result.append((i + 1, line))  # 1-based line numbers

        return result

    # -----------------------------------------------------------------------
    # Tokenization and Type Conversion
    # -----------------------------------------------------------------------

    def _tokenize(self, line: str) -> list[str]:
        """Split line into comma-separated fields, respecting quotes.

        Args:
            line: Raw line content

        Returns:
            List of field strings (quotes preserved for now)
        """
        # Use Python's csv module for robust parsing
        reader = csv.reader(io.StringIO(line), skipinitialspace=True)
        try:
            fields = next(reader)
        except StopIteration:
            return []

        return fields

    def _convert_int(self, value: str, field_name: str = None, default: int = None) -> int:
        """Convert string to integer.

        Args:
            value: String value
            field_name: Field name for error messages
            default: Value to use when the field is blank. PSS/E writes an empty
                field to mean "use the documented default" — WECC-240's header
                is ``0, 100.00, 34,  ,  ,`` — so a blank is only an error for a
                field the spec gives no default for. Leave as None for those.

        Returns:
            Integer value

        Raises:
            Raw34ParseError: If conversion fails, or the field is blank and no
                default was supplied.
        """
        if default is not None and (value is None or not value.strip()):
            return default
        try:
            # Handle values like "1.0" as integers
            return int(float(value.strip()))
        except (ValueError, AttributeError) as e:
            field_msg = f" for field '{field_name}'" if field_name else ""
            raise Raw34ParseError(
                f"Cannot convert '{value}' to integer{field_msg}",
                line_number=self.current_line,
                section=self.current_section
            ) from e

    def _convert_float(self, value: str, field_name: str = None, default: float = None) -> float:
        """Convert string to float.

        Args:
            value: String value
            field_name: Field name for error messages
            default: Value to use when the field is blank — see
                :meth:`_convert_int`. Leave as None for fields the spec gives no
                default for, so a blank stays an error there.

        Returns:
            Float value

        Raises:
            Raw34ParseError: If conversion fails, or the field is blank and no
                default was supplied.
        """
        if default is not None and (value is None or not value.strip()):
            return default
        try:
            # Handle scientific notation (e.g., "1.23E-4")
            return float(value.strip())
        except (ValueError, AttributeError) as e:
            field_msg = f" for field '{field_name}'" if field_name else ""
            raise Raw34ParseError(
                f"Cannot convert '{value}' to float{field_msg}",
                line_number=self.current_line,
                section=self.current_section
            ) from e

    def _convert_string(self, value: str) -> str:
        """Convert string value, removing quotes if present.

        Args:
            value: String value (may have quotes)

        Returns:
            String value without quotes
        """
        value = value.strip()
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        elif value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        return value

    def _parse_bus_id(self, value: str) -> int | str:
        """Parse bus ID which can be integer or extended string.

        Args:
            value: Bus ID value

        Returns:
            Integer bus number or string bus name
        """
        value = value.strip()
        # Check if it's quoted (extended bus name)
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        else:
            # Integer bus number
            return self._convert_int(value, "bus_id")

    # -----------------------------------------------------------------------
    # Record Parsers - Case Record
    # -----------------------------------------------------------------------

    def _parse_case_record(
        self,
        lines: list[tuple[int, str]]
    ) -> schema.CaseIdentificationRecord:
        """Parse case identification record.

        The case record has a specific structure:
        - Line 1: IC, SBASE, REV, XFRRAT, NXFRAT, BASFRQ (6 comma-delimited values)
        - Line 2: Title line 1
        - Line 3: Title line 2
        - Lines 4-9: GENERAL, GAUSS, NEWTON, ADJUST, TYSL, SOLVER
        - Lines 10+: RATING lines (up to 12)

        Args:
            lines: Lines from case section

        Returns:
            Populated CaseIdentificationRecord

        Raises:
            Raw34ParseError: If case record is invalid
        """
        if not lines:
            raise Raw34ParseError(
                "Case identification record is missing",
                section='CASE'
            )

        # Parse first line (IC, SBASE, REV, ...)
        line_num, first_line = lines[0]
        self.current_line = line_num
        fields = self._tokenize(first_line)

        if len(fields) < 6:
            raise Raw34ParseError(
                f"Case record first line should have 6 fields, got {len(fields)}",
                line_number=line_num,
                line_content=first_line,
                section='CASE'
            )

        # Remove trailing comment from BASFRQ field if present
        basfrq_str = fields[5].split('/')[0].strip()

        case_record = schema.CaseIdentificationRecord(
            new_case_flag=self._convert_int(fields[0], 'IC'),
            system_base_mva=self._convert_float(fields[1], 'SBASE'),
            revision=self._convert_int(fields[2], 'REV'),
            # XFRRAT/NXFRAT: rating units flags, <=0 for MVA. PSS/E leaves them
            # blank when the case uses the default, so 0 (MVA) is the default.
            transformer_ratings_units=self._convert_int(fields[3], 'XFRRAT', default=0),
            branch_ratings_units=self._convert_int(fields[4], 'NXFRAT', default=0),
            # BASFRQ defaults to the program's base-frequency option, 60 Hz in
            # every North American case; PSS/E omits it when unchanged.
            system_base_frequency=self._convert_float(basfrq_str, 'BASFRQ', default=60.0),
        )

        # Parse title lines (next 2 lines)
        if len(lines) >= 2:
            case_record.title_line_1 = lines[1][1].strip()
        if len(lines) >= 3:
            case_record.title_line_2 = lines[2][1].strip()

        # Parse configuration lines (GENERAL, GAUSS, etc.)
        # These are stored as-is
        config_lines = []
        for i in range(3, min(9, len(lines))):
            config_lines.append(lines[i][1].strip())

        # Assign to appropriate fields
        if len(config_lines) > 0:
            case_record.general = config_lines[0]
        if len(config_lines) > 1:
            case_record.gauss = config_lines[1]
        if len(config_lines) > 2:
            case_record.newton = config_lines[2]
        if len(config_lines) > 3:
            case_record.adjust = config_lines[3]
        if len(config_lines) > 4:
            case_record.tysl = config_lines[4]
        if len(config_lines) > 5:
            case_record.solver = config_lines[5]

        # Parse RATING lines (starting from line 9)
        ratings = []
        for i in range(9, len(lines)):
            line = lines[i][1].strip()
            if line.startswith('RATING'):
                ratings.append(line)

        if ratings:
            case_record.ratings = ratings

        return case_record

    # -----------------------------------------------------------------------
    # Record Parsers - Simple Single-Line Records
    # -----------------------------------------------------------------------

    def _parse_bus_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.BusRecord]:
        """Parse bus data records.

        Args:
            lines: Lines from bus section

        Returns:
            List of BusRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 1:
                continue  # Skip empty lines

            try:
                bus = schema.BusRecord(
                    bus_number=self._convert_int(fields[0], 'bus_number')
                )

                # Optional fields with defaults
                if len(fields) > 1:
                    bus.name = self._convert_string(fields[1])
                if len(fields) > 2:
                    bus.base_voltage = self._convert_float(fields[2], 'base_voltage')
                if len(fields) > 3:
                    bus.bus_type = self._convert_int(fields[3], 'bus_type')
                if len(fields) > 4:
                    bus.area = self._convert_int(fields[4], 'area')
                if len(fields) > 5:
                    bus.zone = self._convert_int(fields[5], 'zone')
                if len(fields) > 6:
                    bus.owner = self._convert_int(fields[6], 'owner')
                if len(fields) > 7:
                    bus.voltage_magnitude = self._convert_float(fields[7], 'voltage_magnitude')
                if len(fields) > 8:
                    bus.voltage_angle = self._convert_float(fields[8], 'voltage_angle')
                if len(fields) > 9:
                    bus.normal_voltage_magnitude_high_limit = self._convert_float(fields[9])
                if len(fields) > 10:
                    bus.normal_voltage_magnitude_low_limit = self._convert_float(fields[10])
                if len(fields) > 11:
                    bus.emergency_voltage_magnitude_high_limit = self._convert_float(fields[11])
                if len(fields) > 12:
                    bus.emergency_voltage_magnitude_low_limit = self._convert_float(fields[12])

                records.append(bus)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing bus record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='BUS'
                ) from e

        return records

    # -----------------------------------------------------------------------
    # Placeholder parsers for remaining record types
    # These will be implemented next
    # -----------------------------------------------------------------------

    def _parse_load_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.LoadRecord]:
        """Parse load data records.

        Args:
            lines: Lines from load section

        Returns:
            List of LoadRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 1:
                continue

            try:
                load = schema.LoadRecord(
                    bus_number=self._parse_bus_id(fields[0])
                )

                # Optional fields
                if len(fields) > 1:
                    load.load_id = self._convert_string(fields[1])
                if len(fields) > 2:
                    load.status = self._convert_int(fields[2], 'status')
                if len(fields) > 3:
                    load.area = self._convert_int(fields[3], 'area')
                if len(fields) > 4:
                    load.zone = self._convert_int(fields[4], 'zone')
                if len(fields) > 5:
                    load.constant_real_power = self._convert_float(fields[5])
                if len(fields) > 6:
                    load.constant_imag_power = self._convert_float(fields[6])
                if len(fields) > 7:
                    load.constant_current_real_power = self._convert_float(fields[7])
                if len(fields) > 8:
                    load.constant_current_imag_power = self._convert_float(fields[8])
                if len(fields) > 9:
                    load.constant_admittance_real_power = self._convert_float(fields[9])
                if len(fields) > 10:
                    load.constant_admittance_imag_power = self._convert_float(fields[10])
                if len(fields) > 11:
                    load.owner = self._convert_int(fields[11], 'owner')
                if len(fields) > 12:
                    load.scale = self._convert_int(fields[12], 'scale')
                if len(fields) > 13:
                    load.interruptible = self._convert_int(fields[13], 'interruptible')
                if len(fields) > 14:
                    load.dgenp = self._convert_float(fields[14])
                if len(fields) > 15:
                    load.dgenq = self._convert_float(fields[15])
                if len(fields) > 16:
                    load.dgenf = self._convert_int(fields[16], 'dgenf')

                records.append(load)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing load record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='LOAD'
                ) from e

        return records

    def _parse_fixed_shunt_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.FixedShuntRecord]:
        """Parse fixed shunt data records.

        Args:
            lines: Lines from fixed shunt section

        Returns:
            List of FixedShuntRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 1:
                continue

            try:
                shunt = schema.FixedShuntRecord(
                    bus_number=self._parse_bus_id(fields[0])
                )

                # Optional fields
                if len(fields) > 1:
                    shunt.shunt_id = self._convert_string(fields[1])
                if len(fields) > 2:
                    shunt.status = self._convert_int(fields[2], 'status')
                if len(fields) > 3:
                    shunt.gl = self._convert_float(fields[3], 'gl')
                if len(fields) > 4:
                    shunt.bl = self._convert_float(fields[4], 'bl')

                records.append(shunt)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing fixed shunt record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='FIXED_SHUNT'
                ) from e

        return records

    def _parse_generator_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.GeneratorRecord]:
        """Parse generator data records.

        Args:
            lines: Lines from generator section

        Returns:
            List of GeneratorRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 1:
                continue

            try:
                gen = schema.GeneratorRecord(
                    bus_number=self._parse_bus_id(fields[0])
                )

                # Optional fields (generators have many!)
                if len(fields) > 1:
                    gen.gen_id = self._convert_string(fields[1])
                if len(fields) > 2:
                    gen.p_output = self._convert_float(fields[2])
                if len(fields) > 3:
                    gen.q_output = self._convert_float(fields[3])
                if len(fields) > 4:
                    gen.max_q_output = self._convert_float(fields[4])
                if len(fields) > 5:
                    gen.min_q_output = self._convert_float(fields[5])
                if len(fields) > 6:
                    gen.regulated_voltage_setpoint = self._convert_float(fields[6])
                if len(fields) > 7:
                    gen.regulated_bus_number = self._parse_bus_id(fields[7])
                if len(fields) > 8:
                    gen.rated_mva = self._convert_float(fields[8])
                if len(fields) > 9:
                    gen.zr = self._convert_float(fields[9])
                if len(fields) > 10:
                    gen.zx = self._convert_float(fields[10])
                if len(fields) > 11:
                    gen.rt = self._convert_float(fields[11])
                if len(fields) > 12:
                    gen.xt = self._convert_float(fields[12])
                if len(fields) > 13:
                    gen.gtap = self._convert_float(fields[13])
                if len(fields) > 14:
                    gen.status = self._convert_int(fields[14], 'status')
                if len(fields) > 15:
                    gen.rmpct = self._convert_float(fields[15])
                if len(fields) > 16:
                    gen.max_p_output = self._convert_float(fields[16])
                if len(fields) > 17:
                    gen.min_p_output = self._convert_float(fields[17])
                if len(fields) > 18:
                    gen.o1 = self._convert_int(fields[18], 'o1')
                if len(fields) > 19:
                    gen.f1 = self._convert_float(fields[19])
                if len(fields) > 20:
                    gen.o2 = self._convert_int(fields[20], 'o2')
                if len(fields) > 21:
                    gen.f2 = self._convert_float(fields[21])
                if len(fields) > 22:
                    gen.o3 = self._convert_int(fields[22], 'o3')
                if len(fields) > 23:
                    gen.f3 = self._convert_float(fields[23])
                if len(fields) > 24:
                    gen.o4 = self._convert_int(fields[24], 'o4')
                if len(fields) > 25:
                    gen.f4 = self._convert_float(fields[25])
                if len(fields) > 26:
                    gen.wmod = self._convert_int(fields[26], 'wmod')
                if len(fields) > 27:
                    gen.wpf = self._convert_float(fields[27])

                records.append(gen)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing generator record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='GENERATOR'
                ) from e

        return records

    def _parse_branch_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse branch (line) data records.

        Branch records have 34 fields:
        - I, J, CKT: Bus numbers and circuit ID (3 fields)
        - R, X, B: Impedance and charging (3 fields)
        - NAME: Branch name (1 field, 40 chars)
        - RATE1-RATE12: Branch ratings (12 fields)
        - GI, BI, GJ, BJ: Line shunt admittances (4 fields)
        - STAT, MET, LEN: Status, metered end, length (3 fields)
        - O1,F1,O2,F2,O3,F3,O4,F4: Owner data (8 fields)

        Args:
            lines: Lines from branch section

        Returns:
            List of BranchRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num
            try:
                fields = self._tokenize(line)

                # v33 and v34 lay this record out differently, and the shift
                # affects every field from index 6 on:
                #
                #   v34: I,J,CKT,R,X,B,'NAME',RATE1..RATE12,GI,BI,GJ,BJ,ST,MET,LEN,O1,F1..
                #   v33: I,J,CKT,R,X,B,RATEA,RATEB,RATEC,     GI,BI,GJ,BJ,ST,MET,LEN,O1,F1..
                #
                # v33 has no NAME and 3 ratings rather than 12, so its records
                # run 24 fields against v34's 35. Parsing a v33 line with the
                # v34 offsets reads RATEA as the name and GI as a rating, so the
                # layout has to follow the REV the case declares.
                #
                # Fields through LEN are required; the four owner pairs
                # O1/F1..O4/F4 are optional in PSS/E and commonly omitted or
                # truncated after the first pair, so they fall back to defaults.
                is_v33 = self._revision is not None and self._revision < 34
                min_fields = 22 if is_v33 else 26
                if len(fields) < min_fields:
                    raise Raw34ParseError(
                        f"Branch record should have at least {min_fields} fields "
                        f"for REV {self._revision or 34}, got {len(fields)}",
                        line_number=line_num,
                        line_content=line,
                        section='BRANCH'
                    )

                if is_v33:
                    # RATEA/B/C map onto the first three of the 12 v34 rating
                    # slots; the rest stay 0 (unset), matching v34's meaning.
                    ratings = [self._convert_float(fields[i], f'RATE{i-5}') for i in range(6, 9)]
                    ratings += [0.0] * 9
                    branch = schema.BranchRecord(
                        from_bus_number=self._convert_int(fields[0], 'I'),
                        to_bus_number=self._convert_int(fields[1], 'J'),
                        circuit=self._convert_string(fields[2]),
                        r=self._convert_float(fields[3], 'R'),
                        x=self._convert_float(fields[4], 'X'),
                        b=self._convert_float(fields[5], 'B'),
                        name="",  # v33 has no NAME field
                        ratings=ratings,
                        g_from=self._convert_float(fields[9], 'GI'),
                        b_from=self._convert_float(fields[10], 'BI'),
                        g_to=self._convert_float(fields[11], 'GJ'),
                        b_to=self._convert_float(fields[12], 'BJ'),
                        status=self._convert_int(fields[13], 'STAT'),
                        metered_end=self._convert_int(fields[14], 'MET'),
                        length=self._convert_float(fields[15], 'LEN'),
                        o1=self._convert_int(fields[16], 'O1') if len(fields) > 16 else 1,
                        f1=self._convert_float(fields[17], 'F1') if len(fields) > 17 else 1.0,
                        o2=self._convert_int(fields[18], 'O2') if len(fields) > 18 else 0,
                        f2=self._convert_float(fields[19], 'F2') if len(fields) > 19 else 0.0,
                        o3=self._convert_int(fields[20], 'O3') if len(fields) > 20 else 0,
                        f3=self._convert_float(fields[21], 'F3') if len(fields) > 21 else 0.0,
                        o4=self._convert_int(fields[22], 'O4') if len(fields) > 22 else 0,
                        f4=self._convert_float(fields[23], 'F4') if len(fields) > 23 else 0.0,
                    )
                    records.append(branch)
                    continue

                # Parse ratings (fields 7-18, indices 7-18)
                ratings = [self._convert_float(fields[i], f'RATE{i-6}') for i in range(7, 19)]

                branch = schema.BranchRecord(
                    from_bus_number=self._convert_int(fields[0], 'I'),
                    to_bus_number=self._convert_int(fields[1], 'J'),
                    circuit=self._convert_string(fields[2]),
                    r=self._convert_float(fields[3], 'R'),
                    x=self._convert_float(fields[4], 'X'),
                    b=self._convert_float(fields[5], 'B'),
                    name=self._convert_string(fields[6]),
                    ratings=ratings,
                    g_from=self._convert_float(fields[19], 'GI'),
                    b_from=self._convert_float(fields[20], 'BI'),
                    g_to=self._convert_float(fields[21], 'GJ'),
                    b_to=self._convert_float(fields[22], 'BJ'),
                    status=self._convert_int(fields[23], 'STAT'),
                    metered_end=self._convert_int(fields[24], 'MET'),
                    length=self._convert_float(fields[25], 'LEN'),
                    o1=self._convert_int(fields[26], 'O1') if len(fields) > 26 else 1,
                    f1=self._convert_float(fields[27], 'F1') if len(fields) > 27 else 1.0,
                    o2=self._convert_int(fields[28], 'O2') if len(fields) > 28 else 0,
                    f2=self._convert_float(fields[29], 'F2') if len(fields) > 29 else 0.0,
                    o3=self._convert_int(fields[30], 'O3') if len(fields) > 30 else 0,
                    f3=self._convert_float(fields[31], 'F3') if len(fields) > 31 else 0.0,
                    o4=self._convert_int(fields[32], 'O4') if len(fields) > 32 else 0,
                    f4=self._convert_float(fields[33], 'F4') if len(fields) > 33 else 0.0,
                )

                records.append(branch)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing branch record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='BRANCH'
                ) from e

        return records

    def _parse_switch_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse switching device data records.

        Switch records have 21 fields:
        - I, J, CKT: Bus numbers and circuit ID (3 fields)
        - X: Switch reactance (1 field)
        - RATE1-RATE12: Switch ratings (12 fields)
        - STAT, NSTAT, MET, STYPE: Status fields (4 fields)
        - NAME: Switch name (1 field)

        Args:
            lines: Lines from switch section

        Returns:
            List of SwitchRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num
            try:
                fields = self._tokenize(line)

                if len(fields) < 21:
                    raise Raw34ParseError(
                        f"Switch record should have 21 fields, got {len(fields)}",
                        line_number=line_num,
                        line_content=line,
                        section='SWITCH'
                    )

                # Parse ratings (fields 4-15, indices 4-15)
                ratings = [self._convert_float(fields[i], f'RATE{i-3}') for i in range(4, 16)]

                switch = schema.SwitchRecord(
                    from_bus_number=self._convert_int(fields[0], 'I'),
                    to_bus_number=self._convert_int(fields[1], 'J'),
                    circuit=self._convert_string(fields[2]),
                    x=self._convert_float(fields[3], 'X'),
                    ratings=ratings,
                    status=self._convert_int(fields[16], 'STAT'),
                    nstat=self._convert_int(fields[17], 'NSTAT'),
                    metered_end=self._convert_int(fields[18], 'MET'),
                    stype=self._convert_int(fields[19], 'STYPE'),
                    name=self._convert_string(fields[20])
                )

                records.append(switch)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing switch record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='SWITCH'
                ) from e

        return records

    def _parse_transformer_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse transformer data records (multi-line).

        Each transformer record consists of:
        - Line 1: Basic identification (I, J, K, CKT, CW, CZ, CM, MAG1, MAG2, NMETR, NAME, STAT, O1-F4, VECGRP, ZCOD)
        - Line 2: Impedance data (R1-2, X1-2, SBASE1-2, etc.)
        - Line 3: Winding 1 data (WINDV1, NOMV1, ANG1, RATE1-1 through RATE1-12, etc.)
        - Line 4: Winding 2 data
        - Line 5 (optional): Winding 3 data if K != 0

        Args:
            lines: Lines from transformer section

        Returns:
            List of TransformerRecord objects
        """
        records = []
        i = 0

        while i < len(lines):
            line_num, line = lines[i]
            self.current_line = line_num

            try:
                # Parse line 1 (basic data)
                fields1 = self._tokenize(line)
                # 20 fields covers I..F4, everything the converters need. v34
                # appends VECGRP (index 20) and ZCOD (21); v33 has neither, so a
                # v33 record is complete at 20. Both are already read below
                # behind length guards, so the only change needed for v33 is not
                # rejecting the shorter line.
                if len(fields1) < 20:
                    raise Raw34ParseError(
                        f"Transformer line 1 should have at least 20 fields, got {len(fields1)}",
                        line_number=line_num,
                        line_content=line,
                        section='TRANSFORMER'
                    )

                # Extract K to determine if this is a 3-winding transformer
                k = self._convert_int(fields1[2], 'K')

                # Determine number of lines for this transformer
                num_lines = 5 if k != 0 else 4

                if i + num_lines > len(lines):
                    raise Raw34ParseError(
                        f"Incomplete transformer record: expected {num_lines} lines, only {len(lines) - i} remaining",
                        line_number=line_num,
                        section='TRANSFORMER'
                    )

                # Parse line 2 (impedance data)
                _, line2 = lines[i + 1]
                fields2 = self._tokenize(line2)

                # Parse line 3 (winding 1 data)
                _, line3 = lines[i + 2]
                fields3 = self._tokenize(line3)

                # Parse line 4 (winding 2 data)
                _, line4 = lines[i + 3]
                fields4 = self._tokenize(line4)

                # Parse all fields
                # Line 1: I, J, K, CKT, CW, CZ, CM, MAG1, MAG2, NMETR, NAME, STAT, O1, F1, O2, F2, O3, F3, O4, F4, VECGRP, ZCOD
                # Line 2: R1-2, X1-2, SBASE1-2 (and for 3-winding: R2-3, X2-3, SBASE2-3, R3-1, X3-1, SBASE3-1, VMSTAR, ANSTAR)
                # Line 3: WINDV1, NOMV1, ANG1, RATE1-1 through RATE1-12, COD1, CONT1, RMA1, RMI1, VMA1, VMI1, NTP1, TAB1, CR1, CX1, CNXA1, NOD1
                # Line 4: WINDV2, NOMV2, ANG2, RATE2-1 through RATE2-12, COD2, CONT2, RMA2, RMI2, VMA2, VMI2, NTP2, TAB2, CR2, CX2, CNXA2, NOD2

                transformer = schema.TransformerRecord(
                    # Line 1
                    i=self._convert_int(fields1[0], 'I'),
                    j=self._convert_int(fields1[1], 'J'),
                    k=k,
                    circuit=self._convert_string(fields1[3]) if len(fields1) > 3 else '1',
                    cw=self._convert_int(fields1[4], 'CW') if len(fields1) > 4 else 1,
                    cz=self._convert_int(fields1[5], 'CZ') if len(fields1) > 5 else 1,
                    cm=self._convert_int(fields1[6], 'CM') if len(fields1) > 6 else 1,
                    mag1=self._convert_float(fields1[7], 'MAG1') if len(fields1) > 7 else 0.0,
                    mag2=self._convert_float(fields1[8], 'MAG2') if len(fields1) > 8 else 0.0,
                    nmetr=self._convert_int(fields1[9], 'NMETR') if len(fields1) > 9 else 2,
                    name=self._convert_string(fields1[10]) if len(fields1) > 10 else '',
                    status=self._convert_int(fields1[11], 'STAT') if len(fields1) > 11 else 1,
                    o1=self._convert_int(fields1[12], 'O1') if len(fields1) > 12 else 1,
                    f1=self._convert_float(fields1[13], 'F1') if len(fields1) > 13 else 1.0,
                    o2=self._convert_int(fields1[14], 'O2') if len(fields1) > 14 else 0,
                    f2=self._convert_float(fields1[15], 'F2') if len(fields1) > 15 else 0.0,
                    o3=self._convert_int(fields1[16], 'O3') if len(fields1) > 16 else 0,
                    f3=self._convert_float(fields1[17], 'F3') if len(fields1) > 17 else 0.0,
                    o4=self._convert_int(fields1[18], 'O4') if len(fields1) > 18 else 0,
                    f4=self._convert_float(fields1[19], 'F4') if len(fields1) > 19 else 0.0,
                    vecgrp=self._convert_string(fields1[20]) if len(fields1) > 20 else '',
                    zcod=self._convert_int(fields1[21], 'ZCOD') if len(fields1) > 21 else 0,
                    # Line 2 (impedance data)
                    r1_2=self._convert_float(fields2[0], 'R1-2') if len(fields2) > 0 else 0.0,
                    x1_2=self._convert_float(fields2[1], 'X1-2') if len(fields2) > 1 else 0.0,
                    sbase1_2=self._convert_float(fields2[2], 'SBASE1-2') if len(fields2) > 2 else 100.0,
                    # Line 3 (winding 1 data)
                    windv1=self._convert_float(fields3[0], 'WINDV1') if len(fields3) > 0 else 1.0,
                    nomv1=self._convert_float(fields3[1], 'NOMV1') if len(fields3) > 1 else 0.0,
                    ang1=self._convert_float(fields3[2], 'ANG1') if len(fields3) > 2 else 0.0,
                    rate1_1=self._convert_float(fields3[3], 'RATE1-1') if len(fields3) > 3 else 0.0,
                    rate1_2=self._convert_float(fields3[4], 'RATE1-2') if len(fields3) > 4 else 0.0,
                    rate1_3=self._convert_float(fields3[5], 'RATE1-3') if len(fields3) > 5 else 0.0,
                    rate1_4=self._convert_float(fields3[6], 'RATE1-4') if len(fields3) > 6 else 0.0,
                    rate1_5=self._convert_float(fields3[7], 'RATE1-5') if len(fields3) > 7 else 0.0,
                    rate1_6=self._convert_float(fields3[8], 'RATE1-6') if len(fields3) > 8 else 0.0,
                    rate1_7=self._convert_float(fields3[9], 'RATE1-7') if len(fields3) > 9 else 0.0,
                    rate1_8=self._convert_float(fields3[10], 'RATE1-8') if len(fields3) > 10 else 0.0,
                    rate1_9=self._convert_float(fields3[11], 'RATE1-9') if len(fields3) > 11 else 0.0,
                    rate1_10=self._convert_float(fields3[12], 'RATE1-10') if len(fields3) > 12 else 0.0,
                    rate1_11=self._convert_float(fields3[13], 'RATE1-11') if len(fields3) > 13 else 0.0,
                    rate1_12=self._convert_float(fields3[14], 'RATE1-12') if len(fields3) > 14 else 0.0,
                    # Line 4 (winding 2 data)
                    windv2=self._convert_float(fields4[0], 'WINDV2') if len(fields4) > 0 else 1.0,
                    nomv2=self._convert_float(fields4[1], 'NOMV2') if len(fields4) > 1 else 0.0,
                    ang2=self._convert_float(fields4[2], 'ANG2') if len(fields4) > 2 else 0.0,
                    rate2_1=self._convert_float(fields4[3], 'RATE2-1') if len(fields4) > 3 else 0.0,
                    rate2_2=self._convert_float(fields4[4], 'RATE2-2') if len(fields4) > 4 else 0.0,
                    rate2_3=self._convert_float(fields4[5], 'RATE2-3') if len(fields4) > 5 else 0.0,
                    rate2_4=self._convert_float(fields4[6], 'RATE2-4') if len(fields4) > 6 else 0.0,
                    rate2_5=self._convert_float(fields4[7], 'RATE2-5') if len(fields4) > 7 else 0.0,
                    rate2_6=self._convert_float(fields4[8], 'RATE2-6') if len(fields4) > 8 else 0.0,
                    rate2_7=self._convert_float(fields4[9], 'RATE2-7') if len(fields4) > 9 else 0.0,
                    rate2_8=self._convert_float(fields4[10], 'RATE2-8') if len(fields4) > 10 else 0.0,
                    rate2_9=self._convert_float(fields4[11], 'RATE2-9') if len(fields4) > 11 else 0.0,
                    rate2_10=self._convert_float(fields4[12], 'RATE2-10') if len(fields4) > 12 else 0.0,
                    rate2_11=self._convert_float(fields4[13], 'RATE2-11') if len(fields4) > 13 else 0.0,
                    rate2_12=self._convert_float(fields4[14], 'RATE2-12') if len(fields4) > 14 else 0.0,
                )

                records.append(transformer)

                # Advance to next transformer record
                i += num_lines

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing transformer record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='TRANSFORMER'
                ) from e

        return records

    def _parse_area_interchange_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse area interchange data records.

        Area interchange records have 5 fields:
        - I: Area number (1 field)
        - ISW: Slack bus number (1 field)
        - PDES: Desired net interchange in MW (1 field)
        - PTOL: Interchange tolerance in MW (1 field)
        - ARNAME: Area name (1 field)

        Args:
            lines: Lines from area interchange section

        Returns:
            List of AreaInterchangeRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num
            try:
                fields = self._tokenize(line)

                if len(fields) < 5:
                    raise Raw34ParseError(
                        f"Area interchange record should have at least 5 fields, got {len(fields)}",
                        line_number=line_num,
                        line_content=line,
                        section='AREA'
                    )

                area = schema.AreaInterchangeRecord(
                    area_number=self._convert_int(fields[0], 'I'),
                    bus_number=self._convert_int(fields[1], 'ISW'),
                    pdes=self._convert_float(fields[2], 'PDES'),
                    ptol=self._convert_float(fields[3], 'PTOL'),
                    name=self._convert_string(fields[4])
                )

                records.append(area)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing area interchange record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='AREA'
                ) from e

        return records

    def _parse_two_terminal_dc_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse two-terminal DC transmission line records (multi-line).

        Each two-terminal DC record consists of 3 lines:
        - Line 1: Basic identification data
        - Line 2: Rectifier data
        - Line 3: Inverter data

        Args:
            lines: Lines from two-terminal DC section

        Returns:
            List of TwoTerminalDCRecord objects
        """
        records = []
        i = 0

        while i < len(lines):
            if i + 3 > len(lines):
                break

            line_num, line = lines[i]
            self.current_line = line_num

            try:
                # Parse line 1 (basic data)
                fields1 = self._tokenize(line)

                # Parse line 2 (rectifier data)
                _, line2 = lines[i + 1]
                fields2 = self._tokenize(line2)

                # Parse line 3 (inverter data)
                _, line3 = lines[i + 2]
                fields3 = self._tokenize(line3)

                # Line 1: NAME, MDC, RDC, SETVL, VSCHD, VCMOD, RCOMP, DELTI, METER, DCVMIN, CCCITMX, CCCACC
                name = self._convert_string(fields1[0]) if len(fields1) > 0 else ""
                mdc = int(fields1[1]) if len(fields1) > 1 else 0
                rdc = float(fields1[2]) if len(fields1) > 2 else 0.0
                setvl = float(fields1[3]) if len(fields1) > 3 else 0.0
                vschd = float(fields1[4]) if len(fields1) > 4 else 0.0
                vcmod = float(fields1[5]) if len(fields1) > 5 else 0.0
                rcomp = float(fields1[6]) if len(fields1) > 6 else 0.0
                delti = float(fields1[7]) if len(fields1) > 7 else 0.0
                meter = self._convert_string(fields1[8]) if len(fields1) > 8 else "I"
                dcvmin = float(fields1[9]) if len(fields1) > 9 else 0.0
                cccitmx = int(fields1[10]) if len(fields1) > 10 else 20
                cccacc = float(fields1[11]) if len(fields1) > 11 else 1.0

                # Line 2: IPR, NBR, ANMXR, ANMNR, RCR, XCR, EBASR, TRR, TAPR, TMXR, TMNR, STPR, ICR, IFR, ITR, IDR, XCAPR, NDR
                ipr = int(fields2[0]) if len(fields2) > 0 else 0
                nbr = int(fields2[1]) if len(fields2) > 1 else 0
                anmxr = float(fields2[2]) if len(fields2) > 2 else 90.0
                anmnr = float(fields2[3]) if len(fields2) > 3 else 0.0
                rcr = float(fields2[4]) if len(fields2) > 4 else 0.0
                xcr = float(fields2[5]) if len(fields2) > 5 else 0.0
                ebasr = float(fields2[6]) if len(fields2) > 6 else 0.0
                trr = float(fields2[7]) if len(fields2) > 7 else 1.0
                tapr = float(fields2[8]) if len(fields2) > 8 else 1.0
                tmxr = float(fields2[9]) if len(fields2) > 9 else 1.5
                tmnr = float(fields2[10]) if len(fields2) > 10 else 0.51
                stpr = float(fields2[11]) if len(fields2) > 11 else 0.00625
                icr = int(fields2[12]) if len(fields2) > 12 else 0
                ifr = int(fields2[13]) if len(fields2) > 13 else 0
                itr = int(fields2[14]) if len(fields2) > 14 else 0
                idr = self._convert_string(fields2[15]) if len(fields2) > 15 else "1"
                xcapr = float(fields2[16]) if len(fields2) > 16 else 0.0
                ndr = int(fields2[17]) if len(fields2) > 17 else 0

                # Line 3: IPI, NBI, ANMXI, ANMNI, RCI, XCI, EBASI, TRI, TAPI, TMXI, TMNI, STPI, ICI, IFI, ITI, IDI, XCAPI, NDI
                ipi = int(fields3[0]) if len(fields3) > 0 else 0
                nbi = int(fields3[1]) if len(fields3) > 1 else 0
                anmxi = float(fields3[2]) if len(fields3) > 2 else 90.0
                anmni = float(fields3[3]) if len(fields3) > 3 else 0.0
                rci = float(fields3[4]) if len(fields3) > 4 else 0.0
                xci = float(fields3[5]) if len(fields3) > 5 else 0.0
                ebasi = float(fields3[6]) if len(fields3) > 6 else 0.0
                tri = float(fields3[7]) if len(fields3) > 7 else 1.0
                tapi = float(fields3[8]) if len(fields3) > 8 else 1.0
                tmxi = float(fields3[9]) if len(fields3) > 9 else 1.5
                tmni = float(fields3[10]) if len(fields3) > 10 else 0.51
                stpi = float(fields3[11]) if len(fields3) > 11 else 0.00625
                ici = int(fields3[12]) if len(fields3) > 12 else 0
                ifi = int(fields3[13]) if len(fields3) > 13 else 0
                iti = int(fields3[14]) if len(fields3) > 14 else 0
                idi = self._convert_string(fields3[15]) if len(fields3) > 15 else "1"
                xcapi = float(fields3[16]) if len(fields3) > 16 else 0.0
                ndi = int(fields3[17]) if len(fields3) > 17 else 0

                dc = schema.TwoTerminalDCRecord(
                    name=name, mdc=mdc, rdc=rdc, setvl=setvl, vschd=vschd,
                    vcmod=vcmod, rcomp=rcomp, delti=delti, meter=meter,
                    dcvmin=dcvmin, cccitmx=cccitmx, cccacc=cccacc,
                    ipr=ipr, nbr=nbr, anmxr=anmxr, anmnr=anmnr,
                    rcr=rcr, xcr=xcr, ebasr=ebasr, trr=trr, tapr=tapr,
                    tmxr=tmxr, tmnr=tmnr, stpr=stpr, icr=icr, ifr=ifr,
                    itr=itr, idr=idr, xcapr=xcapr, ndr=ndr,
                    ipi=ipi, nbi=nbi, anmxi=anmxi, anmni=anmni,
                    rci=rci, xci=xci, ebasi=ebasi, tri=tri, tapi=tapi,
                    tmxi=tmxi, tmni=tmni, stpi=stpi, ici=ici, ifi=ifi,
                    iti=iti, idi=idi, xcapi=xcapi, ndi=ndi,
                )

                records.append(dc)
                i += 3

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing two-terminal DC record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='TWO_TERM_DC'
                ) from e

        return records

    def _parse_vsc_dc_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse VSC DC transmission line records (multi-line).

        Each VSC DC record consists of 3 lines:
        - Line 1: DC line identification, resistance, and ownership
        - Line 2: Converter 1 data
        - Line 3: Converter 2 data

        Two VscDcRecord objects are created per 3-line group (one per converter),
        sharing line-level fields (name, mdc, rdc, ownership).

        Args:
            lines: Lines from VSC DC section

        Returns:
            List of VscDcRecord objects (2 per DC line)
        """
        records = []
        i = 0

        while i < len(lines):
            if i + 3 > len(lines):
                break

            line_num, line = lines[i]
            self.current_line = line_num

            try:
                # Line 1: NAME, MDC, RDC, O1, F1, O2, F2, O3, F3, O4, F4
                fields1 = self._tokenize(line)
                name = self._convert_string(fields1[0]) if len(fields1) > 0 else ""
                mdc = int(fields1[1]) if len(fields1) > 1 else 1
                rdc = float(fields1[2]) if len(fields1) > 2 else 0.0
                o1 = int(fields1[3]) if len(fields1) > 3 else 1
                f1 = float(fields1[4]) if len(fields1) > 4 else 1.0
                o2 = int(fields1[5]) if len(fields1) > 5 else 0
                f2 = float(fields1[6]) if len(fields1) > 6 else 0.0
                o3 = int(fields1[7]) if len(fields1) > 7 else 0
                f3 = float(fields1[8]) if len(fields1) > 8 else 0.0
                o4 = int(fields1[9]) if len(fields1) > 9 else 0
                f4 = float(fields1[10]) if len(fields1) > 10 else 0.0

                # Parse converter lines (2 and 3)
                for conv_idx in range(2):
                    _, conv_line = lines[i + 1 + conv_idx]
                    cf = self._tokenize(conv_line)

                    # IBUS, TYPE, MODE, DCSET, ACSET, ALOSS, BLOSS, MINLOSS, SMAX, IMAX, PWF, MAXQ, MINQ, VSREG, RMPCT, NREG
                    ibus = int(cf[0]) if len(cf) > 0 else 0
                    converter_type = int(cf[1]) if len(cf) > 1 else 1
                    mode = int(cf[2]) if len(cf) > 2 else 1
                    dcset = float(cf[3]) if len(cf) > 3 else 0.0
                    acset = float(cf[4]) if len(cf) > 4 else 1.0
                    aloss = float(cf[5]) if len(cf) > 5 else 0.0
                    bloss = float(cf[6]) if len(cf) > 6 else 0.0
                    minloss = float(cf[7]) if len(cf) > 7 else 0.0
                    smax = float(cf[8]) if len(cf) > 8 else 0.0
                    imax = float(cf[9]) if len(cf) > 9 else 0.0
                    pwf = float(cf[10]) if len(cf) > 10 else 1.0
                    maxq = float(cf[11]) if len(cf) > 11 else 9999.0
                    minq = float(cf[12]) if len(cf) > 12 else -9999.0
                    vsreg = int(cf[13]) if len(cf) > 13 else 0
                    rmpct = float(cf[14]) if len(cf) > 14 else 100.0
                    nreg = int(cf[15]) if len(cf) > 15 else 0

                    vsc = schema.VscDcRecord(
                        name=name, mdc=mdc, rdc=rdc,
                        o1=o1, f1=f1, o2=o2, f2=f2, o3=o3, f3=f3, o4=o4, f4=f4,
                        ibus=ibus, converter_type=converter_type, mode=mode,
                        dcset=dcset, acset=acset, aloss=aloss, bloss=bloss,
                        minloss=minloss, smax=smax, imax=imax, pwf=pwf,
                        maxq=maxq, minq=minq, vsreg=vsreg, rmpct=rmpct, nreg=nreg,
                    )
                    records.append(vsc)

                i += 3

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing VSC DC record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='VSC_DC'
                ) from e

        return records

    def _parse_impedance_correction_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse transformer impedance correction records (multi-line).

        Each record starts with table_number on first line, followed by T/F_real/F_imag
        triplets that may span multiple lines. A triplet with T=0 terminates the record.
        Continuation lines do NOT start with an integer table number.

        Args:
            lines: Lines from impedance correction section

        Returns:
            List of ImpedanceCorrectionRecord objects
        """
        records = []
        i = 0

        while i < len(lines):
            line_num, line = lines[i]
            self.current_line = line_num

            try:
                # Collect all values for this record (first line + continuation lines)
                all_values = list(self._tokenize(line))
                i += 1

                # Continuation lines: peek ahead — if next line doesn't start with
                # an integer followed by comma-separated triplets starting fresh,
                # it's a continuation. Heuristic: continuation lines start with whitespace
                # or a float (not a bare integer table number).
                while i < len(lines):
                    next_line_num, next_line = lines[i]
                    stripped = next_line.strip()
                    # A new record starts with an integer table_number followed by ","
                    # Continuation lines start with whitespace or a float value
                    if stripped and not next_line[0].isspace():
                        # Check if first token could be a table number (integer)
                        first_token = stripped.split(',')[0].strip()
                        try:
                            int(first_token)
                            # Looks like a new table number — stop collecting
                            break
                        except ValueError:
                            pass
                    # It's a continuation line
                    all_values.extend(self._tokenize(next_line))
                    i += 1

                if len(all_values) < 1:
                    continue

                table_num = self._convert_int(all_values[0], 'I')
                rec = schema.ImpedanceCorrectionRecord(table_number=table_num)

                # Parse T/F_real/F_imag triplets from remaining values
                triplet_fields = []
                for n in range(1, 12):
                    triplet_fields.extend([f't{n}', f'f{n}_real', f'f{n}_imag'])

                val_idx = 1
                for field_name in triplet_fields:
                    if val_idx >= len(all_values):
                        break
                    value = self._convert_float(all_values[val_idx])
                    setattr(rec, field_name, value)
                    val_idx += 1

                records.append(rec)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing impedance correction record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='IMPEDANCE_CORRECTION'
                ) from e

        return records

    def _parse_multi_terminal_dc_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse multi-terminal DC transmission line records (multi-line).

        Each record consists of:
        - Line 1: NAME, NCONV, NDCBS, NDCLN, MDC, VCONV, VCMOD, VCONVN
        - NCONV converter lines
        - NDCBS DC bus lines
        - NDCLN DC link lines

        Args:
            lines: Lines from multi-terminal DC section

        Returns:
            List of MultiTerminalDCRecord objects
        """
        records = []
        i = 0

        while i < len(lines):
            line_num, line = lines[i]
            self.current_line = line_num

            try:
                fields = self._tokenize(line)
                if len(fields) < 4:
                    i += 1
                    continue

                name = self._convert_string(fields[0])
                nconv = self._convert_int(fields[1], 'NCONV')
                ndcbs = self._convert_int(fields[2], 'NDCBS')
                ndcln = self._convert_int(fields[3], 'NDCLN')

                rec = schema.MultiTerminalDCRecord(
                    name=name, nconv=nconv, ndcbs=ndcbs, ndcln=ndcln,
                )

                if len(fields) > 4:
                    rec.mdc = self._convert_int(fields[4], 'MDC')
                if len(fields) > 5:
                    rec.vconv = self._convert_float(fields[5])
                if len(fields) > 6:
                    rec.vcmod = self._convert_float(fields[6])
                if len(fields) > 7:
                    rec.vconvn = self._convert_float(fields[7])

                # Skip sub-record lines (converters + DC buses + DC links)
                sub_lines = nconv + ndcbs + ndcln
                i += 1 + sub_lines

                records.append(rec)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing multi-terminal DC record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='MULTI_TERMINAL_DC'
                ) from e

        return records

    def _parse_multi_section_line_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse multi-section line grouping records.

        Multi-section line records are variable-length single-line records:
        - I, J, ID, MET: Fixed fields (4 fields)
        - DUM1-DUM9: Variable section identifiers (0-9 fields)

        Args:
            lines: Lines from multi-section line section

        Returns:
            List of MultiSectionLineRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num
            try:
                fields = self._tokenize(line)

                if len(fields) < 4:
                    raise Raw34ParseError(
                        f"Multi-section line record should have at least 4 fields, got {len(fields)}",
                        line_number=line_num,
                        line_content=line,
                        section='MULTI_SECTION'
                    )

                # Parse fixed fields
                msl = schema.MultiSectionLineRecord(
                    i=self._convert_int(fields[0], 'I'),
                    j=self._convert_int(fields[1], 'J'),
                    line_id=self._convert_string(fields[2]),
                    met=self._convert_int(fields[3], 'MET')
                )

                # Parse variable section identifiers (DUM1-DUM9)
                dum_fields = ['dum1', 'dum2', 'dum3', 'dum4', 'dum5', 'dum6', 'dum7', 'dum8', 'dum9']
                for i, field_name in enumerate(dum_fields):
                    field_index = 4 + i
                    if field_index < len(fields):
                        setattr(msl, field_name, self._convert_int(fields[field_index], field_name.upper()))

                records.append(msl)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing multi-section line record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='MULTI_SECTION'
                ) from e

        return records

    def _parse_zone_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.ZoneRecord]:
        """Parse zone data records.

        Args:
            lines: Lines from zone section

        Returns:
            List of ZoneRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 1:
                continue

            try:
                zone = schema.ZoneRecord(
                    zone_number=self._convert_int(fields[0], 'zone_number')
                )

                # Optional fields
                if len(fields) > 1:
                    zone.zone_name = self._convert_string(fields[1])

                records.append(zone)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing zone record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='ZONE'
                ) from e

        return records

    def _parse_interarea_transfer_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.InterareaTransferRecord]:
        """Parse interarea transfer data records.

        Args:
            lines: Lines from interarea transfer section

        Returns:
            List of InterareaTransferRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 2:
                continue

            try:
                transfer = schema.InterareaTransferRecord(
                    from_area=self._convert_int(fields[0], 'from_area'),
                    to_area=self._convert_int(fields[1], 'to_area')
                )

                # Optional fields
                if len(fields) > 2:
                    transfer.transfer_id = self._convert_string(fields[2])
                if len(fields) > 3:
                    transfer.power_transfer = self._convert_float(fields[3])

                records.append(transfer)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing interarea transfer record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='INTERAREA'
                ) from e

        return records

    def _parse_owner_records(
        self,
        lines: list[tuple[int, str]]
    ) -> list[schema.OwnerRecord]:
        """Parse owner data records.

        Args:
            lines: Lines from owner section

        Returns:
            List of OwnerRecord instances
        """
        records = []
        for line_num, line in lines:
            self.current_line = line_num
            fields = self._tokenize(line)

            if len(fields) < 1:
                continue

            try:
                owner = schema.OwnerRecord(
                    owner_number=self._convert_int(fields[0], 'owner_number')
                )

                # Optional fields
                if len(fields) > 1:
                    owner.owner_name = self._convert_string(fields[1])

                records.append(owner)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing owner record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='OWNER'
                ) from e

        return records

    def _parse_facts_device_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse FACTS device data records (single-line).

        Each FACTS device record is a single line with fields:
        NAME, I, J, MODE, PDES, QDES, VSET, SHMX, TRMX, VTMN, VTMX,
        VSMX, IMX, LINX, RMPCT, OWNER, SET1, SET2, VSREF, REMOT, MNAME, NREG

        Args:
            lines: Lines from FACTS device section

        Returns:
            List of FactsDeviceRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num
            try:
                fields = self._tokenize(line)
                if len(fields) < 2:
                    continue

                record = schema.FactsDeviceRecord(
                    name=fields[0].strip().strip("'"),
                    ibus=int(fields[1]),
                    jbus=int(fields[2]) if len(fields) > 2 else 0,
                    mode=int(fields[3]) if len(fields) > 3 else 1,
                    pdes=float(fields[4]) if len(fields) > 4 else 0.0,
                    qdes=float(fields[5]) if len(fields) > 5 else 0.0,
                    vset=float(fields[6]) if len(fields) > 6 else 1.0,
                    shmx=float(fields[7]) if len(fields) > 7 else 9999.0,
                    trmx=float(fields[8]) if len(fields) > 8 else 9999.0,
                    vtmn=float(fields[9]) if len(fields) > 9 else 0.9,
                    vtmx=float(fields[10]) if len(fields) > 10 else 1.1,
                    vsmx=float(fields[11]) if len(fields) > 11 else 1.0,
                    imx=float(fields[12]) if len(fields) > 12 else 9999.0,
                    linx=float(fields[13]) if len(fields) > 13 else 0.05,
                    rmpct=float(fields[14]) if len(fields) > 14 else 100.0,
                    owner=int(fields[15]) if len(fields) > 15 else 1,
                    set1=float(fields[16]) if len(fields) > 16 else 0.0,
                    set2=float(fields[17]) if len(fields) > 17 else 0.0,
                    vsref=int(fields[18]) if len(fields) > 18 else 0,
                    remot=int(fields[19]) if len(fields) > 19 else 0,
                    mname=fields[20].strip().strip("'") if len(fields) > 20 else "            ",
                    nreg=int(fields[21]) if len(fields) > 21 else 0,
                )
                records.append(record)
                logger.debug(
                    f"Line {line_num}: Parsed FACTS device '{record.name}' "
                    f"at bus {record.ibus}"
                )
            except Exception as e:
                logger.warning(f"Line {line_num}: Failed to parse FACTS device record: {e}")

        logger.info(f"Parsed {len(records)} FACTS device records")
        return records

    def _parse_switched_shunt_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse switched shunt data records (variable-length single line).

        Format: I, MODSW, ADJM, STAT, VSWHI, VSWLO, SWREG, RMPCT, RMIDNT, BINIT,
                [N1, B1, [N2, B2, ... [N8, B8]]]

        Args:
            lines: Lines from switched shunt section

        Returns:
            List of SwitchedShuntRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num

            try:
                fields = self._tokenize(line)
                if len(fields) < 1:
                    continue

                ss = schema.SwitchedShuntRecord(
                    bus_number=self._convert_int(fields[0], 'I'),
                )

                # Fixed fields (indices 1-9)
                if len(fields) > 1:
                    ss.modsw = self._convert_int(fields[1], 'MODSW')
                if len(fields) > 2:
                    ss.adjm = self._convert_int(fields[2], 'ADJM')
                if len(fields) > 3:
                    ss.status = self._convert_int(fields[3], 'STAT')
                if len(fields) > 4:
                    ss.vswhi = self._convert_float(fields[4])
                if len(fields) > 5:
                    ss.vswlo = self._convert_float(fields[5])
                if len(fields) > 6:
                    ss.swreg = self._convert_int(fields[6], 'SWREG')
                if len(fields) > 7:
                    ss.rmpct = self._convert_float(fields[7])
                if len(fields) > 8:
                    ss.rmidnt = self._convert_string(fields[8])
                if len(fields) > 9:
                    ss.binit = self._convert_float(fields[9])

                # Variable N/B pairs (indices 10+, up to 8 pairs)
                nb_names = ['n1', 'b1', 'n2', 'b2', 'n3', 'b3', 'n4', 'b4',
                            'n5', 'b5', 'n6', 'b6', 'n7', 'b7', 'n8', 'b8']
                for idx, attr_name in enumerate(nb_names):
                    field_index = 10 + idx
                    if field_index >= len(fields):
                        break
                    if idx % 2 == 0:  # N fields are int
                        setattr(ss, attr_name, self._convert_int(fields[field_index], attr_name.upper()))
                    else:  # B fields are float
                        setattr(ss, attr_name, self._convert_float(fields[field_index]))

                records.append(ss)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing switched shunt record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='SWITCHED_SHUNT'
                ) from e

        return records

    def _parse_gne_device_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse GNE (General Network Element) device data records (multi-line).

        Each record consists of:
        - Line 1: NAME, MODEL, NTERM, BUS1..BUSNTERM, NREAL, NINTG, NCHAR
        - Line 2: ST, OWNER, NMETR
        - ceil(NREAL/10) lines of real data values
        - ceil(NINTG/10) lines of integer data values
        - ceil(NCHAR/10) lines of character data values

        Args:
            lines: Lines from GNE device section

        Returns:
            List of GneDeviceRecord objects
        """
        import math
        records = []
        i = 0

        while i < len(lines):
            line_num, line = lines[i]
            self.current_line = line_num

            try:
                fields = self._tokenize(line)
                if len(fields) < 3:
                    i += 1
                    continue

                name = self._convert_string(fields[0])
                model = self._convert_string(fields[1])
                nterm = self._convert_int(fields[2], 'NTERM')

                # Bus numbers follow: BUS1..BUSNTERM
                bus_numbers = []
                for t in range(nterm):
                    idx = 3 + t
                    if idx < len(fields):
                        bus_numbers.append(self._convert_int(fields[idx], f'BUS{t+1}'))

                # After bus numbers: NREAL, NINTG, NCHAR
                base_idx = 3 + nterm
                nreal = self._convert_int(fields[base_idx], 'NREAL') if base_idx < len(fields) else 0
                nintg = self._convert_int(fields[base_idx + 1], 'NINTG') if base_idx + 1 < len(fields) else 0
                nchar = self._convert_int(fields[base_idx + 2], 'NCHAR') if base_idx + 2 < len(fields) else 0

                rec = schema.GneDeviceRecord(
                    name=name, model=model, nterm=nterm,
                    bus_numbers=bus_numbers,
                    nreal=nreal, nintg=nintg, nchar=nchar,
                )

                i += 1

                # Line 2: ST, OWNER, NMETR
                if i < len(lines):
                    _, line2 = lines[i]
                    f2 = self._tokenize(line2)
                    if len(f2) > 0:
                        rec.status = self._convert_int(f2[0], 'ST')
                    if len(f2) > 1:
                        rec.owner = self._convert_int(f2[1], 'OWNER')
                    if len(f2) > 2:
                        rec.nmetr = self._convert_int(f2[2], 'NMETR')
                    i += 1

                # Real data lines (10 values per line)
                real_lines = math.ceil(nreal / 10) if nreal > 0 else 0
                real_data = []
                for _ in range(real_lines):
                    if i < len(lines):
                        _, rline = lines[i]
                        real_data.extend(self._convert_float(v) for v in self._tokenize(rline))
                        i += 1
                rec.real_data = real_data[:nreal]

                # Integer data lines
                intg_lines = math.ceil(nintg / 10) if nintg > 0 else 0
                integer_data = []
                for _ in range(intg_lines):
                    if i < len(lines):
                        _, iline = lines[i]
                        integer_data.extend(self._convert_int(v, 'INTG') for v in self._tokenize(iline))
                        i += 1
                rec.integer_data = integer_data[:nintg]

                # Character data lines
                char_lines = math.ceil(nchar / 10) if nchar > 0 else 0
                character_data = []
                for _ in range(char_lines):
                    if i < len(lines):
                        _, cline = lines[i]
                        character_data.extend(self._convert_string(v) for v in self._tokenize(cline))
                        i += 1
                rec.character_data = character_data[:nchar]

                records.append(rec)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing GNE device record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='GNE'
                ) from e

        return records

    def _parse_induction_machine_records(self, lines: list[tuple[int, str]]) -> list:
        """Parse induction machine data records (single line per record).

        Format: I, ID, ST, SC, DC, AREA, ZONE, OWNER, TC, BC, MBASE, RATEKV,
                PC, PSET, H, A, B, D, E, RA, XA, XM, R1, X1, R2, X2, X3,
                E1, SE1, E2, SE2, IA1, IA2, XAMULT

        Args:
            lines: Lines from induction machine section

        Returns:
            List of InductionMachineRecord objects
        """
        records = []

        for line_num, line in lines:
            self.current_line = line_num

            try:
                fields = self._tokenize(line)
                if len(fields) < 2:
                    continue

                im = schema.InductionMachineRecord(
                    bus_id=self._convert_int(fields[0], 'I'),
                    name=self._convert_string(fields[1]) if len(fields) > 1 else '1 ',
                )

                # Int fields: (field_index, attribute_name)
                int_map = [
                    (2, 'status'), (3, 'scode'), (4, 'dcode'),
                    (5, 'area'), (6, 'zone'), (7, 'owner'),
                    (8, 'tcode'), (9, 'bcode'), (12, 'pcode'),
                ]
                for idx, attr in int_map:
                    if idx < len(fields):
                        setattr(im, attr, self._convert_int(fields[idx], attr.upper()))

                # Float fields: (field_index, attribute_name)
                float_map = [
                    (10, 'mbase'), (11, 'ratekv'), (13, 'pset'),
                    (14, 'h'), (15, 'a'), (16, 'b'), (17, 'd'), (18, 'e'),
                    (19, 'ra'), (20, 'xa'), (21, 'xm'),
                    (22, 'r1'), (23, 'x1'), (24, 'r2'), (25, 'x2'), (26, 'x3'),
                    (27, 'e1'), (28, 'se1'), (29, 'e2'), (30, 'se2'),
                    (31, 'ia1'), (32, 'ia2'), (33, 'xamult'),
                ]
                for idx, attr in float_map:
                    if idx < len(fields):
                        setattr(im, attr, self._convert_float(fields[idx]))

                records.append(im)

            except Exception as e:
                if isinstance(e, Raw34ParseError):
                    raise
                raise Raw34ParseError(
                    f"Error parsing induction machine record: {e}",
                    line_number=line_num,
                    line_content=line,
                    section='INDUCTION'
                ) from e

        return records
