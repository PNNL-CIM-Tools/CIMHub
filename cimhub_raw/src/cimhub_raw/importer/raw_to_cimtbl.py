"""PSS/E RAW v34 -> ``.cimtbl`` documents -> cim18v17 (``BusBranchModel``).

Usage::

    from cimhub_raw.raw34_reader import Raw34Reader
    from cimhub_raw.importer.raw_to_cimtbl import raw_to_cim

    network = raw_to_cim(Raw34Reader("IEEE_14_bus.raw").read_all(), name="IEEE14", artifact_dir="out/IEEE14")

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md``; plan: ``.development/RAW_REWRITE_PLAN.md``.
"""

from __future__ import annotations

import textwrap

from cimgraph.models import BusBranchModel
from cimtables.document import Column, Document, DocumentSet, Import, ObjectStatement, Row, Table

from cimhub_core.base import CimtblImporter
from cimhub_core.cimtbl import CIM_PROFILE, cell, mrid
from cimhub_raw.importer.cimtbl import (
    area_interchange,
    branch,
    bus,
    case_identification,
    facts_device,
    fixed_shunt,
    gne_device,
    impedance_correction,
    induction_machine,
    load,
    multi_section_line,
    multi_terminal_dc,
    owner,
    switch,
    switched_shunt,
    two_terminal_dc,
    vsc_dc,
    zone,
)
from cimhub_raw.importer.cimtbl.ratings import rating_type_table
from cimhub_raw.importer.topology import substation_groups

#: The master's ``Authority`` unless the caller names another (plan D7).
AUTHORITY = "https://github.com/PNNL-CIM-Tools/CIMHub"


class Site:
    """What the orchestrator computes once and hands to the mappers: case values, region, bus zones, areas and base
    voltages, and substations."""

    def __init__(self, native, name: str):
        self.values = case_identification.case_values(native)
        self.region = mrid("rgn_", name, lowercase=True)
        self.zones = zone.bus_zones(native)
        buses = [record for record, _ in bus.filled_buses(native)]
        self.base_kv = {record.bus_number: record.base_voltage for record in buses}
        self.areas = {record.bus_number: int(record.area) for record in buses}
        self.substations = substation_groups(native, self.zones, self.values.zero_impedance_threshold)
        self.substation_of = bus.substation_of(self.substations)


#: ``(native class, mapper(native, site))`` in ``Import`` order. The phase-2 stubs return an empty document, or
#: raise when their table has records (plan 4.2).
MAPPING_ORDER = (
    (zone.NATIVE_CLASS, lambda native, site: zone.map_zone(native, site.region)),
    (area_interchange.NATIVE_CLASS, lambda native, site: area_interchange.map_area_interchange(native)),
    (bus.NATIVE_CLASS, lambda native, site: bus.map_bus(native, site.substations,
                                                        site.values.zero_impedance_threshold)),
    (branch.NATIVE_CLASS, lambda native, site: branch.map_branch(native, site.substation_of, site.base_kv,
                                                                 site.values.branch_ratings_in_current)),
    (switch.NATIVE_CLASS, lambda native, site: switch.map_switch(native, site.substation_of, site.base_kv,
                                                                 site.values.branch_ratings_in_current)),
    (multi_section_line.NATIVE_CLASS, lambda native, site: multi_section_line.map_multi_section_line(native,
                                                                                                    site.zones)),
    (load.NATIVE_CLASS, lambda native, site: load.map_load(native, site.substation_of, site.base_kv, site.areas,
                                                           site.zones)),
    (fixed_shunt.NATIVE_CLASS, lambda native, site: fixed_shunt.map_fixed_shunt(native, site.substation_of,
                                                                                site.base_kv, site.values.base_mva)),
    (switched_shunt.NATIVE_CLASS, lambda native, site: switched_shunt.map_switched_shunt(
        native, site.substation_of, site.base_kv, site.values.base_mva)),
    (two_terminal_dc.NATIVE_CLASS, lambda native, site: two_terminal_dc.map_two_terminal_dc(native)),
    (vsc_dc.NATIVE_CLASS, lambda native, site: vsc_dc.map_vsc_dc(native)),
    (impedance_correction.NATIVE_CLASS, lambda native, site: impedance_correction.map_impedance_correction(native)),
    (multi_terminal_dc.NATIVE_CLASS, lambda native, site: multi_terminal_dc.map_multi_terminal_dc(native)),
    (facts_device.NATIVE_CLASS, lambda native, site: facts_device.map_facts_device(native)),
    (gne_device.NATIVE_CLASS, lambda native, site: gne_device.map_gne_device(native)),
    (induction_machine.NATIVE_CLASS, lambda native, site: induction_machine.map_induction_machine(native)),
)

#: Classes the master reads, or that have no artifact by design (Owner: CIM 18 gap).
_HANDLED = {case_identification.NATIVE_CLASS, owner.NATIVE_CLASS} | {cls for cls, _ in MAPPING_ORDER}

#: The voltage-limit types of the busbars' limit sets: direction high/low x durationKind normal/emergency (RAW-19).
_VOLTAGE_LIMIT_TYPES = (
    ("olt_normal_high", "normal high", "normal", "true", "high"),
    ("olt_normal_low", "normal low", "normal", "true", "low"),
    ("olt_emergency_high", "emergency high", "emergency", "false", "high"),
    ("olt_emergency_low", "emergency low", "emergency", "false", "low"),
)


def _master_comment(native, site: Site, name: str) -> str:
    case = case_identification.case_record(native)
    lines = [f"PSS/E RAW case {name}: {(case.titles or [''])[0].strip()}",
             "Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#master"]
    options = [keyword.upper() for keyword in ("gauss", "newton", "adjust", "tysl", "solver")
               if getattr(case, keyword)]
    if options:
        lines.append(f"untranscribed: {', '.join(options)} (solution options)")
    if site.values.branch_ratings_units_defaulted:
        lines.append("defaulted: NXFRAT=0 (branch and switch ratings in MVA; the spec's 'present option setting')")
    owners = native.count(owner.NATIVE_CLASS)
    if owners:
        lines.append(f"untranscribed: Owner {owners} (ownership is a CIM 18 gap)")
    unmapped = sorted((cls.__name__, native.count(cls)) for cls in native.graph
                      if cls not in _HANDLED and native.count(cls))
    if unmapped:
        lines.append(textwrap.fill("not mapped: " + ", ".join(f"{cls_name} {count}" for cls_name, count in unmapped),
                                   width=116, break_long_words=False))
    return "\n".join(lines)


def map_master(native, parts: list[Document], site: Site, *, name: str, authority: str = AUTHORITY) -> Document:
    """The master: BasePower first (every later ``(pu system)`` converts on it), BaseFrequency, the case's
    GeographicalRegion, the BaseVoltages, the voltage-limit and rating-set types, then one ``Import`` per non-empty
    part."""
    values = site.values
    voltages = bus.base_voltages(native)
    statements = [
        ObjectStatement("BasePower", [(Column("mRID"), "sbase"), (Column("basePower", "MVA"), cell(values.base_mva))],
                        comment="defaulted: SBASE=100" if values.base_mva_defaulted else None),
        ObjectStatement("BaseFrequency", [(Column("mRID"), f"bf_{values.base_frequency:g}hz"),
                                          (Column("frequency", "Hz"), cell(values.base_frequency))],
                        comment=f"defaulted: BASFRQ={values.base_frequency:g}" if values.base_frequency_defaulted
                        else None),
        ObjectStatement("GeographicalRegion", [(Column("mRID"), site.region), (Column("name"), name)]),
        Table("BaseVoltage", [Column("mRID"), Column("nominalVoltage", "kV")],
              [Row([key, cell(kv)]) for key, kv in voltages.items()], comment="one per distinct BASKV"),
        Table("OperationalLimitType", [Column("mRID"), Column("name"), Column("durationKind"),
                                       Column("isInfiniteDuration"), Column("direction")],
              [Row(list(row)) for row in _VOLTAGE_LIMIT_TYPES], comment="bus voltage limits (RAW-19)"),
        rating_type_table(case_identification.case_record(native)),
        *(Import(part.name) for part in parts),
    ]
    return Document(name=name, statements=statements, profile=CIM_PROFILE, authority=authority, model=name,
                    comment=_master_comment(native, site, name))


class RawImporter(CimtblImporter):
    """A RAW v34 model to ``.cimtbl`` documents: the master and one document per mapped RAW table.

    ``name`` is the master's ``Model`` and file stem, and the name of the case's GeographicalRegion.
    """

    model_cls = BusBranchModel

    def __init__(self, name: str, *, authority: str = AUTHORITY):
        self.name = name
        self.authority = authority

    def to_cimtbl(self, model) -> DocumentSet:
        site = Site(model, self.name)
        parts = [part for part in (mapper(model, site) for _, mapper in MAPPING_ORDER) if part.statements]
        return DocumentSet(master=map_master(model, parts, site, name=self.name, authority=self.authority),
                           parts=parts)


def raw_to_cim(model, *, name: str, authority: str = AUTHORITY, network=None, artifact_dir=None):
    """A RAW model (``Raw34Reader(path).read_all()``) as a cim18v17 network, built from its written artifacts."""
    return RawImporter(name, authority=authority).to_cim(model, network=network, artifact_dir=artifact_dir)


__all__ = ["MAPPING_ORDER", "RawImporter", "map_master", "raw_to_cim"]
