"""The DSS model as a ``cimtopology.core.Network``, for the topology walk (DSS-1).

- **Sources:** every ``Vsource`` (``New Circuit`` included), with its DSS defaults (``vsource.with_defaults``);
  ``basekv`` is phase-to-phase on a 3-phase source and the source voltage on a 1-phase one.
- **Branches:** every ``Line`` (switches too: an open switch keeps its voltage), and every ``Reactor`` or
  ``Capacitor`` with a ``bus2`` on another bus (a series element). Whether a switch is normally open comes
  from its ``SwtControl`` in S3; until then every branch is closed, which the walk does not depend on.
- **Transformers:** every ``Transformer``, with ``phases``, ``windings``, ``kVs`` and ``conns`` from the
  instance, else its ``XfmrCode``. A polyphase winding's kV is phase-to-phase; a single-phase coil's
  connection comes from its nodes (nodes 1-3 are phase conductors, 0 and 4+ neutral), and windings 2 and 3
  on one bus form a split-phase secondary (``transformer.is_split_phase``).

Bus names are lowercased, as the mappers use them. Equipment names are ``<Class>.<name>``, so a Line and a
Reactor may share a name, as DSS allows.
"""

from __future__ import annotations

from typing import NamedTuple

from cimtopology.core import Branch, Coil, Connection, Network, Source, System, Transformer

from cimhub_opendss.importer.cimtbl import vsource as vsource_mapper
from cimhub_opendss.importer.cimtbl.transformer import is_split_phase, parse_bus, winding_nodes
from cimhub_opendss.schema import opendss_schema as schema

_PHASE_NODES = {1, 2, 3}
_SOURCE_SYSTEM = {3: System.THREE_PHASE, 1: System.SINGLE_PHASE}
_DSS_DEFAULT_PHASES = 3


class _Winding(NamedTuple):
    number: int
    bus: str
    nodes: tuple[int, ...]
    kv: float


def dss_network(native) -> Network:
    """The sources, branches and transformer coils of a DSS model."""
    codes = {code.name.lower(): code for code in native.list_by_class(schema.Xfmrcode)}
    return Network(
        sources=tuple(_source(vsource) for vsource in native.list_by_class(schema.Vsource)),
        branches=tuple(_branches(native)),
        transformers=tuple(_transformer(xf, codes) for xf in native.list_by_class(schema.Transformer)),
    )


def _source(vsource) -> Source:
    vsource, _, _ = vsource_mapper.with_defaults(vsource)
    if vsource.phases not in _SOURCE_SYSTEM:
        raise ValueError(f"Vsource {vsource.name}: phases={vsource.phases}; only 1- and 3-phase sources are walked")
    return Source(parse_bus(vsource.bus1)[0], float(vsource.basekv), _SOURCE_SYSTEM[vsource.phases])


def _branches(native):
    for line in native.list_by_class(schema.Line):
        if line.bus1 is None or line.bus2 is None:
            raise ValueError(f"Line {line.name}: bus1={line.bus1}, bus2={line.bus2}; both are needed")
        yield Branch(f"Line.{line.name}".lower(), parse_bus(line.bus1)[0], parse_bus(line.bus2)[0],
                     switch=bool(line.Switch))
    for series_class in (schema.Reactor, schema.Capacitor):
        for element in native.list_by_class(series_class):
            if element.bus2 is not None and parse_bus(element.bus2)[0] != parse_bus(element.bus1)[0]:
                yield Branch(f"{series_class.__name__}.{element.name}".lower(), parse_bus(element.bus1)[0],
                             parse_bus(element.bus2)[0])


def _slot(xf, code, slot: str):
    """The instance's value, else its XfmrCode's (the reader gives an unset array as ``[]``)."""
    value = getattr(xf, slot)
    if value in (None, []) and code is not None:
        value = getattr(code, slot)
    return value


def _transformer(xf, codes) -> Transformer:
    code = None
    if xf.XfmrCode:
        code = codes.get(str(xf.XfmrCode).lower())
        if code is None:
            raise ValueError(f"Transformer {xf.name}: XfmrCode={xf.XfmrCode} is not defined")
    for slot in ("bus", "kV", "conn"):
        if getattr(xf, slot) is not None or getattr(code, slot, None) is not None:
            raise ValueError(f"Transformer {xf.name}: {slot} is set without wdg= or an array")
    phases = _slot(xf, code, "phases") or _DSS_DEFAULT_PHASES
    buses = list(xf.buses or [])
    kvs = _slot(xf, code, "kVs") or []
    conns = [str(conn).lower() for conn in _slot(xf, code, "conns") or []] or ["wye"] * len(buses)
    count = _slot(xf, code, "windings") or len(buses)
    if not (len(buses) == len(kvs) == len(conns) == count):
        raise ValueError(f"Transformer {xf.name}: windings={count}, buses={buses}, kVs={kvs}, conns={conns}; "
                         "one of each per winding")
    windings = []
    for number, (spec, kv, conn) in enumerate(zip(buses, kvs, conns), start=1):
        bus, given = parse_bus(spec)
        windings.append(_Winding(number, bus, winding_nodes(given, phases, conn == "wye", name=xf.name), float(kv)))
    coils = tuple(_coil(winding, windings, phases, xf.name) for winding in windings)
    return Transformer(f"Transformer.{xf.name}".lower(), coils)


def _coil(winding: _Winding, windings: list[_Winding], phases: int, name: str) -> Coil:
    if phases > 1:
        return Coil(winding.bus, winding.kv, Connection.POLYPHASE, frozenset(winding.nodes[:phases]))
    conductors = frozenset(node for node in winding.nodes if node in _PHASE_NODES)
    on_bus = [other for other in windings if other.bus == winding.bus]
    if len(on_bus) > 1 and is_split_phase(on_bus):
        connection = Connection.HALF
    elif len(conductors) == 2:
        connection = Connection.PHASE_PHASE
    elif len(conductors) == 1:
        connection = Connection.PHASE_NEUTRAL
    else:
        raise ValueError(f"Transformer {name}: winding {winding.number} on {winding.bus}{winding.nodes} "
                         "has no phase conductor")
    return Coil(winding.bus, winding.kv, connection, conductors)
