"""EnergyConsumer -> GLM ``load`` or ``triplex_load``, parented to its bus
(``EXPORT_MAPPING.md#x3-loads-and-capacitors``; the importer's S4a inverted).

GLM's ``base_power`` form holds a ZIP load per phase: for each part k (impedance, current, power) of the
LoadResponseCharacteristic, S_k = P x p_k + j Q x q_k at nominal voltage, ``base_power_X`` = sum |S_k|,
``<k>_fraction_X`` = |S_k| / base and ``<k>_pf_X`` = P_k / |S_k|, negative when Q_k is (GridLAB-D's leading
sign). Per phase is ``get_phase_loads``' (EnergyConsumerPhase values, else the total split evenly):

- wye: ``_A``/``_B``/``_C`` on the phases, ``phases`` the letters then N;
- delta: GLM's A, B, C are the branches AB, BC, CA (``node.cpp:2535``), as are the branch children cimtables'
  binder makes on a delta consumer (``ld_x_AB`` has phase A, ``_BC`` B, ``_AC`` C), so a three-phase delta's per
  phase is GLM's per branch; a two-phase delta is its one branch; ``phases`` the letters then D;
- split phase: a wye consumer on s1, s2 is the legs ``_1``/``_2``, a delta one the 240 V part ``_12``. The GLM
  importer makes a record's 240 V part its own consumer ``<base>_12`` (S4a-6), so a ``<base>_12`` delta consumer on
  the bus of the wye consumer ``<base>`` is that consumer's ``_12`` again, and one alone is named ``<base>``.

A voltage-exponent model whose exponents are 0, 1 or 2 is exactly constant power, current or impedance (``EXPONENT_KIND``);
another exponent raises, as does a negative part (generation): GLM's base_power form has neither. A consumer of no
power is a load with no base.

A ConformLoad whose group's schedule is a player (``player.py``) writes each base as ``<player>.value*<base>`` (an
expression, as the reader keeps it), and one whose group's days are a GLM schedule (``schedule.py``) as
``<schedule>*<base>``; its 240 V part must follow the same source. A ConformLoad whose group has no schedule or no
points, and a NonConformLoad, are written static, their groups named in one warning (X29, X30).
"""

from __future__ import annotations

import logging

import cimprofiles.cim18.cim18v17 as cim
from cimtopology.core import System

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.load import get_load_response, get_phase_loads
from cimhub_core.getters.load_schedule import get_load_schedule
from cimhub_core.getters.terminals import get_terminal_nodes
from cimhub_core.names import export_name
from cimhub_gridlabd.exporter import player, schedule
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.glm_writer import format_float
from cimhub_gridlabd.schema import gridlabd as schema

CIM_CLASSES = (cim.EnergyConsumer, cim.ConformLoad, cim.NonConformLoad)
KINDS = ("impedance", "current", "power")
#: a voltage exponent GLM holds exactly -> its ZIP part
EXPONENT_KIND = {0.0: "power", 1.0: "current", 2.0: "impedance"}
DELTA = cim.PhaseShuntConnectionKind.D
#: a delta load's branch -> GLM's slot letter (``node.cpp:2535``)
BRANCH_SLOT = {"AB": "A", "BC": "B", "AC": "C"}
#: a split-phase leg -> GLM's suffix
LEG = {cim.SinglePhaseKind.s1: "1", cim.SinglePhaseKind.s2: "2"}
#: GLM's base_power is in VA, so P is read in W and Q in VAr
if glm_unit(schema.Load, "base_power_A") != "VA" or glm_unit(schema.TriplexLoad, "base_power_1") != "VA":
    raise ValueError("GLM base_power is no longer in VA; the load export's units must follow it")

_SLOTS = {
    "name": Slot("written", "Names (X1)"), "parent": Slot("written", "its bus"),
    "phases": Slot("written", "the letters then N (wye) or D (delta); a split-phase bus's letter then S"),
    "nominal_voltage": Slot("written", "its bus's"),
}
_PER_PHASE = Slot("written", "base_power form: module docstring; <player>.value*<base> on a ConformLoad whose group's "
                             "schedule is a player (X29), <schedule>*<base> on one whose group's days are a GLM "
                             "schedule (X30)")
SLOTS = {
    schema.Load: with_default(schema.Load, {
        **_SLOTS, **{f"base_power_{letter}": _PER_PHASE for letter in "ABC"},
        **{f"{kind}_{part}_{letter}": _PER_PHASE for kind in KINDS for part in ("fraction", "pf") for letter in "ABC"},
    }, Slot("unset", "not in CIM; GridLAB-D's default (the explicit constant_* forms are not written)")),
    schema.TriplexLoad: with_default(schema.TriplexLoad, {
        **_SLOTS, **{f"base_power_{leg}": _PER_PHASE for leg in ("1", "2", "12")},
        **{f"{kind}_{part}_{leg}": _PER_PHASE for kind in KINDS for part in ("fraction", "pf")
           for leg in ("1", "2", "12")},
    }, Slot("unset", "not in CIM; GridLAB-D's default")),
}


_log = logging.getLogger(__name__)


def export(context) -> list:
    consumers = context.objects(*CIM_CLASSES)
    by_name = {(get_terminal_nodes(consumer)[0], export_name(consumer, context.names.source)): consumer
               for consumer in consumers}
    records, merged, players, static = [], set(), {}, set()
    for consumer in consumers:
        if consumer.mRID in merged:
            continue
        [node] = get_terminal_nodes(consumer)
        text = export_name(consumer, context.names.source)
        native_class, slots = _load(consumer, context.buses[node])
        drop = ""
        if _is_240v_part(consumer, text, context.buses[node]):
            base = by_name.get((node, text[:-3]))
            if base is not None:
                continue  # written with its legs, below
            drop = "_12"
        follows = _player(context, consumer, players, static)
        part = by_name.get((node, text + "_12"))
        if part is not None and _is_240v_part(part, text + "_12", context.buses[node]):
            if _player(context, part, players, static) != follows:
                raise ValueError(f"EnergyConsumer {part.mRID!r}: the 240 V part of {consumer.mRID!r} follows another "
                                 "player; a GLM record's bases follow one")
            slots.update({slot: value for slot, value in _load(part, context.buses[node])[1].items()
                          if slot.endswith("_12")})
            merged.add(part.mRID)
        name = context.names.name(consumer, drop=drop)
        if follows is not None:
            for slot in [slot for slot in slots if slot.startswith("base_power_")]:
                context.model.expressions[(name, slot)] = f"{follows}*{format_float(slots.pop(slot))}"
        records.append(native_class(name=name, **slots))
    if static:
        _log.warning("%d load group(s) are written static (no schedule, no points, or a NonConformLoad's): %s",
                     len(static), sorted(static))
    return records


def _player(context, consumer, players: dict, static: set) -> str | None:
    """What the consumer's base reads, ``<player>.value`` or ``<schedule>``, or None (``players``: schedule uri ->
    player name or None, so each schedule's points are checked once; ``static``: the groups written static). A group
    of days reads the schedule ``schedule.py`` wrote for it."""
    found = get_load_schedule(consumer)
    if found is None:
        return None
    if found.conform and found.schedule is not None:
        uri = found.schedule.uri()
        if uri not in players:
            has_points = player.points(context, found.schedule) is not None
            players[uri] = player.player_name(context, found.schedule) if has_points else None
        if players[uri] is not None:
            return f"{players[uri]}.value"
    if found.conform and found.days:
        name = schedule.schedule_name(context, found.group)
        if name in context.model.schedules:
            return name
    static.add(str(found.group.name or found.group.mRID))
    return None


def _is_240v_part(consumer: cim.EnergyConsumer, text: str, bus) -> bool:
    """A delta consumer on a split-phase bus exported as ``<base>_12``: the GLM importer's 240 V part (S4a-6)."""
    return bus.system is System.SPLIT_PHASE and consumer.phaseConnection is DELTA and text.endswith("_12")


def _load(consumer: cim.EnergyConsumer, bus) -> tuple[type, dict]:
    """The consumer's GLM class and slots, without its name."""
    split = bus.system is System.SPLIT_PHASE
    native_class = schema.TriplexLoad if split else schema.Load
    loads = get_phase_loads(consumer, active_unit="W", reactive_unit="VAr")
    delta = loads.connection is DELTA
    slots = {"parent": bus.name, "nominal_voltage": bus.nominal_voltage}
    if split:
        slots["phases"] = bus.phases
        if delta:
            parts = {"12": _sum(loads.per_phase.values())}
        else:
            parts = {LEG[phase]: power for phase, power in loads.per_phase.items()}
    else:
        phase_letters = letters(loads.phases)
        slots["phases"] = phase_letters + ("D" if delta else "N")
        parts = _delta_parts(consumer, loads, phase_letters) if delta else {
            letters((phase,)): power for phase, power in loads.per_phase.items()}
    fractions = _fractions(consumer)
    for suffix, power in parts.items():
        slots.update(_zip_slots(consumer, suffix, power, fractions))
    return native_class, slots


def _delta_parts(consumer, loads, phase_letters: str) -> dict:
    if len(phase_letters) == 3:
        return {letters((phase,)): power for phase, power in loads.per_phase.items()}
    if len(phase_letters) == 2:
        return {BRANCH_SLOT[phase_letters]: _sum(loads.per_phase.values())}
    raise ValueError(f"EnergyConsumer {consumer.mRID!r}: a delta load on one phase")


def _sum(powers):
    powers = list(powers)
    return type(powers[0])(sum(power.p for power in powers), sum(power.q for power in powers))


def _fractions(consumer) -> dict[str, tuple[float, float]]:
    """``{kind: (p share, q share)}`` of the consumer's LoadResponseCharacteristic (module docstring)."""
    response = get_load_response(consumer)
    if not response.exponential:
        return {"impedance": (response.p_impedance, response.q_impedance),
                "current": (response.p_current, response.q_current), "power": (response.p_power, response.q_power)}
    exponents = (response.p_exponent, response.q_exponent)
    if any(exponent not in EXPONENT_KIND for exponent in exponents):
        raise ValueError(f"EnergyConsumer {consumer.mRID!r}: voltage exponents {exponents}; GLM holds 0, 1 or 2 only")
    fractions = {kind: [0.0, 0.0] for kind in KINDS}
    fractions[EXPONENT_KIND[exponents[0]]][0] = 1.0
    fractions[EXPONENT_KIND[exponents[1]]][1] = 1.0
    return {kind: tuple(shares) for kind, shares in fractions.items()}


def _zip_slots(consumer, suffix: str, power, fractions: dict) -> dict:
    """``base_power_X`` and each part's fraction and power factor (module docstring)."""
    parts = {kind: complex(power.p * p_share, power.q * q_share) for kind, (p_share, q_share) in fractions.items()}
    if any(part.real < 0 for part in parts.values()):
        raise ValueError(f"EnergyConsumer {consumer.mRID!r}: a negative p; GLM's base_power holds consumption only")
    base = sum(abs(part) for part in parts.values())
    if base == 0:
        return {}
    slots = {f"base_power_{suffix}": base}
    for kind, part in parts.items():
        if abs(part) == 0:
            continue
        slots[f"{kind}_fraction_{suffix}"] = abs(part) / base
        power_factor = part.real / abs(part)
        slots[f"{kind}_pf_{suffix}"] = -power_factor if part.imag < 0 else power_factor
    return slots
