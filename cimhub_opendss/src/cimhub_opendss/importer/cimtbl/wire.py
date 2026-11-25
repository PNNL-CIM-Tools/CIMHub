"""OpenDSS ``WireData``, ``CNData``, ``TSData`` -> ``wiredata.cimtbl``, ``cndata.cimtbl``, ``tsdata.cimtbl``.

One ``OverheadWireInfo``, ``ConcentricNeutralCableInfo`` or ``TapeShieldCableInfo`` per DSS object, values as the
deck writes them. A rated wire's ``normamps``/``emergamps`` also become an ``OperationalLimitSet`` with a normal
and an emergency ``CurrentLimit``, on ``AssetInfo.OperationalLimitSet`` (GridAPPS-D extension). A conductor's three unit selectors (``Runits``, ``GMRunits``, ``radunits``) become header
units, so the mapper writes one table per unit combination, as the LineCode mapper writes one per length unit.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#wire-catalogs``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, copied_columns, lookup, mrid, untranscribed_values
from cimhub_opendss.importer.cimtbl.linecode import LENGTH_UNIT
from cimhub_opendss.schema import opendss_schema as schema

_OVERHEAD = "OverheadWireInfo"
_CN = "ConcentricNeutralCableInfo"
_TS = "TapeShieldCableInfo"

_LIMITS = ("{kind} CurrentLimit of the wire's OperationalLimitSet <mRID>_limits "
           "(AssetInfo.OperationalLimitSet)")
_UNITS = "the unit of {slots} in the header (LENGTH_UNIT); unset raises (every wire in the sweep sets it)"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"


def _conductor(info: str) -> dict[str, Field]:
    """The ``ConductorData`` slots every wire and cable class shares, mapped onto ``info``."""
    return {
        "name": Field("copied", ((info, "name", None),), "mRID = prefix + name, lowercased"),
        "Rdc": Field("copied", ((info, "rDC20", "ohm/{r_length}"),), "DC resistance (DSS gives no temperature)"),
        "Rac": Field("copied", ((info, "rAC25", "ohm/{r_length}"),),
                     "DSS: resistance at 60 Hz, temperature unstated; rAC25 as in EPRI's ExportCIMXML. Unset: "
                     "1.02 x Rdc, the engine's rule (ac_from_dc), with a defaulted comment"),
        "Runits": Field("mapped", note=_UNITS.format(slots="Rdc, Rac" + (", Rstrand" if info == _CN else ""))),
        "GMRac": Field("copied", ((info, "gmr", "{gmr_length}"),), "unset raises (the engine's 0.7788 x radius "
                                                                   "default; no deck in the sweep omits it)"),
        "GMRunits": Field("mapped", note=_UNITS.format(slots="GMRac" + (", GmrStrand" if info == _CN else ""))),
        "radius": Field("copied", ((info, "radius", "{radius_length}"),),
                        "one of radius and diam; both raise (DSS keeps the last, the reader does not record "
                        "which), neither raises"),
        "radunits": Field("mapped", note=_UNITS.format(slots="radius, diam and every cable dimension")),
        "diam": Field("derived", note="radius = diam / 2 (radius_from_diameter)"),
        "normamps": Field("copied", ((info, "ratedCurrent", "A"),), "also the " + _LIMITS.format(kind="normal")
                          + "; unset with emergamps set: emergamps / 1.5 (wire_ratings, the engine's rule), "
                            "defaulted"),
        "emergamps": Field("structural", note="the " + _LIMITS.format(kind="emergency") + "; unset: 1.5 x normamps "
                                              "(wire_ratings, the engine's rule), defaulted"),
        "Seasons": Field("structural", note=_NOT_MAPPED + " (an indexed rating array that names no calendar season; "
                                                          "home OperationalLimitType.season)"),
        "Ratings": Field("structural", note=_NOT_MAPPED + " (with Seasons)"),
        "Capradius": Field("structural", note=_NOT_MAPPED + " (the radius for capacitance; not WireInfo.coreRadius)"),
        "like": Field("untranscribed", note="the reader resolves like= before mapping"),
    }


def _cable(info: str) -> dict[str, Field]:
    """``CableData``: the insulation slots CNData and TSData add."""
    return {
        **_conductor(info),
        "EpsR": Field("untranscribed", note="insulation relative permittivity; no home on CableInfo "
                                            "(InsulationInfo has a material, not a permittivity). DSS default 2.3, "
                                            "which every cable in the sweep uses"),
        "InsLayer": Field("copied", ((info, "insulationThickness", "{radius_length}"),)),
        "DiaIns": Field("copied", ((info, "diameterOverInsulation", "{radius_length}"),)),
        "DiaCable": Field("copied", ((info, "diameterOverJacket", "{radius_length}"),)
                          + (((info, "diameterOverNeutral", "{radius_length}"),) if info == _CN else ()),
                          "the outer diameter" + ("; a CN cable has no jacket over its strands, so it is also "
                                                  "the diameter over the neutral (ExportCIMXML)" if info == _CN
                                                  else "")),
    }


WIREDATA_FIELDS = _conductor(_OVERHEAD)

CNDATA_FIELDS = {
    **_cable(_CN),
    "k": Field("copied", ((_CN, "neutralStrandCount", None),)),
    "DiaStrand": Field("derived", note="neutralStrandRadius = DiaStrand / 2 (radius_from_diameter), radunits"),
    "GmrStrand": Field("copied", ((_CN, "neutralStrandGmr", "{gmr_length}"),), "in GMRunits, as DSS says"),
    "Rstrand": Field("copied", ((_CN, "neutralStrandRDC20", "ohm/{r_length}"),),
                     "DSS calls it the strand's AC resistance; neutralStrandRDC20 as in ExportCIMXML, CIM's only "
                     "strand resistance"),
    "SemiconLayer": Field("structural", note=_NOT_MAPPED),
}

TSDATA_FIELDS = {
    **_cable(_TS),
    "DiaShield": Field("derived", note="diameterOverScreen = DiaShield - 2 TapeLayer (screen_diameter): DSS "
                                       "measures over the tape, CIM's screen diameter is the shield's inside "
                                       "(ExportCIMXML)"),
    "TapeLayer": Field("copied", ((_TS, "tapeThickness", "{radius_length}"),)),
    "TapeLap": Field("copied", ((_TS, "tapeLap", "percent"),)),
}

#: ``(native class, mRID prefix, FIELDS)`` per wire catalog, in ``Import`` order.
CATALOGS = (
    (schema.Wiredata, "wire_", WIREDATA_FIELDS),
    (schema.Cndata, "cn_", CNDATA_FIELDS),
    (schema.Tsdata, "ts_", TSDATA_FIELDS),
)


#: The derived column each cable class adds after its copied ones: ``(column, slot it comes from)``.
_DERIVED_COLUMN = {_CN: ("neutralStrandRadius", "DiaStrand"), _TS: ("diameterOverScreen", "DiaShield")}
_INFO_CLASS = {schema.Wiredata: _OVERHEAD, schema.Cndata: _CN, schema.Tsdata: _TS}
_DERIVED_NOTE = {
    _OVERHEAD: "radius = diam / 2 (radius_from_diameter) where the deck gives diam",
    _CN: "radius = diam / 2 and neutralStrandRadius = DiaStrand / 2 (radius_from_diameter)",
    _TS: "radius = diam / 2 (radius_from_diameter); diameterOverScreen = DiaShield - 2 TapeLayer "
         "(screen_diameter)",
}

_PROVENANCE = """OpenDSS {native} -> {info} (catalog).
Source table: {native} (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#wire-catalogs"""


#: The engine's emergency rating over the normal one of a wire that gives only one of them (``ConductorData``).
EMERGENCY_FACTOR = 1.5


def wire_ratings(wire) -> dict[str, tuple[float, str | None]]:
    """``{"normamps": (amps, note), "emergamps": (amps, note)}`` of a rated wire, ``{}`` of an unrated one. As the
    engine rates the wire, an unset emergamps is 1.5 x normamps and an unset normamps is emergamps / 1.5
    (engine-checked); ``note`` then says so."""
    if wire.normamps is None and wire.emergamps is None:
        return {}
    if wire.normamps is None:
        return {"normamps": (float(wire.emergamps) / EMERGENCY_FACTOR, "defaulted: normamps = emergamps / 1.5"),
                "emergamps": (float(wire.emergamps), None)}
    if wire.emergamps is None:
        return {"normamps": (float(wire.normamps), None),
                "emergamps": (EMERGENCY_FACTOR * float(wire.normamps), "defaulted: emergamps = 1.5 x normamps")}
    return {"normamps": (float(wire.normamps), None), "emergamps": (float(wire.emergamps), None)}


def ac_from_dc(rdc: float) -> float:
    """The engine's AC resistance when a wire gives only ``Rdc``: Rac = 1.02 x Rdc (``ConductorData.pas``)."""
    return 1.02 * rdc


def radius_from_diameter(diameter: float) -> float:
    return diameter / 2


def screen_diameter(dia_shield: float, tape_layer: float) -> float:
    """CIM's screen diameter (the shield's inside) from DSS's diameter over the tape shield."""
    return dia_shield - 2 * tape_layer


def _unit(wire, slot: str) -> str:
    value = getattr(wire, slot)
    if value is None:
        raise ValueError(f"{type(wire).__name__} {wire.name}: {slot} unset; the values have no unit")
    return lookup(LENGTH_UNIT, str(value).lower(), slot=slot, record_id=wire.name)


def _check(wire, fields: dict[str, Field]) -> None:
    unmapped = [slot for slot, field in fields.items()
                if field.note.startswith(_NOT_MAPPED) and getattr(wire, slot) not in (None, [])]
    if unmapped:
        raise ValueError(f"{type(wire).__name__} {wire.name}: {', '.join(unmapped)} not mapped yet "
                         "(no deck in the sweep sets them)")
    if (wire.radius is None) == (wire.diam is None):
        raise ValueError(f"{type(wire).__name__} {wire.name}: give one of radius and diam (DSS keeps the last "
                         "set, which the reader does not record)")
    if wire.GMRac is None:
        raise ValueError(f"{type(wire).__name__} {wire.name}: GMRac unset (the engine would take 0.7788 x radius)")
    if wire.Rac is None and wire.Rdc is None:
        raise ValueError(f"{type(wire).__name__} {wire.name}: sets neither Rac nor Rdc")


def _wire_row(wire, prefix: str, fields: dict[str, Field]) -> tuple[tuple[Column, ...], Row]:
    """The columns (their units are the wire's) and the row of one wire or cable."""
    _check(wire, fields)
    info = _INFO_CLASS[type(wire)]
    radius_unit = _unit(wire, "radunits")
    pairs = copied_columns(fields, info, r_length=_unit(wire, "Runits"), gmr_length=_unit(wire, "GMRunits"),
                           radius_length=radius_unit)
    values = {slot: getattr(wire, slot) for slot, _ in pairs}
    notes = []
    if wire.Rac is None:
        values["Rac"] = ac_from_dc(wire.Rdc)
        notes.append("defaulted: Rac = 1.02 x Rdc")
    if wire.radius is None:
        values["radius"] = radius_from_diameter(wire.diam)
    ratings = wire_ratings(wire)
    if ratings and wire.normamps is None:
        values["normamps"], note = ratings["normamps"]
        notes.append(note)
    columns = [column for _, column in pairs]
    texts = [cell(values[slot]) for slot, _ in pairs]
    columns.append(Column("OperationalLimitSet"))
    texts.append(f"{mrid(prefix, wire.name, lowercase=True)}_limits" if ratings else None)
    if info in _DERIVED_COLUMN:
        column, source = _DERIVED_COLUMN[info]
        columns.append(Column(column, radius_unit))
        texts.append(cell(_derived_cable_value(wire, source)))
    untranscribed = untranscribed_values(fields, wire)
    if untranscribed:
        notes.append(untranscribed)
    row = Row([mrid(prefix, wire.name, lowercase=True), *texts], comment="\n".join(notes) or None)
    return tuple(columns), row


def _derived_cable_value(cable, source: str):
    if getattr(cable, source) is None:
        return None
    if source == "DiaStrand":
        return radius_from_diameter(cable.DiaStrand)
    if cable.TapeLayer is None:
        raise ValueError(f"TSData {cable.name}: DiaShield without TapeLayer gives no screen diameter")
    return screen_diameter(cable.DiaShield, cable.TapeLayer)


def map_wires(native, native_class: type, prefix: str, fields: dict[str, Field]) -> Document:
    """Every object of one wire catalog class as one document (``wiredata``, ``cndata``, ``tsdata``), one
    table per unit combination."""
    name = native_class.__name__.lower()
    wires = native.list_by_class(native_class)
    if not wires:
        return Document(name=name, statements=[], profile=CIM_PROFILE)
    info = _INFO_CLASS[native_class]
    by_columns: dict[tuple[Column, ...], list[Row]] = {}
    limit_sets, limits = [], []
    for wire in wires:
        columns, row = _wire_row(wire, prefix, fields)
        by_columns.setdefault(columns, []).append(row)
        ratings = wire_ratings(wire)
        if ratings:
            limit_set = f"{mrid(prefix, wire.name, lowercase=True)}_limits"
            limit_sets.append(Row([limit_set]))
            for slot, (suffix, limit_type) in (("normamps", ("norm", "olt_normal")),
                                               ("emergamps", ("emerg", "olt_emergency"))):
                amps, note = ratings[slot]
                limits.append(Row([f"{limit_set[:-len('_limits')]}_{suffix}", cell(amps), limit_type, limit_set],
                                  comment=note))
    statements = []
    if limit_sets:  # before the wires, which name them (AssetInfo.OperationalLimitSet)
        statements += [Table("OperationalLimitSet", [Column("mRID")], limit_sets),
                       Table("CurrentLimit", [Column("mRID"), Column("normalValue", "A"), Column("OperationalLimitType"),
                                              Column("OperationalLimitSet")], limits)]
    statements += [Table(info, [Column("mRID"), *columns], rows, comment=f"derived: {_DERIVED_NOTE[info]}")
                   for columns, rows in by_columns.items()]
    return Document(name=name, statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(native=native_class.__name__, info=info, count=len(wires)))
