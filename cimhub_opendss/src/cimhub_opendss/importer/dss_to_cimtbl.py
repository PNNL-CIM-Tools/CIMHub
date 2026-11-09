"""OpenDSS deck -> ``.cimtbl`` documents -> cim18v17: the orchestrator.

The topology walk runs once (``site``); the master holds the containers, BaseFrequency and BaseVoltages, and
``bus.cimtbl`` gives every bus its ``ConnectivityNode`` and BaseVoltage; the core ``zip_fractions.cimtbl``
(DSS-7) is always written. ``MAPPING_ORDER`` is the ``Import``
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
from cimhub_core.load_response import zip_fractions
from cimhub_opendss.importer.cimtbl import (capacitor, capcontrol, generator, geometry, line, linecode, load,
                                            pvsystem, reactor, regcontrol, storage, transformer, vsource, wire,
                                            xfmrcode)
from cimhub_opendss.importer.topology import dss_network
from cimhub_opendss.schema import opendss_schema as schema


class Site(NamedTuple):
    """What every mapper shares: the walk's bus systems, the container mRIDs, the base frequency (Hz) and the
    importer's ``length_unit`` override (DSS-3)."""
    circuit: str
    buses: dict[str, BusSystem]
    substation: str
    feeder: str
    base_frequency: float
    length_unit: str | None


def _wire_mapper(native_class, prefix, fields):
    return native_class, lambda native, site: wire.map_wires(native, native_class, prefix, fields)


#: ``(native class, mapper(native, site))`` in ``Import`` order: catalogs before the instances that use them.
MAPPING_ORDER = (
    *(_wire_mapper(*catalog) for catalog in wire.CATALOGS),
    (schema.Linespacing, lambda native, site: geometry.map_linespacing(native)),
    (schema.Linegeometry, lambda native, site: geometry.map_linegeometry(native)),
    (linecode.NATIVE_CLASS, lambda native, site: linecode.map_linecode(
        native, base_frequency=site.base_frequency, length_unit=site.length_unit)),
    (xfmrcode.NATIVE_CLASS, lambda native, site: xfmrcode.map_xfmrcode(native, site.buses)),
    (vsource.NATIVE_CLASS, lambda native, site: vsource.map_vsource(native, site.buses, site.substation)),
    (line.NATIVE_CLASS, lambda native, site: line.map_line(native, site.buses, site.feeder,
                                                           base_frequency=site.base_frequency,
                                                           length_unit=site.length_unit)),
    (reactor.NATIVE_CLASS, lambda native, site: reactor.map_reactor(native, site.buses, site.feeder)),
    (transformer.NATIVE_CLASS, lambda native, site: transformer.map_transformer(native, site.buses, site.feeder)),
    (regcontrol.NATIVE_CLASS, lambda native, site: regcontrol.map_regcontrol(native)),
    (load.NATIVE_CLASS, lambda native, site: load.map_load(native, site.buses, site.feeder)),
    (capacitor.NATIVE_CLASS, lambda native, site: capacitor.map_capacitor(native, site.buses, site.feeder)),
    (capcontrol.NATIVE_CLASS, lambda native, site: capcontrol.map_capcontrol(native, site.buses)),
    (pvsystem.NATIVE_CLASS, lambda native, site: pvsystem.map_pvsystem(native, site.buses, site.feeder)),
    (storage.NATIVE_CLASS, lambda native, site: storage.map_storage(native, site.buses, site.feeder)),
    (generator.NATIVE_CLASS, lambda native, site: generator.map_generator(native, site.buses, site.feeder)),
)

#: Classes a mapper of another class reads in full, so they are mapped too: the switch controls (DSS-9).
READ_BY_OTHERS = tuple(native_class for native_class, _ in line.CONTROLS)

#: The master's ``Authority`` unless the caller names another (plan D7).
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"


def _options(native):
    """The deck's ``Options`` (circuit name and kept ``Set`` options); a deck with no ``New Circuit`` raises."""
    options = native.list_by_class(schema.Options)
    if not options or options[0].circuit is None:
        raise ValueError("the deck has no New Circuit")
    return options[0]


def base_frequency(native) -> tuple[float, bool]:
    """``(Hz, defaulted)``: ``Set defaultbasefreq``, else the DSS default (DSS-3b)."""
    frequency = _options(native).defaultbasefreq
    if frequency is None:
        return float(dss_defaults(schema.Options)["defaultbasefreq"]), True
    return float(frequency), False


def site(native, length_unit: str | None = None) -> Site:
    """Walk the deck's topology and name its containers."""
    circuit = str(_options(native).circuit)
    return Site(circuit, walk(dss_network(native)), mrid("sub_", circuit, lowercase=True),
                mrid("fdr_", circuit, lowercase=True), base_frequency(native)[0], length_unit)


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
    """The master's BaseFrequency (``base_frequency``)."""
    frequency, defaulted = base_frequency(native)
    comment = f"defaulted: defaultbasefreq={frequency}" if defaulted else None
    return ObjectStatement("BaseFrequency", [(Column("mRID"), f"bf_{frequency:g}hz"),
                                             (Column("frequency", "Hz"), cell(float(frequency)))], comment=comment)


def limit_types() -> Table:
    """The two ``OperationalLimitType``s every ``CurrentLimit`` names (R1, approved 2026-11-08)."""
    rows = [Row([limit_mrid, kind, kind, infinite, "absoluteValue"]) for limit_mrid, kind, infinite in line.LIMIT_TYPES]
    return Table("OperationalLimitType", [Column("mRID"), Column("name"), Column("durationKind"),
                                          Column("isInfiniteDuration"), Column("direction")], rows)


def map_master(native, parts: list[Document], site: Site, *, name: str, authority: str = AUTHORITY) -> Document:
    """The master document: containers, BaseFrequency, BaseVoltages, then one ``Import`` per non-empty part."""
    mapped = {native_class for native_class, _ in MAPPING_ORDER} | {schema.Options, *READ_BY_OTHERS}
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
        limit_types(),
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

    ``name`` is the master's ``Model`` and file stem (the deck's name, e.g. ``IEEE13_CDPSM``). ``length_unit``
    is the per-length unit of line codes with no units on code or line, overriding the magnitude gate (DSS-3).
    """

    def __init__(self, name: str, *, authority: str = AUTHORITY, length_unit: str | None = None):
        self.name = name
        self.authority = authority
        self.length_unit = length_unit

    def to_cimtbl(self, model) -> DocumentSet:
        walked = site(model, self.length_unit)
        documents = [map_buses(walked), zip_fractions(), *(mapper(model, walked) for _, mapper in MAPPING_ORDER)]
        parts = [part for part in documents if part.statements]
        return DocumentSet(master=map_master(model, parts, walked, name=self.name, authority=self.authority),
                           parts=parts)


def dss_to_cim(model, *, name: str, authority: str = AUTHORITY, length_unit: str | None = None, network=None,
               artifact_dir=None):
    """A DSS model (``DssReader(path).read_all()``) as a cim18v17 network, built from its written artifacts."""
    return DssImporter(name, authority=authority, length_unit=length_unit).to_cim(model, network=network,
                                                                                artifact_dir=artifact_dir)
