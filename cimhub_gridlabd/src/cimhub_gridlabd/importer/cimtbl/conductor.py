"""GLM ``overhead_line_conductor``, ``underground_line_conductor``, ``triplex_line_conductor`` -> one ``.cimtbl``
each: the wire catalogs.

One ``WireInfo`` per conductor, values as the deck writes them, in their written units. An underground conductor
is a ``ConcentricNeutralCableInfo`` (neutral strands), a ``TapeShieldCableInfo`` (a shield) or, with neither, a
bare ``OverheadWireInfo`` (S2-5). A triplex conductor is an ``OverheadWireInfo``: CIM has no triplex class, and the
insulation is on the configuration. Summer ratings become ``ratedCurrent`` and an AssetInfo ``OperationalLimitSet``
(D9); unset ratings are not filled (S2-7).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s2-catalogs``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import (HEADER_FIELDS, label, limit_rows, limit_tables, provenance, rating_fields, ratings, written_columns)
from cimhub_gridlabd.schema import gridlabd as schema

OVERHEAD, CN, TS = "OverheadWireInfo", "ConcentricNeutralCableInfo", "TapeShieldCableInfo"

_RESISTANCE = "Kersting's 50 C AC value, which the Java exporter writes from rAC50 (S2-6)"
_RADIUS = "radius = diameter / 2 (radius_from_diameter), in the diameter's unit"

OVERHEAD_FIELDS = {
    "name": Field("copied", ((OVERHEAD, "name", None),), "mRID = ohc_ + name"),
    **HEADER_FIELDS,
    "geometric_mean_radius": Field("copied", ((OVERHEAD, "gmr", "{unit}"),), "unset raises"),
    "resistance": Field("copied", ((OVERHEAD, "rAC50", "{unit}"),), _RESISTANCE + "; unset raises"),
    "diameter": Field("derived", ((OVERHEAD, "radius", "{unit}"),), _RADIUS),
    **rating_fields((OVERHEAD,)),
}

TRIPLEX_FIELDS = {
    "name": Field("copied", ((OVERHEAD, "name", None),), "mRID = tpc_ + name"),
    **HEADER_FIELDS,
    "resistance": OVERHEAD_FIELDS["resistance"],
    "geometric_mean_radius": OVERHEAD_FIELDS["geometric_mean_radius"],
    **rating_fields((OVERHEAD,)),
}

_ALL = (OVERHEAD, CN, TS)
_CABLES = (CN, TS)
_SHIELD_GAP = ("no CIM home; Kersting derives it from the screen diameter and tape thickness (eq. 4.89), as the "
               "Java exporter does. The taxonomy CN cables write 0.00")

UNDERGROUND_FIELDS = {
    "name": Field("copied", tuple((info, "name", None) for info in _ALL), "mRID = ugc_ + name"),
    **HEADER_FIELDS,
    "outer_diameter": Field("copied", tuple((info, "diameterOverJacket", "{unit}") for info in _CABLES),
                            "on a bare wire untranscribed (no jacket; the Java exporter writes 1.2 x diameter, "
                            "canBury)"),
    "conductor_gmr": Field("copied", tuple((info, "gmr", "{unit}") for info in _ALL), "unset raises"),
    "conductor_diameter": Field("derived", tuple((info, "radius", "{unit}") for info in _ALL), _RADIUS),
    "conductor_resistance": Field("copied", tuple((info, "rAC50", "{unit}") for info in _ALL),
                                  _RESISTANCE + "; unset raises"),
    "neutral_gmr": Field("copied", ((CN, "neutralStrandGmr", "{unit}"),)),
    "neutral_diameter": Field("derived", ((CN, "neutralStrandRadius", "{unit}"),),
                              "neutralStrandRadius = neutral_diameter / 2 (radius_from_diameter)"),
    "neutral_resistance": Field("copied", ((CN, "neutralStrandRDC20", "{unit}"),),
                                "the strand's DC value, as the Java exporter reads it"),
    "neutral_strands": Field("copied", ((CN, "neutralStrandCount", None),), "> 0 selects the CN class (S2-5)"),
    "shield_thickness": Field("copied", ((TS, "tapeThickness", "{unit}"),), "> 0 selects the TS class (S2-5)"),
    "shield_diameter": Field("copied", ((TS, "diameterOverScreen", "{unit}"),),
                             "the Java exporter writes it from diameterOverScreen"),
    "insulation_relative_permitivitty": Field("untranscribed", note="no CableInfo home (as DSS EpsR); GridLAB-D "
                                                                    "default 1.0, the Java exports write 2.3"),
    "shield_gmr": Field("untranscribed", note=_SHIELD_GAP),
    "shield_resistance": Field("untranscribed", note=_SHIELD_GAP),
    **rating_fields(_ALL),
}

#: ``(native class, mRID prefix, FIELDS)`` per conductor catalog, in ``Import`` order.
CATALOGS = (
    (schema.OverheadLineConductor, "ohc_", OVERHEAD_FIELDS),
    (schema.UndergroundLineConductor, "ugc_", UNDERGROUND_FIELDS),
    (schema.TriplexLineConductor, "tpc_", TRIPLEX_FIELDS),
)
PREFIX = {native_class: prefix for native_class, prefix, _ in CATALOGS}
FIELDS = {native_class: fields for native_class, _, fields in CATALOGS}

#: The slots that only one cable class has a home for: set (not 0) on another class raises.
_CLASS_ONLY = {"neutral_gmr": CN, "neutral_diameter": CN, "neutral_resistance": CN, "neutral_strands": CN,
               "shield_thickness": TS, "shield_diameter": TS}
#: The diameter slots whose half is a derived radius column, per native class: ``(slot, column)``.
_RADII = {
    schema.OverheadLineConductor: (("diameter", "radius"),),
    schema.UndergroundLineConductor: (("conductor_diameter", "radius"), ("neutral_diameter", "neutralStrandRadius")),
    schema.TriplexLineConductor: (),
}


def radius_from_diameter(diameter: float) -> float:
    return diameter / 2


def info_class(conductor) -> str:
    """The ``WireInfo`` class of a conductor (S2-5)."""
    if not isinstance(conductor, schema.UndergroundLineConductor):
        return OVERHEAD
    strands = (conductor.neutral_strands or 0) > 0
    shield = (conductor.shield_thickness or 0) > 0
    if strands and shield:
        raise ValueError(f"{label(conductor)}: sets both neutral_strands and shield_thickness (two cable kinds)")
    return CN if strands else TS if shield else OVERHEAD


def _check(conductor, info: str) -> None:
    gmr, resistance = (("conductor_gmr", "conductor_resistance") if isinstance(conductor, schema.UndergroundLineConductor)
                       else ("geometric_mean_radius", "resistance"))
    for slot in (gmr, resistance):
        if getattr(conductor, slot) is None:
            raise ValueError(f"{label(conductor)}: {slot} unset (GridLAB-D would take 0, and ln(1/GMR) fails)")
    misplaced = [slot for slot, home in _CLASS_ONLY.items()
                 if home != info and getattr(conductor, slot, None) not in (None, 0)]
    if misplaced:
        raise ValueError(f"{label(conductor)}: {', '.join(misplaced)} set on a {info}, which has no home for them")


def _row(model: GlmModel, conductor, prefix: str, fields: dict[str, Field]) -> tuple[str, tuple[Column, ...], Row]:
    """The class, columns and row of one conductor."""
    info = info_class(conductor)
    _check(conductor, info)
    info_mrid = mrid(prefix, conductor.name)
    pairs = written_columns(model, conductor, fields, info)
    for slot, column in _RADII[type(conductor)]:
        diameter = getattr(conductor, slot)
        if diameter is not None and (column == "radius" or info == CN):
            pairs.append((Column(column, registry_unit(model.unit(conductor, slot))),
                          cell(radius_from_diameter(diameter))))
    limits, unset = ratings(conductor)
    pairs.append((Column("OperationalLimitSet"), f"{info_mrid}_limits" if limits else None))
    notes = []
    if unset:
        notes.append(f"not filled (S2-7): {', '.join(unset)}")
    if info == OVERHEAD and getattr(conductor, "outer_diameter", None) is not None:
        notes.append(f"untranscribed on a bare wire: outer_diameter={cell(conductor.outer_diameter)}")
    untranscribed = untranscribed_values(fields, conductor)
    if untranscribed:
        notes.append(untranscribed)
    columns = tuple(column for column, _ in pairs)
    return info, columns, Row([info_mrid, *(text for _, text in pairs)], comment="\n".join(notes) or None)


def _derived_note(native_class: type, columns: tuple[Column, ...]) -> str | None:
    names = {column.name for column in columns}
    derived = [f"{column} = {slot} / 2" for slot, column in _RADII[native_class] if column in names]
    return "derived (radius_from_diameter): " + ", ".join(derived) if derived else None


def map_conductors(model: GlmModel, native_class: type) -> Document:
    """Every conductor of one GLM conductor class as one document, one table per (class, units)."""
    prefix, fields = PREFIX[native_class], FIELDS[native_class]
    conductors = model.list_by_class(native_class)
    by_columns: dict[tuple[str, tuple[Column, ...]], list[Row]] = {}
    limit_sets, limits = [], []
    for conductor in conductors:
        info, columns, row = _row(model, conductor, prefix, fields)
        by_columns.setdefault((info, columns), []).append(row)
        rated, _ = ratings(conductor)
        if rated:
            info_mrid = mrid(prefix, conductor.name)
            limit_sets.append(f"{info_mrid}_limits")
            limits += limit_rows(info_mrid, rated)
    statements = [*limit_tables(limit_sets, limits),
                  *(Table(info, [Column("mRID"), *columns], rows, comment=_derived_note(native_class, columns))
                    for (info, columns), rows in by_columns.items())]
    targets = ", ".join(sorted({info for info, _ in by_columns}))
    return Document(name=native_class.class_name, statements=statements, profile=CIM_PROFILE,
                    comment=provenance(native_class.class_name, targets, len(conductors)) if conductors else None)


def wire_info_mrid(conductor) -> str:
    """The ``WireInfo`` mRID of a conductor record."""
    return mrid(PREFIX[type(conductor)], conductor.name)

