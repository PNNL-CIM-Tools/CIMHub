"""raw RAW v34 File Writer

This module provides a FormatWriter implementation for PSS/E RAW version 34
files. It writes a GraphModel of RAW record dataclasses to a complete RAW file
using the AnnotationSerializer from cimhub_core.

Usage::

    from cimhub_raw.raw34_reader import Raw34Reader
    from cimhub_raw.raw34_writer import Raw34Writer

    Raw34Writer().write(Raw34Reader("input.raw").read_all(), "output.raw")

Features:
    - Section-based output with proper BEGIN/END markers
    - Automatic field formatting via AnnotationSerializer
    - Multi-line record support (transformers, DC lines, etc.)
    - Proper terminator handling ("0 /" between sections)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cimhub_core.base import FormatWriter
from cimhub_core.serialization import AnnotationSerializer
from cimhub_core import GraphModel
import cimhub_raw.schema.raw_v34.raw34_schema as schema

__all__ = ["Raw34Writer"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Section markers for raw RAW v34 format
SECTION_MARKERS = {
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


class Raw34Writer(FormatWriter):
    """Writer for raw RAW v34 format files.

    This writer implements the FormatWriter interface from cimhub_core and
    writes all 19 record types defined in the raw RAW v34 specification.
    """

    def __init__(self):
        """Initialize writer with AnnotationSerializer."""
        self.serializer = AnnotationSerializer(separator=',')

    def _write_case_record(self, f, case_record: schema.CaseIdentificationRecord) -> None:
        """Write case identification record (special multi-part format).

        Format:
            Line 1: IC, SBASE, REV, XFRRAT, NXFRAT, BASFRQ
            Lines 2-3: Title lines (required by PSS/E; written as blank when not set)
            Lines 4-9: Configuration lines (GENERAL, GAUSS, NEWTON, etc.) (optional)
            Lines 10+: RATING lines (optional)

        Args:
            f: File object to write to
            case_record: Case identification record
        """
        # Write first line with numeric fields
        parts = [
            str(case_record.new_case_flag),
            f"{case_record.system_base_mva:.2f}",
            str(int(case_record.revision)),
            str(case_record.transformer_ratings_units),
            str(case_record.branch_ratings_units),
            f"{case_record.system_base_frequency:.2f}",
        ]
        f.write(','.join(parts))
        f.write('\n')

        # PSS/E v34 unconditionally reads exactly two title lines after the
        # first line before entering the system-wide data section.  Always
        # write both (blank when not populated) so the section-transition
        # marker that follows is not mis-consumed as title text.
        title_1 = getattr(case_record, 'title_line_1', None) or ''
        title_2 = getattr(case_record, 'title_line_2', None) or ''
        # Fall back to the schema titles list when individual attrs are absent
        if not title_1 and not title_2:
            titles_list = list(getattr(case_record, 'titles', None) or [])
            title_1 = titles_list[0] if len(titles_list) > 0 else ''
            title_2 = titles_list[1] if len(titles_list) > 1 else ''
        f.write(title_1 + '\n')
        f.write(title_2 + '\n')

        # Write configuration lines
        for field_name in ['general', 'gauss', 'newton', 'adjust', 'tysl', 'solver']:
            value = getattr(case_record, field_name, None)
            if value:
                f.write(value)
                f.write('\n')

        # Write rating lines
        if hasattr(case_record, 'ratings') and case_record.ratings:
            for rating in case_record.ratings:
                f.write(rating)
                f.write('\n')

    def _serialize_vsc_group(self, records: list) -> str:
        """Serialize one VSC DC line as its 3-line RAW block.

        The reader creates one ``VscDcRecord`` per converter (two per DC line),
        each carrying a copy of the shared line-level header. Serializing them
        independently would repeat that header, so emit it once from the first
        record and then only the converter line of each subsequent record.

        Args:
            records: The VscDcRecord objects belonging to one DC line.

        Returns:
            The RAW block: header line followed by one line per converter.
        """
        header, first_converter = self.serialize(records[0]).split('\n', 1)
        converters = [first_converter]
        for record in records[1:]:
            converters.append(self.serialize(record).split('\n', 1)[1])
        return '\n'.join([header, *converters])

    def _write_vsc_records(self, f, records: list) -> None:
        """Write VSC DC records, grouping each DC line's converters together."""
        groups: dict[Any, list] = {}
        for record in records:
            groups.setdefault(record.name, []).append(record)

        for group in groups.values():
            f.write(self._serialize_vsc_group(group))
            f.write('\n')

    def _write_section(self, f, section_name: str, records: list,
                       prev_section_name: str = None, next_section_name: str = None) -> None:
        """Write a section with BEGIN/END markers and records.

        Args:
            f: File object to write to
            section_name: Section name key (e.g., 'BUS', 'LOAD')
            records: List of record objects for this section
            prev_section_name: Previous section name (for END marker)
            next_section_name: Next section name (unused)
        """
        begin_marker, end_marker = SECTION_MARKERS[section_name]

        # Write transition from previous section.
        # For the first section the "previous" terminator is the system-wide
        # data end marker, so both pieces appear on the same line as PSS/E requires:
        #   0 / END OF SYSTEM-WIDE DATA, BEGIN BUS DATA
        if prev_section_name:
            prev_end_marker = SECTION_MARKERS[prev_section_name][1]
            f.write(f'{prev_end_marker}, {begin_marker}\n')
        else:
            f.write(f'0 / END OF SYSTEM-WIDE DATA, {begin_marker}\n')

        # Write records
        if records:
            if section_name == 'VSC_DC':
                self._write_vsc_records(f, records)
            else:
                for record in records:
                    serialized = self.serialize(record)
                    f.write(serialized)
                    f.write('\n')

        # Write terminator if this is the last section
        if not next_section_name:
            f.write(f'{end_marker}\n')

    def write(self, model: GraphModel, destination: str) -> None:
        """Write a GraphModel containing RAW records to a RAW file.

        Writes directly from the GraphModel without constructing a RawModel,
        which avoids the LinkML schema's unique-key validation on load_records
        (a bus can legitimately have multiple loads distinguished by load_id).

        Args:
            model: GraphModel containing RAW schema dataclass instances
            destination: Path to output .raw file
        """
        sections = [
            ('BUS',           model.list_by_class(schema.BusRecord) or []),
            ('LOAD',          model.list_by_class(schema.LoadRecord) or []),
            ('FIXED_SHUNT',   model.list_by_class(schema.FixedShuntRecord) or []),
            ('GENERATOR',     model.list_by_class(schema.GeneratorRecord) or []),
            ('BRANCH',        model.list_by_class(schema.BranchRecord) or []),
            ('SWITCH',        model.list_by_class(schema.SwitchRecord) or []),
            ('TRANSFORMER',   model.list_by_class(schema.TransformerRecord) or []),
            ('AREA',          model.list_by_class(schema.AreaInterchangeRecord) or []),
            ('TWO_TERM_DC',   model.list_by_class(schema.TwoTerminalDCRecord) or []),
            ('VSC_DC',        model.list_by_class(schema.VscDcRecord) or []),
            ('IMPEDANCE',     model.list_by_class(schema.ImpedanceCorrectionRecord) or []),
            ('MULTI_TERM_DC', model.list_by_class(schema.MultiTerminalDCRecord) or []),
            ('MULTI_SECTION', model.list_by_class(schema.MultiSectionLineRecord) or []),
            ('ZONE',          model.list_by_class(schema.ZoneRecord) or []),
            ('INTERAREA',     model.list_by_class(schema.InterareaTransferRecord) or []),
            ('OWNER',         model.list_by_class(schema.OwnerRecord) or []),
            ('FACTS',         model.list_by_class(schema.FactsDeviceRecord) or []),
            ('SWITCHED_SHUNT',model.list_by_class(schema.SwitchedShuntRecord) or []),
            ('GNE',           model.list_by_class(schema.GneDeviceRecord) or []),
            ('INDUCTION',     model.list_by_class(schema.InductionMachineRecord) or []),
        ]

        dest_path = Path(destination)
        logger.info(f"Writing {destination}")

        with open(dest_path, 'w', encoding='utf-8') as f:
            case_record = model.first(schema.CaseIdentificationRecord)
            if case_record:
                self._write_case_record(f, case_record)

            for i, (section_name, records) in enumerate(sections):
                prev_section_name = sections[i-1][0] if i > 0 else None
                next_section_name = sections[i+1][0] if i < len(sections) - 1 else None
                self._write_section(f, section_name, records, prev_section_name, next_section_name)

            f.write('Q\n')

        logger.info(f"Successfully wrote {destination}")

    def serialize(self, obj: Any) -> str:
        """Convert a single dataclass instance to its RAW format string.

        Uses AnnotationSerializer to format fields according to schema annotations.

        Args:
            obj: A LinkML-generated dataclass instance (e.g., BusRecord, LoadRecord)

        Returns:
            The RAW format representation (may contain newlines for multi-line records)
        """
        return self.serializer.serialize(obj)
