"""GLM ``switch``, ``fuse``, ``recloser``, ``sectionalizer`` -> one ``.cimtbl`` each: ``LoadBreakSwitch``, ``Fuse``,
``Recloser``, ``Sectionaliser`` (S3a).

GLM gives a device one state, ``status``: it is ``open`` and ``normalOpen`` (S3a-6). A per-phase state that differs
from it on one of the device's phases raises: no deck has one, and CIM would need ``SwitchPhase`` rows. The
``phases`` cell is the switched conductors, N dropped, blank when ABC (S3a-7). An open device between laterals on
different phases takes ``phaseSide1`` (its switched conductors) and ``phaseSide2`` (its to end's) instead
(``topology.crossed_phases``, S6-9). A fuse's ``current_limit`` is its
``ratedCurrent`` (S3a-8); the device's own ratings go on its own ``OperationalLimitSet`` (S3a-5). Impedance
stand-ins, reliability data and reclosing settings are untranscribed (S3a-9). A ``sectionalizer`` adds no slots to
``switch`` and maps as one (S3a-10).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s3a-lines-and-switches``.
"""

from __future__ import annotations

from cimtables.document import Column, Document, Row, Table

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, phases_cell, untranscribed_values
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl.catalog import label, native_name
from cimhub_gridlabd.importer.cimtbl.link import Limits, classify, ends, link_ratings, provenance
from cimhub_gridlabd.importer.topology import crossed_phases
from cimhub_gridlabd.schema import gridlabd as schema

PREFIX = "sw_"

_STAND_IN = Field("untranscribed", note="GridLAB-D's numerical stand-in for a closed device (as DSS-8)")
_RELIABILITY = Field("untranscribed", note="reliability data")
_PHASE_STATE = Field("structural", note="on the device's phases must equal status, else raises (S3a-6); on a "
                                        "phase it lacks, listed on the row")


def _own(cim_class: str) -> dict[str, Field]:
    return {
        "name": Field("copied", ((cim_class, "name", None),), "mRID = sw_ + name"),
        "phases": Field("structural", note="the switched conductors A, B, C, N dropped; ABC is blank (S3a-7)"),
        "status": Field("structural", note="open and normalOpen (OPEN = true); unset: GridLAB-D's CLOSED, "
                                           "defaulted (S3a-6)"),
    }


_SWITCH_OWN = {
    **{f"phase_{letter}_state": _PHASE_STATE for letter in "ABC"},
    "operating_mode": Field("untranscribed", note="with every phase state equal to status, BANKED and INDIVIDUAL "
                                                  "operate the same (switch_object.cpp:308)"),
    "switch_impedance": _STAND_IN,
    "switch_resistance": _STAND_IN,
    "switch_reactance": _STAND_IN,
}

SWITCH_FIELDS = classify(schema.Switch, {**_own("LoadBreakSwitch"), **_SWITCH_OWN})
RECLOSER_FIELDS = classify(schema.Recloser, {
    **_own("Recloser"), **_SWITCH_OWN,
    "retry_time": Field("untranscribed", note="protection setting; home RecloseSequence, which waits for the "
                                              "protection model (DSS-11, U15)"),
    "max_number_of_tries": Field("untranscribed", note="protection setting; see retry_time"),
    "number_of_tries": Field("untranscribed", note="state"),
})
SECTIONALIZER_FIELDS = classify(schema.Sectionalizer, {**_own("Sectionaliser"), **_SWITCH_OWN})
FUSE_FIELDS = classify(schema.Fuse, {
    **_own("Fuse"),
    **{f"phase_{letter}_status": Field("structural", note="unset or GOOD; BLOWN raises on a phase the fuse has "
                                                          "(S3a-6)") for letter in "ABC"},
    "current_limit": Field("copied", (("Fuse", "ratedCurrent", "{unit}"),),
                           "S3a-8; unset: GridLAB-D's 9999 A (fuse.cpp:119) is not filled, the row says so"),
    "repair_dist_type": _RELIABILITY,
    "mean_replacement_time": _RELIABILITY,
    "fuse_resistance": _STAND_IN,
})

#: ``(native class, CIM class, FIELDS)`` per switching artifact, in Import order.
SWITCHES = (
    (schema.Switch, "LoadBreakSwitch", SWITCH_FIELDS),
    (schema.Fuse, "Fuse", FUSE_FIELDS),
    (schema.Recloser, "Recloser", RECLOSER_FIELDS),
    (schema.Sectionalizer, "Sectionaliser", SECTIONALIZER_FIELDS),
)
FIELDS = {native_class: fields for native_class, _, fields in SWITCHES}
_CIM_CLASS = {native_class: cim_class for native_class, cim_class, _ in SWITCHES}


def _phases(device) -> str:
    """The device's switched conductors in ABC order (S3a-7)."""
    written = str(device.phases) if device.phases is not None else ""
    unknown = set(written) - set("ABCN")
    switched = "".join(letter for letter in "ABC" if letter in written)
    if unknown or not switched:
        raise ValueError(f"{label(device)}: phases {device.phases or 'unset'}; A, B, C (and N) are mapped")
    return switched


def _is_open(device, switched: str) -> tuple[bool, list[str]]:
    """``(open, notes)`` from ``status``; a per-phase state on one of the device's phases that differs raises
    (S3a-6). The notes list the defaulted status and the states on phases the device lacks."""
    notes = []
    if device.status is None:
        notes.append("defaulted: status=CLOSED")
    is_open = str(device.status) == "OPEN"
    fuse = isinstance(device, schema.Fuse)
    lacking = []
    for letter in "ABC":
        slot = f"phase_{letter}_status" if fuse else f"phase_{letter}_state"
        value = getattr(device, slot)
        if value is None:
            continue
        if letter not in switched:
            lacking.append(f"{native_name(device, slot)}={value}")
        elif fuse and str(value) == "BLOWN":
            raise ValueError(f"{label(device)}: {native_name(device, slot)} BLOWN; a per-phase state is not "
                             "mapped (S3a-6)")
        elif not fuse and (str(value) == "OPEN") != is_open:
            raise ValueError(f"{label(device)}: {native_name(device, slot)} {value} but status "
                             f"{device.status or 'CLOSED'}; a per-phase state is not mapped (S3a-6)")
    if lacking:
        notes.append(f"untranscribed (a phase it lacks): {', '.join(lacking)}")
    return is_open, notes


def _row(model: GlmModel, device, roots: dict[str, str], buses) -> tuple[tuple[Column, ...], Row]:
    switched = _phases(device)
    is_open, notes = _is_open(device, switched)
    node1, node2, bus = ends(device, roots, buses)
    columns = [Column("mRID"), Column("name"), Column("node1"), Column("node2")]
    cells = [mrid(PREFIX, device.name), str(device.name), node1, node2]
    far = crossed_phases(model, device)
    if far is None:
        columns.append(Column("phases"))
        cells.append(phases_cell(switched))
    else:
        columns += [Column("phaseSide1"), Column("phaseSide2")]
        cells += [switched, far]
        notes.append(f"an open tie between laterals on different phases ({switched} to {far}); GridLAB-D cannot load "
                     "it (link.cpp:649), S6-9")
    if isinstance(device, schema.Fuse):
        columns.append(Column("ratedCurrent", registry_unit(model.unit(device, "current_limit"))))
        cells.append(cell(device.current_limit))
        if device.current_limit is None:
            notes.append("not filled (S3a-8): current_limit")
    columns += [Column("open"), Column("normalOpen"), Column("BaseVoltage")]
    cells += [cell(is_open), cell(is_open), bus.base_voltage]
    untranscribed = untranscribed_values(FIELDS[type(device)], device)
    if untranscribed:
        notes.append(untranscribed)
    return tuple(columns), Row(cells, comment="\n".join(notes) or None)


def map_switches(model: GlmModel, native_class: type, roots: dict[str, str], buses, feeder: str) -> Document:
    """Every device of one GLM switching class as one document: the devices, then their limit sets."""
    devices = model.list_by_class(native_class)
    cim_class = _CIM_CLASS[native_class]
    by_columns: dict[tuple[Column, ...], list[Row]] = {}
    limits = Limits()
    for device in devices:
        columns, row = _row(model, device, roots, buses)
        by_columns.setdefault(columns, []).append(row)
        limits.add(mrid(PREFIX, device.name), link_ratings(device))
    statements = [Table(cim_class, [*columns, Column("EquipmentContainer", default=feeder)], rows)
                  for columns, rows in by_columns.items()]
    return Document(name=native_class.class_name, statements=[*statements, *limits.tables()], profile=CIM_PROFILE,
                    comment=provenance(native_class.class_name, cim_class, len(devices)) if devices else None)
