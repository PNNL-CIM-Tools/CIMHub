"""OpenDSS series ``Reactor`` -> ``reactor.cimtbl``: one ``SeriesCompensator`` per reactor (shape
``series_compensator``).

r and x are the deck's R and X (ohm per phase); with no mutual coupling r0 = r and x0 = x, as in the engine's CIM
export. SeriesCompensator has no per-phase class, so an ``Update`` gives its generated Terminals their phases.
Its ratings are an ``OperationalLimitSet``, as a line's (the deck's own normamps/emergamps only).

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#reactor``.
"""

from __future__ import annotations

from collections.abc import Mapping

from cimtables.connectivity import parse_phases, phase_code
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, mrid, phases_cell, untranscribed_values
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import line as line_mapper
from cimhub_opendss.importer.cimtbl.transformer import parse_bus
from cimhub_opendss.schema import opendss_schema as schema

NATIVE_CLASS = schema.Reactor
PREFIX = "rx_"

_SERIES = "SeriesCompensator"
_NO_DECK = "no deck in the sweep sets it, so a mapping waits for one"
_NOT_MAPPED = "raises when set: " + _NO_DECK
_RELIABILITY = "a reliability setting; no home in the network profile parts"

FIELDS = {
    "name": Field("copied", ((_SERIES, "name", None),), "mRID = rx_ + name, lowercased"),
    "bus1": Field("structural", note="node1 and the phases (the line rule)"),
    "bus2": Field("structural", note="node2; unset or on bus1's bus (a shunt or neutral reactor) raises"),
    "phases": Field("structural", note="the conductor count; default 3"),
    "kvar": Field("structural", note=_NOT_MAPPED + " (X from kvar and kV)"),
    "kv": Field("untranscribed", note="acts only with kvar, which raises"),
    "conn": Field("untranscribed", note="a series reactor has no neutral"),
    "Rmatrix": Field("structural", note=_NOT_MAPPED),
    "Xmatrix": Field("structural", note=_NOT_MAPPED),
    "Parallel": Field("structural", note="raises when yes: " + _NO_DECK),
    "R": Field("copied", ((_SERIES, "r", "ohm"), (_SERIES, "r0", "ohm")), "per phase; r0 = r (no mutual); default 0"),
    "X": Field("copied", ((_SERIES, "x", "ohm"), (_SERIES, "x0", "ohm")), "per phase; x0 = x (no mutual); unset "
                                                                         "raises"),
    "Rp": Field("structural", note=_NOT_MAPPED + " (a parallel R)"),
    "Z1": Field("structural", note=_NOT_MAPPED),
    "Z2": Field("structural", note=_NOT_MAPPED),
    "Z0": Field("structural", note=_NOT_MAPPED),
    "Z": Field("structural", note=_NOT_MAPPED),
    "RCurve": Field("structural", note=_NOT_MAPPED),
    "LCurve": Field("structural", note=_NOT_MAPPED),
    "LmH": Field("structural", note=_NOT_MAPPED + " (X from an inductance)"),
    "normamps": Field("structural", note="instance OperationalLimitSet rx_<name>_limits: CurrentLimit _norm "
                                         "(olt_normal); nothing from the engine's kvar-derived default"),
    "emergamps": Field("structural", note="CurrentLimit _emerg (olt_emergency) in rx_<name>_limits"),
    "faultrate": Field("untranscribed", note=_RELIABILITY),
    "pctperm": Field("untranscribed", note=_RELIABILITY),
    "repair": Field("untranscribed", note=_RELIABILITY),
    "basefreq": Field("untranscribed", note="no home on a compensator; x is at the model's frequency"),
    "enabled": Field("copied", ((_SERIES, "normallyInService", None),), "default true"),
    "like": Field("untranscribed", note="the reader resolves like= before mapping"),
}

_UNMAPPED = ("kvar", "Rmatrix", "Xmatrix", "Rp", "Z1", "Z2", "Z0", "Z", "RCurve", "LCurve", "LmH")

_PROVENANCE = """OpenDSS series Reactor -> SeriesCompensator between its buses: r, x per phase, r0 = r, x0 = x.
Source table: Reactor (records: {count})
Mapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#reactor"""


def _check(reactor) -> None:
    """Raise on what the mapping does not cover (on the record as written, before defaults)."""
    unmapped = [slot for slot in _UNMAPPED if getattr(reactor, slot) not in (None, [])]
    if reactor.Parallel:
        unmapped.append("Parallel")
    if unmapped:
        raise ValueError(f"Reactor {reactor.name}: {', '.join(unmapped)} not mapped yet (no deck in the sweep sets "
                         "them)")
    if reactor.bus2 is None or parse_bus(reactor.bus2)[0] == parse_bus(reactor.bus1)[0]:
        raise ValueError(f"Reactor {reactor.name}: bus1={reactor.bus1}, bus2={reactor.bus2}; a shunt or neutral "
                         "reactor is not mapped (a series reactor joins two buses)")
    if reactor.X is None:
        raise ValueError(f"Reactor {reactor.name}: X is unset; only a reactor given by R and X is mapped")


def map_reactor(native, buses: Mapping[str, BusSystem], container: str) -> Document:
    """Every ``Reactor`` of a DSS model as one ``reactor`` document; ``container`` is the Feeder mRID."""
    reactors = native.list_by_class(NATIVE_CLASS)
    if not reactors:
        return Document(name="reactor", statements=[], profile=CIM_PROFILE)
    defaults = dss_defaults(NATIVE_CLASS)
    rows, terminals, limit_sets, limits = [], [], [], []
    for original in reactors:
        _check(original)
        reactor, defaulted = fill_defaults(FIELDS, original, defaults)
        label = f"Reactor {reactor.name}"
        bus1, bus2, phases = line_mapper.line_phases(reactor, int(reactor.phases), buses, label=label)
        compensator = mrid(PREFIX, reactor.name, lowercase=True)
        r, x = float(reactor.R), float(reactor.X)
        rows.append(Row([compensator, str(reactor.name), bus1, bus2, cell(r), cell(x), cell(r), cell(x),
                         cell(reactor.enabled), buses[bus1].base_voltage],
                        comment="\n".join(part for part in (defaulted, untranscribed_values(FIELDS, reactor)) if part)
                        or None))
        if phases_cell(phases) is not None:  # a balanced three-phase reactor's Terminals keep CIM's default
            code = phase_code(parse_phases(phases))
            terminals += [Row([f"{compensator}_T1", code]), Row([f"{compensator}_T2", code])]
        amps = {slot: float(getattr(reactor, slot)) for slot in ("normamps", "emergamps")
                if getattr(reactor, slot) is not None}
        if amps:
            limit_set, limit_rows = line_mapper.rating_rows(compensator, amps)
            limit_sets.append(limit_set)
            limits += limit_rows
    columns = [Column("mRID"), Column("name"), Column("node1"), Column("node2"), Column("r", "ohm"),
               Column("x", "ohm"), Column("r0", "ohm"), Column("x0", "ohm"), Column("normallyInService"),
               Column("BaseVoltage"), Column("EquipmentContainer", default=container)]
    statements = [
        Table(_SERIES, columns, rows, comment="r0 = r, x0 = x: no mutual coupling (the engine's CIM export)"),
        *([Table("Terminal", [Column("mRID"), Column("phases")], terminals, update=True,
                 comment="SeriesCompensator has no per-phase class: a reactor of fewer than three phases gives its "
                         "generated Terminals their phases here")] if terminals else []),
        *line_mapper.rating_tables(limit_sets, limits),
    ]
    return Document(name="reactor", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(reactors)))
