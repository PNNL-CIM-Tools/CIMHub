"""The DC side of a RAW DC line (P2-1): a ``DCLine`` container holding two ``DCTopologicalNode``s and a
``DCLineSegment`` between them, and one ``ACDCConverterDCTerminal`` (polarity positive) per converter. RAW gives one
equivalent pole, so no return path is modeled. Bus-branch, as the AC buses are ``TopologicalNode``s. VSC lines
write these now; two-terminal lines will reuse them (P2b).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#dc-topology-decision-p2-1``.
"""

from __future__ import annotations

from cimtables.document import Column, Row, Table

from cimhub_core.cimtbl import cell


class DCRows:
    """The DC rows of a document's lines and converters, collected line by line."""

    def __init__(self):
        self.lines: list[Row] = []
        self.nodes: list[Row] = []
        self.segments: list[Row] = []
        self.segment_terminals: list[Row] = []
        self.converter_terminals: list[Row] = []

    def add_line(self, line: str, name: str, resistance_ohm: float, in_service: bool,
                 comment: str | None = None) -> tuple[str, str]:
        """The line ``line``, its nodes ``<line>_n1`` / ``_n2`` and its segment ``<line>_seg`` (an RDC of 0 is still a
        segment); returns the two nodes."""
        self.lines.append(Row([line, name], comment=comment))
        nodes = (f"{line}_n1", f"{line}_n2")
        for number, node in enumerate(nodes, start=1):
            self.nodes.append(Row([node, f"{name}_n{number}", line]))
        segment = f"{line}_seg"
        self.segments.append(Row([segment, name, cell(resistance_ohm), cell(in_service), line]))
        for number, node in enumerate(nodes, start=1):
            self.segment_terminals.append(Row([f"{segment}_DC{number}", segment, node, str(number)]))
        return nodes

    def add_converter(self, converter: str, node: str) -> None:
        self.converter_terminals.append(Row([f"{converter}_DC1", converter, node, "1"]))

    def tables(self, line_comment: str | None = None) -> list[Table]:
        """The line-side tables, in bind order: lines, nodes, segments, segment terminals."""
        return [
            Table("DCLine", [Column("mRID"), Column("name")], self.lines, comment=line_comment),
            Table("DCTopologicalNode", [Column("mRID"), Column("name"), Column("DCEquipmentContainer")], self.nodes,
                  comment="two per line: n1 at converter 1 (or the rectifier), n2 at the other"),
            Table("DCLineSegment", [Column("mRID"), Column("name"), Column("resistance", "ohm"), Column("inService"),
                                    Column("EquipmentContainer")], self.segments, comment="resistance = RDC"),
            Table("DCTerminal", [Column("mRID"), Column("DCConductingEquipment"), Column("DCTopologicalNode"),
                                 Column("sequenceNumber")], self.segment_terminals),
        ]

    def converter_terminal_table(self) -> Table:
        """After the converters: each converter's one DC terminal on its node."""
        return Table("ACDCConverterDCTerminal",
                     [Column("mRID"), Column("DCConductingEquipment"), Column("DCTopologicalNode"),
                      Column("sequenceNumber"), Column("polarity", default="positive")],
                     self.converter_terminals, comment="one per converter, polarity positive (one equivalent pole, "
                                                       "no return path)")
