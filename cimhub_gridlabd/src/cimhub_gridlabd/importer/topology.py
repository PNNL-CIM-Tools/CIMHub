"""The GLM model as a ``cimtopology.core.Network``, for the topology walk (GLM-1, GLM-4).

- **Buses:** every root bus object. A bus is any ``node`` or ``triplex_node`` subclass (``meter``, ``load``,
  ``capacitor``, ``substation``, ``triplex_meter``, ...). A bus whose ``parent`` is a bus is solved by GridLAB-D
  as its parent's bus, so it is not a bus of its own: ``bus_roots`` maps it to the root of its parent chain.
- **Sources:** every ``substation`` and every bus with ``bustype SWING``. Its kV is the system voltage of its
  ``nominal_voltage`` (phase to neutral) on the system its phases give (``line_kv``).
- **Branches:** every line, switch, fuse, recloser, sectionalizer, series reactor and regulator (a regulator keeps
  the voltage). A switching device's ``status OPEN`` is a normally open branch.
- **Transformers:** one ``Coil`` per winding, from the ``transformer_configuration``. ``WYE_WYE``: polyphase
  coils on the transformer's phase conductors, whatever their number: GridLAB-D applies ``V_primary /
  V_secondary`` to the phase voltages, and the ratings are line to line (``transformer.cpp``: ``Np = V_primary /
  sqrt(3)``), so a 1-phase ``CN`` unit of 12500/480 V is one phase of a 480 V wye secondary. ``DELTA_DELTA``,
  ``DELTA_GWYE``: polyphase, 3-phase only. ``SINGLE_PHASE_CENTER_TAPPED``: a phase-to-neutral primary and two
  split-phase halves of ``secondary_voltage`` each (120 V halves of a 240 V secondary).

Equipment names are the GLM names (unique across a model). Values in volts become the walk's kV through pint
(``cimprofiles.units``), never by hand.
"""

from __future__ import annotations

import math

from cimprofiles.units import units
from cimtopology.core import Branch, Coil, Connection, Network, Source, System, Transformer

from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.schema import gridlabd as schema

BUS_CLASSES = (schema.Node, schema.TriplexNode)
BRANCH_CLASSES = (schema.OverheadLine, schema.UndergroundLine, schema.TriplexLine, schema.Switch, schema.Fuse,
                  schema.Recloser, schema.Sectionalizer, schema.SeriesReactor, schema.Regulator)
SWITCHING_CLASSES = (schema.Switch, schema.Fuse, schema.Recloser, schema.Sectionalizer)
_PHASE_LETTERS = frozenset("ABC")
_DELTA_CONNECTIONS = {"DELTA_DELTA", "DELTA_GWYE"}
_CENTER_TAP = "SINGLE_PHASE_CENTER_TAPPED"


def line_kv(phase_to_neutral_kv: float, system: System) -> float:
    """The system voltage (``BusSystem.kv``) of a bus whose GLM ``nominal_voltage`` is ``phase_to_neutral_kv``:
    x sqrt(3) on a 3-phase system (7.2 kV -> 12.47), x 2 on a split-phase one (0.12 -> 0.24), unchanged on a
    single-phase one."""
    if system is System.THREE_PHASE:
        return phase_to_neutral_kv * math.sqrt(3)
    if system is System.SPLIT_PHASE:
        return phase_to_neutral_kv * 2
    return phase_to_neutral_kv


def kv(model: GlmModel, record, slot: str) -> float:
    """``slot`` of ``record`` in kV, from the unit it is written in (or the schema's)."""
    value = getattr(record, slot)
    if value is None:
        raise ValueError(f"{record.class_name} {record.name}: {slot} is not set")
    return units.Quantity(float(value), model.unit(record, slot)).to("kV").magnitude


def phase_letters(record) -> frozenset[str]:
    """The phase conductors (A, B, C) in a GLM ``phases`` value; N, S and D are not conductors."""
    if record.phases is None:
        raise ValueError(f"{record.class_name} {record.name}: phases is not set")
    return frozenset(str(record.phases)) & _PHASE_LETTERS


def _buses(model: GlmModel) -> dict[str, object]:
    return {name: record for cls, bucket in model.graph.items() if issubclass(cls, BUS_CLASSES)
            for name, record in bucket.items()}


def bus_roots(model: GlmModel) -> dict[str, str]:
    """Bus object name -> the bus it is solved as: itself, or the root of its ``parent`` chain (GLM-4)."""
    buses = _buses(model)
    roots: dict[str, str] = {}
    for name, record in buses.items():
        chain = [name]
        while record.parent is not None:
            if record.parent not in buses:
                raise ValueError(f"{record.class_name} {chain[-1]}: parent {record.parent} is not a bus object")
            if record.parent in chain:
                raise ValueError(f"{record.class_name} {name}: parent chain loops: {' -> '.join(chain)}")
            chain.append(record.parent)
            record = buses[record.parent]
        roots[name] = chain[-1]
    return roots


def glm_network(model: GlmModel) -> Network:
    """The sources, branches and transformer coils of a GLM model, on root buses."""
    roots = bus_roots(model)
    return Network(
        sources=tuple(_sources(model, roots)),
        branches=tuple(_branches(model, roots)),
        transformers=tuple(_transformer(model, xf, roots) for xf in model.list_by_class(schema.Transformer)),
        nodes=tuple(sorted(set(roots.values()))),
    )


def _end(record, slot: str, roots: dict[str, str]) -> str:
    bus = getattr(record, slot)
    if bus not in roots:
        raise ValueError(f"{record.class_name} {record.name}: {slot} {bus} is not a bus object")
    return roots[bus]


def _sources(model: GlmModel, roots: dict[str, str]):
    for name, record in _buses(model).items():
        if not (isinstance(record, schema.Substation) or str(record.bustype) == "SWING"):
            continue
        if roots[name] != name:
            raise ValueError(f"{record.class_name} {name}: a swing bus with a parent")
        conductors = phase_letters(record)
        if len(conductors) == 3:
            system = System.THREE_PHASE
        elif len(conductors) == 1:
            system = System.SINGLE_PHASE
        else:
            raise ValueError(f"{record.class_name} {name}: phases {record.phases}; only 1- and 3-phase swing buses")
        yield Source(name, line_kv(kv(model, record, "nominal_voltage"), system), system)


def _branches(model: GlmModel, roots: dict[str, str]):
    for cls in BRANCH_CLASSES:
        for record in model.list_by_class(cls):
            is_open = str(record.status) == "OPEN"
            switching = isinstance(record, SWITCHING_CLASSES)
            if is_open and not switching:
                raise ValueError(f"{record.class_name} {record.name}: status OPEN on a device that is not a switch")
            yield Branch(str(record.name), _end(record, "from_node", roots), _end(record, "to", roots),
                         switch=switching, open=is_open)


def _transformer(model: GlmModel, xf, roots: dict[str, str]) -> Transformer:
    if xf.configuration is None:
        raise ValueError(f"transformer {xf.name}: configuration is not set")
    config = model.by_name(xf.configuration)
    if not isinstance(config, schema.TransformerConfiguration):
        raise ValueError(f"transformer {xf.name}: configuration {xf.configuration} is a {config.class_name}")
    primary, secondary = _end(xf, "from_node", roots), _end(xf, "to", roots)
    conductors = phase_letters(xf)
    connect = str(config.connect_type)
    v1, v2 = kv(model, config, "primary_voltage"), kv(model, config, "secondary_voltage")
    if connect == _CENTER_TAP:
        if len(conductors) != 1 or "S" not in str(xf.phases):
            raise ValueError(f"transformer {xf.name}: {connect} needs one phase and S, got phases {xf.phases}")
        coils = (Coil(primary, v1, Connection.PHASE_NEUTRAL, conductors),
                 Coil(secondary, v2, Connection.HALF, frozenset({"1"})),
                 Coil(secondary, v2, Connection.HALF, frozenset({"2"})))
    elif connect == "WYE_WYE" or (connect in _DELTA_CONNECTIONS and len(conductors) == 3):
        coils = (Coil(primary, v1, Connection.POLYPHASE, conductors),
                 Coil(secondary, v2, Connection.POLYPHASE, conductors))
    else:
        raise ValueError(f"transformer {xf.name}: connect_type {connect} on phases {xf.phases} is not walked")
    return Transformer(str(xf.name), coils)
