"""GridLAB-D model -> ``.cimtbl`` documents -> cim18v17: the orchestrator.

The topology walk runs once (``site``). The master holds the containers, BaseFrequency and BaseVoltages, then one
``Import`` per part: ``bus.cimtbl`` (every root bus), ``source.cimtbl`` and the core ``zip_fractions.cimtbl`` (the
shared ZIP load models) first, then ``MAPPING_ORDER``, the class
parts in the plan's section 2 order (catalogs before the instances that use them); each slice adds its mappers.
``CLASSIFIED`` holds every mapped class's ``FIELDS``. A GLM class not in it is listed by count on the master's
comment (GLM-14), so nothing disappears silently. A value the reader kept as an expression (``LIGHTS*1.2``) in a
slot a mapper reads raises (GLM-8): the mapper would otherwise see the slot as unset. The exception is a load's
``base_power``, whose mapper reads a ``<player>.value*K`` itself (S4a-2). A bus's own load accumulators raise
(S4a-7). An inverter's ``solar`` or ``battery`` is classified with it and written in ``inverter.cimtbl`` (S4b).
A player is a load group and its schedule (S8); the schedule's points are not in the artifact but in the caller's
``time_points`` (``GlmImporter(time_points=...)``, the Parquet sidecar's tables, as GDM's).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#master``.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Callable, NamedTuple


from cimtables.document import Column, Document, DocumentSet, Import, ObjectStatement, Row, Table
from cimtopology.core import BusSystem, base_voltage_mrid, nominal_kv, walk

from cimhub_core.base import CimtblImporter
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid
from cimhub_core.load_response import zip_fractions
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.importer.cimtbl import (bus, capacitor, conductor, configuration, inverter, line, load, player,
                                             schedule,
                                            regulator, series_reactor, spacing, switch, transformer,
                                            transformer_configuration)
from cimhub_gridlabd.importer.cimtbl.catalog import limit_types
from cimhub_gridlabd.importer.topology import BRANCH_CLASSES, bus_roots, glm_network, service_buses, swing_buses
from cimhub_gridlabd.schema import gridlabd as schema

#: The master's ``Authority`` unless the caller names another (plan D7).
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"

#: GridLAB-D's ``powerflow::nominal_frequency`` default (powerflow/powerflow.h).
DEFAULT_FREQUENCY_HZ = 60.0

_log = logging.getLogger(__name__)


class Site(NamedTuple):
    """What every mapper shares: the walk's bus systems, each bus object's root bus (GLM-4), the container mRIDs
    and names, and the base frequency (Hz)."""
    name: str
    buses: dict[str, BusSystem]
    roots: dict[str, str]
    substation: str
    feeder: str
    base_frequency: float
    substation_name: str
    feeder_name: str
    services: dict[str, str]  # a one-phase service's secondary bus -> its split-phase conductors (topology)


#: ``(native class, mapper(model, site))`` in ``Import`` order, after ``bus`` and ``source``. Each slice adds its
#: mappers.
MAPPING_ORDER: tuple[tuple[type | str, Callable[[GlmModel, Site], Document]], ...] = (
    *((native_class, lambda model, site, native_class=native_class: conductor.map_conductors(model, native_class))
      for native_class, _, _ in conductor.CATALOGS),
    (schema.LineSpacing, lambda model, site: spacing.map_line_spacing(model)),
    (schema.LineConfiguration, lambda model, site: configuration.map_line_configuration(model, site.base_frequency)),
    (schema.TriplexLineConfiguration, lambda model, site: configuration.map_triplex_line_configuration(model)),
    (schema.TransformerConfiguration, lambda model, site: transformer_configuration.map_transformer_configuration(
        model, transformer_configuration.wirings(model, site.roots, site.buses))),
    *((native_class, lambda model, site, native_class=native_class:
       line.map_lines(model, native_class, site.roots, site.buses, site.feeder)) for native_class, _, _ in line.LINES),
    *((native_class, lambda model, site, native_class=native_class:
       switch.map_switches(model, native_class, site.roots, site.buses, site.feeder))
      for native_class, _, _ in switch.SWITCHES),
    (series_reactor.NATIVE_CLASS, lambda model, site: series_reactor.map_series_reactors(model, site.roots, site.buses,
                                                                                         site.feeder)),
    (schema.Transformer, lambda model, site: transformer.map_transformers(model, site.roots, site.buses,
                                                                          site.feeder)),
    (schema.Regulator, lambda model, site: regulator.map_regulators(model, site.roots, site.buses, site.feeder)),
    (player.NATIVE_CLASS, lambda model, site: player.map_players(model, load.references(model, players=True))),
    ("schedule", lambda model, site: schedule.map_schedules(model, load.references(model, players=False))),
    *((load_class.native, lambda model, site, load_class=load_class:
       load.map_loads(model, load_class, site.roots, site.buses, site.feeder, site.services))
      for load_class in load.LOAD_CLASSES),
    (schema.Capacitor, lambda model, site: capacitor.map_capacitors(model, site.roots, site.buses, site.feeder)),
    (schema.Inverter, lambda model, site: inverter.map_inverters(model, site.roots, site.buses, site.feeder)),
)

#: Each mapped link class's mRID prefix (a regulator: ``regulator.unit_mrids``). Every link mapper puts its ``from``
#: on terminal 1 and ``to`` on terminal 2.
LINK_PREFIXES: dict[type, str] = {**{native_class: line.PREFIX for native_class, _, _ in line.LINES},
                                  **{native_class: switch.PREFIX for native_class, _, _ in switch.SWITCHES},
                                  series_reactor.NATIVE_CLASS: series_reactor.PREFIX,
                                  schema.Transformer: transformer.PREFIX}

#: Every mapped class's field classification: the expression guard and the master's not-mapped list read it.
CLASSIFIED: dict[type, dict[str, Field]] = {**bus.FIELDS, **conductor.FIELDS, schema.LineSpacing: spacing.FIELDS,
                                            **configuration.FIELDS, **line.FIELDS, **switch.FIELDS,
                                            series_reactor.NATIVE_CLASS: series_reactor.FIELDS,
                                            schema.TransformerConfiguration: transformer_configuration.FIELDS,
                                            schema.Transformer: transformer.FIELDS,
                                            schema.Regulator: regulator.FIELDS,
                                            schema.RegulatorConfiguration: regulator.CONFIGURATION_FIELDS,
                                            player.NATIVE_CLASS: player.FIELDS, **load.FIELDS,
                                            schema.Capacitor: capacitor.FIELDS, **inverter.CLASSIFIED}


def base_frequency(model: GlmModel) -> tuple[float, bool]:
    """``(Hz, defaulted)``: ``module powerflow { nominal_frequency ...; }`` or ``#set
    powerflow::nominal_frequency=...``, else GridLAB-D's 60 Hz."""
    given = model.modules.get("powerflow", {}).get("nominal_frequency")
    if given is None:
        given = model.globals.get("powerflow::nominal_frequency")
    if given is None:
        return DEFAULT_FREQUENCY_HZ, True
    return float(given), False


def site(model: GlmModel, name: str, *, substation: str | None = None, feeder: str | None = None) -> Site:
    """Walk the model's topology and name its containers: ``substation`` and ``feeder``, each ``name`` unless given."""
    substation = name if substation is None else substation
    feeder = name if feeder is None else feeder
    buses, roots = walk(glm_network(model)), bus_roots(model)
    return Site(name, buses, roots, mrid("sub_", substation), mrid("fdr_", feeder), base_frequency(model)[0],
                substation, feeder, service_buses(model, roots))


def check_expressions(model: GlmModel, classified: dict[type, dict[str, Field]],
                      read_by_mapper: dict[type, set[str]]) -> None:
    """Raise if a slot a mapper reads (not untranscribed) holds an expression the reader kept (GLM-8), unless its
    mapper reads the expression itself (``read_by_mapper``: a load's scheduled base, S4a-2)."""
    for (name, slot), text in sorted(model.expressions.items()):
        record = model.by_name(name)
        fields = classified.get(type(record))
        if slot in read_by_mapper.get(type(record), ()):
            continue
        if fields is not None and fields[slot].kind != "untranscribed":
            origin = model.origins[name]
            raise ValueError(f"{record.class_name} {name} ({origin[0]}:{origin[1]}): {slot} is the expression "
                             f"{text!r}, which no mapper reads yet")


def feeder_heads(model: GlmModel, roots: dict[str, str]) -> list[str]:
    """``Feeder.NormalHeadTerminal``: the Terminal on a swing bus of every link that touches one, ``<mRID>_T1`` for
    its ``from`` and ``_T2`` for its ``to`` (the loader's Terminal names). A head on a link no mapper writes raises:
    its Terminal would not exist."""
    swings = {str(record.name) for record in swing_buses(model)}
    heads = []
    for native_class in (*BRANCH_CLASSES, schema.Transformer):
        for link in model.list_by_class(native_class):
            for number, slot in enumerate(("from_node", "to"), start=1):
                if roots[getattr(link, slot)] not in swings:
                    continue
                heads += [f"{equipment}_T{number}" for equipment in _link_mrids(model, link)]
    return sorted(heads)


def _link_mrids(model: GlmModel, link) -> list[str]:
    """The equipment a link is written as: one, or a regulator's units."""
    if isinstance(link, schema.Regulator):
        return regulator.unit_mrids(model, link)
    if type(link) not in LINK_PREFIXES:
        raise ValueError(f"{link.class_name} {link.name}: the feeder head, but no mapper writes a {link.class_name}")
    return [mrid(LINK_PREFIXES[type(link)], link.name)]


def _feeder_head(model: GlmModel, site: Site) -> list[Table]:
    """The head Terminals, set once every part has written its Terminals (after the Imports)."""
    rows = [Row([terminal, site.feeder]) for terminal in feeder_heads(model, site.roots)]
    if not rows:
        return []
    return [Table("Terminal", [Column("mRID"), Column("NormalHeadFeeder")], rows, update=True,
                  comment="the feeder head: each link's Terminal on a swing bus (Feeder.NormalHeadTerminal)")]


def _base_voltages(buses: dict[str, BusSystem]) -> Table:
    """The walk's distinct bus voltages, highest first."""
    walked = sorted({nominal_kv(bus.kv) for bus in buses.values()}, reverse=True)
    rows = [Row([base_voltage_mrid(kv), cell(kv)]) for kv in walked]
    return Table("BaseVoltage", [Column("mRID"), Column("nominalVoltage", "kV")], rows)


def _base_frequency(model: GlmModel) -> ObjectStatement:
    frequency, defaulted = base_frequency(model)
    comment = f"defaulted: powerflow::nominal_frequency={frequency}" if defaulted else None
    return ObjectStatement("BaseFrequency", [(Column("mRID"), f"bf_{frequency:g}hz"),
                                             (Column("frequency", "Hz"), cell(frequency))], comment=comment)


def _not_mapped(model: GlmModel, mapped) -> list[tuple[str, int]]:
    """``(GLM type, count)`` of every object no mapper reads: schema classes and types the schema lacks."""
    counts = {cls.class_name: model.count(cls) for cls in model.graph if cls not in mapped}
    counts.update(model.not_read)
    unread = len(set(model.schedules) - set(load.references(model, players=False)))
    if unread:
        counts["schedule"] = unread  # no load's base reads it (a house's)
    return sorted(counts.items())


def map_master(model: GlmModel, parts: list[Document], site: Site, *, authority: str = AUTHORITY) -> Document:
    """The master document: containers, BaseFrequency, BaseVoltages, then one ``Import`` per non-empty part."""
    mapped = set(CLASSIFIED)
    comment = f"GridLAB-D model {site.name}\nMapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#master"
    counts = _not_mapped(model, mapped)
    if counts:
        comment += "\n" + textwrap.fill("not mapped: " + ", ".join(f"{name} {count}" for name, count in counts),
                                       width=116, break_long_words=False)
    common = [
        ObjectStatement("Substation", [(Column("mRID"), site.substation), (Column("name"), site.substation_name)]),
        ObjectStatement("Feeder", [(Column("mRID"), site.feeder), (Column("name"), site.feeder_name),
                                   (Column("NormalEnergizingSubstation"), site.substation)]),
        _base_frequency(model),
        _base_voltages(site.buses),
        limit_types(),
    ]
    statements = [*common, *(Import(part.name) for part in parts), *_feeder_head(model, site)]
    return Document(name=site.name, statements=statements,
                    profile=CIM_PROFILE, authority=authority, model=site.name, comment=comment)


class GlmImporter(CimtblImporter):
    """A GLM model to ``.cimtbl`` documents: the master and one document per mapped GLM class.

    ``name`` is the master's ``Model`` and file stem (the model's name, e.g. ``IEEE13_cdpsm``). ``substation`` and
    ``feeder`` name the containers (``sub_<substation>``, ``fdr_<feeder>``), each ``name`` unless given, so a model's
    scope and its container keys can differ (a utility code over a feeder's own key). ``time_points`` is the
    caller's dict of time point tables: ``to_cim`` adds the players' ``RegularTimePoint`` table to it (S8-4); without
    it the points are dropped with one warning.
    """

    def __init__(self, name: str, *, authority: str = AUTHORITY, substation: str | None = None,
                 feeder: str | None = None, time_points: dict | None = None):
        self.name = name
        self.authority = authority
        self.substation = substation
        self.feeder = feeder
        self.time_points = time_points

    def to_cimtbl(self, model: GlmModel) -> DocumentSet:
        check_expressions(model, CLASSIFIED, load.EXPRESSION_SLOTS)
        bus.check_bus_loads(model, CLASSIFIED)
        walked = site(model, self.name, substation=self.substation, feeder=self.feeder)
        documents = [bus.map_buses(model, walked.buses, walked.roots, walked.feeder),
                     bus.map_source(model, walked.buses, walked.substation), zip_fractions(),
                     *(mapper(model, walked) for _, mapper in MAPPING_ORDER)]
        parts = [part for part in documents if part.statements]
        return DocumentSet(master=map_master(model, parts, walked, authority=self.authority), parts=parts)

    def to_cim(self, model: GlmModel, *, network=None, artifact_dir=None):
        """The core ``to_cim``, then the players' and schedules' points, keyed by their bound schedules' uri (S8-4,
        S9)."""
        bound = super().to_cim(model, network=network, artifact_dir=artifact_dir)
        points = {**player.player_points(model),
                  **schedule.schedule_points(model, load.references(model, players=False))}
        if not points:
            return bound
        if self.time_points is None:
            _log.warning("the points of %d player(s) and schedule(s) are dropped: pass GlmImporter(time_points={}) to "
                         "keep them: %s", len(points), sorted(points))
            return bound
        from cimhub_core.time_points import add_regular_time_points  # the time-points extra

        add_regular_time_points(self.time_points, bound, points)
        return bound


def glm_to_cim(model: GlmModel, *, name: str, authority: str = AUTHORITY, substation: str | None = None,
               feeder: str | None = None, network=None, artifact_dir=None, time_points: dict | None = None):
    """A GLM model (``GlmReader(path).read_all()``) as a cim18v17 network, built from its written artifacts; the
    players' points go to ``time_points`` (``GlmImporter``)."""
    importer = GlmImporter(name, authority=authority, substation=substation, feeder=feeder, time_points=time_points)
    return importer.to_cim(model, network=network, artifact_dir=artifact_dir)
