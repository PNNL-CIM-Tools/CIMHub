"""GridLAB-D model -> ``.cimtbl`` documents -> cim18v17: the orchestrator.

The topology walk runs once (``site``). The master holds the containers, BaseFrequency and BaseVoltages, then one
``Import`` per part: ``bus.cimtbl`` (every root bus) and ``source.cimtbl`` first, then ``MAPPING_ORDER``, the class
parts in the plan's section 2 order (catalogs before the instances that use them); each slice adds its mappers.
``CLASSIFIED`` holds every mapped class's ``FIELDS``. A GLM class not in it is listed by count on the master's
comment (GLM-14), so nothing disappears silently. A value the reader kept as an expression (``LIGHTS*1.2``) in a
slot a mapper reads raises (GLM-8): the mapper would otherwise see the slot as unset.

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#master``.
"""

from __future__ import annotations

import textwrap
from typing import Callable, NamedTuple

from cimtables.document import Column, Document, DocumentSet, Import, ObjectStatement, Row, Table
from cimtopology.core import BusSystem, base_voltage_mrid, nominal_kv, walk

from cimhub_core.base import CimtblImporter
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.importer.cimtbl import bus, conductor, configuration, spacing
from cimhub_gridlabd.importer.cimtbl.catalog import limit_types
from cimhub_gridlabd.importer.topology import bus_roots, glm_network
from cimhub_gridlabd.schema import gridlabd as schema

#: The master's ``Authority`` unless the caller names another (plan D7).
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"

#: GridLAB-D's ``powerflow::nominal_frequency`` default (powerflow/powerflow.h).
DEFAULT_FREQUENCY_HZ = 60.0


class Site(NamedTuple):
    """What every mapper shares: the walk's bus systems, each bus object's root bus (GLM-4), the container mRIDs
    and the base frequency (Hz)."""
    name: str
    buses: dict[str, BusSystem]
    roots: dict[str, str]
    substation: str
    feeder: str
    base_frequency: float


#: ``(native class, mapper(model, site))`` in ``Import`` order, after ``bus`` and ``source``. Each slice adds its
#: mappers.
MAPPING_ORDER: tuple[tuple[type, Callable[[GlmModel, Site], Document]], ...] = (
    *((native_class, lambda model, site, native_class=native_class: conductor.map_conductors(model, native_class))
      for native_class, _, _ in conductor.CATALOGS),
    (schema.LineSpacing, lambda model, site: spacing.map_line_spacing(model)),
    (schema.LineConfiguration, lambda model, site: configuration.map_line_configuration(model, site.base_frequency)),
    (schema.TriplexLineConfiguration, lambda model, site: configuration.map_triplex_line_configuration(model)),
)

#: Every mapped class's field classification: the expression guard and the master's not-mapped list read it.
CLASSIFIED: dict[type, dict[str, Field]] = {**bus.FIELDS, **conductor.FIELDS, schema.LineSpacing: spacing.FIELDS,
                                            **configuration.FIELDS}


def base_frequency(model: GlmModel) -> tuple[float, bool]:
    """``(Hz, defaulted)``: ``module powerflow { nominal_frequency ...; }`` or ``#set
    powerflow::nominal_frequency=...``, else GridLAB-D's 60 Hz."""
    given = model.modules.get("powerflow", {}).get("nominal_frequency")
    if given is None:
        given = model.globals.get("powerflow::nominal_frequency")
    if given is None:
        return DEFAULT_FREQUENCY_HZ, True
    return float(given), False


def site(model: GlmModel, name: str) -> Site:
    """Walk the model's topology and name its containers."""
    return Site(name, walk(glm_network(model)), bus_roots(model), mrid("sub_", name), mrid("fdr_", name),
                base_frequency(model)[0])


def check_expressions(model: GlmModel, classified: dict[type, dict[str, Field]]) -> None:
    """Raise if a slot a mapper reads (not untranscribed) holds an expression the reader kept (GLM-8)."""
    for (name, slot), text in sorted(model.expressions.items()):
        record = model.by_name(name)
        fields = classified.get(type(record))
        if fields is not None and fields[slot].kind != "untranscribed":
            origin = model.origins[name]
            raise ValueError(f"{record.class_name} {name} ({origin[0]}:{origin[1]}): {slot} is the expression "
                             f"{text!r}, which no mapper reads yet (GLM-8)")


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
        ObjectStatement("Substation", [(Column("mRID"), site.substation), (Column("name"), site.name)]),
        ObjectStatement("Feeder", [(Column("mRID"), site.feeder), (Column("name"), site.name),
                                   (Column("NormalEnergizingSubstation"), site.substation)]),
        _base_frequency(model),
        _base_voltages(site.buses),
        limit_types(),
    ]
    return Document(name=site.name, statements=[*common, *(Import(part.name) for part in parts)],
                    profile=CIM_PROFILE, authority=authority, model=site.name, comment=comment)


class GlmImporter(CimtblImporter):
    """A GLM model to ``.cimtbl`` documents: the master and one document per mapped GLM class.

    ``name`` is the master's ``Model`` and file stem (the model's name, e.g. ``IEEE13_cdpsm``).
    """

    def __init__(self, name: str, *, authority: str = AUTHORITY):
        self.name = name
        self.authority = authority

    def to_cimtbl(self, model: GlmModel) -> DocumentSet:
        check_expressions(model, CLASSIFIED)
        walked = site(model, self.name)
        documents = [bus.map_buses(model, walked.buses, walked.roots, walked.feeder),
                     bus.map_source(model, walked.buses, walked.substation),
                     *(mapper(model, walked) for _, mapper in MAPPING_ORDER)]
        parts = [part for part in documents if part.statements]
        return DocumentSet(master=map_master(model, parts, walked, authority=self.authority), parts=parts)


def glm_to_cim(model: GlmModel, *, name: str, authority: str = AUTHORITY, network=None, artifact_dir=None):
    """A GLM model (``GlmReader(path).read_all()``) as a cim18v17 network, built from its written artifacts."""
    return GlmImporter(name, authority=authority).to_cim(model, network=network, artifact_dir=artifact_dir)
