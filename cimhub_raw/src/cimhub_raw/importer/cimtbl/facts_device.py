"""RAW FACTS device -> ``facts_device.cimtbl``: a shunt-only device (a STATCOM, J = 0) as a
``StaticSynchronousCompensator`` on bus I with a voltage ``RegulatingControl`` (P2-2). A series element (J != 0:
SSSC, UPFC, IPFC) raises; UPFC and IPFC have no CIM 18 class.

Mapping spec: ``cimhub_raw/docs/CIMTBL_MAPPING.md#facts-device-shunt-only-decision-p2-2``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table
from cimtopology.core.voltage import base_voltage_mrid

import cimhub_raw.schema.raw_v34.raw34_schema as schema
from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, fill_defaults, lookup, mrid, untranscribed_names
from cimhub_raw.importer.cimtbl.derived import ka_from_rating, volts_from_per_unit
from cimhub_raw.importer.cimtbl.records import listed_off_default, raw_defaults
from cimhub_raw.importer.node_breaker import NodeBreaker

NATIVE_CLASS = schema.FactsDeviceRecord
#: prefixes requested from the cimtbl-translate table owners (plan C3)
PREFIX = "fd_"
CONTROL_PREFIX = "fdc_"

#: MODE of a shunt-only device -> inService; MODE 2..8 need a series element (J != 0), which raises first
IN_SERVICE = {1: True, 0: False}
#: the series element's fields and RMPCT: CIM cannot hold them on a shunt-only device, so a value other than the
#: default is listed on the row
LISTED_SLOTS = ("pdes", "qdes", "trmx", "vtmn", "vtmx", "vsmx", "imx", "linx", "set1", "set2", "vsref", "mname",
                "rmpct")

_SERIES = "the series element's; a shunt-only device does not use it: listed on the row when not the default"
FIELDS = {
    "name": Field("structural", note="NAME: the key, mRID fd_<NAME> (control fdc_<NAME>), name NAME"),
    "ibus": Field("structural", note="I: the device's bus, BaseVoltage and EquipmentContainer (its substation)"),
    "jbus": Field("structural", note="J: 0 is a shunt-only device; nonzero (a series element: SSSC, UPFC, IPFC) "
                                     "raises"),
    "mode": Field("mapped", note="MODE: inService = (MODE == 1); 2..8 need J != 0; blank: 1 (defaulted)"),
    "pdes": Field("untranscribed", note=f"PDES: {_SERIES}"),
    "qdes": Field("untranscribed", note=f"QDES: {_SERIES}"),
    "vset": Field("derived", note="VSET (pu): the control's targetValue = VSET x BASKV(FCREG), in V "
                                  "(volts_from_per_unit); blank: 1.0 (defaulted)"),
    "shmx": Field("derived", note="SHMX (MVA at unity voltage): ratedI = SHMX / (sqrt(3) x BASKV(I)) kA "
                                  "(ka_from_rating); 0 (no shunt) stays 0; blank: 9999 (defaulted)"),
    "trmx": Field("untranscribed", note=f"TRMX: {_SERIES}"),
    "vtmn": Field("untranscribed", note=f"VTMN: {_SERIES}"),
    "vtmx": Field("untranscribed", note=f"VTMX: {_SERIES}"),
    "vsmx": Field("untranscribed", note=f"VSMX: {_SERIES}"),
    "imx": Field("untranscribed", note=f"IMX: {_SERIES}"),
    "linx": Field("untranscribed", note=f"LINX: {_SERIES}"),
    "rmpct": Field("untranscribed", note="RMPCT: a shunt's share of a coordinated voltage control has no CIM home "
                                         "(qPercent is SynchronousMachine's; CIM 18 gap); listed when not 100"),
    "owner": Field("untranscribed", note="OWNER: ownership is an asset concept (CIM 18 gap)"),
    "set1": Field("untranscribed", note=f"SET1: {_SERIES}"),
    "set2": Field("untranscribed", note=f"SET2: {_SERIES}"),
    "vsref": Field("untranscribed", note=f"VSREF: {_SERIES}"),
    "remot": Field("structural", note="FCREG: the control's Terminal bb_<FCREG>_T1, or bb_<I>_T1 when 0 (RAW-11), "
                                      "or the NREG node's busbar; blank: 0 (defaulted)"),
    "mname": Field("untranscribed", note=f"MNAME: {_SERIES}"),
    "nreg": Field("structural", note="NREG: a node of bus FCREG; nonzero: the control's Terminal is that node's "
                                     "busbar bb_s<IS>_n<NREG>_T1 (R6, RAW-11); blank: 0 (defaulted)"),
}

_PROVENANCE = """PSS/E RAW FACTS device -> StaticSynchronousCompensator (shunt only) + its voltage RegulatingControl.
Source table: FACTS device (records: {count})
Mapping: cimhub_raw/docs/CIMTBL_MAPPING.md#facts-device-shunt-only-decision-p2-2"""


def _regulated_bus(device) -> int:
    return device.remot or device.ibus


def regulated_nodes(native) -> list[tuple[int, int, str]]:
    """``(regulated bus, NREG, record id)`` of every FACTS device whose control regulates a node (R6)."""
    return [(_regulated_bus(device), device.nreg, f"FACTS device {device.name}")
            for device in native.list_by_class(NATIVE_CLASS) if device.nreg]


def map_facts_device(native, substations_by_bus: dict[int, str], base_kv_of: dict[int, float],
                     node_breaker: NodeBreaker) -> Document:
    records = sorted(native.list_by_class(NATIVE_CLASS), key=lambda device: device.name)
    if not records:
        return Document(name="facts_device", statements=[], profile=CIM_PROFILE)
    defaults = raw_defaults(NATIVE_CLASS)
    control_rows, device_rows = [], []
    for record in records:
        device, defaulted = fill_defaults(FIELDS, record, defaults)
        record_id = f"FACTS device {device.name}"
        if device.jbus:
            raise NotImplementedError(f"{record_id}: J {device.jbus}, a series element (SSSC, UPFC or IPFC; no case "
                                      "has one yet, and UPFC/IPFC have no CIM 18 class)")
        in_service = lookup(IN_SERVICE, device.mode, slot="mode", record_id=record_id)
        regulated = _regulated_bus(device)
        if regulated not in base_kv_of:
            raise ValueError(f"{record_id}: FCREG {regulated} is no bus")
        bus = device.ibus
        control = mrid(CONTROL_PREFIX, device.name)
        control_rows.append(Row([control, device.name, "voltage", "false", "true",
                                 cell(volts_from_per_unit(device.vset, base_kv_of[regulated])),
                                 node_breaker.regulated_terminal(regulated, device.nreg, record_id)]))
        notes = [note for note in (defaulted, listed_off_default(device, LISTED_SLOTS, defaults)) if note]
        device_rows.append(Row([
            mrid(PREFIX, device.name), device.name, str(bus), cell(ka_from_rating(device.shmx, base_kv_of[bus])),
            cell(in_service), "true", control, base_voltage_mrid(base_kv_of[bus]), substations_by_bus[bus]],
            comment="; ".join(notes) or None))

    statements = [
        Table("RegulatingControl", [Column(name) for name in ("mRID", "name", "mode", "discrete", "enabled",
                                                              "targetValue", "Terminal")],
              control_rows, comment="one per device; targetValue in V"),
        Table("StaticSynchronousCompensator",
              [Column("mRID"), Column("name"), Column("bus"), Column("ratedI", "kA"), Column("inService"),
               Column("controlEnabled"), Column("RegulatingControl"), Column("BaseVoltage"),
               Column("EquipmentContainer")],
              device_rows, comment=f"shunt only (J = 0); ratedI = SHMX / (sqrt(3) x BASKV)\n"
                                   f"{untranscribed_names(FIELDS)}"),
    ]
    return Document(name="facts_device", statements=statements, profile=CIM_PROFILE,
                    comment=_PROVENANCE.format(count=len(records)))
