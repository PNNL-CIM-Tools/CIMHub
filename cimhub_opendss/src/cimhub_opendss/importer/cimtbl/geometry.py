"""OpenDSS ``LineSpacing`` and ``LineGeometry`` -> ``linespacing.cimtbl``, ``linegeometry.cimtbl``.

Geometry stays geometry (``conductor-geometry`` skill): a LineSpacing is an ``XYSpacing`` template with one
``XYConductorPosition`` per conductor; a LineGeometry is a ``WireConfiguration`` with one
``WireSequenceConfiguration`` per conductor, naming its wire or cable. A geometry that gives its positions inline
(``cond=1 x=.. h=..``) gets its own synthesized ``XYSpacing``. No impedance is computed.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#linespacing-and-linegeometry``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, ObjectStatement, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, lookup, mrid, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import wire
from cimhub_opendss.importer.cimtbl.linecode import LENGTH_UNIT
from cimhub_opendss.schema import opendss_schema as schema

_SPACING = "XYSpacing"
_POSITION = "XYConductorPosition"
_CONFIGURATION = "WireConfiguration"
_RATING = "no home on a WireConfiguration; instance limits or untranscribed (plan D9)"
_FOLDED = "the reader folds the cond= blocks into the arrays; set alone (no cond=) it raises"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"

LINESPACING_FIELDS = {
    "name": Field("copied", ((_SPACING, "name", None),), "mRID = spc_ + name, lowercased; isTemplate = true"),
    "nconds": Field("structural", note="one XYConductorPosition per conductor, sequenceNumber 1..nconds; x and h "
                                       "must have nconds values"),
    "nphases": Field("structural", note="kind: phase for conductors 1..nphases, neutral after"),
    "x": Field("structural", note="XYConductorPosition.xCoord ({length}), one per conductor"),
    "h": Field("structural", note="XYConductorPosition.yCoord ({length}), one per conductor"),
    "units": Field("mapped", note="the length unit of xCoord and yCoord (LENGTH_UNIT); unset raises"),
    "detailed": Field("structural", note=_NOT_MAPPED + " (the equivalent-distance form has no positions)"),
    "EqDistPhPh": Field("structural", note=_NOT_MAPPED + " (the equivalent-distance form has no positions)"),
    "EqDistPhN": Field("structural", note=_NOT_MAPPED + " (the equivalent-distance form has no positions)"),
    "AvgPhaseHeight": Field("structural", note=_NOT_MAPPED + " (the equivalent-distance form has no positions)"),
    "AvgNeutralHeight": Field("structural", note=_NOT_MAPPED + " (the equivalent-distance form has no positions)"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

LINEGEOMETRY_FIELDS = {
    "name": Field("copied", ((_CONFIGURATION, "name", None),), "mRID = wc_ + name, lowercased"),
    "nconds": Field("structural", note="one WireSequenceConfiguration per conductor, sequenceNumber 1..nconds; "
                                       "the conductor names and (inline) positions must have nconds values"),
    "nphases": Field("copied", ((_CONFIGURATION, "numberOfPhases", None),),
                     "also the kind of an inline position: phase for 1..nphases, neutral after"),
    "spacing": Field("structural", note="WireConfiguration.WireSpacing = spc_ + spacing; with inline positions it "
                                        "raises"),
    "xs": Field("structural", note="inline positions: a synthesized XYSpacing wc_<name>_spc, xCoord ({length})"),
    "hs": Field("structural", note="inline positions: the synthesized XYSpacing's yCoord ({length})"),
    "units": Field("mapped", note="the length unit of the inline positions (LENGTH_UNIT); unset raises. The "
                                  "reader raises when the cond= blocks give different units"),
    "wires": Field("structural", note="the conductor names in cond order; each resolves to exactly one of "
                                      "WireData, CNData, TSData (a name in two raises) and is the "
                                      "WireSequenceConfiguration.WireInfo. A mixed assembly (607: a TS phase, a "
                                      "bare neutral) arrives here whole, so the array carries no kind"),
    "cncables": Field("structural", note="as wires; only one of wires, cncables, tscables may be set"),
    "tscables": Field("structural", note="as wires; only one of wires, cncables, tscables may be set"),
    "cond": Field("structural", note=_FOLDED),
    "wire": Field("structural", note=_FOLDED),
    "cncable": Field("structural", note=_FOLDED),
    "tscable": Field("structural", note=_FOLDED),
    "x": Field("structural", note=_FOLDED),
    "h": Field("structural", note=_FOLDED),
    "reduce": Field("untranscribed", note="Kron reduction of the neutrals; a solver choice the consumer makes "
                                          "from the segment's phases"),
    "normamps": Field("untranscribed", note=_RATING),
    "emergamps": Field("untranscribed", note=_RATING),
    "Seasons": Field("untranscribed", note=_RATING),
    "Ratings": Field("untranscribed", note=_RATING),
    "LineType": Field("untranscribed", note="no home on a WireConfiguration"),
    "conductors": Field("structural", note=_NOT_MAPPED),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

#: ``(native class, mRID prefix, FIELDS)`` in ``Import`` order: spacings before the geometries that use them.
CATALOGS = (
    (schema.Linespacing, "spc_", LINESPACING_FIELDS),
    (schema.Linegeometry, "wc_", LINEGEOMETRY_FIELDS),
)

_SPACING_PREFIX, _GEOMETRY_PREFIX = "spc_", "wc_"
#: the deck's one EarthResistivity, which every WireConfiguration names (EXPORT_MAPPING.md S6g, G1)
EARTH_MRID = "earth"
#: DSS earthmodel (lowered) -> EarthModelKind; FullCarson has none and raises
EARTH_MODELS = {"carson": "carson", "deri": "deri"}
_FOLDED_SLOTS = ("cond", "wire", "cncable", "tscable", "x", "h")
_NAME_ARRAYS = ("wires", "cncables", "tscables")

_PROVENANCE = """OpenDSS {native} -> {targets} (catalog). No impedance is computed: geometry stays geometry.
Source table: {native} (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#linespacing-and-linegeometry"""


def _not_mapped(record, slots) -> None:
    unmapped = [slot for slot in slots if getattr(record, slot) not in (None, [])]
    if unmapped:
        raise ValueError(f"{type(record).__name__} {record.name}: {', '.join(unmapped)} not mapped yet "
                         "(no deck in the sweep sets them)")


def spacing_statements(spacing_mrid: str, name: str, xs: list[float] | None, hs: list[float] | None, units,
                       nphases: int | None, nconds: int | None, *, comment: str | None = None) -> list:
    """An ``XYSpacing`` template and its ``XYConductorPosition`` table: conductors 1..nphases are phases, the
    rest neutrals."""
    if nphases is None or nconds is None:
        raise ValueError(f"{name}: nphases and nconds must be set")
    if nphases < 1 or nphases > nconds:
        raise ValueError(f"{name}: nphases={nphases} must be between 1 and nconds={nconds}")
    if xs is None or hs is None or len(xs) != nconds or len(hs) != nconds:
        raise ValueError(f"{name}: {len(xs or [])} x and {len(hs or [])} h values for nconds={nconds}")
    if units is None:
        raise ValueError(f"{name}: the positions have no units")
    unit = lookup(LENGTH_UNIT, str(units).lower(), slot="units", record_id=name)
    rows = [Row([f"{spacing_mrid}_{k}", str(k), cell(float(x)), cell(float(h)), "phase" if k <= nphases else "neutral"])
            for k, (x, h) in enumerate(zip(xs, hs), start=1)]
    return [
        ObjectStatement("XYSpacing", [(Column("mRID"), spacing_mrid), (Column("name"), str(name)),
                                      (Column("isTemplate"), "true")], comment=comment),
        Table("XYConductorPosition", [Column("mRID"), Column("XYSpacing", default=spacing_mrid),
                                      Column("sequenceNumber"), Column("xCoord", unit), Column("yCoord", unit),
                                      Column("kind")], rows),
    ]


def map_linespacing(native) -> Document:
    """Every ``LineSpacing`` as an ``XYSpacing`` template in one ``linespacing`` document."""
    spacings = native.list_by_class(schema.Linespacing)
    statements = []
    for spacing in spacings:
        if spacing.detailed is not None and not spacing.detailed:
            raise ValueError(f"Linespacing {spacing.name}: detailed=No not mapped yet (no deck in the sweep sets it)")
        _not_mapped(spacing, ("EqDistPhPh", "EqDistPhN", "AvgPhaseHeight", "AvgNeutralHeight"))
        statements += spacing_statements(mrid(_SPACING_PREFIX, spacing.name, lowercase=True), spacing.name,
                                         spacing.x, spacing.h, spacing.units, spacing.nphases, spacing.nconds,
                                         comment=untranscribed_values(LINESPACING_FIELDS, spacing))
    return Document(name="linespacing", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(native="LineSpacing", targets="XYSpacing + XYConductorPosition",
                                               count=len(spacings)) if spacings else None)


def wire_infos(native) -> dict[str, list[str]]:
    """``{lowered name: [WireInfo mRID, ...]}`` over the three wire catalogs; more than one mRID is a name two
    catalogs share."""
    infos: dict[str, list[str]] = {}
    for native_class, prefix, _ in wire.CATALOGS:
        for record in native.list_by_class(native_class):
            infos.setdefault(str(record.name).lower(), []).append(mrid(prefix, record.name, lowercase=True))
    return infos


def conductor_infos(record, nconds: int, infos: dict[str, list[str]]) -> list[str]:
    """The ``WireInfo`` mRID of each conductor of a LineGeometry (or a Line with ``spacing=``), in cond order."""
    label = f"{type(record).__name__} {record.name}"
    arrays = [getattr(record, slot) for slot in _NAME_ARRAYS if getattr(record, slot)]
    if len(arrays) != 1:
        raise ValueError(f"{label}: sets {len(arrays)} of wires, cncables, tscables; the order between them is "
                         "not recorded, so give one")
    [names] = arrays
    if len(names) != nconds:
        raise ValueError(f"{label}: {len(names)} conductor names for nconds={nconds}")
    resolved = []
    for name in names:
        found = infos.get(str(name).lower(), [])
        if len(found) != 1:
            raise ValueError(f"{label}: conductor {name!r} is "
                             + ("in no wire catalog" if not found else f"in two catalogs ({', '.join(found)})"))
        resolved.append(found[0])
    return resolved


def wire_sequence_table(configuration: str, wire_info_mrids: list[str]) -> Table:
    """The ``WireSequenceConfiguration`` rows of one ``WireConfiguration``, sequenceNumber 1..n."""
    rows = [Row([f"{configuration}_{k}", str(k), info]) for k, info in enumerate(wire_info_mrids, start=1)]
    return Table("WireSequenceConfiguration", [Column("mRID"), Column("WireConfiguration", default=configuration),
                                               Column("sequenceNumber"), Column("WireInfo")], rows)


def _geometry_statements(geometry, infos: dict[str, list[str]], spacings: set[str]) -> list:
    _not_mapped(geometry, ("conductors",))
    if geometry.nphases is None or geometry.nconds is None:
        raise ValueError(f"LineGeometry {geometry.name}: nphases and nconds must be set")
    if geometry.nphases < 1 or geometry.nphases > geometry.nconds:
        raise ValueError(f"LineGeometry {geometry.name}: nphases={geometry.nphases} must be between 1 and "
                         f"nconds={geometry.nconds}")
    configuration = mrid(_GEOMETRY_PREFIX, geometry.name, lowercase=True)
    statements = []
    if geometry.spacing:
        if geometry.xs or geometry.hs or any(getattr(geometry, slot) not in (None, []) for slot in _FOLDED_SLOTS):
            raise ValueError(f"LineGeometry {geometry.name}: gives both spacing= and inline positions")
        if str(geometry.spacing).lower() not in spacings:
            raise ValueError(f"LineGeometry {geometry.name}: spacing={geometry.spacing!r} is no LineSpacing")
        spacing = mrid(_SPACING_PREFIX, geometry.spacing, lowercase=True)
    else:
        if not geometry.xs and any(getattr(geometry, slot) not in (None, []) for slot in _FOLDED_SLOTS):
            raise ValueError(f"LineGeometry {geometry.name}: a cond/wire/x/h value without cond= blocks")
        spacing = f"{configuration}_spc"
        statements += spacing_statements(spacing, geometry.name, geometry.xs, geometry.hs, geometry.units,
                                         geometry.nphases, geometry.nconds,
                                         comment=f"synthesized: the inline positions of LineGeometry {geometry.name}")
    statements += [
        ObjectStatement("WireConfiguration", [(Column("mRID"), configuration), (Column("name"), str(geometry.name)),
                                              (Column("numberOfPhases"), cell(geometry.nphases)),
                                              (Column("WireSpacing"), spacing),
                                              (Column("EarthResistivity"), EARTH_MRID)],
                        comment=untranscribed_values(LINEGEOMETRY_FIELDS, geometry)),
        wire_sequence_table(configuration, conductor_infos(geometry, geometry.nconds, infos)),
    ]
    return statements


def map_linegeometry(native) -> Document:
    """Every ``LineGeometry`` as a ``WireConfiguration`` in one ``linegeometry`` document, after the deck's
    ``EarthResistivity`` that they and the ``spacing=`` lines' configurations name (``earth_statement``)."""
    geometries = native.list_by_class(schema.Linegeometry)
    infos = wire_infos(native)
    spacings = {str(spacing.name).lower() for spacing in native.list_by_class(schema.Linespacing)}
    earth = earth_statement(native)
    statements = [*([earth] if earth is not None else []),
                  *(statement for geometry in geometries for statement in _geometry_statements(geometry, infos, spacings))]
    return Document(name="linegeometry", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(native="LineGeometry",
                                               targets="EarthResistivity, WireConfiguration + WireSequenceConfiguration",
                                               count=len(geometries)) if statements else None)


def uses_geometry(native) -> bool:
    """The deck gives a WireConfiguration: a LineGeometry, or a non-switch Line by ``spacing=``."""
    return bool(native.list_by_class(schema.Linegeometry)) or any(
        line.spacing and not line.Switch for line in native.list_by_class(schema.Line))


def _text(value) -> str:
    return str(getattr(value, "text", value))


def earth_statement(native) -> ObjectStatement | None:
    """The deck's ``EarthResistivity`` for its geometries: ``Set earthmodel`` and the geometry lines' ``rho``
    (ohm-m; they must agree), the engine's Deri and 100 when unset (DSS-6). A deck without geometry gets one only
    when it sets ``earthmodel``: a floating EarthResistivity no line names, kept so the export writes the setting
    back. Otherwise None: its earth model computes nothing."""
    options = native.list_by_class(schema.Options)  # none in a model of geometry alone: no Set earthmodel
    model = options[0].earthmodel if options else None
    geometry = uses_geometry(native)
    if not geometry and model is None:
        return None
    defaulted = []
    if model is None:
        model = dss_defaults(schema.Options)["earthmodel"]
        defaulted.append(f"earthmodel={_text(model)}")
    kind = EARTH_MODELS.get(_text(model).lower())
    if kind is None:
        raise ValueError(f"earthmodel={_text(model)}: EarthModelKind has {sorted(EARTH_MODELS)}")
    rhos = {float(line.rho) for line in native.list_by_class(schema.Line)
            if not line.Switch and (line.geometry or line.spacing) and line.rho is not None}
    if len(rhos) > 1:
        raise ValueError(f"geometry lines give rho {sorted(rhos)}; one EarthResistivity per deck is mapped")
    if rhos:
        rho = rhos.pop()
    else:
        rho = float(dss_defaults(schema.Line)["rho"])
        defaulted.append(f"rho={cell(rho)}")
    source = "the deck's earthmodel and its geometry lines' rho" if geometry else "the deck's earthmodel; no line names it"
    comment = f"{source} (ohm-m: the profile types rho Resistance)"
    if defaulted:
        comment += f"\ndefaulted: {', '.join(defaulted)}"
    return ObjectStatement("EarthResistivity", [(Column("mRID"), EARTH_MRID), (Column("name"), kind),
                                                (Column("earthModelType"), kind), (Column("rho", "ohm"), cell(rho))],
                           comment=comment)
