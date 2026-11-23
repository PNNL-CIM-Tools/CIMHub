"""GLM buses -> ``bus.cimtbl`` (ConnectivityNodes) and ``source.cimtbl`` (EnergySources): the S1 field
classification (I3).

A bus is any ``node`` or ``triplex_node`` subclass. Each class's ``FIELDS`` names every slot: the few that carry
model data explicitly, the rest in untranscribed groups, each with its reason. ``classify`` raises on a slot no group
claims, so a schema regeneration that adds one fails here instead of disappearing.

Mapping spec: ``cimhub_gridlabd/docs/CIMTBL_MAPPING.md#buses`` and ``#source``.
"""

from __future__ import annotations

import cmath
import math
import textwrap
from collections import Counter, defaultdict

from cimprofiles.units import units
from cimtables.document import Column, Document, ObjectStatement, Row, Table
from cimtopology.core import BusSystem, nominal_kv

from cimhub_core.cimtbl import CIM_PROFILE, Field, cell, field_names, mrid, phases_cell
from cimhub_gridlabd.glm_reader import GlmModel
from cimhub_gridlabd.importer.topology import bus_records, line_voltage, phase_letters, swing_buses
from cimhub_gridlabd.schema import gridlabd as schema

#: The classes S1 classifies in full. Other bus classes (load, capacitor, triplex_load, ...) still get a
#: ConnectivityNode when they are a root bus; their own slots are classified by their slices.
NATIVE_CLASSES = (schema.Node, schema.Meter, schema.Substation, schema.TriplexNode, schema.TriplexMeter)

_COMMON = {
    "name": Field("copied", (("ConnectivityNode", "mRID", None), ("ConnectivityNode", "name", None)),
                  note="root buses only; a child bus is its root's node (GLM-4)"),
    "parent": Field("structural", note="a bus whose parent is a bus is solved as the root of its parent chain: no "
                                       "node of its own; its name is listed on the root's row (GLM-4)"),
    "phases": Field("structural", note="a child's phase conductors must be a subset of its root's; on a swing bus, "
                                       "EnergySource.phases (blank when ABC)"),
    "nominal_voltage": Field("structural", note="checked against the walk's kV on the bus's system (line_voltage); a "
                                                "disagreement over 10 % is listed in bus.cimtbl, not written (GLM-1). "
                                                "On a swing bus: EnergySource.nominalVoltage, derived by line_voltage"),
    "bustype": Field("structural", note="SWING: an EnergySource row (source.cimtbl). PQ, PV, SWING_PQ: a plain bus. "
                                        "SWING_PQ only turns into a swing when islanded"),
}

#: ``(note, exact names, name prefixes)``: the untranscribed groups; an exact name wins over a prefix. Every
#: other slot must be explicit.
_GROUPS = (
    ("object metadata with no network-profile home", (
        "groupid", "rank", "flags", "in_svc", "out_svc", "condition", "solution", "service_status",
        "service_status_double", "previous_uptime", "current_uptime", "busflags", "reference_bus",
        "topological_parent", "NR_powerflow_parent", "house_present", "maximum_voltage_error",
        "reset_disabled_island_state", "behaving_as_swing"), ()),
    ("home: the location shape (EquipmentLocation); mapped when a deck sets it", ("latitude", "longitude"), ()),
    ("reliability data", ("mean_repair_time",), ()),
    ("dynamics (deltamode, PLL, frequency measurement, grid-friendly appliance trips)", (
        "inrush_integration_method", "Norton_dynamic", "Norton_dynamic_child", "generator_dynamic",
        "frequency_measure_type", "pll_Ki", "pll_Kp", "sfm_Tf"), ("deltamode_", "GFA_")),
    ("solver state and outputs: the initial guess and the solution, not the network",
     ("voltage_AB", "voltage_BC", "voltage_CA", "voltage_12", "voltage_1N", "voltage_2N"),
     ("measured_", "prerotated_current_", "residential_nominal_current_", "indiv_measured_", "distribution_")),
    ("metering and billing", (
        "bill_day", "bill_mode", "customer_interrupted", "customer_interrupted_secondary", "meter_power_consumption",
        "momentary_count", "monthly_bill", "monthly_energy", "monthly_fee", "power_market", "pre_load",
        "previous_monthly_bill", "previous_monthly_energy", "price", "price_base", "s_flag", "sustained_count",
        "t_flag", "total_count"), ("first_tier_", "second_tier_", "third_tier_")),
    ("substation transmission interface (co-simulation with a transmission solver)",
     ("transmission_level_constant_current_load", "transmission_level_constant_impedance_load",
      "transmission_level_constant_power_load"), ()),
    ("solver setting", ("power_convergence_value",), ()),
)

#: A bus's own load accumulators (``power_X``, ``current_X``, ``shunt_X``): no deck sets them on a bus that is not a
#: plain ``triplex_node``, so they raise when set (S4a-7, ``check_bus_loads``).
BUS_LOAD_PREFIXES = ("power_", "current_", "shunt_", "current_inj_")
BUS_LOAD = Field("structural", note="a load on the bus itself: raises when set (S4a-7); a plain triplex_node's "
                                    "power_1/_2/_12 are triplex_node.cimtbl's")
_TRIPLEX_POWER = Field("copied", (("EnergyConsumer", "p", "{unit}"), ("EnergyConsumer", "q", "{unit}")),
                       note="a plain triplex_node's constant power: legs 1, 2 -> s1, s2; 12 -> the 240 V consumer "
                            "(S4a-6, triplex_node.cimtbl)")
_NOT_A_LOAD = {f"power_{leg}": BUS_LOAD for leg in ("1", "2", "12")}

_SWING_VOLTAGE = Field("derived", note="on a SWING bus only: EnergySource voltageMagnitude = line_voltage(|V|) and "
                                       "voltageAngle = arg(V) in degrees (a polar V's as written); elsewhere the "
                                       "solver's initial guess")
_INITIAL_GUESS = Field("untranscribed", note="the solver's initial guess")

_BY_CLASS = {
    schema.Node: {"voltage_A": _SWING_VOLTAGE, "voltage_B": _INITIAL_GUESS, "voltage_C": _INITIAL_GUESS},
    schema.Substation: {
        "positive_sequence_voltage": Field("derived", note="EnergySource voltageMagnitude = line_voltage(|V|), "
                                                           "voltageAngle = arg(V) in degrees (a polar V's as "
                                                           "written); else voltage_A"),
        "reference_phase": Field("structural", note="the phase the angle refers to: unset or PHASE_A, else raises"),
        "base_power": Field("copied", (("BasePower", "basePower", "{unit}"),),
                            note="the system base (cimtables BasePower), in its written unit"),
        "negative_sequence_voltage": Field("untranscribed", note="solver output"),
        "zero_sequence_voltage": Field("untranscribed", note="solver output"),
    },
    schema.TriplexNode: {"voltage_1": _SWING_VOLTAGE, "voltage_2": _INITIAL_GUESS, "voltage_N": _INITIAL_GUESS,
                         **{f"power_{leg}": _TRIPLEX_POWER for leg in ("1", "2", "12")}},
    schema.TriplexMeter: _NOT_A_LOAD,
    schema.TriplexLoad: _NOT_A_LOAD,
}


def classify(native_cls: type, own: dict[str, Field] | None = None) -> dict[str, Field]:
    """``FIELDS`` of one bus class: the common and class rows, ``own`` (a device's slots: a load's, a
    capacitor's), the bus load accumulators (``BUS_LOAD``), then the untranscribed groups. Raises on a slot nothing
    claims."""
    fields: dict[str, Field] = {}
    for klass in reversed(native_cls.__mro__):
        fields.update({slot: field for slot, field in _BY_CLASS.get(klass, {}).items()})
    fields = {**_COMMON, **fields, **(own or {})}
    for slot in field_names(native_cls):
        if slot in fields:
            continue
        if slot.startswith(BUS_LOAD_PREFIXES) and slot not in _EXACT_NAMES:
            fields[slot] = BUS_LOAD
            continue
        note = next((note for note, names, _ in _GROUPS if slot in names), None)  # an exact name wins
        if note is None:
            note = next((note for note, _, prefixes in _GROUPS if slot.startswith(prefixes)), None)
        if note is None:
            raise ValueError(f"{native_cls.__name__}.{slot} is not classified (importer/cimtbl/bus.py)")
        fields[slot] = Field("untranscribed", note=note)
    return {slot: fields[slot] for slot in field_names(native_cls)}


_EXACT_NAMES = {name for _, names, _ in _GROUPS for name in names}


def inherited(fields: dict[str, Field], own: dict[str, Field]) -> dict[str, Field]:
    """A device's bus slots: ``fields`` without its ``own`` (its row comments list those)."""
    return {slot: field for slot, field in fields.items() if slot not in own}

FIELDS = {native_cls: classify(native_cls) for native_cls in NATIVE_CLASSES}


def check_bus_loads(model: GlmModel, classified: dict[type, dict[str, Field]]) -> None:
    """Raise on a bus's own load accumulator that is set (``BUS_LOAD``, S4a-7)."""
    for name, record in sorted(bus_records(model).items()):
        fields = classified.get(type(record), {})
        for slot, field in fields.items():
            if field is BUS_LOAD and getattr(record, slot) is not None:
                raise ValueError(f"{record.class_name} {name}: {slot} {getattr(record, slot)} is a load on the bus "
                                 "itself; not mapped (S4a-7)")


# ---------------------------------------------------------------------------
# bus.cimtbl
# ---------------------------------------------------------------------------

#: How far a bus object's ``nominal_voltage`` may sit from the walk's kV before it is listed (GLM-1).
NOMINAL_TOLERANCE = 0.1
_WIDTH = 116


def _wrap(text: str) -> str:
    return textwrap.fill(text, width=_WIDTH, break_long_words=False, break_on_hyphens=False)


def _check_children(records: dict, roots: dict[str, str]) -> dict[str, list[str]]:
    """Root -> its child bus objects, sorted; a child on a phase its root lacks raises (GLM-4)."""
    children: dict[str, list[str]] = defaultdict(list)
    for name, root in sorted(roots.items()):
        if name == root:
            continue
        child, parent = records[name], records[root]
        if not phase_letters(child) <= phase_letters(parent):
            raise ValueError(f"{child.class_name} {name}: phases {child.phases} are not all on its root bus "
                             f"{parent.class_name} {root} ({parent.phases})")
        children[root].append(name)
    return children


def _disagreement(model: GlmModel, record, bus: BusSystem) -> str | None:
    """How a bus object's ``nominal_voltage`` disagrees with the walk (``480.0 V (0.8314 kV 3-phase) on bv_480v``)
    when it is more than ``NOMINAL_TOLERANCE`` from the walk's kV on the walk's system, else ``None``."""
    if (str(record.name), "nominal_voltage") in model.expressions:
        raise ValueError(f"{record.class_name} {record.name}: nominal_voltage is the expression "
                         f"{model.expressions[(str(record.name), 'nominal_voltage')]!r}")
    if record.nominal_voltage is None:
        return "unset"
    unit = model.unit(record, "nominal_voltage")
    own_kv = line_voltage(units.Quantity(record.nominal_voltage, unit).to("kV").magnitude, bus.system)
    if abs(own_kv - bus.kv) <= NOMINAL_TOLERANCE * bus.kv:
        return None
    return f"{cell(record.nominal_voltage)} {unit} ({own_kv:.4g} kV {bus.system.value}) on {bus.base_voltage}"


def untranscribed_set(model: GlmModel, records, fields_by_class: dict[type, dict[str, Field]]) -> str | None:
    """``untranscribed, set here: <class> <slot> <count>, ...``: the untranscribed slots of ``fields_by_class`` this
    model sets on ``records`` (D5: nothing disappears silently)."""
    counts: Counter = Counter()
    for record in records:
        fields = fields_by_class.get(type(record))
        if fields is None:
            continue
        for slot, field in fields.items():
            if field.kind == "untranscribed" and (getattr(record, slot) is not None
                                                  or (str(record.name), slot) in model.expressions):
                counts[(record.class_name, slot)] += 1
    if not counts:
        return None
    return "untranscribed, set here: " + ", ".join(f"{cls} {slot} {count}" for (cls, slot), count in sorted(counts.items()))


def map_buses(model: GlmModel, buses: dict[str, BusSystem], roots: dict[str, str], feeder: str) -> Document:
    """``bus.cimtbl``: one ``ConnectivityNode`` per root bus the walk reaches, with the walk's BaseVoltage; highest
    voltage first, then by name. Children are named on their root's row; ``nominal_voltage`` disagreements and the
    untranscribed slots this model sets are on the table comment."""
    records = bus_records(model)
    children = _check_children(records, roots)
    disagreements: dict[str, list[str]] = defaultdict(list)  # how it disagrees -> the objects, by name
    for name in sorted(roots):
        if roots[name] in buses:
            how = _disagreement(model, records[name], buses[roots[name]])
            if how is not None:
                disagreements[how].append(name)
    rows = []
    for name in sorted((root for root in set(roots.values()) if root in buses),
                       key=lambda bus: (-nominal_kv(buses[bus].kv), bus)):
        notes = []
        if children[name]:
            notes.append("children: " + ", ".join(children[name]))
        if str(records[name].bustype) == "SWING_PQ":
            notes.append("bustype SWING_PQ: a plain bus here; it is a swing only when its island separates (S1-2)")
        rows.append(Row([name, name, buses[name].base_voltage], comment="; ".join(notes) or None))
    comments = []
    if disagreements:
        for how, names in sorted(disagreements.items()):
            comments.append(_wrap(f"nominal_voltage disagrees with the walk ({NOMINAL_TOLERANCE:.0%}): {how} "
                                  f"({len(names)}): " + ", ".join(names)))
    untranscribed = untranscribed_set(model, records.values(), FIELDS)
    if untranscribed:
        comments.append(_wrap(untranscribed))
    table = Table("ConnectivityNode", [Column("mRID"), Column("name"), Column("BaseVoltage"),
                                       Column("ConnectivityNodeContainer", default=feeder)], rows,
                  comment="\n".join(comments) or None)
    return Document(name="bus", statements=[table], profile=CIM_PROFILE,
                    comment=f"GridLAB-D buses -> ConnectivityNode, BaseVoltage from the topology walk "
                            f"(cimtopology.core); {len(rows)} buses.\nMapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#buses")


# ---------------------------------------------------------------------------
# source.cimtbl
# ---------------------------------------------------------------------------

#: GridLAB-D's swing bus has no source impedance; round trips need one (S1-3). A stiff source: short-circuit
#: capacity and X/R, the same in zero sequence.
DEFAULT_SHORT_CIRCUIT_MVA = 10_000.0
DEFAULT_X_OVER_R = 10.0


def default_source_impedance(kv: float) -> tuple[float, float]:
    """``(r, x)`` in ohm of the default source on ``kv`` (line to line): |Z| = kV^2 / ``DEFAULT_SHORT_CIRCUIT_MVA``,
    x / r = ``DEFAULT_X_OVER_R``. 12.47 kV gives |Z| = 0.01555 ohm."""
    z = kv ** 2 / DEFAULT_SHORT_CIRCUIT_MVA
    r = z / math.sqrt(1 + DEFAULT_X_OVER_R ** 2)
    return r, r * DEFAULT_X_OVER_R


def _source_voltage(model: GlmModel, record) -> tuple[str | None, complex, str]:
    """``(slot, V, unit)``: the substation's ``positive_sequence_voltage``, else ``voltage_A`` (``voltage_1`` on a
    triplex bus); ``(None, nominal_voltage, its unit)`` when none is set."""
    candidates = ["positive_sequence_voltage"] if isinstance(record, schema.Substation) else []
    candidates.append("voltage_1" if isinstance(record, schema.TriplexNode) else "voltage_A")
    for slot in candidates:
        if (str(record.name), slot) in model.expressions:
            raise ValueError(f"{record.class_name} {record.name}: {slot} is the expression "
                             f"{model.expressions[(str(record.name), slot)]!r}")
        value = getattr(record, slot)
        if value is not None:
            return slot, complex(value.real, value.imag), model.unit(record, slot)
    return None, complex(record.nominal_voltage, 0.0), model.unit(record, "nominal_voltage")


def _source_row(model: GlmModel, record, bus: BusSystem) -> tuple[tuple[str, str], Row]:
    name = str(record.name)
    reference = getattr(record, "reference_phase", None)  # substations only
    if reference is not None and str(reference) != "PHASE_A":
        raise ValueError(f"substation {name}: reference_phase {reference}; only PHASE_A is mapped")
    if record.nominal_voltage is None:
        raise ValueError(f"{record.class_name} {name}: a swing bus with no nominal_voltage")
    nominal_unit = model.unit(record, "nominal_voltage")
    slot, voltage, voltage_unit = _source_voltage(model, record)
    # a polar value as written: |V| and arg(V) of its rectangular form differ in the last bit between C libraries.
    # A rectangular one's |V| is math.hypot, not abs(complex): abs() calls the C library's hypot, whose last bit varies
    # with the CPU (a golden written on one machine failed on the CI runner); CPython's math.hypot is the same everywhere.
    written = model.polar.get((name, slot))
    if written is not None:
        magnitude, angle = written
    else:
        magnitude, angle = math.hypot(voltage.real, voltage.imag), math.degrees(cmath.phase(voltage))
    in_nominal_unit = units.Quantity(magnitude, voltage_unit).to(nominal_unit).magnitude
    if abs(in_nominal_unit - record.nominal_voltage) > NOMINAL_TOLERANCE * record.nominal_voltage:
        raise ValueError(f"{record.class_name} {name}: source voltage {magnitude:g} {voltage_unit} ({slot}) is more "
                         f"than {NOMINAL_TOLERANCE:.0%} from nominal_voltage {record.nominal_voltage:g} {nominal_unit}")
    nominal = line_voltage(record.nominal_voltage, bus.system)
    r, x = default_source_impedance(units.Quantity(nominal, nominal_unit).to("kV").magnitude)
    derived = f"derived: nominalVoltage = line_voltage(nominal_voltage={cell(record.nominal_voltage)})"
    if slot is None:
        derived += "; defaulted: voltageMagnitude, voltageAngle = nominal_voltage at 0 deg"
    elif written is not None:
        sign = "+" if angle >= 0 else ""
        derived += f", voltageMagnitude and voltageAngle from {slot}={cell(magnitude)}{sign}{cell(angle)}d (as written)"
    else:
        sign = "+" if voltage.imag >= 0 else ""
        derived += f", voltageMagnitude and voltageAngle from {slot}={cell(voltage.real)}{sign}{cell(voltage.imag)}j"
    derived += (f"; defaulted: r x r0 x0 of a stiff source, {DEFAULT_SHORT_CIRCUIT_MVA:g} MVA short circuit, "
                f"X/R {DEFAULT_X_OVER_R:g} (S1-3)")
    phases = "".join(sorted(phase_letters(record)))
    cells = [mrid("src_", name), name, name, phases_cell(phases), cell(nominal),
             cell(line_voltage(magnitude, bus.system)), cell(angle),
             cell(r), cell(x), cell(r), cell(x), bus.base_voltage]
    return (nominal_unit, voltage_unit), Row(cells, comment=derived)


def map_source(model: GlmModel, buses: dict[str, BusSystem], substation: str) -> Document:
    """``source.cimtbl``: an ``EnergySource`` per substation and SWING bus, and the substations' ``BasePower``."""
    statements: list = []
    grouped: dict[tuple[str, str], list[Row]] = defaultdict(list)
    sources = swing_buses(model)
    for record in sources:
        name = str(record.name)
        if name not in buses:
            raise ValueError(f"{record.class_name} {name}: the walk did not reach this swing bus")
        if isinstance(record, schema.Substation) and record.base_power is not None:
            statements.append(ObjectStatement("BasePower", [
                (Column("mRID"), mrid("sbase_", name)),
                (Column("basePower", model.unit(record, "base_power")), cell(record.base_power))]))
        key, row = _source_row(model, record, buses[name])
        grouped[key].append(row)
    for (nominal_unit, voltage_unit), rows in sorted(grouped.items()):
        columns = [Column("mRID"), Column("name"), Column("node"), Column("phases"),
                   Column("nominalVoltage", nominal_unit), Column("voltageMagnitude", voltage_unit),
                   Column("voltageAngle", "deg"), Column("r", "ohm"), Column("x", "ohm"), Column("r0", "ohm"),
                   Column("x0", "ohm"), Column("BaseVoltage"), Column("EquipmentContainer", default=substation)]
        statements.append(Table("EnergySource", columns, rows))
    return Document(name="source", statements=statements, profile=CIM_PROFILE,
                    comment=f"GridLAB-D substation and SWING buses -> EnergySource; sources: {len(sources)}.\n"
                            f"Mapping: cimhub_gridlabd/docs/CIMTBL_MAPPING.md#source")
