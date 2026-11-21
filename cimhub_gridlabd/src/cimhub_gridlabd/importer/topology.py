"""The GLM model as a ``cimtopology.core.Network``, for the topology walk (GLM-1, GLM-4).

- **Buses:** every root bus object. A bus is any ``node`` or ``triplex_node`` subclass (``meter``, ``load``,
  ``capacitor``, ``substation``, ``triplex_meter``, ...). A bus whose ``parent`` is a bus is solved by GridLAB-D
  as its parent's bus, so it is not a bus of its own: ``bus_roots`` maps it to the root of its parent chain.
- **Sources:** every ``substation`` and every bus with ``bustype SWING``. Its kV is the system voltage of its
  ``nominal_voltage`` (phase to neutral) on the system its phases give (``line_voltage``). ``SWING_PQ`` is a plain
  bus: it becomes a swing only when its island separates (S1-2).
- **Branches:** every line, switch, fuse, recloser, sectionalizer, series reactor and regulator (a regulator keeps
  the voltage). A switching device's ``status OPEN`` is a normally open branch. A link's phases (N and D aside)
  must be on both its end objects, as GridLAB-D's ``link::init`` throws (``link.cpp:649``, ``:664``); a center
  tap's S is on its to end only (``:604``). One exception, which GridLAB-D cannot load but CIM holds
  (``SwitchPhase.phaseSide1``/``phaseSide2``): an open switching device between laterals on different phases
  (``crossed_phases``, S6-9).
- **Transformers:** one ``Coil`` per winding, from the ``transformer_configuration``. ``WYE_WYE`` and
  ``SINGLE_PHASE`` (one case in ``transformer.cpp:282``): GridLAB-D applies ``V_primary / V_secondary`` to the
  phase voltages and takes its impedance base on ``secondary_voltage`` as written, so the voltages are a ratio to
  it, and the deck says what they rate (``coil_rated``). Line to line (the Java CIMHub exports, S3b-3): polyphase
  coils on the transformer's phase conductors, whatever their number, so a 1-phase ``CN`` unit of 12500/480 V is
  one phase of a 480 V wye secondary. The coil, phase to neutral (the Milsoft WindMil exports, S6): polyphase coils
  of the written voltage x sqrt 3, except a one-conductor unit's primary, a phase-to-neutral coil. A coil-rated
  one-phase service is split-phase (``service_phases``, the user's rule): a 120 V secondary is one leg (s1 to N) and
  a 240 V one a center tap (two halves, s1 N s2), both on a 240 V system, as a 208 V secondary of three coils is ABC
  line to line. Any other one-phase secondary is one phase of a wye, as its primary is (S6-11): a 277 V coil is on
  a 480 V system. ``DELTA_DELTA``, ``DELTA_GWYE``: polyphase, 3-phase only. ``SINGLE_PHASE_CENTER_TAPPED``: a
  phase-to-neutral primary and two split-phase halves of ``secondary_voltage`` each (120 V halves of a 240 V
  secondary).

Equipment names are the GLM names (unique across a model). Values in volts become the walk's kV through pint
(``cimprofiles.units``), never by hand.
"""

from __future__ import annotations

import math

from cimprofiles.units import units
from cimtopology.core import Branch, Coil, Connection, Network, Source, System, Transformer
from cimtopology.core.voltage import NAMEPLATE_TOLERANCE

from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.schema import gridlabd as schema

BUS_CLASSES = (schema.Node, schema.TriplexNode)
BRANCH_CLASSES = (schema.OverheadLine, schema.UndergroundLine, schema.TriplexLine, schema.Switch, schema.Fuse,
                  schema.Recloser, schema.Sectionalizer, schema.SeriesReactor, schema.Regulator)
SWITCHING_CLASSES = (schema.Switch, schema.Fuse, schema.Recloser, schema.Sectionalizer)
_PHASE_LETTERS = frozenset("ABC")
_DELTA_CONNECTIONS = {"DELTA_DELTA", "DELTA_GWYE"}
WYE_CONNECTIONS = {"WYE_WYE", "SINGLE_PHASE"}
_CENTER_TAP = "SINGLE_PHASE_CENTER_TAPPED"
#: A one-phase service's secondary_voltage (kV, within the walk's nameplate tolerance, as ``coil_rated``) -> the
#: split-phase conductors it lands on (the user's, 2026-11-16):
#: 120 V is the s1 leg to N; 240 V is center-tapped, s1 N s2 (two 120 V halves around a grounded N, GridLAB-D's
#: center-tap star of its one coil), so its legs read 120 V to ground. Either is a 240 V split-phase system.
SERVICE_PHASES = {0.12: "s1N", 0.24: "s1s2N"}


def line_voltage(phase_to_neutral: float, system: System) -> float:
    """The system voltage of a bus whose GLM voltage (``nominal_voltage``, ``|voltage_A|``) is
    ``phase_to_neutral``, in the same unit: x sqrt(3) on a 3-phase system (7200 V -> 12470.8 V), x 2 on a
    split-phase one (120 -> 240), unchanged on a single-phase one."""
    if system is System.THREE_PHASE:
        return phase_to_neutral * math.sqrt(3)
    if system is System.SPLIT_PHASE:
        return phase_to_neutral * 2
    return phase_to_neutral


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


def bus_records(model: GlmModel) -> dict[str, object]:
    """Name -> record of every bus object (any ``node`` or ``triplex_node`` subclass)."""
    return {name: record for cls, bucket in model.graph.items() if issubclass(cls, BUS_CLASSES)
            for name, record in bucket.items()}


def bus_roots(model: GlmModel) -> dict[str, str]:
    """Bus object name -> the bus it is solved as: itself, or the root of its ``parent`` chain (GLM-4)."""
    buses = bus_records(model)
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


def swing_buses(model: GlmModel) -> list:
    """Every ``substation`` and every bus with ``bustype SWING``, by name."""
    return sorted((record for record in bus_records(model).values()
                   if isinstance(record, schema.Substation) or str(record.bustype) == "SWING"),
                  key=lambda record: str(record.name))


def source_system(record) -> System:
    """A swing bus's system: 3-phase on three conductors, single-phase on one; any other count raises."""
    conductors = phase_letters(record)
    if len(conductors) == 3:
        return System.THREE_PHASE
    if len(conductors) == 1:
        return System.SINGLE_PHASE
    raise ValueError(f"{record.class_name} {record.name}: phases {record.phases}; only 1- and 3-phase swing buses")


def _sources(model: GlmModel, roots: dict[str, str]):
    for record in swing_buses(model):
        name = str(record.name)
        if roots[name] != name:
            raise ValueError(f"{record.class_name} {name}: a swing bus with a parent")
        system = source_system(record)
        yield Source(name, line_voltage(kv(model, record, "nominal_voltage"), system), system)


def _branches(model: GlmModel, roots: dict[str, str]):
    for cls in BRANCH_CLASSES:
        for record in model.list_by_class(cls):
            is_open = str(record.status) == "OPEN"
            switching = isinstance(record, SWITCHING_CLASSES)
            if is_open and not switching:
                raise ValueError(f"{record.class_name} {record.name}: status OPEN on a device that is not a switch")
            check_end_phases(model, record)
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
    check_end_phases(model, xf, center_tap=connect == _CENTER_TAP)
    v1, v2 = kv(model, config, "primary_voltage"), kv(model, config, "secondary_voltage")
    if connect == _CENTER_TAP:
        if len(conductors) != 1 or "S" not in str(xf.phases):
            raise ValueError(f"transformer {xf.name}: {connect} needs one phase and S, got phases {xf.phases}")
        coils = (Coil(primary, v1, Connection.PHASE_NEUTRAL, conductors),
                 Coil(secondary, v2, Connection.HALF, frozenset({"1"})),
                 Coil(secondary, v2, Connection.HALF, frozenset({"2"})))
    elif connect in WYE_CONNECTIONS and coil_rated(model, xf, config, roots):
        if len(conductors) == 1:
            coils = (Coil(primary, v1, Connection.PHASE_NEUTRAL, conductors),
                     *_service_coils(secondary, v2, service_phases(model, xf, config, roots), conductors))
        else:
            coils = (Coil(primary, line_voltage(v1, System.THREE_PHASE), Connection.POLYPHASE, conductors),
                     Coil(secondary, line_voltage(v2, System.THREE_PHASE), Connection.POLYPHASE, conductors))
    elif connect in WYE_CONNECTIONS or (connect in _DELTA_CONNECTIONS and len(conductors) == 3):
        coils = (Coil(primary, v1, Connection.POLYPHASE, conductors),
                 Coil(secondary, v2, Connection.POLYPHASE, conductors))
    else:
        raise ValueError(f"transformer {xf.name}: connect_type {connect} on phases {xf.phases} is not walked")
    return Transformer(str(xf.name), coils)


def service_phases(model: GlmModel, xf, config, roots: dict[str, str]) -> str | None:
    """The split-phase conductors of a one-phase service's secondary (``SERVICE_PHASES``): a coil-rated
    ``WYE_WYE``/``SINGLE_PHASE`` on one phase and N whose ``secondary_voltage`` is 120 or 240 V within the walk's
    nameplate tolerance (a 110 V can is a leg). None for any other transformer, whose secondary keeps its GLM
    phases."""
    if str(config.connect_type) not in WYE_CONNECTIONS or len(phase_letters(xf)) != 1:
        return None
    if not coil_rated(model, xf, config, roots):
        return None
    secondary = kv(model, config, "secondary_voltage")
    return next((phases for volts, phases in SERVICE_PHASES.items()
                  if math.isclose(secondary, volts, rel_tol=NAMEPLATE_TOLERANCE)), None)


def _service_coils(bus: str, kv_coil: float, service: str | None, conductors: frozenset[str]) -> tuple[Coil, ...]:
    """A one-phase coil-rated secondary for the walk: a split-phase leg (120 V), the two halves of a center tap
    (240 V), else one phase of a wye, a polyphase coil of the coil voltage x sqrt 3 (S6-11: a 277 V coil is on a
    480 V system, as its 7200 V primary is on 12.47 kV)."""
    if service == "s1N":
        return (Coil(bus, kv_coil, Connection.HALF, frozenset({"1"})),)
    if service == "s1s2N":
        return (Coil(bus, kv_coil / 2, Connection.HALF, frozenset({"1"})),
                Coil(bus, kv_coil / 2, Connection.HALF, frozenset({"2"})))
    return (Coil(bus, line_voltage(kv_coil, System.THREE_PHASE), Connection.POLYPHASE, conductors),)


def service_buses(model: GlmModel, roots: dict[str, str]) -> dict[str, str]:
    """Each one-phase service's secondary bus -> its split-phase conductors (``service_phases``). Only loads may sit
    on one: a link other than its transformer, a capacitor or an inverter raises, since their phase letters have no
    split-phase meaning yet; two services on one bus must agree."""
    services: dict[str, str] = {}
    for xf in model.list_by_class(schema.Transformer):
        service = service_phases(model, xf, model.by_name(xf.configuration), roots)
        if service is None:
            continue
        bus = roots[xf.to]
        if services.setdefault(bus, service) != service:
            raise ValueError(f"transformer {xf.name}: service {service} on bus {bus}, which another gives "
                             f"{services[bus]}")
    for cls in (*BRANCH_CLASSES, schema.Transformer):
        for link in model.list_by_class(cls):
            for slot in ("from_node", "to"):
                bus = roots[getattr(link, slot)]
                if bus in services and not (cls is schema.Transformer and slot == "to"):
                    raise ValueError(f"{link.class_name} {link.name}: on the {services[bus]} service bus {bus}; "
                                     "only loads are mapped on a one-phase service")
    for cls in (schema.Capacitor, schema.Inverter):
        for record in model.list_by_class(cls):
            bus = roots.get(str(record.name)) or roots.get(str(record.parent))
            if bus in services:
                raise ValueError(f"{record.class_name} {record.name}: on the {services[bus]} service bus {bus}; "
                                 "only loads are mapped on a one-phase service")
    return services


def check_end_phases(model: GlmModel, link, *, center_tap: bool = False) -> None:
    """A link's phases, N and D aside, must be on both its end objects (``link.cpp:649``, ``:664``); a center
    tap's from end needs its phase letter, its to end the S (``:604``-``:617``)."""
    carried = set(str(link.phases or "")) - {"N", "D"}
    crossed = crossed_phases(model, link) is not None
    for slot, written in (("from_node", "from"), ("to", "to")):
        if slot == "to" and crossed:
            continue
        end = model.by_name(getattr(link, slot))
        needed = (carried - {"S"} if slot == "from_node" else {"S"}) if center_tap else carried
        if not needed <= set(str(end.phases or "")):
            raise ValueError(f"{link.class_name} {link.name}: phases {link.phases} are not all on its {written} "
                             f"{end.class_name} {end.name} ({end.phases}); GridLAB-D throws (link.cpp:664)")


def crossed_phases(model: GlmModel, link) -> str | None:
    """The to end's phases of an open switching device between laterals on different phases (S6-9): its switched
    letters are on its from end, and its to end has as many letters, none of them those, paired in ABC order
    (``SwitchPhase.phaseSide2``). ``None`` for any other link; GridLAB-D loads neither case (``link.cpp:649``)."""
    if not isinstance(link, SWITCHING_CLASSES) or str(link.status) != "OPEN":
        return None
    carried = phase_letters(link)
    near, far = phase_letters(model.by_name(link.from_node)), phase_letters(model.by_name(link.to))
    if not carried <= near or carried & far or len(far) != len(carried):
        return None
    return "".join(sorted(far))


def coil_rated(model: GlmModel, xf, config, roots: dict[str, str]) -> bool:
    """Whether a wye ``config``'s voltages rate the coil (phase to neutral) rather than the line, as ``xf`` wires
    it: its ``primary_voltage`` is the ``nominal_voltage`` (phase to neutral) of the bus ``from`` is solved as,
    or that x sqrt 3, within the walk's nameplate tolerance; anything else raises (S6)."""
    bus = model.by_name(_end(xf, "from_node", roots))
    written, nominal = kv(model, config, "primary_voltage"), kv(model, bus, "nominal_voltage")
    if math.isclose(written, nominal, rel_tol=NAMEPLATE_TOLERANCE):
        return True
    if math.isclose(written, line_voltage(nominal, System.THREE_PHASE), rel_tol=NAMEPLATE_TOLERANCE):
        return False
    raise ValueError(f"transformer {xf.name}: primary_voltage {written:.6g} kV of {config.name} is neither the "
                     f"{nominal:.6g} kV nominal_voltage of its from bus {bus.name} nor that x sqrt 3")
