"""GLM ``load``, ``triplex_load`` and a plain ``triplex_node``'s power -> ``load.cimtbl``, ``triplex_load.cimtbl``,
``triplex_node.cimtbl`` (S4a).

One ``EnergyConsumer`` per load on its root bus (GLM-4), on the phases that carry power (S4a-1). GLM loads are per
phase, so the consumer's p and q are the totals and, when its phase children differ, each child gets its own p and q
(``Update Table EnergyConsumerPhase``). A phase's power is its constant power, or GridLAB-D's split of
``base_power`` by the fractions and power factors at nominal voltage (S4a-3); a ``<schedule>.value*K`` base is K
(S4a-2). The voltage response is the shared ZIP row of the one kind every phase uses, else a ``zip_`` row of the
load's fractions (S4a-4). A split-phase record has the legs (1, 2: s1, s2 to neutral) and the 240 V part (12) as two
consumers (S4a-6). Explicit constant current and impedance raise (S4a-5). A record with no power is a consumer
of p = q = 0 on its wired phases, and each record is one service: ``customerCount`` 1 on its first consumer
(defaulted, GLM has no count).

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#s4a-loads-and-capacitors``.
"""

from __future__ import annotations

import math
import re
import textwrap
from typing import NamedTuple

from cimprofiles.units import units
from cimtables.document import Column, Document, Row, Table
from cimtopology.core import BusSystem

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, mrid, phases_cell, untranscribed_values
from cimhub_core.load_response import COLUMNS as RESPONSE_COLUMNS
from cimhub_core.load_response import ZIP_CONSTANT_I, ZIP_CONSTANT_PQ, ZIP_CONSTANT_Z
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.glm_schema import registry_unit
from cimhub_gridlabd.importer.cimtbl import bus
from cimhub_gridlabd.importer.cimtbl.catalog import label
from cimhub_gridlabd.importer.cimtbl.link import provenance
from cimhub_gridlabd.importer.topology import phase_letters
from cimhub_gridlabd.schema import gridlabd as schema

PREFIX = "ld_"
_WIDTH = 116  # row comment width, as cimhub_core.cimtbl
ANCHOR = "s4a-loads-and-capacitors"

_CONSUMER = "EnergyConsumer"
KINDS = ("power", "current", "impedance")
#: one kind -> the shared core row (``zip_fractions.cimtbl``)
SHARED_RESPONSE = {"power": ZIP_CONSTANT_PQ, "current": ZIP_CONSTANT_I, "impedance": ZIP_CONSTANT_Z}
#: a delta load's A/B/C are the branches AB/BC/CA (node.cpp:2535); the binder names a branch child by its PhaseCode
DELTA_BRANCH = {"A": "AB", "B": "BC", "C": "AC"}
#: ``<schedule>.value*<number>``: a base scaled by a schedule (S4a-2)
SCHEDULED = re.compile(r"^\s*([A-Za-z_][\w.:-]*)\.value\s*\*\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$")

#: An explicit current, impedance or connection form: raises when set (S4a-5, ``check``).
NOT_MAPPED = Field("structural", note="raises when set: no deck sets it, so a mapping waits for one (S4a-5)")
_ZIP_NOTE = ("GridLAB-D's split at nominal voltage (S4a-3): P = base x fraction x |pf|, Q = P x sqrt(1/pf^2 - 1), "
             "negative on a negative pf; pf 0 is all Q")


class LoadClass(NamedTuple):
    """One native load class: its phase suffixes and the slot that holds a phase's constant power."""
    native: type
    artifact: str
    suffixes: tuple[str, ...]
    power: str  # the constant power slot, "{suffix}" filled
    has_base: bool  # base_power + fractions (load, triplex_load; a plain triplex_node has none)


LOAD = LoadClass(schema.Load, "load", ("A", "B", "C"), "constant_power_{}", True)
TRIPLEX_LOAD = LoadClass(schema.TriplexLoad, "triplex_load", ("1", "2", "12"), "constant_power_{}", True)
TRIPLEX_NODE = LoadClass(schema.TriplexNode, "triplex_node", ("1", "2", "12"), "power_{}", False)
LOAD_CLASSES = (LOAD, TRIPLEX_LOAD, TRIPLEX_NODE)


def _own_fields(load_class: LoadClass) -> dict[str, Field]:
    """The load slots of a load or triplex_load (a plain triplex_node's are bus.py's)."""
    fields = {
        "load_class": Field("untranscribed", note="for sorting only (load.cpp:518)"),
        "load_priority": Field("untranscribed", note="read by nothing in powerflow"),
        "measured_power": Field("untranscribed", note="solver output"),
    }
    for suffix in load_class.suffixes:
        fields[f"constant_power_{suffix}"] = Field("copied", ((_CONSUMER, "p", "VA"), (_CONSUMER, "q", "VA")),
                                                   "the phase's p + jq, VA via pint; with base_power_X raises")
        fields[f"base_power_{suffix}"] = Field("derived", note=_ZIP_NOTE + "; <schedule>.value*K is K (S4a-2)")
        for kind in KINDS:
            fields[f"{kind}_fraction_{suffix}"] = Field("derived", note="with base_power; default 0, the power "
                                                                        "fraction 1 - I - Z when they don't sum to 1")
            fields[f"{kind}_pf_{suffix}"] = Field("derived", note="with base_power; default 1")
        for part in ("_real", "_reac"):
            fields[f"constant_power_{suffix}{part}"] = NOT_MAPPED
        for kind in ("current", "impedance"):
            for part in ("", "_real", "_reac"):
                fields[f"constant_{kind}_{suffix}{part}"] = NOT_MAPPED
    explicit = ("AN", "BN", "CN", "AB", "BC", "CA") if load_class is LOAD else ()
    for connection in explicit:
        for kind in KINDS:
            for part in ("", "_real", "_reac"):
                fields[f"constant_{kind}_{connection}{part}"] = NOT_MAPPED
    for slot in ("measured_voltage_", "measured_power_", "indiv_measured_power_"):
        for suffix in (*load_class.suffixes, "AB", "BC", "CA"):
            fields[f"{slot}{suffix}"] = Field("untranscribed", note="solver output")
    fields.update({slot: Field("untranscribed", note="engine option") for slot in (
        "phase_loss_protection", "inrush_integration_method_capacitance", "inrush_integration_method_inductance")})
    return fields


#: Each device class's own slots (its row comments list their untranscribed values); its bus slots are counted on the
#: table comment.
OWN = {load_class.native: {slot: field for slot, field in _own_fields(load_class).items()
                           if slot in load_class.native.__dataclass_fields__} for load_class in (LOAD, TRIPLEX_LOAD)}
FIELDS = {native: bus.classify(native, own) for native, own in OWN.items()}

#: The slots whose expression the mapper reads (``check_expressions`` lets them through): a scheduled base.
EXPRESSION_SLOTS = {load_class.native: {f"base_power_{suffix}" for suffix in load_class.suffixes}
                    for load_class in (LOAD, TRIPLEX_LOAD)}


# -- one phase's power -------------------------------------------------------------------------------------------

def _va(model: GlmModel, record, slot: str) -> complex:
    """``slot`` (a complex power) in VA, from the unit it is written in."""
    value = getattr(record, slot)
    factor = units.Quantity(1.0, registry_unit(model.unit(record, slot))).to("VA").magnitude
    return complex(value.real, value.imag) * factor


def scheduled_base(model: GlmModel, record, slot: str) -> tuple[float | None, str | None]:
    """``(base VA, the schedule reference)`` of a ``base_power`` slot: as written, or K of ``<schedule>.value*K``
    (S4a-2); any other expression raises."""
    text = model.expressions.get((str(record.name), slot))
    unit = registry_unit(model.unit(record, slot))
    if text is None:
        value = getattr(record, slot)
        return (None, None) if value is None else (units.Quantity(float(value), unit).to("VA").magnitude, None)
    match = SCHEDULED.match(text)
    if match is None:
        raise ValueError(f"{label(record)}: {slot} is the expression {text!r}; only <schedule>.value*<number> is "
                         "mapped (S4a-2)")
    return units.Quantity(float(match.group(2)), unit).to("VA").magnitude, match.group(1)


def zip_split(base: float, fractions: dict[str, float], factors: dict[str, float]) -> tuple[dict[str, complex], bool]:
    """``({kind: S at nominal voltage}, repaired)``: GridLAB-D's split of ``base`` (VA) by the fractions and power
    factors (``load.cpp:945-983``). When the fractions don't sum to 1 the power fraction becomes 1 - I - Z."""
    fractions = dict(fractions)
    repaired = not math.isclose(sum(fractions.values()), 1.0)
    if repaired:
        fractions["power"] = 1.0 - fractions["current"] - fractions["impedance"]
    parts = {}
    for kind in KINDS:
        fraction, pf = fractions[kind], factors[kind]
        if fraction == 0:
            continue
        if pf == 0:
            parts[kind] = complex(0.0, base * fraction)
            continue
        p = base * fraction * abs(pf)
        q = p * math.sqrt(1 / pf ** 2 - 1)
        parts[kind] = complex(p, -q if pf < 0 else q)
    return parts, repaired


class _Phase(NamedTuple):
    parts: dict[str, complex]  # kind -> S (VA)
    scheduled: str | None = None  # "base_power_A=ieeezipload.value*19723.08" (S4a-2)
    repaired: str | None = None  # "power_fraction_A=0.4": GridLAB-D's repair of fractions that don't sum to 1

    @property
    def total(self) -> complex:
        return sum(self.parts.values(), 0j)


def phase_power(model: GlmModel, record, load_class: LoadClass, suffix: str) -> _Phase | None:
    """One phase's (leg's) power by kind, or None when nothing is set on it."""
    power_slot = load_class.power.format(suffix)
    explicit = getattr(record, power_slot)
    base, schedule = scheduled_base(model, record, f"base_power_{suffix}") if load_class.has_base else (None, None)
    if base is not None and base != 0:
        if explicit is not None:
            raise ValueError(f"{label(record)}: base_power_{suffix} and {power_slot} are both set; GridLAB-D keeps "
                             "only the base form (load.cpp:984)")
        fractions = {kind: float(getattr(record, f"{kind}_fraction_{suffix}") or 0.0) for kind in KINDS}
        factors = {kind: float(1.0 if getattr(record, f"{kind}_pf_{suffix}") is None
                               else getattr(record, f"{kind}_pf_{suffix}")) for kind in KINDS}
        parts, repaired = zip_split(base, fractions, factors)
        return _Phase(parts,
                      None if schedule is None else f"base_power_{suffix}={schedule}.value*{cell(base)}",
                      f"power_fraction_{suffix}={cell(1.0 - fractions['current'] - fractions['impedance'])}"
                      if repaired else None)
    if explicit is None:
        return None
    return _Phase({"power": _va(model, record, power_slot)})


# -- the consumer --------------------------------------------------------------------------------------------------

class Consumer(NamedTuple):
    """One EnergyConsumer: mRID suffix, connection, and its phase children's power by binder child key."""
    suffix: str
    phases: str  # the consumer's phases cell before the balanced rule
    delta: bool
    children: dict[str, _Phase]  # binder child suffix (A, AB, s1, s12) -> power


def check(record, own: dict[str, Field]) -> None:
    """The explicit current, impedance and connection forms raise (S4a-5)."""
    for slot, field in own.items():
        if field is NOT_MAPPED and getattr(record, slot) is not None:
            raise ValueError(f"{label(record)}: {slot} {getattr(record, slot)}; not mapped (S4a-5)")


def consumers(model: GlmModel, record, load_class: LoadClass) -> list[Consumer]:
    """The record's consumers: a load's one; a split-phase record's legs and its 240 V part (S4a-6); one of no power
    when no phase carries any (``_powerless``)."""
    powers = {suffix: phase_power(model, record, load_class, suffix) for suffix in load_class.suffixes}
    carrying = {suffix: phase for suffix, phase in powers.items() if phase is not None and phase.total != 0}
    written = str(record.phases or "")
    if load_class is LOAD and "S" in written:
        raise ValueError(f"{label(record)}: phases {written}; a split-phase load is a triplex_load")
    if not carrying:
        return [_powerless(record, load_class)]
    if load_class is LOAD:
        if "D" in written:
            phases = "".join(sorted({letter for suffix in carrying for letter in DELTA_BRANCH[suffix]}))
            by_branch = {DELTA_BRANCH[suffix]: phase for suffix, phase in carrying.items()}
            children = {branch: by_branch.get(branch, _Phase({})) for branch in sorted(_delta_children(phases))}
            return [Consumer("", phases, True, children)]
        return [Consumer("", "".join(carrying), False, dict(carrying))]
    result = []
    legs = {f"s{suffix}": carrying[suffix] for suffix in ("1", "2") if suffix in carrying}
    if legs:
        result.append(Consumer("", "".join(legs), False, legs))
    if "12" in carrying:
        result.append(Consumer("_12", "s1s2", True, {"s12": carrying["12"]}))
    return result


def _powerless(record, load_class: LoadClass) -> Consumer:
    """A record with no power on any phase is still a consumer (a service, counted by ``customerCount``): p = q = 0
    on its wired phases, a split-phase record on its legs."""
    if load_class is not LOAD:
        return Consumer("", "s1s2", False, {"s1": _Phase({}), "s2": _Phase({})})
    letters = "".join(sorted(phase_letters(record)))
    if "D" in str(record.phases):
        return Consumer("", letters, True, {branch: _Phase({}) for branch in sorted(_delta_children(letters))})
    return Consumer("", letters, False, {letter: _Phase({}) for letter in letters})


def _delta_children(phases: str) -> set[str]:
    """The branch PhaseCodes the binder makes on a delta consumer of ``phases`` (``connectivity.phase_plan``)."""
    following = {"A": "B", "B": "C", "C": "A"}
    return {"".join(sorted(letter + following[letter])) for letter in phases if following[letter] in phases}


def response(consumer_list: list[Consumer]) -> tuple[str, tuple[float, ...] | None]:
    """``(LoadResponse mRID, the zip_ row's six fractions or None)`` from the totals of the parts (S4a-4)."""
    totals = {kind: sum((phase.parts.get(kind, 0j) for consumer in consumer_list
                         for phase in consumer.children.values()), 0j) for kind in KINDS}
    used = [kind for kind in KINDS if totals[kind] != 0]
    if not used:
        return ZIP_CONSTANT_PQ, None  # no power: nothing responds to the voltage
    if len(used) == 1:
        return SHARED_RESPONSE[used[0]], None
    p_total = sum(total.real for total in totals.values())
    q_total = sum(total.imag for total in totals.values())
    p = [totals[kind].real / p_total if p_total else None for kind in KINDS]
    q = [totals[kind].imag / q_total if q_total else None for kind in KINDS]
    p = p if p_total else q
    q = q if q_total else p
    fractions = (*p, *q)
    return "zip_" + "_".join(f"{round(fraction, 6):g}" for fraction in fractions), fractions


def _notes(found: list[Consumer]) -> list[str]:
    """The record's scheduled bases (S4a-2) and repaired fractions (S4a-3), one line each."""
    phases = [phase for consumer in found for phase in consumer.children.values()]
    scheduled = [phase.scheduled for phase in phases if phase.scheduled]
    repaired = [phase.repaired for phase in phases if phase.repaired]
    notes = []
    if scheduled:
        notes.append(f"scheduled: {', '.join(scheduled)}; the base is mapped, the schedule is not (S4a-2, TODO)")
    if repaired:
        notes.append(f"defaulted: {', '.join(repaired)} (the fractions did not sum to 1: GridLAB-D's repair, "
                     "load.cpp:945)")
    return [textwrap.fill(note, width=_WIDTH, break_long_words=False, break_on_hyphens=False) for note in notes]


def _equal(consumer: Consumer) -> bool:
    """One phase child, or children with the same power: no per-phase rows; the consumer's total is the value (the
    load getter splits it evenly over the conductors, and one delta branch or the 240 V part is the whole load)."""
    return len({phase.total for phase in consumer.children.values()}) == 1


# -- the documents ---------------------------------------------------------------------------------------------------

def map_loads(model: GlmModel, load_class: LoadClass, roots: dict[str, str], buses: dict[str, BusSystem],
              feeder: str) -> Document:
    """One load class as one document: its zip_ rows, the consumers, then the phase children's values."""
    records = [record for record in model.list_by_class(load_class.native) if type(record) is load_class.native]
    if load_class is TRIPLEX_NODE:
        records = [record for record in records
                   if any(getattr(record, f"power_{suffix}") is not None for suffix in load_class.suffixes)]
    if not records:
        return Document(name=load_class.artifact, statements=[], profile=CIM_PROFILE)
    own = OWN.get(load_class.native, {})
    consumer_rows, phase_rows, responses, powerless = [], [], {}, []
    for record in records:
        check(record, own)
        found = consumers(model, record, load_class)
        if not any(phase.total for consumer in found for phase in consumer.children.values()):
            powerless.append(str(record.name))
        load_response, fractions = response(found)
        if fractions is not None:
            if responses.setdefault(load_response, fractions) != fractions:
                raise ValueError(f"{label(record)}: its ZIP fractions {fractions} differ from another load's beyond "
                                 f"the 6 places of {load_response}")
        node = roots[str(record.name)]
        comment = "\n".join(part for part in (*_notes(found), untranscribed_values(own, record)) if part) or None
        for index, consumer in enumerate(found):
            name = f"{record.name}{consumer.suffix}"
            consumer_mrid = mrid(PREFIX, name)
            total = sum((phase.total for phase in consumer.children.values()), 0j)
            balanced = _equal(consumer)
            phases = phases_cell(consumer.phases) if balanced else consumer.phases
            customers = cell(1) if index == 0 else None  # one service per record, counted once
            consumer_rows.append(Row([consumer_mrid, name, node, phases, "D" if consumer.delta else "Y",
                                      cell(not consumer.delta), cell(total.real), cell(total.imag), customers,
                                      load_response, buses[node].base_voltage],
                                     comment=comment if index == 0 else None))  # the record's notes, once
            if not balanced:
                for child, phase in consumer.children.items():
                    phase_rows.append(Row([f"{consumer_mrid}_{child}", cell(phase.total.real),
                                           cell(phase.total.imag)]))
    statements = []
    header = provenance(load_class.native.class_name, "EnergyConsumer (+ EnergyConsumerPhase values)", len(records),
                        ANCHOR)
    if powerless:
        header += "\n" + textwrap.fill(f"no power on any phase (a consumer of p = q = 0): {', '.join(powerless)}",
                                        width=_WIDTH, break_long_words=False)
    if not consumer_rows:
        return Document(name=load_class.artifact, statements=[], profile=CIM_PROFILE)
    if responses:
        statements.append(Table("LoadResponseCharacteristic", [Column(name) for name in RESPONSE_COLUMNS],
                                [Row([mrid_, "false", *(cell(value) for value in fractions)])
                                 for mrid_, fractions in sorted(responses.items())],
                                comment="the loads' own ZIP fractions of P and Q (S4a-4)"))
    fields = FIELDS.get(load_class.native, bus.FIELDS.get(load_class.native))
    counted = bus.untranscribed_set(model, records, {load_class.native: bus.inherited(fields, own)})
    statements.append(Table(_CONSUMER, [Column("mRID"), Column("name"), Column("node"), Column("phases"),
                                        Column("phaseConnection"), Column("grounded"), Column("p", "W"),
                                        Column("q", "VAr"), Column("customerCount"), Column("LoadResponse"),
                                        Column("BaseVoltage"),
                                        Column("EquipmentContainer", default=feeder)], consumer_rows,
                            comment="\n".join(part for part in (
                                "p, q: the totals at nominal voltage, consumption positive; phases: the phases that "
                                "carry power, blank when ABC and equal (S4a-1)",
                                "defaulted: customerCount=1 on each record's first consumer (GLM has no customer "
                                "count; a record is one service, its 240 V part not counted again)", counted)
                                if part)))
    if phase_rows:
        statements.append(Table("EnergyConsumerPhase", [Column("mRID"), Column("p", "W"), Column("q", "VAr")],
                                phase_rows, update=True, comment="the phases differ, so each child carries its own "
                                                                 "p, q (a delta child is its branch)"))
    return Document(name=load_class.artifact, statements=statements, profile=CIM_PROFILE, comment=header)
