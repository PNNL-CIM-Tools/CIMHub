"""OpenDSS deck -> ``.cimtbl`` documents -> cim18v17: the orchestrator.

The topology walk runs once (``site``); the master holds the containers, BaseFrequency and BaseVoltages, and
``bus.cimtbl`` gives every bus its ``ConnectivityNode`` and BaseVoltage. ``MAPPING_ORDER`` is the ``Import``
order of the class parts (DSS_REWRITE_PLAN.md section 2): catalogs before the instances that use them. Each slice
adds its mappers here. A DSS class nothing reads is listed by count on the master's comment (DSS-11), so nothing
disappears silently.

Mapping spec: ``cimhub_opendss/docs/CIMTBL_MAPPING.md#master`` and ``#buses``.
"""

from __future__ import annotations

import textwrap
from typing import NamedTuple

from cimtables.document import Column, Document, DocumentSet, Import, ObjectStatement, Row, Table
from cimtopology.core import BusSystem, base_voltage_mrid, nominal_kv, walk

from cimhub_core.base import CimtblImporter
from cimhub_core.cimtbl import CIM_PROFILE, cell, mrid
from cimhub_opendss.dss_reader import dss_defaults
from cimhub_opendss.importer.cimtbl import linecode, vsource
from cimhub_opendss.importer.topology import dss_network
from cimhub_opendss.schema import opendss_schema as schema


class Site(NamedTuple):
    """What every mapper shares: the walk's bus systems and the container mRIDs."""
    circuit: str
    buses: dict[str, BusSystem]
    substation: str
    feeder: str


#: ``(native class, mapper(native, site))`` in ``Import`` order.
MAPPING_ORDER = (
    (linecode.NATIVE_CLASS, lambda native, site: linecode.map_linecode(native)),
    (vsource.NATIVE_CLASS, lambda native, site: vsource.map_vsource(native, site.buses, site.substation)),
)

#: The master's ``Authority`` unless the caller names another (plan D7).
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"


def _options(native):
    """The deck's ``Options`` (circuit name and kept ``Set`` options); a deck with no ``New Circuit`` raises."""
    options = native.list_by_class(schema.Options)
    if not options or options[0].circuit is None:
        raise ValueError("the deck has no New Circuit")
    return options[0]


def site(native) -> Site:
    """Walk the deck's topology and name its containers."""
    circuit = str(_options(native).circuit)
    return Site(circuit, walk(dss_network(native)), mrid("sub_", circuit, lowercase=True),
                mrid("fdr_", circuit, lowercase=True))


def _base_voltages(native, buses: dict[str, BusSystem]) -> Table:
    """The walk's distinct bus voltages, highest first; the comment reconciles them with ``voltagebases``."""
    walked = sorted({nominal_kv(bus.kv) for bus in buses.values()}, reverse=True)
    rows = [Row([base_voltage_mrid(kv), cell(kv)]) for kv in walked]
    given = _options(native).voltagebases or []
    notes = [f"voltagebases: {', '.join(cell(float(kv)) for kv in given)}" if given else "no voltagebases"]
    unused = [kv for kv in given if nominal_kv(kv) not in walked]
    missing = [kv for kv in walked if kv not in {nominal_kv(base) for base in given}]
    if unused:
        notes.append(f"on no bus: {', '.join(cell(float(kv)) for kv in unused)}")
    if missing:
        notes.append(f"not in voltagebases: {', '.join(cell(kv) for kv in missing)}")
    return Table("BaseVoltage", [Column("mRID"), Column("nominalVoltage", "kV")], rows, comment="; ".join(notes))


def _base_frequency(native) -> ObjectStatement:
    """``Set defaultbasefreq``, else the DSS default (DSS-3b)."""
    frequency = _options(native).defaultbasefreq
    comment = None
    if frequency is None:
        frequency = dss_defaults(schema.Options)["defaultbasefreq"]
        comment = f"defaulted: defaultbasefreq={frequency}"
    return ObjectStatement("BaseFrequency", [(Column("mRID"), f"bf_{frequency:g}hz"),
                                             (Column("frequency", "Hz"), cell(float(frequency)))], comment=comment)


def map_master(native, parts: list[Document], site: Site, *, name: str, authority: str = AUTHORITY) -> Document:
    """The master document: containers, BaseFrequency, BaseVoltages, then one ``Import`` per non-empty part."""
    mapped = {native_class for native_class, _ in MAPPING_ORDER} | {schema.Options}
    counts = sorted((cls.__name__, native.count(cls)) for cls in native.graph if cls not in mapped)
    comment = f"OpenDSS deck {name}\nMapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#master"
    if counts:
        comment += "\n" + textwrap.fill("not mapped: " + ", ".join(f"{cls_name} {count}" for cls_name, count in counts),
                                       width=116, break_long_words=False)
    common = [
        ObjectStatement("Substation", [(Column("mRID"), site.substation), (Column("name"), site.circuit)]),
        ObjectStatement("Feeder", [(Column("mRID"), site.feeder), (Column("name"), site.circuit),
                                   (Column("NormalEnergizingSubstation"), site.substation)]),
        _base_frequency(native),
        _base_voltages(native, site.buses),
    ]
    return Document(name=name, statements=[*common, *(Import(part.name) for part in parts)], profile=CIM_PROFILE,
                    authority=authority, model=name, comment=comment)


def map_buses(site: Site) -> Document:
    """``bus.cimtbl``: one ``ConnectivityNode`` per bus the walk reaches, with its BaseVoltage; highest voltage
    first, then by name, so the file does not depend on the walk's internals."""
    ordered = sorted(site.buses.items(), key=lambda item: (-nominal_kv(item[1].kv), item[0]))
    rows = [Row([bus, bus, system.base_voltage]) for bus, system in ordered]
    table = Table("ConnectivityNode", [Column("mRID"), Column("name"), Column("BaseVoltage"),
                                       Column("ConnectivityNodeContainer", default=site.feeder)], rows)
    return Document(name="bus", statements=[table], profile=CIM_PROFILE,
                    comment=f"Bus voltages from the topology walk (cimtopology.core) from the source buses; "
                            f"{len(rows)} buses.\nMapping: cimhub_opendss/docs/CIMTBL_MAPPING.md#buses")


class DssImporter(CimtblImporter):
    """A DSS model to ``.cimtbl`` documents: the master, ``bus``, and one document per mapped DSS class.

    ``name`` is the master's ``Model`` and file stem (the deck's name, e.g. ``IEEE13_CDPSM``).
    """

    def __init__(self, name: str, *, authority: str = AUTHORITY):
        self.name = name
        self.authority = authority

    def to_cimtbl(self, model) -> DocumentSet:
        walked = site(model)
        documents = [map_buses(walked), *(mapper(model, walked) for _, mapper in MAPPING_ORDER)]
        parts = [part for part in documents if part.statements]
        return DocumentSet(master=map_master(model, parts, walked, name=self.name, authority=self.authority),
                           parts=parts)


def dss_to_cim(model, *, name: str, authority: str = AUTHORITY, network=None, artifact_dir=None):
    """A DSS model (``DssReader(path).read_all()``) as a cim18v17 network, built from its written artifacts."""
    return DssImporter(name, authority=authority).to_cim(model, network=network, artifact_dir=artifact_dir)
