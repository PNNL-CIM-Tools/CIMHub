"""PowerTransformer (and an AutoTransformer that is not a VoltageRegulator) -> GLM ``transformer`` +
``transformer_configuration`` (``EXPORT_MAPPING.md#x2-transformers-and-regulators``, decisions X2-X4, X7).

Each unit (``get_transformer_units``: a tank, else the transformer) is read once (``get_transformer_model``, per unit
on winding 1's ``ratedS``) and written in one of four forms:

- **native** (X2): two windings GridLAB-D models, Y/Yn/I to Y/Yn/I on the same phases ``WYE_WYE`` (one coil
  ``SINGLE_PHASE``), D-D on three phases ``DELTA_DELTA``, D-Yn on three phases at GridLAB-D's fixed shift
  (``DELTA_GWYE``, the high side leading by 30 degrees, ``transformer.cpp:663``; an unset ``phaseShift`` is that
  standard connection) ``DELTA_GWYE``;
- **centre tap**: three windings on s1, s2, N, ``SINGLE_PHASE_CENTER_TAPPED`` with the model's star written whole
  (``impedance`` the primary's branch, ``impedance1``/``impedance2`` the halves, each on its own winding's voltage,
  ``transformer.cpp:845``);
- **wye-wye replacement** (X3, the user's rule): any other two-winding model as ``WYE_WYE`` on winding 1's phases,
  from the ends' ratings and the (1, 2) impedance; the phase shift, the zero-sequence path and the grounding are
  lost, and each is logged;
- **star split** (X4, the user's rule): three windings that are not a centre tap become three two-winding legs, winding
  i to a fake 1 kV star bus (``<unit>_star``). Star branch Zi = (Zij + Zik - Zjk) / 2 on winding 1's ``ratedS``,
  each leg on its own winding's ``ratedS``. A D winding's leg is ``DELTA_GWYE`` (the delta on the winding's side, so
  its shift is kept), a Y/Yn/I one ``WYE_WYE``, any other ``WYE_WYE`` as X3. The core is on leg 1.

Four or more windings raise. GridLAB-D's base is ``secondary_voltage``² / ``power_rating`` as written
(``transformer.cpp:244``): a polyphase unit is written line to line on its whole kVA, a coil (one phase) on its own
voltage and kVA, so a percent on the unit's own base needs no change, except a polyphase wye on n < 3 phases,
whose coil base is n/3 of GridLAB-D's (the importer's k = 3 S_coil / S_total, S3b-4, inverted). GridLAB-D throws on
R <= 0 or X <= 0 (``transformer_configuration.cpp:337``), so such a branch is written at ``FLOOR`` pu and logged
(the user's rule, section 8.5 Q2). A RatioTapChanger on the unit (an LTC) is folded into its winding's voltage at the
actual step; its control is not written (X5).
"""

from __future__ import annotations

import logging
import math
from typing import NamedTuple

import cimprofiles.cim18.cim18v17 as cim

from cimhub_core.export_slots import Slot, with_default
from cimhub_core.getters.tap_changer import get_tap_ratio
from cimhub_core.getters.transformer import Winding, get_transformer_model, get_transformer_units
from cimhub_gridlabd.exporter.buses import letters
from cimhub_gridlabd.exporter.line import ratings
from cimhub_gridlabd.exporter.units import glm_unit
from cimhub_gridlabd.schema import gridlabd as schema

_log = logging.getLogger(__name__)

CIM_CLASSES = (cim.PowerTransformer, cim.AutoTransformer)
CONNECTION = cim.WindingConnection
WYE_KINDS = (CONNECTION.Y, CONNECTION.Yn, CONNECTION.I)
SPLIT = (cim.SinglePhaseKind.s1, cim.SinglePhaseKind.s2)
#: pu written for a series branch whose R or X is not positive (section 8.5 Q2)
FLOOR = 1e-6
#: GridLAB-D's DELTA_GWYE shift of winding 2 (deg): the low side lags by 30 degrees, Dyn1; unset is the same
DELTA_GWYE_SHIFT = -30.0
#: the fake star bus of a three-winding unit (X4), line to line
STAR_VOLTAGE = 1000.0

_CONFIGURATION_SLOTS = {
    "name": Slot("written", "the TankConfiguration's name when every instance wires it alike, else <unit>_config"),
    "connect_type": Slot("written", "WYE_WYE, SINGLE_PHASE, DELTA_DELTA, DELTA_GWYE, SINGLE_PHASE_CENTER_TAPPED "
                                    "(module docstring)"),
    "primary_voltage": Slot("written", "winding 1's ratedU (V), a coil's baseU; an LTC's actual ratio folded in"),
    "secondary_voltage": Slot("written", "winding 2's, likewise; a centre tap's half; a star leg's 1000 V"),
    "power_rating": Slot("written", "winding 1's ratedS (kVA); a star leg's own winding's"),
    **{f"power{letter}_rating": Slot("written", "a coil's or a centre tap's kVA on its phase") for letter in "ABC"},
    "impedance": Slot("written", "the (1, 2) R + jX in pu (R the windings' r and the mesh r); a centre tap's or a "
                                 "star leg's star branch; not positive: FLOOR"),
    "impedance1": Slot("written", "a centre tap's s1 half of the star"),
    "impedance2": Slot("written", "a centre tap's s2 half of the star"),
    "shunt_resistance": Slot("written", "1 / the core g (pu); unset: not written (GridLAB-D's lossless core)"),
    "shunt_reactance": Slot("written", "1 / the core b (pu); unset: not written"),
}
_TRANSFORMER_SLOTS = {
    "name": Slot("written", "the transformer's; a tank of several <transformer>_<n>; a star leg <unit>_<winding>"),
    "phases": Slot("written", "winding 1's A, B, C, then N; a centre tap's letter, then S"),
    "from_node": Slot("written", "winding 1's bus"), "to": Slot("written", "winding 2's bus; a star leg's star bus"),
    "configuration": Slot("written", "its transformer_configuration"),
    **{f"continuous_rating_{letter}": Slot("written", "get_current_limits normal") for letter in "ABC"},
    **{f"emergency_rating_{letter}": Slot("written", "get_current_limits emergency") for letter in "ABC"},
}
SLOTS = {
    schema.TransformerConfiguration: with_default(schema.TransformerConfiguration, _CONFIGURATION_SLOTS,
                                                  Slot("unset", "not in CIM (thermal, inrush); GridLAB-D's default")),
    schema.Transformer: with_default(schema.Transformer, _TRANSFORMER_SLOTS,
                                     Slot("unset", "not in CIM; GridLAB-D's default")),
}


class Leg(NamedTuple):
    """One GLM transformer and the configuration it needs."""

    equipment: object  # the CIM transformer (its ratings and names)
    suffix: str  # the leg's name after the transformer's (``_2``, ``_1_3``)
    name: str
    phases: str
    from_node: str
    to: str
    configuration: dict  # the transformer_configuration's slots, without its name
    template: object | None  # the TankConfiguration a shared configuration is named by
    with_ratings: bool


def export(context) -> list:
    legs, stars = [], []
    singles, banks = _group_banks(context.objects(*CIM_CLASSES))
    for transformer, suffix, model, template in singles:
        unit_legs, star = _unit_legs(transformer, model, template, suffix, context)
        legs += unit_legs
        stars += star
    for bank in banks:
        _log.warning("%s: single-phase units with a phase-to-phase coil on the same buses, written as one bank",
                     ", ".join(transformer.mRID for transformer, _ in bank))
        unit_legs, star = _unit_legs(bank[0][0], bank_model([model for _, model in bank]), None, "", context)
        legs += unit_legs
        stars += star
    configurations = _configurations(legs, context.names)
    records = [*stars]
    records += [schema.TransformerConfiguration(name=name, **slots) for name, slots in configurations.values()]
    for leg in legs:
        slots = {"name": leg.name, "phases": leg.phases, "from_node": leg.from_node, "to": leg.to,
                 "configuration": configurations[_configuration_key(leg)][0]}
        if leg.with_ratings:
            slots.update(ratings(leg.equipment, letters(_phase_kinds(leg.phases)), schema.Transformer))
        records.append(schema.Transformer(**slots))
    return records


def _read(unit):
    """The unit's model in pu on winding 1's ratedS, voltages and powers in GLM's units."""
    return get_transformer_model(unit, "pu", voltage_unit=glm_unit(schema.TransformerConfiguration, "primary_voltage"),
                                 power_unit=glm_unit(schema.TransformerConfiguration, "power_rating"))


def _group_banks(transformers) -> tuple[list[tuple], list[list[tuple]]]:
    """``(singles, banks)``: each unit as ``(transformer, suffix, model, template)``, except single-phase units with
    a phase-to-phase coil whose windings land on the same buses, which GLM can only write together (the user's rule,
    2026-11-21): each such group of two or three is a bank of ``(transformer, model)``."""
    singles, candidates = [], {}
    for transformer in transformers:
        units = get_transformer_units(transformer)
        for number, unit in enumerate(units, start=1):
            model = _read(unit)
            if len(units) == 1 and _phase_to_phase_can(model):
                key = tuple(winding.end.Terminal.ConnectivityNode.mRID for winding in model.windings)
                candidates.setdefault(key, []).append((transformer, model))
                continue
            singles.append((transformer, "" if len(units) == 1 else f"_{number}", model,
                            getattr(unit, "TankConfiguration", None)))
    banks = []
    for group in candidates.values():
        if len(group) == 1:
            transformer, model = group[0]
            singles.append((transformer, "", model, None))
        else:
            banks.append(sorted(group, key=lambda item: item[0].mRID))
    return singles, banks


def _phase_to_phase_can(model) -> bool:
    """Every winding is one coil, phase to neutral or between two phases, and at least one is between two."""
    shapes = [(len(letters(winding.phases)), cim.SinglePhaseKind.N in winding.phases) for winding in model.windings]
    return all(shape in ((1, True), (2, False)) for shape in shapes) and (2, False) in shapes


def bank_model(models: list):
    """Two or three like cans as one polyphase model: each winding on the union of the cans' phases, wye where its
    coils go to the neutral and delta where they go between phases, its ratedS their sum. The per unit is the cans'
    own, which must agree (unlike cans raise)."""
    first = models[0]
    for other in models[1:]:
        if not _same_per_unit(first, other):
            raise ValueError(f"{other.windings[0].end.mRID!r}: its per unit differs from {first.windings[0].end.mRID!r}; "
                             f"only like cans are written as a bank")
    windings = []
    for number, winding in enumerate(first.windings):
        coils = [model.windings[number] for model in models]
        to_neutral = [cim.SinglePhaseKind.N in coil.phases for coil in coils]
        if any(to_neutral) and not all(to_neutral):
            raise ValueError(f"winding {winding.number} of {winding.end.mRID!r}: its cans mix wye and delta coils")
        bank_letters = letters(phase for coil in coils for phase in coil.phases)
        phases = tuple(cim.SinglePhaseKind(letter) for letter in bank_letters)
        windings.append(winding._replace(phases=phases + ((cim.SinglePhaseKind.N,) if all(to_neutral) else ()),
                                         connection=winding.connection if all(to_neutral) else CONNECTION.D,
                                         rated_s=sum(coil.rated_s for coil in coils), base_u=None))
    return first._replace(windings=tuple(windings), base_power=first.base_power * len(models))


def _same_per_unit(first, other) -> bool:
    """Whether two cans have one series impedance between each pair of windings, in pu on their own bases."""
    if first.mesh.keys() != other.mesh.keys():
        return False
    for pair in first.mesh:
        a, b = _series(first, *pair), _series(other, *pair)
        if not (math.isclose(a.real, b.real, rel_tol=1e-6) and math.isclose(a.imag, b.imag, rel_tol=1e-6)):
            return False
    return True


def _unit_legs(transformer, model, template, suffix: str, context) -> tuple[list[Leg], list]:
    windings = model.windings
    name = context.names.name(transformer, suffix=suffix)
    if len(windings) == 3 and any(phase in SPLIT for winding in windings for phase in winding.phases):
        return [_center_tap(transformer, model, suffix, name, template, context)], []
    if len(windings) == 2:
        connect_type = native_connect_type(windings)
        written = letters(windings[0].phases)
        if connect_type is None:
            _log.warning("%s: %s, not a GridLAB-D connection; written as WYE_WYE (X3)", name,
                         "-".join(str(winding.connection.value) for winding in windings))
            connect_type = "WYE_WYE"
            written = letters(phase for winding in windings for phase in winding.phases)  # an open bank's 3
        return [_two_winding(transformer, model, suffix, name, template, connect_type, written, context)], []
    if len(windings) == 3:
        return _star_split(transformer, model, suffix, name, context)
    raise ValueError(f"{type(transformer).__name__} {transformer.mRID!r}: {len(windings)} windings; GLM takes two, "
                     f"a centre tap or three (a star split)")


def native_connect_type(windings: tuple[Winding, Winding]) -> str | None:
    """The GLM connect_type GridLAB-D models for two windings, or None (module docstring)."""
    first, second = windings
    first_letters, second_letters = letters(first.phases), letters(second.phases)
    if first.connection in WYE_KINDS and second.connection in WYE_KINDS and first_letters == second_letters:
        return "SINGLE_PHASE" if len(first_letters) == 1 else "WYE_WYE"
    if len(first_letters) != 3 or len(second_letters) != 3:
        return None
    if first.connection is CONNECTION.D and second.connection is CONNECTION.D:
        return "DELTA_DELTA"
    if (first.connection is CONNECTION.D and second.connection is CONNECTION.Yn
            and second.phase_shift in (None, DELTA_GWYE_SHIFT)):
        return "DELTA_GWYE"
    return None


def _two_winding(transformer, model, suffix: str, name: str, template, connect_type: str, written: str,
                 context) -> Leg:
    """One GLM transformer on the ``written`` phase letters."""
    first, second = model.windings
    factor = _coil_factor(len(written), connect_type)
    z = _series(model, 1, 2) * factor
    slots = {"connect_type": connect_type, **_ratings(first, second, connect_type),
             "impedance": _complex(_positive(z, name)), **_shunt(model, factor)}
    _fold_taps(model, slots)
    phases = written + ("" if connect_type == "DELTA_DELTA" else "N")
    return Leg(transformer, suffix, name, phases, _bus(first, context), _bus(second, context), slots, template, True)


def _center_tap(transformer, model, suffix: str, name: str, template, context) -> Leg:
    primary, half_1, half_2 = model.windings
    letter = letters(primary.phases)
    if len(letter) != 1:
        raise ValueError(f"{name}: a centre tap's primary is on {letter or 'no phase'}, not one phase")
    star = _star(model)
    kva = primary.rated_s
    slots = {"connect_type": "SINGLE_PHASE_CENTER_TAPPED", "primary_voltage": _coil_voltage(primary),
             "secondary_voltage": _coil_voltage(half_1), "power_rating": kva, f"power{letter}_rating": kva,
             "impedance": _complex(_positive(star[0], name)), "impedance1": _complex(_positive(star[1], name)),
             "impedance2": _complex(_positive(star[2], name)), **_shunt(model, 1.0)}
    _fold_taps(model, slots)
    return Leg(transformer, suffix, name, letter + "S", _bus(primary, context), _bus(half_1, context), slots,
               template, True)


def _star_split(transformer, model, suffix: str, name: str, context) -> tuple[list[Leg], list]:
    windings = model.windings
    star_letters = letters(windings[0].phases)
    star_name = context.names.name(transformer, suffix=suffix + "_star")
    three_phase = len(star_letters) >= 2
    star_bus = schema.Node(name=star_name, phases=star_letters + "N",
                           nominal_voltage=STAR_VOLTAGE / math.sqrt(3) if three_phase else STAR_VOLTAGE)
    legs = []
    for winding, branch in zip(windings, _star(model), strict=True):
        if winding.connection is CONNECTION.D and len(letters(winding.phases)) == 3:
            connect_type = "DELTA_GWYE"
        else:
            if winding.connection not in WYE_KINDS:
                _log.warning("%s winding %d: %s in a star split, written WYE_WYE (X3)", name, winding.number,
                             winding.connection.value)
            connect_type = "WYE_WYE"
        own = winding.rated_s / model.base_power  # the branch moves from winding 1's ratedS to its own
        factor = _coil_factor(len(letters(winding.phases)), connect_type)
        slots = {"connect_type": connect_type, "primary_voltage": _winding_voltage(winding),
                 "secondary_voltage": STAR_VOLTAGE, "power_rating": winding.rated_s,
                 "impedance": _complex(_positive(branch * own * factor, f"{name} winding {winding.number}")),
                 **(_shunt(model, own * factor) if winding.number == 1 else {})}
        _fold_taps(model, slots, only=winding.number)
        leg_suffix = f"{suffix}_{winding.number}"
        legs.append(Leg(transformer, leg_suffix, context.names.name(transformer, suffix=leg_suffix),
                        _phases(winding, connect_type), _bus(winding, context), star_name, slots, None,
                        winding.number == 1))
    return legs, [star_bus]


def _star(model) -> tuple[complex, complex, complex]:
    """The star branches of three windings: Zi = (Zij + Zik - Zjk) / 2."""
    z12, z13, z23 = _series(model, 1, 2), _series(model, 1, 3), _series(model, 2, 3)
    return (z12 + z13 - z23) / 2, (z12 + z23 - z13) / 2, (z13 + z23 - z12) / 2


def _series(model, first: int, second: int) -> complex:
    """R + jX between two windings, pu on the model's base: both windings' r and the mesh's r and x."""
    mesh = model.mesh.get((first, second))
    if mesh is None:
        raise ValueError(f"no mesh impedance between windings {first} and {second} (a {model.form.value} unit)")
    resistance = sum(winding.r or 0.0 for winding in model.windings if winding.number in (first, second))
    return complex(resistance + (mesh.r or 0.0), mesh.x)


def _positive(z: complex, label: str) -> complex:
    """``z`` with an R or X that is not positive written at ``FLOOR`` (GridLAB-D throws on it), logged."""
    if z.real > 0 and z.imag > 0:
        return z
    _log.warning("%s: R + jX %s pu is not positive; written with %g pu in its place (section 8.5 Q2)", label, z,
                 FLOOR)
    return complex(z.real if z.real > 0 else FLOOR, z.imag if z.imag > 0 else FLOOR)


def _coil_factor(count: int, connect_type: str) -> float:
    """GridLAB-D's base against the coil's for a polyphase wye on ``count`` < 3 phases: n / 3 (module docstring)."""
    if connect_type == "WYE_WYE" and count == 2:
        return count / 3
    return 1.0


def _ratings(first: Winding, second: Winding, connect_type: str) -> dict:
    slots = {"primary_voltage": _winding_voltage(first), "secondary_voltage": _winding_voltage(second),
             "power_rating": first.rated_s}
    if connect_type == "SINGLE_PHASE":
        slots[f"power{letters(first.phases)}_rating"] = first.rated_s
    return slots


def _winding_voltage(winding: Winding) -> float:
    """A coil's own voltage, else the winding's ratedU (line to line)."""
    if len(letters(winding.phases)) == 1:
        return _coil_voltage(winding)
    if winding.rated_u is None:
        raise ValueError(f"winding {winding.number} of {winding.end.mRID!r}: ratedU is unset")
    return winding.rated_u


def _coil_voltage(winding: Winding) -> float:
    if winding.base_u is None:
        raise ValueError(f"winding {winding.number} of {winding.end.mRID!r}: has no coil voltage")
    return winding.base_u


def _shunt(model, factor: float) -> dict:
    """The core as GLM's shunt, pu: 1 / g and 1 / b; an unset part is not written."""
    slots = {}
    if model.core.g:
        slots["shunt_resistance"] = factor / model.core.g
    if model.core.b:
        slots["shunt_reactance"] = factor / model.core.b
    return slots


def _fold_taps(model, slots: dict, only: int | None = None) -> None:
    """An LTC at its actual step: its winding's voltage times the ratio (X5); the control is not written."""
    for winding in model.windings:
        tap = getattr(winding.end, "RatioTapChanger", None)
        if tap is None or (only is not None and winding.number != only):
            continue
        slot = "primary_voltage" if winding.number == 1 or only is not None else "secondary_voltage"
        slots[slot] *= get_tap_ratio(tap, which="actual")
        _log.warning("%s: its RatioTapChanger is written at its actual ratio; GLM's transformer has no tap control",
                     tap.mRID)


def _phases(winding: Winding, connect_type: str) -> str:
    return letters(winding.phases) + ("" if connect_type == "DELTA_DELTA" else "N")


def _phase_kinds(phases: str):
    return [cim.SinglePhaseKind(letter) for letter in phases if letter in "ABC"]


def _bus(winding: Winding, context) -> str:
    return context.buses[winding.end.Terminal.ConnectivityNode].name


def _complex(z: complex) -> schema.Complex:
    return schema.Complex(real=z.real, imag=z.imag)


def _configuration_key(leg: Leg) -> tuple:
    return leg.template, tuple(sorted((slot, repr(value)) for slot, value in leg.configuration.items()))


def _configurations(legs: list[Leg], names) -> dict[tuple, tuple[str, dict]]:
    """``{key: (name, slots)}``, one per distinct configuration: a template's name when its instances share one,
    else ``<leg>_config`` (legs without a template that are alike share the first's)."""
    by_template: dict = {}
    for leg in legs:
        by_template.setdefault(leg.template, {}).setdefault(_configuration_key(leg), leg)
    named = {}
    for template, configurations in by_template.items():
        for key, leg in configurations.items():
            if template is not None and len(configurations) == 1:
                name = names.name(template)
            else:
                name = names.name(leg.equipment, suffix=leg.suffix + "_config")
            named[key] = (name, leg.configuration)
    return named
