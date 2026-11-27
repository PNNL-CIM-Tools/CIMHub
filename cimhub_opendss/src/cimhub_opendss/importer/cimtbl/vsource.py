"""OpenDSS ``Vsource`` (``New Circuit`` included) -> ``vsource.cimtbl``: one ``EnergySource`` per source.

DSS gives a source's Thevenin impedance one of three ways (ohms, short-circuit MVA, short-circuit current) and
keeps the one set last. The reader does not record the order, so a source that sets two raises. MVA and current
are converted as ``VSource.pas`` ``RecalcElementData`` does; the engine is the test oracle. The units go with the
values: kV and MVA give ohm, and a current's kV x A gives kVA and so kohm, the header's unit.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#vsource``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import NamedTuple

from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, phases_cell, untranscribed_names
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl.transformer import parse_bus
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Vsource
PREFIX = "src_"

_SOURCE = "EnergySource"
_SQRT3 = math.sqrt(3)
_HARMONICS = "harmonic solution setting; no home in the network profile parts"
_SHAPE = "time series; no home in the network profile parts"
_NOT_MAPPED = "raises when set: no deck in the sweep uses it, so a mapping waits for one"

FIELDS = {
    "name": Field("copied", ((_SOURCE, "name", None),), "mRID = src_ + name, lowercased"),
    "bus1": Field("structural", note="node, and phases from its conductors; default sourcebus"),
    "basekv": Field("copied", ((_SOURCE, "nominalVoltage", "kV"),)),
    "pu": Field("derived", note="voltageMagnitude (kV) = basekv x pu"),
    "angle": Field("copied", ((_SOURCE, "voltageAngle", "deg"),)),
    "frequency": Field("untranscribed", note="the master's BaseFrequency is the deck's"),
    "phases": Field("structural", note="3 = ABC, 1 = the phase of bus1's conductor"),
    "MVAsc3": Field("derived", note="r, x (thevenin_from_short_circuit)"),
    "MVAsc1": Field("derived", note="r0, x0 (thevenin_from_short_circuit)"),
    "x1r1": Field("derived", note="r, x (thevenin_from_short_circuit)"),
    "x0r0": Field("derived", note="r0, x0 (thevenin_from_short_circuit)"),
    "Isc3": Field("derived", note="the 3-phase short-circuit kVA (kvasc_from_isc), then as MVAsc3; r, x in kohm"),
    "Isc1": Field("derived", note="the 1-phase short-circuit kVA (kvasc_from_isc), then as MVAsc1; r0, x0 in kohm"),
    "R1": Field("copied", ((_SOURCE, "r", "ohm"),)),
    "X1": Field("copied", ((_SOURCE, "x", "ohm"),)),
    "R0": Field("copied", ((_SOURCE, "r0", "ohm"),)),
    "X0": Field("copied", ((_SOURCE, "x0", "ohm"),)),
    "ScanType": Field("untranscribed", note=_HARMONICS),
    "Sequence": Field("untranscribed", note=_HARMONICS),
    "bus2": Field("structural", note="raises when set: an ungrounded (series) source has no source-shape home"),
    "Z1": Field("structural", note=_NOT_MAPPED),
    "Z0": Field("structural", note=_NOT_MAPPED),
    "Z2": Field("structural", note=_NOT_MAPPED),
    "puZ1": Field("structural", note=_NOT_MAPPED),
    "puZ0": Field("structural", note=_NOT_MAPPED),
    "puZ2": Field("structural", note=_NOT_MAPPED),
    "baseMVA": Field("structural", note=_NOT_MAPPED + " (the base of puZ1/puZ0/puZ2)"),
    "Yearly": Field("untranscribed", note=_SHAPE),
    "Daily": Field("untranscribed", note=_SHAPE),
    "Duty": Field("untranscribed", note=_SHAPE),
    "Model": Field("untranscribed", note="Thevenin or ideal source model; no home on EnergySource"),
    "puZideal": Field("untranscribed", note="the ideal model's impedance; no home on EnergySource"),
    "spectrum": Field("untranscribed", note=_HARMONICS),
    "basefreq": Field("untranscribed", note="the master's BaseFrequency is the deck's"),
    "enabled": Field("copied", ((_SOURCE, "normallyInService", None),)),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

#: The three ways to give the impedance; DSS keeps whichever was set last.
IMPEDANCE_GROUPS = {
    "ohms": ("R1", "X1", "R0", "X0"),
    "MVAsc": ("MVAsc3", "MVAsc1"),
    "Isc": ("Isc3", "Isc1"),
}
_UNMAPPED = ("bus2", "Z1", "Z0", "Z2", "puZ1", "puZ0", "puZ2", "baseMVA")
_ALWAYS_DEFAULTED = ("bus1", "basekv", "pu", "angle", "phases")
#: The defaults each group takes: MVAsc takes its own and the X/R ratios, Isc only the ratios.
_GROUP_DEFAULTED = {"ohms": (), "MVAsc": ("MVAsc3", "MVAsc1", "x1r1", "x0r0"), "Isc": ("x1r1", "x0r0")}
_NODE_PHASE = {1: "A", 2: "B", 3: "C"}

_PROVENANCE = """OpenDSS Vsource -> EnergySource on its bus.
Source table: Vsource (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#vsource"""


class Thevenin(NamedTuple):
    """Sequence impedances, in the unit ``thevenin`` returns with them."""
    r1: float
    x1: float
    r0: float
    x0: float


def thevenin_from_short_circuit(kv: float, mvasc3: float, mvasc1: float, x1r1: float, x0r0: float) -> Thevenin:
    """The Thevenin impedance of a source given by short-circuit power (``VSource.pas`` ``RecalcElementData``):
    kV and MVA give ohm, kV and kVA give kohm.

    X1 = kV² / MVAsc3 / √(1 + 1/x1r1²), R1 = X1 / x1r1. R0 is the positive root of
    (1 + x0r0²) R0² + 4 (R1 + X1 x0r0) R0 + 4 (R1² + X1²) − (3 kV² / MVAsc1)² = 0, and X0 = R0 x0r0:
    the 1-phase fault current through 2 Z1 + Z0.

    Raises on what gives no passive source: kV, MVAsc3 or MVAsc1 not above 0, x1r1 not above 0, x0r0 below 0, or a
    negative R0 (the engine refuses some and computes a negative, infinite or zero impedance for the rest).
    """
    for what, value in (("kV", kv), ("MVAsc3", mvasc3), ("MVAsc1", mvasc1), ("x1r1", x1r1)):
        if value <= 0:
            raise ValueError(f"{what}={value:g}; a short-circuit source needs it above 0")
    if x0r0 < 0:
        raise ValueError(f"x0r0={x0r0:g}; a short-circuit source needs it 0 or above")
    x1 = kv ** 2 / mvasc3 / math.sqrt(1 + 1 / x1r1 ** 2)
    r1 = x1 / x1r1
    a = 1 + x0r0 ** 2
    b = 4 * (r1 + x1 * x0r0)
    c = 4 * (r1 ** 2 + x1 ** 2) - (3 * kv ** 2 / mvasc1) ** 2
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        raise ValueError(f"MVAsc1={mvasc1} at {kv} kV gives no real R0 for MVAsc3={mvasc3}, x0r0={x0r0}")
    r0 = (-b + math.sqrt(discriminant)) / (2 * a)
    if r0 < 0:
        raise ValueError(f"MVAsc1={mvasc1:g} at {kv:g} kV gives R0={r0:g} for MVAsc3={mvasc3:g}, x0r0={x0r0:g}; "
                         "the engine keeps a negative R0, which is no passive source")
    return Thevenin(r1, x1, r0, r0 * x0r0)


def kvasc_from_isc(kv: float, isc3: float, isc1: float, phases: int) -> tuple[float, float]:
    """The 3- and 1-phase short-circuit power from currents: kV and A give kVA. The 1-phase factor is 1 on a
    1-phase source."""
    factor = _SQRT3 if phases == 3 else 1.0
    return _SQRT3 * kv * isc3, factor * kv * isc1


def impedance_group(source) -> str:
    """The impedance group the source sets (``MVAsc`` when it sets none); two groups raise."""
    unmapped = [slot for slot in _UNMAPPED if getattr(source, slot) not in (None, [])]
    if unmapped:
        raise ValueError(f"Vsource {source.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep "
                         "sets them)")
    groups = [group for group, slots in IMPEDANCE_GROUPS.items()
              if any(getattr(source, slot) is not None for slot in slots)]
    if len(groups) > 1:
        raise ValueError(f"Vsource {source.name}: sets the {' and '.join(groups)} impedance groups; DSS keeps "
                         "whichever was set last, which the reader does not record")
    for group in ("ohms", "Isc"):
        if groups == [group] and any(getattr(source, slot) is None for slot in IMPEDANCE_GROUPS[group]):
            raise ValueError(f"Vsource {source.name}: sets only part of {', '.join(IMPEDANCE_GROUPS[group])}")
    return groups[0] if groups else "MVAsc"


def with_defaults(source):
    """``(source, group, comment)``: the source with its DSS defaults filled (only its group's impedance
    defaults), its impedance group, and the ``defaulted:`` comment or ``None``."""
    group = impedance_group(source)
    defaults = dss_defaults(NATIVE_CLASS)
    slots = _ALWAYS_DEFAULTED + _GROUP_DEFAULTED[group]
    filled, comment = fill_defaults(FIELDS, source, {slot: defaults[slot] for slot in slots})
    return filled, group, comment


def thevenin(source, group: str) -> tuple[Thevenin, str]:
    """``(impedance, unit)`` of a source with its defaults filled: ohm as given or from MVAsc, kohm from Isc."""
    if group == "ohms":
        return Thevenin(source.R1, source.X1, source.R0, source.X0), "ohm"
    if group == "Isc":
        kvasc3, kvasc1 = kvasc_from_isc(source.basekv, source.Isc3, source.Isc1, source.phases)
        return thevenin_from_short_circuit(source.basekv, kvasc3, kvasc1, source.x1r1, source.x0r0), "kohm"
    return thevenin_from_short_circuit(source.basekv, source.MVAsc3, source.MVAsc1, source.x1r1, source.x0r0), "ohm"


def _phases(source) -> tuple[str, str]:
    """``(bus, phases)`` of the source's terminal."""
    bus, nodes = parse_bus(source.bus1)
    phase_nodes = tuple(node for node in nodes if node != 0)
    if source.phases == 3 and phase_nodes in ((), (1, 2, 3)):
        return bus, "ABC"
    if source.phases == 1 and len(phase_nodes) <= 1:
        return bus, _NODE_PHASE[phase_nodes[0] if phase_nodes else 1]
    raise ValueError(f"Vsource {source.name}: phases={source.phases} on {source.bus1}; only a 3-phase source "
                     "on nodes 1.2.3 or a 1-phase source on one of 1, 2, 3 is mapped")


def _comment(group: str, original, defaulted: str | None) -> str | None:
    """The row comment: the impedance inputs the deck gives (``original``, before defaults), then the defaults."""
    given = [f"{slot}={getattr(original, slot)}" for slot in IMPEDANCE_GROUPS[group]
             if group != "ohms" and getattr(original, slot) is not None]
    parts = [f"derived from {', '.join(given)}"] if given else []
    if defaulted:
        parts.append(defaulted)
    return "; ".join(parts) or None


def map_vsource(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Vsource`` of a DSS model as one ``vsource`` document.

    ``buses`` is the topology walk's result; ``container`` is the EquipmentContainer mRID (the Substation).
    """
    sources = native.list_by_class(NATIVE_CLASS)
    rows_by_unit: dict[str, list[Row]] = {}
    for original in sources:
        source, group, defaulted = with_defaults(original)
        bus, phases = _phases(source)
        if bus not in buses:
            raise ValueError(f"Vsource {source.name}: no bus voltage for {bus}")
        z, unit = thevenin(source, group)
        rows_by_unit.setdefault(unit, []).append(Row([
            mrid(PREFIX, source.name, lowercase=True), str(source.name), bus, phases_cell(phases), cell(source.basekv),
            cell(source.basekv * source.pu), cell(source.angle), cell(z.r1), cell(z.x1), cell(z.r0), cell(z.x0),
            cell(source.enabled), buses[bus].base_voltage,
        ], comment=_comment(group, original, defaulted)))
    if not rows_by_unit:
        return Document(name="vsource", statements=[], profile=CIM_PROFILE)
    tables = []
    for unit, rows in rows_by_unit.items():
        columns = [Column("mRID"), Column("name"), Column("node"), Column("phases"), Column("nominalVoltage", "kV"),
                   Column("voltageMagnitude", "kV"), Column("voltageAngle", "deg"), Column("r", unit),
                   Column("x", unit), Column("r0", unit), Column("x0", unit), Column("normallyInService"),
                   Column("BaseVoltage"), Column("EquipmentContainer", default=container)]
        tables.append(Table(_SOURCE, columns, rows, comment=untranscribed_names(FIELDS)))
    return Document(name="vsource", statements=tables, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(sources)))
