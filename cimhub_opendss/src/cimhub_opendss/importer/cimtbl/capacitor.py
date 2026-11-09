"""OpenDSS ``Capacitor`` -> ``capacitor.cimtbl``: one ``LinearShuntCompensator`` per capacitor.

One section: ``nomQ`` is the deck's kvar and ``nomU`` its kV, as rated; ``bPerSection`` = nomQ / nomU^2. A
CapControl adds its ``RegulatingControl``, ``aVRDelay`` and ``controlEnabled`` to the row later, by an ``Update``
in ``capcontrol.cimtbl``.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#capacitor``.
"""

from __future__ import annotations

from collections.abc import Mapping

from cimprofiles.cim18.cim18v17 import cim18v17 as cim
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, phases_cell, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl.injection import device_terminal, is_delta
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Capacitor
PREFIX = "cap_"

_SHUNT = "LinearShuntCompensator"
_NOT_MAPPED = "raises when set: no deck in the sweep sets it, so a mapping waits for one"
_RELIABILITY = "a reliability setting; no home in the network profile parts"

FIELDS = {
    "name": Field("copied", ((_SHUNT, "name", None),), "mRID = cap_ + name, lowercased"),
    "bus1": Field("structural", note="node and phases, as a load's (1/2/3 are A/B/C)"),
    "bus2": Field("structural", note=_NOT_MAPPED + " (an ungrounded wye or a series capacitor)"),
    "phases": Field("structural", note="the conductor count; default 3"),
    "kvar": Field("copied", ((_SHUNT, "nomQ", "kVAr"),), "the total over the phases; more than one step raises; "
                                                    "default 1200"),
    "kv": Field("copied", ((_SHUNT, "nomU", "kV"),),
                "as rated (LN for 1-phase wye, else LL); also bPerSection (S) = nomQ / nomU^2 "
                "(b_per_section); default 12.47"),
    "conn": Field("mapped", ((_SHUNT, "phaseConnection", None), (_SHUNT, "grounded", None)),
                  "wye -> Y, grounded; delta -> D, not grounded; default wye"),
    "cmatrix": Field("structural", note=_NOT_MAPPED + " (a capacitance matrix instead of kvar)"),
    "cuf": Field("structural", note=_NOT_MAPPED + " (microfarads instead of kvar)"),
    "R": Field("structural", note="0 is untranscribed; nonzero raises (a series R is not mapped)"),
    "XL": Field("structural", note="0 is untranscribed; nonzero raises (a series reactor is not mapped)"),
    "Harm": Field("untranscribed", note="the tuning harmonic of the R/XL filter"),
    "Numsteps": Field("structural", note="maximumSections; more than 1 raises (unequal steps would need a "
                                         "NonlinearShuntCompensator); default 1"),
    "states": Field("structural", note="sections = normalSections = the steps closed (a switch's normalOpen = "
                                       "open rule); default all closed"),
    "normamps": Field("structural", note=_NOT_MAPPED + " (an OperationalLimitSet, as a line's)"),
    "emergamps": Field("structural", note=_NOT_MAPPED),
    "faultrate": Field("untranscribed", note=_RELIABILITY),
    "pctperm": Field("untranscribed", note=_RELIABILITY),
    "repair": Field("untranscribed", note=_RELIABILITY),
    "basefreq": Field("untranscribed", note="no home on a compensator; bPerSection is at the model's frequency"),
    "enabled": Field("copied", ((_SHUNT, "normallyInService", None),), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = tuple(slot for slot, field in FIELDS.items() if field.note.startswith(_NOT_MAPPED))
_SERIES = ("R", "XL")

_PROVENANCE = """OpenDSS Capacitor -> LinearShuntCompensator on its bus: one section, nomQ and nomU as rated,
bPerSection = nomQ / nomU^2. A CapControl adds the control by an Update in capcontrol.cimtbl.
Source table: Capacitor (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#capacitor"""


def b_per_section(kvar: float, kv: float) -> float:
    """Susceptance (S) of one section rated ``kvar`` at ``kv``: nomQ / nomU^2 (total kvar on the LL kV of a
    3-phase bank, a unit's kvar on its own kV otherwise)."""
    return float(cim.ReactivePower(kvar, "kVAr")) / float(cim.Voltage(kv, "kV")) ** 2


def _check(capacitor) -> None:
    unmapped = [slot for slot in _UNMAPPED if getattr(capacitor, slot) not in (None, [])]
    series = [slot for slot in _SERIES if any(float(value) != 0 for value in getattr(capacitor, slot) or [])]
    if unmapped or series:
        raise ValueError(f"Capacitor {capacitor.name}: {', '.join(unmapped + series)} not mapped yet (no deck "
                         "in the sweep sets them)")
    steps = len(capacitor.kvar or [None])
    if (capacitor.Numsteps or 1) > 1 or steps > 1:
        raise ValueError(f"Capacitor {capacitor.name}: {max(steps, capacitor.Numsteps or 1)} steps; only one "
                         "section is mapped")


def map_capacitor(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Capacitor`` of a DSS model as one ``capacitor`` document; ``container`` is the Feeder mRID."""
    capacitors = native.list_by_class(NATIVE_CLASS)
    defaults = dss_defaults(NATIVE_CLASS)
    rows = []
    for original in capacitors:
        _check(original)
        capacitor, defaulted = fill_defaults(FIELDS, original, defaults)
        terminal = device_terminal(f"Capacitor {capacitor.name}", capacitor.bus1, int(capacitor.phases),
                                   is_delta(capacitor.conn), buses)
        kvar, kv = float(capacitor.kvar[0]), float(capacitor.kv)
        closed = sum(int(state) for state in capacitor.states) if capacitor.states else 1
        rows.append(Row([
            mrid(PREFIX, capacitor.name, lowercase=True), str(capacitor.name), terminal.bus, phases_cell(terminal.phases),
            terminal.connection, cell(terminal.grounded), cell(kvar), cell(kv), cell(b_per_section(kvar, kv)),
            "1", cell(closed), cell(closed), cell(capacitor.enabled), terminal.system.base_voltage,
        ], comment="\n".join(part for part in (defaulted, untranscribed_values(FIELDS, capacitor)) if part)
            or None))
    if not rows:
        return Document(name="capacitor", statements=[], profile=CIM_PROFILE)
    columns = [Column("mRID"), Column("name"), Column("node"), Column("phases"), Column("phaseConnection"),
               Column("grounded"), Column("nomQ", "kVAr"), Column("nomU", "kV"), Column("bPerSection", "S"),
               Column("maximumSections"), Column("normalSections"), Column("sections"), Column("normallyInService"),
               Column("BaseVoltage"), Column("EquipmentContainer", default=container)]
    table = Table(_SHUNT, columns, rows, comment="derived: bPerSection = nomQ / nomU^2 (b_per_section); "
                                                 "sections = normalSections = the steps states closes")
    return Document(name="capacitor", statements=[table], profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(capacitors)))
