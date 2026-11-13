"""WireInfo -> OpenDSS ``WireData`` / ``CNData`` / ``TSData`` (``EXPORT_MAPPING.md#wire-catalogs``).

Every WireInfo in the network is written, used or not (E3), in metres (B1): ``Runits=m GMRunits=m radunits=m``.
The three catalogs share one name namespace, because a LineGeometry names its conductors without their catalog.
DSS has no unshielded cable, so a plain CableInfo is a WireData, its insulation unmodelled (B7).
"""

from __future__ import annotations

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.getters import describe
from cimhub_core.getters.wire import WIRE_KINDS, get_wire_info
from cimhub_opendss.exporter.naming import Names
from cimhub_opendss.exporter.slots import Slot
from cimhub_opendss.schema import opendss_schema as schema

CIM_CLASSES = WIRE_KINDS
NATIVE = {
    cim.OverheadWireInfo: schema.Wiredata,
    cim.CableInfo: schema.Wiredata,  # B7
    cim.ConcentricNeutralCableInfo: schema.Cndata,
    cim.TapeShieldCableInfo: schema.Tsdata,
}
WIRE_NAMESPACE = "wire"
UNIT = "m"  # B1

_NOT_IN_CIM = "not in CIM (untranscribed or raising on import)"
_COMMON = {
    "name": Slot("written", "Names, one namespace for the three catalogs"),
    "Rdc": Slot("written", "get_wire_info.r_dc20 (ohm/m); Rdc and Rac both unset raises"),
    "Rac": Slot("rule", "get_wire_info.r_ac25 (ohm/m); unset -> not written, the engine's 1.02 x Rdc"),
    "Runits": Slot("written", "m (B1)"),
    "GMRac": Slot("rule", "get_wire_info.gmr (m); unset -> not written, the engine's 0.7788 x radius"),
    "GMRunits": Slot("written", "m (B1)"),
    "radius": Slot("written", "get_wire_info.radius (m); unset raises"),
    "radunits": Slot("written", "m (B1)"),
    "normamps": Slot("written", "the wire's normal limit, else ratedCurrent (A)"),
    "emergamps": Slot("rule", "the wire's emergency limit (A); unset -> not written, the engine's 1.5 x normamps"),
    "diam": Slot("not mapped", "radius is written instead"),
    "Seasons": Slot("unset", _NOT_IN_CIM),
    "Ratings": Slot("unset", _NOT_IN_CIM),
    "Capradius": Slot("unset", _NOT_IN_CIM),
    "like": Slot("not mapped", "the writer never writes like="),
}
_CABLE = {
    "EpsR": Slot("unset", "no permittivity on CableInfo; the engine's 2.3"),
    "InsLayer": Slot("written", "cable.insulation_thickness (m)"),
    "DiaIns": Slot("written", "cable.diameter_over_insulation (m)"),
}
SLOTS = {
    schema.Wiredata: _COMMON,
    schema.Cndata: {
        **_COMMON, **_CABLE,
        "k": Slot("written", "cable.neutral_strand_count"),
        "DiaStrand": Slot("written", "2 x cable.neutral_strand_radius (m)"),
        "GmrStrand": Slot("written", "cable.neutral_strand_gmr (m)"),
        "Rstrand": Slot("written", "cable.neutral_strand_r_dc20 (ohm/m), CIM's only strand resistance"),
        "SemiconLayer": Slot("unset", _NOT_IN_CIM),
        "DiaCable": Slot("written", "cable.diameter_over_neutral (m), the circle of the strands; unset raises"),
    },
    schema.Tsdata: {
        **_COMMON, **_CABLE,
        "DiaShield": Slot("written", "cable.diameter_over_screen + 2 x tape_thickness (m): DSS measures over the tape"),
        "TapeLayer": Slot("written", "cable.tape_thickness (m)"),
        "TapeLap": Slot("written", "cable.tape_lap (percent)"),
        "DiaCable": Slot("written", "cable.diameter_over_jacket (m)"),
    },
}


def wire_name(wire: cim.WireInfo, names: Names) -> str:
    """The wire's DSS name, as its catalog record and every LineGeometry write it."""
    return names.name(wire, WIRE_NAMESPACE)


def export(context) -> list:
    """One catalog record per WireInfo."""
    return [_record(wire, context.names) for wire in context.objects(*CIM_CLASSES)]


def _record(wire: cim.WireInfo, names: Names):
    values = get_wire_info(wire, UNIT, f"ohm/{UNIT}")
    if values.r_dc20 is None and values.r_ac25 is None:
        raise ValueError(f"{describe(wire)}: rDC20 and rAC25 are unset; DSS needs a resistance")
    if values.radius is None:
        raise ValueError(f"{describe(wire)}: radius is unset")
    native = NATIVE[values.kind]
    slots = dict(
        name=wire_name(wire, names),
        Rdc=values.r_dc20, Rac=values.r_ac25, Runits=UNIT,
        GMRac=values.gmr, GMRunits=UNIT,
        radius=values.radius, radunits=UNIT,
        normamps=values.limits.normal if values.limits.normal is not None else values.rated_current,
        emergamps=values.limits.emergency,
    )
    cable = values.cable
    if native is not schema.Wiredata:
        slots.update(InsLayer=cable.insulation_thickness, DiaIns=cable.diameter_over_insulation)
    if native is schema.Cndata:
        if cable.diameter_over_neutral is None:
            raise ValueError(f"{describe(wire)}: diameterOverNeutral is unset; DSS DiaCable is the strands' circle")
        slots.update(
            k=cable.neutral_strand_count,
            DiaStrand=None if cable.neutral_strand_radius is None else 2 * cable.neutral_strand_radius,
            GmrStrand=cable.neutral_strand_gmr,
            Rstrand=cable.neutral_strand_r_dc20,
            DiaCable=cable.diameter_over_neutral,
        )
    if native is schema.Tsdata:
        if cable.diameter_over_screen is None or cable.tape_thickness is None:
            raise ValueError(f"{describe(wire)}: diameterOverScreen and tapeThickness are needed for DiaShield")
        slots.update(
            DiaShield=cable.diameter_over_screen + 2 * cable.tape_thickness,
            TapeLayer=cable.tape_thickness,
            TapeLap=cable.tape_lap,
            DiaCable=cable.diameter_over_jacket,
        )
    return native(**slots)
