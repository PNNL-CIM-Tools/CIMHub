"""What the S3a line and switch mappers share: the link slots, the ends, the ratings and the provenance header.

Every GridLAB-D branch is a ``link``: ``from`` and ``to`` are bus objects, solved as their root bus (GLM-4), and
``continuous_rating_X``/``emergency_rating_X`` are its own ratings. Those go, as written, on the equipment's own
``OperationalLimitSet`` (D9, S3a-4, S3a-5).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3a-lines-and-switches``.
"""

from __future__ import annotations

from cimtables.document import Column, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import Field, field_names
from cimhub_gridlabd.importer.cimtbl.catalog import label, limit_rows, native_name

#: The per-phase rating slots of a link: ``(suffix, slots)``.
RATING_SLOTS = (("norm", tuple(f"continuous_rating_{phase}" for phase in "ABC")),
                ("emerg", tuple(f"emergency_rating_{phase}" for phase in "ABC")))

_HEADER = Field("untranscribed", note="object header; no deck sets it on a link")
_RATING = {"norm": Field("structural", note="the normal CurrentLimit of the equipment's own OperationalLimitSet "
                                            "<mRID>_limits (S3a-4, S3a-5); the set phases must agree"),
           "emerg": Field("structural", note="the emergency CurrentLimit of that set")}

#: The link slots every line and switch has, but ``phases`` and ``status``, whose rule is per class.
LINK_FIELDS = {
    "from_node": Field("structural", note="node1: the root bus of the object it names (GLM-4)"),
    "to": Field("structural", note="node2: the root bus of the object it names (GLM-4)"),
    **{slot: _HEADER for slot in ("parent", "groupid", "latitude", "longitude", "in_svc", "out_svc", "rank", "flags")},
    **{slot: _RATING[suffix] for suffix, slots in RATING_SLOTS for slot in slots},
    "nominal_voltage": Field("untranscribed", note="the walk gives the BaseVoltage (GLM-1)"),
    "mean_repair_time": Field("untranscribed", note="reliability data"),
    "pdispatch": Field("untranscribed", note="dispatch control; no network-profile home"),
    "pdispatch_offset": Field("untranscribed", note="dispatch control; no network-profile home"),
    "set_pdispatch": Field("untranscribed", note="dispatch control; no network-profile home"),
}

#: ``(note, exact names, prefixes)``: the untranscribed link slots by group.
_GROUPS = (
    ("solver output or state", ("overloaded_status", "flow_direction", "triplex_neutral_1_value",
                                "triplex_neutral_2_value", "condition", "solution"), ("power_", "current_", "fault_")),
    ("inrush solver setting", (), ("inrush_",)),
)


def classify(native_cls: type, own: dict[str, Field]) -> dict[str, Field]:
    """``FIELDS`` of one link class: ``own`` (``name``, ``phases``, ``status`` and the class's slots), the link
    slots, then the untranscribed groups, in schema order. Raises on a slot nothing claims."""
    fields = {**LINK_FIELDS, **own}
    for slot in field_names(native_cls):
        if slot in fields:
            continue
        note = next((note for note, names, prefixes in _GROUPS if slot in names or slot.startswith(prefixes)), None)
        if note is None:
            raise ValueError(f"{native_cls.__name__}.{slot} is not classified (importer/cimtbl/link.py)")
        fields[slot] = Field("untranscribed", note=note)
    return {slot: fields[slot] for slot in field_names(native_cls)}


def ends(record, roots: dict[str, str], buses: dict[str, BusSystem]) -> tuple[str, str, BusSystem]:
    """``(node1, node2, node1's BusSystem)``: the root buses of ``from`` and ``to`` (the walk checked both)."""
    node1, node2 = roots[record.from_node], roots[record.to]
    return node1, node2, buses[node1]


def link_ratings(record) -> dict[str, float]:
    """``{"norm": A, "emerg": A}`` of a link's own ratings (either may be missing); set phases that differ raise."""
    limits = {}
    for suffix, slots in RATING_SLOTS:
        values = {getattr(record, slot) for slot in slots if getattr(record, slot) is not None}
        if len(values) > 1:
            written = ", ".join(f"{native_name(record, slot)}={getattr(record, slot)}" for slot in slots
                                if getattr(record, slot) is not None)
            raise ValueError(f"{label(record)}: {written}; one rating per link is mapped")
        if values:
            limits[suffix] = float(values.pop())
    return limits


class Limits:
    """The ``OperationalLimitSet`` and ``CurrentLimit`` rows of one document's equipment."""

    def __init__(self):
        self.sets: list[Row] = []
        self.limits: list[Row] = []

    def add(self, equipment: str, limits: dict[str, float], comment: str | None = None) -> None:
        if limits:
            self.sets.append(Row([f"{equipment}_limits", equipment], comment=comment))
            self.limits += limit_rows(equipment, limits)

    def tables(self) -> list[Table]:
        if not self.sets:
            return []
        return [Table("OperationalLimitSet", [Column("mRID"), Column("Equipment")], self.sets),
                Table("CurrentLimit", [Column("mRID"), Column("normalValue", "A"), Column("OperationalLimitType"),
                                       Column("OperationalLimitSet")], self.limits)]


def provenance(native: str, targets: str, count: int) -> str:
    return (f"GridLAB-D {native} -> {targets}.\nSource table: {native} (records: {count})\n"
            "Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3a-lines-and-switches")
