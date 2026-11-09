"""Tie flows: the ``TieFlow`` pairs of a device whose terminals' buses lie in more than one AREA (R5).

The device's home end is its non-metered end, whose area PSS/E charges with the device's losses. Each terminal whose
bus is outside the home area carries two ``TieFlow``s: its bus's area with ``positiveFlowIn = false`` (flow into the
terminal leaves that area) and the home area with ``positiveFlowIn = true``. The two sum to zero, as ControlArea's
rule 3 asks of a tie seen from both areas. Branches, switches and transformers write their own (MET / NMETR are
their fields).

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#tie-flows``.
"""

from __future__ import annotations

from cimtables.document import Column, Row, Table

from cimhub_core.cimtbl import lookup, mrid
from cimhub_raw.importer.cimtbl.area_interchange import area_mrid

PREFIX = "tf_"  # requested from the cimtbl-translate table owners (plan C3)

#: branch MET / switch METERED -> the home (non-metered) end: 1 meters bus I, so J is home
HOME_END = {1: 2, 2: 1}


class TieFlowRows:
    """The ``TieFlow`` rows of a document's ties, collected device by device."""

    def __init__(self, bus_area: dict[int, int], control_areas: set[int]):
        self.bus_area = bus_area
        self.control_areas = control_areas
        self.rows: list[Row] = []

    def is_tie(self, buses: tuple[int, ...]) -> bool:
        return len({self.bus_area[bus] for bus in buses}) > 1

    def add(self, equipment_mrid: str, key: str, buses: tuple[int, ...], home_end: int, record_id: str,
            terminals: tuple[str, ...] | None = None) -> None:
        """A pair on each terminal ``<equipment>_T<k>`` (k = 1..) whose bus is outside the home end's area. Call only
        for a tie (``is_tie``): ``home_end`` is looked up from MET / NMETR only there. ``terminals``: the terminal
        mRIDs, one per bus, when they belong to different equipment (a DC line's converters, P2-3)."""
        home_area = self.bus_area[buses[home_end - 1]]
        for end, bus in enumerate(buses, start=1):
            area = self.bus_area[bus]
            if area == home_area:
                continue
            terminal = terminals[end - 1] if terminals else f"{equipment_mrid}_T{end}"
            for flow_area, flows_in in ((area, "false"), (home_area, "true")):
                if flow_area not in self.control_areas:
                    raise ValueError(f"{record_id}: AREA {flow_area} has no area-interchange record (no ControlArea "
                                     f"{area_mrid(flow_area)})")
                self.rows.append(Row([mrid(PREFIX, f"{flow_area}_{terminal}"), f"{flow_area}_{key}_T{end}", flows_in,
                                      area_mrid(flow_area), terminal]))

    def tables(self, metered_flag: str) -> list[Table]:
        if not self.rows:
            return []
        return [Table("TieFlow", [Column("mRID"), Column("name"), Column("positiveFlowIn"), Column("ControlArea"),
                                  Column("Terminal")], self.rows,
                      comment=f"tie flows: two TieFlows on each tie's metered terminal, positiveFlowIn = false for "
                              f"the terminal's bus's area and true for the home (non-metered) end's area "
                              f"({metered_flag})")]


def off_tie_note(untranscribed: str | None, metered_flag: str) -> str:
    """A device table's comment: its untranscribed names, and where its metered-end flag is still untranscribed."""
    note = f"untranscribed off a tie: {metered_flag} (a tie's TieFlows record it; CIM 18 gap, RAW-22)"
    return "\n".join(filter(None, [untranscribed, note]))


def branch_home_end(metered_end: int, record_id: str, slot: str = "metered_end") -> int:
    """The home end of a two-terminal tie from its MET / METERED: any code other than 1 or 2 raises."""
    return lookup(HOME_END, metered_end, slot=slot, record_id=record_id)

